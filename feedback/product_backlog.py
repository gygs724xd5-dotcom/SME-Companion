import json
import re
from difflib import SequenceMatcher
from pathlib import Path


PRODUCT_BACKLOG_PATH = Path("product_backlog.json")
PRODUCT_FEEDBACK_LOG_PATH = Path("data") / "feedback" / "product_feedback_log.jsonl"

_STOPWORDS = {
    "หน้า",
    "เมนู",
    "ระบบ",
    "ใช้",
    "ใช้งาน",
    "มาก",
    "ครับ",
    "ค่ะ",
    "คับ",
    "ตรงนี้",
    "the",
    "a",
    "an",
    "is",
    "too",
}


def _normalize(message: str) -> str:
    normalized = str(message or "").strip().lower()
    normalized = re.sub(r"[^\w\sก-๙]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _tokenize(message: str) -> set[str]:
    return {token for token in _normalize(message).split() if token and token not in _STOPWORDS}


def _similarity(left: str, right: str) -> float:
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens or not right_tokens:
        return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()

    overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    sequence = SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()
    return max(overlap, sequence)


def _priority_rank(priority: str) -> int:
    return {"High": 3, "Medium": 2, "Low": 1}.get(priority, 0)


def _issue_title(record: dict) -> str:
    summary = str(record.get("summary") or record.get("raw_message") or "").strip()
    if not summary:
        return f"{record.get('category') or 'Other'} feedback"
    return summary[:80]


def load_product_backlog(path: Path = PRODUCT_BACKLOG_PATH) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("issues", [])
    return []


def save_product_backlog(issues: list[dict], path: Path = PRODUCT_BACKLOG_PATH) -> None:
    path.write_text(json.dumps(list(issues or []), ensure_ascii=False, indent=2), encoding="utf-8")


def append_product_feedback_log(record: dict, path: Path = PRODUCT_FEEDBACK_LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_product_feedback(limit: int | None = None, path: Path = PRODUCT_FEEDBACK_LOG_PATH) -> list[dict]:
    if not path.exists():
        return []

    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if limit is None:
        return records
    return records[-limit:]


def find_duplicate_issue(record: dict, issues: list[dict]) -> dict | None:
    message = record.get("raw_message") or record.get("summary") or ""
    category = record.get("category")

    best_issue = None
    best_score = 0.0
    for issue in issues:
        if issue.get("category") != category:
            continue
        candidate = issue.get("title") or issue.get("latest_example") or ""
        score = _similarity(message, candidate)
        if score > best_score:
            best_issue = issue
            best_score = score

    return best_issue if best_score >= 0.5 else None


def upsert_product_backlog_issue(record: dict, path: Path = PRODUCT_BACKLOG_PATH) -> dict:
    issues = load_product_backlog(path)
    issue = find_duplicate_issue(record, issues)

    if issue is None:
        issue = {
            "title": _issue_title(record),
            "category": record.get("category") or "Other",
            "priority": record.get("priority") or "Low",
            "count": 1,
            "latest_example": record.get("raw_message") or "",
            "first_seen": record.get("timestamp"),
            "last_seen": record.get("timestamp"),
            "status": "open",
        }
        issues.append(issue)
    else:
        issue["count"] = int(issue.get("count") or 0) + 1
        issue["latest_example"] = record.get("raw_message") or issue.get("latest_example") or ""
        issue["last_seen"] = record.get("timestamp") or issue.get("last_seen")
        if _priority_rank(record.get("priority")) > _priority_rank(issue.get("priority")):
            issue["priority"] = record.get("priority")
        issue["status"] = issue.get("status") or "open"

    save_product_backlog(issues, path)
    return issue
