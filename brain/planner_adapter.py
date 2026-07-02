from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from brain.canonical_objects import PlannerContext


PLANNER_CONTEXT_VERSION = "5.3.2"
PLANNER_CONTEXT_SOURCE = "v5_planner_adapter"


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return dict(value)
    return {}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _nested_get(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_text(*values: Any, default: str = "") -> str:
    for value in values:
        if value not in (None, "", [], {}):
            return str(value)
    return default


def _workflow_owner(workflow_data: dict[str, Any]) -> str:
    return _first_text(
        workflow_data.get("workflow_owner"),
        workflow_data.get("owner_skill_id"),
        workflow_data.get("owner_domain"),
        workflow_data.get("workflow_id"),
        workflow_data.get("workflow"),
        _nested_get(workflow_data, "workflow_state", "owner_skill_id"),
        _nested_get(workflow_data, "workflow_state", "owner_domain"),
        _nested_get(workflow_data, "workflow_state", "workflow_id"),
        _nested_get(workflow_data, "workflow_state", "workflow"),
    )


def _confidence(route: dict[str, Any], knowledge_context: dict[str, Any], reasoning_context: dict[str, Any]) -> float:
    for candidate in (
        reasoning_context.get("confidence"),
        knowledge_context.get("confidence"),
        _nested_get(route, "business_intelligence", "confidence"),
        _nested_get(route, "business_intelligence", "top_confidence"),
        _nested_get(route, "business_context", "confidence"),
    ):
        value = _float(candidate, default=-1.0)
        if value >= 0.0:
            return value
    return 0.0


def build_planner_context(
    route,
    knowledge_context=None,
    reasoning_context=None,
    workflow_state=None,
) -> PlannerContext:
    """Package V5 runtime context for the existing V4 planner.

    The adapter is informational only. It does not execute planner logic, alter
    planner output, route requests, start workflows, or influence responses.
    """

    route_data = _as_dict(route)
    knowledge_data = _as_dict(knowledge_context) or _as_dict(route_data.get("knowledge_context"))
    reasoning_data = _as_dict(reasoning_context) or _as_dict(route_data.get("reasoning_context"))
    workflow_data = _as_dict(workflow_state) or _as_dict(route_data.get("business_workflow"))
    plan = _as_dict(route_data.get("planner_output"))
    canonical_entities = _as_dict(route_data.get("canonical_entities"))

    selected_domain = _first_text(
        reasoning_data.get("selected_domain"),
        knowledge_data.get("selected_domain"),
        route_data.get("selected_business_domain"),
        _nested_get(route_data, "business_intelligence", "matched_domain"),
    )
    selected_skill = _first_text(
        reasoning_data.get("selected_skill"),
        knowledge_data.get("selected_skill"),
        route_data.get("selected_business_skill"),
        _nested_get(route_data, "business_intelligence", "top_skill"),
        _nested_get(route_data, "business_intelligence", "matched_skill", "skill_id"),
    )
    business_goal = _first_text(
        reasoning_data.get("business_goal"),
        plan.get("goal"),
        route_data.get("user_message"),
        _nested_get(route_data, "conversation_understanding", "raw_text"),
    )
    decision_type = _first_text(
        reasoning_data.get("decision_type"),
        plan.get("task_type"),
        route_data.get("task_type"),
        _nested_get(route_data, "intent_resolution", "resolved_intent"),
        default="unknown",
    )

    planner_inputs = {
        "planner_output": plan,
        "knowledge_context_id": knowledge_data.get("knowledge_context_id", ""),
        "reasoning_context_id": reasoning_data.get("reasoning_context_id", ""),
        "intent_resolution": route_data.get("intent_resolution") or {},
        "conversation_understanding": route_data.get("conversation_understanding") or {},
        "canonical_entities": canonical_entities,
    }
    planner_hints = {
        "selected_domain": selected_domain,
        "selected_skill": selected_skill,
        "business_goal": business_goal,
        "decision_type": decision_type,
        "recommended_next_action": reasoning_data.get("recommended_next_action", ""),
        "reasoning_pattern": reasoning_data.get("reasoning_pattern", ""),
        "missing_entities": reasoning_data.get("missing_entities") or [],
        "workflow_owner": _workflow_owner(workflow_data),
        "canonical_entity_slots": canonical_entities.get("slots") or {},
    }
    planner_constraints = [
        "diagnostics_only",
        "existing_v4_planner_output_is_source_of_truth",
        "do_not_change_routing",
        "do_not_change_workflow",
        "do_not_change_response",
    ]

    diagnostics = {
        "planner_context_created": True,
        "planner_context_version": PLANNER_CONTEXT_VERSION,
        "planner_context_source": PLANNER_CONTEXT_SOURCE,
        "runtime_mode": "diagnostics_only",
        "planner_decision_owner": "existing_v4_path",
        "planner_logic_executed": False,
        "knowledge_context_present": bool(knowledge_data),
        "reasoning_context_present": bool(reasoning_data),
        "workflow_state_present": bool(workflow_data),
        "canonical_entities_present": bool(canonical_entities),
        "canonical_entity_count": len(canonical_entities.get("entities") or []),
        "canonical_entity_slots": sorted((canonical_entities.get("slots") or {}).keys()),
        "canonical_entities_usage": "supporting_context_only",
    }

    return PlannerContext(
        selected_domain=selected_domain,
        selected_skill=selected_skill,
        business_goal=business_goal,
        decision_type=decision_type,
        workflow_owner=planner_hints["workflow_owner"],
        workflow_state=workflow_data,
        planner_inputs=planner_inputs,
        planner_hints=planner_hints,
        planner_constraints=planner_constraints,
        confidence=_confidence(route_data, knowledge_data, reasoning_data),
        diagnostics=diagnostics,
        version=PLANNER_CONTEXT_VERSION,
    )
