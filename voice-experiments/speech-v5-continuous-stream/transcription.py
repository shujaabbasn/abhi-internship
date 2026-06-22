from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE,WHISPER_DEVICE,WHISPER_COMPUTE_TYPE
import noisereduce
import soundfile

whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE)

def transcribe_and_detect(filename):
    data,rate=soundfile.read(filename)
    cleaned=noisereduce.reduce_noise(y=data,sr=rate,prop_decrease=0.5)
    soundfile.write(filename,cleaned,rate)

    print("transcription in progress")
    _,info=whisper_model.transcribe(filename,language=None) #first pass: detect language

    if info.language=="ur" and info.language_probability>0.3:
        language="ur"
    else:
        language="en"
    print("urdu probability:",info.language_probability if info.language=="ur" else 0.0)

    parts,_=whisper_model.transcribe(filename,language=language) #second pass: transcribe with detected language
    text=""
    for part in parts:
        text=text+part.text+" "
    text=text.strip()
    print("detected language:",language)
    return text,language