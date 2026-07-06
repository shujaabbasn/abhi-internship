import subprocess
import time
import soundfile
import sounddevice
import numpy
import webrtcvad

from config import PIPER_PATH, VOICE_MAP, SAMPLE_RATE, VAD_AGGRESSIVENESS, FRAME_DURATION_MS

vad=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000) #samples per VAD frame

def speak_interruptible(text, language, output_wav):
    #default to English if the language isn't in our map
    model_file=VOICE_MAP.get(language,VOICE_MAP["en"])
    #reads text and outputs audio
    subprocess.run([PIPER_PATH,"--model",model_file,"--output_file",output_wav],input=text,text=True,check=True)

    data,samplerate=soundfile.read(output_wav)
    duration=len(data)/samplerate

    frame_buffer=numpy.array([],dtype=numpy.int16)
    interrupted=False

    def mic_callback(indata,__,_,status): #listens for user speech WHILE response is playing
        nonlocal frame_buffer,interrupted
        if status:
            print(status)

        frame_buffer=numpy.concatenate([frame_buffer,indata.flatten()])

        while len(frame_buffer)>=FRAME_SIZE:
            frame=frame_buffer[:FRAME_SIZE]
            frame_buffer=frame_buffer[FRAME_SIZE:]
            if vad.is_speech(frame.tobytes(),SAMPLE_RATE):
                interrupted=True

    #Play the resulting audio file
    sounddevice.play(data,samplerate)

    with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=mic_callback): #mono channel, 16b audiodepth
        start_time=time.time()
        while time.time()-start_time<duration and not interrupted:
            sounddevice.sleep(50)

    if interrupted:
        sounddevice.stop()
        print("interrupted")
        return True

    sounddevice.wait()
    return False
