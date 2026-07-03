from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    text: str=""
    language: str="english"

@app.post("/chat")
def chat(message: ChatMessage):
    reply_text="you said: "+message.text
    return {"reply": reply_text}