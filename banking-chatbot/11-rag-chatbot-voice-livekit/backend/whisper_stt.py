from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
from dotenv import load_dotenv
import os
import re
load_dotenv()

DOMAIN_WORDS_EN=[
    "account","balance","amount","currency","exchange","transfer","send","recipient",
    "weather","loan","bank","branch","dollar","rupee","PKR","USD","city","convert","number"
]

_DOMAIN_WORDS_LOWER={w.lower() for w in DOMAIN_WORDS_EN}

WHISPER_MODEL_SIZE=os.environ["WHISPER_MODEL_SIZE"]
WHISPER_DEVICE=os.environ["WHISPER_DEVICE"]
WHISPER_COMPUTE_TYPE=os.environ["WHISPER_COMPUTE_TYPE"]
NO_SPEECH_PROB_THRESHOLD=0.6
REPEATED_SENTENCE_LIMIT=3
REPEATED_WORD_LIMIT=5

whisper_model=None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model=WhisperModel(WHISPER_MODEL_SIZE,device=WHISPER_DEVICE,compute_type=WHISPER_COMPUTE_TYPE)
    return whisper_model

def _extract_text(parts):
    text_parts=[]
    for part in parts:
        if part.no_speech_prob>NO_SPEECH_PROB_THRESHOLD:
            continue
        text_parts.append(part.text)
    text=" ".join(text_parts).strip()
    if _is_repetitive_hallucination(text):
        return ""
    return text

def _is_repetitive_hallucination(text):
    sentences=[s.strip() for s in re.split(r"[.!?۔]+",text) if s.strip()]
    if sentences:
        counts={}
        for sentence in sentences:
            counts[sentence]=counts.get(sentence,0)+1
        if max(counts.values())>=REPEATED_SENTENCE_LIMIT:
            return True
    words=text.split()
    if words:
        word_counts={}
        for word in words:
            word_counts[word]=word_counts.get(word,0)+1
        if max(word_counts.values())>=REPEATED_WORD_LIMIT:
            return True
    return False

def _transcribe_forced(model,file_path,language):
    parts,_=model.transcribe(file_path,language=language,vad_filter=True,temperature=0.0)
    parts=list(parts)
    text=_extract_text(parts)
    if parts:
        avg_logprob=sum(p.avg_logprob for p in parts)/len(parts)
    else:
        avg_logprob=-999.0
    return text,avg_logprob

def transcribe_audio(file_path):
    model=get_whisper_model()
    #detect_language needs a decoded audio array, not a file path - unlike transcribe(),
    #which decodes internally. this is the exact bug that crashed every /transcribe call.
    audio=decode_audio(file_path)
    detected_language,_,all_probs=model.detect_language(audio,vad_filter=True)
    probs=dict(all_probs) if all_probs else {}
    urdu_probability=probs.get("ur",0.0)+probs.get("hi",0.0)
    english_probability=probs.get("en",0.0)
    CONFIDENCE_MARGIN=2.0
    #the margin check alone isn't enough - it only compares en vs ur to each other,
    #so if the model's actual top guess is some unrelated third language (e.g. "zh"
    #at 49% confidence, with en at just 14% and ur at under 1%), en still "wins" the
    #margin check despite the model not really thinking it's english either. requiring
    #the top overall guess to actually be en/ur/hi closes that gap - anything else
    #falls through to the dual forced-transcription comparison below instead
    confidently_urdu=detected_language in ("ur","hi") and urdu_probability>english_probability*CONFIDENCE_MARGIN
    confidently_english=detected_language=="en" and english_probability>urdu_probability*CONFIDENCE_MARGIN

    if confidently_urdu:
        text,_=_transcribe_forced(model,file_path,"ur")
        return text,"ur"

    if confidently_english:
        text,_=_transcribe_forced(model,file_path,"en")
        en_words=re.findall(r"[A-Za-z']+",text)
        non_domain_en_words=[w for w in en_words if w.lower() not in _DOMAIN_WORDS_LOWER]
        if en_words and not non_domain_en_words:
            ur_text,_=_transcribe_forced(model,file_path,"ur")
            return ur_text,"ur"
        return text,"en"
    en_text,en_score=_transcribe_forced(model,file_path,"en")
    ur_text,ur_score=_transcribe_forced(model,file_path,"ur")

    if not en_text and not ur_text:
        return "","en"
    #one side got filtered out (hallucination). only trust the other side's text if
    #it wasn't actually the WEAKER attempt - a hallucination that scored more
    #confident than a real transcription means the whole utterance was unclear,
    #and the surviving text is likely just as wrong, just not repetitive enough
    #to have been caught (e.g. "بہت بہت بہت..." filtered at -0.09, while "It's not
    #as good as you think." survived unfiltered at a worse -0.96 - the filtered
    #side was actually the more confident one)
    if not en_text:
        if en_score>ur_score:
            return "","en"
        return ur_text,"ur"
    if not ur_text:
        if ur_score>en_score:
            return "","en"
        return en_text,"en"

    en_words=re.findall(r"[A-Za-z']+",en_text)
    non_domain_en_words=[w for w in en_words if w.lower() not in _DOMAIN_WORDS_LOWER]
    if en_words and not non_domain_en_words:
        return ur_text,"ur"

    if ur_score>=en_score:
        return ur_text,"ur"
    return en_text,"en"