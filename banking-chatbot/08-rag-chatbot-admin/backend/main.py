from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
import inspect
import requests
import os
import backend_logic
import cron
import tts

load_dotenv()
CURRENCY_API=os.environ["CURRENCY_API"]
CITIES_API=os.environ["CITIES_API"]
FRONTEND_URL=os.environ["FRONTEND_URL"]

app=FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
def sync_cache_on_startup():
    cron.run_sync()

class Session(BaseModel):
    pending_intent:Optional[str]=None
    pending_fields:dict={}
    missing_fields:list=[]

class ChatRequest(BaseModel):
    message:str
    session:Session

class SpeakRequest(BaseModel):
    text:str

@app.post("/speak")
def speak(request:SpeakRequest):
    audio=tts.text_to_speech(request.text)
    return Response(content=audio,media_type="audio/wav")

def validate_field(field_name,value):
    if field_name in ["currency","to_currency","from_currency"]:
        value=value.lower()
        url=CURRENCY_API+value+".json"
        response=requests.get(url)
        if response.status_code!=200:
            return False,"Invalid currency code. Please use a standard 3-letter code like usd, pkr, eur."
    if field_name in ["account_number","from_account","to_account","recipient_account"]:
        if len(value)<10 or len(value)>20:
            return False,"Invalid account number. Must be between 10 and 20 digits."
        if backend_logic.get_account(value) is None:
            return False,"Account was not found"
    if field_name=="amount":
        try:
            amount=float(value)
            if amount<0:
                return False,"Amount cannot be negative."
            if amount>10000000:
                return False,"Amount too large. Please contact the bank directly."
        except ValueError:
            return False,"Amount has to be a number."
    if field_name=="city":
        url=CITIES_API+value
        response=requests.get(url)
        if response.status_code!=200 or not response.text.strip():
            return False,"Could not validate city name. Please enter a valid city."
    if field_name in ["wants_info","wants_contact"]:
        if value.lower() not in ["yes","no","y","n","yeah","nah","haan","hn","han","nahi","nhi","nope"]:
            return False,"Please answer with 'yes' or 'no'."
    return True,None

def yes_no_question(field_name):
    if field_name=="wants_info":
        return "Would you like info about the loans abhi offers? (yes/no)"
    if field_name=="wants_contact":
        return "Are you interested in obtaining a loan? (yes/no)"
    return "Please provide "+field_name+":"

def run_function(intent,fields,original_query):
    intent_doc=backend_logic.get_intent(intent)
    if intent_doc is None:
        intent_doc=backend_logic.get_intent("unknown")
    handler=getattr(backend_logic,intent_doc["func_name"])
    return handler(fields,original_query)

def get_available_funcs():
    funcs=[]
    for name,func in inspect.getmembers(backend_logic,inspect.isfunction):
        if func.__module__!="backend_logic":
            continue
        params=list(inspect.signature(func).parameters.keys())
        if params==["fields","original_query"]:
            funcs.append(name)
    return funcs

class IntentIn(BaseModel):
    name:str
    description:str
    required_fields:List[str]
    example_question:Optional[str]=None
    example_fields:dict={}

@app.get("/intents")
def list_intents():
    return list(backend_logic.intents_collection.find({},{"_id":0}))

@app.get("/funcs")
def list_funcs():
    return get_available_funcs()

@app.post("/intents")
def create_intent(intent:IntentIn):
    available=get_available_funcs()
    if intent.name not in available:
        raise HTTPException(
            status_code=400,
            detail="No function named '"+intent.name+"' was found in backend_logic.py. "
        )
    data=intent.model_dump()
    data["func_name"]=intent.name
    backend_logic.intents_collection.update_one(
        {"name":intent.name},
        {"$set":data},
        upsert=True
    )
    return {"message":"Intent '"+intent.name+"' saved."}

@app.delete("/intents/{name}")
def delete_intent(name:str):
    result=backend_logic.intents_collection.delete_one({"name":name})
    if result.deleted_count==0:
        raise HTTPException(status_code=404,detail="Intent '"+name+"' not found.")
    return {"message":"Intent '"+name+"' deleted."}

@app.post("/chat")
def chat(request:ChatRequest):
    message=request.message.strip()
    session=request.session
    if session.missing_fields:
        field_name=session.missing_fields[0]
        if field_name in ["account_number","from_account","to_account","recipient_account"]:
            digits_only=""
            for character in message:
                if character.isdigit():
                    digits_only=digits_only+character
            message=digits_only
        if field_name=="recipient_account" and message==session.pending_fields.get("from_account"):
            retry_message="You cannot send money to your own account. "+yes_no_question(field_name)
            return {
                "type":"ask_field",
                "message":retry_message,
                "field":field_name,
                "session":session.model_dump()
            }
        is_valid,error=validate_field(field_name,message)
        if not is_valid:
            retry_message=error+" "+yes_no_question(field_name)
            return {
                "type":"ask_field",
                "message":retry_message,
                "field":field_name,
                "session":session.model_dump()
            }

        session.pending_fields[field_name]=message
        session.missing_fields.pop(0)

        if session.pending_intent=="request_loan" and field_name=="wants_info" and message.lower() in ["yes","y","yeah","sure","haan","han"]:
            session.missing_fields.append("wants_contact")

        if session.missing_fields:
            next_field=session.missing_fields[0]
            next_message=yes_no_question(next_field)
            if session.pending_intent=="request_loan" and next_field=="wants_contact":
                loan_info=backend_logic.knowledge_base({},"what loan types does abhi offer")
                next_message=loan_info+"\n\n"+next_message
            return {
                "type":"ask_field",
                "message":next_message,
                "field":next_field,
                "session":session.model_dump()
            }
        result=run_function(session.pending_intent,session.pending_fields,message)
        return {
            "type":"answer",
            "message":result,
            "session":{"pending_intent":None,"pending_fields":{},"missing_fields":[]}
        }

    parsed=backend_logic.detect_intent(message)
    intent=parsed["intent"]
    fields=parsed["fields"]
    intent_doc=backend_logic.get_intent(intent)
    if intent_doc is None:
        intent=backend_logic.get_intent("unknown")["name"]
        required=[]
    else:
        required=intent_doc["required_fields"]
    missing=[]
    field_errors={}
    for field in required:
        value=fields.get(field)
        if field=="wants_info":
            fields.pop(field,None)
            value=None
        if field in ["account_number","from_account","to_account","recipient_account"] and value:
            digits_only=""
            for character in value:
                if character.isdigit():
                    digits_only=digits_only+character
            value=digits_only
            if value:
                fields[field]=value
            else:
                fields.pop(field,None)
                value=None
        if not value:
            missing.append(field)
        elif field=="recipient_account" and value==fields.get("from_account"):
            fields.pop(field,None)
            missing.append(field)
            field_errors[field]="You cannot send money to your own account."
        else:
            is_valid,error=validate_field(field,value)
            if not is_valid:
                fields.pop(field,None)
                missing.append(field)
                field_errors[field]=error
    if missing:
        first_field=missing[0]
        response_message=yes_no_question(first_field)
        if first_field in field_errors:
            response_message=field_errors[first_field]+" "+yes_no_question(first_field)
        return {
            "type":"ask_field",
            "message":response_message,
            "field":first_field,
            "session":{
                "pending_intent":intent,
                "pending_fields":fields,
                "missing_fields":missing
            }
        }

    result=run_function(intent,fields,message)
    return {
        "type":"answer",
        "message":result,
        "session":{"pending_intent":None,"pending_fields":{},"missing_fields":[]}
    }