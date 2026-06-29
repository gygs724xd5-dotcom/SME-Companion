from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

try:
    import streamlit as st
except Exception:  # pragma: no cover - streamlit is optional for direct unit tests
    st = None

from memory.application_state import application_state, ensure_application_state


_fallback_trace: dict | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_state():
    if st is None:
        return None
    try:
        return st.session_state
    except Exception:
        return None


def _workflow_state_from(source: dict | None) -> dict:
    source = source or {}
    workflow = source.get("workflow") or {}
    conversation = source.get("conversation") or {}
    return (
        workflow.get("workflow_state_v2")
        or conversation.get("workflow_state_v2")
        or source.get("workflow_state_v2")
        or {}
    )


def _safe_get(container, key, default=None):
    try:
        if container is None:
            return default
        if hasattr(container, "get"):
            return container.get(key, default)
        return container[key]
    except Exception:
        return default


def _key_state(overrides: dict | None = None) -> dict:
    session = _session_state()
    session_app_state = _safe_get(session, "application_state", {}) or {}
    app_state = session_app_state if isinstance(session_app_state, dict) else application_state
    conversation = _safe_get(session, "conversation_state", {}) or (app_state.get("conversation") or {})
    workflow_state = (
        (conversation or {}).get("workflow_state_v2")
        or _workflow_state_from(app_state)
        or {}
    )
    workflow_section = app_state.get("workflow") or {}
    developer = app_state.get("developer") or {}
    route = _safe_get(session, "last_task_route", {}) or developer.get("task_route") or {}
    planner = route.get("planner_output") or {}

    state = {
        "active_workflow_id": (
            workflow_state.get("workflow")
            or workflow_section.get("active_workflow_id")
            or workflow_section.get("current_workflow")
            or (conversation or {}).get("current_workflow")
        ),
        "planner_locked": bool(route.get("planner_locked") or planner.get("planner_locked")),
        "workflow_state_v2.workflow": workflow_state.get("workflow"),
        "workflow_state_v2.step": workflow_state.get("step"),
        "workflow_state_v2.collected_fields": deepcopy(workflow_state.get("collected_fields") or {}),
        "workflow_state_v2.missing_fields": list(workflow_state.get("missing_fields") or []),
        "response_source": _safe_get(session, "last_response_source") or developer.get("last_response_source"),
        "last_response_empty": bool(_safe_get(session, "last_response_empty") or developer.get("last_response_empty")),
        "last_pipeline_error": _safe_get(session, "last_pipeline_error") or developer.get("last_pipeline_error"),
    }
    if overrides:
        state.update(overrides)
    return state


def _set_trace(trace: dict) -> None:
    global _fallback_trace
    _fallback_trace = trace

    session = _session_state()
    if session is not None:
        session["last_pipeline_trace"] = trace
        session_app_state = _safe_get(session, "application_state")
        if isinstance(session_app_state, dict):
            ensure_application_state(session_app_state)
            session_app_state.setdefault("debug", {})["last_pipeline_trace"] = trace

    ensure_application_state(application_state)
    application_state.setdefault("debug", {})["last_pipeline_trace"] = trace


def _mark_trace_error(message: str) -> None:
    trace = _fallback_trace
    if not isinstance(trace, dict):
        return
    trace["trace_error"] = message
    try:
        _set_trace(trace)
    except Exception:
        pass


def start_pipeline_trace(user_message):
    try:
        trace = {
            "trace_id": str(uuid4()),
            "user_message": str(user_message or ""),
            "status": "started",
            "started_at": _now(),
            "finalized_at": None,
            "events": [],
            "trace_error": None,
        }
        _set_trace(trace)
        add_pipeline_event(
            "input",
            "start_pipeline_trace",
            "user input received",
            {"user_message_length": len(str(user_message or ""))},
        )
        return trace
    except Exception as error:
        try:
            _mark_trace_error(f"{type(error).__name__}: {error}")
        except Exception:
            pass
        return {}


def add_pipeline_event(stage, function, message="", key_state=None):
    try:
        trace = get_pipeline_trace()
        if not isinstance(trace, dict) or not trace:
            trace = {
                "trace_id": str(uuid4()),
                "user_message": "",
                "status": "started",
                "started_at": _now(),
                "finalized_at": None,
                "events": [],
                "trace_error": None,
            }
        events = trace.setdefault("events", [])
        events.append(
            {
                "step_id": len(events) + 1,
                "stage": str(stage or ""),
                "function": str(function or ""),
                "message": str(message or ""),
                "key_state": _key_state(key_state if isinstance(key_state, dict) else None),
                "timestamp": _now(),
            }
        )
        _set_trace(trace)
        return trace
    except Exception as error:
        try:
            _mark_trace_error(f"{type(error).__name__}: {error}")
        except Exception:
            pass
        return {}


def finalize_pipeline_trace(status="completed"):
    try:
        trace = get_pipeline_trace()
        if not isinstance(trace, dict) or not trace:
            return {}
        trace["status"] = str(status or "completed")
        trace["finalized_at"] = _now()
        _set_trace(trace)
        return trace
    except Exception as error:
        try:
            _mark_trace_error(f"{type(error).__name__}: {error}")
        except Exception:
            pass
        return {}


def get_pipeline_trace():
    try:
        session = _session_state()
        trace = _safe_get(session, "last_pipeline_trace")
        if isinstance(trace, dict):
            return trace
        debug = application_state.get("debug") or {}
        trace = debug.get("last_pipeline_trace")
        if isinstance(trace, dict):
            return trace
        return _fallback_trace or {}
    except Exception:
        return _fallback_trace or {}
