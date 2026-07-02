from fastapi import FastAPI
import greet_user

app=FastAPI()

app.include_router(greet_user.router)

@app.get("/")
def read_root():
    return {"message":"Hello from the main app!"}