from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from brain.canonical_objects import KnowledgeContext, ReasoningContext


REASONING_RUNTIME_VERSION = "5.1.3"
REASONING_RUNTIME_SOURCE = "business_reasoning_runtime"


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


def _as_list(value: Any) -> list[Any]:
    if value in (None, "", {}):
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def _compact_list(values: list[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        if value in (None, "", [], {}):
            continue
        key = repr(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


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


def _known_entities(route: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
    extracted = route.get("extracted_entities") or {}
    if isinstance(extracted, dict) and isinstance(extracted.get("extracted_entities"), dict):
        extracted = extracted.get("extracted_entities") or {}
    business_context_entities = _nested_get(route, "business_context", "extracted_entities")
    memory_entities = memory.get("entities") if isinstance(memory.get("entities"), dict) else {}

    known: dict[str, Any] = {}
    for source in (memory_entities, business_context_entities, extracted):
        if isinstance(source, dict):
            known.update({key: value for key, value in source.items() if value not in (None, "", [], {})})
    return known


def _missing_entities(
    route: dict[str, Any],
    knowledge_context: dict[str, Any],
    workflow_state: dict[str, Any],
    known_entities: dict[str, Any],
) -> list[Any]:
    workflow_missing = (
        workflow_state.get("missing_entities")
        or workflow_state.get("missing_fields")
        or _nested_get(route, "business_workflow", "missing_entities")
        or _nested_get(route, "business_context", "missing_entities")
        or []
    )
    required = knowledge_context.get("required_entities") or []
    inferred_missing = []
    known_keys = {str(key).lower() for key in known_entities.keys()}
    for entity in required:
        entity_name = str(entity or "").strip()
        if entity_name and entity_name.lower() not in known_keys:
            inferred_missing.append(entity)
    return _compact_list([*_as_list(workflow_missing), *inferred_missing])


def _business_goal(route: dict[str, Any], knowledge_context: dict[str, Any]) -> str:
    skill = knowledge_context.get("selected_skill") or ""
    for candidate in knowledge_context.get("candidate_skills") or []:
        if isinstance(candidate, dict) and candidate.get("skill_id") == skill:
            metadata = candidate.get("metadata") or {}
            business_goal = metadata.get("business_goal")
            if business_goal:
                return str(business_goal)
    return str(
        _nested_get(route, "planner_output", "goal")
        or route.get("user_message")
        or _nested_get(route, "conversation_understanding", "raw_text")
        or ""
    )


def _decision_type(route: dict[str, Any]) -> str:
    return str(
        _nested_get(route, "planner_output", "task_type")
        or route.get("task_type")
        or _nested_get(route, "intent_resolution", "resolved_intent")
        or "unknown"
    )


def _business_stage(route: dict[str, Any], knowledge_context: dict[str, Any], workflow_state: dict[str, Any]) -> str:
    if workflow_state.get("status"):
        return str(workflow_state.get("status"))
    if _nested_get(route, "business_workflow", "workflow_stage"):
        return str(_nested_get(route, "business_workflow", "workflow_stage"))
    skill = knowledge_context.get("selected_skill") or ""
    for candidate in knowledge_context.get("candidate_skills") or []:
        if isinstance(candidate, dict) and candidate.get("skill_id") == skill:
            stage = ((candidate.get("metadata") or {}).get("legacy_fields") or {}).get("conversation_stage")
            if stage:
                return str(stage)
    return ""


def _recommended_next_action(route: dict[str, Any], workflow_state: dict[str, Any]) -> str:
    return str(
        workflow_state.get("next_required_action")
        or workflow_state.get("next_action")
        or _nested_get(route, "business_workflow", "next_action")
        or _nested_get(route, "planner_output", "next_step")
        or ""
    )


def _confidence(route: dict[str, Any], knowledge_context: dict[str, Any]) -> float:
    candidates = [
        knowledge_context.get("confidence"),
        _nested_get(route, "business_intelligence", "confidence"),
        _nested_get(route, "business_intelligence", "top_confidence"),
        _nested_get(route, "business_context", "confidence"),
    ]
    for candidate in candidates:
        value = _float(candidate, default=-1.0)
        if value >= 0.0:
            return value
    return 0.0


def build_reasoning_context(
    route,
    knowledge_context=None,
    workflow_state=None,
    memory=None,
) -> ReasoningContext:
    """Create diagnostics-only V5.1.3 business reasoning context.

    This adapter infers high-level context from existing runtime artifacts. It
    does not choose routes, change planner output, execute workflows, or render
    responses.
    """

    route_data = _as_dict(route)
    knowledge_data = _as_dict(knowledge_context) or _as_dict(route_data.get("knowledge_context"))
    workflow_data = _as_dict(workflow_state) or _as_dict(route_data.get("business_workflow"))
    memory_data = _as_dict(memory) or _as_dict(route_data.get("conversation_memory"))

    known = _known_entities(route_data, memory_data)
    missing = _missing_entities(route_data, knowledge_data, workflow_data, known)
    selected_domain = str(
        knowledge_data.get("selected_domain")
        or route_data.get("selected_business_domain")
        or _nested_get(route_data, "business_intelligence", "matched_domain")
        or ""
    )
    selected_skill = str(
        knowledge_data.get("selected_skill")
        or route_data.get("selected_business_skill")
        or _nested_get(route_data, "business_intelligence", "top_skill")
        or ""
    )
    reasoning_pattern = str(
        knowledge_data.get("reasoning_pattern")
        or _nested_get(route_data, "business_intelligence", "thinking_pattern")
        or ""
    )
    assumptions = _compact_list(
        [
            "existing_planner_decision_is_source_of_truth",
            *(_as_list(_nested_get(route_data, "reasoning", "assumptions"))),
        ]
    )

    diagnostics = {
        "reasoning_runtime_created": True,
        "reasoning_runtime_version": REASONING_RUNTIME_VERSION,
        "reasoning_source": REASONING_RUNTIME_SOURCE,
        "runtime_mode": "diagnostics_only",
        "planner_decision_owner": "existing_v4_path",
        "workflow_decision_owner": "existing_workflow_runtime",
        "response_decision_owner": "existing_response_pipeline",
        "knowledge_context_present": bool(knowledge_data),
    }

    return ReasoningContext(
        knowledge_context_id=str(knowledge_data.get("knowledge_context_id") or ""),
        business_goal=_business_goal(route_data, knowledge_data),
        decision_type=_decision_type(route_data),
        business_stage=_business_stage(route_data, knowledge_data, workflow_data),
        selected_domain=selected_domain,
        selected_skill=selected_skill,
        known_entities=known,
        missing_entities=missing,
        assumptions=assumptions,
        risks=_compact_list(_as_list(_nested_get(route_data, "business_intelligence", "risks"))),
        opportunities=_compact_list(_as_list(_nested_get(route_data, "business_intelligence", "opportunities"))),
        recommended_next_action=_recommended_next_action(route_data, workflow_data),
        reasoning_pattern=reasoning_pattern,
        confidence=_confidence(route_data, knowledge_data),
        diagnostics=diagnostics,
        version=REASONING_RUNTIME_VERSION,
    )


def create_reasoning_context(
    route,
    knowledge_context: KnowledgeContext | dict | None = None,
    workflow_state=None,
    memory=None,
) -> ReasoningContext:
    return build_reasoning_context(
        route,
        knowledge_context=knowledge_context,
        workflow_state=workflow_state,
        memory=memory,
    )
