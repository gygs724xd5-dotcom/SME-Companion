from __future__ import annotations

from dataclasses import dataclass

from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)
from brain.workflow_registry import get_workflow_definition, get_workflow_registry
from brain.workflow_state_machine import detect_workflow_intent


WORKFLOW_ANSWER = "workflow_answer"
NEW_INTENT = "new_intent"
TEMPORARY_INTERRUPT = "temporary_interrupt"
WORKFLOW_SWITCH = "workflow_switch"
CANCEL_WORKFLOW = "cancel_workflow"
RESUME_WORKFLOW = "resume_workflow"
SMALL_TALK = "small_talk"
UNKNOWN = "unknown"


_CANCEL_TRIGGERS = {
    "cancel",
    "stop",
    "\u0e22\u0e01\u0e40\u0e25\u0e34\u0e01",
    "\u0e2b\u0e22\u0e38\u0e14",
    "\u0e40\u0e25\u0e34\u0e01\u0e17\u0e33",
}

_RESUME_TRIGGERS = {
    "resume",
    "continue",
    "\u0e15\u0e48\u0e2d",
    "\u0e17\u0e33\u0e15\u0e48\u0e2d",
    "\u0e01\u0e25\u0e31\u0e1a\u0e21\u0e32\u0e15\u0e48\u0e2d",
}

_TIME_TRIGGERS = {
    "what time",
    "current time",
    "\u0e01\u0e35\u0e48\u0e42\u0e21\u0e07",
    "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e01\u0e35\u0e48\u0e42\u0e21\u0e07",
    "\u0e40\u0e27\u0e25\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
}

_SMALL_TALK_TRIGGERS = {
    "hi",
    "hello",
    "thanks",
    "thank you",
    "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35",
    "\u0e02\u0e2d\u0e1a\u0e04\u0e38\u0e13",
}

_EXTRA_WORKFLOW_TRIGGERS: dict[str, tuple[str, ...]] = {
    WORKFLOW_SALES_PLAN_7_DAY: (
        "\u0e27\u0e32\u0e07\u0e41\u0e1c\u0e19\u0e01\u0e32\u0e23\u0e02\u0e32\u0e22",
        "\u0e27\u0e32\u0e07\u0e41\u0e1c\u0e19\u0e02\u0e32\u0e22",
        "\u0e41\u0e1c\u0e19\u0e01\u0e32\u0e23\u0e02\u0e32\u0e22",
    ),
    WORKFLOW_COST_CALCULATION: (
        "\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
        "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
    ),
    WORKFLOW_RECEIPT_CAPTURE: (
        "\u0e2d\u0e48\u0e32\u0e19\u0e1a\u0e34\u0e25",
        "\u0e1a\u0e34\u0e25",
        "\u0e2a\u0e25\u0e34\u0e1b",
    ),
    WORKFLOW_CONTENT_PLAN: (
        "\u0e2a\u0e23\u0e49\u0e32\u0e07\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
        "\u0e17\u0e33\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
        "\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
        "\u0e04\u0e2d\u0e19\u0e40\u0e17\u0e19\u0e15\u0e4c",
    ),
    WORKFLOW_DASHBOARD_REQUEST: (
        "\u0e27\u0e34\u0e40\u0e04\u0e23\u0e32\u0e30\u0e2b\u0e4c\u0e23\u0e49\u0e32\u0e19",
        "\u0e41\u0e14\u0e0a\u0e1a\u0e2d\u0e23\u0e4c\u0e14",
        "business analysis",
    ),
}

_REQUEST_WORDS = (
    "\u0e0a\u0e48\u0e27\u0e22",
    "\u0e02\u0e2d",
    "\u0e2d\u0e22\u0e32\u0e01",
    "\u0e27\u0e32\u0e07\u0e41\u0e1c\u0e19",
    "\u0e04\u0e33\u0e19\u0e27\u0e13",
    "\u0e2d\u0e48\u0e32\u0e19",
    "\u0e2a\u0e23\u0e49\u0e32\u0e07",
    "\u0e27\u0e34\u0e40\u0e04\u0e23\u0e32\u0e30\u0e2b\u0e4c",
    "plan",
    "calculate",
    "create",
    "analyze",
    "read",
)


@dataclass(frozen=True)
class PriorityDecision:
    classification: str
    priority_action: str
    detected_new_intent: str | None = None
    allow_field_extraction: bool = False
    active_workflow_id: str | None = None
    workflow_step: str | None = None
    missing_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "classification": self.classification,
            "priority_action": self.priority_action,
            "detected_new_intent": self.detected_new_intent,
            "allow_field_extraction": self.allow_field_extraction,
            "active_workflow_id": self.active_workflow_id,
            "workflow_state_v2.step": self.workflow_step,
            "workflow_state_v2.missing_fields": list(self.missing_fields),
        }


def classify_message_priority(user_message: str | None, current_state: dict | None) -> dict:
    state = current_state or {}
    workflow_state = _workflow_state_v2(state)
    os_state = ((state.get("conversation") or {}).get("conversation_os") or {})
    active_workflow_id = (
        os_state.get("active_workflow_id")
        or state.get("active_workflow_id")
        or workflow_state.get("workflow")
        or (state.get("workflow") or {}).get("current_workflow")
        or (state.get("conversation") or {}).get("current_workflow")
    )
    planner_locked = bool(os_state.get("planner_locked") or state.get("planner_locked"))
    step = workflow_state.get("step")
    missing_fields = tuple(workflow_state.get("missing_fields") or ())
    message = str(user_message or "").strip()
    normalized = message.lower()

    decision = _classify(
        message=message,
        normalized=normalized,
        active_workflow_id=active_workflow_id,
        step=step,
        missing_fields=missing_fields,
        planner_locked=planner_locked,
    )
    return decision.to_dict()


def _classify(
    *,
    message: str,
    normalized: str,
    active_workflow_id: str | None,
    step: str | None,
    missing_fields: tuple[str, ...],
    planner_locked: bool,
) -> PriorityDecision:
    if not normalized:
        return _decision(UNKNOWN, "route_normally", active_workflow_id, step, missing_fields)

    if _contains_any(normalized, _CANCEL_TRIGGERS):
        return _decision(CANCEL_WORKFLOW, "cancel_active_workflow", active_workflow_id, step, missing_fields)
    if normalized in _RESUME_TRIGGERS:
        return _decision(RESUME_WORKFLOW, "resume_active_workflow", active_workflow_id, step, missing_fields)
    if _contains_any(normalized, _TIME_TRIGGERS):
        return _decision(TEMPORARY_INTERRUPT, "answer_interrupt_preserve_workflow", active_workflow_id, step, missing_fields)

    detected_workflow = _detect_new_workflow_intent(message)
    if detected_workflow:
        classification = WORKFLOW_SWITCH if active_workflow_id and detected_workflow != active_workflow_id else NEW_INTENT
        return _decision(
            classification,
            "route_to_planner",
            active_workflow_id,
            step,
            missing_fields,
            detected_new_intent=detected_workflow,
        )

    if _is_small_talk(normalized):
        return _decision(SMALL_TALK, "answer_small_talk", active_workflow_id, step, missing_fields)

    if step == "completed" or not missing_fields:
        return _decision(UNKNOWN, "route_to_planner", active_workflow_id, step, missing_fields)

    if active_workflow_id and (planner_locked or step) and _looks_like_short_field_answer(message, normalized):
        return _decision(
            WORKFLOW_ANSWER,
            "continue_field_extraction",
            active_workflow_id,
            step,
            missing_fields,
            allow_field_extraction=True,
        )

    return _decision(UNKNOWN, "route_normally", active_workflow_id, step, missing_fields)


def _decision(
    classification: str,
    priority_action: str,
    active_workflow_id: str | None,
    step: str | None,
    missing_fields: tuple[str, ...],
    *,
    detected_new_intent: str | None = None,
    allow_field_extraction: bool = False,
) -> PriorityDecision:
    return PriorityDecision(
        classification=classification,
        priority_action=priority_action,
        detected_new_intent=detected_new_intent,
        allow_field_extraction=allow_field_extraction,
        active_workflow_id=active_workflow_id,
        workflow_step=step,
        missing_fields=missing_fields,
    )


def _workflow_state_v2(state: dict) -> dict:
    workflow = state.get("workflow") or {}
    conversation = state.get("conversation") or {}
    os_state = conversation.get("conversation_os") or {}
    active_id = os_state.get("active_workflow_id")
    active = (os_state.get("workflow_states") or {}).get(active_id) if active_id else {}
    return (
        state.get("workflow_state_v2")
        or workflow.get("workflow_state_v2")
        or conversation.get("workflow_state_v2")
        or (active or {}).get("state_machine")
        or {}
    )


def _detect_new_workflow_intent(message: str) -> str | None:
    detected = detect_workflow_intent(message)
    if detected:
        return detected

    normalized = message.lower()
    for workflow_id, triggers in _EXTRA_WORKFLOW_TRIGGERS.items():
        if any(trigger.lower() in normalized for trigger in triggers):
            return workflow_id

    definition = get_workflow_registry().detect(message)
    if definition and definition.workflow_id:
        return definition.workflow_id
    return None


def _contains_any(normalized: str, triggers) -> bool:
    return any(trigger and trigger in normalized for trigger in triggers)


def _is_small_talk(normalized: str) -> bool:
    return normalized in _SMALL_TALK_TRIGGERS or any(normalized.startswith(trigger + " ") for trigger in _SMALL_TALK_TRIGGERS)


def _looks_like_short_field_answer(message: str, normalized: str) -> bool:
    if "?" in message or "\u0e44\u0e2b\u0e21" in normalized:
        return False
    if _contains_any(normalized, _REQUEST_WORDS):
        return False
    words = [word for word in normalized.split() if word]
    if len(words) > 6:
        return _has_number(normalized) and len(words) <= 14 and len(message) <= 160
    return len(message) <= 80


def _has_number(value: str) -> bool:
    return any(character.isdigit() for character in value)


def workflow_name(workflow_id: str | None) -> str | None:
    definition = get_workflow_definition(workflow_id)
    return definition.workflow_name if definition else None
