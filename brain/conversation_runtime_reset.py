from __future__ import annotations

from copy import deepcopy


RESET_RUNTIME_STATE_VERSION = "v5.2.0.1"


RUNTIME_CONVERSATION_DEFAULTS = {
    "current_topic": None,
    "business_type": None,
    "latest_business_goal": None,
    "last_question": None,
    "last_answer": None,
    "follow_up_expected": False,
    "last_intent": None,
    "previous_intent": None,
    "conversation_stage": "new",
    "last_feedback": None,
    "last_correction": None,
    "greeted": False,
    "current_workflow": None,
    "workflow_step": None,
    "workflow_data": {},
    "workflow_started_at": None,
    "last_workflow_message": None,
    "workflow_state_v2": {},
    "workflow_blocked_phrases": {},
    "conversation_os": {},
    "last_generated_response": None,
    "last_response_type": None,
    "last_generation_context": {},
    "last_variant_history": [],
    "last_transformation_chain": [],
    "transformation_history": [],
    "response_memory": {},
}


RESET_CLEARED_KEYS = [
    "conversation",
    "workflow",
    "business_context",
    "conversation_understanding",
    "conversation_memory",
    "conversation_intelligence",
    "business_intelligence",
    "knowledge_context",
    "reasoning_context",
    "planner_context",
    "last_task_route",
    "last_reasoning",
    "last_llm_decision",
    "response_envelope_cache",
    "response_memory",
    "last_generated_response",
    "last_response_type",
    "last_generation_context",
    "last_variant_history",
    "last_transformation_chain",
    "transformation_history",
    "last_business_entities",
    "extracted_entities",
    "last_intent",
    "previous_intent",
    "followup_chain",
    "continuation_mode",
    "last_completed_workflow",
]


RESET_PRESERVED_KEYS = [
    "auth_session",
    "auth_owner_id",
    "authenticated",
    "current_user",
    "current_owner_id",
    "current_store_id",
    "current_store_name",
    "store",
    "store_profile",
    "business_memory",
    "ui",
    "developer_mode",
    "future_hooks",
]


def _fresh_conversation_state(conversation_id: str | None = None) -> dict:
    state = deepcopy(RUNTIME_CONVERSATION_DEFAULTS)
    state["conversation_id"] = conversation_id
    state["chat_history"] = []
    state["pending_followup"] = None
    return state


def _fresh_workflow_state() -> dict:
    return {
        "current_workflow": None,
        "workflow_step": None,
        "workflow_data": {},
        "workflow_state_v2": {},
        "workflow": None,
        "step": None,
        "is_ready": False,
        "last_workflow_message": None,
    }


def reset_transient_conversation_state(
    application_state: dict | None,
    *,
    conversation_id: str | None = None,
    reason: str = "new_conversation",
) -> tuple[dict, dict]:
    """Clear per-conversation runtime state while keeping durable store identity."""
    source = application_state if isinstance(application_state, dict) else {}
    next_state = deepcopy(source)

    store = deepcopy(next_state.get("store") or {})
    store.pop("last_completed_workflow", None)
    next_state["store"] = store

    developer = deepcopy(next_state.get("developer") or {})
    developer_mode = developer.get("developer_mode")
    future_hooks = deepcopy(developer.get("future_hooks"))
    developer = {}
    if developer_mode is not None:
        developer["developer_mode"] = developer_mode
    if future_hooks is not None:
        developer["future_hooks"] = future_hooks

    diagnostics = {
        "conversation_reset_applied": True,
        "reset_runtime_state_version": RESET_RUNTIME_STATE_VERSION,
        "reset_cleared_keys": list(RESET_CLEARED_KEYS),
        "reset_preserved_keys": list(RESET_PRESERVED_KEYS),
        "reset_reason": reason,
    }
    developer.update(diagnostics)

    next_state["conversation"] = _fresh_conversation_state(conversation_id)
    next_state["workflow"] = _fresh_workflow_state()
    next_state["business_context"] = {}
    next_state["developer"] = developer

    for key in (
        "conversation_understanding",
        "conversation_memory",
        "conversation_intelligence",
        "business_intelligence",
        "knowledge_context",
        "reasoning_context",
        "planner_context",
        "last_task_route",
        "last_reasoning",
        "last_llm_decision",
        "response_envelope_cache",
        "response_memory",
    ):
        next_state.pop(key, None)

    return next_state, diagnostics


def clear_conversation_runtime_state(
    application_state: dict | None,
    *,
    conversation_id: str | None = None,
    reason: str = "new_conversation",
) -> tuple[dict, dict]:
    return reset_transient_conversation_state(
        application_state,
        conversation_id=conversation_id,
        reason=reason,
    )
