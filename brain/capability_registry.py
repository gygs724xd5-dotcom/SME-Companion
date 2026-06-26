from __future__ import annotations

from copy import deepcopy


CAPABILITIES = {
    "sales_plan": {
        "name": "Sales Plan",
        "description": "Plan short-term sales actions using existing workflow inputs.",
        "available": True,
        "maturity": "workflow_ready",
        "required_modules": ["brain.workflow_state_machine", "brain.workflow_readiness"],
    },
    "content_plan": {
        "name": "Content Plan",
        "description": "Create content planning guidance from existing store and workflow context.",
        "available": True,
        "maturity": "workflow_ready",
        "required_modules": ["brain.workflow_state_machine", "content_engine"],
    },
    "cost_calculation": {
        "name": "Cost Calculation",
        "description": "Calculate cost and margin when required cost inputs are provided.",
        "available": True,
        "maturity": "workflow_ready",
        "required_modules": ["brain.workflow_state_machine", "brain.workflow_field_extractor"],
    },
    "dashboard_request": {
        "name": "Dashboard Request",
        "description": "Route dashboard requests to the current product feedback/dashboard placeholder flow.",
        "available": True,
        "maturity": "basic",
        "required_modules": ["app", "feedback.product_learning_engine"],
    },
    "receipt_upload": {
        "name": "Receipt Upload",
        "description": "Capture receipt files and preserve upload state without OCR extraction.",
        "available": True,
        "maturity": "capture_only",
        "required_modules": ["memory.receipt_state", "memory.receipt_storage"],
    },
    "conversation_memory": {
        "name": "Conversation Memory",
        "description": "Use current conversation state and recent chat history as planning context.",
        "available": True,
        "maturity": "available",
        "required_modules": ["memory.application_state", "memory.store_memory"],
    },
    "product_feedback": {
        "name": "Product Feedback",
        "description": "Classify and record product feedback for Developer Intelligence.",
        "available": True,
        "maturity": "available",
        "required_modules": ["feedback.product_classifier", "feedback.product_learning_engine"],
    },
    "developer_intelligence": {
        "name": "Developer Intelligence",
        "description": "Expose read-only developer diagnostics and product learning signals.",
        "available": True,
        "maturity": "available",
        "required_modules": ["feedback.developer_alert_engine", "feedback.sprint_recommendation_engine"],
    },
    "ocr": {
        "name": "OCR",
        "description": "Future receipt image text extraction engine.",
        "available": False,
        "maturity": "future",
        "required_modules": ["placeholder.ocr_engine"],
    },
    "inventory": {
        "name": "Inventory",
        "description": "Future stock and inventory operating engine.",
        "available": False,
        "maturity": "future",
        "required_modules": ["placeholder.inventory_engine"],
    },
    "pos_sync": {
        "name": "POS Sync",
        "description": "Future POS integration and transaction sync engine.",
        "available": False,
        "maturity": "future",
        "required_modules": ["placeholder.pos_sync_engine"],
    },
    "business_forecast": {
        "name": "Business Forecast",
        "description": "Future sales and business forecasting engine.",
        "available": False,
        "maturity": "future",
        "required_modules": ["placeholder.sales_forecast_engine"],
    },
}


ALIASES = {
    "sales": "sales_plan",
    "sales plan": "sales_plan",
    "sales_plan": "sales_plan",
    "content": "content_plan",
    "content plan": "content_plan",
    "content_plan": "content_plan",
    "cost": "cost_calculation",
    "cost calculation": "cost_calculation",
    "cost_calculation": "cost_calculation",
    "dashboard": "dashboard_request",
    "dashboard request": "dashboard_request",
    "dashboard_request": "dashboard_request",
    "receipt": "receipt_upload",
    "receipt upload": "receipt_upload",
    "receipt_upload": "receipt_upload",
    "conversation": "conversation_memory",
    "conversation memory": "conversation_memory",
    "conversation_memory": "conversation_memory",
    "product feedback": "product_feedback",
    "product_feedback": "product_feedback",
    "developer": "developer_intelligence",
    "developer intelligence": "developer_intelligence",
    "developer_intelligence": "developer_intelligence",
    "ocr": "ocr",
    "inventory": "inventory",
    "pos": "pos_sync",
    "pos sync": "pos_sync",
    "pos_sync": "pos_sync",
    "forecast": "business_forecast",
    "business forecast": "business_forecast",
    "business_forecast": "business_forecast",
}


def _normalize_capability_key(name: str | None) -> str | None:
    normalized = str(name or "").strip().lower().replace("-", " ").replace("_", " ")
    if not normalized:
        return None
    return ALIASES.get(normalized) or ALIASES.get(normalized.replace(" ", "_"))


def get_capability(name: str | None) -> dict | None:
    key = _normalize_capability_key(name)
    if not key or key not in CAPABILITIES:
        return None
    return deepcopy(CAPABILITIES[key])


def list_capabilities(include_future: bool = True) -> list[dict]:
    capabilities = []
    for capability in CAPABILITIES.values():
        if include_future or capability.get("available"):
            capabilities.append(deepcopy(capability))
    return capabilities


def is_capability_available(name: str | None) -> bool:
    capability = get_capability(name)
    return bool(capability and capability.get("available"))
