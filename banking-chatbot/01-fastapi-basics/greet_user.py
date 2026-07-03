from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from pymongo import MongoClient

client=MongoClient("mongodb://localhost:27017")
db=client["fastapi_testproject"] 
users_collection=db["users"]

class UserProfile(BaseModel):
    username:str
    age:int
    role:str

router=APIRouter() 

@router.get("/something")
def read_something():
    return {"message":"Hello"}

@router.get("/search")
def search_users(name:str,age:Optional[int]=None):
    name_lower=name.lower()
    user_data=users_collection.find_one({"username_lower":name_lower})
    if not user_data:
        raise HTTPException(
            status_code=404, 
            detail=f"Sorry, the user '{name}' does not exist."
        )
        
    return {
        "message": "User found in MongoDB", 
        "user": user_data["username"],
        "data": {
            "age": user_data["age"],
            "role": user_data["role"]
        }
    }
        
        
@router.post("/create")
def create_user(user:UserProfile):
    name_lower=user.username.lower()
    existing_user=users_collection.find_one({"username_lower": name_lower})
    if existing_user:
        raise HTTPException(status_code=400,detail="User already exists, cant create")
    new_user={
        "username":user.username,
        "username_lower":name_lower,
        "age":user.age,
        "role":user.role,
    }
    users_collection.insert_one(new_user)
    return {"message":f"Successfully created user {user.username}!"}

@router.get("/allusers")
def get_all():
    all_users=list(users_collection.find({},{"_id":0}))
    return {"users":all_users}

@router.put("/update")
def update(name:str,new_age:int):
    name_lower=name.lower()
    if not users_collection.find_one({"username_lower":name_lower}):
        raise HTTPException(status_code=404,detail="no user of this name exists")
    name_lower=name.lower()
    users_collection.update_one({"username_lower":name_lower},{"$set": {"age":new_age}})
    return {"updated"}
    
@router.delete("/delete")
def delete(name:str):
    name_lower=name.lower()
    if not users_collection.find_one({"username_lower":name_lower}):
        raise HTTPException(status_code=404,detail="no user of this name exists")
    users_collection.delete_one({"username_lower":name_lower})
    return {"deleted"}