import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


STORE_PROFILE_DIR = Path(__file__).resolve().parent.parent / "data" / "store_profile"
STORE_PROFILE_FILE = STORE_PROFILE_DIR / "active_store.json"

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization",
    "secret",
)


def ensure_store_profile_dir() -> None:
    STORE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def save_store_profile(store_data: dict) -> None:
    if not isinstance(store_data, dict):
        return
    if store_data.get("store_source") != "manual":
        return

    ensure_store_profile_dir()
    clean_data = _remove_sensitive_values(deepcopy(store_data))
    clean_data["store_source"] = "manual"
    clean_data.setdefault("created_at", _now_iso())
    clean_data["updated_at"] = _now_iso()
    STORE_PROFILE_FILE.write_text(
        json.dumps(clean_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_store_profile() -> dict | None:
    if not STORE_PROFILE_FILE.exists():
        return None

    try:
        data = json.loads(STORE_PROFILE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict):
        return None
    if data.get("store_source") != "manual":
        return None
    if not isinstance(data.get("store_profile"), dict) or not data["store_profile"]:
        return None
    return _remove_sensitive_values(data)


def clear_store_profile() -> None:
    try:
        STORE_PROFILE_FILE.unlink(missing_ok=True)
    except OSError:
        return


def has_store_profile() -> bool:
    return load_store_profile() is not None
