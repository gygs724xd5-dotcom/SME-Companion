from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from brain.conversation_memory_engine import _snippet, remember_turn


def commit_response_boundary(
    *,
    session_state: dict,
    application_state: dict,
    final_reply: str,
    intent: str | None = None,
    workflow: str | None = None,
    business_topic: str | None = None,
    response_metadata: dict | None = None,
    assistant_message: dict | None = None,
) -> dict:
    """Commit the rendered assistant reply to history and compact memory together."""
    metadata = dict(response_metadata or {})
    reply = str(final_reply or "").strip()
    message = dict(assistant_message or {})
    message.setdefault("role", "assistant")
    message["content"] = reply

    history = session_state.setdefault("chat_history", [])
    history.append(message)

    conversation_state = session_state.setdefault("conversation_state", {})
    conversation = dict((application_state or {}).get("conversation") or {})
    current_memory = deepcopy(
        conversation.get("conversation_memory")
        or application_state.get("conversation_memory")
        or conversation_state.get("conversation_memory")
        or {}
    )
    user_message = metadata.get("user_message") or session_state.get("last_user_message")
    staged_user_turn = bool(user_message and current_memory.get("last_user_message") == _snippet(user_message))

    if staged_user_turn:
        updated_memory = remember_turn(current_memory, None, assistant_reply=reply)
        if current_memory.get("turn_count") is not None:
            updated_memory["turn_count"] = current_memory.get("turn_count")
        if intent and not updated_memory.get("last_intent"):
            updated_memory["last_intent"] = intent
        if workflow and not updated_memory.get("last_workflow"):
            updated_memory["last_workflow"] = workflow
        if business_topic and not updated_memory.get("focused_business_topic"):
            updated_memory["focused_business_topic"] = business_topic
    else:
        updated_memory = remember_turn(
            current_memory,
            user_message,
            assistant_reply=reply,
            intent=intent,
            workflow=workflow,
            business_topic=business_topic,
        )

    updated_memory["last_assistant_reply"] = _snippet(reply)
    replies = list(updated_memory.get("recent_assistant_replies") or [])
    if updated_memory["last_assistant_reply"] and (not replies or replies[-1] != updated_memory["last_assistant_reply"]):
        replies.append(updated_memory["last_assistant_reply"])
    updated_memory["recent_assistant_replies"] = replies[-6:]
    updated_memory["updated_at"] = datetime.now(timezone.utc).isoformat()

    conversation_state["conversation_memory"] = updated_memory
    conversation["conversation_memory"] = updated_memory
    conversation["chat_history"] = [dict(item) for item in history]
    conversation["conversation_id"] = session_state.get("conversation_id")
    application_state["conversation"] = conversation
    application_state["conversation_memory"] = updated_memory

    return {
        "assistant_message": message,
        "chat_history": conversation["chat_history"],
        "conversation_memory": updated_memory,
        "application_state": application_state,
    }
