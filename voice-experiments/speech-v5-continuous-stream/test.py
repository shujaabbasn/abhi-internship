#single turn test to verify each component works individually
import queue
import time
import os
import wave
import numpy
from record import start_listening,stop_listening
from transcription import transcribe_and_detect
from llm import query_llm
from speaker import speak
from config import SAMPLE_RATE

speech_queue=queue.Queue()

print("starting single turn test")
print("speak something, it will record one utterance and respond")

start_listening(speech_queue)

#wait for one utterance
input_file=speech_queue.get() #blocks until speech is detected and saved
stop_listening() #stop mic after getting one utterance
print("got recording:",input_file)
text,language=transcribe_and_detect(input_file)
os.remove(input_file)
print("detected language:",language)
print("user said:",text)

if text.strip():
    reply,_=query_llm(text,[])
    print("response:",reply)
    if reply:
        timestamp=time.strftime("%d-%m-%Y_%H-%M-%S")
        output_file=f"response_{timestamp}.wav"
        speak(reply,language,output_file)
else:
    print("no speech detected")

print("test done")