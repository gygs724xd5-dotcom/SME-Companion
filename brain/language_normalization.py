from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field


LANGUAGE_NORMALIZATION_VERSION = "5.8.4"


@dataclass(frozen=True)
class LanguageNormalizationResult:
    original_text: str
    normalized_text: str
    normalizations_applied: list[dict] = field(default_factory=list)
    normalization_count: int = 0
    confidence: float = 1.0
    version: str = LANGUAGE_NORMALIZATION_VERSION
    diagnostic_only: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


_PHRASE_RULES: tuple[tuple[str, str, str], ...] = (
    ("ช่วยคำนวนกำไร", "ช่วยคำนวณกำไร", "common_misspelling_profit_request"),
    ("คำนวนกำไร", "คำนวณกำไร", "common_misspelling_profit_phrase"),
    ("ช่วยคำนวน", "ช่วยคำนวณ", "common_misspelling_calculate_request"),
    ("คำนวน", "คำนวณ", "common_misspelling_calculate"),
    ("ช่วยคิดกำไร", "ช่วยคำนวณกำไร", "profit_calculation_request_variant"),
    ("คิดกำไร", "คำนวณกำไร", "profit_calculation_variant"),
)

_SPACING_RULES: tuple[tuple[str, str, str], ...] = (
    (r"กำไร\s+เท่าไร", "กำไรเท่าไร", "profit_question_spacing"),
    (r"กำไร\s+เท่าไหร่", "กำไรเท่าไหร่", "profit_question_spacing"),
    (r"ต้นทุน\s+เท่าไร", "ต้นทุนเท่าไร", "cost_question_spacing"),
    (r"ต้นทุน\s+เท่าไหร่", "ต้นทุนเท่าไหร่", "cost_question_spacing"),
)


def normalize_user_language(user_text: str | None) -> dict:
    """Conservatively normalize common Thai variants before intent detection."""

    original = str(user_text or "")
    normalized = original
    applied: list[dict] = []

    for source, target, rule_id in _PHRASE_RULES:
        if source not in normalized:
            continue
        before = normalized
        normalized = normalized.replace(source, target)
        if normalized != before:
            applied.append(
                {
                    "rule_id": rule_id,
                    "source": source,
                    "target": target,
                }
            )

    for pattern, target, rule_id in _SPACING_RULES:
        updated, count = re.subn(pattern, target, normalized)
        if count:
            normalized = updated
            applied.append(
                {
                    "rule_id": rule_id,
                    "source": pattern,
                    "target": target,
                    "count": count,
                }
            )

    confidence = 0.98 if applied else 1.0
    return LanguageNormalizationResult(
        original_text=original,
        normalized_text=normalized,
        normalizations_applied=applied,
        normalization_count=len(applied),
        confidence=confidence,
    ).to_dict()
