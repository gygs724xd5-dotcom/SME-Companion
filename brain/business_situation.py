from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


BUSINESS_SITUATION_VERSION = "5.5.3"
BUSINESS_SITUATION_SOURCE = "business_situation_runtime"


BUSINESS_ALIASES = {
    "bakery": "bakery",
    "coffee shop": "coffee_shop",
    "fish shop": "fish_shop",
    "restaurant": "restaurant",
    "tea shop": "tea_shop",
}


def _new_id() -> str:
    return f"business_situation_{uuid4().hex}"


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if value in (None, "", {}, ()):
        return []
    return [value]


def _first_text(*values: Any, default: str = "") -> str:
    for value in values:
        if value not in (None, "", [], {}):
            return str(value)
    return default


def _normalize_business(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.replace("-", " ").replace("_", " ")
    for alias, normalized in BUSINESS_ALIASES.items():
        if alias in text:
            return normalized
    words = [word for word in text.split() if word not in {"a", "an", "the", "my", "our", "business", "store"}]
    if len(words) <= 4 and any(word in words for word in {"shop", "store", "bakery", "restaurant"}):
        return "_".join(words)
    return ""


def _extract_conversation_business(user_message: str, business_context: dict) -> str:
    message_value = _normalize_business(user_message)
    if message_value:
        return message_value
    source = str(business_context.get("source") or "")
    if source in {"current_message", "workflow", "conversation_memory"}:
        return _normalize_business(
            _first_text(
                business_context.get("business_type"),
                business_context.get("current_product"),
            )
        )
    return ""


def _latest_memory_payload(memory: Any) -> dict:
    if isinstance(memory, list):
        for event in reversed(memory):
            payload = event.get("payload") if isinstance(event, dict) and isinstance(event.get("payload"), dict) else event
            if isinstance(payload, dict) and payload:
                return payload
        return {}
    memory_dict = _as_dict(memory)
    events = _as_list(memory_dict.get("events"))
    for event in reversed(events):
        payload = event.get("payload") if isinstance(event, dict) and isinstance(event.get("payload"), dict) else event
        if isinstance(payload, dict) and payload:
            return payload
    return memory_dict


def _store_profile(state: dict) -> dict:
    store = _as_dict(state.get("store"))
    if isinstance(store.get("profile"), dict):
        return _as_dict(store.get("profile"))
    return store


def _extract_memory_business(application_state: dict) -> str:
    memory = _latest_memory_payload(application_state.get("business_memory"))
    store = _store_profile(application_state)
    return _normalize_business(
        _first_text(
            memory.get("business_type"),
            memory.get("store_type"),
            memory.get("business"),
            store.get("business_type"),
            store.get("store_type"),
            store.get("business"),
        )
    )


def _runtime_situation(
    *,
    user_message: str,
    application_state: dict,
    business_context: dict,
    planner_output: dict,
    perception_diagnostics: dict | None,
) -> dict:
    conversation_business = _extract_conversation_business(user_message, business_context)
    situation_business = _normalize_business(business_context.get("business_type"))
    memory_business = _extract_memory_business(application_state)
    current_business = conversation_business or situation_business or memory_business
    if conversation_business:
        business_source = "conversation_runtime"
    elif situation_business:
        business_source = "business_situation"
    elif memory_business:
        business_source = "business_memory"
    else:
        business_source = "unknown"

    current_goal = _first_text(
        business_context.get("current_goal"),
        planner_output.get("goal"),
        default="",
    )
    goal_source = "conversation_runtime" if business_context.get("current_goal") else ("planner" if planner_output.get("goal") else "unknown")
    current_problem = _first_text(business_context.get("current_problem"), default="")
    problem_source = "conversation_runtime" if current_problem else "unknown"
    current_operation = _first_text(
        planner_output.get("workflow"),
        planner_output.get("task_type"),
        business_context.get("current_campaign"),
        default="",
    )
    current_focus = _first_text(
        business_context.get("current_discussion_topic"),
        business_context.get("current_product"),
        current_goal,
        user_message,
        default="",
    )
    memory_conflict = bool(
        conversation_business
        and memory_business
        and conversation_business != memory_business
    )
    situation_confidence = 0.95 if conversation_business else float(business_context.get("confidence") or (0.45 if memory_business else 0.0))
    diagnostics = {
        "business_source": business_source,
        "goal_source": goal_source,
        "problem_source": problem_source,
        "memory_conflict": memory_conflict,
        "memory_value": memory_business,
        "conversation_value": conversation_business,
        "current_value": current_business,
        "override_reason": "conversation_runtime_overrides_durable_memory" if memory_conflict else "",
        "runtime_only": True,
        "diagnostic_only": True,
        "routing_changed": False,
        "planner_changed": False,
        "workflow_changed": False,
        "responses_changed": False,
        "memory_changed": False,
        "execution_changed": False,
        "commit_boundary_changed": False,
    }
    return {
        "current_business": current_business,
        "current_goal": current_goal,
        "current_problem": current_problem,
        "current_operation": current_operation,
        "current_focus": current_focus,
        "situation_confidence": situation_confidence,
        "situation_source": business_source,
        "situation_diagnostics": diagnostics,
    }


def _unique(values: list[Any]) -> list:
    result = []
    seen = set()
    for value in values:
        if value in (None, "", [], {}):
            continue
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _extract_relevant_entities(canonical_entities: dict | None, extracted_entities: dict | None) -> dict:
    canonical = _as_dict(canonical_entities)
    extracted = _as_dict(extracted_entities)
    slots = _as_dict(canonical.get("slots"))
    entities = _as_list(canonical.get("entities"))
    extracted_payload = _as_dict(extracted.get("extracted_entities")) or extracted
    return {
        "canonical_slots": slots,
        "canonical_entities": entities,
        "extracted_entities": extracted_payload,
    }


def _conversation_purpose(intent: str | None, task_type: str | None = None) -> str:
    value = str(intent or "").strip().lower()
    task = str(task_type or "").strip().lower()
    if value in {"customer_reply", "customer_says_expensive"}:
        return "support"
    if value in {"pricing_question", "cost_calculation", "profit_calculation"} or "calculation" in task:
        return "analyze"
    if value in {"sales_planning", "marketing_strategy", "content_planning"}:
        return "recommend"
    if value in {"business_context_update", "reference_resolution"}:
        return "clarify"
    if value in {"general_question", "label_explanation"}:
        return "explain"
    return "help"


def _business_topic(business_context: dict, intent_resolution: dict, planner_output: dict | None = None) -> str:
    plan = _as_dict(planner_output)
    return _first_text(
        business_context.get("current_discussion_topic"),
        business_context.get("business_type"),
        intent_resolution.get("resolved_intent"),
        plan.get("task_type"),
        default="general_business",
    )


def _known_evidence(
    user_message: str,
    conversation_understanding: dict,
    business_context: dict,
    memory_context: dict | None = None,
    canonical_entities: dict | None = None,
) -> list[dict]:
    evidence = []
    if str(user_message or "").strip():
        evidence.append(
            {
                "source": "user",
                "kind": "current_message",
                "summary": str(user_message or "").strip(),
                "confidence": 1.0,
            }
        )
    detected_intent = conversation_understanding.get("detected_intent") or business_context.get("detected_intent")
    if detected_intent:
        evidence.append(
            {
                "source": "conversation_understanding",
                "kind": "detected_intent",
                "summary": detected_intent,
                "confidence": conversation_understanding.get("confidence")
                or business_context.get("intent_confidence"),
            }
        )
    if business_context.get("business_type"):
        evidence.append(
            {
                "source": "business_context",
                "kind": "business_type",
                "summary": business_context.get("business_type"),
                "confidence": business_context.get("confidence"),
            }
        )
    memory = _as_dict(memory_context)
    if memory:
        evidence.append(
            {
                "source": "memory",
                "kind": "conversation_memory",
                "summary": {
                    key: memory.get(key)
                    for key in ("last_intent", "previous_intent", "business_topic")
                    if memory.get(key) not in (None, "", [], {})
                },
                "confidence": memory.get("confidence"),
            }
        )
    canonical = _as_dict(canonical_entities)
    if canonical.get("entities") or canonical.get("slots"):
        evidence.append(
            {
                "source": "canonical_entities",
                "kind": "business_entities",
                "summary": {
                    "slots": canonical.get("slots") or {},
                    "entity_count": len(canonical.get("entities") or []),
                },
                "confidence": canonical.get("confidence"),
            }
        )
    return evidence


def _material_uncertainty(
    business_context: dict,
    extracted_entities: dict | None = None,
    planner_output: dict | None = None,
) -> list[dict]:
    uncertainties = []
    for conflict in _as_list(business_context.get("conflicts")):
        uncertainties.append(
            {
                "kind": "context_conflict",
                "description": conflict,
                "why_material": "Conflicting business context may change judgment.",
            }
        )
    extracted = _as_dict(extracted_entities)
    for entity in _as_list(extracted.get("missing_entities")):
        uncertainties.append(
            {
                "kind": "entity_uncertainty",
                "description": entity,
                "why_material": "The entity may affect business understanding if the current task depends on it.",
            }
        )
    plan = _as_dict(planner_output)
    for item in _as_list(plan.get("missing_information")):
        uncertainties.append(
            {
                "kind": "planning_uncertainty",
                "description": item,
                "why_material": "The planner currently treats this as potentially relevant context.",
            }
        )
    return uncertainties


def _constraints(business_context: dict, canonical_entities: dict | None = None) -> list:
    values = []
    values.extend(_as_list(business_context.get("constraints")))
    slots = _as_dict(_as_dict(canonical_entities).get("slots"))
    for key in ("budget", "deadline", "time", "quantity", "capacity"):
        if slots.get(key) not in (None, "", [], {}):
            values.append({key: slots.get(key)})
    return _unique(values)


def _risks(intent: str | None, task_type: str | None, business_context: dict) -> list[str]:
    risks = list(_as_list(business_context.get("risks")))
    value = str(intent or "").lower()
    task = str(task_type or "").lower()
    if value in {"pricing_question", "cost_calculation", "profit_calculation"} or "calculation" in task:
        risks.append("financial_accuracy_risk")
    if value in {"customer_reply", "customer_says_expensive"}:
        risks.append("customer_trust_risk")
    if value in {"marketing_strategy", "content_planning"} or "marketing" in task or "content" in task:
        risks.append("brand_message_risk")
    return _unique(risks)


def _opportunities(intent: str | None, task_type: str | None, business_context: dict) -> list[str]:
    opportunities = list(_as_list(business_context.get("opportunities")))
    value = str(intent or "").lower()
    task = str(task_type or "").lower()
    if value in {"sales_planning", "marketing_strategy", "content_planning"} or "sales" in task or "marketing" in task:
        opportunities.append("revenue_growth")
    if value in {"customer_reply", "customer_says_expensive"}:
        opportunities.append("customer_retention")
    if value in {"cost_calculation", "profit_calculation"} or "calculation" in task:
        opportunities.append("margin_clarity")
    return _unique(opportunities)


@dataclass
class BusinessSituation:
    situation_id: str = field(default_factory=_new_id)
    objective: str = ""
    business_context: dict = field(default_factory=dict)
    known_evidence: list = field(default_factory=list)
    known_constraints: list = field(default_factory=list)
    material_uncertainty: list = field(default_factory=list)
    relevant_business_entities: dict = field(default_factory=dict)
    business_topic: str = "general_business"
    conversation_purpose: str = "help"
    required_capabilities: list = field(default_factory=list)
    potential_business_risks: list = field(default_factory=list)
    potential_opportunities: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    current_business: str = ""
    current_goal: str = ""
    current_problem: str = ""
    current_operation: str = ""
    current_focus: str = ""
    situation_confidence: float = 0.0
    situation_source: str = "unknown"
    situation_diagnostics: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)
    version: str = BUSINESS_SITUATION_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def build_business_situation(
    *,
    user_message: str,
    application_state: dict | None = None,
    conversation_understanding: dict | None = None,
    business_context: dict | None = None,
    intent_resolution: dict | None = None,
    canonical_entities: dict | None = None,
    extracted_entities: dict | None = None,
    planner_output: dict | None = None,
    perception_diagnostics: dict | None = None,
) -> dict:
    """Build an additive V5.4 Business Situation context.

    The object is semantic context only. It does not route, execute, authorize
    commits, or build responses.
    """

    state = _as_dict(application_state)
    understanding = _as_dict(conversation_understanding)
    context = _as_dict(business_context)
    intent = _as_dict(intent_resolution)
    plan = _as_dict(planner_output)
    memory_context = (
        state.get("conversation_memory")
        or _as_dict(state.get("conversation")).get("conversation_memory")
        or {}
    )
    resolved_intent = _first_text(
        intent.get("resolved_intent"),
        context.get("current_message_intent"),
        context.get("detected_intent"),
        understanding.get("detected_intent"),
    )
    objective = _first_text(
        plan.get("goal"),
        understanding.get("planner_message"),
        intent.get("planner_message"),
        user_message,
    )
    task_type = plan.get("task_type")
    required_capabilities = _unique(_as_list(plan.get("required_skills")) + _as_list(plan.get("task_type")))
    runtime = _runtime_situation(
        user_message=user_message,
        application_state=state,
        business_context=context,
        planner_output=plan,
        perception_diagnostics=perception_diagnostics,
    )

    situation = BusinessSituation(
        objective=objective,
        business_context={
            "detected_intent": resolved_intent,
            "business_type": context.get("business_type"),
            "current_message_intent": context.get("current_message_intent"),
            "previous_context_intent": context.get("previous_context_intent"),
            "intent_changed": bool(context.get("intent_changed")),
            "source": context.get("source"),
            "confidence": context.get("confidence"),
        },
        known_evidence=_known_evidence(user_message, understanding, context, memory_context, canonical_entities),
        known_constraints=_constraints(context, canonical_entities),
        material_uncertainty=_material_uncertainty(context, extracted_entities, plan),
        relevant_business_entities=_extract_relevant_entities(canonical_entities, extracted_entities),
        business_topic=_business_topic(context, intent, plan),
        conversation_purpose=_conversation_purpose(resolved_intent, task_type),
        required_capabilities=required_capabilities,
        potential_business_risks=_risks(resolved_intent, task_type, context),
        potential_opportunities=_opportunities(resolved_intent, task_type, context),
        assumptions=[
            "Business Situation is runtime context only in V5.5.3.",
            "Existing routing, response, and commit behavior remain authoritative for runtime compatibility.",
            "Current Business Situation may override durable Business Memory only inside the active runtime.",
        ],
        current_business=runtime["current_business"],
        current_goal=runtime["current_goal"],
        current_problem=runtime["current_problem"],
        current_operation=runtime["current_operation"],
        current_focus=runtime["current_focus"],
        situation_confidence=runtime["situation_confidence"],
        situation_source=runtime["situation_source"],
        situation_diagnostics=runtime["situation_diagnostics"],
        diagnostics={
            "business_situation_created": True,
            "business_situation_version": BUSINESS_SITUATION_VERSION,
            "business_situation_source": BUSINESS_SITUATION_SOURCE,
            "runtime_mode": "compatibility_context_only",
            "routes_changed": False,
            "routing_changed": False,
            "planner_changed": False,
            "workflow_changed": False,
            "responses_changed": False,
            "memory_changed": False,
            "execution_changed": False,
            "commit_boundary_changed": False,
            "runtime": runtime["situation_diagnostics"],
            "perception": _as_dict(perception_diagnostics),
        },
    )
    return situation.to_dict()
