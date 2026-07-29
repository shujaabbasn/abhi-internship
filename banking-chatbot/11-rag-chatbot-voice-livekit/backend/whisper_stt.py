from faster_whisper import WhisperModel
from dotenv import load_dotenv
import os
import re
load_dotenv()

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
        #belt-and-suspenders check: even with vad_filter, whisper can still flag a
        #segment as likely non-speech itself via no_speech_prob - skip those too
        if part.no_speech_prob>NO_SPEECH_PROB_THRESHOLD:
            continue
        text_parts.append(part.text)
    text=" ".join(text_parts).strip()
    if _is_repetitive_hallucination(text):
        return ""
    return text

def _is_repetitive_hallucination(text):
    #on garbled/ambiguous audio whisper can get stuck repeating the same short
    #sentence many times in a row (e.g. "Good night." x13) instead of failing
    #cleanly - a distinct failure mode from silence hallucination, and one
    #no_speech_prob doesn't catch since each individual repeated segment can look
    #confident enough on its own
    sentences=[s.strip() for s in re.split(r"[.!?۔]+",text) if s.strip()]
    if sentences:
        counts={}
        for sentence in sentences:
            counts[sentence]=counts.get(sentence,0)+1
        if max(counts.values())>=REPEATED_SENTENCE_LIMIT:
            return True
    #a second, distinct hallucination pattern: whisper looping the same single word
    #with no punctuation at all (e.g. "اپنے اپنے اپنے ..." dozens of times) - the
    #sentence-level check above never sees this, since with no punctuation the
    #entire run is just one "sentence" that only ever appears once
    words=text.split()
    if words:
        word_counts={}
        for word in words:
            word_counts[word]=word_counts.get(word,0)+1
        if max(word_counts.values())>=REPEATED_WORD_LIMIT:
            return True
    return False

def transcribe_audio(file_path):
    model=get_whisper_model()
    #vad_filter skips silent/non-speech audio before it ever reaches the model -
    #without it, whisper hallucinates plausible-sounding filler text (e.g. "thank you",
    #"be careful") on silence or noise, instead of returning nothing
    #temperature=0.0 disables whisper's default 6-attempt retry cascade (it normally
    #retries at increasing randomness levels when a segment fails its own quality
    #checks) - on real-time audio that retrying is mostly wasted on silence/noise
    #segments anyway, and was adding several extra seconds of latency per turn
    parts,info=model.transcribe(file_path,language=None,vad_filter=True,temperature=0.0)
    text=_extract_text(parts)

    #language=None makes whisper score every language it knows, not just pick one -
    #we only ever want english or urdu, so compare just those two against each other
    #and ignore every other language it may have guessed (portuguese, norwegian, etc.
    #have shown up as false positives on short/noisy clips)
    language_probs=dict(info.all_language_probs) if info.all_language_probs else {}
    #whisper often mistakes urdu speech for hindi since they're the same spoken language
    #with different scripts, so a hindi guess counts as evidence for urdu here
    urdu_probability=language_probs.get("ur",0.0)+language_probs.get("hi",0.0)
    english_probability=language_probs.get("en",0.0)
    forced_language="ur" if urdu_probability>english_probability else "en"

    #only worth re-transcribing if the first pass already decoded in the exact
    #language we've settled on - "hi" doesn't count even when forced_language is "ur":
    #hindi and urdu sound identical but decode in different scripts (devanagari vs
    #arabic), so a "hi" first pass still needs a forced "ur" redo to get urdu script out
    already_correct=info.language==forced_language
    if not already_correct:
        parts,_=model.transcribe(file_path,language=forced_language,vad_filter=True,temperature=0.0)
        text=_extract_text(parts)

    return text,forced_language