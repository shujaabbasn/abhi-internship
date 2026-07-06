import time
import os
import wave
import numpy
from transcription import transcribe_and_detect
from record import record_until_silence
from llm import query_llm
from speaker import speak
from config import SAMPLE_RATE

conversation_history=[] #persists across all turns, passed to llm every time so it sees full back and forth
interrupt_input_file=None #holds path to wav saved during interruption, used next loop instead of re-recording
while True:
    timestamp=time.strftime("%d-%m-%Y_%H-%M-%S") #unique timestamp per turn so files dont overwrite each other
    input_file=f"input_{timestamp}.wav"
    output_file=f"response_{timestamp}.wav"

    if interrupt_input_file: #user already spoke during last interruption, reuse that audio instead of waiting for new input
        input_file=interrupt_input_file
        interrupt_input_file=None #reset so the turn after uses normal recording
    else:
        record_until_silence(input_file) #normal turn, wait for user to speak then silence

    text,language=transcribe_and_detect(input_file)
    os.remove(input_file) #delete immediately, no point accumulating wav files on disk

    print("detected language: ",language)

    if not text.strip() or len(text.strip())<3: #skip if transcription returned nothing or just noise transcribed as 1-2 chars
        continue

    reply,conversation_history=query_llm(text,conversation_history) #send text + full history, get reply + updated history (now includes this turn)
    print("response:",reply)

    if reply:
        was_interrupted,interrupt_audio=speak(reply,language,output_file) #play response, mic is open the whole time listening for interruption
        if os.path.exists(output_file):
            os.remove(output_file) #delete response wav, os.path.exists check because if piper failed file might not exist
        if was_interrupted:
            if interrupt_audio: #only save if mic actually captured something after the 0.5s settle window
                timestamp=time.strftime("%d-%m-%Y_%H-%M-%S")
                interrupt_input_file=f"input_{timestamp}.wav"
                audio=numpy.concatenate(interrupt_audio,axis=0) #stitch mic chunks into one array
                with wave.open(interrupt_input_file,"wb") as wav: #write to wav so transcription.py can read it next loop
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(SAMPLE_RATE)
                    wav.writeframes(audio.tobytes())
            continue #jump back to top of loop, interrupt_input_file now set so recording is skipped
