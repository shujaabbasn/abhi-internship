from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

class Database:
    def __init__(self):
        self.url=os.environ.get("MONGO_URL","mongodb://localhost:27017")
        self.db_name=os.environ.get("MONGO_DB_NAME","abhi_bank")
        self.client=MongoClient(self.url)
        self.db=self.client[self.db_name]
        print("db connection initialized")

    def get_db(self):
        return self.db

    def get_collection(self,collection_name):
        return self.db[collection_name]

mongo_manager=Database()
db=mongo_manager.get_db()
accounts_collection=mongo_manager.get_collection("accounts")
intents_collection=mongo_manager.get_collection("intents")
field_prompts_collection=mongo_manager.get_collection("field_prompts")
tts_settings_collection=mongo_manager.get_collection("tts_settings")