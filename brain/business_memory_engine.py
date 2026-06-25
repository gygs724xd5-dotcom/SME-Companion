import json
from datetime import datetime
from pathlib import Path


MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "business_memory.json"

VALID_EVENT_TYPES = {
    "chat_question",
    "sales_problem",
    "content_generated",
    "campaign_generated",
    "diagnosis",
    "goal_update",
}


def _empty_memory() -> dict:
    return {"stores": {}}


def _store_key(store_name: str) -> str:
    return str(store_name or "").strip().lower()


def _load_all_memory() -> dict:
    if not MEMORY_FILE.exists():
        return _empty_memory()

    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_memory()

    if not isinstance(data, dict):
        return _empty_memory()
    data.setdefault("stores", {})
    return data


def _save_all_memory(memory: dict) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(
        json.dumps(memory, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_business_event(
    store_name,
    event_type,
    summary,
    metadata=None,
) -> dict | None:
    """Append a deterministic business event to local JSON memory."""
    key = _store_key(store_name)
    if not key:
        return None

    normalized_event_type = str(event_type or "").strip()
    if normalized_event_type not in VALID_EVENT_TYPES:
        normalized_event_type = "chat_question"

    memory = _load_all_memory()
    stores = memory.setdefault("stores", {})
    store = stores.setdefault(
        key,
        {
            "store_name": str(store_name or "").strip(),
            "events": [],
        },
    )
    store["store_name"] = str(store_name or "").strip()

    event = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "event_type": normalized_event_type,
        "summary": str(summary or "").strip(),
        "metadata": metadata or {},
    }
    store.setdefault("events", []).append(event)
    _save_all_memory(memory)
    return event


def load_business_memory(store_name) -> dict:
    key = _store_key(store_name)
    if not key:
        return {"store_name": "", "events": []}

    store = _load_all_memory().get("stores", {}).get(key)
    if not store:
        return {"store_name": str(store_name or "").strip(), "events": []}

    store.setdefault("events", [])
    return store


def get_recent_business_events(store_name, limit=5) -> list[dict]:
    try:
        safe_limit = max(1, int(limit))
    except (TypeError, ValueError):
        safe_limit = 5

    events = load_business_memory(store_name).get("events", [])
    return list(reversed(events[-safe_limit:]))
