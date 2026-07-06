import numpy
from faster_whisper import WhisperModel #openai's whisper: has language identification

from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, ALLOWED_LANGUAGES

whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE)

def detect_language(recorded_audio):
    #LANGUAGE DETECTION (restricted to en/ur only)
    audio_float=recorded_audio.flatten().astype(numpy.float32)/32768.0 #int16 -> float32, normalized
    _,_,all_language_probs=whisper_model.detect_language(audio_float)

    best_prob=-1
    detected_language="en" #fallback if something goes very wrong
    for lang_code,prob in all_language_probs:
        if lang_code in ALLOWED_LANGUAGES and prob>best_prob:
            best_prob=prob
            detected_language=lang_code

    return detected_language

def transcribe(filename, language):
    #TRANSCRIPTION
    print("local transcription in progress")
    parts,info=whisper_model.transcribe(filename,language=language) #forced to en/ur
    text_pieces=[]
    for part in parts: #adding each string to list
        text_pieces.append(part.text)
    return " ".join(text_pieces).strip() #joining all strings, removing whitespace
