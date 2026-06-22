import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="webrtcvad")
warnings.filterwarnings("ignore", category=FutureWarning)

import threading
import queue
import json
import numpy as np
import time
import requests
import sounddevice as sd
import webrtcvad
import noisereduce as nr
import torch

# ===== MLX & STT / TTS Libraries =====
import mlx_whisper
from transformers import VitsModel, AutoTokenizer
from kokoro_onnx import Kokoro

# ===== CONFIGURATION =====
SAMPLE_RATE = 16000
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo" # Apple Silicon optimized Whisper

OLLAMA_MODEL = "alif-urdu" # Your custom bilingual model
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TEMPERATURE = 0.5
CONTEXT_WINDOW_SIZE = 50

SYSTEM_PROMPT = (
    "You are a highly capable, bilingual voice assistant. "
    "Keep replies short, 1-2 sentences maximum. "
    "Answer the question, do not repeat it back to the user. "
    "Reply in only one language per response. "
    "Never use Roman Urdu, Devanagari, markdown, or special symbols."
)

MMS_URDU_MODEL_ID = "facebook/mms-tts-urd-script_arabic"

VAD_AGGRESSIVENESS = 3
FRAME_DURATION_MS = 20
SILENCE_DURATION_MS = 1000
SILENCE_FRAMES_NEEDED = SILENCE_DURATION_MS // FRAME_DURATION_MS
CONSECUTIVE_SPEECH_FRAMES_NEEDED = 8 
QUEUE_TIMEOUT = 0.5
MAX_LISTEN_SECONDS = 15
MIN_RMS = 120
MIN_AUDIO_SECONDS = 0.5

# ===== HARDWARE OPTIMIZATION =====
# Detect Apple Silicon GPU (Metal Performance Shaders) for Urdu TTS
mac_gpu = "mps" if torch.backends.mps.is_built() else "cpu"
print(f"Hardware Check: Using {mac_gpu.upper()} for PyTorch models.")

# Load MMS (Urdu) to the Mac GPU
print("Loading MMS Urdu TTS Model to GPU...")
mms_model = VitsModel.from_pretrained(MMS_URDU_MODEL_ID).to(mac_gpu)
mms_tokenizer = AutoTokenizer.from_pretrained(MMS_URDU_MODEL_ID)
MMS_SAMPLE_RATE = mms_model.config.sampling_rate

# Load Kokoro (English) 
print("Loading Kokoro English TTS Model...")
kokoro_tts = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

recording_voice_detector = webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)

# Globals for listening loop
audio_parts = []
frame_buffer = np.array([], dtype=np.int16)
speech_started = False
silence_count = 0
speech_frame_count = 0
recording_done = False

stop_event = threading.Event()
pause_event = threading.Event()
listener_thread = None

# ===== AUDIO CAPTURE =====
def capture_mic_audio(audio_input, frame_count, time_info, status):
    global frame_buffer, speech_started, silence_count, speech_frame_count, recording_done
    audio_parts.append(audio_input.copy())
    frame_buffer = np.concatenate([frame_buffer, audio_input.flatten()])
    while len(frame_buffer) >= FRAME_SIZE:
        current_frame = frame_buffer[0:FRAME_SIZE]
        frame_buffer = frame_buffer[FRAME_SIZE:]
        is_speech = recording_voice_detector.is_speech(current_frame.tobytes(), SAMPLE_RATE)
        if is_speech:
            speech_frame_count += 1
            if speech_frame_count >= CONSECUTIVE_SPEECH_FRAMES_NEEDED:
                speech_started = True
            silence_count = 0
        else:
            speech_frame_count = 0
            if speech_started:
                silence_count += 1
                if silence_count >= SILENCE_FRAMES_NEEDED:
                    recording_done = True

def listener_loop(speech_queue):
    global audio_parts, frame_buffer, speech_started, silence_count, speech_frame_count, recording_done
    while not stop_event.is_set():
        while pause_event.is_set() and not stop_event.is_set():
            time.sleep(0.05)
        if stop_event.is_set():
            break
        audio_parts = []
        frame_buffer = np.array([], dtype=np.int16)
        speech_started = False
        silence_count = 0
        speech_frame_count = 0
        recording_done = False
        
        print("\n🟢 Listening...")
        start_time = time.time()
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=capture_mic_audio):
            while not recording_done and not stop_event.is_set() and not pause_event.is_set():
                sd.sleep(50)
                if time.time() - start_time >= MAX_LISTEN_SECONDS:
                    break
        
        if len(audio_parts) > 0 and speech_started:
            recorded_audio = np.concatenate(audio_parts, axis=0)
            speech_queue.put(recorded_audio)

# ===== BILINGUAL PIPELINE =====
def has_arabic_script(text):
    for char in text:
        if 0x0600 <= ord(char) <= 0x06FF:
            return True
    return False

def transcribe_and_detect(audio_integer):
    flat_audio = audio_integer.flatten()
    if len(flat_audio) / SAMPLE_RATE < MIN_AUDIO_SECONDS:
        return "", "en"
    
    audio_volume = np.sqrt(np.mean(flat_audio.astype(np.float32)**2))
    if audio_volume < MIN_RMS:
        return "", "en"
    
    float_audio = flat_audio.astype(np.float32) / 32768.0
    cleaned_audio = nr.reduce_noise(y=float_audio, sr=SAMPLE_RATE, prop_decrease=0.5)

    # MLX-Whisper handles transcription incredibly fast on Mac unified memory
    try:
        result = mlx_whisper.transcribe(cleaned_audio, path_or_hf_repo=WHISPER_MODEL)
        text = result["text"].strip()
    except Exception as e:
        print("Transcription Error:", e)
        return "", "en"

    # Identify if the user spoke Urdu
    if has_arabic_script(text):
        return text, "ur"
    elif len(text) >= 3:
        return text, "en"
    
    return "", "en"

def stream_llm_sentences(user_text, previous_context, sentence_queue, detected_language):
    lang_rule = " The user spoke Urdu. You MUST reply ONLY in Urdu using Arabic script." if detected_language == "ur" else " The user spoke English. You MUST reply ONLY in English."
    full_prompt = SYSTEM_PROMPT + lang_rule

    previous_context = previous_context[-CONTEXT_WINDOW_SIZE:] + [{"role": "user", "content": user_text}]
    messages = [{"role": "system", "content": full_prompt}] + previous_context
    
    request_data = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "options": {"temperature": OLLAMA_TEMPERATURE}
    }
    
    full_reply, token_buffer = "", ""
    try:
        response = requests.post(OLLAMA_URL, json=request_data, stream=True, timeout=30)
        response.raise_for_status()
        print("🤖 Bot: ", end="", flush=True)
        for raw_line in response.iter_lines():
            if raw_line:
                chunk = json.loads(raw_line)
                token = chunk.get("message", {}).get("content", "")
                
                # Cleanup stray tokens just in case
                token = token.replace("<|im_start|>", "").replace("<|im_end|>", "")
                
                if token:
                    token_buffer += token
                    full_reply += token
                    print(token, end="", flush=True)
                    
                    # Chunking at punctuation
                    completed, current = split_sentences(token_buffer)
                    for sentence in completed:
                        if sentence.strip():
                            sentence_queue.put(sentence.strip())
                    token_buffer = current
                if chunk.get("done", False):
                    break
        if token_buffer.strip():
            sentence_queue.put(token_buffer.strip())
        print()
    except Exception as e:
        print("LLM Error:", e)
    
    sentence_queue.put(None)
    return previous_context + [{"role": "assistant", "content": full_reply}]

def split_sentences(text):
    completed, current = [], ""
    for char in text:
        current += char
        if char in ".?!۔؟":
            if current.strip():
                completed.append(current.strip())
            current = ""
    return completed, current

# ===== DUAL TTS ROUTER =====
def synthesize_sentence(text, language):
    if language == "ur":
        # Pass to Apple Silicon GPU
        inputs = mms_tokenizer(text, return_tensors="pt").to(mac_gpu)
        with torch.no_grad():
            output = mms_model(**inputs).waveform
        float_audio = output.cpu().squeeze().numpy()
        return float_audio, MMS_SAMPLE_RATE
    else:
        # Use Kokoro for hyper-realistic fast English
        samples, sample_rate = kokoro_tts.create(text, voice="af_heart", speed=1.0, lang="en-us")
        return samples, sample_rate

def synthesize_sentences(sentence_queue, audio_queue, detected_language):
    while True:
        try:
            sentence = sentence_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue
        if sentence is None:
            audio_queue.put(None)
            break
        try:
            audio_data, rate = synthesize_sentence(sentence, detected_language)
            if audio_data is not None:
                audio_queue.put((audio_data, rate))
        except Exception as e:
            print(f"TTS error: {e}")

def play_audio(audio_queue):
    while True:
        try:
            item = audio_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue
        if item is None:
            break
        playback_audio, sample_rate = item
        sd.play(playback_audio, sample_rate)
        sd.wait()

# ===== MAIN LOOP =====
speech_queue = queue.Queue()
conversation_history = []

print("🚀 Voice Assistant Initialized (M1 Pro Optimized)")
stop_event.clear()
listener_thread = threading.Thread(target=listener_loop, args=(speech_queue,), daemon=True)
listener_thread.start()

try:
    while True:
        try:
            audio_array = speech_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue

        user_text, detected_lang = transcribe_and_detect(audio_array)
        if len(user_text.strip()) < 2 or not any(c.isalpha() for c in user_text):
            continue

        print(f"\n👤 You [{detected_lang.upper()}]: {user_text}")

        # Pause mic to prevent loopback
        pause_event.set()
        time.sleep(0.05)

        sentence_queue = queue.Queue()
        audio_queue = queue.Queue()

        tts_thread = threading.Thread(target=synthesize_sentences, args=(sentence_queue, audio_queue, detected_lang), daemon=True)
        playback_thread = threading.Thread(target=play_audio, args=(audio_queue,), daemon=True)
        
        tts_thread.start()
        playback_thread.start()

        conversation_history = stream_llm_sentences(user_text, conversation_history, sentence_queue, detected_lang)

        tts_thread.join()
        playback_thread.join()
        time.sleep(0.3) 
        pause_event.clear()

except KeyboardInterrupt:
    print("\n🛑 Shutting down...")
    stop_event.set()
    pause_event.clear()
    listener_thread.join()