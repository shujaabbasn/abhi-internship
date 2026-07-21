from faster_whisper import WhisperModel

WHISPER_MODEL_SIZE="medium"
WHISPER_DEVICE="cpu"
WHISPER_COMPUTE_TYPE="int8"
URDU_REDO_THRESHOLD=0.3

whisper_model=None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        print("Loading Whisper model... (this will download ~1.5GB the first time)")
        whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE)
    return whisper_model

def transcribe_audio(file_path):
    model=get_whisper_model()
    parts,info=model.transcribe(file_path,language=None)
    text=" ".join(part.text for part in parts).strip()

    #whisper often mistakes urdu speech for hindi since they are the same spoken language
    #with different scripts, so treat a hindi guess the same as an urdu guess here
    urdu_leaning_prob=info.language_probability if info.language in ("ur","hi") else 0.0
    if urdu_leaning_prob>URDU_REDO_THRESHOLD:
        parts_ur,_=model.transcribe(file_path,language="ur")
        text=" ".join(part.text for part in parts_ur).strip()

    return text
