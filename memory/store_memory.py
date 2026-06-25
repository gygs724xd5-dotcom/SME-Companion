import json
from datetime import datetime
from pathlib import Path


MEMORY_FILE = Path(__file__).with_name("store_memory.json")


def _empty_memory() -> dict:
    return {"stores": {}}


def _store_key(store_name: str) -> str:
    return store_name.strip().lower()


def load_memory() -> dict:
    if not MEMORY_FILE.exists():
        return _empty_memory()

    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_memory()


def save_memory(memory: dict) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(
        json.dumps(memory, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_store_profile(store_name: str) -> dict | None:
    key = _store_key(store_name)
    if not key:
        return None

    return load_memory().get("stores", {}).get(key, {}).get("profile")


def save_store_profile(
    store_name: str,
    store_type: str,
    product: str,
    target_customer: str,
    tone: str,
) -> dict:
    memory = load_memory()
    stores = memory.setdefault("stores", {})
    key = _store_key(store_name)
    stores.setdefault(key, {})

    profile = {
        "store_name": store_name.strip(),
        "store_type": store_type.strip(),
        "product": product.strip(),
        "target_customer": target_customer.strip(),
        "tone": tone.strip(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    stores[key]["profile"] = profile
    stores[key].setdefault("history", [])
    save_memory(memory)
    return profile


def get_content_history(store_name: str, limit: int = 5) -> list[dict]:
    key = _store_key(store_name)
    if not key:
        return []

    history = load_memory().get("stores", {}).get(key, {}).get("history", [])
    return list(reversed(history[-limit:]))


def get_recent_topics(store_name: str, limit: int = 5) -> list[str]:
    return [
        item.get("topic", "")
        for item in get_content_history(store_name, limit=limit)
        if item.get("topic")
    ]


def save_generated_content(
    store_name: str,
    topic: str,
    content_angle: str,
    strategy_name: str,
    markdown: str,
) -> dict:
    memory = load_memory()
    stores = memory.setdefault("stores", {})
    key = _store_key(store_name)
    stores.setdefault(key, {"profile": None, "history": []})

    item = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "content_angle": content_angle,
        "strategy_name": strategy_name,
        "markdown": markdown,
    }
    stores[key].setdefault("history", []).append(item)
    save_memory(memory)
    return item
