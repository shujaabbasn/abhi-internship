from typing import Dict, Any, Optional

# In-memory session store — keyed by session_id
sessions: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return sessions.get(session_id)


def create_session(session_id: str) -> Dict[str, Any]:
    sessions[session_id] = {
        "intent": None,
        "fields": {},
        "missing_fields": [],
        "awaiting_field": None,
        "original_query": None,
    }
    return sessions[session_id]


def update_session(session_id: str, data: Dict[str, Any]):
    if session_id in sessions:
        sessions[session_id].update(data)


def clear_session(session_id: str):
    """Reset a session to its initial blank state (keep it alive for next turn)."""
    if session_id in sessions:
        sessions[session_id] = {
            "intent": None,
            "fields": {},
            "missing_fields": [],
            "awaiting_field": None,
            "original_query": None,
        }
