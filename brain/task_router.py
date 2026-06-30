from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json

from brain.conversation_manager import active_workflow_state, planner_locked
from brain.business_context_engine import build_business_context, sanitize_user_context_text
from brain.business_intelligence_bridge import (
    inject_business_intelligence,
    run_business_intelligence_bridge,
)
from brain.capability_registry import get_capability, is_capability_available
from brain.conversation_memory_engine import get_last_context, remember_turn
from brain.conversation_understanding_engine import understand_conversation
from brain.intent_resolver import resolve_intent
from brain.llm_orchestrator import build_reasoning_context, decide_llm_usage
from brain.planner_engine import build_execution_plan
from brain.reasoning_engine import build_reasoning
from brain.skill_loader import load_skills


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


def build_task_route(application_state, user_message) -> dict:
    state = application_state if application_state is not None else {}
    if planner_locked(state):
        workflow_state = active_workflow_state(state) or {}
        return {
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
            },
            "conversation_understanding": {},
            "conversation_intelligence": {},
            "intent_resolution": {"resolved_intent": "continue_previous_workflow", "resolved_workflow": workflow_state.get("workflow_id")},
            "business_context": {},
            "conversation_memory": {},
            "task_type": workflow_state.get("workflow_name"),
            "selected_capability": None,
            "loaded_skills": [],
            "reasoning": {"action": "continue_active_workflow", "workflow_ready": not bool(workflow_state.get("missing_fields"))},
            "reasoning_mode": "workflow",
            "llm_reasoning_context": {},
            "llm_decision": {"should_use_llm": False, "reason": "Planner locked by Conversation OS."},
            "workflow_ready": not bool(workflow_state.get("missing_fields")),
            "llm_needed": False,
            "capability_available": True,
            "placeholders": dict(PLACEHOLDER_ENGINES),
            "planner_locked": True,
        }

    existing_interpretation = state.get("conversation_understanding") or ((state.get("conversation") or {}).get("understanding")) or {}
    if existing_interpretation.get("raw_text") == str(user_message or ""):
        interpretation = existing_interpretation
    else:
        interpretation = understand_conversation(user_message, state)
    memory_context = get_last_context(state)
    business_context = build_business_context(
        state,
        user_message,
        understanding=interpretation,
        conversation_memory=memory_context,
    )
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
    planner_message = intent_resolution.get("planner_message") or interpretation.get("planner_message") or user_message
    plan = build_execution_plan(enriched_state, planner_message)
    bridge_result = run_business_intelligence_bridge(
        user_message,
        {
            "conversation_understanding": interpretation,
            "conversation_intelligence": conversation_intelligence,
            "conversation_memory": memory_context,
            "business_context": business_context,
            "intent_resolution": intent_resolution,
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
    llm_reasoning_context["prompt_context_size"] = _prompt_context_size(llm_reasoning_context)
    llm_decision = decide_llm_usage(llm_reasoning_context)
    llm_needed = bool(llm_decision.get("should_use_llm"))

    return {
        "planner_output": plan,
        "conversation_understanding": interpretation,
        "conversation_intelligence": conversation_intelligence,
        "intent_resolution": intent_resolution,
        "business_context": business_context,
        "normalized_business_context": business_context,
        "context_source": business_context.get("source"),
        "context_confidence": business_context.get("confidence"),
        "context_conflicts": business_context.get("conflicts") or [],
        "stale_context_detected": bool(business_context.get("is_stale") or business_context.get("conflicts")),
        "selected_business_skill": _selected_business_skill(bridge_result, reasoning),
        "selected_business_domain": bridge_result.get("matched_domain"),
        "matched_intents": _matched_intents(plan, interpretation, intent_resolution, reasoning),
        "included_context_sections": list(llm_reasoning_context.keys()),
        "omitted_context_sections": [],
        "prompt_context_size": llm_reasoning_context.get("prompt_context_size"),
        "conversation_memory": memory_context,
        "business_intelligence": bridge_result,
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
    }


def developer_diagnostics(task_route: dict | None) -> dict:
    route = task_route or {}
    skills = route.get("loaded_skills") or []
    loaded_skill_names = [skill.get("name") for skill in skills if skill.get("available")]

    return {
        "Planner Output": route.get("planner_output") or {},
        "Conversation Understanding": route.get("conversation_understanding") or {},
        "Conversation Intelligence": route.get("conversation_intelligence") or {},
        "Task Type": route.get("task_type"),
        "Selected Capability": (route.get("selected_capability") or {}).get("name"),
        "Loaded Skill": loaded_skill_names,
        "Business Skill Search": bool((route.get("business_intelligence") or {}).get("bridge_used") or (route.get("business_intelligence") or {}).get("fallback_used")),
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
        "Business Response Mode": (route.get("business_intelligence") or {}).get("response_mode"),
        "normalized_business_context": route.get("normalized_business_context") or route.get("business_context") or {},
        "context_source": route.get("context_source") or ((route.get("business_context") or {}).get("source")),
        "context_confidence": route.get("context_confidence") or ((route.get("business_context") or {}).get("confidence")),
        "context_conflicts": route.get("context_conflicts") or ((route.get("business_context") or {}).get("conflicts")) or [],
        "stale_context_detected": bool(route.get("stale_context_detected") or ((route.get("business_context") or {}).get("is_stale"))),
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
    }
