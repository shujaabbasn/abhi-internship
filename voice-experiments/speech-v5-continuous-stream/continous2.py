import warnings
warnings.filterwarnings("ignore",category=UserWarning,module="webrtcvad")
import threading
import queue
import json
import numpy
import time
import requests
import sounddevice
import subprocess
import webrtcvad
import noisereduce
import torch
from transformers import VitsModel,AutoTokenizer
from faster_whisper import WhisperModel

#CONFIG
#stt
SAMPLE_RATE=16000
WHISPER_MODEL_SIZE="medium"
WHISPER_DEVICE="cpu" #mps not supported by faster-whisper
WHISPER_COMPUTE_TYPE="int8"
AUTO_DETECT_BEAM=1 #first pass
FORCED_URDU_BEAM=3 #if urdu, more beams to decode properly

#llm using alif now, slower
OLLAMA_MODEL="alif-urdu"
OLLAMA_URL="http://localhost:11434/api/chat"
OLLAMA_TEMPERATURE=0.5
OLLAMA_NUM_PREDICT=100
CONTEXT_WINDOW_SIZE=50
SYSTEM_PROMPT=(
    "You are a helpful voice assistant. "
    "Keep replies short, 1-2 sentences maximum. "
    "Answer the question, do not repeat it back to the user. "
    "Reply in only one language per response. "
    "Never use Roman Urdu, Devanagari, markdown, or special symbols."
)

#tts
#english uses piper
#urdu uses meta mms
PIPER_PATH="piper"
PIPER_VOICE_ENGLISH="./voices/en_US-bryce-medium.onnx"
PIPER_SAMPLE_RATE=22050
MMS_URDU_MODEL_ID="facebook/mms-tts-urd-script_arabic"

#vad
VAD_AGGRESSIVENESS=3
FRAME_DURATION_MS=20
SILENCE_DURATION_MS=1000
SILENCE_FRAMES_NEEDED=SILENCE_DURATION_MS//FRAME_DURATION_MS
CONSECUTIVE_SPEECH_FRAMES_NEEDED=8 #160ms sustained speech to confirm start

INTERRUPT_FRAMES_NEEDED=15 #300ms confirmed speech then interrupt
INTERRUPT_ENABLED=False

QUEUE_TIMEOUT=0.5
MAX_LISTEN_SECONDS=15
MIN_RMS=120 #speech rms vol threshold
MIN_AUDIO_SECONDS=0.5 #too short to be real speech
MAX_NO_SPEECH_PROBABILITY=0.6 #whisper hallucination filter for the auto-detect pass

print("loading whisper model")
whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE)
print("loading mms urdu tts model")
mms_model=VitsModel.from_pretrained(MMS_URDU_MODEL_ID)
mms_tokenizer=AutoTokenizer.from_pretrained(MMS_URDU_MODEL_ID)
MMS_SAMPLE_RATE=mms_model.config.sampling_rate
recording_voice_detector=webrtcvad.Vad(VAD_AGGRESSIVENESS)
playback_voice_detector=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000) #320 samples needed by webrtcvad

#recording globals for mic capture and listener loop
audio_parts=[]
frame_buffer=numpy.array([],dtype=numpy.int16)
speech_started=False
silence_count=0
speech_frame_count=0
recording_done=False

stop_event=threading.Event()
pause_event=threading.Event() #pauses mic during playback
listener_thread=None

#sounddevice calls this on every mic chunk, runs the vad state machine
#swap point: replace recording_voice_detector with silero if accuracy needs improving
def capture_mic_audio(audio_input,frame_count,time_info,status):
    global frame_buffer,speech_started,silence_count,speech_frame_count,recording_done
    audio_parts.append(audio_input.copy())
    frame_buffer=numpy.concatenate([frame_buffer,audio_input.flatten()])
    while len(frame_buffer)>=FRAME_SIZE:
        current_frame=frame_buffer[0:FRAME_SIZE]
        frame_buffer=frame_buffer[FRAME_SIZE:]
        is_speech=recording_voice_detector.is_speech(current_frame.tobytes(),SAMPLE_RATE)
        if is_speech==True:
            speech_frame_count=speech_frame_count+1
            if speech_frame_count>=CONSECUTIVE_SPEECH_FRAMES_NEEDED:
                speech_started=True
            silence_count=0
        else:
            speech_frame_count=0
            if speech_started==True:
                silence_count=silence_count+1
                if silence_count>=SILENCE_FRAMES_NEEDED:
                    recording_done=True

#runs on background thread, one cycle per utterance, pauses during playback
def listener_loop(speech_queue):
    global audio_parts,frame_buffer,speech_started,silence_count,speech_frame_count,recording_done
    while stop_event.is_set()==False:
        #hold here while talking
        while pause_event.is_set()==True and stop_event.is_set()==False:
            time.sleep(0.05)
        if stop_event.is_set()==True:
            break
        #reset state
        audio_parts=[]
        frame_buffer=numpy.array([],dtype=numpy.int16)
        speech_started=False
        silence_count=0
        speech_frame_count=0
        recording_done=False
        print("listening")
        start_time=time.time()
        with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=capture_mic_audio):
            while recording_done==False and stop_event.is_set()==False and pause_event.is_set()==False:
                sounddevice.sleep(50)
                if time.time()-start_time>=MAX_LISTEN_SECONDS:
                    break
        #submit only if real speech was detected, no leading silence trim because it clips words
        if len(audio_parts)>0 and speech_started==True:
            recorded_audio=numpy.concatenate(audio_parts,axis=0)
            speech_queue.put(recorded_audio)

def start_listening(speech_queue):
    global listener_thread
    stop_event.clear()
    listener_thread=threading.Thread(target=listener_loop,args=(speech_queue,),daemon=True)
    listener_thread.start()

def pause_listening():
    pause_event.set()

def resume_listening():
    pause_event.clear()

def stop_listening():
    stop_event.set()
    pause_event.clear()
    if listener_thread!=None:
        listener_thread.join(timeout=3)

#https://github.com/urduhack/urdu-characters
def has_arabic_script(text):
    for char in text:
        code_point=ord(char)
        if code_point>=0x0600 and code_point<=0x06FF:
            return True
    return False

#transcription and language detection
def transcribe_and_detect_language(audio_integer):
    flat_audio=audio_integer.flatten()
    if len(flat_audio)/SAMPLE_RATE<MIN_AUDIO_SECONDS:
        return "","en"
    audio_volume=numpy.sqrt(numpy.mean(flat_audio.astype(numpy.float32)**2))
    if audio_volume<MIN_RMS:
        return "","en"
    float_audio=flat_audio.astype(numpy.float32)/32768.0
    cleaned_audio=noisereduce.reduce_noise(y=float_audio,sr=SAMPLE_RATE,prop_decrease=0.5) #audio waveform, sr,spectral gating

    #first pass
    segments,info=whisper_model.transcribe(cleaned_audio,language=None,beam_size=AUTO_DETECT_BEAM)
    auto_text=""
    for segment in segments:
        if segment.no_speech_prob>MAX_NO_SPEECH_PROBABILITY:
            continue
        auto_text=auto_text+segment.text+" "
    auto_text=auto_text.strip()
    print("whisper detected:",info.language)

    #arabic script in output means its already urdu
    if has_arabic_script(auto_text)==True:
        return auto_text,"ur"

    #check if auto-detect gave usable english
    auto_has_letter=False
    for char in auto_text:
        if char.isalpha()==True:
            auto_has_letter=True
            break
    if auto_has_letter==True and len(auto_text)>=3 and info.language=="en":
        return auto_text,"en"

    #auto-detect failed or guessed a non-english language
    #user only speaks english or urdu so forcing urdu
    print("trying forced urdu")
    urdu_segments,_=whisper_model.transcribe(cleaned_audio,language="ur",beam_size=FORCED_URDU_BEAM)
    urdu_text=""
    for segment in urdu_segments:
        urdu_text=urdu_text+segment.text+" "
    urdu_text=urdu_text.strip()
    if has_arabic_script(urdu_text)==True and len(urdu_text)>=2:
        return urdu_text,"ur"

    #nothing worked, fall back to auto-detect text if it had something
    if auto_has_letter==True and len(auto_text)>=3:
        return auto_text,"en"
    return "","en"

#split streaming llm text into speakable chunks at sentence boundaries
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
    return completed,current

def interrupt_monitor(interrupt_event,interrupt_chunks_list):
    monitor_state={"consecutive":0}
    def monitor_mic(indata,frame_count,time_info,status):
        if interrupt_event.is_set()==True:
            return
        interrupt_chunks_list.append(indata.copy())
        mic_frame=indata.flatten()
        is_speech=playback_voice_detector.is_speech(mic_frame.tobytes(),SAMPLE_RATE)
        if is_speech==True:
            monitor_state["consecutive"]=monitor_state["consecutive"]+1
            if monitor_state["consecutive"]>=INTERRUPT_FRAMES_NEEDED:
                interrupt_event.set()
                sounddevice.stop()
        else:
            monitor_state["consecutive"]=0
    monitor_stream=sounddevice.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=FRAME_SIZE,
        callback=monitor_mic
    )
    return monitor_stream

#stream tokens from ollama, split into sentences, push to queue as they complete
#detected_language is passed so llm knows langauge
def stream_llm_sentences(user_text,previous_context,sentence_queue,interrupt_event,detected_language):
    #hard language instruction from what whisper detected
    if detected_language=="ur":
        language_instruction=" The user spoke Urdu. You MUST reply ONLY in Urdu using Arabic script, nothing else."
    else:
        language_instruction=" The user spoke English. You MUST reply ONLY in English."
    full_system_prompt=SYSTEM_PROMPT+language_instruction

    previous_context=previous_context[-CONTEXT_WINDOW_SIZE:]+[{"role":"user","content":user_text}]
    messages=[{"role":"system","content":full_system_prompt}]
    for message in previous_context:
        messages.append(message)
    request_data={
        "model":OLLAMA_MODEL,
        "messages":messages,
        "stream":True,
        "options":{
            "temperature":OLLAMA_TEMPERATURE,
            "num_predict":OLLAMA_NUM_PREDICT
        }
    }
    full_reply=""
    token_buffer=""
    try:
        response=requests.post(OLLAMA_URL,json=request_data,stream=True,timeout=30)
        response.raise_for_status()
        print("bot: ",end="",flush=True)
        for raw_line in response.iter_lines():
            if interrupt_event.is_set()==True:
                break
            if raw_line:
                chunk=json.loads(raw_line)
                token=chunk.get("message",{}).get("content","")
                if len(token)>0:
                    token_buffer=token_buffer+token
                    full_reply=full_reply+token
                    print(token,end="",flush=True)
                    completed,token_buffer=split_sentences(token_buffer)
                    for sentence in completed:
                        if len(sentence)>0:
                            sentence_queue.put(sentence)
                if chunk.get("done",False)==True:
                    break
        #flush the last fragment that had no ending punctuation
        if len(token_buffer.strip())>0 and interrupt_event.is_set()==False:
            sentence_queue.put(token_buffer.strip())
        print()
    except Exception:
        print("llm error")
    sentence_queue.put(None) #tells tts thread no more sentences are coming
    updated_context=previous_context+[{"role":"assistant","content":full_reply}]
    return updated_context

#turn one sentence into a float32 audio array plus its sample rate
#mms takes arabic script urdu directly and the whisper forced-urdu pass produces it
def synthesize_sentence(text,language):
    if language=="ur":
        inputs=mms_tokenizer(text,return_tensors="pt")
        with torch.no_grad():
            model_output=mms_model(**inputs).waveform
        float_audio=model_output.squeeze().numpy()
        return float_audio,MMS_SAMPLE_RATE
    else:
        process=subprocess.run(
            [PIPER_PATH,"--model",PIPER_VOICE_ENGLISH,"--output-raw"],
            input=text.encode("utf-8"),
            capture_output=True
        )
        if len(process.stdout)==0:
            return None,PIPER_SAMPLE_RATE
        raw_audio=numpy.frombuffer(process.stdout,dtype=numpy.int16)
        float_audio=raw_audio.astype(numpy.float32)/32768.0
        return float_audio,PIPER_SAMPLE_RATE

#tts thread
def synthesize_sentences(sentence_queue,audio_queue,detected_language,interrupt_event):
    while interrupt_event.is_set()==False:
        try:
            sentence=sentence_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue
        if sentence is None:
            audio_queue.put(None)
            break
        try:
            audio_data,sample_rate=synthesize_sentence(sentence,detected_language)
            if audio_data is not None:
                audio_queue.put((audio_data,sample_rate))
        except Exception:
            print("tts error")
    #if interrupted mid-synthesis still send sentinel so playback exits cleanly
    if interrupt_event.is_set()==True:
        audio_queue.put(None)

#playback thread: plays each sentence fully and cleanly with sounddevice.play
#sounddevice.play releases the device cleanly on macos so listening works next turn
def play_audio(audio_queue,interrupt_event,interrupt_chunks_list):
    monitor_stream=None
    if INTERRUPT_ENABLED==True:
        monitor_stream=interrupt_monitor(interrupt_event,interrupt_chunks_list)
        monitor_stream.start()
    while interrupt_event.is_set()==False:
        try:
            item=audio_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue
        if item is None:
            break
        playback_audio,sample_rate=item
        sounddevice.play(playback_audio,sample_rate) #soundevice.rec removed for now
        sounddevice.wait()
    if monitor_stream!=None:
        monitor_stream.stop()
        monitor_stream.close()

#main
speech_queue=queue.Queue()
conversation_history=[]
print("starting")
start_listening(speech_queue)
try:
    while True:
        try:
            audio_array=speech_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue
        user_text,detected_language=transcribe_and_detect_language(audio_array)
        #skip empty or noise transcriptions
        if len(user_text.strip())<2:
            continue
        has_letter=False
        for char in user_text:
            if char.isalpha()==True:
                has_letter=True
                break
        if has_letter==False:
            continue

        print("user:",user_text,"["+detected_language+"]")

        #mew interrupt event so old state never carries over
        sentence_queue=queue.Queue()
        audio_queue=queue.Queue()
        interrupt_event=threading.Event()
        interrupt_chunks=[]

        pause_listening()
        time.sleep(0.05) #let the mic stream close

        #tts thread synthesizes sentence 2 while sentence 1 plays simultaneously
        tts_thread=threading.Thread(
            target=synthesize_sentences,
            args=(sentence_queue,audio_queue,detected_language,interrupt_event),
            daemon=True
        )
        tts_thread.start()

        #playback thread plays audio fully and cleanly
        playback_thread=threading.Thread(
            target=play_audio,
            args=(audio_queue,interrupt_event,interrupt_chunks),
            daemon=True
        )
        playback_thread.start()

        #stream the llm on the main thread and tts and playback run in parallel
        llm_start=time.time()
        conversation_history=stream_llm_sentences(
            user_text,conversation_history,sentence_queue,interrupt_event,detected_language
        )
        print("llm:",round(time.time()-llm_start,2),"s")

        tts_thread.join() #main loop pauses till these finish
        playback_thread.join()
        time.sleep(0.3) #letting the audio fully release before the mic reopens
        resume_listening()

        if interrupt_event.is_set()==True:
            if len(interrupt_chunks)>0:
                interruption_audio=numpy.concatenate(interrupt_chunks,axis=0)
                speech_queue.put(interruption_audio)
            continue

except KeyboardInterrupt:
    print("\nshutting down")
    stop_listening()