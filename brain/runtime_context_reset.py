from __future__ import annotations

from copy import deepcopy
from typing import Any


RUNTIME_CONTEXT_VERSION = "v5.2.0.2"


RUNTIME_CONTEXT_KEYS = [
    "knowledge_context",
    "business_judgment",
    "judgment_response_handoff",
    "judgment_outcome",
    "judgment_revision",
    "reasoning_context",
    "planner_context",
    "planner_decision",
    "response_envelope",
    "response_envelope_cache",
    "planner_migration",
    "planner_hints",
    "planner_decision",
    "execution_plan",
    "execution_context",
    "route_cache",
    "last_task_route",
    "last_llm_decision",
    "selected_domain",
    "selected_skill",
    "current_business_goal",
    "reasoning_pattern",
    "reasoning_confidence",
    "response_metadata",
    "response_route",
    "diagnostic_context",
    "followup_runtime",
    "workflow_runtime",
    "current_topic",
    "focused_business_topic",
    "current_discussion_topic",
    "current_product",
    "previous_workflow",
    "last_workflow",
    "current_workflow",
    "workflow_context",
    "completed_workflow_followup_context",
    "active_cost_context",
    "active_content_context",
    "previous_generated_response",
    "transformation_history",
    "last_transformation_chain",
]


PRESERVED_RUNTIME_ROOTS = [
    "auth_session",
    "auth_owner_id",
    "authenticated",
    "current_user",
    "current_owner_id",
    "current_store_id",
    "current_store_name",
    "business_memory",
    "store_profile",
    "store",
    "selected_store",
    "user_profile",
    "settings",
    "product_catalog",
    "inventory",
    "business_config",
    "ui",
    "receipt",
    "dashboard",
]


def _clear_runtime_keys(value: Any, *, skipped_root: bool = False) -> tuple[Any, set[str]]:
    if isinstance(value, dict):
        cleared: set[str] = set()
        next_value = {}
        for key, child in value.items():
            if not skipped_root and key in RUNTIME_CONTEXT_KEYS:
                cleared.add(key)
                continue
            child_skipped = skipped_root or key in PRESERVED_RUNTIME_ROOTS
            cleaned_child, child_cleared = _clear_runtime_keys(child, skipped_root=child_skipped)
            cleared.update(child_cleared)
            next_value[key] = cleaned_child
        return next_value, cleared

    if isinstance(value, list):
        cleared: set[str] = set()
        next_items = []
        for item in value:
            cleaned_item, item_cleared = _clear_runtime_keys(item, skipped_root=skipped_root)
            cleared.update(item_cleared)
            next_items.append(cleaned_item)
        return next_items, cleared

    return value, set()


def reset_runtime_contexts(
    application_state: dict | None,
    reason: str = "new_conversation",
) -> tuple[dict, dict]:
    """Clear V5 per-turn runtime context while preserving durable business memory."""
    source = application_state if isinstance(application_state, dict) else {}
    next_state = deepcopy(source)
    next_state, actually_cleared = _clear_runtime_keys(next_state)

    diagnostics = {
        "runtime_context_reset_applied": True,
        "runtime_context_version": RUNTIME_CONTEXT_VERSION,
        "runtime_contexts_cleared": list(RUNTIME_CONTEXT_KEYS),
        "runtime_contexts_preserved": list(PRESERVED_RUNTIME_ROOTS),
        "runtime_reset_reason": reason,
        "runtime_contexts_found": sorted(actually_cleared),
    }

    developer = deepcopy(next_state.get("developer") or {})
    developer.update(diagnostics)
    next_state["developer"] = developer

    return next_state, diagnostics
