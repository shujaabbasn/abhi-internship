#test different piper tuning settings to find least robotic sound
#plays the same sentence with different noise/speed settings

import subprocess
import numpy
import sounddevice
import time

PIPER_PATH="piper"
PIPER_SAMPLE_RATE=22050
MODEL="./voices/ur_PK-fasih-medium-model.onnx"
TEXT="آپ کا اکاؤنٹ بیلنس پچاس ہزار روپے ہے"

def play_piper(text,model,length_scale,noise_scale,noise_w,label):
    print(f"\n  [{label}] length={length_scale} noise={noise_scale} noise_w={noise_w}")
    process=subprocess.run(
        [PIPER_PATH,"--model",model,"--output-raw",
         "--length-scale",str(length_scale),
         "--noise-scale",str(noise_scale),
         "--noise-w",str(noise_w)],
        input=text.encode("utf-8"),
        capture_output=True
    )
    if process.returncode!=0 or len(process.stdout)==0:
        print("  error")
        return
    raw_audio=numpy.frombuffer(process.stdout,dtype=numpy.int16)
    playback_data=raw_audio.astype(numpy.float32)/32768.0
    duration=len(playback_data)/PIPER_SAMPLE_RATE
    print(f"  playing ({duration:.1f}s)...")
    sounddevice.play(playback_data,PIPER_SAMPLE_RATE)
    sounddevice.wait()

print("="*60)
print("PIPER VOICE TUNING TEST")
print("="*60)
print(f"text: {TEXT}")
print(f"model: {MODEL}")

#default settings
play_piper(TEXT,MODEL,1.0,0.667,0.8,"A - default")
time.sleep(1)

#slower, more natural pace
play_piper(TEXT,MODEL,1.2,0.667,0.8,"B - slower pace")
time.sleep(1)

#more phoneme variation (less monotone)
play_piper(TEXT,MODEL,1.0,0.9,0.8,"C - more variation")
time.sleep(1)

#slower + more variation
play_piper(TEXT,MODEL,1.2,0.9,0.9,"D - slower + more variation")
time.sleep(1)

#even slower, max variation
play_piper(TEXT,MODEL,1.3,1.0,1.0,"E - slowest + max variation")
time.sleep(1)

#faster, crisp
play_piper(TEXT,MODEL,0.8,0.5,0.6,"F - faster, crisp")
time.sleep(1)

print()
print("="*60)
print("DONE - pick the letter that sounds best")
print("="*60)
print("then tell me which one and i'll update all_in_one.py")
