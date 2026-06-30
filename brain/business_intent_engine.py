from __future__ import annotations

import re
from typing import Any


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pricing_question": (
        "ราคาเท่าไร",
        "ราคาเท่าไหร่",
        "ขายเท่าไร",
        "ขายเท่าไหร่",
        "ตั้งราคา",
        "กี่บาท",
        "price",
        "how much",
        "pricing",
    ),
    "profit_calculation": (
        "กำไร",
        "profit",
        "margin",
        "เหลือเท่าไร",
        "เหลือเท่าไหร่",
        "คุ้มไหม",
    ),
    "sales_summary": (
        "สรุปยอดขาย",
        "ยอดขาย",
        "ขายได้",
        "sales summary",
        "sales report",
        "revenue",
    ),
    "cost_calculation": (
        "ต้นทุน",
        "cost",
        "คำนวณต้นทุน",
        "ทุน",
        "ค่าใช้จ่าย",
    ),
    "inventory_check": (
        "สต็อก",
        "สต๊อก",
        "คงเหลือ",
        "เหลือกี่",
        "inventory",
        "stock",
        "in stock",
    ),
    "marketing_content": (
        "โพสต์",
        "แคปชั่น",
        "คอนเทนต์",
        "โฆษณา",
        "โปรโมชั่น",
        "โปรโมชัน",
        "campaign",
        "marketing",
        "caption",
        "content",
        "facebook post",
    ),
    "customer_reply": (
        "ตอบลูกค้า",
        "ลูกค้าถาม",
        "ลูกค้าบอก",
        "ลูกค้าทัก",
        "reply customer",
        "customer reply",
        "respond to customer",
    ),
    "product_question": (
        "สินค้า",
        "ผลิตภัณฑ์",
        "เมนู",
        "ทำจากอะไร",
        "มีอะไร",
        "product",
        "service",
    ),
    "dashboard_request": (
        "แดชบอร์ด",
        "dashboard",
        "ภาพรวม",
        "รายงาน",
        "overview",
    ),
}

INTENT_ORDER = [
    "profit_calculation",
    "pricing_question",
    "sales_summary",
    "cost_calculation",
    "inventory_check",
    "marketing_content",
    "customer_reply",
    "product_question",
    "dashboard_request",
]


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _matched_keywords(message: str, keywords: tuple[str, ...]) -> list[str]:
    normalized = _normalize_text(message)
    return [keyword for keyword in keywords if _normalize_text(keyword) in normalized]


def detect_business_intent(user_message: str | None) -> dict:
    """Detect a broad business intent before skill matching."""
    message = str(user_message or "").strip()
    if not message:
        return {
            "detected_intent": "unknown",
            "intent_confidence": 0.0,
            "matched_intent_keywords": [],
        }

    scored: list[tuple[float, str, list[str]]] = []
    for intent in INTENT_ORDER:
        matches = _matched_keywords(message, INTENT_KEYWORDS[intent])
        if not matches:
            continue
        score = min(0.95, 0.45 + (0.17 * len(matches)))
        if intent == "profit_calculation":
            score += 0.2
        if any(len(keyword) >= 8 for keyword in matches):
            score += 0.08
        scored.append((min(0.98, score), intent, matches))

    if not scored:
        return {
            "detected_intent": "unknown",
            "intent_confidence": 0.2 if message else 0.0,
            "matched_intent_keywords": [],
        }

    scored.sort(key=lambda item: (-item[0], INTENT_ORDER.index(item[1])))
    confidence, intent, matches = scored[0]
    return {
        "detected_intent": intent,
        "intent_confidence": round(confidence, 2),
        "matched_intent_keywords": matches,
    }
