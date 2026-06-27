from __future__ import annotations

from difflib import SequenceMatcher
import re

from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)


GENERIC_FALLBACK_MARKERS = (
    "\u0e40\u0e25\u0e48\u0e32\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e2d\u0e35\u0e01\u0e19\u0e34\u0e14",
    "\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23\u0e43\u0e2b\u0e49\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e2d\u0e30\u0e44\u0e23",
)

FIELD_QUESTIONS = {
    "product": "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e19\u0e35\u0e49\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e15\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32\u0e2d\u0e30\u0e44\u0e23\u0e04\u0e23\u0e31\u0e1a",
    "product_or_business_type": "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e19\u0e35\u0e49\u0e08\u0e30\u0e42\u0e1f\u0e01\u0e31\u0e2a\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32\u0e2b\u0e23\u0e37\u0e2d\u0e1b\u0e23\u0e30\u0e40\u0e20\u0e17\u0e23\u0e49\u0e32\u0e19\u0e2d\u0e30\u0e44\u0e23\u0e04\u0e23\u0e31\u0e1a",
    "daily_capacity_or_available_quantity": "\u0e27\u0e31\u0e19\u0e25\u0e30\u0e02\u0e32\u0e22\u0e44\u0e14\u0e49\u0e1b\u0e23\u0e30\u0e21\u0e32\u0e13\u0e01\u0e35\u0e48\u0e0a\u0e34\u0e49\u0e19\u0e04\u0e23\u0e31\u0e1a",
    "selling_window_or_sales_channel": "\u0e02\u0e32\u0e22\u0e0a\u0e48\u0e27\u0e07\u0e40\u0e27\u0e25\u0e32\u0e44\u0e2b\u0e19 \u0e2b\u0e23\u0e37\u0e2d\u0e02\u0e32\u0e22\u0e17\u0e32\u0e07\u0e0a\u0e48\u0e2d\u0e07\u0e17\u0e32\u0e07\u0e44\u0e2b\u0e19\u0e04\u0e23\u0e31\u0e1a",
    "ingredients_costs": "\u0e21\u0e35\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e2b\u0e23\u0e37\u0e2d\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a\u0e2d\u0e30\u0e44\u0e23\u0e1a\u0e49\u0e32\u0e07\u0e04\u0e23\u0e31\u0e1a",
    "total_units": "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e0a\u0e38\u0e14\u0e19\u0e35\u0e49\u0e17\u0e33\u0e44\u0e14\u0e49\u0e01\u0e35\u0e48\u0e0a\u0e34\u0e49\u0e19\u0e04\u0e23\u0e31\u0e1a",
}

WORKFLOW_TOPICS = {
    WORKFLOW_CONTENT_PLAN: "\u0e41\u0e1c\u0e19\u0e04\u0e2d\u0e19\u0e40\u0e17\u0e19\u0e15\u0e4c",
    WORKFLOW_SALES_PLAN_7_DAY: "\u0e41\u0e1c\u0e19\u0e02\u0e32\u0e22",
    WORKFLOW_COST_CALCULATION: "\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
    WORKFLOW_DASHBOARD_REQUEST: "\u0e41\u0e14\u0e0a\u0e1a\u0e2d\u0e23\u0e4c\u0e14\u0e23\u0e49\u0e32\u0e19",
    WORKFLOW_RECEIPT_CAPTURE: "\u0e1a\u0e34\u0e25 / \u0e2a\u0e25\u0e34\u0e1b",
}


def is_generic_fallback(reply: str | None) -> bool:
    text = str(reply or "").strip()
    if not text:
        return True
    return any(marker in text for marker in GENERIC_FALLBACK_MARKERS)


def is_repetitive_reply(reply: str | None, chat_history: list[dict] | None) -> bool:
    text = str(reply or "").strip()
    if not text:
        return False
    for message in reversed(chat_history or []):
        if message.get("role") == "assistant" and message.get("content"):
            previous = str(message.get("content") or "").strip()
            return SequenceMatcher(None, previous, text).ratio() >= 0.92
    return False


def _first_missing_question(missing: list[str]) -> str:
    for field in missing or []:
        if field in FIELD_QUESTIONS:
            return FIELD_QUESTIONS[field]
    return "\u0e02\u0e2d\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e2d\u0e35\u0e01 1 \u0e08\u0e38\u0e14\u0e04\u0e23\u0e31\u0e1a"


def _business_context_reply(business_context: dict) -> str | None:
    business_type = (business_context or {}).get("business_type")
    if not business_type:
        return None
    label = str(business_type).replace("_", " ")
    return (
        "\u0e23\u0e31\u0e1a\u0e17\u0e23\u0e32\u0e1a\u0e04\u0e23\u0e31\u0e1a "
        f"\u0e1c\u0e21\u0e08\u0e33\u0e44\u0e27\u0e49\u0e27\u0e48\u0e32\u0e23\u0e49\u0e32\u0e19\u0e19\u0e35\u0e49\u0e40\u0e1b\u0e47\u0e19 {label}\n\n"
        "\u0e16\u0e49\u0e32\u0e08\u0e30\u0e43\u0e2b\u0e49\u0e1c\u0e21\u0e0a\u0e48\u0e27\u0e22\u0e17\u0e33\u0e42\u0e1e\u0e2a\u0e15\u0e4c "
        "\u0e02\u0e2d\u0e0a\u0e37\u0e48\u0e2d\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32\u0e17\u0e35\u0e48\u0e08\u0e30\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e15\u0e01\u0e48\u0e2d\u0e19\u0e04\u0e23\u0e31\u0e1a"
    )


def select_planner_first_response(route: dict | None, chat_history: list[dict] | None = None) -> dict:
    route = route or {}
    plan = route.get("planner_output") or {}
    intent = route.get("intent_resolution") or plan.get("intent_resolution") or {}
    business_context = route.get("business_context") or plan.get("business_context") or {}
    workflow = plan.get("workflow") or intent.get("resolved_workflow")
    confidence = intent.get("confidence") or ((route.get("conversation_understanding") or {}).get("confidence"))
    missing = list(plan.get("missing_information") or [])

    if intent.get("resolved_intent") == "business_context_update":
        reply = _business_context_reply(business_context)
        if reply:
            return {"handled": True, "reply": reply, "intent": "BUSINESS_CONTEXT_UPDATE", "topic": business_context.get("business_type")}

    current_goal = str(plan.get("goal") or "")
    has_numeric_fields = bool(re.search(r"\d", current_goal))
    if workflow and plan.get("next_step") == "collect_missing_information" and (
        workflow == WORKFLOW_CONTENT_PLAN or not has_numeric_fields
    ):
        return {
            "handled": True,
            "reply": _first_missing_question(missing),
            "intent": workflow,
            "topic": WORKFLOW_TOPICS.get(workflow),
        }

    if confidence == "HIGH" and plan.get("task_type") == "Content Plan" and not missing:
        return {
            "handled": True,
            "reply": "\u0e44\u0e14\u0e49\u0e04\u0e23\u0e31\u0e1a \u0e1c\u0e21\u0e08\u0e30\u0e0a\u0e48\u0e27\u0e22\u0e27\u0e32\u0e07\u0e42\u0e04\u0e23\u0e07\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e43\u0e2b\u0e49 \u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e19\u0e35\u0e49\u0e08\u0e30\u0e42\u0e1f\u0e01\u0e31\u0e2a\u0e02\u0e32\u0e22\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32\u0e15\u0e31\u0e27\u0e44\u0e2b\u0e19\u0e04\u0e23\u0e31\u0e1a",
            "intent": WORKFLOW_CONTENT_PLAN,
            "topic": WORKFLOW_TOPICS.get(WORKFLOW_CONTENT_PLAN),
        }

    return {"handled": False}


def guard_response(reply: str | None, route: dict | None, chat_history: list[dict] | None = None) -> dict:
    if not is_generic_fallback(reply) and not is_repetitive_reply(reply, chat_history):
        return {"changed": False, "reply": reply}
    selected = select_planner_first_response(route, chat_history)
    if selected.get("handled"):
        return {**selected, "changed": True}
    plan = (route or {}).get("planner_output") or {}
    workflow = plan.get("workflow") or ((route or {}).get("intent_resolution") or {}).get("resolved_workflow")
    missing = list(plan.get("missing_information") or [])
    if workflow and missing:
        return {
            "changed": True,
            "reply": _first_missing_question(missing),
            "intent": workflow,
            "topic": WORKFLOW_TOPICS.get(workflow),
        }
    return {"changed": False, "reply": reply}
