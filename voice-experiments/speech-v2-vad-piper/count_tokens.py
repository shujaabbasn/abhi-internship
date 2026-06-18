import requests
#count tokens for arabic script
r1=requests.post("http://localhost:11434/api/generate",json={"model":"qwen2.5:3b","prompt":"آپ کا بیلنس کتنا ہے","raw":True,"options":{"num_predict":0}})
print("arabic tokens:",r1.json()["prompt_eval_count"])

#count tokens for roman
r2=requests.post("http://localhost:11434/api/generate",json={"model":"qwen2.5:3b","prompt":"aap ka balance kitna hai","raw":True,"options":{"num_predict":0}})
print("roman tokens:",r2.json()["prompt_eval_count"])