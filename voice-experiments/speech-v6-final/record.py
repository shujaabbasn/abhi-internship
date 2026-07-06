import wave
import numpy
import sounddevice
import webrtcvad

from config import SAMPLE_RATE,VAD_AGGRESSIVENESS,FRAME_DURATION_MS,SILENCE_DURATION_MS

vad=webrtcvad.Vad(VAD_AGGRESSIVENESS) #created once at import, reused every recording session
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000) #16000*20/1000=320 samples per vad frame, vad needs exactly this many at a time
SILENCE_FRAMES_NEEDED=SILENCE_DURATION_MS//FRAME_DURATION_MS #1000/20=50 silent frames needed to end recording

#module level globals, reset at start of every record_until_silence() call
audio_parts=[] #accumulates raw audio chunks to stitch into wav at the end
frame_buffer=numpy.array([],dtype=numpy.int16) #holds leftover samples between callback calls until we have a full frame
speech_started=False #stays False until first speech detected, so leading silence is ignored
silence_count=0 #counts consecutive silent frames after speech started
done=False #set to True when silence threshold hit, exits the main wait loop

def vad_callback(indata,__,_,status): #sounddevice calls this automatically every ~20ms with new mic audio
    global frame_buffer,speech_started,silence_count,done
    if status:
        print(status)
    audio_parts.append(indata.copy()) #save copy of every chunk regardless of speech/silence, .copy() because indata is a shared buffer that gets overwritten
    frame_buffer=numpy.concatenate([frame_buffer,indata.flatten()]) #indata is 2d (samples x channels) so flatten to 1d before appending
    while len(frame_buffer)>=FRAME_SIZE: #process as many complete frames as possible, while handles cases where sounddevice gives more than one frame at once
        frame,frame_buffer=frame_buffer[0:FRAME_SIZE],frame_buffer[FRAME_SIZE:] #slice one frame off front, keep rest as leftover
        if vad.is_speech(frame.tobytes(),SAMPLE_RATE): #ask webrtc vad: is this 20ms chunk speech? .tobytes() converts numpy array to raw bytes the c library expects
            is_speech=True
        else:
            is_speech=False

        if is_speech==True:
            speech_started=True #mark that user has started talking
            silence_count=0 #reset silence counter on any speech
        elif speech_started==True: #only count silence after speech has begun, ignore leading silence
            silence_count=silence_count+1
            if silence_count>=SILENCE_FRAMES_NEEDED: #50 consecutive silent frames = 1 second of silence = user finished talking
                done=True

def record_until_silence(filename):
    global audio_parts,frame_buffer,speech_started,silence_count,done
    audio_parts=[] #reset all state for this new recording session
    frame_buffer=numpy.array([],dtype=numpy.int16)
    speech_started=False
    silence_count=0
    done=False

    print("listening")
    with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=vad_callback): #open mic, sounddevice calls vad_callback on background thread
        while done==False: #main thread just waits here, vad_callback does the work
            sounddevice.sleep(50) #check every 50ms, low cpu usage
    print("recording stopped")
    recorded_audio=numpy.concatenate(audio_parts,axis=0) #stitch all chunks into one continuous array along time axis

    with wave.open(filename,"wb") as wav:
        wav.setnchannels(1) #mono
        wav.setsampwidth(2) #2 bytes = 16bit, matches dtype="int16" from inputstream
        wav.setframerate(SAMPLE_RATE) #16000hz, whisper expects this
        wav.writeframes(recorded_audio.tobytes())
