from collections import Counter


def summarize_feedback(records: list[dict]) -> dict:
    safe_records = list(records or [])
    by_category = Counter(record.get("category") or "general" for record in safe_records)
    by_priority = Counter(record.get("priority") or "low" for record in safe_records)
    recommended_focus = by_category.most_common(1)[0][0] if by_category else None

    return {
        "total_count": len(safe_records),
        "by_category": dict(by_category),
        "by_priority": dict(by_priority),
        "top_messages": [
            record.get("message", "")
            for record in safe_records[-10:]
            if record.get("message")
        ],
        "recommended_focus": recommended_focus,
    }
