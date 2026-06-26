from __future__ import annotations

from collections import Counter

from feedback.developer_alert_engine import collect_developer_alerts
from feedback.product_backlog import load_product_backlog, load_product_feedback
from feedback.trend_engine import generate_trends


MODULE_MAP = {
    "Conversation Workflow": ["brain/conversation_workflow_engine.py", "app.py", "feedback/developer_alert_engine.py"],
    "Receipt OCR": ["memory/receipt_storage.py", "app.py"],
    "Dashboard Builder": ["app.py", "brain/business_os_engine.py"],
    "AI Response Quality": ["brain/chat_companion_engine.py", "brain/response_cleaner.py", "llm/llm_router.py"],
    "Product Brain": ["feedback/product_learning_engine.py", "feedback/product_backlog.py"],
    "UX Issues": ["app.py"],
}


def _impact(score: int) -> str:
    if score >= 15:
        return "Very High"
    if score >= 8:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def recommend_next_sprint(chat_history: list[dict] | None = None, limit: int = 5) -> list[dict]:
    alerts = collect_developer_alerts(chat_history)
    trends = generate_trends(chat_history)
    backlog = load_product_backlog()
    feedback = load_product_feedback()
    scores = Counter()
    evidence = {}

    for alert in alerts:
        if alert.get("category") == "Conversation Failure":
            scores["Conversation Workflow"] += int(alert.get("count") or 0) * 4
            evidence.setdefault("Conversation Workflow", []).append(f"{alert.get('count')} conversation failures")
        elif alert.get("category") == "Silent Signals":
            scores["AI Response Quality"] += int(alert.get("count") or 0) * 3
            evidence.setdefault("AI Response Quality", []).append(f"{alert.get('count')} silent signals")
        elif "Receipt" in str(alert.get("title")):
            scores["Receipt OCR"] += int(alert.get("count") or 0) * 3
            evidence.setdefault("Receipt OCR", []).append(str(alert.get("title")))
        elif alert.get("category") == "Product Backlog":
            scores["Product Brain"] += int(alert.get("count") or 0) * 2
            evidence.setdefault("Product Brain", []).extend(alert.get("evidence") or [])

    for issue in backlog:
        title = str(issue.get("title") or "")
        category = issue.get("category") or "Other"
        count = int(issue.get("count") or 0)
        if "receipt" in title.lower() or "บิล" in title or "สลิป" in title:
            scores["Receipt OCR"] += count * 2
            evidence.setdefault("Receipt OCR", []).append(f"{count} receipt requests")
        elif "dashboard" in title.lower() or "แดชบอร์ด" in title:
            scores["Dashboard Builder"] += count * 2
            evidence.setdefault("Dashboard Builder", []).append(f"{count} dashboard requests")
        elif category in {"UX", "UI", "Dashboard"}:
            scores["UX Issues"] += count
            evidence.setdefault("UX Issues", []).append(f"{count} {category} reports")
        elif category == "AI Response":
            scores["AI Response Quality"] += count * 2
            evidence.setdefault("AI Response Quality", []).append(f"{count} AI response reports")

    for record in feedback:
        text = str(record.get("raw_message") or record.get("summary") or "")
        if "บิล" in text or "สลิป" in text or "receipt" in text.lower():
            scores["Receipt OCR"] += 1
        if "dashboard" in text.lower() or "แดชบอร์ด" in text:
            scores["Dashboard Builder"] += 1

    for issue in trends.get("top_growing_issues", [])[:5]:
        name = issue.get("issue") or ""
        if "Conversation" in name or "workflow" in name.lower():
            scores["Conversation Workflow"] += int(issue.get("count") or 0)

    if not scores:
        scores["Product Brain"] = 1
        evidence["Product Brain"] = ["No major active alerts; continue improving developer intelligence."]

    recommendations = []
    for index, (area, score) in enumerate(scores.most_common(limit), start=1):
        recommendations.append(
            {
                "rank": index,
                "priority": area,
                "impact": _impact(score),
                "evidence": evidence.get(area, [])[:5] or [f"score={score}"],
                "expected_user_impact": "High" if score >= 8 else "Medium",
                "reason": f"{area} has the strongest combined signal score for this sprint.",
                "recommended_files_modules": MODULE_MAP.get(area, ["app.py"]),
            }
        )
    return recommendations
