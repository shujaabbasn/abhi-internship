import wave
import numpy
import sounddevice
import webrtcvad

from config import SAMPLE_RATE, VAD_AGGRESSIVENESS, FRAME_DURATION_MS, SILENCE_DURATION_MS

vad=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000) #samples per VAD frame
SILENCE_FRAMES_LIMIT=SILENCE_DURATION_MS//FRAME_DURATION_MS #consecutive silent frames = turn done

def record_until_silence(filename):
    print("listening")

    audio_parts=[]
    frame_buffer=numpy.array([],dtype=numpy.int16)
    speech_started=False
    silence_count=0
    done=False

    def mic_callback(indata,__,_,status): #to accumulate parts of audio + run VAD
        nonlocal frame_buffer,speech_started,silence_count,done
        if status:
            print(status)

        audio_parts.append(indata.copy())
        frame_buffer=numpy.concatenate([frame_buffer,indata.flatten()])

        while len(frame_buffer)>=FRAME_SIZE:
            frame=frame_buffer[:FRAME_SIZE]
            frame_buffer=frame_buffer[FRAME_SIZE:]

            is_speech=vad.is_speech(frame.tobytes(),SAMPLE_RATE)

            if is_speech:
                speech_started=True
                silence_count=0
            elif speech_started:
                silence_count+=1
                if silence_count>=SILENCE_FRAMES_LIMIT:
                    done=True

    with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=mic_callback): #mono channel, 16b audiodepth
        while not done:
            sounddevice.sleep(50)

    print("recording stopped")
    recorded_audio=numpy.concatenate(audio_parts,axis=0) #vector

    with wave.open(filename,"wb") as wave_file:
        wave_file.setnchannels(1)
        wave_file.setsampwidth(2) #bitdepth to match input
        wave_file.setframerate(SAMPLE_RATE) #set samplerate
        wave_file.writeframes(recorded_audio.tobytes()) #array to bytes

    return recorded_audio
