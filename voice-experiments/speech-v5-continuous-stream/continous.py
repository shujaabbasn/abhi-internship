import warnings
warnings.filterwarnings("ignore",category=UserWarning,module="webrtcvad")
import threading
import queue
import json
import numpy
import time
import requests
import sounddevice
import webrtcvad
import noisereduce
from faster_whisper import WhisperModel
from piper.voice import PiperVoice
SAMPLE_RATE=16000
WHISPER_MODEL_SIZE="medium"
WHISPER_DEVICE="cpu"
WHISPER_COMPUTE_TYPE="int8"
OLLAMA_MODEL="qwen2.5:7b"
OLLAMA_URL="http://localhost:11434/api/chat"
OLLAMA_TEMPERATURE=0.5
OLLAMA_NUM_PREDICT=100
SYSTEM_PROMPT=(
    "You are a helpful voice assistant. "
    "Keep replies short, 1-2 sentences maximum. "
    "Users may speak in English, Urdu, or mix both. "
    "Reply in only ONE language per response. "
    "If the user speaks mostly Urdu, reply fully in proper Urdu using Arabic/Nastaliq script. "
    "If the user speaks English, reply fully in English. "
    "Never mix languages or scripts in one reply. "
    "Never use Roman Urdu, Devanagari, markdown, or special symbols."
)
PIPER_VOICE_ENGLISH="./voices/en_US-bryce-medium.onnx"
PIPER_VOICE_URDU="./voices/ur_PK-fasih-medium-model.onnx"
PIPER_SAMPLE_RATE=22050

VAD_AGGRESSIVENESS=2 
FRAME_DURATION_MS=20
SILENCE_DURATION_MS=700
SILENCE_FRAMES_NEEDED=SILENCE_DURATION_MS//FRAME_DURATION_MS
QUEUE_TIMEOUT=0.4
MAX_LISTEN_SECONDS=18
CONSECUTIVE_SPEECH_FRAMES_NEEDED=5 
MIN_RMS=100 
MIN_AUDIO_SECONDS=0.4
print("loading models into memory")
whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE)
piper_en=PiperVoice.load(PIPER_VOICE_ENGLISH)
piper_ur=PiperVoice.load(PIPER_VOICE_URDU)
recording_vad=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000)

audio_parts=[]
frame_buffer=numpy.array([],dtype=numpy.int16)
speech_started=False
silence_count=0
speech_frame_count=0
recording_done=False

stop_event=threading.Event()
bot_speaking_event=threading.Event()
global_interrupt_event=threading.Event()

listener_thread=None
is_listening=False

def get_mic_audio(audio_input,frame_count,time_info,status):
    global frame_buffer,speech_started,silence_count,speech_frame_count,recording_done
    audio_parts.append(audio_input.copy())
    frame_buffer=numpy.concatenate([frame_buffer,audio_input.flatten()])
    while len(frame_buffer)>=FRAME_SIZE:
        current_frame=frame_buffer[0:FRAME_SIZE]
        frame_buffer=frame_buffer[FRAME_SIZE:]
        is_speech=recording_vad.is_speech(current_frame.tobytes(),SAMPLE_RATE)
        if is_speech==True:
            speech_frame_count=speech_frame_count+1
            if speech_frame_count>=CONSECUTIVE_SPEECH_FRAMES_NEEDED:
                speech_started=True
                if bot_speaking_event.is_set()==True:
                    print("\n[interrupted!]")
                    global_interrupt_event.set()
            silence_count=0
        else:
            speech_frame_count=0
            if speech_started==True:
                silence_count=silence_count+1
                if silence_count>=SILENCE_FRAMES_NEEDED:
                    recording_done=True

def listener_loop(speech_queue):
    global audio_parts,frame_buffer,speech_started,silence_count,speech_frame_count,recording_done,is_listening
    while stop_event.is_set()==False:
        audio_parts=[]
        frame_buffer=numpy.array([],dtype=numpy.int16)
        speech_started=False
        silence_count=0
        speech_frame_count=0
        recording_done=False
        if is_listening==False:
            print("\n[listening...]")
            is_listening=True
        start_time=time.time()
        with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=get_mic_audio):
            while recording_done==False:
                if stop_event.is_set()==True:
                    break
                sounddevice.sleep(40)
                if time.time()-start_time>=MAX_LISTEN_SECONDS:
                    break
        if len(audio_parts)>0:
            if speech_started==True:
                if global_interrupt_event.is_set()==False:
                    recorded_audio=numpy.concatenate(audio_parts,axis=0)
                    speech_queue.put(recorded_audio)
                    is_listening=False
                else:
                    is_listening=False
            else:
                is_listening=False
        else:
            is_listening=False

def start_listening(speech_queue):
    global listener_thread
    stop_event.clear()
    listener_thread=threading.Thread(target=listener_loop,args=(speech_queue,),daemon=True)
    listener_thread.start()

def stop_listening():
    stop_event.set()
    if listener_thread!=None:
        listener_thread.join(timeout=3)

def transcribe_and_detect_language(audio_integer):
    flat_audio=audio_integer.flatten()
    if len(flat_audio)/SAMPLE_RATE<MIN_AUDIO_SECONDS:
        return "","en"
    audio_volume=numpy.sqrt(numpy.mean(flat_audio.astype(numpy.float32)**2))
    if audio_volume<MIN_RMS:
        return "","en"
    float_audio=flat_audio.astype(numpy.float32)/32768.0
    cleaned_audio=noisereduce.reduce_noise(y=float_audio,sr=SAMPLE_RATE,prop_decrease=0.7)
    segments,info=whisper_model.transcribe(cleaned_audio,language=None,beam_size=5,vad_filter=True)
    text=""
    for segment in segments:
        text=text+segment.text
    text=text.strip()
    print("whisper detected:",info.language)
    has_urdu=False
    for c in text:
        if 0x0600<=ord(c)<=0x06FF:
            has_urdu=True
            break
    if info.language=="ur":
        return text,"ur"
    if has_urdu==True:
        return text,"ur"
    return text,"en"

def split_sentences(text):
    completed=[]
    current=""
    for char in text:
        current=current+char
        if char in ".?!۔؟":
            stripped=current.strip()
            if len(stripped)>0:
                completed.append(stripped)
            current=""
    if len(current.strip())>0:
        completed.append(current.strip())
    return completed

def stream_llm_sentences(user_text,chat_history,sentence_queue):
    chat_history=chat_history[-50:]
    chat_history.append({"role":"user","content":user_text})
    sys_msg={"role":"system","content":SYSTEM_PROMPT}
    messages=[sys_msg]
    for msg in chat_history:
        messages.append(msg)
    request_data={"model":OLLAMA_MODEL,"messages":messages,"stream":True,"options":{"temperature":OLLAMA_TEMPERATURE,"num_predict":OLLAMA_NUM_PREDICT}}
    full_reply=""
    token_buffer=""
    try:
        response=requests.post(OLLAMA_URL,json=request_data,stream=True,timeout=30)
        response.raise_for_status()
        print("bot: ",end="",flush=True)
        for raw_line in response.iter_lines():
            if global_interrupt_event.is_set()==True:
                break
            if raw_line:
                chunk=json.loads(raw_line)
                msg_data=chunk.get("message",{})
                token=msg_data.get("content","")
                if len(token)>0:
                    token_buffer=token_buffer+token
                    full_reply=full_reply+token
                    print(token,end="",flush=True)
                    completed=split_sentences(token_buffer)
                    for i in range(len(completed)):
                        if i<len(completed)-1:
                            sentence=completed[i]
                            if len(sentence)>0:
                                sentence_queue.put(sentence)
                    if len(completed)>0:
                        token_buffer=completed[len(completed)-1]
                is_done=chunk.get("done",False)
                if is_done==True:
                    break
        if len(token_buffer.strip())>0:
            if global_interrupt_event.is_set()==False:
                sentence_queue.put(token_buffer.strip())
        print()
    except Exception:
        print("\n[llm error]")
    sentence_queue.put(None)
    chat_history.append({"role":"assistant","content":full_reply})
    return chat_history

def synthesize_sentences(sentence_queue,audio_queue,voice_obj):
    while global_interrupt_event.is_set()==False:
        try:
            sentence=sentence_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue
        if sentence is None:
            audio_queue.put(None)
            break
        try:
            for audio_bytes in voice_obj.synthesize_stream_raw(sentence):
                if global_interrupt_event.is_set()==True:
                    break
                audio_queue.put(audio_bytes)
        except Exception as e:
            print("tts error:",e)
    audio_queue.put(None)

def play_and_detect_interrupt(audio_queue):
    bot_speaking_event.set()
    stream=sounddevice.OutputStream(samplerate=PIPER_SAMPLE_RATE,channels=1,dtype='int16')
    stream.start()
    while global_interrupt_event.is_set()==False:
        try:
            raw_audio=audio_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue
        if raw_audio is None:
            break
        if global_interrupt_event.is_set()==False:
            audio_chunk=numpy.frombuffer(raw_audio,dtype=numpy.int16)
            stream.write(audio_chunk)
    stream.stop()
    stream.close()
    bot_speaking_event.clear()

def talk_and_listen(sentence_queue,voice_obj):
    audio_queue=queue.Queue()
    tts_thread=threading.Thread(target=synthesize_sentences,args=(sentence_queue,audio_queue,voice_obj),daemon=True)
    playback_thread=threading.Thread(target=play_and_detect_interrupt,args=(audio_queue,),daemon=True)
    tts_thread.start()
    playback_thread.start()
    tts_thread.join()
    playback_thread.join()
speech_queue=queue.Queue()
conversation_history=[]
print("Voice Assistant Started")
start_listening(speech_queue)
try:
    while True:
        try:
            audio_array=speech_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue
        user_text,lang=transcribe_and_detect_language(audio_array)
        if len(user_text.strip())<2:
            continue
        print("\nuser:",user_text,"[",lang,"]")
        global_interrupt_event.clear()
        sentence_queue=queue.Queue()
        voice_obj=None
        if lang=="ur":
            voice_obj=piper_ur
        else:
            voice_obj=piper_en
        speak_thread=threading.Thread(target=talk_and_listen,args=(sentence_queue,voice_obj),daemon=True)
        speak_thread.start()
        conversation_history=stream_llm_sentences(user_text,conversation_history,sentence_queue)
        speak_thread.join()
        global_interrupt_event.clear()
except KeyboardInterrupt:
    print("\nshutting down")
    stop_listening()