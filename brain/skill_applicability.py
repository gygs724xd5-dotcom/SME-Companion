from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from brain.knowledge_skill_reference import as_dict, as_list


SKILL_APPLICABILITY_VERSION = "5.9.1"


@dataclass
class SkillApplicabilityResult:
    skill_id: str
    status: str
    matched_conditions: list = field(default_factory=list)
    unmet_conditions: list = field(default_factory=list)
    unknown_conditions: list = field(default_factory=list)
    excluded_conditions: list = field(default_factory=list)
    support_strength: float = 0.0
    reason: str = ""
    version: str = SKILL_APPLICABILITY_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _lookup(field: str, context: dict) -> Any:
    if field in context.get("current_turn", {}):
        return context["current_turn"][field]
    if field in context.get("business_context", {}):
        return context["business_context"][field]
    if field in context.get("conversation_context", {}):
        return context["conversation_context"][field]
    return context.get(field)


def _condition_passes(condition: dict, context: dict) -> tuple[str, bool | None]:
    field = str(condition.get("field") or "")
    operator = str(condition.get("operator") or "equals")
    expected = condition.get("value", condition.get("values"))
    value = _lookup(field, context)
    if operator == "exists":
        return field, value not in (None, "", [], {})
    if operator == "missing":
        return field, value in (None, "", [], {})
    if value in (None, "", [], {}):
        return field, None
    if operator == "equals":
        return field, value == expected
    if operator == "not_equals":
        return field, value != expected
    if operator == "in":
        return field, value in as_list(expected)
    if operator == "not_in":
        return field, value not in as_list(expected)
    if operator == "contains":
        return field, str(expected) in str(value)
    return field, None


def evaluate_skill_applicability(skill: Any, context: dict | None = None) -> SkillApplicabilityResult:
    context = context or {}
    applicability = as_dict(getattr(skill, "applicability", {}))
    exclusions = as_dict(getattr(skill, "exclusion_conditions", {}))
    matched, unmet, unknown, excluded = [], [], [], []
    for condition in as_list(exclusions.get("any")) + as_list(exclusions.get("all")):
        if not isinstance(condition, dict):
            continue
        name, result = _condition_passes(condition, context)
        if result is True:
            excluded.append(name)
    if excluded:
        return SkillApplicabilityResult(skill.skill_id, "EXCLUDED", excluded_conditions=excluded, support_strength=0.0, reason="explicit exclusion condition matched")
    if not applicability:
        return SkillApplicabilityResult(skill.skill_id, "APPLICABLE", support_strength=0.65, reason="no applicability limits declared")
    group_results = []
    for group in ("all", "any", "none"):
        conditions = [item for item in as_list(applicability.get(group)) if isinstance(item, dict)]
        if not conditions:
            continue
        results = [_condition_passes(condition, context) for condition in conditions]
        for name, result in results:
            if result is True:
                matched.append(name)
            elif result is False:
                unmet.append(name)
            else:
                unknown.append(name)
        bools = [result for _, result in results]
        if group == "all":
            group_results.append(all(value is True for value in bools) if None not in bools else None)
        elif group == "any":
            group_results.append(any(value is True for value in bools) if not all(value is None for value in bools) else None)
        elif group == "none":
            group_results.append(not any(value is True for value in bools) if None not in bools else None)
    if any(result is False for result in group_results):
        status = "NOT_APPLICABLE"
        strength = 0.0
    elif any(result is None for result in group_results):
        status = "APPLICABILITY_UNKNOWN"
        strength = 0.35
    elif matched:
        status = "APPLICABLE"
        strength = 0.9
    else:
        status = "PARTIALLY_APPLICABLE"
        strength = 0.55
    return SkillApplicabilityResult(skill.skill_id, status, matched, unmet, unknown, excluded, strength, status.lower())
