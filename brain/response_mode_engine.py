from __future__ import annotations

from dataclasses import dataclass


SHORT_REPLY = "SHORT_REPLY"
ASK_NEXT_FIELD = "ASK_NEXT_FIELD"
GENERATE_OUTPUT = "GENERATE_OUTPUT"
NORMAL_CHAT = "NORMAL_CHAT"
BUSINESS_CONSULTING = "BUSINESS_CONSULTING"
WORKFLOW_COMPLETE = "WORKFLOW_COMPLETE"
INTERRUPTION = "INTERRUPTION"
RESUME_WORKFLOW = "RESUME_WORKFLOW"
SMALL_TALK = "SMALL_TALK"
CLARIFICATION = "CLARIFICATION"

SUPPORTED_RESPONSE_MODES = {
    SHORT_REPLY,
    ASK_NEXT_FIELD,
    GENERATE_OUTPUT,
    NORMAL_CHAT,
    BUSINESS_CONSULTING,
    WORKFLOW_COMPLETE,
    INTERRUPTION,
    RESUME_WORKFLOW,
    SMALL_TALK,
    CLARIFICATION,
}

_BUSINESS_TASK_TERMS = {
    "analysis",
    "business analysis",
    "business_analysis",
    "business consulting",
    "dashboard",
    "general business help",
    "sales planning",
    "sales plan",
}

_SMALL_TALK_INTENTS = {"GREETING", "THANKS", "SMALL_TALK"}


@dataclass(frozen=True)
class ResponseModeDecision:
    mode: str
    reason: str

    def to_dict(self) -> dict:
        return {"mode": self.mode, "reason": self.reason}


def _lower(value) -> str:
    return str(value or "").strip().lower()


def determine_response_mode(
    *,
    workflow_state: dict | None = None,
    planner: dict | None = None,
    reasoning: dict | None = None,
    conversation_intent: str | None = None,
    priority_decision: dict | None = None,
    reply_kind: str | None = None,
) -> ResponseModeDecision:
    """Select the presentation mode for the final assistant reply."""
    workflow_state = workflow_state or {}
    planner = planner or {}
    reasoning = reasoning or {}
    priority_decision = priority_decision or {}

    if reply_kind in {INTERRUPTION, RESUME_WORKFLOW, CLARIFICATION, SHORT_REPLY}:
        return ResponseModeDecision(reply_kind, "Explicit reply kind selected by caller.")

    priority_action = _lower(priority_decision.get("priority_action"))
    if "interrupt" in priority_action:
        return ResponseModeDecision(INTERRUPTION, "Conversation priority selected a temporary interruption.")
    if "resume" in priority_action:
        return ResponseModeDecision(RESUME_WORKFLOW, "Conversation priority selected workflow resume.")

    if reasoning.get("requires_clarification") or planner.get("requires_clarification"):
        return ResponseModeDecision(CLARIFICATION, "Clarification is required before answering.")

    if workflow_state:
        if workflow_state.get("step") == "completed":
            return ResponseModeDecision(WORKFLOW_COMPLETE, "Workflow state is completed.")
        if workflow_state.get("is_ready") or workflow_state.get("next_action") == "generate":
            return ResponseModeDecision(GENERATE_OUTPUT, "Workflow has enough fields to generate output.")
        if workflow_state.get("workflow") and workflow_state.get("missing_fields"):
            return ResponseModeDecision(ASK_NEXT_FIELD, "Workflow is collecting missing fields.")

    next_step = _lower(planner.get("next_step"))
    if next_step == "collect_missing_information":
        return ResponseModeDecision(ASK_NEXT_FIELD, "Planner is collecting missing information.")

    task_type = _lower(planner.get("task_type") or planner.get("workflow") or reasoning.get("workflow"))
    if any(term in task_type for term in _BUSINESS_TASK_TERMS):
        return ResponseModeDecision(BUSINESS_CONSULTING, "Business task should use a structured consulting answer.")

    if str(conversation_intent or "").upper() in _SMALL_TALK_INTENTS:
        return ResponseModeDecision(SMALL_TALK, "Conversation intent is small talk.")

    if reply_kind == GENERATE_OUTPUT:
        return ResponseModeDecision(GENERATE_OUTPUT, "Caller selected output generation.")

    return ResponseModeDecision(NORMAL_CHAT, "Default conversational response.")
