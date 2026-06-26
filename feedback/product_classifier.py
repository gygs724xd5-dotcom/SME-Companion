from datetime import datetime, timezone
from uuid import uuid4

from feedback.product_priority import assign_priority, calculate_severity


SUPPORTED_CATEGORIES = {
    "UI",
    "UX",
    "Performance",
    "Bug",
    "Feature Request",
    "AI Response",
    "Dashboard",
    "Reports",
    "Export",
    "Notification",
    "POS Integration",
    "Workflow",
    "Data",
    "Other",
}


def _normalize(message: str) -> str:
    return str(message or "").strip().lower()


def _contains_any(message: str, keywords: list[str]) -> bool:
    return any(keyword in message for keyword in keywords)


def classify_product_feedback(message: str) -> dict:
    normalized = _normalize(message)

    category_rules = [
        ("POS Integration", ["pos", "พีโอเอส", "sync pos", "ซิงก์ pos", "เชื่อม pos"]),
        ("Export", ["export", "ส่งออก", "ดาวน์โหลด", "excel", "csv", "pdf"]),
        ("Dashboard", ["dashboard", "แดชบอร์ด", "ภาพรวม", "กราฟ", "ตัวเลข"]),
        ("Reports", ["report", "reports", "รายงาน", "รีพอร์ต"]),
        ("Notification", ["notification", "แจ้งเตือน", "line notify", "ไลน์"]),
        ("Performance", ["โหลดช้า", "ช้า", "หน่วง", "ค้าง", "lag", "slow", "performance"]),
        ("Bug", ["bug", "บั๊ก", "พัง", "error", "กดไม่ได้", "ใช้ไม่ได้", "เปิดไม่ได้", "หาย", "crash", "เด้ง"]),
        ("AI Response", ["ai", "คำตอบ", "ตอบยาว", "ตอบสั้น", "ตอบไม่ตรง", "chat ยาว", "แชทยาว"]),
        ("Workflow", ["workflow", "ขั้นตอน", "หลายขั้น", "ทำต่อไม่ได้", "ไปต่อไม่ได้", "ติดขั้นตอน"]),
        ("Data", ["ข้อมูล", "data", "ยอดไม่ตรง", "ตัวเลขไม่ตรง", "บันทึก"]),
        ("Feature Request", ["อยากให้มี", "อยากได้", "น่าจะมี", "เพิ่ม", "ควรมี", "ถ้ามี", "feature", "ฟีเจอร์"]),
        ("UI", ["ui", "ปุ่ม", "สี", "font", "ฟอนต์", "เล็ก", "ใหญ่", "ไม่สวย", "อ่านยาก"]),
        ("UX", ["ux", "งง", "ใช้ยาก", "หายาก", "มือถือใช้ยาก", "ไม่เข้าใจ", "เมนู"]),
    ]

    category = "Other"
    for candidate, keywords in category_rules:
        if _contains_any(normalized, keywords):
            category = candidate
            break

    severity = calculate_severity(message, category)
    priority = assign_priority(message, category, severity)

    return {
        "category": category if category in SUPPORTED_CATEGORIES else "Other",
        "severity": severity,
        "priority": priority,
        "summary": summarize_feedback_message(message, category),
    }


def summarize_feedback_message(message: str, category: str) -> str:
    clean_message = " ".join(str(message or "").strip().split())
    if not clean_message:
        return f"{category} feedback"
    return clean_message[:120]


def build_product_feedback_record(message: str, conversation_id: str | None = None) -> dict:
    classification = classify_product_feedback(message)
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid4()),
        "timestamp": timestamp,
        "conversation_id": conversation_id,
        "category": classification["category"],
        "severity": classification["severity"],
        "priority": classification["priority"],
        "raw_message": str(message or "").strip(),
        "summary": classification["summary"],
        "status": "open",
    }
