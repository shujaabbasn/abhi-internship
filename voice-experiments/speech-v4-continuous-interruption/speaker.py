import subprocess
import soundfile
import sounddevice
import numpy
# import torch
# from silero_vad import load_silero_vad
# from config import PIPER_PATH,PIPER_VOICE_EN,PIPER_VOICE_UR,SAMPLE_RATE,VAD_THRESHOLD,SILERO_CHUNK_SIZE
import time
import webrtcvad
from config import PIPER_PATH,PIPER_VOICE_EN,PIPER_VOICE_UR,SAMPLE_RATE,VAD_AGGRESSIVENESS,FRAME_DURATION_MS


# DEVICE="cpu"
 
# vad_model=load_silero_vad()
# vad_model=vad_model.to(DEVICE)

vad=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000)

def speak(text,language,output_wav):
    if language=="ur":
        voice=PIPER_VOICE_UR
    else:
        voice=PIPER_VOICE_EN
    subprocess.run([PIPER_PATH,"--model",voice,"--output_file",output_wav],input=text,text=True,check=True)
    data,samplerate=soundfile.read(output_wav)
    interrupt_audio=[] #will hold mic chunks captured during playback
    interrupted=False
 
    sounddevice.play(data,samplerate) #start playback
    time.sleep(0.5)
    duration=len(data)/samplerate
    start_time=time.time()
    consecutive_speech=0
    while time.time()-start_time<duration:
        chunk=sounddevice.rec(FRAME_SIZE,samplerate=SAMPLE_RATE,channels=1,dtype="int16")
        sounddevice.wait()
        interrupt_audio.append(chunk.copy())
        frame=chunk.flatten()
        if vad.is_speech(frame.tobytes(),SAMPLE_RATE):
            consecutive_speech=consecutive_speech+1
            if consecutive_speech>=10:
                interrupted=True
                sounddevice.stop()
                print("interrupted")
                break
        else:
            consecutive_speech=0
 
    if interrupted==False:
        sounddevice.wait() #waiting for playback to finish
        return False,[]
    return True,interrupt_audio
 


# def interruption_callback(indata,__,_,status):
#     global frame_buffer,interrupted
#     if status==True:
#         print(status)
#     interrupt_audio.append(indata.copy()) #always buffer
#     frame_buffer=numpy.concatenate([frame_buffer,indata.flatten()])
#     while len(frame_buffer)>=FRAME_SIZE:
#         frame,frame_buffer=frame_buffer[0:FRAME_SIZE],frame_buffer[FRAME_SIZE:]
#         if vad.is_speech(frame.tobytes(),SAMPLE_RATE):
#             interrupted=True

# def speak(text,language,output_wav):
#     global frame_buffer,interrupted,interrupt_audio
#     frame_buffer=numpy.array([],dtype=numpy.int16)
#     interrupted=False
#     interrupt_audio=[]
#     model_file=VOICE_MAP.get(language,VOICE_MAP["en"])
#     subprocess.run([PIPER_PATH,"--model",model_file,"--output_file",output_wav],input=text,text=True,check=True)
#     data,samplerate=soundfile.read(output_wav)
#     duration=len(data)/samplerate
#     with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=interruption_callback):
#         sounddevice.play(data,samplerate)
#         frame_buffer=numpy.array([],dtype=numpy.int16) #discard noise from frame buffer only
#         interrupt_audio=[] #discard buffered noise, start fresh from here
#         start_time=time.time()
#         while time.time()-start_time<duration and not interrupted:
#             sounddevice.sleep(50)
#     if interrupted:
#         sounddevice.stop()
#         print("interrupted")
#         return True,interrupt_audio
#     sounddevice.wait()
#     return False,[]