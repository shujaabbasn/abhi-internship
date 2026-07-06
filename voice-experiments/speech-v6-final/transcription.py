from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE,WHISPER_DEVICE,WHISPER_COMPUTE_TYPE,ALLOWED_LANGUAGES

whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE) #loaded once at import, takes a few seconds, reused every turn

def transcribe_and_detect(filename):
    print("transcription in progress")
    parts,info=whisper_model.transcribe(filename,language=None) #language=None tells whisper to auto-detect. returns parts=text segments generator, info=metadata

    text_pieces=[] #whisper returns segments (sentence chunks), collect them all then join
    for s in parts:
        text_pieces.append(s.text)
    text=" ".join(text_pieces).strip()

    #info.language = which language whisper thinks it heard e.g. "en", "ur", "zh"
    #info.language_probability = confidence score 0.0-1.0 from whisper's internal language classifier (softmax over 99 languages)
    #whisper is trained mostly on english so urdu probability is always low even for clear urdu speech
    if info.language=="ur": #if whisper picked urdu, get its confidence score
        ur_prob=info.language_probability
    else:
        ur_prob=0.0 #if whisper picked anything else treat urdu prob as 0
    print("ur prob:",round(ur_prob,3))

    if ur_prob>0.3: #threshold intentionally low because whisper undershoots urdu confidence, even 0.3 usually means real urdu
        lang="ur"
        parts_ur,_=whisper_model.transcribe(filename,language="ur") #re-transcribe forced to urdu for better accuracy, auto-detect pass sometimes mixes scripts
        text_pieces_ur=[]
        for s in parts_ur:
            text_pieces_ur.append(s.text)
        text=" ".join(text_pieces_ur).strip()
    else:
        lang="en" #everything non-urdu defaults to english, auto-detect pass already gave good english text so no need to re-transcribe

    print("detected language:",lang)
    return text,lang
