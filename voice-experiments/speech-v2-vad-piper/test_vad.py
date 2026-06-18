import sounddevice
import numpy
import torch
from silero_vad import load_silero_vad

SAMPLE_RATE=16000
SILERO_CHUNK_SIZE=512

vad_model=load_silero_vad()
vad_model.reset_states()

print("speak now, showing probabilities...")
for i in range(100):
    chunk=sounddevice.rec(SILERO_CHUNK_SIZE,samplerate=SAMPLE_RATE,channels=1,dtype="int16")
    sounddevice.wait()
    float_chunk=chunk.flatten().astype(numpy.float32)/32768.0
    float_chunk=float_chunk*10 #boost gain
    float_chunk=numpy.clip(float_chunk,-1.0,1.0) #clip to valid range
    tensor=torch.from_numpy(float_chunk)
    prob=vad_model(tensor,SAMPLE_RATE).item()
    print(round(prob,3))