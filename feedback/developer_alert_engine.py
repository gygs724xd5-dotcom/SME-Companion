from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from brain.conversation_workflow_engine import detect_workflow
from feedback.product_backlog import load_product_backlog, load_product_feedback


BUSINESS_MEMORY_PATH = Path("data") / "business_memory.json"
RECEIPT_INDEX_PATH = Path("data") / "receipts" / "receipt_index.jsonl"

FRUSTRATION_MARKERS = [
    "ไม่ใช่",
    "ยังไม่ตรง",
    "งง",
    "ไม่เข้าใจ",
    "พูดใหม่",
    "ไม่เอา",
    "ไม่ถูก",
]

LONG_REPLY_WORD_LIMIT = 180


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _alert_id(category: str, title: str, evidence: list[str]) -> str:
    seed = "|".join([category, title, *evidence[:3]])
    return str(uuid5(NAMESPACE_URL, seed))


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _contains_any(text: str, keywords: list[str]) -> bool:
    normalized = _normalize(text)
    return any(keyword in normalized for keyword in keywords)


def _similar(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def _priority(count: int, severe: bool = False) -> str:
    if severe or count >= 3:
        return "High"
    if count >= 1:
        return "Medium"
    return "Low"


def _severity(count: int, severe: bool = False) -> str:
    if severe or count >= 3:
        return "High"
    if count >= 1:
        return "Medium"
    return "Low"


def _build_alert(
    category: str,
    title: str,
    description: str,
    evidence: list[str],
    conversation_examples: list[dict] | None = None,
    recommended_action: str = "Review the related workflow and add focused regression coverage.",
    status: str = "open",
    severe: bool = False,
) -> dict:
    count = len(evidence)
    return {
        "id": _alert_id(category, title, evidence),
        "timestamp": _now(),
        "category": category,
        "priority": _priority(count, severe),
        "severity": _severity(count, severe),
        "count": count,
        "title": title,
        "description": description,
        "evidence": evidence[:10],
        "conversation_examples": (conversation_examples or [])[:5],
        "recommended_action": recommended_action,
        "status": status,
    }


def _conversation_turns(chat_history: list[dict] | None) -> list[dict]:
    turns = []
    messages = list(chat_history or [])
    for index, message in enumerate(messages):
        if message.get("role") != "user":
            continue
        assistant = None
        for candidate in messages[index + 1 :]:
            if candidate.get("role") == "assistant":
                assistant = candidate
                break
            if candidate.get("role") == "user":
                break
        next_user = None
        for candidate in messages[index + 1 :]:
            if candidate.get("role") == "user":
                next_user = candidate
                break
        turns.append(
            {
                "index": index,
                "user": str(message.get("content") or ""),
                "assistant": str((assistant or {}).get("content") or ""),
                "next_user": str((next_user or {}).get("content") or ""),
            }
        )
    return turns


def detect_conversation_failures(chat_history: list[dict] | None) -> list[dict]:
    failures = []
    previous_assistant = ""
    previous_question = ""

    for turn in _conversation_turns(chat_history):
        user = turn["user"]
        assistant = turn["assistant"]
        next_user = turn["next_user"]
        workflow = detect_workflow(user).get("workflow")
        evidence = []
        issue = None

        if workflow and assistant:
            workflow_terms = {
                "WORKFLOW_COST_CALCULATION": ["ต้นทุน", "วัตถุดิบ", "ราคา", "ชิ้น", "margin", "กำไร"],
                "WORKFLOW_DASHBOARD_REQUEST": ["dashboard", "แดชบอร์ด", "ภาพรวม", "กราฟ"],
                "WORKFLOW_RECEIPT_CAPTURE": ["บิล", "สลิป", "ใบเสร็จ", "อัปโหลด", "ไฟล์"],
            }.get(workflow, [])
            if workflow_terms and not _contains_any(assistant, workflow_terms):
                issue = "AI ignored active workflow"
                evidence.append(f"User workflow={workflow}: {user}")
                evidence.append(f"Assistant: {assistant[:220]}")

        if _contains_any(user, ["ต้นทุน", "คำนวณ"]) and _contains_any(assistant, ["โปรโมชัน", "โพสต์", "แคปชัน"]):
            issue = "AI switched topic unexpectedly"
            evidence.append(f"User asked for cost calculation: {user}")
            evidence.append(f"Assistant moved to marketing/content: {assistant[:220]}")

        if previous_assistant and assistant and _similar(previous_assistant, assistant) > 0.9:
            issue = "AI repeated previous answer"
            evidence.append(f"Repeated assistant answer: {assistant[:220]}")

        question = _last_question(assistant)
        if question and previous_question and _similar(question, previous_question) > 0.9:
            issue = "AI asked the same question twice"
            evidence.append(f"Repeated question: {question}")

        if _contains_any(user, ["ต้นทุน", "บิล", "สลิป", "dashboard", "แดชบอร์ด"]) and _contains_any(
            assistant,
            ["ควรโพสต์", "ทำโปร", "เพิ่มยอดขาย", "ลูกค้าเก่า"],
        ):
            issue = issue or "AI answered with unrelated business advice"
            evidence.append(f"Potentially unrelated answer: {assistant[:220]}")

        if workflow and next_user and detect_workflow(next_user).get("workflow") not in {workflow, None}:
            issue = issue or "Workflow abandoned"
            evidence.append(f"Workflow {workflow} followed by new topic: {next_user}")

        if workflow and assistant and not _last_question(assistant) and len(user.split()) <= 8:
            issue = issue or "Missing clarification"
            evidence.append(f"Short workflow request without clarification: {user}")

        if len(assistant.split()) > LONG_REPLY_WORD_LIMIT:
            issue = issue or "Long unnecessary reply"
            evidence.append(f"Long reply words={len(assistant.split())}: {assistant[:220]}")

        if _looks_like_template_repetition(assistant):
            issue = issue or "Reply template repetition"
            evidence.append(f"Template-like repetition: {assistant[:220]}")

        if issue:
            failures.append(
                {
                    "issue": issue,
                    "user": user,
                    "assistant": assistant,
                    "reaction": next_user,
                    "evidence": evidence or [user],
                    "suggested_fix": _suggested_fix(issue, workflow),
                }
            )

        if assistant:
            previous_assistant = assistant
            previous_question = question or previous_question

    return failures


def detect_silent_signals(chat_history: list[dict] | None) -> list[dict]:
    signals = []
    turns = _conversation_turns(chat_history)
    frustration_count = 0

    for turn in turns:
        user = turn["user"]
        assistant = turn["assistant"]
        next_user = turn["next_user"]
        signal = None
        evidence = []

        if _contains_any(user, FRUSTRATION_MARKERS):
            frustration_count += 1
            signal = "Possible confusion"
            evidence.append(f"Frustration marker: {user}")

        if assistant and _last_question(assistant) and not next_user:
            signal = signal or "Possible abandonment"
            evidence.append(f"Assistant asked a question and conversation stopped: {_last_question(assistant)}")

        if assistant and len(assistant.split()) > LONG_REPLY_WORD_LIMIT and not next_user:
            signal = signal or "Possible UX problem"
            evidence.append(f"Long final assistant reply words={len(assistant.split())}")

        if assistant and next_user:
            current_workflow = detect_workflow(user).get("workflow")
            next_workflow = detect_workflow(next_user).get("workflow")
            if current_workflow and next_workflow and current_workflow != next_workflow:
                signal = signal or "Possible workflow failure"
                evidence.append(f"User changed topic immediately from {current_workflow} to {next_workflow}")

        if signal:
            signals.append(
                {
                    "issue": signal,
                    "user": user,
                    "assistant": assistant,
                    "reaction": next_user,
                    "evidence": evidence,
                    "suggested_fix": "Review the turn for clarity, brevity, and workflow continuity.",
                }
            )

    if frustration_count >= 2:
        signals.append(
            {
                "issue": "Possible confusion",
                "user": "Multiple frustration markers in the same conversation",
                "assistant": "",
                "reaction": "",
                "evidence": [f"Frustration markers count={frustration_count}"],
                "suggested_fix": "Add recovery handling for repeated correction/frustration messages.",
            }
        )

    return signals


def _last_question(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for line in reversed(lines):
        if line.endswith("?") or "ไหม" in line or "หรือ" in line:
            return line
    return ""


def _looks_like_template_repetition(text: str) -> bool:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if len(lines) < 4:
        return False
    counts = Counter(lines)
    return any(count >= 2 and len(line) > 12 for line, count in counts.items())


def _suggested_fix(issue: str, workflow: str | None) -> str:
    if workflow:
        return f"Add a workflow guard and regression test for {workflow}: {issue}."
    if "repeated" in issue.lower():
        return "Add repetition checks before rendering assistant replies."
    if "long" in issue.lower():
        return "Constrain reply length for workflow and clarification turns."
    return "Review conversation state transitions and assistant reply generation."


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _load_business_events() -> list[dict]:
    if not BUSINESS_MEMORY_PATH.exists():
        return []
    try:
        data = json.loads(BUSINESS_MEMORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    events = []
    for store in (data.get("stores") or {}).values():
        for event in store.get("events") or []:
            events.append(event)
    return events


def _recent(records: list[dict], days: int, time_key: str = "timestamp") -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent_records = []
    for record in records:
        raw = str(record.get(time_key) or record.get("created_at") or "")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed >= cutoff:
            recent_records.append(record)
    return recent_records


def collect_developer_alerts(
    chat_history: list[dict] | None = None,
    conversation_id: str | None = None,
) -> list[dict]:
    del conversation_id
    alerts = []
    failures = detect_conversation_failures(chat_history)
    silent_signals = detect_silent_signals(chat_history)
    feedback = load_product_feedback()
    backlog = load_product_backlog()
    receipts = _load_jsonl(RECEIPT_INDEX_PATH)
    business_events = _load_business_events()

    if failures:
        alerts.append(
            _build_alert(
                "Conversation Failure",
                "Conversation Workflow Failure",
                "Conversation diagnostics found workflow drift, repetition, missing clarification, or unrelated advice.",
                [item for failure in failures for item in failure.get("evidence", [])],
                failures,
                "Inspect the affected workflow prompts/state and add regression tests for the failing turn pattern.",
                severe=len(failures) >= 3,
            )
        )

    if silent_signals:
        alerts.append(
            _build_alert(
                "Silent Signals",
                "Silent user frustration signals detected",
                "The user may be confused, abandoning the flow, or changing topic after an unsatisfying answer.",
                [item for signal in silent_signals for item in signal.get("evidence", [])],
                silent_signals,
                "Tighten clarification, recovery, and short-answer behavior in chat workflows.",
                severe=len(silent_signals) >= 3,
            )
        )

    high_feedback = [record for record in feedback if record.get("priority") == "High"]
    if high_feedback:
        alerts.append(
            _build_alert(
                "Product Feedback",
                "High priority product feedback",
                "Users submitted high priority product feedback.",
                [record.get("raw_message") or record.get("summary") or "" for record in high_feedback],
                recommended_action="Review high priority feedback and map it to backlog ownership.",
                severe=True,
            )
        )

    repeated_backlog = [issue for issue in backlog if int(issue.get("count") or 0) >= 3 and issue.get("status", "open") == "open"]
    if repeated_backlog:
        alerts.append(
            _build_alert(
                "Product Backlog",
                "Repeated backlog issues",
                "Open backlog items are receiving repeated evidence.",
                [f"{issue.get('title')} x{issue.get('count')}" for issue in repeated_backlog],
                recommended_action="Prioritize repeated open issues during sprint planning.",
                severe=any(int(issue.get("count") or 0) >= 5 for issue in repeated_backlog),
            )
        )

    receipt_requests = [
        record
        for record in feedback
        if _contains_any(record.get("raw_message") or record.get("summary") or "", ["บิล", "สลิป", "receipt", "ocr"])
    ]
    if len(receipt_requests) + len(receipts) >= 3:
        alerts.append(
            _build_alert(
                "Receipt Workflow",
                "Receipt workflow demand is rising",
                "Receipt uploads or OCR-related requests are recurring.",
                [*(record.get("raw_message") or "" for record in receipt_requests[:5]), f"receipt_uploads={len(receipts)}"],
                recommended_action="Evaluate OCR parsing and receipt summary work for the next sprint.",
            )
        )

    strategy_events = [event for event in business_events if event.get("event_type") in {"content_generated", "campaign_generated", "goal_update"}]
    if len(_recent(strategy_events, 7, "created_at")) >= 10:
        alerts.append(
            _build_alert(
                "Daily Strategy usage",
                "Daily strategy usage is active",
                "Strategy generation and goal updates are being used repeatedly.",
                [event.get("summary") or event.get("event_type") or "" for event in strategy_events[-10:]],
                recommended_action="Use recent strategy activity to validate dashboard and workflow priorities.",
            )
        )

    return sorted(alerts, key=lambda alert: (alert["priority"] == "High", alert["count"]), reverse=True)


def build_system_health(alerts: list[dict], chat_history: list[dict] | None = None) -> dict:
    failures = [alert for alert in alerts if alert.get("category") == "Conversation Failure"]
    silent = [alert for alert in alerts if alert.get("category") == "Silent Signals"]
    total_turns = len([message for message in (chat_history or []) if message.get("role") == "user"])
    failure_count = sum(int(alert.get("count") or 0) for alert in failures)
    silent_count = sum(int(alert.get("count") or 0) for alert in silent)
    return {
        "total_conversations": total_turns,
        "conversation_failures": failure_count,
        "silent_signals": silent_count,
        "conversation_failure_rate": round((failure_count / total_turns) * 100, 1) if total_turns else 0.0,
        "silent_signal_rate": round((silent_count / total_turns) * 100, 1) if total_turns else 0.0,
        "ai_success_rate": round(max(0.0, 100.0 - ((failure_count / total_turns) * 100)), 1) if total_turns else 100.0,
        "workflow_completion_rate": round(max(0.0, 100.0 - ((failure_count / max(total_turns, 1)) * 100)), 1),
    }


def build_smart_warnings(alerts: list[dict]) -> list[str]:
    warnings = []
    for alert in alerts:
        if alert.get("category") == "Conversation Failure" and alert.get("priority") == "High":
            warnings.append("⚠ AI conversation quality is degrading.")
        if alert.get("title") == "Receipt workflow demand is rising":
            warnings.append("⚠ Receipt feature requests are rising.")
        if alert.get("category") == "Product Backlog" and _contains_any(" ".join(alert.get("evidence") or []), ["dashboard", "แดชบอร์ด"]):
            warnings.append("⚠ Dashboard UX complaints increased.")
        if _contains_any(" ".join(alert.get("evidence") or []), ["ต้นทุน", "cost"]):
            warnings.append("⚠ Cost Calculation workflow failed multiple times.")
    return list(dict.fromkeys(warnings))
