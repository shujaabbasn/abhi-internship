import time
from recorder import record_until_silence
from transcriber import detect_language, transcribe
from llm_client import query_llm
from speaker import speak_interruptible

conversation_history=[]
print("voice assistant ready - press Ctrl+C to quit")

while True:
    t=time.strftime("%Y%m%d_%H%M%S")

    record_until_silence(f"input_{t}.wav")

    lang=detect_language(f"input_{t}.wav")
    print("language:",lang)

    user_text=transcribe(f"input_{t}.wav",lang)
    print("user:",user_text)

    if not user_text:
        continue

    reply,conversation_history=query_llm(user_text,conversation_history)
    print("assistant:",reply)

    if reply:
        speak_interruptible(reply,lang,f"response_{t}.wav")