from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone


BUSINESS_TYPE_ALIASES = {
    "ร้านขายชา": "tea_shop",
    "ร้านชา": "tea_shop",
    "ชานม": "tea_shop",
    "ชาไทย": "tea_shop",
    "tea shop": "tea_shop",
    "coffee shop": "coffee_shop",
    "ร้านกาแฟ": "coffee_shop",
    "ร้านอาหาร": "restaurant",
    "ร้านขนม": "bakery",
    "เบเกอรี่": "bakery",
    "เสื้อผ้า": "fashion_shop",
    "ร้านเสื้อผ้า": "fashion_shop",
}

PRODUCT_ALIASES = {
    "ชา": "tea",
    "ชานม": "milk_tea",
    "ชาไทย": "thai_tea",
    "กาแฟ": "coffee",
    "ขนม": "bakery",
}

GOAL_KEYWORDS = {
    "today_action": ["วันนี้ควรทำอะไร", "วันนี้ทำอะไร", "ควรทำอะไรวันนี้", "ทำอะไรดีวันนี้"],
    "create_content": ["ทำโพสต์", "เขียนโพสต์", "สร้างโพสต์", "แคปชั่น", "คอนเทนต์"],
    "increase_sales": ["เพิ่มยอด", "ยอดขาย", "ขายดีขึ้น", "ไม่มีออเดอร์"],
    "set_price": ["ราคาเท่าไร", "ตั้งราคา", "ขายเท่าไร"],
}

PROBLEM_KEYWORDS = {
    "low_sales": ["ยอดตก", "ขายไม่ดี", "ไม่มีออเดอร์", "ลูกค้าน้อย"],
    "pricing_unclear": ["ราคาเท่าไร", "ตั้งราคา", "แพงไป", "ถูกไป"],
    "content_needed": ["โพสต์อะไร", "คอนเทนต์อะไร", "แคปชั่น"],
}


def _clean_dict(data: dict | None) -> dict:
    return {key: value for key, value in (data or {}).items() if value not in (None, "", [], {})}


def _store_profile(application_state: dict | None) -> dict:
    store = (application_state or {}).get("store") or {}
    if isinstance(store.get("profile"), dict):
        return store.get("profile") or {}
    return store


def _match_alias(message: str, aliases: dict[str, str]) -> str | None:
    lowered = str(message or "").strip().lower()
    for phrase, value in aliases.items():
        if phrase.lower() in lowered:
            return value
    return None


def _match_keyword_group(message: str, groups: dict[str, list[str]]) -> str | None:
    lowered = str(message or "").strip().lower()
    for name, keywords in groups.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return name
    return None


def _topic_from_context(context: dict, message: str) -> str | None:
    goal = context.get("current_goal")
    problem = context.get("current_problem")
    product = context.get("current_product")
    business_type = context.get("business_type")
    if goal == "today_action":
        return "daily business planning"
    if goal == "create_content":
        return "content planning"
    if goal == "set_price":
        return "pricing"
    if problem:
        return problem
    if product:
        return str(product)
    if business_type:
        return str(business_type)
    if message:
        return str(message).strip()[:80]
    return None


def build_business_context(
    application_state: dict | None,
    user_message: str | None,
    understanding: dict | None = None,
    conversation_memory: dict | None = None,
) -> dict:
    """Evolve current business context from profile, memory, and the latest turn."""
    state = application_state or {}
    previous = deepcopy(
        state.get("business_context")
        or ((state.get("conversation") or {}).get("business_context"))
        or {}
    )
    profile = _store_profile(state)
    message = str(user_message or "").strip()
    context = dict(previous)

    profile_business_type = profile.get("store_type") or profile.get("business_type")
    profile_product = profile.get("product")
    profile_customer = profile.get("target_customer") or profile.get("customer_type")

    business_type = _match_alias(message, BUSINESS_TYPE_ALIASES)
    product = _match_alias(message, PRODUCT_ALIASES)
    goal = _match_keyword_group(message, GOAL_KEYWORDS)
    problem = _match_keyword_group(message, PROBLEM_KEYWORDS)

    if business_type:
        context["business_type"] = business_type
    elif profile_business_type and not context.get("business_type"):
        context["business_type"] = profile_business_type

    if product:
        context["current_product"] = product
    elif profile_product and not context.get("current_product"):
        context["current_product"] = profile_product

    if profile_customer and not context.get("customer_type"):
        context["customer_type"] = profile_customer

    if goal:
        context["current_goal"] = goal
    if problem:
        context["current_problem"] = problem

    if any(term in message.lower() for term in ["แคมเปญ", "campaign", "โปรโมชัน", "โปรโมชั่น"]):
        context["current_campaign"] = message[:120]

    focused_topic = (
        (conversation_memory or {}).get("focused_business_topic")
        or ((understanding or {}).get("conversation_context") or {}).get("current_topic")
    )
    context["current_discussion_topic"] = _topic_from_context(context, message) or focused_topic
    context["source"] = "conversation_intelligence"
    context["updated_at"] = datetime.now(timezone.utc).isoformat()
    return _clean_dict(context)
