import time
import os
import wave
import numpy
from transcription import transcribe_and_detect
from record import record_speech
from llm import query_llm,detect_intent
from speaker import speak
from config import SAMPLE_RATE

conversation_history=[]
interrupt_input_file=None
while True:
    timestamp=time.strftime("%d-%m-%Y_%H-%M-%S") #date month year hour min second
    input_file=f"input_{timestamp}.wav"
    output_file=f"response_{timestamp}.wav"

    if interrupt_input_file:
        #use buffered audio
        input_file=interrupt_input_file
        interrupt_input_file=None
    else:
        record_speech(input_file)

    text,language=transcribe_and_detect(input_file)
    os.remove(input_file)
    print("detected language: ",language)
    print("user said:",text)
    intent=detect_intent(text)
    print("detected intent: ",intent)

    # if not text.strip() or len(text.strip())<3:
    #     continue

    reply,conversation_history=query_llm(text,conversation_history)
    print("response:",reply)

    if reply:
        was_interrupted,interrupt_audio=speak(reply,language,output_file)
        # if os.path.exists(output_file):
        #     os.remove(output_file)
        if was_interrupted:
            if len(interrupt_audio)>0: #only save if ut got something
                timestamp=time.strftime("%d-%m-%Y_%H-%M-%S")
                interrupt_input_file=f"input_{timestamp}.wav"
                audio=numpy.concatenate(interrupt_audio,axis=0)
                with wave.open(interrupt_input_file,"wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(SAMPLE_RATE)
                    wav.writeframes(audio.tobytes())
            continue
        
#store audio in 16bit or 32 bit?
#reducing model paramters hurt performance even at 3b
#mps not usable for whisper
#picking up noise even at 3 vad aggressiveness
#using probabilities, urdu had very low probability each time and was thus not selected
#use speechbrain #ImportError: The 'pyparsing' package is required; normally this is bundled with this package so if you get this warning, consult the packager of your distribution. #tried insalling but kept getting importerror
#def transcribe_and_detect(filename): always gives eng

#hears it own audio and causes interruption: using headphones. maybe increase delay
#start of the interruption message gets cut



#noise cancellation implemented using noisereduce library, uses fourier transformation
#echo cancellation
#use a configurable context window done
#last 50 conversations done. done
#checking intent and storing context?, intent detection done