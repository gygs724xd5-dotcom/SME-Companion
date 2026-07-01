from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json

from brain.business_workflow_engine import decide_business_workflow
from brain.conversation_manager import active_workflow_state, planner_locked
from brain.business_context_engine import build_business_context, sanitize_user_context_text
from brain.business_entity_extractor import extract_business_entities
from brain.business_intelligence_bridge import (
    inject_business_intelligence,
    run_business_intelligence_bridge,
)
from brain.business_knowledge_runtime import (
    KNOWLEDGE_CONTEXT_VERSION,
    KNOWLEDGE_RUNTIME_SOURCE,
    create_knowledge_context,
)
from brain.business_reasoning_runtime import (
    REASONING_RUNTIME_SOURCE,
    REASONING_RUNTIME_VERSION,
    create_reasoning_context,
)
from brain.planner_adapter import (
    PLANNER_CONTEXT_SOURCE,
    PLANNER_CONTEXT_VERSION,
    build_planner_context,
)
from brain.planner_migration import (
    apply_planner_migration_to_state,
    normalize_planner_inputs,
    planner_migration_diagnostics,
)
from brain.business_intent_engine import detect_business_intent
from brain.capability_registry import get_capability, is_capability_available
from brain.conversation_memory_engine import get_last_context, remember_turn
from brain.conversation_understanding_engine import understand_conversation
from brain.intent_resolver import resolve_intent
from brain.llm_orchestrator import build_reasoning_context, decide_llm_usage
from brain.planner_engine import build_execution_plan
from brain.reasoning_engine import build_reasoning
from brain.response_transformation_engine import detect_response_transformation, transformation_source
from brain.response_envelope_runtime import build_response_envelope, response_envelope_diagnostics
from brain.skill_loader import load_skills
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.business_skill_registry import registry_diagnostics


BYPASS_WORKFLOW_RESPONSE_INTENTS = {
    "general_question",
    "label_explanation",
    "customer_reply",
    "customer_says_expensive",
    "marketing_content",
    "business_advice",
    "unknown_with_question",
}

PLACEHOLDER_ENGINES = {
    "ocr_engine": None,
    "inventory_engine": None,
    "sales_forecast_engine": None,
    "business_memory": None,
    "marketing_agent": None,
    "financial_agent": None,
    "inventory_agent": None,
}


TASK_CAPABILITY_NAMES = {
    "Sales Plan": "Sales Plan",
    "Content Plan": "Content Plan",
    "Cost Calculation": "Cost Calculation",
    "Dashboard Request": "Dashboard Request",
    "Receipt Upload": "Receipt Upload",
    "Product Feedback": "Product Feedback",
    "Developer Intelligence": "Developer Intelligence",
    "Marketing": "Content Plan",
    "Business Consulting": "Conversation Memory",
    "General Business Help": "Conversation Memory",
    "OCR": "OCR",
    "Inventory": "Inventory",
    "POS Sync": "POS Sync",
    "Business Forecast": "Business Forecast",
}


def _serialize_skill(skill) -> dict:
    if is_dataclass(skill):
        return asdict(skill)
    return dict(skill or {})


def _reasoning_mode(plan: dict, reasoning: dict) -> str:
    if reasoning.get("response_mode"):
        return str(reasoning.get("response_mode"))
    if plan.get("estimated_response_mode"):
        return str(plan.get("estimated_response_mode"))
    return "unknown"


def _prompt_context_size(context: dict | None) -> int:
    return len(json.dumps(context or {}, ensure_ascii=False, default=str))


def _selected_business_skill(bridge_result: dict | None, reasoning: dict | None) -> str | None:
    bridge = bridge_result or {}
    matched = bridge.get("matched_skill") or {}
    if isinstance(matched, dict):
        return matched.get("skill_id") or matched.get("skill_name")
    return bridge.get("top_skill") or (reasoning or {}).get("business_skill_id")


def _matched_intents(plan: dict | None, interpretation: dict | None, intent_resolution: dict | None, reasoning: dict | None) -> list[str]:
    intents = [
        (intent_resolution or {}).get("resolved_intent"),
        (intent_resolution or {}).get("resolved_workflow"),
        (interpretation or {}).get("detected_intent"),
        (interpretation or {}).get("legacy_intent"),
        (plan or {}).get("task_type"),
        (plan or {}).get("workflow"),
        (reasoning or {}).get("action"),
    ]
    return [str(intent) for intent in intents if intent not in (None, "", [], {})]


def _previous_context_intent(state: dict | None, memory_context: dict | None = None) -> str | None:
    state = state or {}
    conversation = state.get("conversation") or {}
    candidates = [
        (memory_context or {}).get("last_intent"),
        (memory_context or {}).get("previous_intent"),
        (state.get("business_context") or {}).get("detected_intent"),
        (conversation.get("business_context") or {}).get("detected_intent"),
        conversation.get("last_intent"),
        conversation.get("previous_intent"),
    ]
    for candidate in candidates:
        if candidate not in (None, "", [], {}):
            return str(candidate)
    return None


def _context_isolation_metadata(current_intent: str | None, previous_intent: str | None) -> dict:
    current = str(current_intent or "unknown")
    previous = str(previous_intent or "") if previous_intent else None
    comparable = bool(previous and current not in {"unknown", ""} and previous not in {"unknown", ""})
    changed = bool(comparable and current != previous)
    return {
        "current_message_intent": current,
        "previous_context_intent": previous,
        "intent_changed": changed,
        "context_isolation_applied": changed,
    }


def workflow_response_gate(task_route: dict | None) -> dict:
    route = task_route or {}
    workflow = route.get("business_workflow") or ((route.get("business_context") or {}).get("workflow_intelligence")) or ((route.get("llm_reasoning_context") or {}).get("workflow_intelligence")) or {}
    intent = (
        workflow.get("detected_intent")
        or ((route.get("detected_intent") or {}).get("detected_intent"))
        or ((route.get("business_context") or {}).get("detected_intent"))
    )
    action = workflow.get("workflow_action")
    missing_entities = list(workflow.get("missing_entities") or [])
    completeness = workflow.get("entity_completeness") or {}
    required = int(completeness.get("required") or len(workflow.get("required_entities") or []))
    completed = int(completeness.get("completed") or len(workflow.get("completed_entities") or []))
    is_complete = bool(
        workflow.get("workflow_complete")
        or (required > 0 and completed >= required)
        or (required > 0 and float(completeness.get("percent") or 0) >= 1.0)
    )

    blocked_reason = None
    if action in {"interrupt", "resume", "complete", "cancel"}:
        blocked_reason = f"workflow_action_{action}"
    elif intent in BYPASS_WORKFLOW_RESPONSE_INTENTS:
        blocked_reason = f"intent_{intent}"
    elif is_complete:
        blocked_reason = "entity_completeness_complete"
    elif action not in {"continue", "start_new"}:
        blocked_reason = f"workflow_action_{action or 'missing'}"
    elif not missing_entities:
        blocked_reason = "missing_entities_empty"

    allowed = blocked_reason is None
    return {
        "final_response_gate": "workflow_missing_entities" if allowed else "workflow_response_bypassed",
        "workflow_response_allowed": allowed,
        "workflow_response_blocked_reason": blocked_reason,
    }


def _workflow_id_from_business_workflow(workflow: dict | None) -> str | None:
    state = (workflow or {}).get("workflow_state") or {}
    return state.get("workflow_id") or state.get("workflow") or state.get("current_workflow")


def _knowledge_context_for_route(route: dict | None) -> dict:
    route = route or {}
    existing = route.get("knowledge_context")
    if isinstance(existing, dict):
        return existing
    try:
        context = create_knowledge_context(
            user_message=(
                route.get("user_message")
                or (route.get("conversation_understanding") or {}).get("raw_text")
                or (route.get("planner_output") or {}).get("goal")
            ),
            conversation_context={
                "conversation_understanding": route.get("conversation_understanding") or {},
                "conversation_intelligence": route.get("conversation_intelligence") or {},
                "conversation_memory": route.get("conversation_memory") or {},
                "business_context": route.get("business_context") or {},
                "business_workflow": route.get("business_workflow") or {},
                "intent_resolution": route.get("intent_resolution") or {},
                "business_intent": route.get("detected_intent") or {},
                "extracted_entities": (route.get("extracted_entities") or {}).get("extracted_entities")
                if isinstance(route.get("extracted_entities"), dict)
                else route.get("extracted_entities"),
                "selected_business_skill": route.get("selected_business_skill"),
                "selected_business_domain": route.get("selected_business_domain"),
            },
            planner_output=route.get("planner_output") or {},
            business_intelligence=route.get("business_intelligence") or {},
        )
        return context.to_dict()
    except Exception as exc:
        return {
            "candidate_domains": [],
            "candidate_skills": [],
            "selected_domain": "",
            "selected_skill": "",
            "business_rules": [],
            "reasoning_pattern": "",
            "required_entities": [],
            "required_memory": [],
            "workflow_candidates": [],
            "tool_candidates": [],
            "confidence": 0.0,
            "version": KNOWLEDGE_CONTEXT_VERSION,
            "diagnostics": {
                "knowledge_context_created": False,
                "knowledge_context_version": KNOWLEDGE_CONTEXT_VERSION,
                "candidate_domain_count": 0,
                "candidate_skill_count": 0,
                "knowledge_runtime_source": KNOWLEDGE_RUNTIME_SOURCE,
                "knowledge_runtime_error": f"{type(exc).__name__}: {exc}",
            },
        }


def _reasoning_context_for_route(route: dict | None, knowledge_context: dict | None = None) -> dict:
    route = route or {}
    existing = route.get("reasoning_context")
    if isinstance(existing, dict):
        return existing
    knowledge = knowledge_context if isinstance(knowledge_context, dict) else _knowledge_context_for_route(route)
    try:
        context = create_reasoning_context(
            route,
            knowledge_context=knowledge,
            workflow_state=route.get("business_workflow") or {},
            memory=route.get("conversation_memory") or {},
        )
        return context.to_dict()
    except Exception as exc:
        return {
            "business_goal": "",
            "decision_type": "unknown",
            "business_stage": "",
            "selected_domain": "",
            "selected_skill": "",
            "known_entities": {},
            "missing_entities": [],
            "assumptions": [],
            "risks": [],
            "opportunities": [],
            "recommended_next_action": "",
            "reasoning_pattern": "",
            "confidence": 0.0,
            "version": REASONING_RUNTIME_VERSION,
            "diagnostics": {
                "reasoning_runtime_created": False,
                "reasoning_runtime_version": REASONING_RUNTIME_VERSION,
                "reasoning_source": REASONING_RUNTIME_SOURCE,
                "reasoning_runtime_error": f"{type(exc).__name__}: {exc}",
            },
        }


def _planner_context_for_route(
    route: dict | None,
    knowledge_context: dict | None = None,
    reasoning_context: dict | None = None,
) -> dict:
    route = route or {}
    existing = route.get("planner_context")
    if isinstance(existing, dict):
        return existing
    knowledge = knowledge_context if isinstance(knowledge_context, dict) else _knowledge_context_for_route(route)
    reasoning = reasoning_context if isinstance(reasoning_context, dict) else _reasoning_context_for_route(route, knowledge)
    try:
        context = build_planner_context(
            route,
            knowledge_context=knowledge,
            reasoning_context=reasoning,
            workflow_state=route.get("business_workflow") or {},
        )
        return context.to_dict()
    except Exception as exc:
        return {
            "selected_domain": "",
            "selected_skill": "",
            "business_goal": "",
            "decision_type": "unknown",
            "workflow_owner": "",
            "workflow_state": {},
            "planner_inputs": {},
            "planner_hints": {},
            "planner_constraints": ["diagnostics_only"],
            "confidence": 0.0,
            "version": PLANNER_CONTEXT_VERSION,
            "diagnostics": {
                "planner_context_created": False,
                "planner_context_version": PLANNER_CONTEXT_VERSION,
                "planner_context_source": PLANNER_CONTEXT_SOURCE,
                "planner_context_error": f"{type(exc).__name__}: {exc}",
                "runtime_mode": "diagnostics_only",
                "planner_logic_executed": False,
            },
        }


def _matched_skill_payload(route: dict | None) -> dict:
    matched = ((route or {}).get("business_intelligence") or {}).get("matched_skill") or {}
    if not isinstance(matched, dict):
        return {}
    return {
        "skill_id": matched.get("skill_id"),
        "match_score": matched.get("match_score"),
        "matched_aliases": matched.get("matched_aliases") or [],
        "matched_keywords": matched.get("matched_keywords") or [],
    }


def _intent_priority_audit(route: dict | None) -> dict:
    route = route or {}
    business_context = route.get("business_context") or {}
    intent_resolution = route.get("intent_resolution") or {}
    planner_output = route.get("planner_output") or {}
    business_workflow = route.get("business_workflow") or {}
    matched_skill = _matched_skill_payload(route)

    current_message_intent = business_context.get("current_message_intent")
    detected_intent = business_context.get("detected_intent")
    resolved_intent = intent_resolution.get("resolved_intent")
    resolved_workflow = intent_resolution.get("resolved_workflow")
    planner_workflow = planner_output.get("workflow")
    business_workflow_id = _workflow_id_from_business_workflow(business_workflow)

    overrides = []
    previous_intent = current_message_intent or detected_intent
    previous_workflow = business_workflow_id
    if previous_intent and resolved_intent and resolved_intent != previous_intent:
        overrides.append(
            {
                "layer": "intent_resolver",
                "field": "intent",
                "from": previous_intent,
                "to": resolved_intent,
            }
        )
    if previous_workflow and resolved_workflow and resolved_workflow != previous_workflow:
        overrides.append(
            {
                "layer": "intent_resolver",
                "field": "workflow",
                "from": previous_workflow,
                "to": resolved_workflow,
            }
        )
    if resolved_workflow and planner_workflow and planner_workflow != resolved_workflow:
        overrides.append(
            {
                "layer": "planner",
                "field": "workflow",
                "from": resolved_workflow,
                "to": planner_workflow,
            }
        )
    elif previous_workflow and planner_workflow and planner_workflow != previous_workflow:
        overrides.append(
            {
                "layer": "planner",
                "field": "workflow",
                "from": previous_workflow,
                "to": planner_workflow,
            }
        )
    if current_message_intent == "cost_calculation" and str(matched_skill.get("skill_id") or "").endswith("customer_asks_price"):
        overrides.append(
            {
                "layer": "business_skill_matcher",
                "field": "skill_id",
                "from": current_message_intent,
                "to": matched_skill.get("skill_id"),
            }
        )

    return {
        "current_message_text": (route.get("conversation_understanding") or {}).get("raw_text") or planner_output.get("goal") or route.get("user_message"),
        "detected_intent": detected_intent,
        "current_message_intent": current_message_intent,
        "intent_resolution": {
            "resolved_intent": resolved_intent,
            "resolved_workflow": resolved_workflow,
            "resolver_override": intent_resolution.get("resolver_override"),
        },
        "planner_output": {
            "task_type": planner_output.get("task_type"),
            "workflow": planner_workflow,
        },
        "business_workflow": {
            "workflow_state": {
                "workflow_id": business_workflow_id,
            }
        },
        "matched_skill": matched_skill,
        "intent_changed_between_layers": bool(overrides),
        "workflow_changed_between_layers": any(item.get("field") == "workflow" for item in overrides),
        "overrides": overrides,
        "overrode_previous_layer": overrides[-1]["layer"] if overrides else None,
    }


def _with_response_gate(route: dict) -> dict:
    knowledge_context = _knowledge_context_for_route(route)
    route = {**route, "knowledge_context": knowledge_context}
    reasoning_context = _reasoning_context_for_route(route, knowledge_context)
    route = {**route, "reasoning_context": reasoning_context}
    route = {**route, "planner_context": _planner_context_for_route(route, knowledge_context, reasoning_context)}
    route = {**route, "intent_priority_audit": _intent_priority_audit(route)}
    gate = workflow_response_gate(route)
    return {**route, **gate}


def _planner_skipped_route(
    user_message: str | None,
    *,
    reason: str,
    response_source: str,
    extra: dict | None = None,
) -> dict:
    return _with_response_gate({
        "planner_output": {
            "goal": str(user_message or "").strip(),
            "task_type": "Conversation Continuation",
            "workflow": None,
            "required_skills": [],
            "required_information": [],
            "known_information": ["previous_response"],
            "missing_information": [],
            "can_execute": True,
            "next_step": "skip_planner",
            "priority": "high",
            "estimated_response_mode": response_source,
            "planner_skipped": True,
        },
        "conversation_understanding": {},
        "conversation_intelligence": {},
        "intent_resolution": {"resolved_intent": reason, "resolved_workflow": None},
        "detected_intent": {},
        "extracted_entities": {},
        "business_workflow": {},
        "business_context": {},
        "conversation_memory": {},
        "task_type": "Conversation Continuation",
        "selected_capability": None,
        "loaded_skills": [],
        "reasoning": {"action": reason, "workflow_ready": False},
        "reasoning_mode": "conversation_continuation",
        "llm_reasoning_context": {},
        "llm_decision": {"should_use_llm": False, "reason": "Planner skipped for response continuation."},
        "workflow_ready": False,
        "llm_needed": False,
        "capability_available": True,
        "placeholders": dict(PLACEHOLDER_ENGINES),
        "planner_skipped": True,
        "direct_answer_mode": True,
        "continuation_mode": reason,
        "response_source": response_source,
        "response_generation_mode": response_source,
        **(extra or {}),
    })


def _continuation_route_if_planner_should_skip(state: dict, user_message: str | None) -> dict | None:
    transformation = detect_response_transformation(user_message)
    source = transformation_source(state)
    if transformation.get("is_transformation") and source.get("text"):
        return _planner_skipped_route(
            user_message,
            reason="response_transformation",
            response_source="response_transformation",
            extra={
                "transformation_type": transformation.get("transformation_type"),
                "transformation_reason": transformation.get("transformation_reason"),
                "transformation_source": source.get("source"),
                "transformation_chain": source.get("transformation_chain") or [],
                "transformation_history": source.get("transformation_history") or [],
                "used_previous_response": True,
                "rewrite_mode": transformation.get("rewrite_mode"),
                "translation_mode": transformation.get("translation_mode"),
                "reuse_reason": "previous_generated_response_available",
            },
        )

    completed_followup = classify_completed_workflow_followup(state, user_message)
    if completed_followup.get("reuse_completed_workflow"):
        completed = completed_followup.get("completed_workflow") or {}
        return _planner_skipped_route(
            user_message,
            reason="completed_workflow_followup",
            response_source="completed_workflow",
            extra={
                "reuse_completed_workflow": True,
                "reuse_reason": (
                    "completed_cost_result_available"
                    if completed.get("workflow_id") == "cost_calculation"
                    else "completed_workflow_context_available"
                ),
                "followup_chain": completed_followup.get("followup_chain") or [],
                "workflow_followup_mode": completed_followup.get("workflow_followup_mode"),
                "workflow_variant_mode": completed_followup.get("workflow_variant_mode"),
                "workflow_transition_reason": completed_followup.get("workflow_transition_reason"),
            },
        )

    return None


def build_task_route(application_state, user_message) -> dict:
    state = application_state if application_state is not None else {}
    continuation_route = _continuation_route_if_planner_should_skip(state, user_message)
    if continuation_route:
        return continuation_route

    business_intent = detect_business_intent(user_message)
    entity_result = extract_business_entities(user_message, business_intent.get("detected_intent"))
    workflow_decision = decide_business_workflow(
        user_message,
        business_intent=business_intent,
        entity_result=entity_result,
        application_state=state,
    )
    if planner_locked(state) and workflow_decision.get("workflow_action") not in {"interrupt", "start_new"}:
        workflow_state = active_workflow_state(state) or {}
        isolation = _context_isolation_metadata(
            business_intent.get("detected_intent"),
            _previous_context_intent(state),
        )
        return _with_response_gate({
            "planner_output": {
                "goal": str(user_message or "").strip(),
                "task_type": workflow_state.get("workflow_name"),
                "workflow": workflow_state.get("workflow_id"),
                "required_skills": [],
                "required_information": workflow_state.get("required_fields") or [],
                "known_information": ["conversation_os"],
                "missing_information": workflow_state.get("missing_fields") or [],
                "can_execute": not bool(workflow_state.get("missing_fields")),
                "next_step": "continue_active_workflow",
                "priority": "high",
                "estimated_response_mode": "workflow",
                "planner_locked": True,
                "workflow_intelligence": workflow_decision,
            },
            "conversation_understanding": {},
            "conversation_intelligence": {},
            "intent_resolution": {"resolved_intent": "continue_previous_workflow", "resolved_workflow": workflow_state.get("workflow_id")},
            "detected_intent": business_intent,
            "extracted_entities": entity_result,
            "business_workflow": workflow_decision,
            "business_context": {
                **isolation,
                "detected_intent": business_intent.get("detected_intent"),
                "intent_confidence": business_intent.get("intent_confidence"),
                "matched_intent_keywords": business_intent.get("matched_intent_keywords") or [],
                "extracted_entities": entity_result.get("extracted_entities") or {},
                "missing_entities": entity_result.get("missing_entities") or [],
                "entity_confidence": entity_result.get("entity_confidence"),
                "workflow_intelligence": workflow_decision,
            },
            "conversation_memory": {},
            "task_type": workflow_state.get("workflow_name"),
            "selected_capability": None,
            "loaded_skills": [],
            "reasoning": {
                "action": "continue_active_workflow",
                "workflow_ready": not bool(workflow_state.get("missing_fields")) or bool(workflow_decision.get("workflow_complete")),
                "workflow_intelligence": workflow_decision,
            },
            "reasoning_mode": "workflow",
            "llm_reasoning_context": {"workflow_intelligence": workflow_decision, **isolation},
            "llm_decision": {"should_use_llm": False, "reason": "Planner locked by Conversation OS."},
            "workflow_ready": not bool(workflow_state.get("missing_fields")) or bool(workflow_decision.get("workflow_complete")),
            "llm_needed": False,
            "capability_available": True,
            "placeholders": dict(PLACEHOLDER_ENGINES),
            **isolation,
            "planner_locked": True,
        })

    existing_interpretation = state.get("conversation_understanding") or ((state.get("conversation") or {}).get("understanding")) or {}
    if existing_interpretation.get("raw_text") == str(user_message or ""):
        interpretation = existing_interpretation
    else:
        interpretation = understand_conversation(user_message, state)
    memory_context = get_last_context(state)
    isolation = _context_isolation_metadata(
        business_intent.get("detected_intent"),
        _previous_context_intent(state, memory_context),
    )
    business_context = build_business_context(
        state,
        user_message,
        understanding=interpretation,
        conversation_memory=memory_context,
    )
    business_context = {
        **business_context,
        **isolation,
        "detected_intent": business_intent.get("detected_intent"),
        "intent_confidence": business_intent.get("intent_confidence"),
        "matched_intent_keywords": business_intent.get("matched_intent_keywords") or [],
        "extracted_entities": entity_result.get("extracted_entities") or {},
        "missing_entities": entity_result.get("missing_entities") or [],
        "entity_confidence": entity_result.get("entity_confidence"),
        "workflow_intelligence": workflow_decision,
    }
    intent_resolution = resolve_intent(interpretation, memory_context, business_context)
    memory_context = remember_turn(
        memory_context,
        user_message,
        intent=intent_resolution.get("resolved_intent") or interpretation.get("detected_intent"),
        workflow=intent_resolution.get("resolved_workflow"),
        business_topic=business_context.get("current_discussion_topic"),
    )
    conversation_intelligence = {
        "conversation_memory": memory_context,
        "business_context": business_context,
        "intent_resolution": intent_resolution,
    }
    enriched_state = dict(state)
    enriched_state["conversation_understanding"] = interpretation
    enriched_state["conversation_memory"] = memory_context
    enriched_state["business_context"] = business_context
    enriched_state["conversation_intelligence"] = conversation_intelligence
    enriched_state["conversation"] = {
        **(state.get("conversation") or {}),
        "understanding": interpretation,
        "last_understanding": interpretation,
        "conversation_memory": memory_context,
        "business_context": business_context,
        "intent_resolution": intent_resolution,
    }
    routing_state = enriched_state
    if workflow_decision.get("workflow_action") == "interrupt":
        routing_state = dict(enriched_state)
        routing_state["workflow"] = {}
        conversation = dict(routing_state.get("conversation") or {})
        os_state = dict(conversation.get("conversation_os") or {})
        os_state["planner_locked"] = False
        os_state["active_workflow_id"] = None
        conversation["conversation_os"] = os_state
        routing_state["conversation"] = conversation
    preliminary_context_route = {
        "user_message": user_message,
        "knowledge_context": state.get("knowledge_context") or ((state.get("conversation") or {}).get("knowledge_context")),
        "reasoning_context": state.get("reasoning_context") or ((state.get("conversation") or {}).get("reasoning_context")),
        "planner_context": state.get("planner_context") or ((state.get("conversation") or {}).get("planner_context")),
        "conversation_understanding": interpretation,
        "conversation_intelligence": conversation_intelligence,
        "conversation_memory": memory_context,
        "business_context": business_context,
        "business_workflow": workflow_decision,
        "intent_resolution": intent_resolution,
        "detected_intent": business_intent,
        "extracted_entities": entity_result,
    }
    preliminary_knowledge_context = preliminary_context_route.get("knowledge_context") or {}
    preliminary_reasoning_context = preliminary_context_route.get("reasoning_context") or {}
    preliminary_planner_context = preliminary_context_route.get("planner_context") or {}
    planner_migration = normalize_planner_inputs(
        knowledge_context=preliminary_knowledge_context,
        reasoning_context=preliminary_reasoning_context,
        planner_context=preliminary_planner_context,
        user_message=user_message,
    )
    routing_state = apply_planner_migration_to_state(routing_state, planner_migration)

    planner_message = intent_resolution.get("planner_message") or interpretation.get("planner_message") or user_message
    plan = build_execution_plan(routing_state, planner_message)
    plan["workflow_intelligence"] = workflow_decision
    bridge_result = run_business_intelligence_bridge(
        user_message,
        {
            "conversation_understanding": interpretation,
            "conversation_intelligence": conversation_intelligence,
            "conversation_memory": memory_context,
            "business_context": business_context,
            "business_workflow": workflow_decision,
            "intent_resolution": intent_resolution,
            **isolation,
            "intent": business_intent.get("detected_intent"),
            "detected_intent": business_intent.get("detected_intent"),
            "business_intent": business_intent,
            "extracted_entities": entity_result.get("extracted_entities") or {},
            "missing_entities": entity_result.get("missing_entities") or [],
            "store_profile": enriched_state.get("store") or {},
        },
        plan,
    )
    plan = inject_business_intelligence(plan, bridge_result)
    enriched_state["business_intelligence"] = bridge_result
    enriched_state["conversation"] = {
        **(enriched_state.get("conversation") or {}),
        "business_intelligence": bridge_result,
    }
    capability_name = TASK_CAPABILITY_NAMES.get(plan.get("task_type"), plan.get("task_type"))
    capability = get_capability(capability_name)
    capability_available = is_capability_available(capability_name)
    loaded_skills = load_skills(plan.get("required_skills") or [])
    reasoning = build_reasoning(enriched_state, planner_message)

    workflow_state = (enriched_state or {}).get("workflow") or {}
    workflow_ready = bool(
        workflow_state.get("is_ready")
        or (workflow_state.get("workflow_state_v2") or {}).get("is_ready")
        or reasoning.get("workflow_ready")
    )
    llm_reasoning_context = build_reasoning_context(
        user_message=planner_message,
        application_state=enriched_state,
        planner=plan,
        workflow=workflow_state,
        reasoning=reasoning,
        capability=capability,
        loaded_skill=[_serialize_skill(skill) for skill in loaded_skills],
        conversation_intent=interpretation.get("legacy_intent") or interpretation.get("detected_intent"),
        conversation_summary=memory_context,
        business_context=sanitize_user_context_text(business_context),
        store_profile=(enriched_state.get("store") or {}),
        current_task=plan.get("task_type"),
    )
    llm_reasoning_context["normalized_business_context"] = sanitize_user_context_text(business_context)
    llm_reasoning_context["context_source"] = business_context.get("source")
    llm_reasoning_context["context_confidence"] = business_context.get("confidence")
    llm_reasoning_context["context_conflicts"] = business_context.get("conflicts") or []
    llm_reasoning_context["stale_context_detected"] = bool(
        business_context.get("is_stale") or business_context.get("conflicts")
    )
    llm_reasoning_context["selected_business_skill"] = _selected_business_skill(bridge_result, reasoning)
    llm_reasoning_context["selected_business_domain"] = bridge_result.get("matched_domain")
    llm_reasoning_context["matched_intents"] = _matched_intents(plan, interpretation, intent_resolution, reasoning)
    llm_reasoning_context["detected_intent"] = business_intent
    llm_reasoning_context["extracted_entities"] = entity_result
    llm_reasoning_context["workflow_intelligence"] = workflow_decision
    llm_reasoning_context.update(isolation)
    llm_reasoning_context["prompt_context_size"] = _prompt_context_size(llm_reasoning_context)
    llm_decision = decide_llm_usage(llm_reasoning_context)
    llm_needed = bool(llm_decision.get("should_use_llm"))

    return _with_response_gate({
        "planner_output": plan,
        "conversation_understanding": interpretation,
        "conversation_intelligence": conversation_intelligence,
        "intent_resolution": intent_resolution,
        "detected_intent": business_intent,
        "extracted_entities": entity_result,
        "business_workflow": workflow_decision,
        "business_context": business_context,
        "normalized_business_context": business_context,
        "context_source": business_context.get("source"),
        "context_confidence": business_context.get("confidence"),
        "context_conflicts": business_context.get("conflicts") or [],
        "stale_context_detected": bool(business_context.get("is_stale") or business_context.get("conflicts")),
        **isolation,
        "selected_business_skill": _selected_business_skill(bridge_result, reasoning),
        "selected_business_domain": bridge_result.get("matched_domain"),
        "matched_intents": _matched_intents(plan, interpretation, intent_resolution, reasoning),
        "included_context_sections": list(llm_reasoning_context.keys()),
        "omitted_context_sections": [],
        "prompt_context_size": llm_reasoning_context.get("prompt_context_size"),
        "conversation_memory": memory_context,
        "business_intelligence": bridge_result,
        "planner_migration": planner_migration,
        "task_type": plan.get("task_type"),
        "selected_capability": capability,
        "loaded_skills": [_serialize_skill(skill) for skill in loaded_skills],
        "reasoning": reasoning,
        "reasoning_mode": _reasoning_mode(plan, reasoning),
        "llm_reasoning_context": llm_reasoning_context,
        "llm_decision": llm_decision,
        "workflow_ready": workflow_ready,
        "llm_needed": llm_needed,
        "capability_available": capability_available,
        "placeholders": dict(PLACEHOLDER_ENGINES),
    })


def _with_diagnostic_groups(diagnostics: dict) -> dict:
    grouped = {
        "Routing": {
            "task_type": diagnostics.get("Task Type"),
            "intent_priority_audit": diagnostics.get("intent_priority_audit"),
            "intent_resolution": diagnostics.get("intent_resolution"),
            "final_response_gate": diagnostics.get("final_response_gate"),
            "workflow_response_allowed": diagnostics.get("workflow_response_allowed"),
            "workflow_response_blocked_reason": diagnostics.get("workflow_response_blocked_reason"),
            "current_message_intent": diagnostics.get("current_message_intent"),
            "previous_context_intent": diagnostics.get("previous_context_intent"),
            "intent_changed": diagnostics.get("intent_changed"),
        },
        "Conversation": {
            "understanding": diagnostics.get("Conversation Understanding"),
            "intelligence": diagnostics.get("Conversation Intelligence"),
            "conversation_style": diagnostics.get("conversation_style"),
            "continuation_mode": diagnostics.get("continuation_mode"),
            "direct_answer_mode": diagnostics.get("direct_answer_mode"),
            "reuse_reason": diagnostics.get("reuse_reason"),
            "followup_chain": diagnostics.get("followup_chain"),
        },
        "Workflow": {
            "workflow_action": diagnostics.get("workflow_action"),
            "workflow_state": diagnostics.get("workflow_state"),
            "workflow_status": diagnostics.get("workflow_status"),
            "workflow_complete": diagnostics.get("workflow_complete"),
            "workflow_released": diagnostics.get("workflow_released"),
            "workflow_followup_mode": diagnostics.get("workflow_followup_mode"),
            "workflow_variant_mode": diagnostics.get("workflow_variant_mode"),
            "readiness_decision": diagnostics.get("Readiness Decision"),
            "completion_decision": diagnostics.get("Completion Decision"),
            "transition_decision": diagnostics.get("Transition Decision"),
        },
        "Transformation": {
            "transformation_type": diagnostics.get("transformation_type"),
            "transformation_reason": diagnostics.get("transformation_reason"),
            "transformation_source": diagnostics.get("transformation_source"),
            "transformation_chain": diagnostics.get("transformation_chain"),
            "transformation_history": diagnostics.get("transformation_history"),
            "used_previous_response": diagnostics.get("used_previous_response"),
            "rewrite_mode": diagnostics.get("rewrite_mode"),
            "translation_mode": diagnostics.get("translation_mode"),
        },
        "Planner": {
            "planner_output": diagnostics.get("Planner Output"),
            "planner_skipped": diagnostics.get("planner_skipped"),
            "planner_locked": diagnostics.get("Planner Locked"),
            "reasoning_mode": diagnostics.get("Reasoning Mode"),
            "llm_decision": diagnostics.get("LLM Decision"),
            "llm_needed": diagnostics.get("LLM Needed"),
        },
        "Planner Context": {
            "planner_context": diagnostics.get("planner_context"),
            "planner_context_created": diagnostics.get("planner_context_created"),
            "planner_context_version": diagnostics.get("planner_context_version"),
            "planner_context_source": diagnostics.get("planner_context_source"),
            "planner_selected_domain": diagnostics.get("planner_selected_domain"),
            "planner_selected_skill": diagnostics.get("planner_selected_skill"),
            "planner_business_goal": diagnostics.get("planner_business_goal"),
            "planner_confidence": diagnostics.get("planner_confidence"),
            "planner_context_present": diagnostics.get("planner_context_present"),
        },
        "Planner Migration": {
            "planner_runtime_source": diagnostics.get("planner_runtime_source"),
            "planner_runtime_version": diagnostics.get("planner_runtime_version"),
            "planner_used_v5_context": diagnostics.get("planner_used_v5_context"),
            "planner_used_legacy_fallback": diagnostics.get("planner_used_legacy_fallback"),
            "planner_selected_domain": diagnostics.get("planner_selected_domain"),
            "planner_selected_skill": diagnostics.get("planner_selected_skill"),
            "planner_business_goal": diagnostics.get("planner_business_goal"),
            "planner_decision_type": diagnostics.get("planner_decision_type"),
            "planner_confidence": diagnostics.get("planner_confidence"),
            "planner_reason": diagnostics.get("planner_reason"),
        },
        "Business Knowledge": {
            "registry_version": diagnostics.get("registry_version"),
            "registered_domains": diagnostics.get("registered_domains"),
            "registered_skills": diagnostics.get("registered_skills"),
            "business_skill_registry": diagnostics.get("business_skill_registry"),
            "business_knowledge": diagnostics.get("business_knowledge"),
            "knowledge_context_created": diagnostics.get("knowledge_context_created"),
            "knowledge_context_version": diagnostics.get("knowledge_context_version"),
            "candidate_domain_count": diagnostics.get("candidate_domain_count"),
            "candidate_skill_count": diagnostics.get("candidate_skill_count"),
            "knowledge_runtime_source": diagnostics.get("knowledge_runtime_source"),
            "matched_skill": diagnostics.get("Matched Skill"),
            "matched_domain": diagnostics.get("Matched Domain"),
        },
        "Business Reasoning": {
            "business_reasoning": diagnostics.get("business_reasoning"),
            "reasoning_runtime_created": diagnostics.get("reasoning_runtime_created"),
            "reasoning_runtime_version": diagnostics.get("reasoning_runtime_version"),
            "reasoning_source": diagnostics.get("reasoning_source"),
            "business_goal": diagnostics.get("business_goal"),
            "decision_type": diagnostics.get("decision_type"),
            "business_stage": diagnostics.get("business_stage"),
            "reasoning_confidence": diagnostics.get("reasoning_confidence"),
            "reasoning_pattern": diagnostics.get("reasoning_pattern"),
            "selected_domain": diagnostics.get("selected_domain"),
            "selected_skill": diagnostics.get("selected_skill"),
            "reasoning_context_present": diagnostics.get("reasoning_context_present"),
        },
        "Memory": {
            "reuse_completed_workflow": diagnostics.get("reuse_completed_workflow"),
            "variant_source": diagnostics.get("variant_source"),
            "context_source": diagnostics.get("context_source"),
            "context_confidence": diagnostics.get("context_confidence"),
            "context_conflicts": diagnostics.get("context_conflicts"),
            "stale_context_detected": diagnostics.get("stale_context_detected"),
        },
        "Response": {
            "response_type": diagnostics.get("response_type"),
            "response_source": diagnostics.get("response_source"),
            "response_reason": diagnostics.get("response_reason"),
            "response_generation_mode": diagnostics.get("response_generation_mode"),
            "final_response_origin": diagnostics.get("final_response_origin"),
            "response_source_before_gate": diagnostics.get("response_source_before_gate"),
            "response_source_after_gate": diagnostics.get("response_source_after_gate"),
            "reply_builder": diagnostics.get("reply_builder"),
            "natural_response": diagnostics.get("natural_response"),
        },
        "Response Envelope": {
            "response_envelope": diagnostics.get("response_envelope"),
            "response_envelope_created": diagnostics.get("response_envelope_created"),
            "response_envelope_version": diagnostics.get("response_envelope_version"),
            "response_envelope_source": diagnostics.get("response_envelope_source"),
            "response_envelope_present": diagnostics.get("response_envelope_present"),
        },
    }
    return {**diagnostics, "diagnostic_groups": grouped}


def developer_diagnostics(task_route: dict | None) -> dict:
    route = task_route or {}
    skills = route.get("loaded_skills") or []
    loaded_skill_names = [skill.get("name") for skill in skills if skill.get("available")]
    workflow = route.get("business_workflow") or ((route.get("business_context") or {}).get("workflow_intelligence")) or ((route.get("llm_reasoning_context") or {}).get("workflow_intelligence")) or {}
    knowledge_context = _knowledge_context_for_route(route)
    knowledge_diagnostics = knowledge_context.get("diagnostics") or {}
    reasoning_context = _reasoning_context_for_route(route, knowledge_context)
    reasoning_diagnostics = reasoning_context.get("diagnostics") or {}
    planner_context = _planner_context_for_route(route, knowledge_context, reasoning_context)
    planner_context_diagnostics = planner_context.get("diagnostics") or {}
    migration_diagnostics = planner_migration_diagnostics(route.get("planner_migration"))
    business_knowledge = {
        "candidate_domains": knowledge_context.get("candidate_domains") or [],
        "candidate_skills": knowledge_context.get("candidate_skills") or [],
        "selected_domain": knowledge_context.get("selected_domain"),
        "selected_skill": knowledge_context.get("selected_skill"),
        "registry_version": knowledge_diagnostics.get("registry_version"),
        "confidence": knowledge_context.get("confidence"),
    }
    try:
        business_skill_registry = registry_diagnostics()
    except Exception as exc:
        business_skill_registry = {
            "registry_version": None,
            "registered_domains": 0,
            "registered_skills": 0,
            "registry_error": str(exc),
        }

    response_audit_defaults = {
        "final_response_origin": route.get("final_response_origin"),
        "final_response_text_preview": route.get("final_response_text_preview"),
        "final_response_selector": route.get("final_response_selector"),
        "final_response_selected_by": route.get("final_response_selected_by"),
        "final_response_candidates": route.get("final_response_candidates") or [],
        "response_builder": route.get("response_builder"),
        "reply_builder": route.get("reply_builder"),
        "response_source_before_gate": route.get("response_source_before_gate"),
        "response_source_after_gate": route.get("response_source_after_gate"),
        "response_gate_applied": bool(route.get("response_gate_applied")),
        "legacy_response_used": bool(route.get("legacy_response_used")),
        "legacy_response_reason": route.get("legacy_response_reason"),
        "legacy_response_source_file": route.get("legacy_response_source_file"),
        "legacy_response_source_function": route.get("legacy_response_source_function"),
        "deterministic_response_used": bool(route.get("deterministic_response_used")),
        "llm_response_used": bool(route.get("llm_response_used")),
        "workflow_response_used": bool(route.get("workflow_response_used")),
        "reasoning_response_used": bool(route.get("reasoning_response_used")),
        "response_type": route.get("response_type"),
        "response_source": route.get("response_source"),
        "response_reason": route.get("response_reason"),
        "reuse_completed_workflow": bool(route.get("reuse_completed_workflow")),
        "variant_source": route.get("variant_source"),
        "composer_trace": route.get("composer_trace") or [],
        "followup_chain": route.get("followup_chain") or [],
        "conversation_style": route.get("conversation_style"),
        "continuation_mode": route.get("continuation_mode"),
        "direct_answer_mode": bool(route.get("direct_answer_mode")),
        "planner_skipped": bool(route.get("planner_skipped")),
        "reuse_reason": route.get("reuse_reason"),
        "response_generation_mode": route.get("response_generation_mode"),
        "transformation_type": route.get("transformation_type"),
        "transformation_reason": route.get("transformation_reason"),
        "transformation_source": route.get("transformation_source"),
        "transformation_chain": route.get("transformation_chain") or [],
        "transformation_history": route.get("transformation_history") or [],
        "used_previous_response": bool(route.get("used_previous_response")),
        "rewrite_mode": route.get("rewrite_mode"),
        "translation_mode": route.get("translation_mode"),
    }
    response_envelope = build_response_envelope(
        route.get("final_response_text"),
        route,
        response_audit_defaults,
    )
    response_envelope_audit = response_envelope_diagnostics(response_envelope)

    diagnostics = {
        "Planner Output": route.get("planner_output") or {},
        "Conversation Understanding": route.get("conversation_understanding") or {},
        "Conversation Intelligence": route.get("conversation_intelligence") or {},
        "intent_priority_audit": route.get("intent_priority_audit") or _intent_priority_audit(route),
        "intent_resolution": route.get("intent_resolution") or {},
        "Task Type": route.get("task_type"),
        "Selected Capability": (route.get("selected_capability") or {}).get("name"),
        "Loaded Skill": loaded_skill_names,
        "Business Skill Search": bool((route.get("business_intelligence") or {}).get("bridge_used") or (route.get("business_intelligence") or {}).get("fallback_used")),
        "registry_version": business_skill_registry.get("registry_version"),
        "registered_domains": business_skill_registry.get("registered_domains"),
        "registered_skills": business_skill_registry.get("registered_skills"),
        "business_skill_registry": business_skill_registry,
        "business_knowledge": business_knowledge,
        "knowledge_context_created": bool(knowledge_diagnostics.get("knowledge_context_created")),
        "knowledge_context_version": knowledge_diagnostics.get("knowledge_context_version") or knowledge_context.get("version"),
        "candidate_domain_count": knowledge_diagnostics.get("candidate_domain_count", len(business_knowledge["candidate_domains"])),
        "candidate_skill_count": knowledge_diagnostics.get("candidate_skill_count", len(business_knowledge["candidate_skills"])),
        "knowledge_runtime_source": knowledge_diagnostics.get("knowledge_runtime_source"),
        "Matched Skill": ((route.get("business_intelligence") or {}).get("matched_skill") or {}).get("skill_id"),
        "Matched Skills": (route.get("business_intelligence") or {}).get("matched_skills") or [],
        "Ranking Table": (route.get("business_intelligence") or {}).get("ranking_table") or [],
        "Top Skill": (route.get("business_intelligence") or {}).get("top_skill"),
        "Top Confidence": (route.get("business_intelligence") or {}).get("top_confidence"),
        "Matching Reason": (route.get("business_intelligence") or {}).get("matching_reason"),
        "Matched Domain": (route.get("business_intelligence") or {}).get("matched_domain"),
        "Business Principle": (route.get("business_intelligence") or {}).get("business_principle"),
        "Thinking Pattern": (route.get("business_intelligence") or {}).get("thinking_pattern"),
        "Decision Tree": (route.get("business_intelligence") or {}).get("decision_tree") or [],
        "Business Reasoning": (route.get("business_intelligence") or {}).get("business_reasoning") or {},
        "Reasoning Confidence": (route.get("business_intelligence") or {}).get("confidence"),
        "business_reasoning": reasoning_context,
        "reasoning_runtime_created": bool(reasoning_diagnostics.get("reasoning_runtime_created")),
        "reasoning_runtime_version": reasoning_diagnostics.get("reasoning_runtime_version") or reasoning_context.get("version"),
        "reasoning_source": reasoning_diagnostics.get("reasoning_source"),
        "business_goal": reasoning_context.get("business_goal"),
        "decision_type": reasoning_context.get("decision_type"),
        "business_stage": reasoning_context.get("business_stage"),
        "reasoning_confidence": reasoning_context.get("confidence"),
        "reasoning_pattern": reasoning_context.get("reasoning_pattern"),
        "selected_domain": reasoning_context.get("selected_domain"),
        "selected_skill": reasoning_context.get("selected_skill"),
        "reasoning_context_present": bool(reasoning_context),
        "planner_context": planner_context,
        "planner_context_created": bool(planner_context_diagnostics.get("planner_context_created")),
        "planner_context_version": planner_context_diagnostics.get("planner_context_version") or planner_context.get("version"),
        "planner_context_source": planner_context_diagnostics.get("planner_context_source"),
        "planner_selected_domain": planner_context.get("selected_domain"),
        "planner_selected_skill": planner_context.get("selected_skill"),
        "planner_business_goal": planner_context.get("business_goal"),
        "planner_confidence": planner_context.get("confidence"),
        "planner_context_present": bool(planner_context),
        **migration_diagnostics,
        "Business Response Mode": (route.get("business_intelligence") or {}).get("response_mode"),
        "skill_match_audit": (route.get("business_intelligence") or {}).get("skill_match_audit") or {},
        "skill_match_audit_summary": (route.get("business_intelligence") or {}).get("skill_match_audit_summary") or {},
        "skill_matching_bypassed": bool((route.get("business_intelligence") or {}).get("skill_matching_bypassed")),
        "skill_matching_bypass_reason": (route.get("business_intelligence") or {}).get("skill_matching_bypass_reason"),
        "detected_intent": route.get("detected_intent") or ((route.get("llm_reasoning_context") or {}).get("detected_intent")) or {},
        "extracted_entities": route.get("extracted_entities") or ((route.get("llm_reasoning_context") or {}).get("extracted_entities")) or {},
        "workflow_action": workflow.get("workflow_action"),
        "workflow_state": workflow.get("workflow_state") or {},
        "workflow_status": workflow.get("workflow_status") or (workflow.get("workflow_state") or {}).get("workflow_lifecycle_status") or (workflow.get("workflow_state") or {}).get("workflow_status"),
        "workflow_completion_reason": workflow.get("workflow_completion_reason") or (workflow.get("workflow_state") or {}).get("workflow_completion_reason"),
        "workflow_release_reason": workflow.get("workflow_release_reason") or (workflow.get("workflow_state") or {}).get("workflow_release_reason"),
        "workflow_transition_reason": workflow.get("workflow_transition_reason") or (workflow.get("workflow_state") or {}).get("workflow_transition_reason"),
        "workflow_followup_mode": workflow.get("workflow_followup_mode") or (workflow.get("workflow_state") or {}).get("workflow_followup_mode"),
        "workflow_variant_mode": workflow.get("workflow_variant_mode") or (workflow.get("workflow_state") or {}).get("workflow_variant_mode"),
        "response_type": route.get("response_type") or response_audit_defaults.get("response_type"),
        "response_source": route.get("response_source") or response_audit_defaults.get("response_source"),
        "response_reason": route.get("response_reason") or response_audit_defaults.get("response_reason"),
        "reuse_completed_workflow": bool(
            route.get("reuse_completed_workflow")
            or response_audit_defaults.get("reuse_completed_workflow")
            or workflow.get("reuse_completed_workflow")
        ),
        "variant_source": route.get("variant_source") or response_audit_defaults.get("variant_source"),
        "composer_trace": route.get("composer_trace") or response_audit_defaults.get("composer_trace") or [],
        "followup_chain": route.get("followup_chain") or response_audit_defaults.get("followup_chain") or workflow.get("followup_chain") or [],
        "conversation_style": route.get("conversation_style") or response_audit_defaults.get("conversation_style"),
        "continuation_mode": route.get("continuation_mode") or response_audit_defaults.get("continuation_mode"),
        "direct_answer_mode": bool(route.get("direct_answer_mode") or response_audit_defaults.get("direct_answer_mode")),
        "planner_skipped": bool(route.get("planner_skipped") or response_audit_defaults.get("planner_skipped")),
        "reuse_reason": route.get("reuse_reason") or response_audit_defaults.get("reuse_reason"),
        "response_generation_mode": route.get("response_generation_mode") or response_audit_defaults.get("response_generation_mode"),
        "transformation_type": route.get("transformation_type") or response_audit_defaults.get("transformation_type"),
        "transformation_reason": route.get("transformation_reason") or response_audit_defaults.get("transformation_reason"),
        "transformation_source": route.get("transformation_source") or response_audit_defaults.get("transformation_source"),
        "transformation_chain": route.get("transformation_chain") or response_audit_defaults.get("transformation_chain") or [],
        "transformation_history": route.get("transformation_history") or response_audit_defaults.get("transformation_history") or [],
        "used_previous_response": bool(route.get("used_previous_response") or response_audit_defaults.get("used_previous_response")),
        "rewrite_mode": route.get("rewrite_mode") or response_audit_defaults.get("rewrite_mode"),
        "translation_mode": route.get("translation_mode") or response_audit_defaults.get("translation_mode"),
        "workflow_stage": workflow.get("workflow_stage"),
        "workflow_progress": workflow.get("workflow_progress") or {},
        "workflow_confidence": workflow.get("workflow_confidence"),
        "workflow_complete": bool(workflow.get("workflow_complete")),
        "workflow_released": bool(workflow.get("workflow_released") or (workflow.get("workflow_state") or {}).get("workflow_released")),
        "Workflow Complete?": bool(workflow.get("workflow_complete") or (workflow.get("workflow_state") or {}).get("workflow_complete")),
        "Workflow Released?": bool(workflow.get("workflow_released") or (workflow.get("workflow_state") or {}).get("workflow_released")),
        "Workflow Transition": workflow.get("workflow_transition_reason") or (workflow.get("workflow_state") or {}).get("workflow_transition_reason"),
        "Follow-up Mode": workflow.get("workflow_followup_mode") or (workflow.get("workflow_state") or {}).get("workflow_followup_mode"),
        "Variant Mode": workflow.get("workflow_variant_mode") or (workflow.get("workflow_state") or {}).get("workflow_variant_mode"),
        "Execution Reason": workflow.get("execution_reason") or (workflow.get("workflow_state") or {}).get("execution_reason"),
        "workflow_interrupted": bool(workflow.get("workflow_interrupted")),
        "workflow_resume_available": bool(workflow.get("workflow_resume_available")),
        "workflow_reason": workflow.get("workflow_reason"),
        "required_entities": workflow.get("required_entities") or [],
        "completed_entities": workflow.get("completed_entities") or [],
        "missing_entities": workflow.get("missing_entities") or [],
        "entity_mapping_trace": workflow.get("entity_mapping_trace") or [],
        "workflow_readiness_decision": workflow.get("workflow_readiness_decision") or {},
        "Readiness Decision": workflow.get("readiness_decision") or (workflow.get("workflow_state") or {}).get("readiness_decision") or workflow.get("workflow_readiness_decision") or {},
        "Completion Decision": workflow.get("completion_decision") or (workflow.get("workflow_state") or {}).get("completion_decision") or {},
        "Transition Decision": workflow.get("transition_decision") or (workflow.get("workflow_state") or {}).get("transition_decision") or {},
        "calculation_trace": workflow.get("calculation_trace") or {},
        "input_cost": workflow.get("input_cost"),
        "input_unit_cost": workflow.get("input_unit_cost"),
        "input_cost_per_unit": workflow.get("input_cost_per_unit"),
        "input_quantity": workflow.get("input_quantity"),
        "input_total_units": workflow.get("input_total_units"),
        "selected_formula": workflow.get("selected_formula"),
        "computed_total_cost": workflow.get("computed_total_cost"),
        "computed_cost_per_unit": workflow.get("computed_cost_per_unit"),
        "readiness_required_fields": workflow.get("readiness_required_fields") or [],
        "readiness_completed_fields": workflow.get("readiness_completed_fields") or [],
        "readiness_missing_fields": workflow.get("readiness_missing_fields") or [],
        "missing_reason_by_field": workflow.get("missing_reason_by_field") or {},
        "entity_completeness": workflow.get("entity_completeness") or {},
        "normalized_business_context": route.get("normalized_business_context") or route.get("business_context") or {},
        "context_source": route.get("context_source") or ((route.get("business_context") or {}).get("source")),
        "context_confidence": route.get("context_confidence") or ((route.get("business_context") or {}).get("confidence")),
        "context_conflicts": route.get("context_conflicts") or ((route.get("business_context") or {}).get("conflicts")) or [],
        "stale_context_detected": bool(route.get("stale_context_detected") or ((route.get("business_context") or {}).get("is_stale"))),
        "current_message_intent": route.get("current_message_intent") or ((route.get("business_context") or {}).get("current_message_intent")) or ((route.get("llm_reasoning_context") or {}).get("current_message_intent")),
        "previous_context_intent": route.get("previous_context_intent") or ((route.get("business_context") or {}).get("previous_context_intent")) or ((route.get("llm_reasoning_context") or {}).get("previous_context_intent")),
        "intent_changed": bool(route.get("intent_changed") or ((route.get("business_context") or {}).get("intent_changed")) or ((route.get("llm_reasoning_context") or {}).get("intent_changed"))),
        "context_isolation_applied": bool(route.get("context_isolation_applied") or ((route.get("business_context") or {}).get("context_isolation_applied")) or ((route.get("llm_reasoning_context") or {}).get("context_isolation_applied"))),
        "selected_business_skill": route.get("selected_business_skill") or ((route.get("llm_reasoning_context") or {}).get("selected_business_skill")),
        "selected_business_domain": route.get("selected_business_domain") or ((route.get("llm_reasoning_context") or {}).get("selected_business_domain")),
        "matched_intents": route.get("matched_intents") or ((route.get("llm_reasoning_context") or {}).get("matched_intents")) or [],
        "included_context_sections": route.get("included_context_sections") or ((route.get("llm_reasoning_context") or {}).get("included_context_sections")) or [],
        "omitted_context_sections": route.get("omitted_context_sections") or ((route.get("llm_reasoning_context") or {}).get("omitted_context_sections")) or [],
        "prompt_context_size": route.get("prompt_context_size") or ((route.get("llm_reasoning_context") or {}).get("prompt_context_size")),
        "Bridge Used": bool((route.get("business_intelligence") or {}).get("bridge_used")),
        "Fallback Used": bool((route.get("business_intelligence") or {}).get("fallback_used")),
        "Reasoning Mode": route.get("reasoning_mode"),
        "Workflow Ready": bool(route.get("workflow_ready")),
        "Planner Locked": bool(route.get("planner_locked") or (route.get("planner_output") or {}).get("planner_locked")),
        "LLM Decision": route.get("llm_decision") or {},
        "LLM Needed": bool(route.get("llm_needed")),
        "Capability Available": bool(route.get("capability_available")),
        "final_response_gate": route.get("final_response_gate") or workflow_response_gate(route).get("final_response_gate"),
        "workflow_response_allowed": bool(route.get("workflow_response_allowed") if "workflow_response_allowed" in route else workflow_response_gate(route).get("workflow_response_allowed")),
        "workflow_response_blocked_reason": route.get("workflow_response_blocked_reason") or workflow_response_gate(route).get("workflow_response_blocked_reason"),
        **response_envelope_audit,
        **response_audit_defaults,
    }
    return _with_diagnostic_groups(diagnostics)
