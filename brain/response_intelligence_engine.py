from __future__ import annotations

from difflib import SequenceMatcher
import re

from brain.business_context_engine import sanitize_user_context_text
from brain.task_router import workflow_response_gate
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)


RESPONSE_CANDIDATE_SOURCES = (
    "workflow_response",
    "reasoning_response",
    "deterministic_response",
    "direct_conversation_response",
    "llm_response",
    "legacy_response",
    "guard_response",
    "fallback_response",
)

SOURCE_ALIASES = {
    "planner_response": "deterministic_response",
    "planner_first_response": "deterministic_response",
    "response_guard": "guard_response",
    "generic_fallback": "fallback_response",
    "empty_response_fallback": "fallback_response",
}

SOURCE_PRIORITY = (
    "guard_response",
    "workflow_response",
    "reasoning_response",
    "direct_conversation_response",
    "llm_response",
    "deterministic_response",
    "legacy_response",
    "fallback_response",
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


def _preview(text: str | None, limit: int = 180) -> str | None:
    if text is None:
        return None
    compact = " ".join(str(text).strip().split())
    return compact[:limit]


def _canonical_source(source: str | None) -> str:
    raw = str(source or "").strip()
    if not raw:
        return "fallback_response"
    return SOURCE_ALIASES.get(raw, raw if raw in RESPONSE_CANDIDATE_SOURCES else raw)


def _candidate_text(candidate: dict | str | None) -> str | None:
    if isinstance(candidate, dict):
        value = candidate.get("text")
        if value is None:
            value = candidate.get("reply")
        if value is None:
            value = candidate.get("response")
        return None if value is None else str(value)
    if candidate is None:
        return None
    return str(candidate)


def _normalize_candidates(candidates) -> list[dict]:
    raw_candidates: list[dict] = []
    if isinstance(candidates, dict):
        for source, candidate in candidates.items():
            if isinstance(candidate, dict):
                raw_candidates.append({"source": source, **candidate})
            else:
                raw_candidates.append({"source": source, "text": candidate})
    else:
        for candidate in candidates or []:
            if isinstance(candidate, dict):
                raw_candidates.append(dict(candidate))

    by_source = {
        source: {
            "source": source,
            "available": False,
            "selected": False,
            "blocked": False,
            "blocked_reason": None,
            "text_preview": None,
        }
        for source in RESPONSE_CANDIDATE_SOURCES
    }
    for candidate in raw_candidates:
        source = _canonical_source(candidate.get("source"))
        if source not in by_source:
            by_source[source] = {
                "source": source,
                "available": False,
                "selected": False,
                "blocked": False,
                "blocked_reason": None,
                "text_preview": None,
            }
        text = _candidate_text(candidate)
        available = bool(candidate.get("available", text not in (None, "")))
        by_source[source].update(
            {
                "available": available,
                "blocked": bool(candidate.get("blocked", False)),
                "blocked_reason": candidate.get("blocked_reason"),
                "text_preview": _preview(text),
            }
        )
    return list(by_source.values())


def select_final_response(candidates, routing_context: dict | None = None, diagnostics: dict | None = None) -> dict:
    """Make the existing final response choice observable without changing text.

    The app may already have selected a reply before calling this helper. When
    diagnostics supplies that selected source/text, this function records it.
    Otherwise it deterministically picks the first available unblocked candidate
    by the current pipeline priority.
    """
    routing_context = routing_context or {}
    diagnostics = dict(diagnostics or {})
    normalized = _normalize_candidates(candidates)
    gate = workflow_response_gate(routing_context)
    before_gate = _canonical_source(
        diagnostics.get("response_source_before_gate")
        or diagnostics.get("selected_source")
        or diagnostics.get("response_source")
    )
    after_gate = _canonical_source(diagnostics.get("response_source_after_gate") or before_gate)
    final_text = diagnostics.get("final_response_text")
    selected_source = after_gate
    selected_by = diagnostics.get("selected_by") or "existing_response_pipeline"

    if final_text in (None, ""):
        for source in SOURCE_PRIORITY:
            candidate = next((item for item in normalized if item.get("source") == source), None)
            if candidate and candidate.get("available") and not candidate.get("blocked"):
                selected_source = source
                final_text = candidate.get("text_preview")
                selected_by = "select_final_response_priority"
                break

    if selected_source == "workflow_response" and not gate.get("workflow_response_allowed"):
        for candidate in normalized:
            if candidate.get("source") == "workflow_response":
                candidate["blocked"] = True
                candidate["blocked_reason"] = gate.get("workflow_response_blocked_reason")

    selected_candidate = next((item for item in normalized if item.get("source") == selected_source), None)
    if selected_candidate is None:
        selected_candidate = {
            "source": selected_source,
            "available": bool(final_text),
            "selected": False,
            "blocked": False,
            "blocked_reason": None,
            "text_preview": _preview(final_text),
        }
        normalized.append(selected_candidate)
    selected_candidate["available"] = bool(selected_candidate.get("available") or final_text)
    selected_candidate["selected"] = True
    if final_text and not selected_candidate.get("text_preview"):
        selected_candidate["text_preview"] = _preview(final_text)

    reply_builder = diagnostics.get("reply_builder") or "unknown"
    legacy_used = bool(
        selected_source == "legacy_response"
        or before_gate == "legacy_response"
        or "legacy" in str(reply_builder)
        or diagnostics.get("legacy_response_used")
    )
    legacy_reason = diagnostics.get("legacy_response_reason")
    if legacy_used and not legacy_reason:
        legacy_reason = "reply_builder" if "legacy" in str(reply_builder) else "selected_candidate"

    audit = {
        "final_response_origin": selected_source,
        "final_response_text_preview": _preview(final_text),
        "final_response_selector": "select_final_response",
        "final_response_selected_by": selected_by,
        "final_response_candidates": normalized,
        "response_builder": diagnostics.get("response_builder") or selected_source,
        "reply_builder": reply_builder,
        "response_source_before_gate": before_gate,
        "response_source_after_gate": after_gate,
        "response_gate_applied": bool(
            diagnostics.get("response_gate_applied")
            or before_gate != after_gate
            or gate.get("final_response_gate")
        ),
        "legacy_response_used": legacy_used,
        "legacy_response_reason": legacy_reason,
        "legacy_response_source_file": diagnostics.get("legacy_response_source_file"),
        "legacy_response_source_function": diagnostics.get("legacy_response_source_function"),
        "deterministic_response_used": selected_source == "deterministic_response",
        "llm_response_used": selected_source == "llm_response",
        "workflow_response_used": selected_source == "workflow_response",
        "reasoning_response_used": selected_source == "reasoning_response",
    }
    return {"selected_response": final_text, "selected_source": selected_source, "diagnostics": audit}


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


def _active_workflow_state_v2(route: dict) -> dict:
    workflow_context = (
        route.get("workflow")
        or (route.get("llm_reasoning_context") or {}).get("workflow")
        or {}
    )
    workflow_state = workflow_context.get("workflow_state_v2") or {}
    if not workflow_state and workflow_context.get("workflow") and workflow_context.get("step"):
        workflow_state = workflow_context
    if workflow_state.get("workflow") and workflow_state.get("step") != "completed":
        return workflow_state
    return {}


def _business_context_reply(business_context: dict) -> str | None:
    business_type = (business_context or {}).get("business_type")
    if not business_type:
        return None
    label = sanitize_user_context_text(business_type) or "\u0e1b\u0e23\u0e30\u0e40\u0e20\u0e17\u0e23\u0e49\u0e32\u0e19\u0e19\u0e35\u0e49"
    return (
        "\u0e23\u0e31\u0e1a\u0e17\u0e23\u0e32\u0e1a\u0e04\u0e23\u0e31\u0e1a "
        f"\u0e1c\u0e21\u0e08\u0e33\u0e44\u0e27\u0e49\u0e27\u0e48\u0e32\u0e23\u0e49\u0e32\u0e19\u0e19\u0e35\u0e49\u0e40\u0e1b\u0e47\u0e19 {label}\n\n"
        "\u0e16\u0e49\u0e32\u0e08\u0e30\u0e43\u0e2b\u0e49\u0e1c\u0e21\u0e0a\u0e48\u0e27\u0e22\u0e17\u0e33\u0e42\u0e1e\u0e2a\u0e15\u0e4c "
        "\u0e02\u0e2d\u0e0a\u0e37\u0e48\u0e2d\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32\u0e17\u0e35\u0e48\u0e08\u0e30\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e15\u0e01\u0e48\u0e2d\u0e19\u0e04\u0e23\u0e31\u0e1a"
    )


def select_planner_first_response(route: dict | None, chat_history: list[dict] | None = None) -> dict:
    route = route or {}
    gate = workflow_response_gate(route)
    active_workflow_state = _active_workflow_state_v2(route)
    if active_workflow_state:
        return {"handled": False}

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
    if workflow and not active_workflow_state and plan.get("next_step") == "collect_missing_information":
        return {"handled": False}

    if not workflow and plan.get("next_step") == "collect_missing_information" and missing:
        return {
            "handled": True,
            "reply": _first_missing_question(missing),
            "intent": plan.get("task_type"),
            "topic": plan.get("task_type"),
        }

    if workflow and gate.get("workflow_response_allowed") and plan.get("next_step") == "collect_missing_information" and (
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
    gate = workflow_response_gate(route)
    if workflow and missing and gate.get("workflow_response_allowed"):
        return {
            "changed": True,
            "reply": _first_missing_question(missing),
            "intent": workflow,
            "topic": WORKFLOW_TOPICS.get(workflow),
        }
    return {"changed": False, "reply": reply}
