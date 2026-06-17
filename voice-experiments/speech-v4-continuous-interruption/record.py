import wave
import numpy
import time
import sounddevice
import webrtcvad
from config import SAMPLE_RATE,VAD_AGGRESSIVENESS,FRAME_DURATION_MS,SILENCE_FRAMES_NEEDED

vad=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000)

CONSECUTIVE_SPEECH_FRAMES_NEEDED=8 #ai recommended 8x20ms=160ms for sustained speech
MAX_LISTEN_SECONDS=30

audio_parts=[]
frame_buffer=numpy.array([],dtype=numpy.int16)
speech_started=False
silence_count=0
speech_frame_count=0
done=False

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

def record_speech(filename):
    global audio_parts,frame_buffer,speech_started,silence_count,speech_frame_count,done
    audio_parts=[]
    frame_buffer=numpy.array([],dtype=numpy.int16)
    speech_started=False
    silence_count=0
    speech_frame_count=0
    done=False
    print("listening")
    start_time=time.time()
    with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=vad_callback):
        while done==False:
            sounddevice.sleep(50)
            if time.time()-start_time>=MAX_LISTEN_SECONDS:
                print(f"timeout after {MAX_LISTEN_SECONDS}s")
                break
    print("recording stopped")
    recorded_audio=numpy.concatenate(audio_parts,axis=0)
    with wave.open(filename,"wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(recorded_audio.tobytes())

# audio_parts=[]
# frame_buffer=numpy.array([],dtype=numpy.int16)
# speech_started=False
# silence_count=0
# done=False

# def vad_callback(indata,__,_,status):
#     global frame_buffer,speech_started,silence_count,done
#     if status:
#         print(status)
#     audio_parts.append(indata.copy())
#     frame_buffer=numpy.concatenate([frame_buffer,indata.flatten()])
#     while len(frame_buffer)>=FRAME_SIZE:
#         frame,frame_buffer=frame_buffer[0:FRAME_SIZE],frame_buffer[FRAME_SIZE:]
#         if vad.is_speech(frame.tobytes(),SAMPLE_RATE):
#             is_speech=True
#         else:
#             is_speech=False

#         if is_speech==True:
#             speech_started=True
#             silence_count=0
#         elif speech_started==True:
#             silence_count=silence_count+1
#             if silence_count>=SILENCE_FRAMES_NEEDED:
#                 done=True

# def record_until_silence(filename):
#     global audio_parts,frame_buffer,speech_started,silence_count,done
#     audio_parts=[]
#     frame_buffer=numpy.array([],dtype=numpy.int16)
#     speech_started=False
#     silence_count=0
#     done=False

#     print("listening")
#     with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=vad_callback):
#         while done==False:
#             sounddevice.sleep(50)
#     print("recording stopped")
#     recorded_audio=numpy.concatenate(audio_parts,axis=0)

#     with wave.open(filename,"wb") as wav:
#         wav.setnchannels(1)
#         wav.setsampwidth(2)
#         wav.setframerate(SAMPLE_RATE)
#         wav.writeframes(recorded_audio.tobytes())