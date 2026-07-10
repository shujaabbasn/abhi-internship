from pymongo import MongoClient
import json
import os
import tempfile

BACKEND_DIR=os.path.dirname(os.path.abspath(__file__))
CACHE_FILE=os.path.join(BACKEND_DIR,"intents_cache.json")

def get_intents():
    client=MongoClient("mongodb://localhost:27017")
    db=client["abhi_bank"]
    intents_collection=db["intents"]
    return list(intents_collection.find({},{"_id":0}))

def write_file_cache(intents):
    fd,temp_path=tempfile.mkstemp(dir=BACKEND_DIR,prefix=".intents_cache_",suffix=".tmp")
    try:
        with os.fdopen(fd,"w") as file:
            json.dump(intents,file,indent=2)
        os.replace(temp_path,CACHE_FILE)
    except Exception:
        os.remove(temp_path)
        raise

def write_redis_cache(intents):
    try:
        import redis
        redis_client=redis.Redis(host="localhost",port=6379,decode_responses=True,socket_connect_timeout=2)
        redis_client.set("intents_cache",json.dumps(intents))
        return True
    except Exception as error:
        print("Warning: could not write to Redis,",error)
        return False

if __name__=="__main__":
    intents=get_intents()
    write_file_cache(intents)
    print("Wrote",len(intents),"intents to",CACHE_FILE)
    if write_redis_cache(intents):
        print("Wrote",len(intents),"intents to Redis")