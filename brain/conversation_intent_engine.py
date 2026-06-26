GREETING = "GREETING"
GENERAL_CHAT = "GENERAL_CHAT"
START_BUSINESS = "START_BUSINESS"
BUSINESS_ANALYSIS = "BUSINESS_ANALYSIS"
MARKETING = "MARKETING"
CONTENT = "CONTENT"
SALES = "SALES"
CUSTOMER_RETENTION = "CUSTOMER_RETENTION"
PRODUCT_FEEDBACK = "PRODUCT_FEEDBACK"
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
    if intent == PRODUCT_FEEDBACK:
        return "product_feedback"
    return "casual"


def should_use_business_context(intent: str) -> bool:
    return intent in BUSINESS_CONTEXT_INTENTS


def should_show_business_insights(intent: str, user_message: str) -> bool:
    message = _normalize(user_message)
    return intent == BUSINESS_ANALYSIS and _contains_any(message, BUSINESS_INSIGHT_KEYWORDS)


_THAI_GREETING_KEYWORDS = ["สวัสดี", "หวัดดี", "ดีครับ", "ดีค่ะ"]
_THAI_FOLLOW_UP_KEYWORDS = ["ไม่ใช่", "ไม่เอา", "พูดใหม่", "หมายถึง", "ไม่ใช่แบบนั้น"]
_THAI_START_KEYWORDS = ["เปิดร้าน", "เริ่มร้าน", "เริ่มธุรกิจ", "จะขาย", "อยากขาย", "เริ่มขาย"]
_THAI_CONTENT_KEYWORDS = ["โพสต์", "คอนเทนต์", "แคปชั่น", "รีล", "reels", "tiktok", "รูป", "วิดีโอ"]
_THAI_MARKETING_KEYWORDS = ["โปร", "โปรโมชั่น", "โปรโมชัน", "ส่วนลด", "แคมเปญ"]
_THAI_RETENTION_KEYWORDS = ["ซื้อซ้ำ", "ลูกค้าเก่า", "รักษาลูกค้า", "กลับมาซื้อ"]
_THAI_SALES_KEYWORDS = ["ยอดตก", "ยอดขาย", "ขายดี", "เพิ่มยอด", "ปิดการขาย", "ไม่มีออเดอร์"]
_THAI_ANALYSIS_KEYWORDS = ["ร้านนี้", "วิเคราะห์", "คะแนน", "สุขภาพธุรกิจ", "ดูภาพรวม", "ปัญหาร้าน", "ควรทำอะไรต่อ"]
_THAI_GENERAL_KEYWORDS = ["คุย", "ถาม", "ช่วย", "คืออะไร"]
_THAI_PRODUCT_FEEDBACK_KEYWORDS = [
    "อยากให้",
    "น่าจะมี",
    "เพิ่ม",
    "ปรับ",
    "แก้",
    "ตรงนี้",
    "งง",
    "อ่านยาก",
    "ใช้ยาก",
    "หายาก",
    "ตอบยาว",
    "ตอบสั้น",
    "ไม่เข้าใจ",
    "อยากได้",
    "ถ้ามี",
    "ควรมี",
]
_PRODUCT_CONTEXT_KEYWORDS = [
    "app",
    "แอป",
    "ระบบ",
    "หน้า",
    "dashboard",
    "แดชบอร์ด",
    "ภาพรวม",
    "ui",
    "ปุ่ม",
    "เมนู",
    "ฟีเจอร์",
    "feature",
    "แจ้งเตือน",
    "notification",
    "line",
    "chat",
    "แชท",
    "ai",
    "ตอบ",
    "คอนเทนต์",
    "สร้างโพสต์",
    "สมัคร",
    "เริ่มใช้",
    "ใช้งาน",
]
_BUSINESS_ADVICE_PATTERNS = [
    "เพิ่มยอดขาย",
    "เพิ่มยอด",
    "ช่วยเพิ่มยอด",
    "ควรเพิ่มยอด",
    "เพิ่มลูกค้า",
    "เพิ่มออเดอร์",
    "ขายดีขึ้น",
    "ยอดขาย",
]


def is_product_feedback(user_message: str) -> bool:
    message = _normalize(user_message)
    if not message:
        return False

    has_feedback_phrase = _contains_any(message, _THAI_PRODUCT_FEEDBACK_KEYWORDS)
    if not has_feedback_phrase:
        return False

    has_product_context = _contains_any(message, _PRODUCT_CONTEXT_KEYWORDS)
    if _contains_any(message, _BUSINESS_ADVICE_PATTERNS) and not has_product_context:
        return False

    if has_product_context:
        return True

    return message in {"ตรงนี้งง", "ใช้ยาก", "ปรับหน่อย", "แก้หน่อย", "อ่านยาก"}


def detect_conversation_intent(user_message: str) -> str:
    message = _normalize(user_message)
    if not message:
        return OTHER
    if is_product_feedback(message):
        return PRODUCT_FEEDBACK
    if message in {"สวัสดี", "หวัดดี", "ไง"} or _contains_any(message, _THAI_GREETING_KEYWORDS):
        return GREETING
    if _contains_any(message, _THAI_START_KEYWORDS):
        return START_BUSINESS
    if message in {"ไม่ใช่", "ไม่", "พูดใหม่"} or _contains_any(message, _THAI_FOLLOW_UP_KEYWORDS):
        return FOLLOW_UP
    if _contains_any(message, _THAI_CONTENT_KEYWORDS):
        return CONTENT
    if _contains_any(message, _THAI_MARKETING_KEYWORDS):
        return MARKETING
    if _contains_any(message, _THAI_RETENTION_KEYWORDS):
        return CUSTOMER_RETENTION
    if _contains_any(message, _THAI_SALES_KEYWORDS):
        return SALES
    if _contains_any(message, _THAI_ANALYSIS_KEYWORDS):
        return BUSINESS_ANALYSIS
    if _contains_any(message, _THAI_GENERAL_KEYWORDS):
        return GENERAL_CHAT
    return OTHER


def should_show_business_insights(intent: str, user_message: str) -> bool:
    message = _normalize(user_message)
    return intent == BUSINESS_ANALYSIS and _contains_any(message, _THAI_ANALYSIS_KEYWORDS)
