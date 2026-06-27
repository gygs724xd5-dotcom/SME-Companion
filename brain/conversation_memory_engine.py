from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone


RECENT_LIMIT = 6
SNIPPET_LIMIT = 220


def _snippet(value: str | None, limit: int = SNIPPET_LIMIT) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _active_workflow(application_state: dict | None) -> str | None:
    state = application_state or {}
    workflow = state.get("workflow") or {}
    workflow_state = workflow.get("workflow_state_v2") or {}
    return (
        workflow_state.get("workflow")
        or workflow.get("workflow")
        or workflow.get("current_workflow")
        or ((state.get("conversation") or {}).get("workflow_state_v2") or {}).get("workflow")
        or (state.get("conversation") or {}).get("current_workflow")
    )


def _latest_by_role(history: list[dict], role: str) -> str | None:
    for item in reversed(history or []):
        if item.get("role") == role:
            return _snippet(item.get("content"))
    return None


def _recent_by_role(history: list[dict], role: str, limit: int = RECENT_LIMIT) -> list[str]:
    values = []
    for item in reversed(history or []):
        if item.get("role") == role:
            text = _snippet(item.get("content"))
            if text:
                values.append(text)
        if len(values) >= limit:
            break
    return list(reversed(values))


def _reference_target(message: str | None) -> dict:
    text = str(message or "").strip().lower()
    if not text:
        return {}
    if any(term in text for term in ["อันบน", "ข้างบน", "อันแรก"]):
        return {"reference": "previous_assistant_reply", "position": "above"}
    if any(term in text for term in ["อันนี้", "ตัวนี้", "อันนั้น", "แบบเดิม", "อีกอัน"]):
        return {"reference": "latest_assistant_reply"}
    if any(term in text for term in ["ทำต่อ", "ต่อเลย", "ไปต่อ", "continue"]):
        return {"reference": "previous_workflow"}
    return {}


def _compact_from_state(application_state: dict | None) -> dict:
    state = application_state or {}
    conversation = state.get("conversation") or {}
    history = conversation.get("chat_history") or []
    workflow = _active_workflow(state)
    latest_user = _latest_by_role(history, "user")
    latest_assistant = _latest_by_role(history, "assistant")
    last_intent = (
        conversation.get("last_intent")
        or (conversation.get("understanding") or {}).get("detected_intent")
        or (state.get("conversation_understanding") or {}).get("detected_intent")
    )

    return {
        "recent_user_messages": _recent_by_role(history, "user"),
        "recent_assistant_replies": _recent_by_role(history, "assistant"),
        "last_user_message": latest_user,
        "last_assistant_reply": latest_assistant,
        "previous_intent": conversation.get("previous_intent"),
        "last_intent": last_intent,
        "previous_workflow": conversation.get("previous_workflow"),
        "last_workflow": workflow or conversation.get("current_workflow"),
        "focused_business_topic": conversation.get("current_topic") or conversation.get("focused_business_topic"),
        "last_reference": _reference_target(latest_user),
        "turn_count": len(history),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_last_context(application_state: dict | None = None) -> dict:
    """Return lightweight session memory without exposing full LLM history."""
    state = application_state or {}
    existing = deepcopy(
        state.get("conversation_memory")
        or ((state.get("conversation") or {}).get("conversation_memory"))
        or {}
    )
    compact = _compact_from_state(state)
    merged = {**existing, **{key: value for key, value in compact.items() if value not in (None, "", [], {})}}
    return merged


def remember_turn(
    memory: dict | None,
    user_message: str | None,
    assistant_reply: str | None = None,
    intent: str | None = None,
    workflow: str | None = None,
    business_topic: str | None = None,
) -> dict:
    """Update compact memory for one turn. Stores snippets and metadata only."""
    current = deepcopy(memory or {})
    user = _snippet(user_message)
    assistant = _snippet(assistant_reply)
    if user:
        users = list(current.get("recent_user_messages") or [])
        users.append(user)
        current["recent_user_messages"] = users[-RECENT_LIMIT:]
        current["last_user_message"] = user
        current["last_reference"] = _reference_target(user)
    if assistant:
        replies = list(current.get("recent_assistant_replies") or [])
        replies.append(assistant)
        current["recent_assistant_replies"] = replies[-RECENT_LIMIT:]
        current["last_assistant_reply"] = assistant
    if intent:
        current["previous_intent"] = current.get("last_intent")
        current["last_intent"] = intent
    if workflow:
        current["previous_workflow"] = current.get("last_workflow")
        current["last_workflow"] = workflow
    if business_topic:
        current["focused_business_topic"] = business_topic
    current["turn_count"] = int(current.get("turn_count") or 0) + 1
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {key: value for key, value in current.items() if value not in (None, "", [], {})}
