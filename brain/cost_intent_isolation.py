from __future__ import annotations

import re


_NUMBER_PATTERN = r"\d+(?:,\d{3})*(?:\.\d+)?"


def is_strong_cost_calculation_message(message: str | None) -> bool:
    text = str(message or "").strip()
    if not text:
        return False

    normalized = text.lower()
    numbers = re.findall(_NUMBER_PATTERN, normalized)
    if len(numbers) < 2:
        return False

    has_cost_word = bool(
        re.search(
            r"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19|cost|unit cost|cost per",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    has_unit_cost = bool(
        re.search(
            r"(?:"
            + _NUMBER_PATTERN
            + r")\s*(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)?\s*(?:\u0e15\u0e48\u0e2d|/|per)\s*(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|piece|pcs?|units?)",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    has_quantity = bool(
        re.search(
            r"(?:"
            + _NUMBER_PATTERN
            + r")\s*(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|piece|pcs?|units?)",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    return has_cost_word and has_unit_cost and has_quantity
