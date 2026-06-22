import threading
import wave
import numpy
import time
import sounddevice
import webrtcvad
from config import (SAMPLE_RATE,VAD_AGGRESSIVENESS,FRAME_DURATION_MS,
                    SILENCE_FRAMES_NEEDED,MAX_LISTEN_SECONDS,CONSECUTIVE_SPEECH_FRAMES_NEEDED)

vad=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000)

#global state for vad callback
audio_parts=[]
frame_buffer=numpy.array([],dtype=numpy.int16)
speech_started=False
silence_count=0
speech_frame_count=0
done=False

#thread control
stop_event=threading.Event()
listener_thread=None

def vad_callback(indata,__,_,status):
    global frame_buffer,speech_started,silence_count,speech_frame_count,done
    if status:
        print(status)
    audio_parts.append(indata.copy())
    frame_buffer=numpy.concatenate([frame_buffer,indata.flatten()])
    while len(frame_buffer)>=FRAME_SIZE:
        frame=frame_buffer[:FRAME_SIZE]
        frame_buffer=frame_buffer[FRAME_SIZE:]
        if vad.is_speech(frame.tobytes(),SAMPLE_RATE):
            speech_frame_count=speech_frame_count+1
            if speech_frame_count>=CONSECUTIVE_SPEECH_FRAMES_NEEDED:
                speech_started=True
            silence_count=0
        else:
            speech_frame_count=0
            if speech_started==True:
                silence_count=silence_count+1
                if silence_count>=SILENCE_FRAMES_NEEDED:
                    done=True

def _listener_loop(speech_queue):
    global audio_parts,frame_buffer,speech_started,silence_count,speech_frame_count,done
    while stop_event.is_set()==False:
        #reset state for new utterance
        audio_parts=[]
        frame_buffer=numpy.array([],dtype=numpy.int16)
        speech_started=False
        silence_count=0
        speech_frame_count=0
        done=False
        print("listening")
        start_time=time.time()
        with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=vad_callback):
            while done==False and stop_event.is_set()==False:
                sounddevice.sleep(50)
                if time.time()-start_time>=MAX_LISTEN_SECONDS:
                    print(f"timeout after {MAX_LISTEN_SECONDS}s")
                    break
        #only queue if actual speech was detected
        if len(audio_parts)>0 and speech_started==True:
            timestamp=time.strftime("%d-%m-%Y_%H-%M-%S")
            filename=f"input_{timestamp}.wav"
            recorded_audio=numpy.concatenate(audio_parts,axis=0)
            with wave.open(filename,"wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE)
                wav.writeframes(recorded_audio.tobytes())
            speech_queue.put(filename) #push to queue for main thread

def start_listening(speech_queue):
    global listener_thread
    stop_event.clear()
    listener_thread=threading.Thread(target=_listener_loop,args=(speech_queue,),daemon=True)
    listener_thread.start()

def stop_listening():
    stop_event.set()
    if listener_thread:
        listener_thread.join(timeout=3)