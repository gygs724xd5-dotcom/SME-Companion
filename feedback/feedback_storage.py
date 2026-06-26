import json
from pathlib import Path


FEEDBACK_LOG_PATH = Path("data") / "feedback" / "feedback_log.jsonl"


def ensure_feedback_dir() -> None:
    FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def save_feedback(record: dict) -> None:
    ensure_feedback_dir()
    safe_record = {
        key: value
        for key, value in dict(record or {}).items()
        if "api_key" not in str(key).lower() and "secret" not in str(key).lower()
    }
    with FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(safe_record, ensure_ascii=False) + "\n")


def load_feedback(limit: int | None = None) -> list[dict]:
    if not FEEDBACK_LOG_PATH.exists():
        return []

    records = []
    with FEEDBACK_LOG_PATH.open("r", encoding="utf-8") as file:
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
