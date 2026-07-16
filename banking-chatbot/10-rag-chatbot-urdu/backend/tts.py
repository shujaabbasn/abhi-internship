import subprocess
import tempfile
import os
import re
import io
import threading
from db import tts_settings_collection

PIPER_PATH="piper"
VOICES_DIR=os.path.join(os.path.dirname(__file__),"voices")
MODELS_DIR=os.path.join(os.path.dirname(__file__),"models")
XTTS_URDU_DIR=os.path.join(MODELS_DIR,"xtts-urdu")
ORPHEUS_URDU_DIR=os.path.join(MODELS_DIR,"orpheus-urdu")

PIPER_VOICES={
    "en":{"en_US-bryce-medium":"en_US-bryce-medium.onnx"},
    "ur":{"ur_PK-fasih-medium":"ur_PK-fasih-medium-model.onnx"}
}

SHERPA_VOICES={
    "en":{"vits-piper-en_US-bryce-medium":"vits-piper-en_US-bryce-medium"},
    "ur":{"vits-piper-ur_PK-fasih-medium":"vits-piper-ur_PK-fasih-medium"}
}

KOKORO_VOICES={
    "en":{
        "af_heart":"af_heart (Female - Heart)",
        "af_bella":"af_bella (Female - Bella)",
        "am_adam":"am_adam (Male - Adam)",
        "bf_emma":"bf_emma (Female - Emma)",
        "bm_george":"bm_george (Male - George)"
    }
}

COQUI_VOICES={
    "en":{
        "tts_models/en/ljspeech/tacotron2-DDC":"Tacotron2-DDC",
        "tts_models/en/ljspeech/glow-tts":"Glow-TTS",
        "tts_models/en/ljspeech/speedy-speech":"Speedy-Speech"
    }
}

XTTS_URDU_VOICES={
    "ur":{"xtts-urdu-cloned":"XTTS-v2 Urdu (fine-tuned, voice-cloned)"}
}

ORPHEUS_URDU_VOICES={
    "ur":{"orpheus-urdu":"Orpheus 3B Urdu (fine-tuned)"}
}

ENGINE_VOICES={
    "piper":PIPER_VOICES,
    "sherpa-onnx":SHERPA_VOICES,
    "kokoro":KOKORO_VOICES,
    "coqui":COQUI_VOICES,
    "xtts-urdu":XTTS_URDU_VOICES,
    "orpheus-urdu":ORPHEUS_URDU_VOICES
}

_xtts_urdu_state={"model":None,"gpt_cond_latent":None,"speaker_embedding":None}
_orpheus_urdu_state={"model":None,"tokenizer":None}
_snac_state={"model":None}
_sherpa_state={}
_kokoro_state={"model":None}
_coqui_state={}
_model_load_lock=threading.Lock()

def _resolve_voice_key(voices,voice_key):
    if voice_key in voices:
        return voice_key
    return list(voices.keys())[0]

def get_tts_settings():
    doc=tts_settings_collection.find_one({"_id":"default"})
    if doc is None:
        return {
            "engine_en":"piper","voice_en":"en_US-bryce-medium",
            "engine_ur":"piper","voice_ur":"ur_PK-fasih-medium",
            "speed":1.0
        }
    return doc

def save_tts_settings(engine_en,voice_en,engine_ur,voice_ur,speed):
    tts_settings_collection.update_one(
        {"_id":"default"},
        {"$set":{
            "engine_en":engine_en,"voice_en":voice_en,
            "engine_ur":engine_ur,"voice_ur":voice_ur,
            "speed":speed
        }},
        upsert=True
    )

def get_available_engines():
    engines=[]
    engines.append({"name":"piper","label":"Piper","languages":["en","ur"]})
    try:
        import sherpa_onnx
        engines.append({"name":"sherpa-onnx","label":"Sherpa-ONNX","languages":["en","ur"]})
    except ImportError:
        pass
    try:
        import kokoro_onnx
        engines.append({"name":"kokoro","label":"Kokoro","languages":["en"]})
    except ImportError:
        pass
    try:
        from TTS.api import TTS as CoquiTTS
        engines.append({"name":"coqui","label":"Coqui TTS","languages":["en"]})
    except ImportError:
        pass
    if os.path.isdir(XTTS_URDU_DIR):
        engines.append({"name":"xtts-urdu","label":"XTTS-v2 Urdu (fine-tuned)","languages":["ur"]})
    if os.path.isdir(ORPHEUS_URDU_DIR):
        engines.append({"name":"orpheus-urdu","label":"Orpheus 3B Urdu (fine-tuned)","languages":["ur"]})
    return engines

def get_voices_for_engine(engine_name):
    return ENGINE_VOICES.get(engine_name,{})

def space_out_long_digit_runs(text):
    return re.sub(r"\d{9,}",lambda match:" ".join(match.group()),text)

URDU_ONES={
    0:"صفر",1:"ایک",2:"دو",3:"تین",4:"چار",5:"پانچ",6:"چھ",7:"سات",8:"آٹھ",9:"نو",
    10:"دس",11:"گیارہ",12:"بارہ",13:"تیرہ",14:"چودہ",15:"پندرہ",16:"سولہ",17:"سترہ",18:"اٹھارہ",19:"انیس",
    20:"بیس",21:"اکیس",22:"بائیس",23:"تئیس",24:"چوبیس",25:"پچیس",26:"چھبیس",27:"ستائیس",28:"اٹھائیس",29:"انتیس",
    30:"تیس",31:"اکتیس",32:"بتیس",33:"تینتیس",34:"چونتیس",35:"پینتیس",36:"چھتیس",37:"سینتیس",38:"اڑتیس",39:"انتالیس",
    40:"چالیس",41:"اکتالیس",42:"بیالیس",43:"تینتالیس",44:"چوالیس",45:"پینتالیس",46:"چھیالیس",47:"سینتالیس",48:"اڑتالیس",49:"انچاس",
    50:"پچاس",51:"اکاون",52:"باون",53:"تریپن",54:"چون",55:"پچپن",56:"چھپن",57:"ستاون",58:"اٹھاون",59:"انسٹھ",
    60:"ساٹھ",61:"اکسٹھ",62:"باسٹھ",63:"تریسٹھ",64:"چونسٹھ",65:"پینسٹھ",66:"چھیاسٹھ",67:"سڑسٹھ",68:"اڑسٹھ",69:"انہتر",
    70:"ستر",71:"اکہتر",72:"بہتر",73:"تہتر",74:"چوہتر",75:"پچھتر",76:"چھہتر",77:"ستتر",78:"اٹھہتر",79:"اناسی",
    80:"اسی",81:"اکیاسی",82:"بیاسی",83:"تراسی",84:"چوراسی",85:"پچاسی",86:"چھیاسی",87:"ستاسی",88:"اٹھاسی",89:"نواسی",
    90:"نوے",91:"اکانوے",92:"بانوے",93:"ترانوے",94:"چورانوے",95:"پچانوے",96:"چھیانوے",97:"ستانوے",98:"اٹھانوے",99:"ننانوے"
}

def _urdu_two_digits(n):
    return URDU_ONES[n]

def _urdu_below_thousand(n):
    if n==0:
        return ""
    if n<100:
        return _urdu_two_digits(n)
    hundreds=n//100
    rest=n%100
    words=_urdu_two_digits(hundreds)+" سو"
    if rest>0:
        words=words+" "+_urdu_two_digits(rest)
    return words

def number_to_urdu_words(n):
    n=int(n)
    if n==0:
        return URDU_ONES[0]
    if n<0:
        return "منفی "+number_to_urdu_words(-n)
    crore=n//10000000
    n=n%10000000
    lakh=n//100000
    n=n%100000
    thousand=n//1000
    n=n%1000
    rest=n

    parts=[]
    if crore>0:
        parts.append(_urdu_below_thousand(crore)+" کروڑ")
    if lakh>0:
        parts.append(_urdu_below_thousand(lakh)+" لاکھ")
    if thousand>0:
        parts.append(_urdu_below_thousand(thousand)+" ہزار")
    if rest>0:
        parts.append(_urdu_below_thousand(rest))
    return " ".join(parts)

def convert_numbers_to_urdu_words(text):
    def replace(match):
        int_part=match.group(1)
        decimal_part=match.group(2)
        if len(int_part)>=9:
            spoken=" ".join(int_part)
        else:
            spoken=number_to_urdu_words(int_part)
        if decimal_part and decimal_part.strip("0")!="":
            decimal_digits=" ".join(URDU_ONES[int(d)] for d in decimal_part)
            spoken=spoken+" اعشاریہ "+decimal_digits
        return spoken
    return re.sub(r"(\d+)(?:\.(\d+))?",replace,text)

def synthesize_piper(text,voice_file,speed):
    model_path=os.path.join(VOICES_DIR,voice_file)
    fd,output_wav=tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        cmd=[PIPER_PATH,"--model",model_path,"--output_file",output_wav]
        if speed!=1.0:
            cmd.extend(["--length-scale",str(1.0/speed)])
        subprocess.run(cmd,input=text,text=True,check=True)
        with open(output_wav,"rb") as file:
            return file.read()
    finally:
        os.remove(output_wav)

def synthesize_sherpa(text,voice_name,speed):
    import sherpa_onnx
    import wave
    import numpy as np
    import glob

    if voice_name not in _sherpa_state:
        with _model_load_lock:
            if voice_name not in _sherpa_state:
                voice_dir=os.path.join(VOICES_DIR,voice_name)
                onnx_matches=glob.glob(os.path.join(voice_dir,"*.onnx"))
                if not onnx_matches:
                    raise FileNotFoundError("No .onnx model found in "+voice_dir)
                model_path=onnx_matches[0]
                tokens_path=os.path.join(voice_dir,"tokens.txt")
                data_dir=os.path.join(voice_dir,"espeak-ng-data")
                config=sherpa_onnx.OfflineTtsConfig(
                    model=sherpa_onnx.OfflineTtsModelConfig(
                        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                            model=model_path,
                            tokens=tokens_path,
                            data_dir=data_dir
                        )
                    )
                )
                _sherpa_state[voice_name]=sherpa_onnx.OfflineTts(config)

    tts=_sherpa_state[voice_name]
    audio=tts.generate(text,speed=speed)
    buf=io.BytesIO()
    with wave.open(buf,"wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(audio.sample_rate)
        samples=np.array(audio.samples)
        samples=(samples*32767).astype(np.int16)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()

def synthesize_kokoro(text,voice_name,speed):
    import soundfile as sf

    if _kokoro_state["model"] is None:
        with _model_load_lock:
            if _kokoro_state["model"] is None:
                from kokoro_onnx import Kokoro
                _kokoro_state["model"]=Kokoro("kokoro-v1.0.onnx","voices-v1.0.bin")

    kokoro=_kokoro_state["model"]
    samples,sample_rate=kokoro.create(text,voice=voice_name,speed=speed)
    buf=io.BytesIO()
    sf.write(buf,samples,sample_rate,format="WAV")
    buf.seek(0)
    return buf.read()

def synthesize_coqui(text,model_name,speed):
    import soundfile as sf

    if model_name not in _coqui_state:
        with _model_load_lock:
            if model_name not in _coqui_state:
                from TTS.api import TTS as CoquiTTS
                _coqui_state[model_name]=CoquiTTS(model_name=model_name,progress_bar=False)

    tts=_coqui_state[model_name]
    samples=tts.tts(text=text,speed=speed)
    buf=io.BytesIO()
    sf.write(buf,samples,tts.synthesizer.output_sample_rate,format="WAV")
    buf.seek(0)
    return buf.read()

def synthesize_xtts_urdu(text,speed):
    import torch
    import torchaudio
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts

    if _xtts_urdu_state["model"] is None:
        with _model_load_lock:
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
                gpt_cond_latent,speaker_embedding=model.get_conditioning_latents(
                    audio_path=[os.path.join(XTTS_URDU_DIR,"reference","source_voice.wav")],
                    gpt_cond_len=model.config.gpt_cond_len,
                    max_ref_length=model.config.max_ref_len,
                    sound_norm_refs=model.config.sound_norm_refs
                )
                _xtts_urdu_state["model"]=model
                _xtts_urdu_state["gpt_cond_latent"]=gpt_cond_latent
                _xtts_urdu_state["speaker_embedding"]=speaker_embedding

    model=_xtts_urdu_state["model"]
    out=model.inference(
        text=text,
        language="ur",
        gpt_cond_latent=_xtts_urdu_state["gpt_cond_latent"],
        speaker_embedding=_xtts_urdu_state["speaker_embedding"],
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

def _snac_convert_to_audio(codes):
    import torch
    if _snac_state["model"] is None:
        with _model_load_lock:
            if _snac_state["model"] is None:
                from snac import SNAC
                _snac_state["model"]=SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval()
    snac_model=_snac_state["model"]

    num_frames=len(codes)//7
    codes=codes[:num_frames*7]
    codes_0=[]
    codes_1=[]
    codes_2=[]
    for j in range(num_frames):
        i=7*j
        codes_0.append(codes[i])
        codes_1.append(codes[i+1])
        codes_1.append(codes[i+4])
        codes_2.append(codes[i+2])
        codes_2.append(codes[i+3])
        codes_2.append(codes[i+5])
        codes_2.append(codes[i+6])

    code_tensors=[
        torch.tensor(codes_0,dtype=torch.int32).unsqueeze(0),
        torch.tensor(codes_1,dtype=torch.int32).unsqueeze(0),
        torch.tensor(codes_2,dtype=torch.int32).unsqueeze(0)
    ]
    with torch.inference_mode():
        audio_hat=snac_model.decode(code_tensors)
    return audio_hat

def synthesize_orpheus_urdu(text,speed):
    import torch
    import torchaudio
    from transformers import AutoTokenizer,AutoModelForCausalLM

    if _orpheus_urdu_state["model"] is None:
        with _model_load_lock:
            if _orpheus_urdu_state["model"] is None:
                tokenizer=AutoTokenizer.from_pretrained(ORPHEUS_URDU_DIR)
                model=AutoModelForCausalLM.from_pretrained(ORPHEUS_URDU_DIR,torch_dtype=torch.bfloat16,attn_implementation="sdpa")
                model.eval()
                _orpheus_urdu_state["model"]=model
                _orpheus_urdu_state["tokenizer"]=tokenizer

    model=_orpheus_urdu_state["model"]
    tokenizer=_orpheus_urdu_state["tokenizer"]
    device=model.device

    prompt_tokens=tokenizer(text,return_tensors="pt")
    start_token=torch.tensor([[128259]],dtype=torch.int64)
    end_tokens=torch.tensor([[128009,128260,128261,128257]],dtype=torch.int64)
    input_ids=torch.cat([start_token,prompt_tokens.input_ids,end_tokens],dim=1).to(device)
    attention_mask=torch.ones_like(input_ids)

    with torch.inference_mode():
        generated=model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=400,
            do_sample=True,
            temperature=0.6,
            top_p=0.8,
            repetition_penalty=1.3,
            eos_token_id=128258
        )

    new_ids=generated[0][input_ids.shape[1]:].tolist()
    codes=[]
    index=0
    for token_id in new_ids:
        token_string=tokenizer.decode([token_id])
        if "<custom_token_" not in token_string:
            continue
        try:
            number_str=token_string[token_string.rfind("<custom_token_")+14:].rstrip(">")
            code_value=int(number_str)-10-((index%7)*4096)
        except ValueError:
            continue
        if code_value>0:
            codes.append(code_value)
            index+=1

    if len(codes)<7:
        raise RuntimeError("Orpheus produced no usable audio tokens for this input.")

    audio_hat=_snac_convert_to_audio(codes)
    wav=audio_hat.squeeze(0).detach().cpu()
    fd,output_wav=tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        torchaudio.save(output_wav,wav,24000)
        with open(output_wav,"rb") as file:
            return file.read()
    finally:
        os.remove(output_wav)

def text_to_speech(text,language="en"):
    settings=get_tts_settings()
    speed=settings.get("speed",1.0)
    if language=="ur":
        spoken_text=convert_numbers_to_urdu_words(text)
    else:
        spoken_text=space_out_long_digit_runs(text)

    if language=="ur":
        engine=settings.get("engine_ur","piper")
        voice_key=settings.get("voice_ur","ur_PK-fasih-medium")
    else:
        engine=settings.get("engine_en","piper")
        voice_key=settings.get("voice_en","en_US-bryce-medium")

    voices=ENGINE_VOICES.get(engine,{}).get(language)
    if voices is None:
        engine="piper"
        voices=PIPER_VOICES.get(language,PIPER_VOICES["en"])

    if engine=="piper":
        voice_file=voices[_resolve_voice_key(voices,voice_key)]
        return synthesize_piper(spoken_text,voice_file,speed)

    if engine=="sherpa-onnx":
        voice_name=voices[_resolve_voice_key(voices,voice_key)]
        return synthesize_sherpa(spoken_text,voice_name,speed)

    if engine=="kokoro":
        voice_id=_resolve_voice_key(voices,voice_key)
        return synthesize_kokoro(spoken_text,voice_id,speed)

    if engine=="coqui":
        model_name=_resolve_voice_key(voices,voice_key)
        return synthesize_coqui(spoken_text,model_name,speed)

    if engine=="xtts-urdu":
        return synthesize_xtts_urdu(spoken_text,speed)

    if engine=="orpheus-urdu":
        return synthesize_orpheus_urdu(spoken_text,speed)

    raise ValueError("No synthesis path implemented for engine '"+engine+"'")