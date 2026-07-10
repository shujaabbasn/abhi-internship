from pymongo import MongoClient

client=MongoClient("mongodb://localhost:27017")
db=client["abhi_bank"]
intents=db["intents"]

demo_intents=[
    {
        "name": "check_balance",
        "description": "user wants to check their account balance",
        "required_fields": ["account_number"],
        "func_name": "check_balance",
        "example_question": "what is my balance for account 5521",
        "example_fields": {"account_number": "5521"}
    },
    {
        "name": "send_money",
        "description": "user wants to send or transfer money to any account",
        "required_fields": ["amount", "currency", "from_account", "recipient_account"],
        "func_name": "send_money",
        "example_question": "send 500 rupees from account 1234567890 to account 12345",
        "example_fields": {"amount": "500", "currency": "pkr", "from_account": "1234567890", "recipient_account": "12345"}
    },
    {
        "name": "check_weather",
        "description": "user wants to know the current weather",
        "required_fields": ["city"],
        "func_name": "check_weather",
        "example_question": "what is the weather in lahore",
        "example_fields": {"city": "lahore"}
    },
    {
        "name": "currency_conversion",
        "description": "user wants to convert or know an exchange rate between currencies",
        "required_fields": ["amount", "multiplier", "from_currency", "to_currency"],
        "func_name": "currency_conversion",
        "example_question": "I have 5 euros, how much is that in dollars",
        "example_fields": {"amount": "5", "multiplier": "1", "from_currency": "eur", "to_currency": "usd"}
    },
    {
        "name": "knowledge_base",
        "description": "user is asking about Abhi's products, services, account types, or loan types (informational, not an active request)",
        "required_fields": [],
        "func_name": "knowledge_base",
        "example_question": "what loan types does abhi offer",
        "example_fields": {}
    },
    {
        "name": "request_loan",
        "description": "user wants to actively apply for or request a loan",
        "required_fields": ["wants_info"],
        "func_name": "request_loan",
        "example_question": "I want to apply for a loan",
        "example_fields": {}
    },
    {
        "name": "unknown",
        "description": "the question does not match any other intent, including small talk, personal questions about the assistant or anything unrelated to banking",
        "required_fields": [],
        "func_name": "unknown",
        "example_question": "what is your name",
        "example_fields": {}
    },
]
for intent in demo_intents:
    intents.update_one(
        {"name":intent["name"]},
        {"$set":intent},
        upsert=True
    )

print("Seeded",len(demo_intents),"intents:")
for intent in demo_intents:
    print(" ",intent["name"],"-> handler function:",intent["func_name"])