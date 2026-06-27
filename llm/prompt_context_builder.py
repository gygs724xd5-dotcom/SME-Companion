from __future__ import annotations


PLACEHOLDER_CONTEXT_SOURCES = {
    "ocr_engine": None,
    "inventory_engine": None,
    "sales_forecast_engine": None,
    "business_memory": None,
    "marketing_agent": None,
    "financial_agent": None,
    "inventory_agent": None,
}


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


def _skill_summary(loaded_skill: dict | list | None) -> dict | list | None:
    if isinstance(loaded_skill, list):
        return [_skill_summary(skill) for skill in loaded_skill]
    if not isinstance(loaded_skill, dict):
        return None
    return _compact_dict(loaded_skill, ["name", "path", "available", "content"])


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
) -> dict:
    state = application_state or {}
    store = store_profile if store_profile is not None else state.get("store")
    conversation = conversation_memory if conversation_memory is not None else state.get("conversation")
    workflow = workflow_state if workflow_state is not None else state.get("workflow")

    context = {
        "application_state": _compact_dict(
            state.get("ui") or {},
            ["demo_mode"],
        ),
        "planner_output": planner or {},
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
        "business_context": business_context or state.get("business_context") or {},
        "conversation_summary": {
            "recent_messages": _recent_conversation(conversation),
            "current_topic": (conversation or {}).get("current_topic"),
            "last_intent": (conversation or {}).get("last_intent"),
            "memory": (conversation or {}).get("conversation_memory"),
        },
        "store_profile": _compact_dict(
            store or {},
            ["store_name", "store_type", "product", "target_customer", "tone"],
        ),
        "business_memory": business_memory or {},
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
            ["action", "reason", "workflow", "response_mode", "llm_needed", "workflow_ready"],
        ),
        "llm_decision": llm_decision or {},
    }

    if product_brain:
        context["product_brain"] = product_brain

    if developer_mode:
        developer = state.get("developer") or {}
        context["developer_mode"] = _compact_dict(
            developer,
            ["developer_mode", "current_action", "llm_decision", "llm_latency_ms", "token_usage"],
        )

    context["future_context_sources"] = dict(PLACEHOLDER_CONTEXT_SOURCES)
    return {key: value for key, value in context.items() if value not in (None, "", [], {})}
