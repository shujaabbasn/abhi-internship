from sentence_transformers import SentenceTransformer
from db import accounts_collection,intents_collection,field_prompts_collection
from urdu_numbers import urdu_words_to_numbers
import chromadb
import requests
import json
import redis
import os
import re
from dotenv import load_dotenv

load_dotenv()
CACHE_MODE=os.environ["CACHE_MODE"]
OLLAMA_URL=os.environ["OLLAMA_URL"]
CURRENCY_API=os.environ["CURRENCY_API"]
WEATHER_API=os.environ["WEATHER_API"]
REDIS_HOST=os.environ["REDIS_HOST"]
REDIS_PORT=int(os.environ["REDIS_PORT"])

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

redis_client=redis.Redis(host=REDIS_HOST,port=REDIS_PORT,db=0,decode_responses=True)

def get_cached_intents():
    if CACHE_MODE=="file":
        try:
            cache_path=os.path.join(os.path.dirname(__file__),"cached_intents.json")
            with open(cache_path,"r") as f:
                return json.load(f)
        except (FileNotFoundError,json.JSONDecodeError) as error:
            print("Warning: could not read intent cache file,",error)
    elif CACHE_MODE=="redis":
        data=redis_client.get("cached_intents")
        if data:
            return json.loads(data)
    intents={}
    for doc in intents_collection.find():
        intents[doc["name"]]={
            "description":doc["description"],
            "required_fields":doc["required_fields"],
            "examples":doc.get("examples",[])
        }
    return intents

def get_cached_field_prompts():
    if CACHE_MODE=="file":
        try:
            cache_path=os.path.join(os.path.dirname(__file__),"cached_field_prompts.json")
            with open(cache_path,"r") as f:
                return json.load(f)
        except (FileNotFoundError,json.JSONDecodeError) as error:
            print("Warning: could not read field prompt cache file,",error)
    elif CACHE_MODE=="redis":
        data=redis_client.get("cached_field_prompts")
        if data:
            return json.loads(data)
    field_prompts={}
    for doc in field_prompts_collection.find():
        field_prompts[doc["field_name"]]={
            "description":doc.get("description",doc["english"]),
            "english":doc["english"],
            "urdu":doc["urdu"]
        }
    return field_prompts

def get_intent(name):
    return intents_collection.find_one({"name":name})

DOMAIN_WORDS_EN=[
    "account","balance","amount","currency","exchange","transfer","send","recipient",
    "weather","loan","bank","branch","dollar","rupee","PKR","USD","city","convert","number"
]

def detect_intent(query):
    cached_intents=get_cached_intents()

    intent_definitions={}
    examples_text=""
    for name,data in cached_intents.items():
        intent_definitions[name]={
            "description":data["description"],
            "required_fields":data["required_fields"]
        }
        for example in data.get("examples",[]):
            example_response=json.dumps({"intent":name,"fields":example.get("fields",{}),"language":example.get("language","en")})
            examples_text+="Example  User question: "+example["question"]+". Response: "+example_response+". "

    intents_as_json=json.dumps(intent_definitions,indent=2)
    prompt=(
        "You are an intent classifier for a banking assistant. "
        "Here are the available intents in JSON format: "
        +intents_as_json+
        "Carefully read the entire question and extract every required field that is mentioned. "
        "Always use standard 3-letter currency codes (e.g. eur, usd, pkr), never full currency names. "
        "Do not do any math yourself. If the user says half, double, or a percentage, "
        "put the raw amount in the amount field and the fraction as a decimal in multiplier (half = 0.5,double = 2). "
        "Do not guess or assume a value for any field the user did not actually mention - leave it out of fields entirely. "
        "Never assume USD for an unspecified currency, leave from_currency out so it gets asked. "
        "Your audience is Pakistani, so Ruppee likely means PKR not INR. "
        "Correct obvious typos in currency names and city names (e.g. 'dallars'->usd, 'lahoe'->lahore, 'karchi'->karachi). "
        "Use send_money whenever they are moving, paying, or sending money anywhere. "
        "request_loan's only field is wants_info, and that is only ever filled in when the user is directly "
        "answering a yes/no question, never on the first message. Do not invent a wants_info value. "
        "request_loan has no other fields, never include an amount or anything else for this intent. "
        "Use request_loan whenever the user says they want to apply for, get, or request a loan, even without any other detail. "
        "If they are only asking what loan types exist, without saying they want to apply, use knowledge_base instead. "
        "Never invent a city for check_weather if none is mentioned. 'what is weather' or 'weather' with no city named "
        "means fields should be empty, do not guess a city. "
        "A question about the calendar DATE (e.g. 'what is today's date', 'تاریخ') is NOT a weather question - "
        "it does not match any intent, classify it as unknown. "
        "Never treat a word from the question itself (like 'acc', 'account', 'balance', 'number') as an account_number. "
        "Only extract account_number if the user actually states an actual number. If no number is given, leave it out completely. "
        "The 'I want to ...' sentence structure (or its Urdu equivalent 'میں ... چاہتا ہوں') by itself does not "
        "mean request_loan - it only matters what the user wants to do. Only classify as request_loan if they "
        "specifically mention a loan or قرض, never just because of this sentence structure. "
        +examples_text+
        "IMPORTANT: Greetings and small talk (like 'how are you', 'what's up', 'kia haal hai', 'salam') "
        "must be classified as greeting with empty fields. "
        "Any other question that does not clearly and specifically match one of the intents above must be "
        "classified as unknown with empty fields. When in doubt, use unknown rather than guessing a specific intent. "
        "Also classify the language of the message as 'en' or 'ur' (Urdu script or Roman Urdu). "
        "Roman Urdu means Urdu words spelled out using English letters (e.g. 'hai','kya','kia','mera','apka','chahiye', "
        "'paisay','bhejna','kaise','kahan') - a message written this way is still Urdu, classify it as 'ur' even though "
        "none of the letters are Urdu script. Only classify as 'en' if the actual words are English words, not just the alphabet. "
        "The 'language' value must be judged independently for every message based on its own grammar - "
        "never copy the language field from the examples above, each example's language only describes that example's own text. "
        "Ignore these banking/project terms when judging the language, since they are commonly used in English "
        "even inside Urdu sentences: "+", ".join(DOMAIN_WORDS_EN)+". Judge the language only from the grammar and other words. "
        "Now classify this question, respond ONLY in JSON with keys intent, fields, and language, nothing else. "
        "User question: "+query
    )
    response=requests.post(OLLAMA_URL,json={
        "model":"llama3",
        "messages":[{"role":"user","content":prompt}],
        "format":"json",
        "stream":False,
        "options":{"temperature":0.3}
    })
    result=response.json()
    llm_output=result["message"]["content"].strip()
    try:
        parsed_out=json.loads(llm_output)
    except json.JSONDecodeError:
        parsed_out={"intent":"unknown","fields":{},"language":"en"}
    if parsed_out.get("language") not in ("en","ur"):
        parsed_out["language"]="en"
    return parsed_out

def get_field_prompt(field_name):
    cached_field_prompts=get_cached_field_prompts()
    return cached_field_prompts.get(field_name)

def generate_prompt_message(field_name,language,max_attempts=2):
    field_prompt=get_field_prompt(field_name)
    if field_prompt is not None:
        description=field_prompt["description"]
        fixed_fallback=field_prompt["urdu"] if language=="ur" else field_prompt["english"]
    else:
        description="the user's "+field_name.replace("_"," ")
        if language=="ur":
            fixed_fallback="براہ کرم مطلوبہ معلومات فراہم کریں۔"
        else:
            fixed_fallback="Please provide your "+field_name.replace("_"," ")+"."

    #a small local model has repeatedly generated grammatically broken urdu in ways no
    #amount of extra validation checks can fully catch (wrong words, wrong person, bad grammar).
    #urdu always has a curated fallback now, so just use that directly instead of gambling on generation.
    if language=="ur":
        return fixed_fallback

    prompt=(
        "You are a friendly banking assistant chatbot. "
        "You need to ask the user for this piece of information: "+description+". "
        "Write one short, natural, conversational question asking for it. "
        "Write it in English, addressing the user directly as 'you'. "
        "Output only the question itself, no quotes, no extra text."
    )
    last_attempt=None
    for attempt in range(max_attempts):
        response=requests.post(OLLAMA_URL,json={
            "model":"llama3",
            "messages":[{"role":"user","content":prompt}],
            "stream":False,
            "options":{"temperature":0.3}
        })
        result=response.json()["message"]["content"].strip()
        last_attempt=result
        if result:
            return result
    if fixed_fallback is not None:
        return fixed_fallback
    return last_attempt

ERROR_TRANSLATIONS_UR={
    "Invalid currency code. Please use a standard 3-letter code like usd, pkr, eur.":"غلط کرنسی کوڈ۔ براہ کرم معیاری تین حروف کا کوڈ استعمال کریں، مثلاً یو ایس ڈی، پی کے آر۔",
    "Invalid account number. Must be between 10 and 20 digits.":"غلط اکاؤنٹ نمبر۔ یہ 10 سے 20 ہندسوں کے درمیان ہونا چاہیے۔",
    "Account was not found":"اکاؤنٹ نہیں ملا۔",
    "Amount cannot be negative.":"رقم منفی نہیں ہو سکتی۔",
    "Amount too large. Please contact the bank directly.":"رقم بہت زیادہ ہے۔ براہ کرم بینک سے براہ راست رابطہ کریں۔",
    "Amount has to be a number.":"رقم ایک عدد ہونی چاہیے۔",
    "Could not validate city name. Please enter a valid city.":"شہر کا نام تصدیق نہیں ہو سکا۔ براہ کرم درست شہر کا نام درج کریں۔",
    "Please answer with 'yes' or 'no'.":"براہ کرم 'ہاں' یا 'نہیں' میں جواب دیں۔",
    "You cannot send money to your own account.":"آپ اپنے ہی اکاؤنٹ میں رقم نہیں بھیج سکتے۔"
}

def localize_error(error,language):
    if language=="ur" and error in ERROR_TRANSLATIONS_UR:
        return ERROR_TRANSLATIONS_UR[error]
    return error

NUMBER_WORDS={
    "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,
    "ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,
    "seventeen":17,"eighteen":18,"nineteen":19,"twenty":20,"thirty":30,"forty":40,"fifty":50,
    "sixty":60,"seventy":70,"eighty":80,"ninety":90,"hundred":100,"thousand":1000,
    "lakh":100000,"lac":100000,"million":1000000,"crore":10000000,"karor":10000000,
    "ek":1,"aik":1,"do":2,"teen":3,"tin":3,"char":4,"chaar":4,"panch":5,"paanch":5,
    "chay":6,"che":6,"chhe":6,"cheh":6,
    "saat":7,"aath":8,"aat":8,"nau":9,"das":10,"dus":10,
    "gyarah":11,"gyaarah":11,"barah":12,"baarah":12,"tera":13,"terah":13,"chaudah":14,
    "pandrah":15,"pandra":15,"solah":16,"sola":16,
    "satrah":17,"satra":17,"atharah":18,"athara":18,"unnees":19,"unees":19,
    "bees":20,"bis":20,"tees":30,"tis":30,"chalees":40,"chalis":40,
    "pachas":50,"pachaas":50,"saath":60,
    "sattar":70,"assi":80,"assy":80,"nabbe":90,"nawbay":90,
    "sau":100,"sou":100,"hazar":1000,"hazaar":1000,
    #urdu script entries are derived from urdu_numbers.py, the same source tts.py uses for speech output
    **urdu_words_to_numbers()
}

#currency/filler words allowed alongside a spoken number, e.g. "500 rupees" or "دو سو روپے".
#any other unrecognized word means the transcription is unreliable - refuse to guess rather
#than silently parse a wrong amount (see: "دو سوروں بے" misparsing to 2 instead of 200).
AMOUNT_FILLER_WORDS={"rupee","rupees","rs","pkr","rupaye","rupya","only","and","روپے","روپیہ","روپیے"}

def parse_word_number(text):
    words=text.lower().replace("-"," ").split()
    total=0
    current=0
    found=False
    for word in words:
        if word in AMOUNT_FILLER_WORDS:
            continue
        if word not in NUMBER_WORDS:
            return None
        found=True
        value=NUMBER_WORDS[word]
        if value>=100:
            if current==0:
                current=1
            current=current*value
            if value>=1000:
                total=total+current
                current=0
        else:
            current=current+value
    total=total+current
    if found:
        return str(total)
    return None

def normalize_amount(value):
    try:
        float(value)
        return value
    except ValueError:
        return parse_word_number(value)

def extract_digits(text):
    return "".join(character for character in text if character.isdigit())

def ask_llm(query,relevant_parts,language="en"):
    context=" ".join(relevant_parts)
    if language=="ur":
        model="alif-urdu"
        prompt=(
            "ذیل میں دی گئی معلومات کی بنیاد پر جواب دیں۔ "
            "اگر جواب معلومات میں موجود نہ ہو تو کہیں کہ آپ کو نہیں معلوم۔"
            "\n\nمعلومات:\n"+context+"\nسوال: "+query
        )
    else:
        model="qwen2.5:3b"
        prompt=(
            "You have been provided with a knowledge base. "
            "Use only this to form your response. "
            "If the answer is not in the context, say you don't know. "
            "\n\nContext:\n"+context+"\nQuestion: "+query
        )
    response=requests.post(OLLAMA_URL,json={
        "model":model,
        "messages":[{"role":"user","content":prompt}],
        "stream":False,
        "options":{"temperature":0.3}
    })
    result=response.json()
    return result["message"]["content"]

def get_exchange_rate(old,new):
    url=CURRENCY_API+old+".json"
    response=requests.get(url)
    result=response.json()
    rates=result[old]
    if new not in rates:
        return None
    return rates[new]

def get_account(account_number):
    return accounts_collection.find_one({"account_number":account_number})

def check_balance(fields,original_query,language):
    account_number=fields["account_number"]
    account=get_account(account_number)
    if account is None:
        if language=="ur":
            return "اکاؤنٹ نہیں ملا۔"
        return "Account was not found."
    balance=account["balance"]
    if language=="ur":
        return "آپ کا بیلنس "+str(balance)+" روپے ہے۔"
    return "Your balance is PKR "+str(balance)+"."

def send_money(fields,original_query,language):
    amount=float(fields["amount"])
    from_account=fields["from_account"]
    recipient_account=fields["recipient_account"]
    currency="pkr"
    sender=get_account(from_account)
    if sender is None:
        if language=="ur":
            return "آپ کا اکاؤنٹ نہیں ملا۔"
        return "Your account was not found."
    if amount>sender["balance"]:
        if language=="ur":
            return "کافی رقم نہیں ہے۔ آپ کا بیلنس "+str(sender["balance"])+" روپے ہے، "+str(amount)+" نہیں بھیجے جا سکتے۔"
        return "Insufficient funds. Your balance is PKR "+str(sender["balance"])+", cannot send "+str(amount)+"."
    accounts_collection.update_one({"account_number":from_account},{"$inc":{"balance":-amount}})
    accounts_collection.update_one({"account_number":recipient_account},{"$inc":{"balance":amount}})
    new_balance=sender["balance"]-amount
    if language=="ur":
        return str(amount)+" "+currency+" بھیجے جا رہے ہیں۔ ٹرانزیکشن کامیاب رہی۔ نیا بیلنس: "+str(new_balance)+" روپے"
    return "Sending "+str(amount)+" "+currency+". TRANSACTION SUCCESSFUL. New balance: PKR "+str(new_balance)

def check_weather(fields,original_query,language):
    city=fields["city"]
    response=requests.get(WEATHER_API+city+"?format=3")
    clean_text=response.text.encode("ascii","ignore").decode("ascii")
    return clean_text.strip()

def currency_conversion(fields,original_query,language):
    amount=float(fields["amount"])
    multiplier=float(fields["multiplier"])
    from_currency=fields["from_currency"]
    to_currency=fields["to_currency"]
    exchange_rate=get_exchange_rate(from_currency,to_currency)
    if exchange_rate is None:
        if language=="ur":
            return "یہ کرنسی تبدیلی مکمل نہیں ہو سکی۔"
        return "could not process that currency conversion."
    result=amount*multiplier*exchange_rate
    return str(amount*multiplier)+" "+from_currency+" = "+str(round(result,4))+" "+to_currency

def knowledge_base(fields,original_query,language):
    query_embedding=embedding_model.encode(original_query).tolist()
    results=knowledge_collection.query(query_embeddings=[query_embedding])
    return ask_llm(original_query,results["documents"][0],language)

def greeting(fields,original_query,language):
    if language=="ur":
        return "خوش آمدید! میں آپ کی بینکنگ میں کس طرح مدد کر سکتا ہوں؟"
    return "Hello! How can I help you with your banking today?"

def unknown(fields,original_query,language):
    if language=="ur":
        return "معاف کیجیے، میں سمجھ نہیں سکا۔ براہ کرم دوبارہ واضح طور پر بتائیں۔"
    prompt=(
        "You are a banking assistant chatbot. The user message below was not understood "
        "as any specific banking request. Politely say you did not understand and ask them "
        "to rephrase, in one short sentence. Reply only in English. "
        "User message: "+original_query
    )
    response=requests.post(OLLAMA_URL,json={
        "model":"qwen2.5:3b",
        "messages":[{"role":"user","content":prompt}],
        "stream":False,
        "options":{
            "num_predict":40,
            "temperature":0.3
        }
    })
    return response.json()["message"]["content"].strip()

def request_loan(fields,original_query,language):
    wants_info=fields.get("wants_info","").lower()
    if wants_info not in ["yes","y","yeah","sure","haan","han","oh","ہاں"]:
        if language=="ur":
            return "اگر آپ کبھی بھی ہمارے قرض کے آپشنز کے بارے میں جاننا چاہیں تو ہمیں بتائیں۔"
        return "let us know if you'd like to hear about our loan options anytime."
    wants_contact=fields.get("wants_contact","").lower()
    if wants_contact in ["yes","y","yeah","sure","haan","han","oh","ہاں"]:
        if language=="ur":
            return "ہماری ٹیم 2 کاروباری دنوں میں آپ سے رابطہ کرے گی۔"
        return "our team will contact you within 2 business days."
    if language=="ur":
        return "اگر آپ کا ارادہ بدل جائے تو ہمیں بتائیں۔"
    return "let us know if you change your mind."

def bank_timings(fields,original_query,language):
    if language=="ur":
        return "تمام برانچز صبح 9 بجے کھلتی ہیں اور شام 5 بجے بند ہوتی ہیں۔"
    return "all branches open at 9 am and close at 5 pm."

def not_credited(fields,original_query,language):
    if language=="ur":
        return "ہماری ٹیم آپ سے رابطہ کرے گی۔"
    return "our team will contact you."


#select box for intent
#grey out already added intents
#cronjobs
#write a cronjob to automatically run at the start, detect intent uses file
#1. write from db to file (singe node)
#2. redis - multi node

#object storage for scalability in big projects

#environment var .env
#store last massage, upper key gives last message
#toggle button for audio, output message


#mongo using class, to avoid calling everywhere, just include file
#everything like links and calls that can be in env file should be in env file
#taking voice input using browser
#voice button, taking input
#stop talking toh off, or button pressed

#waveform shown
#&&sign if state true then show states

#history maintaining through chaining

#english to urdu dictionary response should not be hardcoded
#use a class for field name and what to ask in db, idk maybe a new table?
#tehn pass that to llm accordingly and get response according to language selected
#use a db to make things congfigurable from ui
#add these tts models too #sherpa
#kokoro
#coqui coice cloning supported
#and different response each time, temp high 