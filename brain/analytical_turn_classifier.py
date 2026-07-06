from __future__ import annotations

import re
from typing import Any


NUMBER_PATTERN = r"\d+(?:,\d{3})*(?:\.\d+)?"

_COST_SUBJECT_PATTERN = (
    r"(?P<subject>"
    r"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19|"
    r"\u0e17\u0e38\u0e19|"
    r"\u0e23\u0e32\u0e04\u0e32\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a|"
    r"\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a|"
    r"cost|raw material cost"
    r")"
)

_CALCULATION_TERMS = (
    "\u0e04\u0e33\u0e19\u0e27\u0e13",
    "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e13",
    "\u0e04\u0e34\u0e14\u0e01\u0e33\u0e44\u0e23",
    "\u0e04\u0e34\u0e14\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
    "\u0e01\u0e33\u0e44\u0e23\u0e01\u0e35\u0e48",
    "\u0e01\u0e33\u0e44\u0e23\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
    "calculate",
    "profit",
    "margin",
)

_CORRECTION_TERMS = (
    "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48",
    "\u0e08\u0e23\u0e34\u0e07 \u0e46",
    "\u0e08\u0e23\u0e34\u0e07\u0e46",
    "\u0e40\u0e21\u0e37\u0e48\u0e2d\u0e01\u0e35\u0e49\u0e1a\u0e2d\u0e01\u0e1c\u0e34\u0e14",
    "\u0e1a\u0e2d\u0e01\u0e1c\u0e34\u0e14",
    "\u0e44\u0e21\u0e48\u0e43\u0e0a\u0e48",
    "\u0e15\u0e31\u0e27\u0e40\u0e25\u0e02\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14",
    "\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14\u0e04\u0e37\u0e2d",
    "\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e40\u0e1e\u0e34\u0e48\u0e21",
    "correction",
    "actually",
    "not",
)


def _to_number(value: str) -> float | int:
    amount = float(str(value).replace(",", ""))
    return int(amount) if amount.is_integer() else amount


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in text for term in terms)


def _subject_from(raw: str | None) -> str | None:
    value = str(raw or "").strip().lower()
    if "\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a" in value or "raw material" in value:
        return "raw_material_cost"
    if "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19" in value or "\u0e17\u0e38\u0e19" in value or "cost" in value:
        return "cost"
    return raw


def explicit_calculation_request_detected(message: str | None) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    if _contains_any(text, _CALCULATION_TERMS):
        return True
    labeled_amounts = re.findall(
        r"(?:^|\s)[A-Za-z\u0e00-\u0e7f]{1,40}?\s*" + NUMBER_PATTERN + r"\s*(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)?",
        text,
        flags=re.IGNORECASE,
    )
    if len(labeled_amounts) >= 2 and re.search(r"\u0e23\u0e27\u0e21\s*(?:\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23|\u0e01\u0e35\u0e48|\?)", text):
        return True
    return bool(
        re.search(r"\d", text)
        and re.search(r"(\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23|\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17|\?)", text)
        and re.search(r"(\u0e01\u0e33\u0e44\u0e23|\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19|profit|cost)", text)
    )


def classify_analytical_turn(message: str | None) -> dict[str, Any]:
    text = str(message or "").strip()
    normalized = text.lower()
    numbers = re.findall(NUMBER_PATTERN, text)
    explicit_calc = explicit_calculation_request_detected(text)

    comparison = None
    change_pattern = re.search(
        _COST_SUBJECT_PATTERN
        + r"[^0-9]{0,40}?(?:\u0e40\u0e1e\u0e34\u0e48\u0e21|\u0e25\u0e14)?[^0-9]{0,20}?"
        + r"(?:\u0e08\u0e32\u0e01|from)\s*(?P<from>"
        + NUMBER_PATTERN
        + r")\s*(?:\u0e40\u0e1b\u0e47\u0e19|\u0e40\u0e2b\u0e25\u0e37\u0e2d|\u0e44\u0e1b\u0e40\u0e1b\u0e47\u0e19|to)\s*(?P<to>"
        + NUMBER_PATTERN
        + r")",
        text,
        flags=re.IGNORECASE,
    )
    if change_pattern:
        raw_subject = change_pattern.group("subject")
        comparison = {
            "type": "change",
            "subject": _subject_from(raw_subject),
            "from_value": _to_number(change_pattern.group("from")),
            "to_value": _to_number(change_pattern.group("to")),
            "currency": "THB",
            "raw": change_pattern.group(0).strip(),
        }

    cost_change_words = bool(
        re.search(_COST_SUBJECT_PATTERN, text, flags=re.IGNORECASE)
        and re.search(r"\u0e40\u0e1e\u0e34\u0e48\u0e21|\u0e2a\u0e39\u0e07\u0e02\u0e36\u0e49\u0e19|\u0e25\u0e14|\u0e40\u0e2b\u0e25\u0e37\u0e2d", text)
    )
    analytical = bool((comparison or cost_change_words) and not explicit_calc)

    correction_detected = _contains_any(normalized, _CORRECTION_TERMS)
    current_value = None
    superseded_values: list[float | int] = []
    latest_match = re.search(
        r"(?:\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14\u0e04\u0e37\u0e2d|\u0e15\u0e31\u0e27\u0e40\u0e25\u0e02\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14\u0e04\u0e37\u0e2d|actually)\s*(?P<value>"
        + NUMBER_PATTERN
        + r")",
        text,
        flags=re.IGNORECASE,
    )
    stable_cost_match = re.search(
        _COST_SUBJECT_PATTERN
        + r"[^0-9]{0,30}?(?:\u0e22\u0e31\u0e07|\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21|is still)?[^0-9]{0,20}?(?P<value>"
        + NUMBER_PATTERN
        + r")",
        text,
        flags=re.IGNORECASE,
    )
    if latest_match:
        current_value = _to_number(latest_match.group("value"))
    elif stable_cost_match:
        current_value = _to_number(stable_cost_match.group("value"))
    elif correction_detected and numbers:
        current_value = _to_number(numbers[0])

    not_value_matches = re.findall(r"\u0e44\u0e21\u0e48\u0e43\u0e0a\u0e48\s*(" + NUMBER_PATTERN + r")", text)
    superseded_values = [_to_number(value) for value in not_value_matches]
    if correction_detected and "\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e40\u0e1e\u0e34\u0e48\u0e21" in normalized:
        superseded_values.append("cost_change_claim")

    correction = None
    if correction_detected:
        correction = {
            "target": "cost" if re.search(_COST_SUBJECT_PATTERN, text, flags=re.IGNORECASE) else "numeric_value",
            "current_value": current_value,
            "currency": "THB" if current_value is not None else None,
            "superseded_values": superseded_values,
            "superseded_claims": ["cost_change"] if "cost_change_claim" in superseded_values else [],
            "raw": text,
        }

    return {
        "analytical_statement_detected": bool(analytical),
        "comparison_change_detected": bool(comparison),
        "correction_detected": bool(correction_detected),
        "explicit_calculation_request_detected": bool(explicit_calc),
        "comparison": comparison,
        "correction": correction,
    }
