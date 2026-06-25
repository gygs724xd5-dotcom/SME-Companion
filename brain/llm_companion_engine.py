import json
import os
from pathlib import Path


DEFAULT_MODEL = "gpt-4.1-mini"


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _api_key() -> str:
    _load_env_file()
    return os.getenv("OPENAI_API_KEY", "").strip()


def is_llm_available() -> bool:
    return bool(_api_key())


def _messages(user_message: str, context: dict) -> list[dict]:
    context_json = json.dumps(context or {}, ensure_ascii=False, separators=(",", ":"))
    system_prompt = (
        "คุณคือ SME Companion เวอร์ชัน AI communication layer สำหรับเจ้าของ SME ไทย "
        "หน้าที่ของคุณคืออธิบายคำแนะนำจาก context ให้ชัด อบอุ่น และเหมือน business coach "
        "ห้ามคิดข้อมูลร้าน ยอดขาย ลูกค้า หรือเหตุการณ์ใหม่เอง "
        "ห้ามเปลี่ยน reasoning หรือคำแนะนำหลักของ engine "
        "ถ้าข้อมูลไม่พอ ให้บอกว่าข้อมูลยังไม่พอและแนะนำวิธีเก็บข้อมูลเพิ่ม "
        "ตอบเป็นภาษาไทยเท่านั้น อธิบายเหตุผล และให้ action ที่ทำได้วันนี้"
    )
    user_prompt = (
        "ข้อความเจ้าของร้าน:\n"
        f"{user_message}\n\n"
        "บริบทจาก deterministic business engines:\n"
        f"{context_json}\n\n"
        "เขียนคำตอบแบบ business coach โดยยึด context เท่านั้น"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def generate_llm_response(user_message, context):
    """Generate a Thai coaching response using OpenAI as a communication layer.

    Returns None when the API key, SDK, or API call is unavailable so callers can
    fall back to deterministic chat without breaking the local app.
    """
    api_key = _api_key()
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    try:
        response = client.chat.completions.create(
            model=model,
            messages=_messages(str(user_message or ""), context or {}),
            temperature=0.4,
            max_tokens=700,
        )
    except Exception:
        return None

    message = response.choices[0].message.content if response.choices else None
    return message.strip() if message else None
