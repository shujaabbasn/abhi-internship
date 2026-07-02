from sentence_transformers import util,SentenceTransformer
import chromadb
import requests

embedding_model=SentenceTransformer("all-MiniLM-L6-v2")

def ask_llm(query,relevant_parts):
    context=""
    for part in relevant_parts:
        context=context+part+" "
        
    prompt=(
        "You have been provided with a knowledge base and a tool."
        "Use only these to form your responses."
        "If the answer is not in the context, say you don't know."
        "Account for any spelling mistakes or typos."
        "Note that the audience is Pakistani and ruppee refers to Pakistani Ruppee"
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

chroma_client=chromadb.Client()

file=open("knowledge.txt","r")
data=file.read()
file.close()

account_types=chroma_client.create_collection("account_types")
parts=data.strip().split("\n")
all_embeddings=[]
for part in parts:
    word_embedding=embedding_model.encode(part)
    all_embeddings.append(word_embedding.tolist()) #json error, chroma needs standard pythin list 
    
all_ids=[]
for i in range(0,len(parts)):
    all_ids.append("part_"+str(i))
    
account_types.add(documents=parts,embeddings=all_embeddings,ids=all_ids)

def get_exchange_rate(old,new):
    url="https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/"+old+".json"
    response=requests.get(url)
    result=response.json()
    rates=result[old]
    new_rate=rates[new]
    return new_rate

def get_intent(query):
    decision_prompt=(
        "You have access to one tool: get_exchange_rate(from_currency,to_currency) "
        "which returns the live exchange rate between two currencies. "
        "Use this tool whenever the user wants to know a currency conversion or exchange rate, "
        "even if it involves a fraction, percentage, or part of an amount (e.g. half, double, 10%). "
        "Note that this is a chatbot for a Pakistani audience. "
        "If the user says rupee, they mean Pakistani Rupee. "
        "If the user says dollar with no country mentioned, they mean USD. "
        "from_currency is the currency the user currently HAS or is starting with. "
        "to_currency is the currency the user WANTS to convert it into. "
        "For example, if the user says 'I have 2 dollars, how much in rupees', "
        "from_currency is usd and to_currency is pkr. "
        "Extract ONLY the raw number mentioned by the user as amount. "
        "Do NOT do any math yourself (no halving, no doubling, no percentages). "
        "If the user wants a fraction or modification of the amount, "
        "add a multiplier field as a decimal (e.g. half = 0.5, double = 2, 10% = 0.1). "
        "If no modification is mentioned, multiplier is 1. "
        "Respond with EXACTLY this format and nothing else: "
        "CALLING TOOL amount,multiplier,from_currency,to_currency "
        "For example: CALLING TOOL 2,1,usd,pkr "
        "If the question does not need any currency conversion at all, respond with exactly: "
        "USING KNOWLEDGEBASE "
        "User question: "+query
    )

    response=requests.post("http://localhost:11434/api/chat",json={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":decision_prompt}],
        "stream":False
    })

    result=response.json()
    intent=result["message"]["content"].strip()
    return intent

while True:
    user_input=input("Enter your query: ")
    intent=get_intent(user_input)
    print("DETECTED INTENT: ",intent)
    if intent.startswith("CALLING TOOL"):
        currency_part=intent.replace("CALLING TOOL", "").strip()
        data=currency_part.split(",")
        amount=data[0]
        multiplier=data[1]
        from_currency=data[2]
        to_currency=data[3]
        exchange_rate=get_exchange_rate(from_currency,to_currency)
        print(amount," ",from_currency," = ",exchange_rate*float(amount)*float(multiplier),to_currency)
    else:
        query_embedding=embedding_model.encode(user_input).tolist()
        results=account_types.query(query_embeddings=[query_embedding])
        response=ask_llm(user_input,results["documents"][0])
        print("Query Response: ",response)
        
# Not all currencies with 3 letter short forms so cant use range indexing, instead split using comma. done
# when user says ruppee, assumes indian ruppee – specify in intent detection prompt, gives old, new currency accodringly. Done in prompt
# format of print("1 ",from_currency," = ",exchange_rate,to_currency) just returns exchange rate not answer: fix in main function, get an amount. done
# User using words like half of the amount, asked llm to do arithmetic, made mistakes, asked for a multiplier and then fixed.
# alternates from and to currency, made more specfic in prompt

#give a list of intents - balance,maketranscation,sendmoney,check weather
#ask llm to detect intent, accordingly call function for each checkbalance,maketransaction,sendmoney etc
#no need to manually parse etc, ask llm to return the intent and its parameters.
#use new context if intent changes, keep current context else.
#json required fields, trigger point