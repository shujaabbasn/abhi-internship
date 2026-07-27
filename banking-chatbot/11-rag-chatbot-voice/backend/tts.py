import os
import re
from db import tts_settings_collection
from urdu_numbers import URDU_ONES
from tts_piper import synthesize_piper
from tts_sherpa import synthesize_sherpa
from tts_kokoro import synthesize_kokoro
from tts_xtts_urdu import synthesize_xtts_urdu,unload_xtts_urdu,XTTS_URDU_DIR
from tts_orpheus_urdu import synthesize_orpheus_urdu,unload_orpheus_urdu,ORPHEUS_URDU_DIR
from tts_mms_urdu import synthesize_mms_urdu,MMS_URDU_DIR
from tts_espeak import synthesize_espeak_urdu

PIPER_VOICES={
    "en":{"en_US-bryce-medium":"en_US-bryce-medium.onnx"},
    "ur":{
        "ur_PK-fasih-medium":"ur_PK-fasih-medium-model.onnx",
        "ur_PK-abhibank-finetune":"ur_PK-abhibank-finetune.onnx"
    }
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

XTTS_URDU_VOICES={
    "ur":{
        "xtts-urdu-cloned":"XTTS-v2 Urdu (fine-tuned, cloned reference)",
        "xtts-urdu-myvoice":"XTTS-v2 Urdu (fine-tuned, your voice)"
    }
}

ORPHEUS_URDU_VOICES={
    "ur":{"orpheus-urdu":"Orpheus 3B Urdu (fine-tuned)"}
}

MMS_URDU_VOICES={
    "ur":{"mms-urdu":"MMS-TTS Urdu (Meta, Arabic script)"}
}

ESPEAK_VOICES={
    "ur":{"espeak-urdu":"eSpeak-NG Urdu (formant synthesis)"}
}

ENGINE_VOICES={
    "piper":PIPER_VOICES,
    "sherpa-onnx":SHERPA_VOICES,
    "kokoro":KOKORO_VOICES,
    "xtts-urdu":XTTS_URDU_VOICES,
    "orpheus-urdu":ORPHEUS_URDU_VOICES,
    "mms-urdu":MMS_URDU_VOICES,
    "espeak-urdu":ESPEAK_VOICES
}

def _resolve_voice_key(voices,voice_key):
    if voice_key in voices:
        return voice_key
    return list(voices.keys())[0]

_tts_settings_cache=None

def get_tts_settings():
    global _tts_settings_cache
    if _tts_settings_cache is None:
        doc=tts_settings_collection.find_one({"_id":"default"})
        if doc is None:
            doc={
                "engine_en":"piper","voice_en":"en_US-bryce-medium",
                "engine_ur":"piper","voice_ur":"ur_PK-fasih-medium",
                "speed":1.0
            }
        _tts_settings_cache=doc
    return dict(_tts_settings_cache)

def save_tts_settings(engine_en,voice_en,engine_ur,voice_ur,speed):
    global _tts_settings_cache
    settings={
        "engine_en":engine_en,"voice_en":voice_en,
        "engine_ur":engine_ur,"voice_ur":voice_ur,
        "speed":speed
    }
    tts_settings_collection.update_one(
        {"_id":"default"},
        {"$set":settings},
        upsert=True
    )
    _tts_settings_cache={**settings,"_id":"default"}

def get_available_engines():
    import shutil
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
    if os.path.isdir(XTTS_URDU_DIR):
        engines.append({"name":"xtts-urdu","label":"XTTS-v2 Urdu (fine-tuned)","languages":["ur"]})
    if os.path.isdir(ORPHEUS_URDU_DIR):
        engines.append({"name":"orpheus-urdu","label":"Orpheus 3B Urdu (fine-tuned)","languages":["ur"]})
    if os.path.isdir(MMS_URDU_DIR):
        engines.append({"name":"mms-urdu","label":"MMS-TTS Urdu (Meta)","languages":["ur"]})
    if shutil.which("espeak-ng"):
        engines.append({"name":"espeak-urdu","label":"eSpeak-NG Urdu","languages":["ur"]})
    return engines

def get_voices_for_engine(engine_name):
    return ENGINE_VOICES.get(engine_name,{})

def space_out_long_digit_runs(text):
    return re.sub(r"\d{9,}",lambda match:" ".join(match.group()),text)

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

    if engine=="xtts-urdu":
        unload_orpheus_urdu()
        resolved_voice_key=_resolve_voice_key(voices,voice_key)
        return synthesize_xtts_urdu(spoken_text,resolved_voice_key,speed)

    if engine=="orpheus-urdu":
        unload_xtts_urdu()
        return synthesize_orpheus_urdu(spoken_text,speed)

    if engine=="mms-urdu":
        return synthesize_mms_urdu(spoken_text,speed)

    if engine=="espeak-urdu":
        return synthesize_espeak_urdu(spoken_text,speed)

    raise ValueError("No synthesis path implemented for engine '"+engine+"'")