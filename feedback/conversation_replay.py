from __future__ import annotations

from feedback.developer_alert_engine import detect_conversation_failures, detect_silent_signals


def build_problem_conversation_replay(chat_history: list[dict] | None = None, limit: int = 20) -> list[dict]:
    problems = []
    for item in detect_conversation_failures(chat_history):
        problems.append(
            {
                "conversation": item.get("user") or "",
                "assistant": item.get("assistant") or "",
                "user_reaction": item.get("reaction") or "",
                "detected_issue": item.get("issue") or "Conversation Failure",
                "suggested_fix": item.get("suggested_fix") or "Review the conversation workflow.",
            }
        )
    for item in detect_silent_signals(chat_history):
        problems.append(
            {
                "conversation": item.get("user") or "",
                "assistant": item.get("assistant") or "",
                "user_reaction": item.get("reaction") or "",
                "detected_issue": item.get("issue") or "Silent Signal",
                "suggested_fix": item.get("suggested_fix") or "Review the user reaction.",
            }
        )
    return problems[-limit:]
