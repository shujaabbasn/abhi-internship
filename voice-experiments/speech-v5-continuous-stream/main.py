import queue
import time
import os
import wave
import numpy
from record import start_listening,stop_listening
from transcription import transcribe_and_detect
from llm import query_llm,detect_intent
from speaker import speak
from transliterate import arabic_to_roman,roman_to_arabic
from config import SAMPLE_RATE,QUEUE_TIMEOUT,USE_TRANSLITERATION

speech_queue=queue.Queue()
conversation_history=[]

print("starting voice assistant")
print("transliteration:",("ON (roman urdu pipeline)" if USE_TRANSLITERATION==True else "OFF (arabic script pipeline)"))
start_listening(speech_queue)

try:
    while True:
        try:
            input_file=speech_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            continue

        text,language=transcribe_and_detect(input_file)
        os.remove(input_file)
        print("detected language:",language)
        print("user said:",text)

        if not text.strip() or len(text.strip())<3:
            continue

        #transliterate arabic->roman before sending to llm (only for urdu)
        llm_input=text
        if USE_TRANSLITERATION==True and language=="ur":
            llm_input=arabic_to_roman(text)
            print("roman urdu input:",llm_input)

        intent=detect_intent(llm_input)
        print("detected intent:",intent)

        llm_start=time.time() #timing for benchmark
        reply,conversation_history=query_llm(llm_input,conversation_history)
        llm_time=time.time()-llm_start
        print(f"response ({llm_time:.2f}s):",reply)

        if reply:
            #transliterate roman->arabic before sending to tts (only for urdu)
            tts_input=reply
            if USE_TRANSLITERATION==True and language=="ur":
                tts_input=roman_to_arabic(reply)
                print("arabic script for tts:",tts_input)

            timestamp=time.strftime("%d-%m-%Y_%H-%M-%S")
            output_file=f"response_{timestamp}.wav"
            was_interrupted,interrupt_audio=speak(tts_input,language,output_file)

            if was_interrupted:
                if len(interrupt_audio)>0:
                    timestamp=time.strftime("%d-%m-%Y_%H-%M-%S")
                    interrupt_file=f"input_{timestamp}.wav"
                    audio=numpy.concatenate(interrupt_audio,axis=0)
                    with wave.open(interrupt_file,"wb") as wav:
                        wav.setnchannels(1)
                        wav.setsampwidth(2)
                        wav.setframerate(SAMPLE_RATE)
                        wav.writeframes(audio.tobytes())
                    speech_queue.put(interrupt_file)
                continue

except KeyboardInterrupt:
    print("\nshutting down")
    stop_listening()