import threading
import queue
import numpy
import time
import sounddevice
import webrtcvad
import noisereduce
from faster_whisper import WhisperModel

#config
SAMPLE_RATE=16000
WHISPER_MODEL_SIZE="medium"
WHISPER_DEVICE="cpu"
WHISPER_COMPUTE_TYPE="int8"

#voice activity detection
VAD_AGGRESSIVENESS=3
FRAME_DURATION_MS=20
SILENCE_DURATION_MS=1500
SILENCE_FRAMES_NEEDED=SILENCE_DURATION_MS//FRAME_DURATION_MS

QUEUE_TIMEOUT=0.5
MAX_LISTEN_SECONDS=15
CONSECUTIVE_SPEECH_FRAMES_NEEDED=8

#noise filters
MIN_RMS_ENERGY=120
MIN_AUDIO_SECONDS=0.5
MAX_NO_SPEECH_PROBABILITY=0.6

#banking intents
BANKING_INTENTS=[
    "account_balance",
    "transfer_money",
    "transaction_history",
    "bill_payment",
    "card_block",
    "loan_inquiry",
    "account_opening",
    "pin_change",
    "complaint",
    "branch_locator"
]

#load whisper
print("loading whisper model")
whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE)
print("whisper loaded")

recording_voice_detector=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000)

#recording state
audio_parts=[]
frame_buffer=numpy.array([],dtype=numpy.int16)
speech_started=False
silence_count=0
speech_frame_count=0
recording_done=False

stop_event=threading.Event()
listener_thread=None

def microphone_callback(audio_input,frame_count,time_info,status):
    global frame_buffer,speech_started,silence_count,speech_frame_count,recording_done
    if status==True:
        print(status)
    audio_parts.append(audio_input.copy())
    frame_buffer=numpy.concatenate([frame_buffer,audio_input.flatten()])
    while len(frame_buffer)>=FRAME_SIZE:
        current_frame=frame_buffer[:FRAME_SIZE]
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

def listener_loop(speech_queue):
    global audio_parts,frame_buffer,speech_started,silence_count,speech_frame_count,recording_done
    while stop_event.is_set()==False:
        if stop_event.is_set()==True:
            break
        audio_parts=[]
        frame_buffer=numpy.array([],dtype=numpy.int16)
        speech_started=False
        silence_count=0
        speech_frame_count=0
        recording_done=False
        print("listening...")
        start_time=time.time()
        with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=microphone_callback):
            while recording_done==False and stop_event.is_set()==False:
                sounddevice.sleep(50)
                if time.time()-start_time>=MAX_LISTEN_SECONDS:
                    print("timeout")
                    break
        if len(audio_parts)>0 and speech_started==True and recording_done==True:
            recorded_audio=numpy.concatenate(audio_parts,axis=0)
            speech_queue.put(recorded_audio)

def start_listening(speech_queue):
    global listener_thread
    stop_event.clear()
    listener_thread=threading.Thread(target=listener_loop,args=(speech_queue,),daemon=True)
    listener_thread.start()

def stop_listening():
    stop_event.set()
    if listener_thread:
        listener_thread.join(timeout=3)

#transcription and language detection
def transcribe_and_detect_language(audio_integer):
    flat_audio=audio_integer.flatten()

    audio_duration=len(flat_audio)/SAMPLE_RATE
    if audio_duration<MIN_AUDIO_SECONDS:
        print("audio too short, skipping")
        return "","en"

    root_mean_square=numpy.sqrt(numpy.mean(flat_audio.astype(numpy.float32)**2))
    print("rms energy:",round(root_mean_square))
    if root_mean_square<MIN_RMS_ENERGY:
        print("audio too quiet, skipping")
        return "","en"

    float_audio=flat_audio.astype(numpy.float32)/32768.0
    cleaned_audio=noisereduce.reduce_noise(y=float_audio,sr=SAMPLE_RATE,prop_decrease=0.5)

    print("transcribing...")
    _,language_detection=whisper_model.transcribe(cleaned_audio,language=None)

    if language_detection.language=="ur" and language_detection.language_probability>0.3:
        detected_language="ur"
    else:
        detected_language="en"

    urdu_probability=language_detection.language_probability
    if language_detection.language!="ur":
        urdu_probability=0.0
    print("urdu probability:",urdu_probability)

    segments,_=whisper_model.transcribe(cleaned_audio,language=detected_language)
    user_text=""
    for segment in segments:
        if segment.no_speech_prob>MAX_NO_SPEECH_PROBABILITY:
            print("skipping hallucinated segment:",segment.text[:50])
            continue
        user_text=user_text+segment.text+" "
    user_text=user_text.strip()
    return user_text,detected_language