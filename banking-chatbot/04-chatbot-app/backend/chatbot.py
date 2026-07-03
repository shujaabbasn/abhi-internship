from sentence_transformers import SentenceTransformer
import chromadb
import requests
import json

embedding_model=SentenceTransformer("all-MiniLM-L6-v2")

intent_definitions={
    "check_balance":{
        "description":"user wants to check their account balance",
        "required_fields":["account_number"]
    },
    "send_money":{
        "description":"user wants to send money or make a transaction to someone",
        "required_fields":["amount","account_number","currency"]
    },
    "check_weather":{
        "description":"user wants to know the current weather",
        "required_fields":["city"]
    },
    "currency_conversion":{
        "description":"user wants to convert or know an exchange rate between currencies",
        "required_fields":["amount","multiplier","from_currency","to_currency"]
    },
    "knowledge_base":{
        "description":"user is asking about Abhi's products, services, or account types",
        "required_fields":[]
    },
    "unknown":{
        "description":"the question does not match any other intent",
        "required_fields":[]
    }
}

chroma_client=chromadb.Client()
account_types=chroma_client.create_collection("account_types")

file=open("knowledge.txt","r")
data=file.read()
file.close()

parts=data.strip().split("\n")
all_embeddings=[]
for part in parts:
    word_embedding=embedding_model.encode(part)
    all_embeddings.append(word_embedding.tolist())

all_ids=[]
for i in range(0,len(parts)):
    all_ids.append("part_"+str(i))

account_types.add(documents=parts,embeddings=all_embeddings,ids=all_ids)

session={}

def check_balance(fields):
    account_number=fields["account_number"]
    example_balance=15000
    return "Account: "+account_number+", Balance: PKR "+str(example_balance)

def send_money(fields):
    amount=fields["amount"]
    account_number=fields["account_number"]
    currency=fields["currency"]
    return "Sending "+amount+" "+currency+" to account "+account_number+". TRANSACTION SUCCESSFUL"

def check_weather(fields):
    city=fields["city"]
    test_response=requests.get("https://countries.dev/cities?q="+city)
    if test_response.status_code!=200 or test_response.text.strip()=="":
        return "invalid_city"
    response=requests.get("https://wttr.in/"+city+"?format=3")
    clean_text=response.text.encode("ascii","ignore").decode("ascii")
    return clean_text.strip()

def currency_conversion(fields):
    amount=float(fields["amount"])
    multiplier=float(fields["multiplier"])
    from_currency=fields["from_currency"]
    to_currency=fields["to_currency"]
    exchange_rate=get_exchange_rate(from_currency,to_currency)
    if exchange_rate is None:
        return "couldn't process that currency conversion"
    return str(amount*multiplier)+" "+from_currency+" = "+str(amount*multiplier*exchange_rate)+" "+to_currency

def get_exchange_rate(old,new):
    url="https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/"+old+".json"
    response=requests.get(url)
    result=response.json()
    rates=result[old]
    if new not in rates or old not in result:
        return None
    return rates[new]

def ask_llm(query,relevant_parts):
    context=""
    for part in relevant_parts:
        context=context+part+" "
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

def knowledge_base(fields,original_query):
    query_embedding=embedding_model.encode(original_query).tolist()
    results=account_types.query(query_embeddings=[query_embedding])
    return ask_llm(original_query,results["documents"][0])

def unknown(original_query):
    response=requests.post("http://localhost:11434/api/chat",json={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":original_query}],
        "stream":False
    })
    result=response.json()
    return result["message"]["content"]

def detect_intent(query):
    intents_as_json=json.dumps(intent_definitions,indent=2)
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
        "If the user does not specify what currency the amount is in, do NOT assume USD or any other currency. "
        "Note that your audience is Pakistani, so any mention of Ruppee likely means PKR not INR. "
        "Account for spelling mistakes and typos in currency names and locations. "
        'Example 1  User question: what is my balance for account 5521. Response: {"intent": "check_balance", "fields": {"account_number": "5521"}}. '
        'Example 2  User question: send 500 rupees to account 12345. Response: {"intent": "send_money", "fields": {"amount": "500", "account_number": "12345", "currency": "pkr"}}. '
        'Example 3  User question: what is the weather in lahore. Response: {"intent": "check_weather", "fields": {"city": "lahore"}}. '
        'Example 4  User question: I have 5 euros, how much is that in dollars. Response: {"intent": "currency_conversion", "fields": {"amount": "5", "multiplier": "1", "from_currency": "eur", "to_currency": "usd"}}. '
        'Example 5  User question: does abhi have accounts for retirement. Response: {"intent": "knowledge_base", "fields": {}}. '
        'Example 6  User question: what is your name. Response: {"intent": "unknown", "fields": {}}. '
        "Now classify this question, respond ONLY in the same JSON format as above, nothing else. "
        "User question: "+query
    )
    response=requests.post("http://localhost:11434/api/chat",json={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":prompt}],
        "stream":False
    })
    result=response.json()
    llm_output=result["message"]["content"].strip()
    parsed_out=json.loads(llm_output)
    return parsed_out

def process_message(user_input):
    if "intent" in session:
        intent=session["intent"]
        fields=session["fields"]
        missing=session["missing"]
        field_to_fill=missing[0]
        
        if field_to_fill=="currency" or field_to_fill=="to_currency" or field_to_fill=="from_currency":
            url="https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/"+user_input+".json"
            test_response=requests.get(url)
            if test_response.status_code!=200:
                return "invalid currency code, please use a standard 3-letter code like usd, pkr, eur etc"
        if field_to_fill=="account_number":
            if len(user_input)<10 or len(user_input)>20:
                return "enter valid bank account number"
        if field_to_fill=="amount":
            if float(user_input)<0:
                return "cannot send or convert a negative amount"
            if float(user_input)>10000000:
                return "amount too big, contact bank directly"
        if field_to_fill=="city":
            city_url="https://countries.dev/cities?q="+user_input
            city_response=requests.get(city_url)
            if city_response.status_code!=200:
                return "invalid city name, enter city name again"

        fields[field_to_fill]=user_input
        missing.remove(field_to_fill)

        if len(missing)>0:
            return "please provide "+missing[0]

        session.clear()
        return execute_intent(intent,fields,user_input)

    parsed=detect_intent(user_input)
    intent=parsed["intent"]
    fields=parsed["fields"]
    required_fields=intent_definitions[intent]["required_fields"]
    missing=[]
    for field_name in required_fields:
        if field_name not in fields or fields[field_name]=="" or fields[field_name] is None:
            missing.append(field_name)

    if len(missing)>0:
        session["intent"]=intent
        session["fields"]=fields
        session["missing"]=missing
        return "please provide "+missing[0]

    return execute_intent(intent,fields,user_input)

def execute_intent(intent,fields,original_query):
    if intent=="check_balance":
        return check_balance(fields)
    elif intent=="send_money":
        return send_money(fields)
    elif intent=="check_weather":
        reply=check_weather(fields)
        if reply=="invalid_city":
            session["intent"]="check_weather"
            session["fields"]=fields
            session["missing"]=["city"]
            return "could not validate city, please provide a valid city name"
        return reply
    elif intent=="currency_conversion":
        return currency_conversion(fields)
    elif intent=="knowledge_base":
        return knowledge_base(fields,original_query)
    else:
        return unknown(original_query)