from __future__ import annotations

from datetime import datetime, timezone

from brain.workflow_field_extractor import extract_workflow_fields
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_GENERAL_BUSINESS_HELP,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
    is_workflow_ready,
)


REQUIRED_FIELDS = {
    WORKFLOW_SALES_PLAN_7_DAY: ["product", "daily_capacity_or_available_quantity", "selling_window_or_sales_channel"],
    WORKFLOW_COST_CALCULATION: ["ingredients_costs", "total_units"],
    WORKFLOW_CONTENT_PLAN: ["product_or_business_type"],
    WORKFLOW_DASHBOARD_REQUEST: [],
    WORKFLOW_RECEIPT_CAPTURE: [],
    WORKFLOW_GENERAL_BUSINESS_HELP: [],
}

WORKFLOW_START_STEPS = {
    WORKFLOW_SALES_PLAN_7_DAY: "collecting_sales_plan_inputs",
    WORKFLOW_COST_CALCULATION: "collecting_cost_inputs",
    WORKFLOW_CONTENT_PLAN: "collecting_content_inputs",
    WORKFLOW_DASHBOARD_REQUEST: "route_to_product_brain",
    WORKFLOW_RECEIPT_CAPTURE: "waiting_for_upload",
    WORKFLOW_GENERAL_BUSINESS_HELP: "general_help",
}

_INTENT_TRIGGERS = {
    WORKFLOW_SALES_PLAN_7_DAY: [
        "แผนการขาย 7 วัน",
        "วางแผนขาย 7 วัน",
        "ทำแผนขาย",
        "วางแผนยอดขาย",
        "อยากขายให้ได้มากขึ้น",
        "แผนขายรายวัน",
    ],
    WORKFLOW_COST_CALCULATION: [
        "คำนวณต้นทุน",
        "ต้นทุนต่อชิ้น",
        "ต้นทุนขนม",
        "กำไรต่อชิ้น",
        "มาร์จิ้น",
        "margin",
    ],
    WORKFLOW_CONTENT_PLAN: ["แผนคอนเทนต์", "คิดคอนเทนต์", "โพสต์อะไรดี", "แคปชั่น"],
    WORKFLOW_DASHBOARD_REQUEST: ["แดชบอร์ด", "dashboard", "ภาพรวมร้าน", "กราฟร้าน"],
    WORKFLOW_RECEIPT_CAPTURE: ["บิล", "ใบเสร็จ", "สลิป", "receipt", "อัปโหลดบิล", "ถ่ายบิล"],
}


def new_workflow_state(workflow: str | None = None) -> dict:
    selected = workflow or WORKFLOW_GENERAL_BUSINESS_HELP
    return {
        "workflow": selected,
        "step": WORKFLOW_START_STEPS.get(selected, "new"),
        "required_fields": list(REQUIRED_FIELDS.get(selected, [])),
        "collected_fields": {},
        "missing_fields": list(REQUIRED_FIELDS.get(selected, [])),
        "is_ready": False,
        "next_action": "detect_workflow" if workflow is None else "collect_fields",
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def detect_workflow_intent(message: str, is_product_feedback: bool = False) -> str | None:
    if is_product_feedback:
        return None
    lowered = str(message or "").strip().lower()
    if not lowered:
        return None
    for workflow, triggers in _INTENT_TRIGGERS.items():
        if any(trigger.lower() in lowered for trigger in triggers):
            return workflow
    return None


def _merge_fields(existing: dict, new_fields: dict) -> dict:
    merged = dict(existing or {})
    for key, value in (new_fields or {}).items():
        if key == "ingredients_costs":
            previous = list(merged.get(key) or [])
            previous_names = {str(item.get("name", "")).strip().lower() for item in previous}
            for item in value or []:
                if str(item.get("name", "")).strip().lower() not in previous_names:
                    previous.append(item)
            merged[key] = previous
        elif value not in (None, "", []):
            merged[key] = value
    return merged


def _missing_fields(workflow: str, fields: dict) -> list[str]:
    if workflow == WORKFLOW_SALES_PLAN_7_DAY:
        missing = []
        if not fields.get("product"):
            missing.append("product")
        if not (fields.get("daily_capacity") or fields.get("available_quantity")):
            missing.append("daily_capacity_or_available_quantity")
        if not (fields.get("selling_window") or fields.get("sales_channel")):
            missing.append("selling_window_or_sales_channel")
        return missing
    if workflow == WORKFLOW_COST_CALCULATION:
        missing = []
        if not fields.get("ingredients_costs"):
            missing.append("ingredients_costs")
        if not fields.get("total_units"):
            missing.append("total_units")
        return missing
    if workflow == WORKFLOW_CONTENT_PLAN:
        return [] if fields.get("product") or fields.get("business_type") else ["product_or_business_type"]
    return []


def update_workflow_state(
    current_state: dict | None,
    user_message: str,
    detected_workflow: str | None = None,
) -> tuple[dict, dict]:
    current = current_state or {}
    workflow = detected_workflow or current.get("workflow") or WORKFLOW_GENERAL_BUSINESS_HELP
    if detected_workflow and detected_workflow != current.get("workflow"):
        current = new_workflow_state(detected_workflow)

    collected_fields = _merge_fields(
        current.get("collected_fields") or {},
        extract_workflow_fields(user_message, workflow=workflow),
    )
    state = {
        **new_workflow_state(workflow),
        **current,
        "workflow": workflow,
        "required_fields": list(REQUIRED_FIELDS.get(workflow, [])),
        "collected_fields": collected_fields,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    state["missing_fields"] = _missing_fields(workflow, collected_fields)
    state["is_ready"] = is_workflow_ready(state)
    if state["is_ready"]:
        state["step"] = "ready_to_generate"
        state["next_action"] = "generate"
    elif workflow in {WORKFLOW_DASHBOARD_REQUEST, WORKFLOW_RECEIPT_CAPTURE}:
        state["next_action"] = "route"
    else:
        state["step"] = WORKFLOW_START_STEPS.get(workflow, "collecting_fields")
        state["next_action"] = "ask_missing_field"
    return state, extract_workflow_fields(user_message, workflow=workflow)
