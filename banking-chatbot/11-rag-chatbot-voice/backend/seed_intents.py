from db import intents_collection as intents

demo_intents=[
    {
        "name": "check_balance",
        "description": "user wants to check their account balance",
        "required_fields": ["account_number"],
        "func_name": "check_balance",
        "examples": [
            {"question": "what is my balance for account 5521", "fields": {"account_number": "5521"}, "language": "en"},
            {"question": "mera account balance kia hai", "fields": {}, "language": "ur"},
        ]
    },
    {
        "name": "send_money",
        "description": "user wants to send or transfer money to any account",
        "required_fields": ["amount", "currency", "from_account", "recipient_account"],
        "func_name": "send_money",
        "examples": [
            {"question": "send 500 rupees from account 1234567890 to account 12345", "fields": {"amount": "500", "currency": "pkr", "from_account": "1234567890", "recipient_account": "12345"}, "language": "en"},
            {"question": "میں پیسے بھیجنا چاہتا ہوں۔", "fields": {}, "language": "ur"},
        ]
    },
    {
        "name": "check_weather",
        "description": "user wants to know the current weather",
        "required_fields": ["city"],
        "func_name": "check_weather",
        "examples": [
            {"question": "what is the weather in lahore", "fields": {"city": "lahore"}, "language": "en"},
        ]
    },
    {
        "name": "currency_conversion",
        "description": "user wants to convert or know an exchange rate between currencies",
        "required_fields": ["amount", "multiplier", "from_currency", "to_currency"],
        "func_name": "currency_conversion",
        "examples": [
            {"question": "I have 5 euros, how much is that in dollars", "fields": {"amount": "5", "multiplier": "1", "from_currency": "eur", "to_currency": "usd"}, "language": "en"},
        ]
    },
    {
        "name": "knowledge_base",
        "description": "user is asking about Abhi's products, services, account types, or loan types (informational, not an active request)",
        "required_fields": [],
        "func_name": "knowledge_base",
        "examples": [
            {"question": "what loan types does abhi offer", "fields": {}, "language": "en"},
            {"question": "ABHI کون سے قرض کی اقسام پیش کرتا ہے؟", "fields": {}, "language": "ur"},
        ]
    },
    {
        "name": "request_loan",
        "description": "user wants to actively apply for or request a loan",
        "required_fields": ["wants_info"],
        "func_name": "request_loan",
        "examples": [
            {"question": "I want to apply for a loan", "fields": {}, "language": "en"},
            {"question": "میں قرض کے لیے درخواست دینا چاہتا ہوں۔", "fields": {}, "language": "ur"},
        ]
    },
    {
        "name": "greeting",
        "description": "user is greeting the assistant or making small talk, e.g. hello, salam, how are you, kia haal hai",
        "required_fields": [],
        "func_name": "greeting",
        "examples": [
            {"question": "hello", "fields": {}, "language": "en"},
            {"question": "how are you", "fields": {}, "language": "en"},
            {"question": "salam", "fields": {}, "language": "ur"},
            {"question": "kia haal hai", "fields": {}, "language": "ur"},
            {"question": "السلام علیکم", "fields": {}, "language": "ur"},
        ]
    },
    {
        "name": "unknown",
        "description": "the question does not match any other intent, including personal questions about the assistant or anything unrelated to banking",
        "required_fields": [],
        "func_name": "unknown",
        "examples": [
            {"question": "what is your name", "fields": {}, "language": "en"},
            {"question": "what is today's date?", "fields": {}, "language": "en"},
            {"question": "آج کیا تاریخ ہے؟", "fields": {}, "language": "ur"},
        ]
    },
]
for intent in demo_intents:
    intents.update_one(
        {"name":intent["name"]},
        {"$set":intent,"$unset":{"example_question":"","example_fields":""}},
        upsert=True
    )

print("Seeded",len(demo_intents),"intents:")
for intent in demo_intents:
    print(" ",intent["name"],"-> handler function:",intent["func_name"],"(",len(intent["examples"]),"examples)")
