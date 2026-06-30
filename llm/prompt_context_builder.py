from __future__ import annotations

import json
import re

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
RECENT_MESSAGE_LIMIT = 4
RECENT_MESSAGE_MAX_CHARS = 280


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
    seen = set()
    for message in history[-limit:]:
        if not isinstance(message, dict):
            continue
        item = _compact_dict(message, ["role", "content"])
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        content = re.sub(r"\s+", " ", content)
        if len(content) > RECENT_MESSAGE_MAX_CHARS:
            content = f"{content[:RECENT_MESSAGE_MAX_CHARS].rstrip()}..."
        item["content"] = content
        fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        compact.append(item)
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


def _business_intent_entity_context(
    business_context: dict | None,
    planner: dict | None,
    reasoning: dict | None,
) -> dict:
    context = business_context or {}
    planner_intelligence = (planner or {}).get("business_intelligence") or {}
    reasoning = reasoning or {}
    detected_intent = (
        context.get("detected_intent")
        or planner_intelligence.get("detected_intent")
        or reasoning.get("detected_intent")
    )
    extracted_entities = (
        context.get("extracted_entities")
        or planner_intelligence.get("extracted_entities")
        or reasoning.get("extracted_entities")
        or {}
    )
    return _compact_dict(
        {
            "detected_intent": detected_intent,
            "intent_confidence": context.get("intent_confidence"),
            "matched_intent_keywords": context.get("matched_intent_keywords"),
            "extracted_entities": extracted_entities,
            "missing_entities": context.get("missing_entities"),
            "entity_confidence": context.get("entity_confidence"),
        }
    )


def _workflow_intelligence_context(
    business_context: dict | None,
    planner: dict | None,
    reasoning: dict | None,
    workflow_state: dict | None,
) -> dict:
    source = (
        (business_context or {}).get("workflow_intelligence")
        or (planner or {}).get("workflow_intelligence")
        or (reasoning or {}).get("workflow_intelligence")
        or (workflow_state or {}).get("workflow_intelligence")
        or {}
    )
    return _compact_dict(source, ["workflow_action", "workflow_stage", "workflow_progress"])


def _workflow_diagnostics(
    business_context: dict | None,
    planner: dict | None,
    reasoning: dict | None,
    workflow_state: dict | None,
) -> dict:
    source = (
        (business_context or {}).get("workflow_intelligence")
        or (planner or {}).get("workflow_intelligence")
        or (reasoning or {}).get("workflow_intelligence")
        or (workflow_state or {}).get("workflow_intelligence")
        or {}
    )
    return _compact_dict(
        source,
        [
            "workflow_action",
            "workflow_state",
            "workflow_stage",
            "workflow_progress",
            "workflow_confidence",
            "workflow_complete",
            "workflow_interrupted",
            "workflow_resume_available",
            "workflow_reason",
            "required_entities",
            "completed_entities",
            "missing_entities",
            "entity_completeness",
        ],
    )


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
    limit = 2 if short_question else RECENT_MESSAGE_LIMIT
    memory = (conversation or {}).get("conversation_memory")
    compact_memory = {}
    if isinstance(memory, dict) and not short_question:
        compact_memory = _compact_dict(
            memory,
            [
                "last_intent",
                "last_workflow",
                "focused_business_topic",
                "recent_topics",
                "summary",
            ],
        )
    summary = {
        "recent_messages": _recent_conversation(conversation, limit=limit),
        "current_topic": (conversation or {}).get("current_topic"),
        "last_intent": (conversation or {}).get("last_intent"),
    }
    if compact_memory:
        summary["memory"] = compact_memory
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


def _selected_skill_id(reasoning: dict | None, planner: dict | None) -> str | None:
    reasoning = reasoning or {}
    planner = planner or {}
    intelligence = planner.get("business_intelligence") or {}
    matched = reasoning.get("matched_skill") or intelligence.get("matched_skill") or {}
    if isinstance(matched, dict):
        return matched.get("skill_id") or matched.get("name")
    if matched:
        return str(matched)
    return (
        reasoning.get("business_skill_id")
        or intelligence.get("top_skill")
        or ((planner.get("business_reasoning") or {}).get("skill_id") if isinstance(planner.get("business_reasoning"), dict) else None)
    )


def _select_relevant_skill(loaded_skill: dict | list | None, reasoning: dict | None, planner: dict | None) -> dict | list | None:
    if not loaded_skill:
        return None
    selected_id = _selected_skill_id(reasoning, planner)
    skills = loaded_skill if isinstance(loaded_skill, list) else [loaded_skill]
    if selected_id:
        selected_text = str(selected_id).strip().lower()
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            identifiers = [
                skill.get("skill_id"),
                skill.get("id"),
                skill.get("name"),
                skill.get("path"),
                skill.get("source_path"),
            ]
            if any(selected_text and selected_text in str(identifier or "").lower() for identifier in identifiers):
                return _skill_summary(skill)
    if len(skills) == 1:
        return _skill_summary(skills[0])
    return [_compact_dict(skill if isinstance(skill, dict) else {}, ["name", "available", "path"]) for skill in skills[:3]]


def _fingerprint(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _dedupe_value(value):
    if isinstance(value, dict):
        return {
            key: deduped
            for key, item in value.items()
            for deduped in [_dedupe_value(item)]
            if deduped not in (None, "", [], {})
        }
    if isinstance(value, list):
        deduped_list = []
        seen = set()
        for item in value:
            deduped = _dedupe_value(item)
            if deduped in (None, "", [], {}):
                continue
            fingerprint = _fingerprint(deduped)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            deduped_list.append(deduped)
        return deduped_list
    return value


def _dedupe_context_sections(context: dict) -> tuple[dict, list[str]]:
    deduped = {}
    omitted = []
    seen_payloads = {}
    for key, value in context.items():
        normalized = _dedupe_value(value)
        if normalized in (None, "", [], {}):
            omitted.append(key)
            continue
        fingerprint = _fingerprint(normalized)
        if fingerprint in seen_payloads:
            omitted.append(key)
            continue
        seen_payloads[fingerprint] = key
        deduped[key] = normalized
    return deduped, omitted


def _business_skill_name(reasoning: dict | None, planner: dict | None) -> str | None:
    reasoning = reasoning or {}
    planner = planner or {}
    intelligence = planner.get("business_intelligence") or {}
    matched = reasoning.get("matched_skill") or intelligence.get("matched_skill") or {}
    if isinstance(matched, dict):
        return matched.get("skill_id") or matched.get("skill_name") or matched.get("name")
    return _selected_skill_id(reasoning, planner)


def _business_domain(reasoning: dict | None, planner: dict | None) -> str | None:
    reasoning = reasoning or {}
    planner = planner or {}
    intelligence = planner.get("business_intelligence") or {}
    matched = reasoning.get("matched_skill") or intelligence.get("matched_skill") or {}
    if isinstance(matched, dict) and matched.get("business_domain"):
        return matched.get("business_domain")
    return reasoning.get("matched_domain") or intelligence.get("matched_domain")


def _matched_intents(planner: dict | None, reasoning: dict | None, llm_decision: dict | None) -> list[str]:
    intents = [
        (planner or {}).get("task_type"),
        (planner or {}).get("workflow"),
        (reasoning or {}).get("action"),
        (reasoning or {}).get("response_mode"),
        (llm_decision or {}).get("response_mode"),
    ]
    return [str(intent) for intent in intents if intent not in (None, "", [], {})]


def _diagnostics(
    context: dict,
    selected_business_context: dict,
    reasoning: dict | None,
    planner: dict | None,
    llm_decision: dict | None,
    included_sections: list[str],
    omitted_sections: list[str],
) -> dict:
    return {
        "prompt_context_size": _context_size(context),
        "selected_business_skill": _business_skill_name(reasoning, planner),
        "selected_business_domain": _business_domain(reasoning, planner),
        "matched_intents": _matched_intents(planner, reasoning, llm_decision),
        "detected_intent": selected_business_context.get("detected_intent"),
        "extracted_entities": selected_business_context.get("extracted_entities") or {},
        "context_source": selected_business_context.get("source"),
        "context_confidence": selected_business_context.get("confidence"),
        "context_conflicts": selected_business_context.get("conflicts") or [],
        "stale_context_detected": bool(selected_business_context.get("is_stale") or selected_business_context.get("conflicts")),
        "included_context_sections": included_sections,
        "omitted_context_sections": omitted_sections,
    }


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
        "business_intent_entities": _business_intent_entity_context(
            selected_business_context,
            planner,
            reasoning,
        ),
        "workflow_context": _workflow_intelligence_context(
            selected_business_context,
            planner,
            reasoning,
            workflow,
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
        workflow_diagnostics = _workflow_diagnostics(
            selected_business_context,
            planner,
            reasoning,
            workflow,
        )
        if workflow_diagnostics:
            context["workflow_diagnostics"] = workflow_diagnostics

    context["loaded_skill"] = _select_relevant_skill(loaded_skill, reasoning, planner)
    if developer_mode:
        context["future_context_sources"] = dict(PLACEHOLDER_CONTEXT_SOURCES)
    compact_context = {key: value for key, value in context.items() if value not in (None, "", [], {})}
    compact_context, omitted_sections = _dedupe_context_sections(compact_context)
    included_sections = list(compact_context.keys())
    compact_context["prompt_context_size"] = _context_size(compact_context)
    compact_context = _enforce_prompt_budget(compact_context, max(1000, int(prompt_budget_chars or DEFAULT_PROMPT_BUDGET_CHARS)))
    compact_context["prompt_context_size"] = _context_size(compact_context)
    if developer_mode:
        compact_context["diagnostics"] = _diagnostics(
            compact_context,
            selected_business_context,
            reasoning,
            planner,
            llm_decision,
            included_sections,
            omitted_sections,
        )
        compact_context["prompt_context_size"] = _context_size(compact_context)
    return compact_context
