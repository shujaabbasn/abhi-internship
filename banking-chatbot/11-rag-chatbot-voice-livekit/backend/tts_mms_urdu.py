import os
import tempfile
import threading

MODELS_DIR=os.path.join(os.path.dirname(__file__),"models")
MMS_URDU_DIR=os.path.join(MODELS_DIR,"mms-tts-urd")

_mms_urdu_state={"model":None,"tokenizer":None}
_mms_lock=threading.Lock()

def synthesize_mms_urdu(text,speed):
    import torch
    import torchaudio
    from transformers import VitsModel,AutoTokenizer

    if _mms_urdu_state["model"] is None:
        with _mms_lock:
            if _mms_urdu_state["model"] is None:
                _mms_urdu_state["model"]=VitsModel.from_pretrained(MMS_URDU_DIR)
                _mms_urdu_state["tokenizer"]=AutoTokenizer.from_pretrained(MMS_URDU_DIR)

    model=_mms_urdu_state["model"]
    tokenizer=_mms_urdu_state["tokenizer"]
    model.speaking_rate=speed

    inputs=tokenizer(text,return_tensors="pt")
    with torch.no_grad():
        output=model(**inputs).waveform

    wav=output.cpu()
    fd,output_wav=tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        torchaudio.save(output_wav,wav,model.config.sampling_rate)
        with open(output_wav,"rb") as file:
            return file.read()
    finally:
        os.remove(output_wav)
