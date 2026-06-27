import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCOPED_STORES_DIR = DATA_DIR / "stores"

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization",
    "secret",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_id(value: str | None) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum() or ch in {"-", "_", "."})[:80]


def _store_id_from_profile(store_data: dict) -> str:
    profile = (store_data or {}).get("store_profile") or {}
    return _safe_id(
        (store_data or {}).get("store_id")
        or profile.get("store_id")
        or profile.get("store_name")
        or "default"
    )


def _scoped_store_file(owner_id: str | None, store_id: str | None = None, store_data: dict | None = None) -> Path | None:
    owner = _safe_id(owner_id)
    if not owner:
        return None
    selected_store = _safe_id(store_id) or _store_id_from_profile(store_data or {})
    if not selected_store:
        return None
    return SCOPED_STORES_DIR / owner / selected_store / "store_profile.json"


def _remove_sensitive_values(value):
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
                continue
            clean[key] = _remove_sensitive_values(item)
        return clean
    if isinstance(value, list):
        return [_remove_sensitive_values(item) for item in value]
    return value


def save_store_profile(store_data: dict, owner_id: str | None = None, store_id: str | None = None) -> None:
    if not isinstance(store_data, dict):
        return
    if store_data.get("store_source") != "manual":
        return
    profile_file = _scoped_store_file(owner_id, store_id, store_data)
    if profile_file is None:
        return

    profile_file.parent.mkdir(parents=True, exist_ok=True)
    clean_data = _remove_sensitive_values(deepcopy(store_data))
    clean_data["store_source"] = "manual"
    clean_data["owner_id"] = _safe_id(owner_id)
    clean_data["store_id"] = _safe_id(store_id) or _store_id_from_profile(clean_data)
    clean_data.setdefault("created_at", _now_iso())
    clean_data["updated_at"] = _now_iso()
    profile_file.write_text(
        json.dumps(clean_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_store_profile(owner_id: str | None = None, store_id: str | None = None) -> dict | None:
    profile_file = _scoped_store_file(owner_id, store_id)
    if profile_file is None:
        return None
    if not profile_file.exists():
        return None

    try:
        data = json.loads(profile_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict):
        return None
    if data.get("store_source") != "manual":
        return None
    if _safe_id(data.get("owner_id")) != _safe_id(owner_id):
        return None
    if _safe_id(data.get("store_id")) != _safe_id(store_id):
        return None
    if not isinstance(data.get("store_profile"), dict) or not data["store_profile"]:
        return None
    return _remove_sensitive_values(data)


def clear_store_profile(owner_id: str | None = None, store_id: str | None = None) -> None:
    profile_file = _scoped_store_file(owner_id, store_id)
    if profile_file is None:
        return
    try:
        profile_file.unlink(missing_ok=True)
    except OSError:
        return


def has_store_profile(owner_id: str | None = None, store_id: str | None = None) -> bool:
    return load_store_profile(owner_id, store_id) is not None
