from __future__ import annotations

from brain.conversation_intent_engine import detect_conversation_intent, is_product_feedback
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)
from brain.workflow_state_machine import REQUIRED_FIELDS, detect_workflow_intent


WORKFLOW_TO_TASK = {
    WORKFLOW_SALES_PLAN_7_DAY: ("Sales Plan", "sales_plan", "sales_planning"),
    WORKFLOW_COST_CALCULATION: ("Cost Calculation", "cost_calculation", "cost_calculation"),
    WORKFLOW_CONTENT_PLAN: ("Content Plan", "content_plan", "content_creation"),
    WORKFLOW_DASHBOARD_REQUEST: ("Dashboard Request", "dashboard_request", "dashboard_builder"),
    WORKFLOW_RECEIPT_CAPTURE: ("Receipt Upload", "receipt_upload", "receipt_capture"),
}


FUTURE_KEYWORDS = {
    "OCR": ["ocr", "read receipt", "scan receipt", "extract receipt"],
    "Inventory": ["inventory", "stock", "stock count"],
    "POS Sync": ["pos", "sync sales", "sync orders"],
    "Business Forecast": ["forecast", "projection", "predict sales"],
}

ENGLISH_TASK_KEYWORDS = {
    WORKFLOW_SALES_PLAN_7_DAY: ["sales plan", "7 day sales", "7-day sales", "sell more", "increase sales"],
    WORKFLOW_COST_CALCULATION: ["cost calculation", "calculate cost", "unit cost", "profit margin", "margin"],
    WORKFLOW_CONTENT_PLAN: ["content plan", "content ideas", "caption", "post ideas"],
    WORKFLOW_DASHBOARD_REQUEST: ["dashboard", "business dashboard", "store overview"],
    WORKFLOW_RECEIPT_CAPTURE: ["receipt upload", "upload receipt", "receipt", "slip"],
}


def _compact_dict(data: dict | None) -> dict:
    return {key: value for key, value in (data or {}).items() if value not in (None, "", [], {})}


def _missing_store_fields(store: dict | None) -> list[str]:
    profile = store or {}
    return [
        field
        for field in ["store_name", "store_type", "product", "target_customer"]
        if not profile.get(field)
    ]


def _known_information(application_state: dict, workflow: str | None) -> list[str]:
    known = []
    store = _compact_dict(application_state.get("store"))
    if store:
        known.append("store_profile")

    conversation = application_state.get("conversation") or {}
    if conversation.get("chat_history"):
        known.append("conversation_history")

    workflow_state = (application_state.get("workflow") or {}).get("workflow_state_v2") or {}
    if workflow_state.get("collected_fields"):
        known.append("workflow_collected_fields")

    receipt = application_state.get("receipt") or {}
    if receipt.get("receipt_uploaded"):
        known.append("receipt_uploaded")

    if workflow and workflow_state.get("workflow") == workflow and workflow_state.get("is_ready"):
        known.append("workflow_ready")

    return known


def _required_information(capability_key: str, workflow: str | None) -> list[str]:
    if workflow in REQUIRED_FIELDS:
        return list(REQUIRED_FIELDS.get(workflow) or [])
    if capability_key in {"conversation_memory", "product_feedback", "developer_intelligence"}:
        return ["user_message"]
    return []


def _missing_information(application_state: dict, capability_key: str, workflow: str | None) -> list[str]:
    workflow_state = (application_state.get("workflow") or {}).get("workflow_state_v2") or {}
    if workflow and workflow_state.get("workflow") == workflow:
        missing = list(workflow_state.get("missing_fields") or [])
        if missing:
            return missing

    if workflow in REQUIRED_FIELDS:
        collected = workflow_state.get("collected_fields") or {}
        missing = []
        if workflow == WORKFLOW_SALES_PLAN_7_DAY:
            if not collected.get("product"):
                missing.append("product")
            if not (collected.get("daily_capacity") or collected.get("available_quantity")):
                missing.append("daily_capacity_or_available_quantity")
            if not (collected.get("selling_window") or collected.get("sales_channel")):
                missing.append("selling_window_or_sales_channel")
        elif workflow == WORKFLOW_COST_CALCULATION:
            if not collected.get("ingredients_costs"):
                missing.append("ingredients_costs")
            if not collected.get("total_units"):
                missing.append("total_units")
        elif workflow == WORKFLOW_CONTENT_PLAN and not (collected.get("product") or collected.get("business_type")):
            missing.append("product_or_business_type")
        return missing

    if capability_key in {"sales_plan", "content_plan", "cost_calculation"}:
        return _missing_store_fields(application_state.get("store"))

    return []


def _future_capability_from_message(message: str) -> tuple[str, str] | None:
    lowered = str(message or "").strip().lower()
    for capability_name, keywords in FUTURE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            capability_key = capability_name.lower().replace(" ", "_")
            return capability_name, capability_key
    return None


def _conversation_understanding(application_state: dict) -> dict:
    return (
        (application_state or {}).get("conversation_understanding")
        or ((application_state or {}).get("conversation") or {}).get("understanding")
        or {}
    )


def _conversation_intelligence(application_state: dict) -> dict:
    return (
        (application_state or {}).get("conversation_intelligence")
        or ((application_state or {}).get("conversation") or {}).get("conversation_intelligence")
        or {}
    )


def _intent_resolution(application_state: dict) -> dict:
    intelligence = _conversation_intelligence(application_state)
    return (
        intelligence.get("intent_resolution")
        or (application_state or {}).get("intent_resolution")
        or ((application_state or {}).get("conversation") or {}).get("intent_resolution")
        or {}
    )


def _business_context(application_state: dict) -> dict:
    intelligence = _conversation_intelligence(application_state)
    return (
        intelligence.get("business_context")
        or (application_state or {}).get("business_context")
        or ((application_state or {}).get("conversation") or {}).get("business_context")
        or {}
    )


def _select_task(application_state: dict, user_message: str) -> tuple[str, str, str | None, list[str], str]:
    understanding = _conversation_understanding(application_state)
    intent_resolution = _intent_resolution(application_state)
    business_context = _business_context(application_state)
    resolved_intent = intent_resolution.get("resolved_intent")
    resolved_workflow = intent_resolution.get("resolved_workflow")
    understood_intent = understanding.get("detected_intent")
    active_workflow = ((application_state.get("workflow") or {}).get("workflow_state_v2") or {}).get("workflow")

    if resolved_intent == "business_planning":
        return "Dashboard Request", "dashboard_request", WORKFLOW_DASHBOARD_REQUEST, ["dashboard_builder"], "workflow"
    if resolved_intent == "content_planning":
        return "Content Plan", "content_plan", WORKFLOW_CONTENT_PLAN, ["content_creation"], "workflow"
    if resolved_intent == "marketing_strategy":
        return "Marketing", "content_plan", None, ["marketing"], "llm"
    if resolved_intent in {"sales_planning", "pricing_question"}:
        return "Sales Plan", "sales_plan", WORKFLOW_SALES_PLAN_7_DAY, ["sales_planning"], "workflow"
    if resolved_intent == "cost_calculation":
        return "Cost Calculation", "cost_calculation", WORKFLOW_COST_CALCULATION, ["cost_calculation"], "workflow"
    if resolved_intent in {"continue_previous_workflow", "follow_up_edit"}:
        workflow = resolved_workflow or active_workflow
        if workflow in WORKFLOW_TO_TASK:
            task_type, capability_key, skill_name = WORKFLOW_TO_TASK[workflow]
            return task_type, capability_key, workflow, [skill_name], "workflow"
        if resolved_intent == "follow_up_edit":
            return "General Business Help", "conversation_memory", None, [], "llm"
    if resolved_intent == "reference_resolution" and intent_resolution.get("resolved_references"):
        if "price" in str(user_message).lower() or "ราคา" in str(user_message):
            return "Sales Plan", "sales_plan", WORKFLOW_SALES_PLAN_7_DAY, ["sales_planning"], "workflow"
        return "General Business Help", "conversation_memory", None, [], "llm"
    if resolved_intent == "business_context_update" or (
        business_context.get("business_type") and str(user_message or "").strip() == str(business_context.get("business_type"))
    ):
        return "General Business Help", "conversation_memory", None, [], "llm"

    if understood_intent == "continue_previous_workflow" and active_workflow:
        workflow = active_workflow
        if workflow in WORKFLOW_TO_TASK:
            task_type, capability_key, skill_name = WORKFLOW_TO_TASK[workflow]
            return task_type, capability_key, workflow, [skill_name], "workflow"
    if understood_intent in {"store_summary", "business_status"}:
        return "Dashboard Request", "dashboard_request", WORKFLOW_DASHBOARD_REQUEST, ["dashboard_builder"], "workflow"
    if understood_intent in {"receipt_reference", "image_reference"}:
        return "Receipt Upload", "receipt_upload", WORKFLOW_RECEIPT_CAPTURE, ["receipt_capture"], "workflow"
    if understood_intent == "cost_question":
        return "Cost Calculation", "cost_calculation", WORKFLOW_COST_CALCULATION, ["cost_calculation"], "workflow"
    if understood_intent == "pricing_question":
        return "Sales Plan", "sales_plan", WORKFLOW_SALES_PLAN_7_DAY, ["sales_planning"], "workflow"

    workflow = detect_workflow_intent(user_message, is_product_feedback=is_product_feedback(user_message))
    lowered = str(user_message or "").strip().lower()
    future = _future_capability_from_message(user_message)
    if future:
        task_type, capability_key = future
        return task_type, capability_key, None, [], "workflow"

    if not workflow:
        for candidate_workflow, keywords in ENGLISH_TASK_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                workflow = candidate_workflow
                break
    if not workflow and active_workflow:
        workflow = active_workflow

    if workflow in WORKFLOW_TO_TASK:
        task_type, capability_key, skill_name = WORKFLOW_TO_TASK[workflow]
        return task_type, capability_key, workflow, [skill_name], "workflow"

    intent = detect_conversation_intent(user_message)
    if intent == "PRODUCT_FEEDBACK":
        return "Product Feedback", "product_feedback", None, ["developer_feedback"], "product_brain"
    if intent == "MARKETING":
        return "Marketing", "content_plan", None, ["marketing"], "llm"
    if intent == "CONTENT":
        return "Content Plan", "content_plan", WORKFLOW_CONTENT_PLAN, ["content_creation"], "workflow"
    if intent == "SALES":
        return "Sales Plan", "sales_plan", WORKFLOW_SALES_PLAN_7_DAY, ["sales_planning"], "workflow"

    developer = application_state.get("developer") or {}
    if developer.get("developer_mode") and developer.get("developer_intent"):
        return "Developer Intelligence", "developer_intelligence", None, ["developer_feedback"], "product_brain"

    return "General Business Help", "conversation_memory", None, [], "llm"


def build_execution_plan(application_state, user_message) -> dict:
    state = application_state or {}
    task_type, capability_key, workflow, required_skills, response_mode = _select_task(state, user_message)
    required_information = _required_information(capability_key, workflow)
    missing_information = _missing_information(state, capability_key, workflow)
    known_information = _known_information(state, workflow)
    can_execute = capability_key not in {"ocr", "inventory", "pos_sync", "business_forecast"}

    if missing_information and workflow not in {WORKFLOW_DASHBOARD_REQUEST, WORKFLOW_RECEIPT_CAPTURE}:
        next_step = "collect_missing_information"
    elif can_execute:
        next_step = "route_to_capability"
    else:
        next_step = "explain_capability_not_available"

    priority = "high" if task_type in {"Receipt Upload", "Cost Calculation", "Sales Plan"} else "normal"

    return {
        "goal": str(user_message or "").strip(),
        "conversation_understanding": _conversation_understanding(state),
        "conversation_intelligence": _conversation_intelligence(state),
        "business_context": _business_context(state),
        "intent_resolution": _intent_resolution(state),
        "task_type": task_type,
        "workflow": workflow,
        "required_skills": required_skills,
        "required_information": required_information,
        "known_information": known_information,
        "missing_information": missing_information,
        "can_execute": bool(can_execute and (not missing_information or next_step == "collect_missing_information")),
        "next_step": next_step,
        "priority": priority,
        "estimated_response_mode": response_mode,
    }
