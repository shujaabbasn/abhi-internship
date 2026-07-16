from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
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

@asynccontextmanager
async def lifespan(app:FastAPI):
    cron.run_sync()
    yield

app=FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"]
)

class Session(BaseModel):
    pending_intent:Optional[str]=None
    pending_fields:dict={}
    missing_fields:list=[]
    language:str="en"

class ChatRequest(BaseModel):
    message:str
    session:Session

class SpeakRequest(BaseModel):
    text:str
    language:str="en"

class TTSSettingsIn(BaseModel):
    engine_en:str="piper"
    voice_en:str="en_US-bryce-medium"
    engine_ur:str="piper"
    voice_ur:str="ur_PK-fasih-medium"
    speed:float=1.0

@app.post("/speak")
def speak(request:SpeakRequest):
    audio=tts.text_to_speech(request.text,request.language)
    return Response(content=audio,media_type="audio/wav")

@app.get("/tts/settings")
def get_tts_settings():
    settings=tts.get_tts_settings()
    settings.pop("_id",None)
    return settings

@app.post("/tts/settings")
def update_tts_settings(body:TTSSettingsIn):
    tts.save_tts_settings(body.engine_en,body.voice_en,body.engine_ur,body.voice_ur,body.speed)
    return {"message":"TTS settings saved."}

@app.get("/tts/engines")
def list_tts_engines():
    engines=tts.get_available_engines()
    result=[]
    for engine in engines:
        voices=tts.get_voices_for_engine(engine["name"])
        result.append({"name":engine["name"],"label":engine["label"],"languages":engine["languages"],"voices":voices})
    return result


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

def run_function(intent,fields,original_query,language):
    intent_doc=backend_logic.get_intent(intent)
    if intent_doc is None:
        intent_doc=backend_logic.get_intent("unknown")
    handler=getattr(backend_logic,intent_doc["func_name"])
    return handler(fields,original_query,language)

def get_available_funcs():
    funcs=[]
    for name,func in inspect.getmembers(backend_logic,inspect.isfunction):
        if func.__module__!="backend_logic":
            continue
        params=list(inspect.signature(func).parameters.keys())
        if params==["fields","original_query","language"]:
            funcs.append(name)
    return funcs

class IntentIn(BaseModel):
    name:str
    description:str
    required_fields:List[str]
    example_question:Optional[str]=None
    example_fields:dict={}

class FieldPromptIn(BaseModel):
    field_name:str
    description:str
    english:str
    urdu:str

@app.get("/intents")
def list_intents():
    return list(backend_logic.intents_collection.find({},{"_id":0}))

@app.get("/field_prompts")
def list_field_prompts():
    return list(backend_logic.field_prompts_collection.find({},{"_id":0}))

@app.post("/field_prompts")
def create_field_prompt(field_prompt:FieldPromptIn):
    data=field_prompt.model_dump()
    backend_logic.field_prompts_collection.update_one(
        {"field_name":field_prompt.field_name},
        {"$set":data},
        upsert=True
    )
    cron.run_sync()
    return {"message":"Field prompt '"+field_prompt.field_name+"' saved."}

@app.delete("/field_prompts/{field_name}")
def delete_field_prompt(field_name:str):
    result=backend_logic.field_prompts_collection.delete_one({"field_name":field_name})
    if result.deleted_count==0:
        raise HTTPException(status_code=404,detail="Field prompt '"+field_name+"' not found.")
    cron.run_sync()
    return {"message":"Field prompt '"+field_name+"' deleted."}

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
    cron.run_sync()
    return {"message":"Intent '"+intent.name+"' saved."}

@app.delete("/intents/{name}")
def delete_intent(name:str):
    result=backend_logic.intents_collection.delete_one({"name":name})
    if result.deleted_count==0:
        raise HTTPException(status_code=404,detail="Intent '"+name+"' not found.")
    cron.run_sync()
    return {"message":"Intent '"+name+"' deleted."}

@app.post("/chat")
def chat(request:ChatRequest):
    message=request.message.strip()
    session=request.session
    if session.missing_fields:
        field_name=session.missing_fields[0]
        if field_name in ["account_number","from_account","to_account","recipient_account"]:
            message=backend_logic.extract_digits(message)
        if field_name=="recipient_account" and message==session.pending_fields.get("from_account"):
            retry_message=backend_logic.localize_error("You cannot send money to your own account.",session.language)+" "+backend_logic.generate_prompt_message(field_name,session.language)
            return {
                "type":"ask_field",
                "message":retry_message,
                "field":field_name,
                "session":session.model_dump()
            }
        if field_name=="amount":
            normalized=backend_logic.normalize_amount(message)
            if normalized is not None:
                message=normalized
        is_valid,error=validate_field(field_name,message)
        if not is_valid:
            retry_message=backend_logic.localize_error(error,session.language)+" "+backend_logic.generate_prompt_message(field_name,session.language)
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
            next_message=backend_logic.generate_prompt_message(next_field,session.language)
            if session.pending_intent=="request_loan" and next_field=="wants_contact":
                loan_info=backend_logic.knowledge_base({},"what loan types does abhi offer",session.language)
                next_message=loan_info+"\n\n"+next_message
            return {
                "type":"ask_field",
                "message":next_message,
                "field":next_field,
                "session":session.model_dump()
            }
        result=run_function(session.pending_intent,session.pending_fields,message,session.language)
        return {
            "type":"answer",
            "message":result,
            "session":Session(language=session.language).model_dump()
        }

    parsed=backend_logic.detect_intent(message)
    intent=parsed["intent"]
    fields=parsed["fields"]
    language=backend_logic.detect_language(message)
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
            value=backend_logic.extract_digits(value)
            if value:
                fields[field]=value
            else:
                fields.pop(field,None)
                value=None
        if field=="amount" and value:
            normalized=backend_logic.normalize_amount(value)
            if normalized is not None:
                value=normalized
                fields[field]=value
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
        field_prompt=backend_logic.generate_prompt_message(first_field,language)
        response_message=field_prompt
        if first_field in field_errors:
            response_message=backend_logic.localize_error(field_errors[first_field],language)+" "+field_prompt
        return {
            "type":"ask_field",
            "message":response_message,
            "field":first_field,
            "session":Session(pending_intent=intent,pending_fields=fields,missing_fields=missing,language=language).model_dump()
        }

    result=run_function(intent,fields,message,language)
    return {
        "type":"answer",
        "message":result,
        "session":Session(language=language).model_dump()
    }