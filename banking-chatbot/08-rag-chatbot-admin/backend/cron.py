from db import intents_collection
import json
import redis
import os
from dotenv import load_dotenv

load_dotenv()
CACHE_MODE=os.environ["CACHE_MODE"]
REDIS_HOST=os.environ["REDIS_HOST"]
REDIS_PORT=int(os.environ["REDIS_PORT"])

redis_client=redis.Redis(host=REDIS_HOST,port=REDIS_PORT,db=0,decode_responses=True)

def run_sync():
    intents={}
    for doc in intents_collection.find():
        intents[doc["name"]]={
            "description":doc["description"],
            "required_fields":doc["required_fields"],
            "example_question":doc.get("example_question"),
            "example_fields":doc.get("example_fields",{})
        }
    if CACHE_MODE=="file":
        cache_path=os.path.join(os.path.dirname(__file__),"cached_intents.json")
        with open(cache_path,"w") as file:
            json.dump(intents,file,indent=2)
        print("synced to file")
    elif CACHE_MODE=="redis":
        redis_client.set("cached_intents",json.dumps(intents))
        print("synced to redis")

if __name__=="__main__":
    run_sync()