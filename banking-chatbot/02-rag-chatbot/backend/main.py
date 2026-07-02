"""
main.py — FastAPI entry point for the ABHI Banking Assistant.

Run with:
    uvicorn main:app --reload --port 8000
"""

import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from session_store import get_session, create_session, update_session, clear_session
from intent_engine import (
    detect_intent,
    intent_definitions,
    validate_field,
    check_balance,
    send_money,
    check_weather,
    currency_conversion,
    knowledge_base,
    unknown,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="ABHI Banking Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    intent: Optional[str] = None
    data: Optional[dict] = None
    awaiting_field: Optional[str] = None
    complete: bool = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIELD_LABELS = {
    "account_number": "account number",
    "amount": "amount",
    "currency": "currency (e.g. pkr, usd, eur)",
    "from_currency": "source currency (e.g. usd, eur)",
    "to_currency": "target currency (e.g. pkr, usd)",
    "city": "city name",
    "multiplier": "multiplier (e.g. 1 for full, 0.5 for half)",
}


def _ask_for_field(field_name: str) -> str:
    label = FIELD_LABELS.get(field_name, field_name.replace("_", " "))
    return f"Please provide your **{label}**:"


def _execute_intent(intent: str, fields: dict, original_query: str) -> tuple[str, dict]:
    if intent == "check_balance":
        return check_balance(fields)
    elif intent == "send_money":
        return send_money(fields)
    elif intent == "check_weather":
        return check_weather(fields)
    elif intent == "currency_conversion":
        return currency_conversion(fields)
    elif intent == "knowledge_base":
        return knowledge_base(fields, original_query)
    else:
        return unknown(original_query, fields)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "model": "qwen2.5:3b"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    message = req.message.strip()

    session = get_session(session_id)

    # ------------------------------------------------------------------
    # Case 1: No active session → detect intent from scratch
    # ------------------------------------------------------------------
    if session is None or session["intent"] is None:
        session = create_session(session_id)

        try:
            parsed = detect_intent(message)
        except Exception as e:
            return ChatResponse(
                reply=f"❌ Sorry, I couldn't understand that. Could you rephrase? ({e})",
                session_id=session_id,
                complete=True,
            )

        intent = parsed.get("intent", "unknown")
        fields = parsed.get("fields", {})

        if intent not in intent_definitions:
            intent = "unknown"

        required = intent_definitions[intent]["required_fields"]
        missing = [
            f for f in required
            if f not in fields or fields[f] == "" or fields[f] is None
        ]

        update_session(session_id, {
            "intent": intent,
            "fields": fields,
            "missing_fields": missing.copy(),
            "original_query": message,
        })

        if missing:
            first = missing[0]
            update_session(session_id, {"awaiting_field": first})
            return ChatResponse(
                reply=_ask_for_field(first),
                session_id=session_id,
                intent=intent,
                awaiting_field=first,
                complete=False,
            )

        # All fields present — execute immediately
        result_text, data = _execute_intent(intent, fields, message)
        clear_session(session_id)
        return ChatResponse(
            reply=result_text,
            session_id=session_id,
            intent=intent,
            data=data,
            complete=True,
        )

    # ------------------------------------------------------------------
    # Case 2: Session is live, awaiting a missing field
    # ------------------------------------------------------------------
    session = get_session(session_id)
    awaiting = session["awaiting_field"]
    fields = session["fields"]
    missing = session["missing_fields"]
    intent = session["intent"]
    original_query = session["original_query"]

    # Validate the provided value
    error = validate_field(awaiting, message)
    if error:
        return ChatResponse(
            reply=error + "\n\n" + _ask_for_field(awaiting),
            session_id=session_id,
            intent=intent,
            awaiting_field=awaiting,
            complete=False,
        )

    # Save the valid value
    fields[awaiting] = message
    missing.remove(awaiting)

    if missing:
        next_field = missing[0]
        update_session(session_id, {
            "fields": fields,
            "missing_fields": missing,
            "awaiting_field": next_field,
        })
        return ChatResponse(
            reply=_ask_for_field(next_field),
            session_id=session_id,
            intent=intent,
            awaiting_field=next_field,
            complete=False,
        )

    # All fields now collected — execute
    update_session(session_id, {"fields": fields, "missing_fields": []})
    result_text, data = _execute_intent(intent, fields, original_query)
    clear_session(session_id)
    return ChatResponse(
        reply=result_text,
        session_id=session_id,
        intent=intent,
        data=data,
        complete=True,
    )
