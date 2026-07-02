from sentence_transformers import util,SentenceTransformer
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
        "description":"the question does not match any other intent, including small talk, personal questions about the assistant, or anything unrelated to banking",
        "required_fields":[]
    }
}

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
        "If the user does not specify what currency the amount is in (e.g. just says a number with no currency mentioned), "
        "do NOT assume USD or any other currency. Leave from_currency out of fields completely so it gets asked. "
        "Note that your audience is Pakistani, so any mention of Ruppee likely mention PKR not INR. "
        "Account for spelling mistakes and typos in currency names and locations. "
        "For example, 'dallars' means dollars/usd, 'ruppes' or 'ruppees' means rupees/pkr etc. "
        "If the city name has an obvious typo or misspelling, correct it to the most likely real city name. "
        "For example, 'lahoe' should become 'lahore', 'karchi' should become 'karachi'. "
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
    answer=result["message"]["content"]
    return answer

def get_exchange_rate(old,new):
    url="https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/"+old+".json"
    response=requests.get(url)
    result=response.json()
    rates=result[old]
    if new not in rates or old not in result:
        print("could not find currency code:",new)
        return None
    new_rate=rates[new]
    return new_rate

def check_balance(fields):
    account_number=fields["account_number"]
    example_balance=15000 #db use
    print("Account: ",account_number,", Balance: PKR",example_balance)

def send_money(fields):
    amount=fields["amount"]
    account_number=fields["account_number"]
    currency=fields["currency"]
    print("Sending",amount,currency,"to account",account_number)
    print("TRANSACTION SUCCESSFUL")

def check_weather(fields):
    city=fields["city"]
    test_response=requests.get("https://countries.dev/cities?q="+city)
    if test_response.status_code!=200 or test_response.text.strip()=="":
        print("could not validate city, please enter a valid city name")
        fields["city"]=input("Please provide city: ")
        check_weather(fields)
        return
    response=requests.get("https://wttr.in/"+city+"?format=3")
    clean_text=response.text.encode("ascii","ignore").decode("ascii")
    print(clean_text.strip())

def currency_conversion(fields):
    amount=float(fields["amount"])
    multiplier=float(fields["multiplier"])
    from_currency=fields["from_currency"]
    to_currency=fields["to_currency"]

    exchange_rate=get_exchange_rate(from_currency,to_currency)
    if exchange_rate is None:
        print("couldn't process that currency conversion")
        return
    print(amount*multiplier,from_currency,"=",amount*multiplier*exchange_rate,to_currency)

def knowledge_base(fields,original_query):
    query_embedding=embedding_model.encode(original_query).tolist()
    results=account_types.query(query_embeddings=[query_embedding])
    answer=ask_llm(original_query,results["documents"][0])
    print("Query Response:",answer)

def unknown(original_query,fields):
    response=requests.post("http://localhost:11434/api/chat",json={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":original_query}],
        "stream":False
    })
    result=response.json()
    answer=result["message"]["content"]
    print(answer)

while True:
    user_input=input("Enter your query: ")
    parsed=detect_intent(user_input)
    intent=parsed["intent"]
    fields=parsed["fields"]
    required_fields=intent_definitions[intent]["required_fields"]
    missing_fields=[]
    for field_name in required_fields:
        if field_name not in fields or fields[field_name]=="" or fields[field_name] is None:
            missing_fields.append(field_name)
    while len(missing_fields)>0:
        field_to_ask=missing_fields[0]
        user_answer=input("Please provide "+field_to_ask+": ")
        if field_to_ask=="currency" or field_to_ask=="to_currency" or field_to_ask=="from_currency":
            url="https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/"+user_answer+".json"
            test_response=requests.get(url)
            if test_response.status_code!=200:
                print("invalid currency code, please use a standard 3-letter code like usd, pkr, eur etc")
                continue
        if field_to_ask=="account_number":
            if len(user_answer)<10 or len(user_answer)>20: #db use
                print("enter valid bank account")
                continue
        if field_to_ask=="amount":
            if float(user_answer)<0:
                print("can not send or convert a negative amount")
                continue
            if float(user_answer)>10000000:
                print("amount too big, contact bank directly")
                continue
        if field_to_ask=="city":
            city_url="https://countries.dev/cities?q="+user_answer
            city_response=requests.get(city_url)
            if city_response.status_code!=200:
                print("invalid city name, enter city name again.")
                continue
        fields[field_to_ask]=user_answer
        missing_fields.remove(field_to_ask)
    if intent=="check_balance":
        check_balance(fields)
    elif intent=="send_money":
        send_money(fields)
    elif intent=="check_weather":
        check_weather(fields)
    elif intent=="currency_conversion":
        currency_conversion(fields)
    elif intent=="knowledge_base":
        knowledge_base(fields,user_input)
    else:
        unknown(user_input,fields)