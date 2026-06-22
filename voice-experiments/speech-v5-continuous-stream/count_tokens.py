import requests
import time

OLLAMA_URL="http://localhost:11434/api/generate"

def count_tokens(label,prompt):
    print(f"\n--- {label} ---")
    print(f"prompt: {prompt}")
    try:
        start=time.time()
        r=requests.post(OLLAMA_URL,json={
            "model":"qwen2.5:3b",
            "prompt":prompt,
            "raw":True,
            "stream":False,
            "options":{"num_predict":1}
        })
        elapsed=time.time()-start
        data=r.json()
        print(f"prompt_eval_count: {data.get('prompt_eval_count','N/A')}")
        print(f"prompt_eval_duration_ms: {data.get('prompt_eval_duration',0)/1000000:.1f}")
        print(f"total time: {elapsed:.2f}s")
    except Exception as e:
        print(f"error: {e}")
        print(f"raw response: {r.text[:500]}")

count_tokens("ARABIC SCRIPT","آپ کا بیلنس کتنا ہے")
count_tokens("ROMAN URDU","aap ka balance kitna hai")
count_tokens("ARABIC LONGER","میں اپنا اکاؤنٹ بیلنس چیک کرنا چاہتا ہوں اور پچھلی ٹرانزیکشنز بھی دیکھنی ہیں")
count_tokens("ROMAN LONGER","mein apna account balance check karna chahta hoon aur pichli transactions bhi dekhni hain")