from __future__ import annotations

from dataclasses import asdict, is_dataclass
from copy import deepcopy
from typing import Any


PLANNER_MIGRATION_VERSION = "5.2.0"
PLANNER_MIGRATION_SOURCE = "v5_planner_decision_migration"


DECISION_TYPE_TO_INTENT = {
    "Sales Plan": "sales_planning",
    "Cost Calculation": "cost_calculation",
    "Content Plan": "content_planning",
    "Dashboard Request": "business_planning",
    "Marketing": "marketing_strategy",
}


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return deepcopy(value)
    return {}


def _first_text(*values: Any, default: str = "") -> str:
    for value in values:
        if value not in (None, "", [], {}):
            return str(value)
    return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _decision_type_from_knowledge(knowledge_context: dict[str, Any]) -> str:
    guidance = knowledge_context.get("response_guidance") or {}
    if isinstance(guidance, dict):
        explicit = _first_text(guidance.get("decision_type"), guidance.get("task_type"))
        if explicit:
            return explicit

    workflow_candidates = knowledge_context.get("workflow_candidates") or knowledge_context.get("workflow_links") or []
    for workflow in workflow_candidates:
        if not isinstance(workflow, dict):
            continue
        label = _first_text(
            workflow.get("task_type"),
            workflow.get("workflow_name"),
            workflow.get("name"),
            workflow.get("workflow_id"),
            workflow.get("workflow"),
        ).lower()
        if "cost" in label:
            return "Cost Calculation"
        if "content" in label or "post" in label:
            return "Content Plan"
        if "dashboard" in label:
            return "Dashboard Request"
        if "receipt" in label:
            return "Receipt Upload"
        if "sales" in label or "price" in label:
            return "Sales Plan"

    selected = " ".join(
        [
            str(knowledge_context.get("selected_skill") or ""),
            str(knowledge_context.get("selected_domain") or ""),
            str(knowledge_context.get("reasoning_pattern") or ""),
        ]
    ).lower()
    if "cost" in selected:
        return "Cost Calculation"
    if "content" in selected or "marketing" in selected:
        return "Content Plan"
    if "dashboard" in selected:
        return "Dashboard Request"
    if "receipt" in selected:
        return "Receipt Upload"
    if "sales" in selected or "price" in selected:
        return "Sales Plan"
    return ""


def normalize_planner_inputs(
    *,
    knowledge_context: Any = None,
    reasoning_context: Any = None,
    planner_context: Any = None,
    user_message: str | None = None,
) -> dict[str, Any]:
    """Normalize V5 runtime context into legacy planner-compatible hints.

    V5.2.0 Phase 1 keeps the V4 route object as the contract. This function
    only chooses compatible planner input hints and diagnostics.
    """

    knowledge = _as_dict(knowledge_context)
    reasoning = _as_dict(reasoning_context)
    planner = _as_dict(planner_context)

    selected_domain = _first_text(
        knowledge.get("selected_domain"),
        knowledge.get("selected_domain_hint"),
        reasoning.get("selected_domain"),
        planner.get("selected_domain"),
    )
    selected_skill = _first_text(
        knowledge.get("selected_skill"),
        reasoning.get("selected_skill"),
        planner.get("selected_skill"),
    )
    business_goal = _first_text(
        reasoning.get("business_goal"),
        planner.get("business_goal"),
        (planner.get("planner_inputs") or {}).get("user_message") if isinstance(planner.get("planner_inputs"), dict) else None,
        user_message,
    )
    decision_type = _first_text(
        _decision_type_from_knowledge(knowledge),
        reasoning.get("decision_type"),
        planner.get("decision_type"),
        default="unknown",
    )
    confidence = max(
        _float(knowledge.get("confidence")),
        _float(reasoning.get("confidence")),
        _float(planner.get("confidence")),
    )
    decision_intent = DECISION_TYPE_TO_INTENT.get(decision_type)
    has_v5_signal = bool(
        selected_domain
        or selected_skill
        or decision_type not in {"", "unknown"}
        or confidence > 0.0
    )
    can_apply_to_v4 = bool(decision_intent)
    used_v5_context = bool(has_v5_signal and can_apply_to_v4)
    used_legacy_fallback = not used_v5_context
    reason = (
        "v5_context_mapped_to_legacy_planner_inputs"
        if used_v5_context
        else "v5_context_incomplete_or_unmapped_using_v4_fallback"
    )

    return {
        "selected_domain": selected_domain,
        "selected_skill": selected_skill,
        "business_goal": business_goal,
        "decision_type": decision_type,
        "decision_intent": decision_intent,
        "confidence": confidence,
        "used_v5_context": used_v5_context,
        "used_legacy_fallback": used_legacy_fallback,
        "reason": reason,
        "runtime_source": PLANNER_MIGRATION_SOURCE,
        "runtime_version": PLANNER_MIGRATION_VERSION,
        "normalized_inputs": {
            "intent_resolution": {"resolved_intent": decision_intent} if decision_intent else {},
            "business_context": {
                "business_domain": selected_domain,
                "selected_business_skill": selected_skill,
            },
            "planner_message": business_goal or str(user_message or ""),
        },
    }


def apply_planner_migration_to_state(
    application_state: dict | None,
    migration: dict[str, Any] | None,
) -> dict:
    """Return a V4-compatible state snapshot with V5 planner hints applied."""

    state = deepcopy(application_state or {})
    data = migration or {}
    if not data.get("used_v5_context"):
        return state

    intent = data.get("decision_intent")
    if intent:
        existing_intelligence = deepcopy(state.get("conversation_intelligence") or {})
        existing_resolution = deepcopy(
            existing_intelligence.get("intent_resolution")
            or state.get("intent_resolution")
            or ((state.get("conversation") or {}).get("intent_resolution"))
            or {}
        )
        existing_resolution["resolved_intent"] = intent
        existing_intelligence["intent_resolution"] = existing_resolution
        state["intent_resolution"] = existing_resolution
        state["conversation_intelligence"] = existing_intelligence

        conversation = deepcopy(state.get("conversation") or {})
        conversation["intent_resolution"] = existing_resolution
        state["conversation"] = conversation

    business_context = deepcopy(state.get("business_context") or {})
    if data.get("selected_domain"):
        business_context["business_domain"] = data.get("selected_domain")
        business_context["selected_business_domain"] = data.get("selected_domain")
    if data.get("selected_skill"):
        business_context["selected_business_skill"] = data.get("selected_skill")
    if business_context:
        state["business_context"] = business_context
        conversation = deepcopy(state.get("conversation") or {})
        conversation["business_context"] = business_context
        state["conversation"] = conversation

    return state


def planner_migration_diagnostics(migration: dict[str, Any] | None) -> dict[str, Any]:
    data = migration or {}
    return {
        "planner_runtime_source": data.get("runtime_source") or PLANNER_MIGRATION_SOURCE,
        "planner_runtime_version": data.get("runtime_version") or PLANNER_MIGRATION_VERSION,
        "planner_used_v5_context": bool(data.get("used_v5_context")),
        "planner_used_legacy_fallback": bool(data.get("used_legacy_fallback", True)),
        "planner_selected_domain": data.get("selected_domain"),
        "planner_selected_skill": data.get("selected_skill"),
        "planner_business_goal": data.get("business_goal"),
        "planner_decision_type": data.get("decision_type"),
        "planner_confidence": data.get("confidence"),
        "planner_reason": data.get("reason"),
    }
