from db import tts_settings_collection

tts_settings_collection.update_one(
    {"_id":"default"},
    {"$set":{
        "engine_en":"piper",
        "voice_en":"en_US-bryce-medium",
        "engine_ur":"piper",
        "voice_ur":"ur_PK-fasih-medium",
        "speed":1.0
    }},
    upsert=True
)
print("tts settings seeded")