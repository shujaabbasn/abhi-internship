from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import greet_user

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(greet_user.router)
