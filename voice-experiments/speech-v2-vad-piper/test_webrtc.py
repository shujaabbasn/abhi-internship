import sounddevice
import numpy
import webrtcvad

SAMPLE_RATE=16000
FRAME_DURATION_MS=20
FRAME_SIZE=int(SAMPLE_RATE*FRAME_DURATION_MS/1000)
VAD_AGGRESSIVENESS=3

vad=webrtcvad.Vad(VAD_AGGRESSIVENESS)

print("speak now...")
for i in range(200):
    chunk=sounddevice.rec(FRAME_SIZE,samplerate=SAMPLE_RATE,channels=1,dtype="int16")
    sounddevice.wait()
    frame=chunk.flatten()
    result=vad.is_speech(frame.tobytes(),SAMPLE_RATE)
    if result:
        print("SPEECH")
    else:
        print("silence")