from __future__ import annotations
import re
from copy import deepcopy
from datetime import datetime, timezone


STATUS_COLLECTING = "COLLECTING"
STATUS_READY = "READY"
STATUS_EXECUTING = "EXECUTING"
STATUS_COMPLETED = "COMPLETED"
STATUS_RELEASED = "RELEASED"

VARIANT_MODE_NONE = None
FOLLOWUP_MODE_NONE = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def workflow_is_executable(workflow_state: dict | None) -> bool:
    state = workflow_state or {}
    if state.get("workflow_status") in {STATUS_COMPLETED, STATUS_RELEASED, "END"}:
        return False
    if state.get("step") == "completed":
        return False
    if state.get("is_ready"):
        return True
    required = list(state.get("required_fields") or [])
    missing = list(state.get("missing_fields") or [])
    return bool(required) and not missing


def lifecycle_status_for_state(workflow_state: dict | None) -> str:
    state = workflow_state or {}
    status = state.get("workflow_status")
    if status == "END" or state.get("step") == "completed":
        return STATUS_COMPLETED
    if status in {STATUS_COMPLETED, STATUS_RELEASED, STATUS_EXECUTING, STATUS_READY, STATUS_COLLECTING}:
        return status
    if workflow_is_executable(state):
        return STATUS_READY
    return STATUS_COLLECTING


def attach_lifecycle_diagnostics(
    workflow_state: dict | None,
    *,
    transition_reason: str | None = None,
    execution_reason: str | None = None,
    completion_reason: str | None = None,
    release_reason: str | None = None,
    followup_mode: str | None = None,
    variant_mode: str | None = None,
) -> dict:
    state = dict(workflow_state or {})
    status = lifecycle_status_for_state(state)
    missing = list(state.get("missing_fields") or [])
    executable = workflow_is_executable(state)
    state.update(
        {
            "workflow_status": status,
            "workflow_complete": status == STATUS_COMPLETED or state.get("step") == "completed",
            "workflow_released": status == STATUS_RELEASED,
            "workflow_executable": executable,
            "workflow_completion_reason": completion_reason or state.get("workflow_completion_reason"),
            "workflow_release_reason": release_reason or state.get("workflow_release_reason"),
            "workflow_transition_reason": transition_reason or state.get("workflow_transition_reason"),
            "workflow_followup_mode": followup_mode if followup_mode is not None else state.get("workflow_followup_mode"),
            "workflow_variant_mode": variant_mode if variant_mode is not None else state.get("workflow_variant_mode"),
            "execution_reason": execution_reason or state.get("execution_reason"),
            "readiness_decision": {
                "workflow_executable": executable,
                "missing_fields": missing,
                "is_ready": bool(state.get("is_ready")),
                "reason": "execute_before_collecting" if executable else "missing_fields_required",
            },
            "completion_decision": {
                "workflow_complete": status == STATUS_COMPLETED or state.get("step") == "completed",
                "reason": completion_reason or state.get("workflow_completion_reason"),
            },
            "transition_decision": {
                "from": state.get("previous_workflow_status"),
                "to": status,
                "reason": transition_reason or state.get("workflow_transition_reason"),
            },
        }
    )
    return state


def mark_executing(workflow_state: dict | None, reason: str) -> dict:
    state = dict(workflow_state or {})
    state["previous_workflow_status"] = lifecycle_status_for_state(state)
    state["workflow_status"] = STATUS_EXECUTING
    state["execution_reason"] = reason
    state["workflow_transition_reason"] = reason
    return attach_lifecycle_diagnostics(state, execution_reason=reason, transition_reason=reason)


def mark_completed(workflow_state: dict | None, reason: str) -> dict:
    state = dict(workflow_state or {})
    state["previous_workflow_status"] = lifecycle_status_for_state(state)
    state["workflow_status"] = STATUS_COMPLETED
    state["workflow_complete"] = True
    state["workflow_completion_reason"] = reason
    state["workflow_transition_reason"] = reason
    return attach_lifecycle_diagnostics(state, completion_reason=reason, transition_reason=reason)


def completed_workflow_context(application_state: dict | None) -> dict | None:
    state = application_state or {}

    if (state.get("developer") or {}).get("conversation_reset_applied"):
        return None

    store_completed = (state.get("store") or {}).get("last_completed_workflow")
    if isinstance(store_completed, dict) and store_completed.get("workflow_id"):
        return deepcopy(store_completed)

    completed = (state.get("business_memory") or {}).get("completed_workflows") or []
    for item in reversed(completed):
        if isinstance(item, dict) and item.get("workflow_id"):
            return deepcopy(item)

    completed = (((state.get("conversation") or {}).get("conversation_memory") or {}).get("completed_workflows") or [])
    for item in reversed(completed):
        if isinstance(item, dict) and item.get("workflow_id"):
            return deepcopy(item)

    return None


def classify_completed_workflow_followup(application_state: dict | None, user_message: str | None) -> dict:
    completed = completed_workflow_context(application_state)
    return {
        "workflow_followup_mode": FOLLOWUP_MODE_NONE,
        "workflow_variant_mode": VARIANT_MODE_NONE,
        "reuse_completed_workflow": False,
        "completed_workflow": completed or {},
        "workflow_transition_reason": "completed workflows are diagnostics only; planner owns next workflow",
        "followup_chain": [],
    }



def completed_to_workflow_state(completed: dict | None) -> dict:
    data = completed or {}
    workflow_id = data.get("workflow_id")
    fields = dict(data.get("collected_fields") or {})
    return attach_lifecycle_diagnostics(
        {
            "workflow": workflow_id,
            "step": "completed",
            "required_fields": [],
            "collected_fields": fields,
            "missing_fields": [],
            "is_ready": False,
            "next_action": "diagnostics_only",
            "last_updated": data.get("completed_at"),
        },
        completion_reason="loaded from completed workflow context",
        followup_mode=FOLLOWUP_MODE_NONE,
    )



def variant_instruction_from_message(message: str | None) -> dict:
    normalized = str(message or "").strip().lower()
    return {
        "short": bool(re.search(r"\u0e2a\u0e31\u0e49\u0e19|short", normalized)),
        "long": bool(re.search(r"\u0e22\u0e32\u0e27|long", normalized)),
        "youth": bool(re.search(r"\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19|teen|young", normalized)),
        "luxury": bool(re.search(r"\u0e2b\u0e23\u0e39|luxury|premium", normalized)),
        "friendly": bool(re.search(r"\u0e40\u0e1b\u0e47\u0e19\u0e01\u0e31\u0e19\u0e40\u0e2d\u0e07|friendly|casual", normalized)),
        "stronger_sales": bool(re.search(r"\u0e02\u0e32\u0e22\u0e40\u0e01\u0e48\u0e07|sell|sales", normalized)),
    }
