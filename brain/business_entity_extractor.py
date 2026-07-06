from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from brain.analytical_turn_classifier import classify_analytical_turn
from brain.business_context_engine import BUSINESS_TYPE_ALIASES, PRODUCT_ALIASES


THAI_MONTHS = (
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
)

DATE_KEYWORDS = (
    "วันนี้",
    "เมื่อวาน",
    "พรุ่งนี้",
    "สัปดาห์นี้",
    "อาทิตย์นี้",
    "เดือนนี้",
    "today",
    "yesterday",
    "tomorrow",
    "this week",
    "this month",
)

REQUIRED_BY_INTENT = {
    "pricing_question": ("product_or_service",),
    "profit_calculation": ("product_or_service", "price", "cost", "quantity"),
    "sales_summary": ("date",),
    "cost_calculation": ("product_or_service", "cost"),
    "inventory_check": ("product_or_service",),
}

CUSTOMER_REPLY_TRAILERS = (
    "ควรตอบยังไง",
    "ตอบยังไง",
    "ควรตอบอย่างไร",
    "ตอบอย่างไร",
)

EXPENSIVE_PHRASES = ("แพงไป", "แพง")


def _clean_dict(data: dict | None) -> dict:
    return {key: value for key, value in (data or {}).items() if value not in (None, "", [], {})}


def _to_number(value: str) -> float | int:
    number = float(str(value).replace(",", ""))
    return int(number) if number.is_integer() else number


def _unique(items: list[Any]) -> list[Any]:
    seen = set()
    unique = []
    for item in items:
        marker = repr(item)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique


def _extract_money(message: str) -> tuple[list[dict], list[dict]]:
    prices = []
    costs = []
    money_pattern = r"(?P<label>ขาย|ราคา|price|sell|ต้นทุน|ทุน|cost)?\s*(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?:บาท|฿|thb|baht)?"
    for match in re.finditer(money_pattern, message, flags=re.IGNORECASE):
        label = (match.group("label") or "").lower()
        amount = _to_number(match.group("amount"))
        item = {"amount": amount, "currency": "THB", "raw": match.group(0).strip()}
        if label in {"ต้นทุน", "ทุน", "cost"}:
            costs.append(item)
        elif label in {"ขาย", "ราคา", "price", "sell"} or re.search(r"(บาท|฿|thb|baht)", match.group(0), re.IGNORECASE):
            prices.append(item)
    return _unique(prices), _unique(costs)


def _extract_quantities(message: str) -> list[dict]:
    quantities = []
    pattern = r"(?:จำนวน|qty|quantity|ขายได้|ได้)?\s*(\d[\d,]*(?:\.\d+)?)\s*(ชิ้น|กล่อง|อัน|แก้ว|ถุง|จาน|ออเดอร์|order|orders|pcs|units?)"
    for match in re.finditer(pattern, message, flags=re.IGNORECASE):
        quantities.append(
            {
                "amount": _to_number(match.group(1)),
                "unit": match.group(2),
                "raw": match.group(0).strip(),
            }
        )
    return _unique(quantities)


def _extract_unit_cost(message: str) -> dict | None:
    pattern = (
        r"(?P<amount>\d[\d,]*(?:\.\d+)?)\s*"
        r"(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)\s*"
        r"(?:\u0e15\u0e48\u0e2d|/)\s*"
        r"(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|pcs?|units?)"
    )
    match = re.search(pattern, message, flags=re.IGNORECASE)
    if not match:
        return None
    return {
        "amount": _to_number(match.group("amount")),
        "currency": "THB",
        "raw": match.group(0).strip(),
    }


def _extract_labeled_money(message: str, labels: tuple[str, ...]) -> dict | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{label_pattern})[^\d]{{0,30}}(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)?",
        message,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return {
        "amount": _to_number(match.group("amount")),
        "currency": "THB",
        "raw": match.group(0).strip(),
    }


def _normalize_profit_money(message: str, prices: list[dict], costs: list[dict]) -> tuple[list[dict], list[dict]]:
    cost = _extract_labeled_money(message, ("\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19", "\u0e17\u0e38\u0e19", "cost"))
    price = _extract_labeled_money(message, ("\u0e02\u0e32\u0e22", "\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22", "sell", "selling price"))
    if cost:
        costs = [cost, *[item for item in costs if item.get("amount") != cost.get("amount")]]
        prices = [item for item in prices if item.get("amount") != cost.get("amount")]
    if price:
        prices = [price, *[item for item in prices if item.get("amount") != price.get("amount")]]
    return _unique(prices), _unique(costs)


def _extract_dates(message: str) -> list[str]:
    dates = []
    lowered = message.lower()
    for keyword in DATE_KEYWORDS:
        if keyword.lower() in lowered:
            dates.append(keyword)
    dates.extend(re.findall(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", message))
    month_pattern = r"\d{1,2}\s*(?:" + "|".join(re.escape(month) for month in THAI_MONTHS) + r")(?:\s*\d{2,4})?"
    dates.extend(re.findall(month_pattern, message))
    return _unique([date.strip() for date in dates if date.strip()])


def _extract_customer_phrases(message: str) -> list[str]:
    phrases = []
    phrases.extend(re.findall(r"[\"“']([^\"”']{2,160})[\"”']", message))
    for pattern in (r"ลูกค้า(?:ถาม|บอก|บ่น|ทัก)ว่า?\s*(.{2,160})", r"customer says?\s*(.{2,160})"):
        for match in re.findall(pattern, message, flags=re.IGNORECASE):
            cleaned = str(match or "").strip()
            for trailer in CUSTOMER_REPLY_TRAILERS:
                cleaned = cleaned.split(trailer, 1)[0].strip()
            phrases.append(cleaned)
    for phrase in EXPENSIVE_PHRASES:
        if phrase in message:
            phrases.append(phrase)
    return _unique([phrase.strip() for phrase in phrases if phrase.strip()])


def _extract_business_type_hints(message: str) -> list[str]:
    hints = []
    lowered = message.lower()
    protected_choux = "ชูครีม" in message
    for phrase, business_type in sorted(BUSINESS_TYPE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        phrase_lower = phrase.lower()
        if protected_choux and phrase == "ครีม":
            continue
        if phrase_lower in lowered:
            hints.append(business_type)
    return _unique(hints)


def _extract_product_or_service_names(message: str) -> list[str]:
    names = []
    lowered = message.lower()
    protected_choux = "ชูครีม" in message
    for phrase, product in sorted(PRODUCT_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if protected_choux and phrase == "ครีม":
            continue
        if phrase.lower() in lowered:
            names.append(product)

    label_patterns = (
        r"(?:สินค้า|เมนู|บริการ|product|service)\s*[:：]?\s*([A-Za-z0-9\u0e00-\u0e7f][A-Za-z0-9\u0e00-\u0e7f\s-]{1,40})",
        r"(?:ขาย|ทำ|โปรโมต)\s+([A-Za-z\u0e00-\u0e7f][A-Za-z0-9\u0e00-\u0e7f\s-]{1,30})(?=\s*(?:ราคา|ขาย|ต้นทุน|จำนวน|กี่|เท่า|$))",
    )
    for pattern in label_patterns:
        for raw in re.findall(pattern, message, flags=re.IGNORECASE):
            candidate = re.sub(r"\s+", " ", raw).strip(" ,.:;")
            if candidate and not re.fullmatch(r"(ราคา|ต้นทุน|จำนวน|บาท|price|cost)", candidate, re.IGNORECASE):
                names.append(candidate)
    return _unique(names)


def _extract_simulation_values(message: str) -> list[dict]:
    values = []
    for match in re.finditer(r"(?:ถ้า|if)\s*([^,.;\n]{2,80})", message, flags=re.IGNORECASE):
        values.append({"type": "condition", "raw": match.group(0).strip(), "value": match.group(1).strip()})
    for match in re.finditer(r"(?:จาก|from)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:เป็น|to)\s*(\d[\d,]*(?:\.\d+)?)", message, flags=re.IGNORECASE):
        values.append({"type": "change", "from": _to_number(match.group(1)), "to": _to_number(match.group(2)), "raw": match.group(0).strip()})
    for match in re.finditer(r"\d[\d,]*(?:\.\d+)?\s*%", message):
        values.append({"type": "percent", "value": match.group(0).strip(), "raw": match.group(0).strip()})
    return _unique(values)


def _explicit_price_item(item: dict) -> bool:
    raw = str((item or {}).get("raw") or "").lower()
    return any(token in raw for token in ("\u0e02\u0e32\u0e22", "\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22", "sell", "selling price"))


def _missing_entities(intent: str | None, entities: dict) -> list[str]:
    missing = []
    required = REQUIRED_BY_INTENT.get(str(intent or "unknown"), ())
    for field in required:
        if field == "product_or_service":
            present = bool(entities.get("product_or_service_names"))
        elif field == "price":
            present = bool(entities.get("prices"))
        elif field == "cost":
            present = bool(entities.get("costs"))
        elif field == "quantity":
            present = bool(entities.get("quantities"))
        elif field == "date":
            present = bool(entities.get("dates"))
        else:
            present = bool(entities.get(field))
        if not present:
            missing.append(field)
    return missing


def _completed_entities(intent: str | None, entities: dict) -> list[str]:
    required = list(REQUIRED_BY_INTENT.get(str(intent or "unknown"), ()))
    missing = set(_missing_entities(intent, entities))
    return [field for field in required if field not in missing]


def _entity_completeness(required: list[str], completed: list[str]) -> dict:
    total = len(required)
    done = len(completed)
    return {
        "completed": done,
        "required": total,
        "percent": 1.0 if total == 0 else round(done / total, 2),
    }


def extract_business_entities(user_message: str | None, detected_intent: str | None = None) -> dict:
    """Extract compact structured entities from the current business message."""
    message = str(user_message or "").strip()
    if not message:
        required = list(REQUIRED_BY_INTENT.get(str(detected_intent or "unknown"), ()))
        return {
            "extracted_entities": {},
            "required_entities": required,
            "completed_entities": [],
            "missing_entities": required,
            "entity_completeness": _entity_completeness(required, []),
            "entity_confidence": 0.0,
        }

    semantic = classify_analytical_turn(message)
    prices, costs = _extract_money(message)
    if detected_intent == "profit_calculation":
        prices, costs = _normalize_profit_money(message, prices, costs)
    elif detected_intent == "cost_calculation":
        labeled_cost = _extract_labeled_money(message, ("\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21", "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19", "\u0e17\u0e38\u0e19", "total cost", "cost"))
        if labeled_cost:
            costs = _unique([labeled_cost, *[item for item in costs if item.get("amount") != labeled_cost.get("amount")]])
            prices = [item for item in prices if item.get("amount") != labeled_cost.get("amount") or _explicit_price_item(item)]
        prices = [item for item in prices if _explicit_price_item(item)]
    if semantic.get("analytical_statement_detected") or semantic.get("correction_detected"):
        prices = [item for item in prices if _explicit_price_item(item)]
    unit_cost = _extract_unit_cost(message) if detected_intent == "cost_calculation" else None
    normalization_trace = []
    if unit_cost:
        costs = _unique([*costs, unit_cost])
        normalization_trace.append(
            {
                "field": "cost",
                "aliases": ["price", "unit_cost", "cost_per_unit"],
                "source": "unit_cost_pattern: amount + บาทต่อชิ้น",
                "raw": unit_cost.get("raw"),
                "value": unit_cost.get("amount"),
            }
        )
    product_or_service_names = _extract_product_or_service_names(message)
    customer_phrases = _extract_customer_phrases(message)
    customer_phrase = next((phrase for phrase in EXPENSIVE_PHRASES if phrase in customer_phrases), None)
    customer_phrase = customer_phrase or (customer_phrases[-1] if customer_phrases else None)
    comparison_values = _extract_simulation_values(message)
    if semantic.get("comparison"):
        comparison_values = _unique(
            [
                {
                    **semantic["comparison"],
                    "from": semantic["comparison"].get("from_value"),
                    "to": semantic["comparison"].get("to_value"),
                },
                *comparison_values,
            ]
        )
    correction = semantic.get("correction") or {}
    entities = _clean_dict(
        {
            "product_or_service_names": product_or_service_names,
            "product_or_service": product_or_service_names[0] if product_or_service_names else None,
            "prices": prices,
            "costs": costs,
            "cost": unit_cost.get("amount") if unit_cost else None,
            "unit_cost": unit_cost.get("amount") if unit_cost else None,
            "cost_per_unit": unit_cost.get("amount") if unit_cost else None,
            "quantities": _extract_quantities(message),
            "dates": _extract_dates(message),
            "customer_phrases": customer_phrases,
            "customer_phrase": customer_phrase,
            "business_type_hints": _extract_business_type_hints(message),
            "comparison_or_simulation_values": comparison_values,
            "analytical_statement_detected": semantic.get("analytical_statement_detected"),
            "comparison_change_detected": semantic.get("comparison_change_detected"),
            "correction_detected": semantic.get("correction_detected"),
            "explicit_calculation_request_detected": semantic.get("explicit_calculation_request_detected"),
            "comparison_change": semantic.get("comparison"),
            "correction": semantic.get("correction"),
            "correction_current_value": correction.get("current_value"),
            "superseded_values": correction.get("superseded_values"),
            "superseded_claims": correction.get("superseded_claims"),
            "entity_mapping_trace": normalization_trace,
        }
    )
    missing = _missing_entities(detected_intent, entities)
    required = list(REQUIRED_BY_INTENT.get(str(detected_intent or "unknown"), ()))
    completed = _completed_entities(detected_intent, entities)
    extracted_field_count = len(entities)
    required_count = len(required)
    confidence = min(0.95, 0.35 + (0.1 * extracted_field_count))
    if required_count:
        confidence += 0.25 * (required_count - len(missing)) / required_count
    return {
        "extracted_entities": entities,
        "required_entities": required,
        "completed_entities": completed,
        "missing_entities": missing,
        "entity_completeness": _entity_completeness(required, completed),
        "entity_confidence": round(min(0.98, confidence), 2),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
