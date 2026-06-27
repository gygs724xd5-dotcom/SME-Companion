from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


AUTH_DIR = Path(__file__).resolve().parent.parent / "data" / "auth"
USERS_FILE = AUTH_DIR / "users.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_owner_id(value: str | None) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum() or ch in {"-", "_", "."})[:80]


def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {"users": {}}
    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"users": {}}
    if not isinstance(data, dict):
        return {"users": {}}
    data.setdefault("users", {})
    return data


def _save_users(data: dict) -> None:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", str(password or "").encode("utf-8"), salt.encode("utf-8"), 120000).hex()


def has_users() -> bool:
    return bool(_load_users().get("users"))


def normalize_owner_id(value: str | None) -> str:
    return _normalize_owner_id(value)


def create_user(owner_id: str, password: str) -> dict:
    owner = _normalize_owner_id(owner_id)
    if not owner or not password:
        return {"ok": False, "error": "missing_credentials"}
    data = _load_users()
    if owner in data["users"]:
        return {"ok": False, "error": "user_exists"}
    salt = secrets.token_hex(16)
    data["users"][owner] = {
        "owner_id": owner,
        "password_hash": _password_hash(password, salt),
        "salt": salt,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _save_users(data)
    return {"ok": True, "owner_id": owner}


def update_user_profile(owner_id: str, store_id: str | None = None, store_name: str | None = None, username: str | None = None) -> dict:
    owner = _normalize_owner_id(owner_id)
    data = _load_users()
    user = (data.get("users") or {}).get(owner)
    if not owner or not user:
        return {"ok": False, "error": "user_not_found"}

    if store_id is not None:
        normalized_store_id = _normalize_owner_id(store_id)
        if normalized_store_id:
            user["store_id"] = normalized_store_id
    if store_name is not None:
        clean_store_name = str(store_name or "").strip()
        if clean_store_name:
            user["store_name"] = clean_store_name
    if username is not None:
        normalized_username = _normalize_owner_id(username)
        if normalized_username:
            user["username"] = normalized_username
    user["updated_at"] = _now_iso()
    _save_users(data)
    return {"ok": True, "owner_id": owner}


def authenticate(owner_id: str, password: str) -> dict:
    owner = _normalize_owner_id(owner_id)
    user = (_load_users().get("users") or {}).get(owner)
    if not user:
        return {"ok": False, "error": "invalid_credentials"}
    expected = user.get("password_hash") or ""
    actual = _password_hash(password, user.get("salt") or "")
    if not hmac.compare_digest(expected, actual):
        return {"ok": False, "error": "invalid_credentials"}
    store_id = _normalize_owner_id(user.get("store_id") or owner)
    return {
        "ok": True,
        "owner_id": owner,
        "username": user.get("username") or owner,
        "store_id": store_id,
        "store_name": user.get("store_name") or store_id,
    }


def session_for_owner(owner_id: str, store_id: str | None = None, store_name: str | None = None, username: str | None = None) -> dict:
    owner = _normalize_owner_id(owner_id)
    selected_store = _normalize_owner_id(store_id or owner)
    return {
        "authenticated": bool(owner),
        "owner_id": owner,
        "username": username or owner,
        "store_id": selected_store,
        "store_name": store_name or selected_store,
        "login_at": _now_iso(),
    }
