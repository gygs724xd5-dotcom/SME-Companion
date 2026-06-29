from __future__ import annotations

import re
from typing import Any


FIELD_ALIASES = {
    "skill_id": ("skill_id", "Skill ID"),
    "skill_name": ("skill_name", "Skill Name"),
    "business_principle": ("business_principle", "Business Principle"),
    "thinking_pattern": ("thinking_pattern", "Thinking Pattern"),
    "decision_tree": ("decision_tree", "Decision Tree"),
    "ai_should_ask": ("ai_should_ask", "AI Should Ask"),
    "ai_should_avoid": ("ai_should_avoid", "AI Should Avoid"),
    "workflow_integration": ("workflow_integration", "Workflow Integration"),
    "response_mode": ("response_mode", "Response Mode"),
    "memory_tags": ("memory_tags", "Memory Tags"),
    "future_learning_notes": ("future_learning_notes", "Future Learning Notes"),
    "recommended_response": ("recommended_response", "Recommended Response"),
    "confidence": ("confidence", "Confidence"),
}


def _get_field(skill: dict[str, Any] | None, field: str, default: Any = "") -> Any:
    if not isinstance(skill, dict):
        return default

    for key in FIELD_ALIASES.get(field, (field,)):
        if key in skill and skill[key] not in (None, ""):
            return skill[key]
    return default


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if (
        len(text) >= 2
        and text[0] == "`"
        and text[-1] == "`"
        and not text.startswith("```")
        and not text.endswith("```")
    ):
        text = text[1:-1].strip()
    return text


def _extract_numbered_or_bulleted_lines(value: Any) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []

    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        match = re.match(r"^(?:[-*]\s+|\d+[.)]\s+)(.+)$", stripped)
        items.append(match.group(1).strip() if match else stripped)

    return items


def _parse_confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        confidence = float(value)
        return max(0.0, min(1.0, confidence))

    text = _clean_text(value).lower()
    first_sentence = re.split(r"[.!?\n]", text, maxsplit=1)[0]
    if "high" in first_sentence:
        return 0.9
    if "medium" in first_sentence:
        return 0.65
    if "low" in first_sentence:
        return 0.35
    if "high" in text:
        return 0.9
    if "medium" in text:
        return 0.65
    if "low" in text:
        return 0.35
    return 0.5


def extract_business_principle(matched_skill: dict[str, Any] | None) -> str:
    return _clean_text(_get_field(matched_skill, "business_principle"))


def extract_decision_tree(matched_skill: dict[str, Any] | None) -> list[str]:
    text = _clean_text(_get_field(matched_skill, "decision_tree"))
    if not text:
        return []

    text = re.sub(r"^`{1,3}[a-zA-Z0-9_-]*\s*", "", text.strip())
    text = re.sub(r"\s*`{1,3}$", "", text.strip())

    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_questions(matched_skill: dict[str, Any] | None) -> list[str]:
    text = _clean_text(_get_field(matched_skill, "ai_should_ask"))
    if not text:
        return []

    lines = _extract_numbered_or_bulleted_lines(text)
    if len(lines) > 1:
        return lines
    return [text]


def extract_memory_tags(matched_skill: dict[str, Any] | None) -> list[str]:
    value = _get_field(matched_skill, "memory_tags")
    if isinstance(value, (list, tuple, set)):
        return [_clean_text(item) for item in value if _clean_text(item)]

    tags: list[str] = []
    for line in _clean_text(value).splitlines():
        tag = re.sub(r"^[-*]\s+", "", line.strip())
        tag = tag.strip("` ")
        if tag:
            tags.append(tag)
    return tags


def build_reasoning_summary(
    user_message: str,
    matched_skill: dict[str, Any] | None,
) -> str:
    skill_name = _clean_text(_get_field(matched_skill, "skill_name", "matched skill"))
    principle = extract_business_principle(matched_skill)
    if principle:
        return (
            f"Matched business skill '{skill_name}'. Use its business principle, "
            "decision tree, questions, avoidance rules, workflow, response mode, "
            "and memory tags to guide later engines."
        )
    return f"Matched business skill '{skill_name}'. Use available skill fields to guide later engines."


def _build_recommended_action(matched_skill: dict[str, Any] | None) -> str:
    skill_name = _clean_text(_get_field(matched_skill, "skill_name", "business situation"))
    decision_tree = extract_decision_tree(matched_skill)
    if decision_tree:
        return f"Apply the '{skill_name}' decision tree and pass structured guidance to response generation."
    return f"Apply the '{skill_name}' business skill and pass structured guidance to response generation."


def reason_business_message(
    user_message: str,
    matched_skill: dict | None,
    conversation_state: dict | None = None,
) -> dict:
    if matched_skill is None:
        return {
            "skill_found": False,
            "reasoning_summary": "No matching business skill.",
        }

    thinking_pattern = _clean_text(_get_field(matched_skill, "thinking_pattern"))
    questions_to_ask = extract_questions(matched_skill)
    things_to_avoid = _extract_numbered_or_bulleted_lines(
        _get_field(matched_skill, "ai_should_avoid")
    )

    return {
        "skill_found": True,
        "skill_id": _clean_text(_get_field(matched_skill, "skill_id")),
        "skill_name": _clean_text(_get_field(matched_skill, "skill_name")),
        "confidence": _parse_confidence(_get_field(matched_skill, "confidence")),
        "business_principle": extract_business_principle(matched_skill),
        "thinking_pattern": thinking_pattern,
        "decision_tree": extract_decision_tree(matched_skill),
        "recommended_action": _build_recommended_action(matched_skill),
        "recommended_response": _clean_text(
            _get_field(matched_skill, "recommended_response")
        ),
        "questions_to_ask": questions_to_ask,
        "things_to_avoid": things_to_avoid,
        "response_mode": _clean_text(_get_field(matched_skill, "response_mode")),
        "workflow": _clean_text(_get_field(matched_skill, "workflow_integration")),
        "memory_tags": extract_memory_tags(matched_skill),
        "future_learning_notes": _clean_text(
            _get_field(matched_skill, "future_learning_notes")
        ),
        "reasoning_summary": build_reasoning_summary(user_message, matched_skill),
        "reasoning_steps": _extract_numbered_or_bulleted_lines(thinking_pattern),
    }
