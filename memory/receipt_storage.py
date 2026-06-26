from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


RECEIPT_DIR = Path("data") / "receipts"
RECEIPT_INDEX_PATH = RECEIPT_DIR / "receipt_index.jsonl"


def ensure_receipt_dir() -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    return RECEIPT_DIR


def _safe_filename(filename: str) -> str:
    cleaned = Path(str(filename or "receipt")).name
    safe = "".join(char if char.isalnum() or char in {".", "-", "_"} else "_" for char in cleaned)
    return safe or "receipt"


def save_uploaded_receipt(uploaded_file, store_name=None) -> dict:
    receipt_dir = ensure_receipt_dir()
    receipt_id = str(uuid4())
    original_filename = _safe_filename(getattr(uploaded_file, "name", "receipt"))
    suffix = Path(original_filename).suffix.lower()
    saved_name = f"{receipt_id}{suffix}" if suffix else receipt_id
    saved_path = receipt_dir / saved_name

    data = uploaded_file.getbuffer()
    saved_path.write_bytes(bytes(data))

    timestamp = datetime.now(timezone.utc).isoformat()
    metadata = {
        "id": receipt_id,
        "timestamp": timestamp,
        "store_name": store_name,
        "original_filename": original_filename,
        "saved_path": str(saved_path),
        "file_type": suffix.lstrip(".") or getattr(uploaded_file, "type", None),
        "status": "uploaded",
        "extracted_text": None,
        "parsed_total": None,
        "parsed_date": None,
    }

    with RECEIPT_INDEX_PATH.open("a", encoding="utf-8") as index_file:
        index_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")

    return metadata


def list_receipts(limit=20) -> list[dict]:
    ensure_receipt_dir()
    if not RECEIPT_INDEX_PATH.exists():
        return []

    records = []
    with RECEIPT_INDEX_PATH.open("r", encoding="utf-8") as index_file:
        for line in index_file:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return list(reversed(records))[:limit]
