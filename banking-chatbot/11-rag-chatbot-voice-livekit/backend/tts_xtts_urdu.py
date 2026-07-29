import os
import tempfile
import threading

MODELS_DIR=os.path.join(os.path.dirname(__file__),"models")
XTTS_URDU_DIR=os.path.join(MODELS_DIR,"xtts-urdu")
VOICE_REFERENCES_DIR=os.path.join(os.path.dirname(__file__),"voice_references")

REFERENCE_WAVS={
    "xtts-urdu-cloned":os.path.join(XTTS_URDU_DIR,"reference","source_voice.wav"),
    "xtts-urdu-myvoice":os.path.join(VOICE_REFERENCES_DIR,"my_voice.wav")
}

_xtts_urdu_state={"model":None,"config":None}
_xtts_conditioning_cache={}
_xtts_lock=threading.Lock()

def unload_xtts_urdu():
    #xtts (5.3GB) and orpheus (6.2GB) can't both fit in memory on a 16GB machine,
    #so whichever engine is switched away from gets evicted before the other loads
    import gc
    with _xtts_lock:
        _xtts_urdu_state["model"]=None
        _xtts_urdu_state["config"]=None
        _xtts_conditioning_cache.clear()
    gc.collect()

def synthesize_xtts_urdu(text,voice_key,speed):
    import torch
    import torchaudio
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts

    if _xtts_urdu_state["model"] is None:
        with _xtts_lock:
            if _xtts_urdu_state["model"] is None:
                device="cuda:0" if torch.cuda.is_available() else "cpu"
                config=XttsConfig()
                config.load_json(os.path.join(XTTS_URDU_DIR,"config.json"))
                model=Xtts.init_from_config(config)
                model.load_checkpoint(
                    config,
                    checkpoint_path=os.path.join(XTTS_URDU_DIR,"model.pth"),
                    vocab_path=os.path.join(XTTS_URDU_DIR,"vocab.json"),
                    use_deepspeed=False
                )
                model.to(device)
                _xtts_urdu_state["model"]=model
                _xtts_urdu_state["config"]=config

    model=_xtts_urdu_state["model"]
    config=_xtts_urdu_state["config"]

    if voice_key not in _xtts_conditioning_cache:
        with _xtts_lock:
            if voice_key not in _xtts_conditioning_cache:
                reference_wav=REFERENCE_WAVS.get(voice_key,REFERENCE_WAVS["xtts-urdu-cloned"])
                gpt_cond_latent,speaker_embedding=model.get_conditioning_latents(
                    audio_path=[reference_wav],
                    gpt_cond_len=config.gpt_cond_len,
                    max_ref_length=config.max_ref_len,
                    sound_norm_refs=config.sound_norm_refs
                )
                _xtts_conditioning_cache[voice_key]={
                    "gpt_cond_latent":gpt_cond_latent,
                    "speaker_embedding":speaker_embedding
                }

    conditioning=_xtts_conditioning_cache[voice_key]
    out=model.inference(
        text=text,
        language="ur",
        gpt_cond_latent=conditioning["gpt_cond_latent"],
        speaker_embedding=conditioning["speaker_embedding"],
        temperature=0.1,
        length_penalty=0.1,
        repetition_penalty=10.0,
        top_k=10,
        top_p=0.3,
        speed=speed
    )
    wav=torch.tensor(out["wav"]).unsqueeze(0)
    fd,output_wav=tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        torchaudio.save(output_wav,wav,24000)
        with open(output_wav,"rb") as file:
            return file.read()
    finally:
        os.remove(output_wav)