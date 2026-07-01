from __future__ import annotations

import re


WORKFLOW_PROFIT_CALCULATION = "PROFIT_CALCULATION"

_NUMBER_PATTERN = r"\d+(?:,\d{3})*(?:\.\d+)?"

_EXPLICIT_PROFIT_TERMS = (
    "\u0e01\u0e33\u0e44\u0e23",
    "profit",
    "margin",
    "\u0e21\u0e32\u0e23\u0e4c\u0e08\u0e34\u0e49\u0e19",
)

_SELLING_PRICE_TERMS = (
    "\u0e02\u0e32\u0e22",
    "\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22",
    "sell",
    "selling price",
)

_COST_TERMS = (
    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
    "\u0e17\u0e38\u0e19",
    "cost",
)

_COST_PER_UNIT_TERMS = (
    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19",
    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e2b\u0e19\u0e48\u0e27\u0e22",
    "\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19",
    "\u0e15\u0e48\u0e2d\u0e2b\u0e19\u0e48\u0e27\u0e22",
    "\u0e17\u0e33\u0e44\u0e14\u0e49\u0e01\u0e35\u0e48\u0e0a\u0e34\u0e49\u0e19",
    "\u0e08\u0e33\u0e19\u0e27\u0e19\u0e0a\u0e34\u0e49\u0e19",
    "unit cost",
    "cost per unit",
    "per unit",
)


def _normalize(message: str | None) -> str:
    return re.sub(r"\s+", " ", str(message or "").strip().lower())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term and term.lower() in text for term in terms)


def _number_count(text: str) -> int:
    return len(re.findall(_NUMBER_PATTERN, text))


def has_profit_calculation_intent(message: str | None) -> bool:
    """Return true for clear profit, margin, or selling-price calculation requests."""
    text = _normalize(message)
    if not text:
        return False
    if _contains_any(text, _EXPLICIT_PROFIT_TERMS):
        return True
    return bool(
        _contains_any(text, _SELLING_PRICE_TERMS)
        and _contains_any(text, _COST_TERMS)
        and _number_count(text) >= 2
    )


def has_cost_per_unit_intent(message: str | None) -> bool:
    """Return true only for clear unit-cost requests."""
    text = _normalize(message)
    if not text or has_profit_calculation_intent(text):
        return False
    if _contains_any(text, _COST_PER_UNIT_TERMS):
        return True
    return bool(
        re.search(
            r"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21.*\u0e17\u0e33\u0e44\u0e14\u0e49.*\u0e0a\u0e34\u0e49\u0e19",
            text,
        )
    )


def planner_intent_for_message(message: str | None) -> str | None:
    if has_profit_calculation_intent(message):
        return "profit_calculation"
    if has_cost_per_unit_intent(message):
        return "cost_calculation"
    return None
