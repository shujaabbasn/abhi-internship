import numpy

import wave
import requests
import sounddevice
import soundfile
import subprocess #added
import os
from faster_whisper import WhisperModel #openai's whisper: has language identification

SAMPLE_RATE=16000 #16k industry standard, will try others
#whisper_model=WhisperModel("medium","cpu","int8") #size,device,quantization
whisper_model=WhisperModel("medium",device="cpu",compute_type="int8")
OLLAMA_MODEL="qwen2.5:7b"

#PROMPTS: #will try multiple

SAMPLE_PROMPT = (
    "You are a helpful voice assistant. Users may speak to you in English, Urdu, "
    "or a mix of both in the same sentence. "
    "Listen to their intent, but you MUST reply in strictly ONE language. "
    "If their dominant language is Urdu, reply entirely in native Urdu script. "
    "If their dominant language is English, reply entirely in English. "
    "Never mix languages in your response. Do NOT use any markdown formatting, "
    "asterisks, bolding or special symbols in your text."
)

# SAMPLE_PROMPT = (
#     "You are a helpful voice assistant. Always reply in the same language "
#     "the user spoke in (English or Urdu). Keep replies short and conversational. "
#     "Do NOT use any markdown formatting, asterisks, bolding or special symbols in your text."
# )


# SAMPLE_PROMPT_2 = (
#     "You are a helpful, friendly voice assistant. You must respond entirely in the "
#     "same language as the user's input (if they speak Urdu, reply in Urdu script. "
#     "if they speak English, reply in English). Your response will be read aloud, so "
#     "keep it fluid, natural, and under 3-4 sentences. Avoid symbols or complex punctuation."
#     "Do NOT use any markdown formatting, asterisks, bolding or special symbols in your text."
# )

PIPER_PATH="piper"
VOICE_MAP={
    "en":"./voices/en_US-bryce-medium.onnx", 
    "ur":"./voices/ur_PK-fasih-medium-model.onnx"
}

#AUDIO RECORDING
input("press enter to start recording")
print("press enter again to stop recording")

audio_parts=[]

def mic_callback(indata,__,_,status): #to accumulate parts of audio
    if status==True:
        print(status)
    audio_parts.append(indata.copy())

with sounddevice.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype="int16",callback=mic_callback): #mono channel, 16b audiodepth
    input() #to stop execution

print("recording stopped")
recorded_audio=numpy.concatenate(audio_parts,axis=0) #vector

INPUT_FILENAME="input.wav" #save in wav type file
with wave.open(INPUT_FILENAME,"wb") as wave_file:
    wave_file.setnchannels(1)
    wave_file.setsampwidth(2) #bitdept to match input
    wave_file.setframerate(SAMPLE_RATE) #set samplerate
    wave_file.writeframes(recorded_audio.tobytes()) #array to bytes
    
#TRANSCRIPTION
print("local transcription in progress")
parts,info=whisper_model.transcribe(INPUT_FILENAME,language=None) #None so it autodetects
text_pieces=[]
for part in parts: #adding each string to list
    piece=part.text
    text_pieces.append(piece)
user_text=" ".join(text_pieces) #joining all strings with space in between
user_text=user_text.strip() #removing whitespace

#LLM
detected_language=info.language #en or ur
print("language detected: ",detected_language)
print("user said:",user_text)
OLLAMA_URL="http://localhost:11434/api/chat" #ollama binds to 127.0.0.1:11434
qwen_data={
    "model":OLLAMA_MODEL,
    "messages":
    [
        {"role":"system","content":SAMPLE_PROMPT},
        {"role": "user","content":user_text}
    ],
    "stream":False,
    "options":
    {
        "temperature":0.3, #lower or higher?
        "num_predict":100 #what should be limit?
    }
}
try:
    response=requests.post(OLLAMA_URL,json=qwen_data)
    response.raise_for_status()
    llm_reply=response.json()["message"]["content"]
    print(llm_reply)

except Exception:
    print("Error")
    llm_reply=""

def speak(text,language):
    #default to English if the language isn't in our map
    model_file=VOICE_MAP.get(language,VOICE_MAP["en"])
    output_wav="response.wav"
    #reads text and outputs audio
    subprocess.run([PIPER_PATH,"--model",model_file,"--output_file", output_wav],input=text,text=True,check=True)
    #Play the resulting audio file
    data,samplerate=soundfile.read(output_wav)
    sounddevice.play(data,samplerate)
    sounddevice.wait()

if llm_reply:
    print("speaking")
    speak(llm_reply,detected_language)
    
    #all parameters should be configurable
    #continuous speaking instead of turn based
    #speak interruption
    #if interrupted, - halt, keep previous as context and listen
    #modular with multiple files
    # for each output file, add a timestamp so new generated each time