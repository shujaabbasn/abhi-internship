import requests

from config import OLLAMA_MODEL, OLLAMA_URL, OLLAMA_TEMPERATURE, OLLAMA_NUM_PREDICT, SAMPLE_PROMPT

def query_llm(user_text, history):
    #LLM - history is a list of {"role":..., "content":...} dicts, grows each turn
    history=history+[{"role":"user","content":user_text}]

    qwen_data={
        "model":OLLAMA_MODEL,
        "messages":[{"role":"system","content":SAMPLE_PROMPT}]+history,
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
        history=history+[{"role":"assistant","content":reply}]
        return reply,history
    except Exception as error:
        print("Error:",error)
        return "",history