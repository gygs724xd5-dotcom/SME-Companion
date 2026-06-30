from __future__ import annotations

import json

from brain.business_context_engine import sanitize_user_context_text


PLACEHOLDER_CONTEXT_SOURCES = {
    "ocr_engine": None,
    "inventory_engine": None,
    "sales_forecast_engine": None,
    "business_memory": None,
    "marketing_agent": None,
    "financial_agent": None,
    "inventory_agent": None,
}

DEFAULT_PROMPT_BUDGET_CHARS = 6000


def _compact_dict(data: dict | None, allowed_keys: list[str] | None = None) -> dict:
    source = data or {}
    keys = allowed_keys or list(source.keys())
    return {
        key: source.get(key)
        for key in keys
        if source.get(key) not in (None, "", [], {})
    }


def _recent_conversation(conversation: dict | None, limit: int = 6) -> list[dict]:
    history = (conversation or {}).get("chat_history") or []
    compact = []
    for message in history[-limit:]:
        if not isinstance(message, dict):
            continue
        compact.append(_compact_dict(message, ["role", "content"]))
    return compact


def _context_size(context: dict) -> int:
    return len(json.dumps(context, ensure_ascii=False, default=str))


def _planner_summary(planner: dict | None) -> dict:
    return _compact_dict(
        planner or {},
        [
            "goal",
            "task_type",
            "workflow",
            "required_information",
            "known_information",
            "missing_information",
            "can_execute",
            "next_step",
            "priority",
            "estimated_response_mode",
            "business_response_mode",
        ],
    )


def _normalized_business_context(business_context: dict | None, *, show_business_insights: bool = False) -> dict:
    context = business_context or {}
    allowed = [
        "business_type",
        "current_product",
        "current_discussion_topic",
        "source",
        "confidence",
        "is_stale",
        "customer_type",
    ]
    if show_business_insights:
        allowed.extend(["conflicts", "internal_labels", "current_goal", "current_problem"])
    compact = _compact_dict(context, allowed)
    return sanitize_user_context_text(compact)


def _business_memory_summary(business_memory: dict | list | None, *, show_business_insights: bool = False) -> dict:
    if not show_business_insights:
        return {}
    if isinstance(business_memory, dict):
        events = business_memory.get("events") or []
    elif isinstance(business_memory, list):
        events = business_memory
    else:
        events = []
    compact_events = []
    for event in events[-3:]:
        if not isinstance(event, dict):
            continue
        compact_events.append(
            sanitize_user_context_text(
                _compact_dict(event, ["event_type", "topic", "summary", "created_at", "payload"])
            )
        )
    return _compact_dict({"recent_events": compact_events})


def _conversation_summary(conversation: dict | None, *, short_question: bool = False) -> dict:
    limit = 2 if short_question else 6
    summary = {
        "recent_messages": _recent_conversation(conversation, limit=limit),
        "current_topic": (conversation or {}).get("current_topic"),
        "last_intent": (conversation or {}).get("last_intent"),
    }
    if not short_question:
        summary["memory"] = (conversation or {}).get("conversation_memory")
    return sanitize_user_context_text(_compact_dict(summary))


def _enforce_prompt_budget(context: dict, budget_chars: int) -> dict:
    if _context_size(context) <= budget_chars:
        return context
    trimmed = dict(context)
    if isinstance(trimmed.get("loaded_skill"), list):
        trimmed["loaded_skill"] = [
            _compact_dict(skill if isinstance(skill, dict) else {}, ["name", "available", "path"])
            for skill in trimmed["loaded_skill"]
        ]
    elif isinstance(trimmed.get("loaded_skill"), dict):
        trimmed["loaded_skill"] = _compact_dict(trimmed["loaded_skill"], ["name", "available", "path"])
    if _context_size(trimmed) <= budget_chars:
        return trimmed
    conversation = trimmed.get("conversation_summary") or {}
    if isinstance(conversation, dict):
        conversation["recent_messages"] = (conversation.get("recent_messages") or [])[-2:]
        conversation.pop("memory", None)
        trimmed["conversation_summary"] = conversation
    if _context_size(trimmed) <= budget_chars:
        return trimmed
    trimmed.pop("business_memory", None)
    trimmed.pop("future_context_sources", None)
    return trimmed


def _skill_summary(loaded_skill: dict | list | None) -> dict | list | None:
    if isinstance(loaded_skill, list):
        return [_skill_summary(skill) for skill in loaded_skill]
    if not isinstance(loaded_skill, dict):
        return None
    return _compact_dict(loaded_skill, ["name", "path", "available", "content"])


def _business_guidance(reasoning: dict | None, planner: dict | None) -> dict:
    reasoning = reasoning or {}
    planner = planner or {}
    intelligence = planner.get("business_intelligence") or {}
    business_reasoning = reasoning.get("business_reasoning") or planner.get("business_reasoning") or intelligence.get("business_reasoning") or {}
    return _compact_dict(
        {
            "matched_skill": reasoning.get("matched_skill") or intelligence.get("matched_skill"),
            "matched_domain": reasoning.get("matched_domain") or intelligence.get("matched_domain"),
            "business_principle": reasoning.get("business_principle") or planner.get("business_principle") or intelligence.get("business_principle"),
            "thinking_pattern": reasoning.get("thinking_pattern") or planner.get("thinking_pattern") or intelligence.get("thinking_pattern"),
            "decision_tree": reasoning.get("decision_tree") or planner.get("decision_tree") or intelligence.get("decision_tree"),
            "questions_to_ask": reasoning.get("questions_to_ask") or planner.get("questions_to_ask") or intelligence.get("questions_to_ask"),
            "response_mode": reasoning.get("response_mode") or planner.get("business_response_mode") or intelligence.get("response_mode"),
            "workflow": reasoning.get("workflow") or intelligence.get("workflow"),
            "memory_tags": reasoning.get("memory_tags") or intelligence.get("memory_tags"),
            "confidence": reasoning.get("confidence") or intelligence.get("confidence") or business_reasoning.get("confidence"),
            "recommended_response": business_reasoning.get("recommended_response"),
            "things_to_avoid": business_reasoning.get("things_to_avoid"),
        }
    )


def build_prompt_context(
    application_state: dict | None,
    planner: dict | None = None,
    capability: dict | None = None,
    loaded_skill: dict | list | None = None,
    reasoning: dict | None = None,
    workflow_state: dict | None = None,
    conversation_memory: dict | None = None,
    store_profile: dict | None = None,
    product_brain: dict | None = None,
    business_context: dict | None = None,
    business_memory: dict | list | None = None,
    current_goal: dict | None = None,
    current_task: str | None = None,
    llm_decision: dict | None = None,
    developer_mode: bool = False,
    show_business_insights: bool = False,
    prompt_budget_chars: int = DEFAULT_PROMPT_BUDGET_CHARS,
) -> dict:
    state = application_state or {}
    store = store_profile if store_profile is not None else state.get("store")
    conversation = conversation_memory if conversation_memory is not None else state.get("conversation")
    workflow = workflow_state if workflow_state is not None else state.get("workflow")
    selected_business_context = business_context or state.get("business_context") or {}
    planner_goal = str((planner or {}).get("goal") or "")
    short_question = bool(planner_goal and len(planner_goal) <= 80 and len(planner_goal.split()) <= 8)

    context = {
        "application_state": _compact_dict(
            state.get("ui") or {},
            ["demo_mode"],
        ),
        "planner_output": _planner_summary(planner),
        "workflow": _compact_dict(
            workflow or {},
            [
                "workflow",
                "current_workflow",
                "step",
                "workflow_step",
                "is_ready",
                "workflow_data",
                "workflow_state_v2",
                "collected_fields",
                "missing_fields",
                "deterministic_reply",
                "user_message",
                "instruction",
            ],
        ),
        "business_context": _normalized_business_context(
            selected_business_context,
            show_business_insights=show_business_insights,
        ),
        "conversation_summary": _conversation_summary(conversation, short_question=short_question),
        "store_profile": _compact_dict(
            store or {},
            ["store_name", "store_type", "product", "target_customer", "tone"],
        ),
        "business_memory": _business_memory_summary(
            business_memory if business_memory is not None else state.get("business_memory"),
            show_business_insights=show_business_insights,
        ),
        "current_goal": current_goal or {},
        "missing_information": (planner or {}).get("missing_information") or (workflow or {}).get("missing_fields") or [],
        "current_task": current_task or (planner or {}).get("task_type"),
        "capability": _compact_dict(
            capability or {},
            ["name", "description", "available", "maturity", "required_modules"],
        ),
        "loaded_skill": _skill_summary(loaded_skill),
        "reasoning": _compact_dict(
            reasoning or {},
            [
                "action",
                "reason",
                "workflow",
                "response_mode",
                "llm_needed",
                "workflow_ready",
                "business_principle",
                "thinking_pattern",
                "decision_tree",
                "questions_to_ask",
                "matched_skill",
                "matched_domain",
                "memory_tags",
                "confidence",
                "bridge_used",
                "fallback_used",
            ],
        ),
        "llm_decision": llm_decision or {},
    }
    business_guidance = _business_guidance(reasoning, planner)
    if business_guidance:
        context["business_guidance"] = business_guidance

    if product_brain:
        context["product_brain"] = product_brain

    if developer_mode:
        developer = state.get("developer") or {}
        context["developer_mode"] = _compact_dict(
            developer,
            ["developer_mode", "current_action", "llm_decision", "llm_latency_ms", "token_usage"],
        )

    context["future_context_sources"] = dict(PLACEHOLDER_CONTEXT_SOURCES)
    compact_context = {key: value for key, value in context.items() if value not in (None, "", [], {})}
    compact_context["prompt_context_size"] = _context_size(compact_context)
    compact_context = _enforce_prompt_budget(compact_context, max(1000, int(prompt_budget_chars or DEFAULT_PROMPT_BUDGET_CHARS)))
    compact_context["prompt_context_size"] = _context_size(compact_context)
    return compact_context
