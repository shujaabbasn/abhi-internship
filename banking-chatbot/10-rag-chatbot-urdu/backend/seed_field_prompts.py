from db import field_prompts_collection as field_prompts

demo_field_prompts=[
    {
        "field_name": "account_number",
        "description": "the user's bank account number",
        "english": "Please provide your account number.",
        "urdu": "براہ کرم اپنا اکاؤنٹ نمبر بتائیں۔"
    },
    {
        "field_name": "from_account",
        "description": "the account number the user wants to send money from",
        "english": "Please provide your from account.",
        "urdu": "براہ کرم وہ اکاؤنٹ نمبر بتائیں جہاں سے آپ رقم بھیجنا چاہتے ہیں۔"
    },
    {
        "field_name": "to_account",
        "description": "the account number",
        "english": "Please provide your to account.",
        "urdu": "براہ کرم اکاؤنٹ نمبر بتائیں۔"
    },
    {
        "field_name": "recipient_account",
        "description": "the recipient's account number that the user wants to send money to",
        "english": "Please provide your recipient account.",
        "urdu": "براہ کرم وصول کنندہ کا اکاؤنٹ نمبر بتائیں۔"
    },
    {
        "field_name": "amount",
        "description": "the amount of money involved in the transaction",
        "english": "Please provide your amount.",
        "urdu": "براہ کرم رقم بتائیں۔"
    },
    {
        "field_name": "currency",
        "description": "the currency of the amount, as a standard 3-letter code like usd or pkr",
        "english": "Please provide your currency.",
        "urdu": "براہ کرم کرنسی بتائیں، مثلاً یو ایس ڈی یا پی کے آر۔"
    },
    {
        "field_name": "from_currency",
        "description": "the currency to convert from, as a standard 3-letter code",
        "english": "Please provide your from currency.",
        "urdu": "براہ کرم وہ کرنسی بتائیں جس سے تبدیل کرنا ہے۔"
    },
    {
        "field_name": "to_currency",
        "description": "the currency to convert to, as a standard 3-letter code",
        "english": "Please provide your to currency.",
        "urdu": "براہ کرم وہ کرنسی بتائیں جس میں تبدیل کرنا ہے۔"
    },
    {
        "field_name": "city",
        "description": "the city name to check the weather for",
        "english": "Please provide your city.",
        "urdu": "براہ کرم شہر کا نام بتائیں۔"
    },
    {
        "field_name": "wants_info",
        "description": "whether the user wants to hear about the bank's loan options, a yes or no answer",
        "english": "Would you like to hear about the loan options we offer? (yes/no)",
        "urdu": "کیا آپ ہمارے قرض کے آپشنز کے بارے میں جاننا چاہیں گے؟ (ہاں یا نہیں)"
    },
    {
        "field_name": "wants_contact",
        "description": "whether the user is interested in a loan and wants the bank's team to contact them, a yes or no answer",
        "english": "Are you interested in a loan? Would you like our team to contact you? (yes/no)",
        "urdu": "کیا آپ کو قرض میں دلچسپی ہے؟ کیا ہماری ٹیم آپ سے رابطہ کرے؟ (ہاں یا نہیں)"
    },
]
for field_prompt in demo_field_prompts:
    field_prompts.update_one(
        {"field_name":field_prompt["field_name"]},
        {"$set":field_prompt},
        upsert=True
    )

print("Seeded",len(demo_field_prompts),"field prompts:")
for field_prompt in demo_field_prompts:
    print(" ",field_prompt["field_name"])