from collections import Counter, defaultdict
from datetime import datetime

from feedback.product_backlog import (
    append_product_feedback_log,
    load_product_backlog,
    load_product_feedback,
    save_product_backlog,
    upsert_product_backlog_issue,
)
from feedback.product_classifier import build_product_feedback_record
from feedback.product_priority import assign_priority


def record_product_feedback(message: str, conversation_id: str | None = None) -> dict:
    record = build_product_feedback_record(message, conversation_id=conversation_id)
    append_product_feedback_log(record)
    issue = upsert_product_backlog_issue(record)
    return {"record": record, "issue": issue}


def aggregate_feedback(records: list[dict] | None = None) -> dict:
    safe_records = list(records if records is not None else load_product_feedback())
    return {
        "total_count": len(safe_records),
        "by_category": dict(Counter(record.get("category") or "Other" for record in safe_records)),
        "by_priority": dict(Counter(record.get("priority") or "Low" for record in safe_records)),
        "by_severity": dict(Counter(record.get("severity") or "Low" for record in safe_records)),
    }


def update_priority(issues: list[dict] | None = None) -> list[dict]:
    backlog = list(issues if issues is not None else load_product_backlog())
    for issue in backlog:
        issue["priority"] = assign_priority(
            issue.get("latest_example") or issue.get("title") or "",
            issue.get("category") or "Other",
        )
    save_product_backlog(backlog)
    return backlog


def merge_duplicates(records: list[dict] | None = None) -> list[dict]:
    safe_records = list(records if records is not None else load_product_feedback())
    save_product_backlog([])
    for record in safe_records:
        upsert_product_backlog_issue(record)
    return load_product_backlog()


def calculate_trends(records: list[dict] | None = None) -> dict:
    safe_records = list(records if records is not None else load_product_feedback())
    daily_counts = defaultdict(int)

    for record in safe_records:
        timestamp = str(record.get("timestamp") or "")
        day = timestamp[:10] if timestamp else "unknown"
        daily_counts[day] += 1

    return {
        "daily_counts": dict(sorted(daily_counts.items())),
        "latest_day": max(daily_counts, default=None),
    }


def _top_issues(categories: set[str], limit: int = 5) -> list[dict]:
    issues = [
        issue
        for issue in load_product_backlog()
        if issue.get("status", "open") == "open" and issue.get("category") in categories
    ]
    return sorted(
        issues,
        key=lambda issue: (int(issue.get("count") or 0), issue.get("last_seen") or ""),
        reverse=True,
    )[:limit]


def prepare_dashboard_data() -> dict:
    records = load_product_feedback()
    backlog = load_product_backlog()
    latest_feedback = sorted(
        records,
        key=lambda record: record.get("timestamp") or "",
        reverse=True,
    )[:10]

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": {
            **aggregate_feedback(records),
            "backlog_open": len([issue for issue in backlog if issue.get("status", "open") == "open"]),
        },
        "top_requested_features": _top_issues({"Feature Request", "Export", "Notification", "POS Integration"}, 5),
        "top_bugs": _top_issues({"Bug", "Performance", "Data"}, 5),
        "top_ux_problems": _top_issues({"UX", "UI", "Dashboard", "Workflow", "AI Response"}, 5),
        "feedback_trend": calculate_trends(records),
        "latest_feedback": latest_feedback,
    }
