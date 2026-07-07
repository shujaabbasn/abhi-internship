from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import backend_logic

app=FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class Session(BaseModel):
    pending_intent:Optional[str]=None
    pending_fields:dict={}
    missing_fields:list=[]

class ChatRequest(BaseModel):
    message:str
    session:Session

def validate_field(field_name,value):
    if field_name in ["currency","to_currency","from_currency"]:
        url="https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/"+value+".json"
        response=requests.get(url)
        if response.status_code!=200:
            return False,"Invalid currency code. Please use a standard 3-letter code like usd, pkr, eur."
    if field_name in ["account_number","from_account","to_account"]:
        if len(value)<10 or len(value)>20:
            return False,"Invalid account number. Must be between 10 and 20 digits."
        if backend_logic.get_account(value) is None:
            return False,"Account "+value+" was not found."
    if field_name=="recipient_account":
        if len(value)<10 or len(value)>20:
            return False,"Invalid account number. Must be between 10 and 20 digits."
    if field_name=="amount":
        try:
            amount=float(value)
            if amount<0:
                return False,"Amount cannot be negative."
            if amount>10000000:
                return False,"Amount too large. Please contact the bank directly."
        except ValueError:
            return False,"Amount must be a number."
    if field_name=="city":
        url="https://countries.dev/cities?q="+value
        response=requests.get(url)
        if response.status_code!=200 or not response.text.strip():
            return False,"Could not validate city name. Please enter a valid city."
    return True,None

def run_function(intent,fields,original_query):
    if intent=="check_balance":
        return backend_logic.check_balance(fields)
    elif intent=="send_money":
        return backend_logic.send_money(fields)
    elif intent=="transfer_funds":
        return backend_logic.transfer_funds(fields)
    elif intent=="check_weather":
        return backend_logic.check_weather(fields)
    elif intent=="currency_conversion":
        return backend_logic.currency_conversion(fields)
    elif intent=="knowledge_base":
        return backend_logic.knowledge_base(original_query)
    else:
        return backend_logic.unknown(original_query)

@app.post("/chat")
def chat(request:ChatRequest):
    message=request.message.strip()
    session=request.session
    if session.missing_fields:
        field_name=session.missing_fields[0]
        is_valid,error=validate_field(field_name,message)
        if not is_valid:
            return {
                "type":"ask_field",
                "message":error+" Please provide "+field_name+":",
                "field":field_name,
                "session":session.model_dump()
            }
        session.pending_fields[field_name]=message
        session.missing_fields.pop(0)
        if session.missing_fields:
            next_field=session.missing_fields[0]
            return {
                "type":"ask_field",
                "message":"Please provide "+next_field+":",
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
    required=backend_logic.intent_definitions[intent]["required_fields"]
    missing=[]
    field_errors={}
    for field in required:
        value=fields.get(field)
        if not value:
            missing.append(field)
        else:
            is_valid,error=validate_field(field,value)
            if not is_valid:
                fields.pop(field,None)
                missing.append(field)
                field_errors[field]=error
    if missing:
        first_field=missing[0]
        message="please provide "+first_field+":"
        if first_field in field_errors:
            message=field_errors[first_field]+" Please provide "+first_field+":"
        return {
            "type":"ask_field",
            "message":message,
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