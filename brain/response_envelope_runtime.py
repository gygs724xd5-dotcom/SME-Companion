from __future__ import annotations

from copy import deepcopy
from typing import Any

from brain.canonical_objects import ResponseEnvelope


RESPONSE_ENVELOPE_VERSION = "5.1.5"
RESPONSE_ENVELOPE_SOURCE = "v4_response_adapter"


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return deepcopy(value) if isinstance(value, list) else []


def _confidence(route: dict) -> float:
    candidates = [
        route.get("confidence"),
        route.get("reasoning_confidence"),
        (route.get("business_intelligence") or {}).get("confidence"),
        (route.get("business_intelligence") or {}).get("top_confidence"),
        (route.get("reasoning_context") or {}).get("confidence"),
        (route.get("planner_context") or {}).get("confidence"),
    ]
    for candidate in candidates:
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    return 0.0


def _response_text(legacy_response: Any, route: dict) -> str:
    if legacy_response is None:
        return str(route.get("final_response_text") or route.get("reply") or "").strip()
    if isinstance(legacy_response, dict):
        return str(
            legacy_response.get("text")
            or legacy_response.get("reply")
            or legacy_response.get("response")
            or ""
        ).strip()
    return str(legacy_response)


def build_response_envelope(
    legacy_response: Any = None,
    route: dict | None = None,
    diagnostics: dict | None = None,
) -> ResponseEnvelope:
    """Wrap the existing V4 response shape for diagnostics only.

    This adapter intentionally does not select, rewrite, clean, or render text.
    It copies the legacy response text into a V5 envelope so diagnostics can
    observe the future runtime contract without changing response behavior.
    """

    route_data = _as_dict(route)
    diagnostic_data = _as_dict(diagnostics)
    workflow = (
        route_data.get("workflow")
        or route_data.get("business_workflow")
        or (route_data.get("business_context") or {}).get("workflow_intelligence")
        or {}
    )
    source = (
        route_data.get("response_source")
        or route_data.get("final_response_origin")
        or route_data.get("response_source_after_gate")
        or diagnostic_data.get("response_source")
        or "legacy_response"
    )
    memory = _as_dict(route_data.get("conversation_memory") or route_data.get("memory"))

    envelope = ResponseEnvelope(
        turn_id=str(route_data.get("turn_id") or diagnostic_data.get("turn_id") or ""),
        text=_response_text(legacy_response, route_data),
        source=str(source),
        domain=str(
            route_data.get("selected_business_domain")
            or route_data.get("selected_domain")
            or (route_data.get("business_knowledge") or {}).get("selected_domain")
            or ""
        ),
        skill_id=str(
            route_data.get("selected_business_skill")
            or route_data.get("selected_skill")
            or (route_data.get("business_knowledge") or {}).get("selected_skill")
            or ""
        ),
        workflow=_as_dict(workflow),
        confidence=_confidence(route_data),
        follow_up=str(route_data.get("follow_up") or diagnostic_data.get("follow_up") or ""),
        memory_read=_as_list(memory.get("read") or memory.get("read_references")),
        memory_write=_as_list(memory.get("write") or memory.get("write_proposals")),
        diagnostics={
            **diagnostic_data,
            "response_envelope_created": True,
            "response_envelope_version": RESPONSE_ENVELOPE_VERSION,
            "response_envelope_source": RESPONSE_ENVELOPE_SOURCE,
            "response_envelope_present": True,
            "compatibility_mode": "v4_response_wrapped_for_diagnostics_only",
        },
    )
    envelope.version = RESPONSE_ENVELOPE_VERSION
    return envelope


def response_envelope_diagnostics(envelope: ResponseEnvelope | dict | None) -> dict:
    data = envelope.to_dict() if isinstance(envelope, ResponseEnvelope) else _as_dict(envelope)
    present = bool(data)
    return {
        "response_envelope": data,
        "response_envelope_created": bool(
            present and (_as_dict(data.get("diagnostics")).get("response_envelope_created") is not False)
        ),
        "response_envelope_version": data.get("version") or RESPONSE_ENVELOPE_VERSION,
        "response_envelope_source": _as_dict(data.get("diagnostics")).get("response_envelope_source")
        or RESPONSE_ENVELOPE_SOURCE,
        "response_envelope_present": present,
    }
