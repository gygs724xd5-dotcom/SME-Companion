from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from feedback.conversation_replay import build_problem_conversation_replay
from feedback.developer_alert_engine import build_system_health, collect_developer_alerts
from feedback.product_backlog import load_product_backlog, load_product_feedback
from feedback.sprint_recommendation_engine import recommend_next_sprint
from feedback.trend_engine import generate_trends


MARKDOWN_EXPORT_PATH = Path("data") / "exports" / "chatgpt_feedback_report.md"
JSON_EXPORT_PATH = Path("data") / "exports" / "product_report.json"


def _section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body.strip() or 'No data.'}\n"


def _bullets(items) -> str:
    lines = []
    for item in items or []:
        if isinstance(item, dict):
            label = item.get("title") or item.get("priority") or item.get("issue") or item.get("category") or "Item"
            count = item.get("count")
            suffix = f" x{count}" if count is not None else ""
            lines.append(f"- {label}{suffix}")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def build_product_report_data(chat_history: list[dict] | None = None) -> dict:
    feedback = load_product_feedback()
    backlog = load_product_backlog()
    alerts = collect_developer_alerts(chat_history)
    trends = generate_trends(chat_history)
    replay = build_problem_conversation_replay(chat_history, limit=20)
    recommendations = recommend_next_sprint(chat_history)
    user_turns = [message for message in (chat_history or []) if message.get("role") == "user"]
    assistant_turns = [message for message in (chat_history or []) if message.get("role") == "assistant"]
    health = build_system_health(alerts, chat_history)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "users": {"active_session_user_turns": len(user_turns)},
        "conversations": {"user_turns": len(user_turns), "assistant_turns": len(assistant_turns)},
        "feedback": {
            "total": len(feedback),
            "by_category": dict(Counter(record.get("category") or "Other" for record in feedback)),
            "by_priority": dict(Counter(record.get("priority") or "Low" for record in feedback)),
        },
        "conversation_failures": [alert for alert in alerts if alert.get("category") == "Conversation Failure"],
        "silent_signals": [alert for alert in alerts if alert.get("category") == "Silent Signals"],
        "top_ai_problems": trends.get("most_repeated_ai_problems", {}),
        "top_ux_problems": trends.get("most_repeated_ux_issues", []),
        "top_bugs": [issue for issue in backlog if issue.get("category") == "Bug"],
        "top_feature_requests": trends.get("most_repeated_feature_requests", []),
        "top_workflow_problems": [alert for alert in alerts if "Workflow" in str(alert.get("title"))],
        "latest_alerts": alerts[:10],
        "sprint_recommendation": recommendations,
        "latest_problem_conversations": replay,
        "health": health,
    }


def build_chatgpt_markdown_report(chat_history: list[dict] | None = None) -> str:
    data = build_product_report_data(chat_history)
    parts = [
        "========================",
        "SME Companion Weekly Report",
        "========================",
        f"\nGenerated At: {data['generated_at']}\n",
        _section("Users", json.dumps(data["users"], ensure_ascii=False, indent=2)),
        _section("Conversations", json.dumps(data["conversations"], ensure_ascii=False, indent=2)),
        _section("Feedback", json.dumps(data["feedback"], ensure_ascii=False, indent=2)),
        _section("Conversation Failures", _bullets(data["conversation_failures"])),
        _section("Silent Signals", _bullets(data["silent_signals"])),
        _section("Top AI Problems", json.dumps(data["top_ai_problems"], ensure_ascii=False, indent=2)),
        _section("Top UX Problems", _bullets(data["top_ux_problems"])),
        _section("Top Bugs", _bullets(data["top_bugs"])),
        _section("Top Feature Requests", _bullets(data["top_feature_requests"])),
        _section("Top Workflow Problems", _bullets(data["top_workflow_problems"])),
        _section("Latest Alerts", _bullets(data["latest_alerts"])),
        _section("Sprint Recommendation", json.dumps(data["sprint_recommendation"], ensure_ascii=False, indent=2)),
        _section("Latest Problem Conversations", json.dumps(data["latest_problem_conversations"], ensure_ascii=False, indent=2)),
        _section(
            "Questions For ChatGPT",
            "\n".join(
                [
                    "Please analyze this report.",
                    "",
                    "1. What are the root causes?",
                    "2. Which sprint should be prioritized?",
                    "3. Which modules should be refactored?",
                    "4. Suggest Codex implementation plan.",
                ]
            ),
        ),
    ]
    return "\n".join(parts).strip() + "\n"


def save_markdown_report(markdown: str, path: Path = MARKDOWN_EXPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def save_json_report(data: dict, path: Path = JSON_EXPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
