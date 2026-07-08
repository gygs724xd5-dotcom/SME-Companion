from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from brain.evidence_runtime import build_evidence_runtime
from brain.evidence_gap_runtime import build_evidence_gap_runtime
from brain.knowledge_runtime import build_knowledge_runtime
from brain.knowledge_skill_bridge import build_knowledge_skill_bridge
from brain.perspective_runtime import build_perspective_runtime
from brain.truth_runtime import build_truth_runtime


BUSINESS_SITUATION_VERSION = "5.5.3"
BUSINESS_SITUATION_SOURCE = "business_situation_runtime"

NO_BUSINESS_SITUATION = "NO_BUSINESS_SITUATION"
COST_CHANGE = "COST_CHANGE"
COST_CORRECTION = "COST_CORRECTION"
PRICING_DECISION = "PRICING_DECISION"
PROFIT_MARGIN_RISK = "PROFIT_MARGIN_RISK"
SALES_OPPORTUNITY = "SALES_OPPORTUNITY"
INVENTORY_RISK = "INVENTORY_RISK"
CUSTOMER_ISSUE = "CUSTOMER_ISSUE"
CASHFLOW_CONCERN = "CASHFLOW_CONCERN"
OPERATIONAL_BOTTLENECK = "OPERATIONAL_BOTTLENECK"
PLANNING_DECISION = "PLANNING_DECISION"
WORKFLOW_STATUS = "WORKFLOW_STATUS"
DATA_QUALITY_ISSUE = "DATA_QUALITY_ISSUE"
GENERAL_BUSINESS_QUESTION = "GENERAL_BUSINESS_QUESTION"

COST = "COST"
PRICING = "PRICING"
SALES = "SALES"
INVENTORY = "INVENTORY"
CUSTOMER = "CUSTOMER"
CASHFLOW = "CASHFLOW"
OPERATIONS = "OPERATIONS"
MARKETING = "MARKETING"
PRODUCT = "PRODUCT"
SUPPLIER = "SUPPLIER"
ACCOUNTING = "ACCOUNTING"
GENERAL = "GENERAL"

ANALYTICAL = "ANALYTICAL"
CAUTIOUS = "CAUTIOUS"
PROACTIVE = "PROACTIVE"
CORRECTIVE = "CORRECTIVE"
EXPLANATORY = "EXPLANATORY"
STRATEGIC = "STRATEGIC"
OPERATIONAL = "OPERATIONAL"
OWNER_ADVISORY = "OWNER_ADVISORY"
NEUTRAL = "NEUTRAL"

NONE = "NONE"
LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"


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


def _bs_normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _bs_lower_text(value: Any) -> str:
    return _bs_normalized_text(value).lower()


def _bs_clamp_confidence(value: Any, default: float = 0.75) -> float:
    if value is None:
        return default
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _bs_contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _bs_has_word(text: str, word: str) -> bool:
    padded = f" {text.replace('.', ' ').replace(',', ' ').replace('?', ' ').replace('!', ' ')} "
    return f" {word} " in padded


def _bs_is_casual_message(text: str) -> bool:
    stripped = text.strip()
    if stripped in {"hi", "hello", "thanks", "thank you", "good morning", "good night"}:
        return True
    return any(_bs_has_word(stripped, word) for word in ("hi", "hello", "thanks")) and not _bs_contains_any(
        stripped,
        ("business", "cost", "price", "sales", "stock", "customer", "cash", "profit", "margin"),
    )


def _bs_nested_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        values: list[str] = []
        for key, item in value.items():
            values.append(str(key))
            values.extend(_bs_nested_values(item))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_bs_nested_values(item))
        return values
    if value in (None, "", [], {}):
        return []
    return [str(value)]


def _bs_context_text(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        parts.extend(_bs_nested_values(value))
    return " ".join(parts).lower()


def _bs_malformed_inputs(
    *,
    extracted_entities: Any,
    evidence_gap_profile: Any,
    business_context: Any,
    active_workflow: Any,
    completed_workflow_context: Any,
    calculation_result: Any,
    recent_context: Any,
) -> list[str]:
    malformed: list[str] = []
    if extracted_entities is not None and not isinstance(extracted_entities, dict):
        malformed.append("extracted_entities")
    if evidence_gap_profile is not None and not isinstance(evidence_gap_profile, dict):
        malformed.append("evidence_gap_profile")
    if business_context is not None and not isinstance(business_context, dict):
        malformed.append("business_context")
    if active_workflow is not None and not isinstance(active_workflow, dict):
        malformed.append("active_workflow")
    if completed_workflow_context is not None and not isinstance(completed_workflow_context, dict):
        malformed.append("completed_workflow_context")
    if calculation_result is not None and not isinstance(calculation_result, dict):
        malformed.append("calculation_result")
    if recent_context is not None and not isinstance(recent_context, list):
        malformed.append("recent_context")
    return malformed


def _bs_evidence_adjustment(evidence_gap_profile: dict) -> tuple[bool, bool, list[str]]:
    if not isinstance(evidence_gap_profile, dict) or not evidence_gap_profile:
        return False, False, []
    gap_type = _bs_normalized_text(evidence_gap_profile.get("gap_type"))
    insufficient = evidence_gap_profile.get("evidence_sufficient") is False
    contradictory = gap_type == "CONTRADICTORY_EVIDENCE" or bool(evidence_gap_profile.get("conflicting_fields"))
    assumptions = []
    if insufficient:
        assumptions.append("Evidence Gap profile indicates evidence is not sufficient.")
    if contradictory:
        assumptions.append("Evidence Gap profile indicates contradictory evidence.")
    return insufficient, contradictory, assumptions


def _bs_workflow_status(active_workflow: dict) -> str:
    if not isinstance(active_workflow, dict):
        return ""
    status = active_workflow.get("workflow_status") or active_workflow.get("status") or active_workflow.get("step")
    return _bs_lower_text(status)


def _bs_domain_from_context(context_text: str) -> str | None:
    domain_markers = (
        (COST, ("cost", "expense", "supplier cost", "cogs")),
        (PRICING, ("price", "pricing", "discount")),
        (SALES, ("sales", "revenue", "lead", "conversion")),
        (INVENTORY, ("inventory", "stock", "out of stock", "shortage")),
        (CUSTOMER, ("customer", "complaint", "support", "review")),
        (CASHFLOW, ("cashflow", "cash flow", "cash shortage", "working capital")),
        (OPERATIONS, ("operation", "bottleneck", "capacity", "staff", "delivery")),
        (MARKETING, ("marketing", "campaign", "content", "post")),
        (PRODUCT, ("product", "sku", "item")),
        (SUPPLIER, ("supplier", "vendor")),
        (ACCOUNTING, ("accounting", "invoice", "tax", "bookkeeping")),
    )
    for domain, markers in domain_markers:
        if _bs_contains_any(context_text, markers):
            return domain
    return None


def _bs_profile(
    *,
    message: str,
    situation_type: str,
    business_domain: str,
    perspective_stance: str,
    risk_level: str,
    opportunity_level: str,
    urgency_level: str,
    owner_attention: str | None,
    recommended_response_posture: str,
    reasoning_summary: str,
    confidence: float,
    assumptions: list[str] | None,
    diagnostics: dict,
) -> dict:
    detected = situation_type != NO_BUSINESS_SITUATION
    clamped_confidence = _bs_clamp_confidence(confidence)
    stable_diagnostics = {
        "business_situation_profile_version": "5.13.1",
        "user_message_present": bool(message),
        "business_situation_detected": detected,
        "business_situation_type": situation_type,
        "business_domain": business_domain,
        "perspective_stance": perspective_stance,
        "business_risk_level": risk_level,
        "business_opportunity_level": opportunity_level,
        "business_urgency_level": urgency_level,
        "owner_attention": owner_attention,
        "recommended_response_posture": recommended_response_posture,
        "business_reasoning_summary": reasoning_summary,
        "business_situation_confidence": clamped_confidence,
        "business_situation_shadow_mode": True,
    }
    stable_diagnostics.update(diagnostics)
    return {
        "situation_detected": detected,
        "situation_type": situation_type,
        "business_domain": business_domain,
        "perspective_stance": perspective_stance,
        "risk_level": risk_level,
        "opportunity_level": opportunity_level,
        "urgency_level": urgency_level,
        "owner_attention": owner_attention,
        "recommended_response_posture": recommended_response_posture,
        "reasoning_summary": reasoning_summary,
        "confidence": clamped_confidence,
        "assumptions": list(assumptions or []),
        "diagnostics": stable_diagnostics,
    }


def evaluate_business_situation(
    user_message: str,
    *,
    intent: str | None = None,
    semantic_type: str | None = None,
    extracted_entities: dict | None = None,
    evidence_gap_profile: dict | None = None,
    truth_confidence: float | None = None,
    business_context: dict | None = None,
    active_workflow: dict | None = None,
    completed_workflow_context: dict | None = None,
    reset_boundary_active: bool = False,
    calculation_result: dict | None = None,
    recent_context: list | None = None,
    owner_goal: str | None = None,
) -> dict:
    """Interpret the business situation behind one user turn.

    This V5.13.1 helper is pure and diagnostic-only. It does not mutate inputs,
    call external services, choose response mode, run workflows, or generate
    final user-facing answer text.
    """
    message = _bs_normalized_text(user_message)
    text = message.lower()
    context = _as_dict(business_context)
    entities = _as_dict(extracted_entities)
    evidence = _as_dict(evidence_gap_profile)
    workflow = _as_dict(active_workflow)
    completed = _as_dict(completed_workflow_context)
    calculation = _as_dict(calculation_result)
    recent = list(recent_context) if isinstance(recent_context, list) else []
    malformed_inputs = _bs_malformed_inputs(
        extracted_entities=extracted_entities,
        evidence_gap_profile=evidence_gap_profile,
        business_context=business_context,
        active_workflow=active_workflow,
        completed_workflow_context=completed_workflow_context,
        calculation_result=calculation_result,
        recent_context=recent_context,
    )
    evidence_insufficient, evidence_contradictory, evidence_assumptions = _bs_evidence_adjustment(evidence)
    truth = _bs_clamp_confidence(truth_confidence, default=1.0)
    workflow_status = _bs_workflow_status(workflow)
    context_text = _bs_context_text(context, entities, calculation, recent)
    completed_context_counted = bool(completed and not reset_boundary_active)
    completed_text = _bs_context_text(completed) if completed_context_counted else ""
    current_context_text = " ".join(part for part in (context_text, completed_text) if part)
    inferred_domain = _bs_domain_from_context(current_context_text)
    intent_text = " ".join([_bs_lower_text(intent), _bs_lower_text(semantic_type)])
    assumptions = list(evidence_assumptions)
    confidence = min(0.82, truth)
    situation_type = NO_BUSINESS_SITUATION
    business_domain = GENERAL
    stance = NEUTRAL
    risk = NONE
    opportunity = NONE
    urgency = NONE
    owner_attention = None
    posture = NEUTRAL
    reason = "no_business_situation_detected"

    if not message:
        confidence = 0.65 if not malformed_inputs else 0.4
        reason = "empty_message"
    elif _bs_is_casual_message(text):
        confidence = 0.9
        reason = "casual_non_business_message"
    elif _bs_contains_any(text, ("workflow status", "status of", "where are we", "are we done", "is it complete")) or workflow_status in {
        "collecting",
        "executing",
        "completed",
        "released",
    } and _bs_contains_any(text, ("status", "done", "complete", "workflow", "step")):
        situation_type = WORKFLOW_STATUS
        business_domain = GENERAL
        stance = OPERATIONAL
        risk = NONE
        urgency = LOW
        posture = OPERATIONAL
        confidence = min(0.86, truth)
        reason = "workflow_status_message"
        owner_attention = "Track workflow state separately from direct business advice."
    elif _bs_contains_any(text, ("i meant", "correction", "correct that", "instead", "actually")) and _bs_contains_any(
        text + " " + intent_text,
        ("cost", "expense", "supplier cost", "unit cost"),
    ):
        situation_type = COST_CORRECTION
        business_domain = COST
        stance = CORRECTIVE
        risk = LOW
        urgency = LOW
        posture = CORRECTIVE
        confidence = min(0.88, truth)
        reason = "cost_correction_detected"
        owner_attention = "Use the corrected cost before interpreting margin or price."
    elif _bs_contains_any(text + " " + intent_text, ("profit", "margin", "break even", "breakeven", "losing money", "not profitable")):
        situation_type = PROFIT_MARGIN_RISK
        business_domain = PRICING if _bs_contains_any(text, ("price", "pricing")) else COST
        stance = ANALYTICAL
        risk = HIGH if _bs_contains_any(text, ("losing money", "negative", "too low", "not profitable")) else MEDIUM
        urgency = MEDIUM
        posture = ANALYTICAL
        confidence = min(0.87, truth)
        reason = "profit_margin_risk_detected"
        owner_attention = "Check whether price, cost, or volume is creating the margin pressure."
    elif _bs_contains_any(text + " " + intent_text, ("price", "pricing", "charge", "discount")) and _bs_contains_any(
        text,
        ("should", "what", "how much", "set", "raise", "lower", "change", "?"),
    ):
        situation_type = PRICING_DECISION
        business_domain = PRICING
        stance = OWNER_ADVISORY
        risk = LOW
        opportunity = MEDIUM
        urgency = LOW
        posture = OWNER_ADVISORY
        confidence = min(0.86, truth)
        reason = "pricing_decision_question"
        owner_attention = "Balance customer willingness to pay against cost and margin."
    elif _bs_contains_any(text + " " + intent_text, ("cost", "expense", "supplier cost", "unit cost", "cogs")) and _bs_contains_any(
        text,
        ("increase", "increased", "higher", "rose", "went up", "decrease", "decreased", "lower", "changed", "now", "from", "to"),
    ):
        situation_type = COST_CHANGE
        business_domain = COST
        stance = ANALYTICAL
        risk = MEDIUM if _bs_contains_any(text, ("increase", "increased", "higher", "rose", "went up")) else LOW
        urgency = LOW
        posture = ANALYTICAL
        confidence = min(0.86, truth)
        reason = "analytical_cost_change_statement"
        owner_attention = "Watch whether the cost movement changes margin or requires a pricing response."
    elif _bs_contains_any(text + " " + intent_text, ("inventory", "stock", "shortage", "out of stock", "run out", "low stock")):
        situation_type = INVENTORY_RISK
        business_domain = INVENTORY
        stance = OPERATIONAL
        risk = HIGH if _bs_contains_any(text, ("out of stock", "run out", "shortage")) else MEDIUM
        urgency = HIGH if risk == HIGH else MEDIUM
        posture = OPERATIONAL
        confidence = min(0.86, truth)
        reason = "inventory_risk_detected"
        owner_attention = "Protect availability while avoiding over-ordering."
    elif _bs_contains_any(text + " " + intent_text, ("complaint", "angry customer", "customer issue", "refund", "support", "bad review", "customer said")):
        situation_type = CUSTOMER_ISSUE
        business_domain = CUSTOMER
        stance = CAUTIOUS
        risk = MEDIUM
        urgency = MEDIUM
        opportunity = LOW
        posture = CAUTIOUS
        confidence = min(0.85, truth)
        reason = "customer_issue_detected"
        owner_attention = "Preserve trust while resolving the specific customer concern."
    elif _bs_contains_any(text + " " + intent_text, ("cashflow", "cash flow", "cash shortage", "short on cash", "working capital", "can't pay", "cannot pay")):
        situation_type = CASHFLOW_CONCERN
        business_domain = CASHFLOW
        stance = CAUTIOUS
        risk = HIGH
        urgency = HIGH
        posture = CAUTIOUS
        confidence = min(0.86, truth)
        reason = "cashflow_concern_detected"
        owner_attention = "Prioritize near-term cash obligations and inflows."
    elif _bs_contains_any(text + " " + intent_text, ("bottleneck", "delay", "capacity", "staff shortage", "too slow", "operation")):
        situation_type = OPERATIONAL_BOTTLENECK
        business_domain = OPERATIONS
        stance = OPERATIONAL
        risk = MEDIUM
        urgency = MEDIUM
        posture = OPERATIONAL
        confidence = min(0.82, truth)
        reason = "operational_bottleneck_detected"
        owner_attention = "Identify the constraint slowing delivery or output."
    elif _bs_contains_any(text + " " + intent_text, ("lead", "sales opportunity", "upsell", "new customer", "big order", "prospect")):
        situation_type = SALES_OPPORTUNITY
        business_domain = SALES
        stance = PROACTIVE
        opportunity = HIGH
        urgency = MEDIUM
        posture = PROACTIVE
        confidence = min(0.82, truth)
        reason = "sales_opportunity_detected"
        owner_attention = "Convert the opportunity without weakening margin or capacity."
    elif _bs_contains_any(text + " " + intent_text, ("what should i do next", "what to do next", "next step", "plan", "planning", "strategy", "focus on")):
        situation_type = PLANNING_DECISION
        business_domain = inferred_domain or GENERAL
        stance = OWNER_ADVISORY
        risk = LOW
        opportunity = MEDIUM
        urgency = LOW
        posture = OWNER_ADVISORY
        confidence = min(0.8, truth)
        reason = "planning_decision_detected"
        owner_attention = "Choose the next business lever with the clearest owner impact."
    elif _bs_contains_any(text + " " + intent_text, ("business", "customer", "sales", "marketing", "product", "supplier", "accounting", "operations")):
        situation_type = GENERAL_BUSINESS_QUESTION
        business_domain = _bs_domain_from_context(text + " " + intent_text) or inferred_domain or GENERAL
        stance = EXPLANATORY
        risk = LOW
        urgency = LOW
        posture = EXPLANATORY
        confidence = min(0.74, truth)
        reason = "general_business_question_detected"
        owner_attention = "Keep the answer tied to the current business decision."
    elif inferred_domain and _bs_contains_any(text, ("should", "what", "how", "next", "improve", "fix", "help")):
        situation_type = GENERAL_BUSINESS_QUESTION
        business_domain = inferred_domain
        stance = OWNER_ADVISORY
        risk = LOW
        urgency = LOW
        posture = OWNER_ADVISORY
        confidence = min(0.68, truth)
        assumptions.append("Business context was used because the current message was generic.")
        reason = "business_context_informed_generic_turn"
        owner_attention = "Use durable business context only as background for the current turn."

    if owner_goal and situation_type != NO_BUSINESS_SITUATION:
        goal = _bs_normalized_text(owner_goal)
        owner_attention = f"{owner_attention or 'Keep the response tied to the owner goal.'} Owner goal: {goal}."

    if evidence_insufficient or evidence_contradictory:
        stance = CAUTIOUS
        posture = CAUTIOUS
        confidence = min(confidence, 0.45 if evidence_contradictory else 0.52)
        if evidence_contradictory:
            risk = MEDIUM if risk in {NONE, LOW} else risk
            reason = f"{reason}_with_contradictory_evidence"
        else:
            reason = f"{reason}_with_insufficient_evidence"
    confidence = min(confidence, truth)

    diagnostics = {
        "intent": intent,
        "semantic_type": semantic_type,
        "truth_confidence": truth,
        "evidence_insufficient": evidence_insufficient,
        "evidence_contradictory": evidence_contradictory,
        "active_workflow_status": workflow_status or None,
        "active_workflow_present": bool(workflow),
        "completed_workflow_context_present": bool(completed),
        "completed_workflow_context_counted": completed_context_counted,
        "reset_boundary_active": bool(reset_boundary_active),
        "business_context_present": bool(context),
        "extracted_entities_present": bool(entities),
        "calculation_result_present": bool(calculation),
        "recent_context_count": len(recent),
        "owner_goal_present": bool(owner_goal),
        "malformed_inputs": malformed_inputs,
        "classification_reason": reason,
        "routing_changed": False,
        "planner_changed": False,
        "workflow_changed": False,
        "responses_changed": False,
        "memory_changed": False,
        "execution_changed": False,
        "commit_boundary_changed": False,
    }
    return _bs_profile(
        message=message,
        situation_type=situation_type,
        business_domain=business_domain,
        perspective_stance=stance,
        risk_level=risk,
        opportunity_level=opportunity,
        urgency_level=urgency,
        owner_attention=owner_attention,
        recommended_response_posture=posture,
        reasoning_summary=reason,
        confidence=confidence,
        assumptions=assumptions,
        diagnostics=diagnostics,
    )


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
    payload = situation.to_dict()
    evidence_runtime = build_evidence_runtime(
        business_situation=payload,
        perception_diagnostics=perception_diagnostics,
        conversation_context={
            "conversation_understanding": understanding,
            "business_context": context,
            "intent_resolution": intent,
        },
        business_memory_reference=state.get("business_memory"),
        structured_business_data={
            "canonical_entities": canonical_entities or {},
            "extracted_entities": extracted_entities or {},
        },
    )
    payload["diagnostics"]["evidence"] = evidence_runtime
    truth_runtime = build_truth_runtime(evidence_runtime=evidence_runtime)
    payload["diagnostics"]["truth"] = truth_runtime
    payload["diagnostics"]["evidence_gap"] = build_evidence_gap_runtime(
        business_situation=payload,
        evidence_runtime=evidence_runtime,
        truth_runtime=truth_runtime,
    )
    payload["diagnostics"]["perspective"] = build_perspective_runtime(
        business_situation=payload,
        evidence_runtime=evidence_runtime,
        truth_runtime=truth_runtime,
        evidence_gap_runtime=payload["diagnostics"]["evidence_gap"],
    )
    payload["diagnostics"]["knowledge"] = build_knowledge_runtime(
        user_message=user_message,
        business_situation=payload,
        perspective_runtime=payload["diagnostics"]["perspective"],
        evidence_runtime=evidence_runtime,
        truth_runtime=truth_runtime,
        conversation_context={
            "conversation_understanding": understanding,
            "business_context": context,
            "intent_resolution": intent,
            "conversation_memory": memory_context,
            "application_state": state,
        },
        structured_business_data={
            "canonical_entities": canonical_entities or {},
            "extracted_entities": extracted_entities or {},
        },
    )
    workflow_state = _as_dict(context.get("workflow_intelligence"))
    workflow_owned_fields = []
    if workflow_state.get("workflow_admission_gate", {}).get("admitted") or workflow_state.get("workflow_action") in {"start_new", "continue", "complete"}:
        workflow_owned_fields = _as_list(workflow_state.get("required_entities")) or _as_list(workflow_state.get("missing_entities"))
    payload["diagnostics"]["knowledge_skill_bridge"] = build_knowledge_skill_bridge(
        {
            "current_message": user_message,
            "normalized_message": user_message,
            "active_topic": payload.get("business_topic"),
            "conversation_context": {
                "conversation_understanding": understanding,
                "business_context": context,
                "intent_resolution": intent,
                "conversation_memory": memory_context,
            },
            "selected_frame": payload["diagnostics"]["perspective"].get("selected_frame"),
            "candidate_frames": payload["diagnostics"]["perspective"].get("candidate_frames") or [],
            "knowledge_runtime_result": payload["diagnostics"]["knowledge"],
            "evidence_runtime_result": evidence_runtime,
            "truth_runtime_result": truth_runtime,
            "clarification_state": {},
            "workflow_state": {
                "workflow_admitted": bool(workflow_state.get("workflow_admission_gate", {}).get("admitted")),
                "workflow_id": workflow_state.get("workflow_id") or workflow_state.get("workflow"),
                "workflow_owned_fields": workflow_owned_fields,
            },
            "business_context": {
                "business_model": (
                    payload["diagnostics"]["knowledge"].get("available_metrics", {}).get("business_model", {}).get("value")
                    or payload["diagnostics"]["knowledge"].get("incomplete_metrics", {}).get("business_model", {}).get("value")
                ),
                "business_type": context.get("business_type"),
            },
            "product_context": {"product": context.get("current_product")},
            "user_goal": resolved_intent,
            "workflow_owned_fields": workflow_owned_fields,
        }
    )
    return payload
