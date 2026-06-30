from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from brain.workflow_registry import WorkflowDefinition, get_workflow_definition, get_workflow_registry
from brain.conversation_priority_engine import (
    WORKFLOW_ANSWER,
    classify_message_priority,
)
from brain.workflow_readiness import WORKFLOW_DASHBOARD_REQUEST, WORKFLOW_RECEIPT_CAPTURE
from brain.workflow_state_machine import new_workflow_state, update_workflow_state
from brain.workflow_lifecycle import (
    STATUS_COMPLETED,
    STATUS_EXECUTING,
    STATUS_RELEASED,
    attach_lifecycle_diagnostics,
)


CONVERSATION_MODES = {
    "general_chat",
    "workflow",
    "planning",
    "analysis",
    "ocr",
    "catalog_import",
    "inventory",
    "crm",
    "marketing",
    "business_coaching",
}

WORKFLOW_STATUS_ACTIVE = {"START", "COLLECT", "VALIDATE", "EXECUTE", "SUMMARY", "PAUSED"}
WORKFLOW_STATUS_DONE = {"END", "CANCELLED", "TIMEOUT"}

CONTROL_CANCEL = {"cancel", "ยกเลิก", "หยุด", "เลิกทำ"}
CONTROL_PAUSE = {"pause", "พักไว้", "ไว้ก่อน", "หยุดไว้ก่อน"}
CONTROL_RESUME = {"resume", "ต่อ", "ทำต่อ", "กลับมาต่อ"}
UNRELATED_TIME = {"what time", "เวลาเท่าไหร่", "กี่โมง"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_conversation_os_state(owner_id: str | None = None, store_id: str | None = None) -> dict:
    timestamp = now_iso()
    return {
        "conversation_id": str(uuid4()),
        "mode": "general_chat",
        "active_workflow_id": None,
        "planner_locked": False,
        "conversation_stack": [],
        "workflow_states": {},
        "created_at": timestamp,
        "updated_at": timestamp,
        "owner_id": owner_id,
        "store_id": store_id,
        "last_event": None,
        "last_resume_prompt": None,
        "last_paused_workflow_id": None,
    }


def ensure_conversation_os_state(application_state: dict | None) -> dict:
    state = application_state if application_state is not None else {}
    conversation = state.setdefault("conversation", {})
    os_state = conversation.get("conversation_os")
    if not isinstance(os_state, dict):
        os_state = new_conversation_os_state(
            owner_id=_owner_id(state),
            store_id=_store_id(state),
        )
        conversation["conversation_os"] = os_state
    os_state.setdefault("conversation_stack", [])
    os_state.setdefault("workflow_states", {})
    os_state.setdefault("mode", "general_chat")
    os_state.setdefault("planner_locked", False)
    os_state.setdefault("last_paused_workflow_id", None)
    os_state["owner_id"] = os_state.get("owner_id") or _owner_id(state)
    os_state["store_id"] = os_state.get("store_id") or _store_id(state)
    return os_state


def active_workflow_state(application_state: dict | None) -> dict | None:
    os_state = ensure_conversation_os_state(application_state if application_state is not None else {})
    active_id = os_state.get("active_workflow_id")
    if not active_id:
        return None
    workflow_state = (os_state.get("workflow_states") or {}).get(active_id)
    if workflow_state and workflow_state.get("workflow_status") not in WORKFLOW_STATUS_DONE and workflow_state.get("workflow_status") != "PAUSED":
        return workflow_state
    return None


def has_active_workflow(application_state: dict | None) -> bool:
    return active_workflow_state(application_state) is not None


def start_workflow(
    application_state: dict | None,
    workflow_id: str,
    *,
    initial_message: str | None = None,
    owner_id: str | None = None,
    store_id: str | None = None,
) -> dict:
    state = application_state if application_state is not None else {}
    os_state = ensure_conversation_os_state(state)
    definition = get_workflow_definition(workflow_id)
    if definition is None:
        raise ValueError(f"Workflow is not registered: {workflow_id}")

    timestamp = now_iso()
    current_active = active_workflow_state(state)
    if current_active and current_active.get("workflow_id") != workflow_id:
        paused = _with_status(current_active, "PAUSED")
        os_state["workflow_states"][paused.get("workflow_id")] = paused
        _push_stack(os_state, paused)

    base_state = new_workflow_state(workflow_id)
    if initial_message:
        base_state, _ = update_workflow_state(base_state, initial_message, detected_workflow=workflow_id)

    workflow_state = _workflow_os_payload(
        definition,
        base_state,
        workflow_status="COLLECT" if base_state.get("missing_fields") else "EXECUTE",
        owner_id=owner_id or os_state.get("owner_id"),
        store_id=store_id or os_state.get("store_id"),
        started_at=timestamp,
    )
    os_state["workflow_states"][workflow_id] = workflow_state
    os_state["active_workflow_id"] = workflow_id
    os_state["mode"] = _valid_mode(definition.mode)
    os_state["planner_locked"] = True
    os_state["updated_at"] = timestamp
    os_state["last_event"] = "workflow_started"
    return workflow_state


def continue_workflow(application_state: dict | None, user_message: str) -> dict:
    state = application_state if application_state is not None else {}
    control = detect_control_intent(user_message)
    current = active_workflow_state(state)
    if not current:
        if control == "resume":
            workflow_state = resume_workflow(state)
            return {
                "handled": bool(workflow_state),
                "event": "resumed" if workflow_state else "no_active_workflow",
                "workflow_state": workflow_state,
            }
        return {"handled": False, "reason": "no_active_workflow"}

    if control == "cancel" and current.get("cancel_allowed", True):
        return {"handled": True, "event": "cancelled", "workflow_state": cancel_workflow(state)}
    if control == "pause" and current.get("resume_allowed", True):
        return {"handled": True, "event": "paused", "workflow_state": pause_workflow(state)}
    if control == "resume":
        return {"handled": True, "event": "resumed", "workflow_state": resume_workflow(state)}
    if is_unrelated_question(user_message):
        return {"handled": False, "event": "temporary_interrupt", "planner_locked": False, "resume_after_reply": True}

    incoming = detect_registered_workflow(user_message)
    if incoming and incoming.workflow_id != current.get("workflow_id"):
        current_definition = get_workflow_definition(current.get("workflow_id"))
        current_priority = current_definition.priority if current_definition else 0
        if incoming.priority > current_priority:
            workflow_state = start_workflow(state, incoming.workflow_id, initial_message=user_message)
            return {
                "handled": True,
                "event": "workflow_switched",
                "workflow_state": workflow_state,
                "interrupted_workflow_id": current.get("workflow_id"),
            }

    priority = classify_message_priority(user_message, state)
    if priority.get("classification") != WORKFLOW_ANSWER:
        if current.get("workflow_id") in {WORKFLOW_DASHBOARD_REQUEST, WORKFLOW_RECEIPT_CAPTURE}:
            return {
                "handled": True,
                "event": "workflow_continued",
                "workflow_state": current,
                "extracted_fields": {},
                "priority_decision": priority,
            }
        return {
            "handled": False,
            "event": "priority_route",
            "priority_decision": priority,
            "planner_locked": False,
            "resume_after_reply": False,
        }

    updated_state, extracted_fields = update_workflow_state(
        _state_machine_view(current),
        user_message,
        detected_workflow=current.get("workflow_id"),
    )
    status = "EXECUTE" if updated_state.get("is_ready") else "COLLECT"
    workflow_state = _merge_workflow_state(current, updated_state, workflow_status=status)
    _set_active_workflow_state(state, workflow_state)
    return {
        "handled": True,
        "event": "workflow_continued",
        "workflow_state": workflow_state,
        "extracted_fields": extracted_fields,
    }


def complete_workflow(application_state: dict | None, workflow_id: str | None = None) -> dict | None:
    state = application_state if application_state is not None else {}
    current = active_workflow_state(state)
    if not current:
        return None
    if workflow_id and current.get("workflow_id") != workflow_id:
        return current
    workflow_state = _with_status(current, "END")
    workflow_state = {
        **workflow_state,
        "workflow_lifecycle_status": STATUS_COMPLETED,
        "workflow_status": "END",
        "workflow_complete": True,
        "workflow_completion_reason": "workflow executed and response generated",
        "workflow_release_reason": "completed workflow released from active planner lock",
        "workflow_released": True,
    }
    _record_completion_memory(state, workflow_state)
    _set_active_workflow_state(state, workflow_state)
    _pop_or_unlock(state)
    return workflow_state


def pause_workflow(application_state: dict | None) -> dict | None:
    state = application_state if application_state is not None else {}
    current = active_workflow_state(state)
    if not current:
        return None
    workflow_state = _with_status(current, "PAUSED")
    _set_active_workflow_state(state, workflow_state)
    workflow_id = workflow_state.get("workflow_id")
    _unlock(state, "workflow_paused")
    ensure_conversation_os_state(state)["last_paused_workflow_id"] = workflow_id
    return workflow_state


def resume_workflow(application_state: dict | None) -> dict | None:
    state = application_state if application_state is not None else {}
    os_state = ensure_conversation_os_state(state)
    current = active_workflow_state(state)
    if not current and os_state.get("conversation_stack"):
        current = os_state["conversation_stack"].pop()
    if not current and os_state.get("last_paused_workflow_id"):
        paused_id = os_state.get("last_paused_workflow_id")
        candidate = (os_state.get("workflow_states") or {}).get(paused_id)
        if candidate and candidate.get("workflow_status") == "PAUSED":
            current = candidate
    if not current:
        return None
    workflow_state = _with_status(current, "COLLECT" if current.get("missing_fields") else "EXECUTE")
    _set_active_workflow_state(state, workflow_state)
    os_state["mode"] = _valid_mode(workflow_state.get("mode"))
    os_state["planner_locked"] = True
    os_state["last_event"] = "workflow_resumed"
    os_state["last_paused_workflow_id"] = None
    os_state["updated_at"] = now_iso()
    return workflow_state


def cancel_workflow(application_state: dict | None) -> dict | None:
    state = application_state if application_state is not None else {}
    current = active_workflow_state(state)
    if not current:
        return None
    workflow_state = _with_status(current, "CANCELLED")
    _set_active_workflow_state(state, workflow_state)
    _pop_or_unlock(state)
    return workflow_state


def route_quick_action(application_state: dict | None, quick_action: str | None) -> dict:
    definition = get_workflow_registry().by_quick_action(quick_action)
    if not definition:
        return {"handled": False, "reason": "unknown_quick_action"}
    workflow_state = start_workflow(application_state if application_state is not None else {}, definition.workflow_id)
    return {"handled": True, "workflow": definition.to_dict(), "workflow_state": workflow_state}


def planner_locked(application_state: dict | None) -> bool:
    current = active_workflow_state(application_state if application_state is not None else {})
    return bool(current and current.get("workflow_status") not in WORKFLOW_STATUS_DONE)


def developer_diagnostics(application_state: dict | None) -> dict:
    state = application_state if application_state is not None else {}
    os_state = deepcopy(ensure_conversation_os_state(state))
    current = active_workflow_state(state) or {}
    return {
        "Conversation Mode": os_state.get("mode"),
        "Active Workflow": current.get("workflow_name") or current.get("workflow_id"),
        "Workflow Step": current.get("current_step"),
        "Conversation Stack": [item.get("workflow_name") or item.get("workflow_id") for item in os_state.get("conversation_stack") or []],
        "Planner Locked": bool(os_state.get("planner_locked")),
        "Collected Fields": current.get("collected_fields") or {},
        "Missing Fields": current.get("missing_fields") or [],
        "Workflow Status": current.get("workflow_status"),
        "workflow_status": current.get("workflow_lifecycle_status") or current.get("workflow_status"),
        "workflow_completion_reason": current.get("workflow_completion_reason"),
        "workflow_release_reason": current.get("workflow_release_reason") or os_state.get("workflow_release_reason"),
        "workflow_transition_reason": current.get("workflow_transition_reason"),
        "workflow_followup_mode": current.get("workflow_followup_mode"),
        "workflow_variant_mode": current.get("workflow_variant_mode"),
        "Workflow Complete?": bool(current.get("workflow_complete") or current.get("workflow_status") == "END"),
        "Workflow Released?": bool(current.get("workflow_released") or (not os_state.get("active_workflow_id") and os_state.get("last_completed_workflow_id"))),
        "Workflow Transition": current.get("workflow_transition_reason") or os_state.get("last_event"),
        "Follow-up Mode": current.get("workflow_followup_mode"),
        "Variant Mode": current.get("workflow_variant_mode"),
        "Execution Reason": current.get("execution_reason"),
        "Readiness Decision": current.get("readiness_decision") or {},
        "Completion Decision": current.get("completion_decision") or {},
        "Transition Decision": current.get("transition_decision") or {},
        "Last Completed Workflow": os_state.get("last_completed_workflow_id"),
        "Resume Available": bool(current.get("resume_allowed")),
    }


def sync_legacy_workflow_state(application_state: dict | None, workflow_state: dict | None) -> None:
    if not application_state or not workflow_state:
        return
    application_state["workflow"] = {
        **(application_state.get("workflow") or {}),
        "current_workflow": workflow_state.get("workflow_id"),
        "workflow": workflow_state.get("workflow_id"),
        "workflow_step": workflow_state.get("current_step"),
        "step": workflow_state.get("current_step"),
        "workflow_data": workflow_state.get("collected_fields") or {},
        "workflow_state_v2": _state_machine_view(workflow_state),
        "is_ready": not bool(workflow_state.get("missing_fields")),
        "last_workflow_message": workflow_state.get("updated_at"),
    }


def detect_registered_workflow(message: str | None) -> WorkflowDefinition | None:
    return get_workflow_registry().detect(message)


def detect_control_intent(message: str | None) -> str | None:
    normalized = str(message or "").strip().lower()
    if not normalized:
        return None
    if any(token in normalized for token in CONTROL_CANCEL):
        return "cancel"
    if any(token in normalized for token in CONTROL_PAUSE):
        return "pause"
    if any(token in normalized for token in CONTROL_RESUME):
        return "resume"
    return None


def is_unrelated_question(message: str | None) -> bool:
    normalized = str(message or "").strip().lower()
    if not normalized:
        return False
    return any(token in normalized for token in UNRELATED_TIME)


def _workflow_os_payload(
    definition: WorkflowDefinition,
    state_machine_state: dict,
    *,
    workflow_status: str,
    owner_id: str | None,
    store_id: str | None,
    started_at: str | None = None,
) -> dict:
    timestamp = now_iso()
    payload = {
        "workflow_id": definition.workflow_id,
        "workflow_name": definition.workflow_name,
        "mode": _valid_mode(definition.mode),
        "current_step": state_machine_state.get("step"),
        "workflow_status": workflow_status,
        "collected_fields": dict(state_machine_state.get("collected_fields") or {}),
        "missing_fields": list(state_machine_state.get("missing_fields") or []),
        "required_fields": list(definition.required_fields or state_machine_state.get("required_fields") or []),
        "started_at": started_at or timestamp,
        "updated_at": timestamp,
        "resume_allowed": definition.resume_allowed,
        "cancel_allowed": definition.cancel_allowed,
        "owner_id": owner_id,
        "store_id": store_id,
        "state_machine": dict(state_machine_state or {}),
    }
    lifecycle_status = STATUS_EXECUTING if workflow_status == "EXECUTE" else None
    payload.update(
        attach_lifecycle_diagnostics(
            {
                **state_machine_state,
                "workflow_status": lifecycle_status,
                "missing_fields": payload["missing_fields"],
            },
            transition_reason="workflow started",
        )
    )
    payload["workflow_status"] = workflow_status
    payload["workflow_lifecycle_status"] = lifecycle_status or payload.get("workflow_status")
    return payload


def _merge_workflow_state(current: dict, state_machine_state: dict, *, workflow_status: str) -> dict:
    timestamp = now_iso()
    lifecycle = attach_lifecycle_diagnostics(
        {
            **state_machine_state,
            "workflow_status": STATUS_EXECUTING if workflow_status == "EXECUTE" else None,
        },
        transition_reason="workflow executable" if workflow_status == "EXECUTE" else "workflow collecting missing fields",
    )
    return {
        **current,
        "current_step": state_machine_state.get("step"),
        "workflow_status": workflow_status,
        "workflow_lifecycle_status": lifecycle.get("workflow_status"),
        "workflow_complete": lifecycle.get("workflow_complete"),
        "workflow_completion_reason": lifecycle.get("workflow_completion_reason"),
        "workflow_release_reason": lifecycle.get("workflow_release_reason"),
        "workflow_transition_reason": lifecycle.get("workflow_transition_reason"),
        "workflow_followup_mode": lifecycle.get("workflow_followup_mode"),
        "workflow_variant_mode": lifecycle.get("workflow_variant_mode"),
        "execution_reason": lifecycle.get("execution_reason"),
        "readiness_decision": lifecycle.get("readiness_decision") or {},
        "completion_decision": lifecycle.get("completion_decision") or {},
        "transition_decision": lifecycle.get("transition_decision") or {},
        "collected_fields": dict(state_machine_state.get("collected_fields") or {}),
        "missing_fields": list(state_machine_state.get("missing_fields") or []),
        "updated_at": timestamp,
        "state_machine": dict(state_machine_state or {}),
    }


def _state_machine_view(workflow_state: dict) -> dict:
    if workflow_state.get("state_machine"):
        return dict(workflow_state.get("state_machine") or {})
    return {
        "workflow": workflow_state.get("workflow_id"),
        "step": workflow_state.get("current_step"),
        "required_fields": list(workflow_state.get("required_fields") or []),
        "collected_fields": dict(workflow_state.get("collected_fields") or {}),
        "missing_fields": list(workflow_state.get("missing_fields") or []),
        "is_ready": not bool(workflow_state.get("missing_fields")),
        "next_action": "generate" if not workflow_state.get("missing_fields") else "ask_missing_field",
        "last_updated": workflow_state.get("updated_at"),
    }


def _set_active_workflow_state(application_state: dict, workflow_state: dict) -> None:
    os_state = ensure_conversation_os_state(application_state)
    workflow_id = workflow_state.get("workflow_id")
    os_state["workflow_states"][workflow_id] = workflow_state
    os_state["active_workflow_id"] = workflow_id
    os_state["mode"] = _valid_mode(workflow_state.get("mode"))
    os_state["planner_locked"] = workflow_state.get("workflow_status") not in WORKFLOW_STATUS_DONE
    os_state["updated_at"] = now_iso()
    sync_legacy_workflow_state(application_state, workflow_state)


def _with_status(workflow_state: dict, status: str) -> dict:
    updated = {**workflow_state, "workflow_status": status, "updated_at": now_iso()}
    if status in WORKFLOW_STATUS_DONE:
        updated["current_step"] = "completed" if status == "END" else status.lower()
    if status == "END":
        updated["workflow_lifecycle_status"] = STATUS_COMPLETED
        updated["workflow_complete"] = True
    elif status == "EXECUTE":
        updated["workflow_lifecycle_status"] = STATUS_EXECUTING
    elif status in {"CANCELLED", "TIMEOUT"}:
        updated["workflow_lifecycle_status"] = STATUS_RELEASED
    return updated


def _push_stack(os_state: dict, workflow_state: dict) -> None:
    stack = os_state.setdefault("conversation_stack", [])
    stack.append(deepcopy(workflow_state))


def _pop_or_unlock(application_state: dict) -> None:
    os_state = ensure_conversation_os_state(application_state)
    stack = os_state.get("conversation_stack") or []
    while stack:
        candidate = stack.pop()
        if candidate.get("workflow_status") not in WORKFLOW_STATUS_DONE:
            resumed = _with_status(candidate, "COLLECT" if candidate.get("missing_fields") else "EXECUTE")
            _set_active_workflow_state(application_state, resumed)
            os_state["last_event"] = "workflow_resumed_from_stack"
            return
    _unlock(application_state, "workflow_completed")


def _unlock(application_state: dict, event: str) -> None:
    os_state = ensure_conversation_os_state(application_state)
    previous_active = os_state.get("active_workflow_id")
    os_state["active_workflow_id"] = None
    os_state["planner_locked"] = False
    os_state["mode"] = "general_chat"
    os_state["updated_at"] = now_iso()
    os_state["last_event"] = event
    if previous_active:
        os_state["last_completed_workflow_id"] = previous_active if event == "workflow_completed" else os_state.get("last_completed_workflow_id")
    if event == "workflow_completed":
        os_state["workflow_release_reason"] = "completed workflow released from active planner lock"
    application_state["workflow"] = {
        **(application_state.get("workflow") or {}),
        "current_workflow": None,
        "workflow": None,
        "workflow_step": None,
        "step": None,
        "workflow_data": {},
        "workflow_state_v2": {},
        "is_ready": False,
    }


def _record_completion_memory(application_state: dict, workflow_state: dict) -> None:
    completed = {
        "workflow_id": workflow_state.get("workflow_id"),
        "workflow_name": workflow_state.get("workflow_name"),
        "completed_at": now_iso(),
        "collected_fields": dict(workflow_state.get("collected_fields") or {}),
        "workflow_status": STATUS_RELEASED,
        "workflow_completion_reason": workflow_state.get("workflow_completion_reason") or "workflow completed",
        "workflow_release_reason": workflow_state.get("workflow_release_reason") or "completed workflow released from active planner lock",
        "owner_id": workflow_state.get("owner_id"),
        "store_id": workflow_state.get("store_id"),
    }

    business_memory = application_state.setdefault("business_memory", {})
    business_memory.setdefault("completed_workflows", []).append(completed)

    conversation = application_state.setdefault("conversation", {})
    conversation.setdefault("conversation_memory", {})
    conversation["conversation_memory"].setdefault("completed_workflows", []).append(completed)

    store = application_state.setdefault("store", {})
    store["last_completed_workflow"] = completed


def _owner_id(application_state: dict) -> str | None:
    auth = application_state.get("auth") or {}
    return application_state.get("owner_id") or auth.get("owner_id")


def _store_id(application_state: dict) -> str | None:
    store = application_state.get("store") or {}
    return application_state.get("store_id") or store.get("store_id")


def _valid_mode(mode: str | None) -> str:
    return mode if mode in CONVERSATION_MODES else "workflow"
