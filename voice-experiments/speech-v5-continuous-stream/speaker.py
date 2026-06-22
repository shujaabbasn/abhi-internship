import subprocess
import soundfile
import sounddevice
import time
import webrtcvad
from config import PIPER_PATH,PIPER_VOICE_EN,PIPER_VOICE_UR,SAMPLE_RATE,VAD_AGGRESSIVENESS,FRAME_DURATION_MS

vad=webrtcvad.Vad(VAD_AGGRESSIVENESS)
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000)

def speak(text,language,output_wav):
    if language=="ur":
        voice=PIPER_VOICE_UR
    else:
        voice=PIPER_VOICE_EN
    subprocess.run([PIPER_PATH,"--model",voice,"--output_file",output_wav],input=text,text=True,check=True)
    data,samplerate=soundfile.read(output_wav)
    interrupt_audio=[]
    interrupted=False

    sounddevice.play(data,samplerate)
    time.sleep(0.5) #small delay so it doesnt pick up its own first audio
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
            if consecutive_speech>=10: #10 consecutive speech frames to confirm interruption
                interrupted=True
                sounddevice.stop()
                print("interrupted")
                break
        else:
            consecutive_speech=0

    if interrupted==False:
        sounddevice.wait()
        return False,[]
    return True,interrupt_audio