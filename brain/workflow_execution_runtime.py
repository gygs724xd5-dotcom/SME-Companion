from __future__ import annotations

from brain.conversation_manager import (
    cancel_workflow as _cancel_workflow,
    complete_workflow as _complete_workflow,
    continue_workflow as _continue_workflow,
    pause_workflow as _pause_workflow,
    release_workflow_domain as _release_workflow_domain,
    resume_workflow as _resume_workflow,
    start_workflow as _start_workflow,
)


def start_workflow(application_state: dict | None, workflow_id: str, **kwargs) -> dict:
    return _start_workflow(application_state, workflow_id, **kwargs)


def resume_workflow(application_state: dict | None) -> dict | None:
    return _resume_workflow(application_state)


def suspend_workflow(application_state: dict | None) -> dict | None:
    return _pause_workflow(application_state)


def pause_workflow(application_state: dict | None) -> dict | None:
    return suspend_workflow(application_state)


def complete_workflow(application_state: dict | None, workflow_id: str | None = None) -> dict | None:
    return _complete_workflow(application_state, workflow_id)


def cancel_workflow(application_state: dict | None) -> dict | None:
    return _cancel_workflow(application_state)


def release_workflow(application_state: dict | None, *, next_workflow_id: str | None = None, reason: str = "workflow_released") -> dict:
    return _release_workflow_domain(application_state, next_workflow_id=next_workflow_id, reason=reason)


def continue_workflow(application_state: dict | None, user_message: str) -> dict:
    return _continue_workflow(application_state, user_message)
