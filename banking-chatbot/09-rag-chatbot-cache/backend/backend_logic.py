from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
import chromadb
import requests
import json
import os
import redis

embedding_model=SentenceTransformer("all-MiniLM-L6-v2")
chroma_client=chromadb.Client()
knowledge_collection=chroma_client.create_collection("knowledge")

account_knowledge_base_path=os.path.join(os.path.dirname(__file__),"account_knowledge.txt")
with open(account_knowledge_base_path,"r") as file:
    account_data=file.read()

loan_knowledge_base_path=os.path.join(os.path.dirname(__file__),"loan_knowledge.txt")
with open(loan_knowledge_base_path,"r") as file:
    loan_data=file.read()

parts=account_data.strip().split("\n")+loan_data.strip().split("\n")

all_embeddings=[]
for part in parts:
    all_embeddings.append(embedding_model.encode(part).tolist())

all_ids=[]
for i in range(0,len(parts)):
    all_ids.append("part_"+str(i))

knowledge_collection.add(documents=parts,embeddings=all_embeddings,ids=all_ids)

client=MongoClient("mongodb://localhost:27017")
db=client["abhi_bank"]
accounts_collection=db["accounts"]
intents_collection=db["intents"]



###################################


USE_REDIS=False
intents_cache_path=os.path.join(os.path.dirname(__file__),"intents_cache.json")
#
##########################





def load_cached_intents():
    if USE_REDIS==True:
        redis_client=redis.Redis(host="localhost",port=6379,decode_responses=True)
        raw=redis_client.get("intents_cache")
        if raw is None:
            return list(intents_collection.find({},{"_id":0}))
        return json.loads(raw)
    if os.path.exists(intents_cache_path):
        with open(intents_cache_path,"r") as file:
            return json.load(file)
    return list(intents_collection.find({},{"_id":0}))



def get_intent_definitions():
    definitions={}
    for doc in load_cached_intents():
        definitions[doc["name"]]={
            "description":doc["description"],
            "required_fields":doc["required_fields"]
        }
    return definitions

def get_intent_examples():
    examples=""
    for doc in load_cached_intents():
        if doc.get("example_question"):
            example_response=json.dumps({"intent":doc["name"],"fields":doc.get("example_fields",{})})
            examples+="Example  User question: "+doc["example_question"]+". Response: "+example_response+". "
    return examples

def get_intent(name):
    for doc in load_cached_intents():
        if doc["name"]==name:
            return doc
    return None

def detect_intent(query):
    intent_definitions=get_intent_definitions()
    intents_as_json=json.dumps(intent_definitions,indent=2)
    examples_text=get_intent_examples()
    prompt=(
        "You are an intent classifier for a banking assistant. "
        "Here are the available intents in JSON format: "
        +intents_as_json+
        "Carefully read the entire question and extract every required field that is mentioned. "
        "Always use standard 3-letter currency codes (e.g. eur, usd, pkr), never full currency names. "
        "Do not do any math yourself. If the user says half, double, or a percentage, "
        "put the raw amount in the amount field and the fraction as a decimal in multiplier (half = 0.5,double = 2). "
        "Do not guess or assume a value for any field the user did not actually mention. "
        "If a field is not mentioned, do not include it in fields at all, leave it out completely. "
        "If the user does not specify what currency the amount is in (e.g. just says a number with no currency mentioned), "
        "do NOT assume USD or any other currency. Leave from_currency out of fields completely so it gets asked. "
        "Note that your audience is Pakistani, so any mention of Ruppee likely mention PKR not INR. "
        "Account for spelling mistakes and typos in currency names and locations. "
        "For example, 'dallars' means dollars/usd, 'ruppes' or 'ruppees' means rupees/pkr etc. "
        "If the city name has an obvious typo or misspelling, correct it to the most likely real city name. "
        "For example, 'lahoe' should become 'lahore', 'karchi' should become 'karachi'. "
        "Use send_money whenever they are moving, paying, or sending money anywhere. "
        "request_loan's only field is wants_info, and that is only ever filled in when the user is directly "
        "answering a yes/no question, never on the first message. Do not invent a wants_info value. "
        "request_loan has no other fields, never include an amount or anything else for this intent. "
        "Use request_loan whenever the user says they want to apply for, get, or request a loan, even without any other detail. "
        "If they are only asking what loan types exist, without saying they want to apply, use knowledge_base instead. "
        "Never invent a city for check_weather if none is mentioned. 'what is weather' or 'weather' with no city named "
        "means fields should be empty, do not guess a city. "
        "Never treat a word from the question itself (like 'acc', 'account', 'balance', 'number') as an account_number. "
        "Only extract account_number if the user actually states an actual number. If no number is given, leave it out completely. "
        +examples_text+
        "Now classify this question, respond ONLY in the same JSON format as above, nothing else. "
        "User question: "+query
    )
    response=requests.post("http://localhost:11434/api/chat",json={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":prompt}],
        "format":"json",
        "stream":False
    })
    result=response.json()
    llm_output=result["message"]["content"].strip()
    parsed_out=json.loads(llm_output)
    return parsed_out

def ask_llm(query,relevant_parts):
    context=" ".join(relevant_parts)
    prompt=(
        "You have been provided with a knowledge base. "
        "Use only this to form your response. "
        "If the answer is not in the context, say you don't know. "
        "\n\nContext:\n"+context+"\nQuestion: "+query
    )
    response=requests.post("http://localhost:11434/api/chat",json={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":prompt}],
        "stream":False
    })
    result=response.json()
    return result["message"]["content"]

def get_exchange_rate(old,new):
    url="https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/"+old+".json"
    response=requests.get(url)
    result=response.json()
    rates=result[old]
    if new not in rates:
        return None
    return rates[new]

def get_account(account_number):
    return accounts_collection.find_one({"account_number":account_number})

def check_balance(fields,original_query):
    account_number=fields["account_number"]
    account=get_account(account_number)
    if account is None:
        return "Account "+account_number+" was not found."
    return "Account: "+account_number+", Balance: PKR "+str(account["balance"])

def send_money(fields,original_query):
    amount=float(fields["amount"])
    from_account=fields["from_account"]
    recipient_account=fields["recipient_account"]
    currency=fields["currency"]
    sender=get_account(from_account)
    if sender is None:
        return "Your account "+from_account+" was not found."
    if amount>sender["balance"]:
        return "Insufficient funds. Your balance in "+from_account+" is PKR "+str(sender["balance"])+", cannot send "+str(amount)+"."
    accounts_collection.update_one({"account_number":from_account},{"$inc":{"balance":-amount}})
    accounts_collection.update_one({"account_number":recipient_account},{"$inc":{"balance":amount}})
    new_balance=sender["balance"]-amount
    return "Sending "+str(amount)+" "+currency+" to account "+recipient_account+". TRANSACTION SUCCESSFUL. New balance in "+from_account+": PKR "+str(new_balance)

def check_weather(fields,original_query):
    city=fields["city"]
    response=requests.get("https://wttr.in/"+city+"?format=3")
    clean_text=response.text.encode("ascii","ignore").decode("ascii")
    return clean_text.strip()

def currency_conversion(fields,original_query):
    amount=float(fields["amount"])
    multiplier=float(fields["multiplier"])
    from_currency=fields["from_currency"]
    to_currency=fields["to_currency"]
    exchange_rate=get_exchange_rate(from_currency,to_currency)
    if exchange_rate is None:
        return "could not process that currency conversion."
    result=amount*multiplier*exchange_rate
    return str(amount*multiplier)+" "+from_currency+" = "+str(round(result,4))+" "+to_currency

def knowledge_base(fields,original_query):
    query_embedding=embedding_model.encode(original_query).tolist()
    results=knowledge_collection.query(query_embeddings=[query_embedding])
    return ask_llm(original_query,results["documents"][0])

def unknown(fields,original_query):
    response=requests.post("http://localhost:11434/api/chat",json={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":original_query}],
        "stream":False
    })
    return response.json()["message"]["content"]

def request_loan(fields,original_query):
    wants_info=fields.get("wants_info","").lower()
    if wants_info not in ["yes","y","yeah","sure","haan","han"]:
        return "let us know if you'd like to hear about our loan options anytime."
    wants_contact=fields.get("wants_contact","").lower()
    if wants_contact in ["yes","y","yeah","sure","haan","han"]:
        return "our team will contact you within 2 business days."
    return "let us know if you change your mind."

def bank_timings(fields,original_query):
    return "all branches open at 9 am and close at 5 pm."


#select box for intent
#grey out already added intents
#cronjobs
#write a cronjob to automatically run at the start, detect intent uses file
#1. write from db to file (singe node)
#2. redis - multi node