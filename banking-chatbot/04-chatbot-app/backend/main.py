from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chatbot

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    text:str=""

@app.post("/chat")
def chat(message:ChatMessage):
    reply=chatbot.process_message(message.text)
    return {"reply":reply}
