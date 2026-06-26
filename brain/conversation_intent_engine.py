GREETING = "GREETING"
GENERAL_CHAT = "GENERAL_CHAT"
START_BUSINESS = "START_BUSINESS"
BUSINESS_ANALYSIS = "BUSINESS_ANALYSIS"
MARKETING = "MARKETING"
CONTENT = "CONTENT"
SALES = "SALES"
CUSTOMER_RETENTION = "CUSTOMER_RETENTION"
FOLLOW_UP = "FOLLOW_UP"
OTHER = "OTHER"

BUSINESS_CONTEXT_INTENTS = {
    BUSINESS_ANALYSIS,
    MARKETING,
    CONTENT,
    SALES,
    CUSTOMER_RETENTION,
}

BUSINESS_INSIGHT_KEYWORDS = [
    "วิเคราะห์",
    "คะแนน",
    "สุขภาพธุรกิจ",
    "ดูภาพรวม",
    "ปัญหาร้าน",
]


def _normalize(message: str) -> str:
    return str(message or "").strip().lower()


def _contains_any(message: str, keywords: list[str]) -> bool:
    return any(keyword in message for keyword in keywords)


def detect_conversation_intent(user_message: str) -> str:
    message = _normalize(user_message)
    if not message:
        return OTHER

    if message in {"สวัสดี", "หวัดดี", "ไง"} or _contains_any(message, ["สวัสดีครับ", "สวัสดีค่ะ"]):
        return GREETING

    if message in {"ไม่ใช่", "ไม่", "พูดใหม่"} or _contains_any(message, ["หมายถึง", "ไม่ใช่แบบนั้น", "ไม่เอา"]):
        return FOLLOW_UP

    if _contains_any(message, ["เปิดร้าน", "เริ่มร้าน", "เริ่มธุรกิจ", "จะขาย", "อยากขาย", "เริ่มขาย"]):
        return START_BUSINESS

    if _contains_any(message, ["โพสต์", "คอนเทนต์", "แคปชั่น"]):
        return CONTENT

    if _contains_any(message, ["โปร", "โปรโมชั่น", "โปรโมชัน"]):
        return MARKETING

    if _contains_any(message, ["ลูกค้ากลับมา", "ซื้อซ้ำ", "รักษาลูกค้า", "ลูกค้าเก่า"]):
        return CUSTOMER_RETENTION

    if _contains_any(message, ["ยอดตก", "ยอดขาย", "ขายดี", "เพิ่มยอด", "ปิดการขาย"]):
        return SALES

    if _contains_any(message, ["ร้านนี้", "วิเคราะห์", "ควรทำอะไรต่อ", "สุขภาพธุรกิจ", "ดูภาพรวม", "ปัญหาร้าน"]):
        return BUSINESS_ANALYSIS

    if _contains_any(message, ["คุย", "ถาม", "ช่วย", "คืออะไร"]):
        return GENERAL_CHAT

    return OTHER


def get_conversation_mode(intent: str) -> str:
    if intent in {GREETING, GENERAL_CHAT, FOLLOW_UP, OTHER}:
        return "casual"
    if intent == START_BUSINESS:
        return "startup_advisor"
    if intent in {CONTENT, MARKETING, SALES, CUSTOMER_RETENTION}:
        return "business_advisor"
    if intent == BUSINESS_ANALYSIS:
        return "business_analysis"
    return "casual"


def should_use_business_context(intent: str) -> bool:
    return intent in BUSINESS_CONTEXT_INTENTS


def should_show_business_insights(intent: str, user_message: str) -> bool:
    message = _normalize(user_message)
    return intent == BUSINESS_ANALYSIS and _contains_any(message, BUSINESS_INSIGHT_KEYWORDS)
