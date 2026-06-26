from datetime import datetime, timezone
from uuid import uuid4


def _normalize(message: str) -> str:
    return str(message or "").strip().lower()


def _contains_any(message: str, keywords: list[str]) -> bool:
    return any(keyword in message for keyword in keywords)


def detect_feedback_category(message: str) -> str:
    normalized = _normalize(message)

    category_rules = [
        ("dashboard", ["dashboard", "แดชบอร์ด", "ภาพรวม", "กราฟ", "ตัวเลข"]),
        ("chat", ["แชท", "chat", "คุย"]),
        ("ai_response", ["ai", "ตอบยาว", "ตอบสั้น", "ตอบไม่ตรง", "ไม่เข้าใจ"]),
        ("content_generator", ["โพสต์", "คอนเทนต์", "caption", "แคปชั่น"]),
        ("onboarding", ["เริ่มใช้", "สมัคร", "สร้างร้าน", "onboarding"]),
        ("notification", ["แจ้งเตือน", "notification", "line"]),
        ("bug", ["error", "พัง", "กดไม่ได้", "bug", "บั๊ก"]),
        ("pricing", ["ราคา", "แพ็กเกจ", "จ่ายเงิน"]),
        ("feature_request", ["อยากให้มี", "เพิ่ม", "feature", "ฟีเจอร์"]),
    ]

    for category, keywords in category_rules:
        if _contains_any(normalized, keywords):
            return category
    return "general"


def detect_feedback_priority(message: str) -> str:
    normalized = _normalize(message)
    if _contains_any(normalized, ["พัง", "ใช้ไม่ได้", "กดไม่ได้", "error", "บั๊ก", "หาย", "ไม่ขึ้น"]):
        return "high"
    if _contains_any(normalized, ["อ่านยาก", "งง", "ไม่เข้าใจ", "ตอบไม่ตรง", "ใช้ยาก"]):
        return "medium"
    return "low"


def is_feedback_too_vague(message: str) -> bool:
    normalized = _normalize(message)
    return normalized in {"ตรงนี้งง", "ใช้ยาก", "ปรับหน่อย"}


def build_feedback_record(
    message,
    category,
    priority,
    store_type=None,
    store_name=None,
    page="chat",
    previous_user_message=None,
    assistant_reply=None,
    app_version="V1.9.5",
):
    return {
        "id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app_version": app_version,
        "page": page,
        "store_type": store_type,
        "store_name": store_name,
        "category": category,
        "priority": priority,
        "message": str(message or "").strip(),
        "previous_user_message": previous_user_message,
        "assistant_reply": assistant_reply,
    }


def build_feedback_acknowledgement(category, priority, needs_clarification=False):
    if needs_clarification:
        return "ขอบคุณครับ  ขอถามเพิ่มนิดเดียว ปัญหานี้เกิดที่หน้าไหนครับ เช่น Dashboard, Chat หรือหน้าสร้างโพสต์?"

    if priority == "high":
        return "ขอบคุณมากครับ  ผมบันทึกปัญหานี้ไว้ให้ทีมพัฒนาแล้ว จะให้ทีมดูเป็นลำดับสำคัญครับ"

    if category == "feature_request":
        return "ขอบคุณมากครับ  ผมบันทึกข้อเสนอแนะนี้ไว้ให้ทีมพัฒนาแล้ว"

    return "ขอบคุณมากครับ  ผมบันทึกข้อเสนอแนะนี้ไว้ให้ทีมพัฒนาแล้ว"
