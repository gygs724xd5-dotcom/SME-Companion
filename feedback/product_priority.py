HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"


def _normalize(message: str) -> str:
    return str(message or "").strip().lower()


def _contains_any(message: str, keywords: list[str]) -> bool:
    return any(keyword in message for keyword in keywords)


def calculate_severity(message: str, category: str) -> str:
    normalized = _normalize(message)

    if _contains_any(
        normalized,
        [
            "crash",
            "critical",
            "พัง",
            "เด้ง",
            "ค้าง",
            "ใช้ไม่ได้",
            "กดไม่ได้",
            "เปิดไม่ได้",
            "error",
            "bug",
            "บั๊ก",
            "ข้อมูลหาย",
            "หายหมด",
        ],
    ):
        return SEVERITY_HIGH

    if category in {"Bug", "Performance", "Workflow"}:
        return SEVERITY_MEDIUM

    if category in {"Feature Request", "Export", "POS Integration", "Notification"}:
        return SEVERITY_MEDIUM

    return SEVERITY_LOW


def assign_priority(message: str, category: str, severity: str | None = None) -> str:
    normalized = _normalize(message)
    effective_severity = severity or calculate_severity(message, category)

    if effective_severity == SEVERITY_HIGH:
        return HIGH

    if category == "Bug" and _contains_any(normalized, ["critical", "ใช้ไม่ได้", "กดไม่ได้", "เปิดไม่ได้"]):
        return HIGH

    if category == "Workflow" and _contains_any(
        normalized,
        ["ติด", "ทำต่อไม่ได้", "ไปต่อไม่ได้", "block", "blocker", "ขั้นตอน", "workflow"],
    ):
        return HIGH

    if category in {"Feature Request", "Export", "Notification", "POS Integration"}:
        return MEDIUM

    if category in {"UI", "Dashboard"} and _contains_any(
        normalized,
        ["เล็ก", "สี", "อ่านยาก", "ไม่สวย", "ปุ่ม", "font", "ฟอนต์"],
    ):
        return LOW

    if category in {"UX", "AI Response", "Reports", "Data", "Performance", "Workflow"}:
        return MEDIUM

    return LOW
