from fastapi import APIRouter,HTTPException
from typing import Optional
from pydantic import BaseModel
from pymongo import MongoClient
import re

client=MongoClient("mongodb://localhost:27017")
db=client["fastapi_testproject"]
users_collection=db["users"]

class UserProfile(BaseModel):
    username:str
    age:int
    role:str
    school:Optional[str]

router=APIRouter()

@router.get("/allusers")
def get_all():
    all_users=list(users_collection.find({},{"_id":0}))
    return {"users":all_users}

@router.get("/search")
def search_users(name:str):
    name_lower=name.lower()
    user_data=users_collection.find_one({"username_lower":name_lower})
    if not user_data:
        raise HTTPException(status_code=404,detail=f"User '{name}' does not exist")
    return {
        "username":user_data["username"],
        "age":user_data["age"],
        "role":user_data["role"],
        "school":user_data["school"]
    }

@router.post("/createuser")
def create_user(user:UserProfile):
    if not user.username.strip():
        raise HTTPException(status_code=400,detail="Username is required")
    if len(user.username)>50:
        raise HTTPException(status_code=400,detail="Username must be 50 characters or less")
    if user.age<1 or user.age>120:
        raise HTTPException(status_code=400,detail="Age must be between 1 and 120")
    if not user.role.strip():
        raise HTTPException(status_code=400,detail="Role is required")
    if user.role.strip().lower() not in ["student","professor","ta"]:
        raise HTTPException(status_code=400,detail="Role must be one of professor, student or ta")
    if len(user.role)>50:
        raise HTTPException(status_code=400,detail="Role must be 50 characters or less")
    if user.school and len(user.school)>50:
        raise HTTPException(status_code=400,detail="School must be 50 characters or less")
    name_lower=user.username.lower()
    existing_user=users_collection.find_one({"username_lower":name_lower})
    if existing_user:
        raise HTTPException(status_code=400,detail="User already exists")
    new_user={
        "username":user.username,
        "username_lower":name_lower,
        "age":user.age,
        "role":user.role,
        "school":user.school
    }
    users_collection.insert_one(new_user)
    return {"message":"Successfully created user "+user.username}

@router.put("/updateage")
def update_age(name:str,new_age:int):
    if new_age<1 or new_age>120:
        raise HTTPException(status_code=400,detail="Age must be between 1 and 120")
    name_lower=name.lower()
    if not users_collection.find_one({"username_lower":name_lower}):
        raise HTTPException(status_code=404,detail="User does not exist")
    users_collection.update_one({"username_lower":name_lower},{"$set":{"age":new_age}})
    return {"message":"Updated "+name+"'s age to "+str(new_age)}

@router.put("/updateschool")
def update_school(name:str,school:str):
    if len(school)>100:
        raise HTTPException(status_code=400,detail="School must be 100 characters or less")
    name_lower=name.lower()
    if not users_collection.find_one({"username_lower":name_lower}):
        raise HTTPException(status_code=404,detail="Not found")
    users_collection.update_one({"username_lower":name_lower},{"$set":{"school":school}})
    return {"message":"Updated"+name+"'s school to "+school}

@router.delete("/deleteuser")
def delete_user(name:str):
    name_lower=name.lower()
    if not users_collection.find_one({"username_lower":name_lower}):
        raise HTTPException(status_code=404,detail="User does not exist")
    users_collection.delete_one({"username_lower":name_lower})
    return {"message":"Deleted user "+name}


#all, add, delete. in form of pages
#toast form to show errors, library npm install