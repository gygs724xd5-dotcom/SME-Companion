from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from feedback.developer_alert_engine import detect_conversation_failures
from feedback.product_backlog import load_product_backlog, load_product_feedback


def _parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _within(timestamp: str, days: int) -> bool:
    parsed = _parse_time(timestamp)
    if not parsed:
        return False
    return parsed >= datetime.now(timezone.utc) - timedelta(days=days)


def _category_counts(records: list[dict], days: int | None = None) -> dict:
    selected = records
    if days is not None:
        selected = [record for record in records if _within(record.get("timestamp") or record.get("last_seen") or "", days)]
    return dict(Counter(record.get("category") or "Other" for record in selected))


def _issue_frequency(records: list[dict]) -> dict:
    counter = Counter()
    for record in records:
        key = record.get("summary") or record.get("raw_message") or record.get("title") or "Unknown"
        counter[str(key)[:120]] += int(record.get("count") or 1)
    return dict(counter.most_common(20))


def _growth(current: int, previous: int) -> float:
    if previous <= 0:
        return float(current) if current else 0.0
    return round(((current - previous) / previous) * 100, 1)


def generate_trends(chat_history: list[dict] | None = None) -> dict:
    feedback = load_product_feedback()
    backlog = load_product_backlog()
    failures = detect_conversation_failures(chat_history)

    seven_day = _category_counts(feedback, 7)
    thirty_day = _category_counts(feedback, 30)
    previous_7_records = [
        record
        for record in feedback
        if _within(record.get("timestamp") or "", 14) and not _within(record.get("timestamp") or "", 7)
    ]
    previous_7 = _category_counts(previous_7_records)

    category_growth = {}
    for category in set(seven_day) | set(previous_7):
        category_growth[category] = {
            "current_7_day": seven_day.get(category, 0),
            "previous_7_day": previous_7.get(category, 0),
            "growth_pct": _growth(seven_day.get(category, 0), previous_7.get(category, 0)),
        }

    issue_counter = Counter()
    for issue in backlog:
        issue_counter[issue.get("title") or "Untitled"] += int(issue.get("count") or 0)
    for failure in failures:
        issue_counter[failure.get("issue") or "Conversation Failure"] += 1

    feature_requests = [
        issue
        for issue in backlog
        if issue.get("category") in {"Feature Request", "Export", "Notification", "POS Integration"}
    ]
    ux_issues = [
        issue
        for issue in backlog
        if issue.get("category") in {"UX", "UI", "Dashboard", "Workflow", "AI Response"}
    ]

    return {
        "top_growing_issues": [
            {"issue": issue, "count": count}
            for issue, count in issue_counter.most_common(10)
        ],
        "seven_day_trend": seven_day,
        "thirty_day_trend": thirty_day,
        "issue_frequency": _issue_frequency(feedback + backlog),
        "category_growth": dict(sorted(category_growth.items(), key=lambda item: item[1]["growth_pct"], reverse=True)),
        "most_repeated_ai_problems": dict(Counter(failure.get("issue") for failure in failures).most_common(10)),
        "most_repeated_feature_requests": [
            issue for issue in sorted(feature_requests, key=lambda item: int(item.get("count") or 0), reverse=True)[:10]
        ],
        "most_repeated_ux_issues": [
            issue for issue in sorted(ux_issues, key=lambda item: int(item.get("count") or 0), reverse=True)[:10]
        ],
    }
