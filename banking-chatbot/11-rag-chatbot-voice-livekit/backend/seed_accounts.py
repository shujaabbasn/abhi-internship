from db import accounts_collection as accounts
demo_accounts=[
    {"account_number":"1234567890","balance":45200.00},
    {"account_number":"9876543210","balance":12000.00}
]
for account in demo_accounts:
    result=accounts.update_one(
        {"account_number":account["account_number"]},
        {"$set":{"balance":account["balance"]}},
        upsert=True
    )
    if result.matched_count==0:
        print("Warning: Incorrect account number! (",account["account_number"],") does not exist.")
    else:
        print("Account",account["account_number"],"updated successfully.")