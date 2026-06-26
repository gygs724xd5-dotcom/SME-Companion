import json
import os
from pathlib import Path


DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _api_key() -> str:
    _load_env_file()
    return os.getenv("DEEPSEEK_API_KEY", "").strip()


def is_available() -> bool:
    return bool(_api_key())


def has_api_key() -> bool:
    return bool(_api_key())


def _normalize_messages(messages, context=None) -> list[dict]:
    if isinstance(messages, list):
        return messages

    context_json = json.dumps(context or {}, ensure_ascii=False, separators=(",", ":"))
    return [
        {
            "role": "system",
            "content": (
                "คุณคือ SME Companion AI สำหรับเจ้าของร้านไทย "
                "ตอบเป็นภาษาไทยเท่านั้น เป็นกันเอง กระชับ เหมือนผู้ช่วยเจ้าของร้าน "
                "คำถามของผู้ใช้สำคัญกว่าบริบทธุรกิจเสมอ "
                "ใช้ข้อมูลร้านเฉพาะเมื่อบริบทระบุว่า include_business_context เป็น true "
                "ถ้าเป็นโหมด startup_advisor ห้ามอ้างอิงร้านเดโม ยอดขาย คะแนน ความเสี่ยง หรือแดชบอร์ด "
                "ห้ามแต่งข้อมูลร้าน ยอดขาย ลูกค้า หรือเหตุการณ์ใหม่เอง "
                "ไม่ยัดแดชบอร์ดหรือศัพท์เทคนิคภาษาอังกฤษ "
                "ตอบให้กระชับ เหมาะกับหน้าจอมือถือ ถ้าผู้ใช้ไม่ได้ขอรายละเอียด ให้ตอบไม่เกิน 5-8 บรรทัด "
                "ถ้าไม่แน่ใจ ให้ถามกลับ 1 คำถาม"
            ),
        },
        {
            "role": "user",
            "content": (
                f"คำถามจากเจ้าของร้าน:\n{messages}\n\n"
                f"บริบทของร้าน:\n{context_json}\n\n"
                "โปรดตอบเป็นภาษาไทยโดยยึดบริบทนี้ และอย่าเปิดเผยชื่อระบบภายในหรือป้ายภาษาอังกฤษ"
            ),
        },
    ]


def generate_response(messages, context=None) -> str | None:
    api_key = _api_key()
    if not api_key:
        print("DeepSeek response fail")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("DeepSeek response fail")
        return None

    client = OpenAI(api_key=api_key, base_url=DEFAULT_BASE_URL)
    model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    try:
        response = client.chat.completions.create(
            model=model,
            messages=_normalize_messages(messages, context),
            temperature=0.7,
            max_tokens=500,
        )
    except Exception as exc:
        print(f"DeepSeek API Error: {exc.__class__.__name__}")
        print("DeepSeek response fail")
        return None

    message = response.choices[0].message.content if response.choices else None
    if not message:
        print("DeepSeek response fail")
        return None

    print("DeepSeek response success")
    return message.strip()
