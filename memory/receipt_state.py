from __future__ import annotations

from datetime import datetime, timezone


RECEIPT_STATE_EMPTY = "EMPTY"
RECEIPT_STATE_UPLOADED = "UPLOADED"
RECEIPT_STATE_WAITING_OCR = "WAITING_OCR"
RECEIPT_STATE_OCR_COMPLETE = "OCR_COMPLETE"
RECEIPT_STATE_ANALYZED = "ANALYZED"


DEFAULT_RECEIPT_STATE = {
    "receipt_uploaded": False,
    "receipt_filename": None,
    "receipt_uploaded_time": None,
    "ocr_status": "empty",
    "analysis_status": "empty",
    "last_receipt_id": None,
    "state": RECEIPT_STATE_EMPTY,
}


def new_receipt_state() -> dict:
    return dict(DEFAULT_RECEIPT_STATE)


def ensure_receipt_state(receipt_state: dict | None = None) -> dict:
    state = dict(DEFAULT_RECEIPT_STATE)
    state.update(receipt_state or {})
    if state.get("analysis_status") == "analyzed":
        state["state"] = RECEIPT_STATE_ANALYZED
    elif state.get("ocr_status") == "complete":
        state["state"] = RECEIPT_STATE_OCR_COMPLETE
    elif state.get("ocr_status") == "waiting":
        state["state"] = RECEIPT_STATE_WAITING_OCR
    elif state.get("receipt_uploaded"):
        state["state"] = RECEIPT_STATE_UPLOADED
    else:
        state["state"] = RECEIPT_STATE_EMPTY
    return state


def mark_receipt_uploaded(metadata: dict | None, receipt_state: dict | None = None) -> dict:
    metadata = metadata or {}
    state = ensure_receipt_state(receipt_state)
    state.update(
        {
            "receipt_uploaded": True,
            "receipt_filename": metadata.get("original_filename") or metadata.get("filename"),
            "receipt_uploaded_time": metadata.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "ocr_status": "waiting",
            "analysis_status": "pending",
            "last_receipt_id": metadata.get("id"),
            "state": RECEIPT_STATE_WAITING_OCR,
        }
    )
    return state


def receipt_is_uploaded(receipt_state: dict | None) -> bool:
    return bool(ensure_receipt_state(receipt_state).get("receipt_uploaded"))

