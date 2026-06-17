from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE,WHISPER_DEVICE,WHISPER_COMPUTE_TYPE,ALLOWED_LANGUAGES

import noisereduce
import soundfile

whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE) 

# def detect_language(filename):
#     #ALWAYS DEFAULTS TO ENGLISH
#     samplerate,audio_data=wavfile.read(filename)
#     audio_float=audio_data.astype(numpy.float32)/32768.0  # int16 -> float32 normalized #debug by claude
#     _,_,probabilities=whisper_model.detect_language(audio_float)
#     highest_probability=-1
#     detected_language="en"
#     for language,probability in probabilities:
#         if (language=="en" or language=="ur") and probability>highest_probability:
#             highest_probability=probability
#             detected_language=language
            
#     # print(f"en prob: {dict(probabilities).get('en',0):.4f}")
#     # print(f"ur prob: {dict(probabilities).get('ur',0):.4f}")
#     # print("detected:",detected_language)
#     return detected_language


# language_classifier=EncoderClassifier.from_hparams(
#     source="speechbrain/lang-id-voxlingua107-ecapa",
#     savedir="tmp"
# )
# def detect_language(filename):
#     signal=language_classifier.load_audio(filename)
#     prediction=language_classifier.classify_batch(signal)
#     label=prediction[3][0]
#     language=label.split(":")[0].strip()
#     if language not in ["en","ur"]:
#         language="en"
#     print("detected language:",language)
#     return language

# def transcribe(filename,lang):
#     print("transcription in progress")
#     parts,_=whisper_model.transcribe(filename,language=lang)
#     for part in parts:
#         text="".join()
#         text=text.strip()
#     return text

def transcribe_and_detect(filename):
    
    data,rate=soundfile.read(filename)
    cleaned=noisereduce.reduce_noise(y=data,sr=rate,prop_decrease=0.5)
    soundfile.write(filename,cleaned,rate)
    
    print("transcription in progress")
    _,info=whisper_model.transcribe(filename,language=None) #only need info for language detection, don't iterate segments

    if info.language=="ur" and info.language_probability>0.3:
        language="ur"
    else:
        language="en"
    print("urdu probability:",info.language_probability if info.language=="ur" else 0.0)

    parts,_=whisper_model.transcribe(filename,language=language)
    text=""
    for part in parts:
        text=text+part.text+" "
    text=text.strip()
    print("detected language:",language)
    return text,language