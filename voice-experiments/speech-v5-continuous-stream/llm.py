import requests
from config import (OLLAMA_MODEL,OLLAMA_URL,OLLAMA_TEMPERATURE,OLLAMA_NUM_PREDICT,
                    SAMPLE_PROMPT,CONTEXT_WINDOW_SIZE,USE_TRANSLITERATION,SAMPLE_PROMPT_ROMAN)

#pick prompt based on transliteration mode
if USE_TRANSLITERATION==True:
    ACTIVE_PROMPT=SAMPLE_PROMPT_ROMAN
else:
    ACTIVE_PROMPT=SAMPLE_PROMPT

def query_llm(user_text,past_context):
    past_context=past_context[-CONTEXT_WINDOW_SIZE:]+[{"role":"user","content":user_text}]
    qwen_data={
        "model":OLLAMA_MODEL,
        "messages":[{"role":"system","content":ACTIVE_PROMPT}]+past_context,
        "stream":False,
        "options":
        {
            "temperature":OLLAMA_TEMPERATURE,
            "num_predict":OLLAMA_NUM_PREDICT
        }
    }
    try:
        response=requests.post(OLLAMA_URL,json=qwen_data)
        response.raise_for_status()
        reply=response.json()["message"]["content"]
        past_context=past_context+[{"role":"assistant","content":reply}]
        return reply,past_context
    except Exception:
        print("Error")
        return "",past_context

def detect_intent(user_input):
    intent_prompt=f"""Analyze the user's input and describe their core intent in 2-3 words. Example: 'coding help', 'set alarm', 'general chat'. Input: "{user_input}". Return ONLY the 2-3 word description."""
    payload={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":intent_prompt}],
        "stream":False,
        "options":{"temperature":0.3}
    }
    try:
        response=requests.post(OLLAMA_URL,json=payload)
        return response.json()["message"]["content"]
    except:
        return "general"