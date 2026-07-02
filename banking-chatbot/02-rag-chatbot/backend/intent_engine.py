"""
intent_engine.py
Refactored version of ragimplementationintent.py.
All functions return strings instead of printing, making them API-safe.
"""

from sentence_transformers import SentenceTransformer
import chromadb
import requests
import json
import os

# ---------------------------------------------------------------------------
# Models & vector store (initialised once at import time)
# ---------------------------------------------------------------------------

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.Client()
account_types = chroma_client.create_collection("account_types")

# knowledge.txt lives one directory above this file (project root)
_knowledge_path = os.path.join(os.path.dirname(__file__), "..", "knowledge.txt")
with open(_knowledge_path, "r") as _f:
    _raw = _f.read()

_parts = [p for p in _raw.strip().split("\n") if p.strip()]
_embeddings = [embedding_model.encode(p).tolist() for p in _parts]
_ids = [f"part_{i}" for i in range(len(_parts))]
account_types.add(documents=_parts, embeddings=_embeddings, ids=_ids)

# ---------------------------------------------------------------------------
# Intent definitions (mirrors the original)
# ---------------------------------------------------------------------------

intent_definitions = {
    "check_balance": {
        "description": "user wants to check their account balance",
        "required_fields": ["account_number"],
    },
    "send_money": {
        "description": "user wants to send money or make a transaction to someone",
        "required_fields": ["amount", "account_number", "currency"],
    },
    "check_weather": {
        "description": "user wants to know the current weather",
        "required_fields": ["city"],
    },
    "currency_conversion": {
        "description": "user wants to convert or know an exchange rate between currencies",
        "required_fields": ["amount", "multiplier", "from_currency", "to_currency"],
    },
    "knowledge_base": {
        "description": "user is asking about Abhi's products, services, or account types",
        "required_fields": [],
    },
    "unknown": {
        "description": (
            "the question does not match any other intent, including small talk, "
            "personal questions about the assistant, or anything unrelated to banking"
        ),
        "required_fields": [],
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OLLAMA_URL = "http://localhost:11434/api/chat"
_MODEL = "qwen2.5:3b"


def _ollama(prompt: str) -> str:
    response = requests.post(
        _OLLAMA_URL,
        json={"model": _MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False},
    )
    return response.json()["message"]["content"]


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

def detect_intent(query: str) -> dict:
    intents_as_json = json.dumps(intent_definitions, indent=2)
    prompt = (
        "You are an intent classifier for a banking assistant. "
        "Here are the available intents in JSON format: "
        + intents_as_json
        + "Carefully read the entire question and extract every required field that is mentioned. "
        "Always use standard 3-letter currency codes (e.g. eur, usd, pkr), never full currency names. "
        "Do not do any math yourself. If the user says half, double, or a percentage, "
        "put the raw amount in the amount field and the fraction as a decimal in multiplier (half = 0.5, double = 2). "
        "Do not guess or assume a value for any field the user did not actually mention. "
        "If a field is not mentioned, do not include it in fields at all, leave it out completely. "
        "If the user does not specify what currency the amount is in (e.g. just says a number with no currency mentioned), "
        "do NOT assume USD or any other currency. Leave from_currency out of fields completely so it gets asked. "
        "Note that your audience is Pakistani, so any mention of Ruppee likely means PKR not INR. "
        "Account for spelling mistakes and typos in currency names and locations. "
        "For example, 'dallars' means dollars/usd, 'ruppes' or 'ruppees' means rupees/pkr etc. "
        "If the city name has an obvious typo or misspelling, correct it to the most likely real city name. "
        "For example, 'lahoe' should become 'lahore', 'karchi' should become 'karachi'. "
        'Example 1  User question: what is my balance for account 5521. Response: {"intent": "check_balance", "fields": {"account_number": "5521"}}. '
        'Example 2  User question: send 500 rupees to account 12345. Response: {"intent": "send_money", "fields": {"amount": "500", "account_number": "12345", "currency": "pkr"}}. '
        'Example 3  User question: what is the weather in lahore. Response: {"intent": "check_weather", "fields": {"city": "lahore"}}. '
        'Example 4  User question: I have 5 euros, how much is that in dollars. Response: {"intent": "currency_conversion", "fields": {"amount": "5", "multiplier": "1", "from_currency": "eur", "to_currency": "usd"}}. '
        'Example 5  User question: does abhi have accounts for retirement. Response: {"intent": "knowledge_base", "fields": {}}. '
        'Example 6  User question: what is your name. Response: {"intent": "unknown", "fields": {}}. '
        "Now classify this question, respond ONLY in the same JSON format as above, nothing else. "
        "User question: " + query
    )
    raw = _ollama(prompt).strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Field validators (return error string or None)
# ---------------------------------------------------------------------------

def validate_field(field_name: str, value: str):
    """Return an error message string if invalid, or None if valid."""
    if field_name in ("currency", "to_currency", "from_currency"):
        url = (
            "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest"
            f"/v1/currencies/{value.lower()}.json"
        )
        try:
            resp = requests.get(url, timeout=6)
            if resp.status_code != 200:
                return (
                    "❌ Invalid currency code. Please use a standard 3-letter code "
                    "like **usd**, **pkr**, **eur**."
                )
        except Exception:
            return "❌ Could not validate currency. Please try again."

    if field_name == "account_number":
        if len(value) < 10 or len(value) > 20:
            return "❌ Invalid account number. Please enter a valid account number (10–20 digits)."

    if field_name == "amount":
        try:
            amt = float(value)
            if amt < 0:
                return "❌ Amount cannot be negative."
            if amt > 10_000_000:
                return "❌ Amount too large. Please contact the bank directly for transactions over PKR 10,000,000."
        except ValueError:
            return "❌ Please enter a valid numeric amount."

    if field_name == "city":
        try:
            resp = requests.get(f"https://countries.dev/cities?q={value}", timeout=6)
            if resp.status_code != 200 or not resp.text.strip():
                return "❌ Could not validate city. Please enter a valid city name."
        except Exception:
            return "❌ Could not validate city. Please try again."

    return None  # valid


# ---------------------------------------------------------------------------
# Intent handlers — all return markdown-formatted strings
# ---------------------------------------------------------------------------

def check_balance(fields: dict) -> tuple[str, dict]:
    account_number = fields["account_number"]
    example_balance = 45200.00  # Updated to match mockup
    return (
        f"💰 **Account Balance**\n\n"
        f"Account: `{account_number}`\n\n"
        f"Current Balance: **PKR {example_balance:,.2f}**",
        {
            "type": "balance",
            "balance": example_balance,
            "currency": "PKR",
            "trend": "+4.2%",
            "history": [30000, 32000, 31000, 40000, 38000, 42000, 45200]
        }
    )


def send_money(fields: dict) -> tuple[str, dict]:
    amount = fields["amount"]
    account_number = fields["account_number"]
    currency = fields["currency"].upper()
    return (
        f"✅ **Transaction Successful**\n\n"
        f"Sent **{currency} {float(amount):,.2f}** to account `{account_number}`.",
        {
            "type": "transaction",
            "amount": float(amount),
            "currency": currency,
            "recipient": "Ahmed Khan", # Mock recipient
            "reference": "#TXN-8842-ABHI"
        }
    )


def check_weather(fields: dict) -> tuple[str, dict]:
    city = fields["city"]
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3", timeout=8)
        clean = response.text.encode("ascii", "ignore").decode("ascii").strip()
        return f"🌤 **Weather Update**\n\n{clean}", None
    except Exception:
        return "❌ Could not fetch weather data. Please try again.", None


def currency_conversion(fields: dict) -> tuple[str, dict]:
    amount = float(fields["amount"])
    multiplier = float(fields["multiplier"])
    from_c = fields["from_currency"].lower()
    to_c = fields["to_currency"].lower()

    url = (
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest"
        f"/v1/currencies/{from_c}.json"
    )
    try:
        resp = requests.get(url, timeout=8)
        result = resp.json()
        rates = result[from_c]
        if to_c not in rates:
            return "❌ Could not find that currency pair. Please check the currency codes.", None
        rate = rates[to_c]
    except Exception:
        return "❌ Could not retrieve exchange rates. Please try again.", None

    converted = amount * multiplier * rate
    return (
        f"💱 **Currency Conversion**\n\n"
        f"**{amount * multiplier:,.2f} {from_c.upper()}** = **{converted:,.2f} {to_c.upper()}**\n\n"
        f"Rate: 1 {from_c.upper()} = {rate:.4f} {to_c.upper()}",
        None
    )


def knowledge_base(fields: dict, original_query: str) -> tuple[str, dict]:
    query_embedding = embedding_model.encode(original_query).tolist()
    results = account_types.query(query_embeddings=[query_embedding])
    context = " ".join(results["documents"][0])
    prompt = (
        "You have been provided with a knowledge base. "
        "Use only this to form your response. "
        "If the answer is not in the context, say you don't know. "
        "\n\nContext:\n" + context + "\nQuestion: " + original_query
    )
    answer = _ollama(prompt)
    return f"📚 **ABHI Knowledge Base**\n\n{answer}", None


def unknown(original_query: str, fields: dict) -> tuple[str, dict]:
    return _ollama(original_query), None
