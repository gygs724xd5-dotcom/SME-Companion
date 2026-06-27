from __future__ import annotations

from datetime import datetime, timezone


def new_inventory_document(document_type: str, source: str, metadata: dict | None = None) -> dict:
    return {
        "document_type": document_type,
        "source": source,
        "metadata": metadata or {},
        "ocr_status": "pending_external_ocr",
        "extracted_text": None,
        "line_items": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_stock_movement(product_id: str, quantity: float, movement_type: str, source_document_id: str | None = None) -> dict:
    return {
        "product_id": product_id,
        "quantity": quantity,
        "movement_type": movement_type,
        "source_document_id": source_document_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def summarize_inventory_foundation() -> dict:
    return {
        "ocr": "external_adapter_required",
        "entities": ["products", "inventory", "revenue", "expense", "stock_movement"],
        "source_of_truth": "inventory_ledger",
        "fake_ocr": False,
    }
