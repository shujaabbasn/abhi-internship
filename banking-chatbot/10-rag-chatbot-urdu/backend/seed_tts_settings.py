from db import tts_settings_collection

tts_settings_collection.update_one(
    {"_id":"default"},
    {"$set":{
        "engine":"piper",
        "voice_en":"en-US-bryce-medium",
        "voice_ur":"ur-PK-fasih-medium",
        "speed":1.0
    }},
    upsert=True
)
print("tts settings seeded")