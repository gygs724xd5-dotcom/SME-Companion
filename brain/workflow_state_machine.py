from __future__ import annotations

import re
from datetime import datetime, timezone

from brain.cost_intent_isolation import is_strong_cost_calculation_message
from brain.planner_intent_priority import (
    has_profit_calculation_intent,
)
from brain.workflow_field_extractor import extract_workflow_fields
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_GENERAL_BUSINESS_HELP,
    WORKFLOW_PROFIT_CALCULATION,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
    is_workflow_ready,
)
from brain.workflow_lifecycle import attach_lifecycle_diagnostics


REQUIRED_FIELDS = {
    WORKFLOW_SALES_PLAN_7_DAY: ["product", "daily_capacity_or_available_quantity", "selling_window_or_sales_channel"],
    WORKFLOW_PROFIT_CALCULATION: ["price", "cost"],
    WORKFLOW_COST_CALCULATION: ["ingredients_costs", "total_units"],
    WORKFLOW_CONTENT_PLAN: ["product_or_business_type"],
    WORKFLOW_DASHBOARD_REQUEST: [],
    WORKFLOW_RECEIPT_CAPTURE: [],
    WORKFLOW_GENERAL_BUSINESS_HELP: [],
}


def _numeric_value(value) -> float | int | None:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, dict):
        for key in ("amount", "cost", "value", "total"):
            nested = _numeric_value(value.get(key))
            if nested is not None:
                return nested
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            nested = _numeric_value(item)
            if nested is not None:
                return nested
        return None
    try:
        amount = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return int(amount) if amount.is_integer() else amount


def _sum_ingredient_costs(items) -> float | int | None:
    if not items:
        return None
    total = 0.0
    found = False
    for item in items or []:
        amount = _numeric_value(item)
        if amount is None:
            continue
        total += float(amount)
        found = True
    if not found:
        return None
    return int(total) if total.is_integer() else total


def cost_calculation_trace(fields: dict | None) -> dict:
    data = fields or {}
    input_cost = _numeric_value(data.get("cost"))
    input_unit_cost = _numeric_value(data.get("unit_cost"))
    input_cost_per_unit = _numeric_value(data.get("cost_per_unit"))
    input_quantity = _numeric_value(data.get("quantity"))
    input_total_units = _numeric_value(data.get("total_units"))
    input_total_cost = _numeric_value(data.get("total_cost"))
    ingredient_total = _sum_ingredient_costs(data.get("ingredients_costs") or data.get("costs"))
    quantity = input_total_units if input_total_units is not None else input_quantity
    unit_cost = input_unit_cost if input_unit_cost is not None else input_cost_per_unit
    total_cost = input_total_cost if input_total_cost is not None else ingredient_total

    selected_formula = None
    computed_total_cost = None
    computed_cost_per_unit = None
    if unit_cost is not None and quantity is not None:
        selected_formula = "unit_cost_times_quantity"
        computed_total_cost = float(unit_cost) * float(quantity)
        computed_cost_per_unit = unit_cost
    elif total_cost is not None and quantity is not None:
        selected_formula = "total_cost_div_quantity"
        computed_total_cost = total_cost
        computed_cost_per_unit = float(total_cost) / float(quantity) if float(quantity) else None
    elif input_cost is not None and quantity is not None:
        selected_formula = "input_cost_div_quantity"
        computed_total_cost = input_cost
        computed_cost_per_unit = float(input_cost) / float(quantity) if float(quantity) else None

    if isinstance(computed_total_cost, float) and computed_total_cost.is_integer():
        computed_total_cost = int(computed_total_cost)
    if isinstance(computed_cost_per_unit, float) and computed_cost_per_unit.is_integer():
        computed_cost_per_unit = int(computed_cost_per_unit)

    return {
        "input_cost": input_cost,
        "input_unit_cost": input_unit_cost,
        "input_cost_per_unit": input_cost_per_unit,
        "input_quantity": input_quantity,
        "input_total_units": input_total_units,
        "selected_formula": selected_formula,
        "computed_total_cost": computed_total_cost,
        "computed_cost_per_unit": computed_cost_per_unit,
    }

WORKFLOW_START_STEPS = {
    WORKFLOW_SALES_PLAN_7_DAY: "collecting_sales_plan_inputs",
    WORKFLOW_PROFIT_CALCULATION: "collecting_profit_inputs",
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


_WORKFLOW_START_ONLY_MESSAGES = {
    WORKFLOW_CONTENT_PLAN: {
        "create post",
        "post",
        "สร้างโพสต์",
        "ทำโพสต์",
        "เขียนโพสต์",
    },
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
    if has_profit_calculation_intent(message):
        return WORKFLOW_PROFIT_CALCULATION
    if is_strong_cost_calculation_message(message):
        return WORKFLOW_COST_CALCULATION
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


def _field_has_value(field: str, fields: dict) -> bool:
    if field == "product_or_business_type":
        return bool(fields.get("product") or fields.get("business_type"))
    if field == "daily_capacity_or_available_quantity":
        return bool(fields.get("daily_capacity") or fields.get("available_quantity"))
    if field == "selling_window_or_sales_channel":
        return bool(fields.get("selling_window") or fields.get("sales_channel"))
    if field == "ingredients_costs":
        return bool(fields.get("ingredients_costs") or fields.get("cost") or fields.get("unit_cost") or fields.get("cost_per_unit"))
    if field == "total_units":
        return bool(fields.get("total_units") or fields.get("quantity"))
    if field == "price":
        return bool(fields.get("price") or fields.get("selling_price") or fields.get("prices"))
    if field == "cost":
        return bool(fields.get("cost") or fields.get("costs") or fields.get("unit_cost") or fields.get("cost_per_unit") or fields.get("ingredients_costs"))
    return bool(fields.get(field))


def _missing_fields(workflow: str, fields: dict, required_fields: list[str] | None = None) -> list[str]:
    if required_fields:
        return [field for field in required_fields if not _field_has_value(field, fields)]
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
        if not (fields.get("ingredients_costs") or fields.get("cost") or fields.get("unit_cost") or fields.get("cost_per_unit")):
            missing.append("ingredients_costs")
        if not (fields.get("total_units") or fields.get("quantity")):
            missing.append("total_units")
        return missing
    if workflow == WORKFLOW_PROFIT_CALCULATION:
        missing = []
        if not (fields.get("price") or fields.get("selling_price") or fields.get("prices")):
            missing.append("price")
        if not (fields.get("cost") or fields.get("costs") or fields.get("unit_cost") or fields.get("cost_per_unit")):
            missing.append("cost")
        return missing
    if workflow == WORKFLOW_CONTENT_PLAN:
        return [] if fields.get("product") or fields.get("business_type") else ["product_or_business_type"]
    return []


def _missing_reason_by_field(required_fields: list[str], fields: dict, missing_fields: list[str]) -> dict:
    reasons = {}
    for field in required_fields or []:
        checked = []
        if field == "ingredients_costs":
            checked = ["ingredients_costs", "cost", "unit_cost", "cost_per_unit"]
        elif field == "total_units":
            checked = ["total_units", "quantity"]
        elif field == "price":
            checked = ["price", "selling_price", "prices"]
        elif field == "cost":
            checked = ["cost", "costs", "unit_cost", "cost_per_unit", "ingredients_costs"]
        elif field == "daily_capacity_or_available_quantity":
            checked = ["daily_capacity", "available_quantity"]
        elif field == "selling_window_or_sales_channel":
            checked = ["selling_window", "sales_channel"]
        elif field == "product_or_business_type":
            checked = ["product", "business_type"]
        else:
            checked = [field]
        matched = [key for key in checked if fields.get(key) not in (None, "", [], {})]
        reasons[field] = {
            "status": "missing" if field in missing_fields else "completed",
            "aliases_checked": checked,
            "matched_aliases": matched,
            "reason": "no alias had a value" if field in missing_fields else "matched alias value before readiness",
        }
    return reasons


def _attach_workflow_diagnostics(state: dict) -> dict:
    required = list(state.get("required_fields") or [])
    completed = [field for field in required if field not in (state.get("missing_fields") or [])]
    state["readiness_required_fields"] = required
    state["readiness_completed_fields"] = completed
    state["readiness_missing_fields"] = list(state.get("missing_fields") or [])
    state["missing_reason_by_field"] = _missing_reason_by_field(required, state.get("collected_fields") or {}, state.get("missing_fields") or [])
    if state.get("workflow") == WORKFLOW_COST_CALCULATION:
        trace = cost_calculation_trace(state.get("collected_fields") or {})
        state["calculation_trace"] = trace
        fields = dict(state.get("collected_fields") or {})
        for key, value in trace.items():
            if value not in (None, "", [], {}):
                fields[key] = value
        state["collected_fields"] = fields
    return state


_TARGET_CUSTOMER_SHORT_ANSWERS = {
    "วัยรุ่น",
    "แม่บ้าน",
    "นักเรียน",
    "นักศึกษา",
    "คนทำงาน",
    "พนักงานออฟฟิศ",
    "ครอบครัว",
    "เด็ก",
    "ผู้ใหญ่",
}


def _clean_thai_answer(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" :,-")


def _strip_answer_prefix(answer: str, prefixes: list[str]) -> str:
    cleaned = _clean_thai_answer(answer)
    for prefix in prefixes:
        pattern = rf"^{re.escape(prefix)}\s*(?:คือ|เป็น|ชื่อ|ชื่อว่า|:|-)?\s*"
        stripped = re.sub(pattern, "", cleaned, count=1, flags=re.IGNORECASE).strip(" :,-")
        if stripped != cleaned:
            return stripped
    return cleaned


def _looks_like_business_type(answer: str) -> bool:
    return bool(re.match(r"^(?:ร้าน|ร้านขาย|ธุรกิจ|ประเภทร้าน|ประเภทธุรกิจ)", _clean_thai_answer(answer)))


def _extract_product_answer(answer: str) -> str | None:
    cleaned = _strip_answer_prefix(
        answer,
        ["ชื่อสินค้า", "สินค้า", "เป็นสินค้า", "เป็น", "เมนู", "ชื่อเมนู", "ขาย", "ทำ"],
    )
    cleaned = _strip_answer_prefix(cleaned, ["ชื่อ"])
    if cleaned:
        return cleaned
    fallback = _clean_thai_answer(answer)
    return fallback or None


def _extract_business_type_answer(answer: str) -> str | None:
    cleaned = _strip_answer_prefix(
        answer,
        ["ประเภทร้าน", "ประเภทธุรกิจ", "ธุรกิจ", "เป็นร้าน", "ร้าน"],
    )
    if cleaned.startswith("ขาย"):
        cleaned = "ร้าน" + cleaned
    if _looks_like_business_type(answer):
        return _clean_thai_answer(cleaned if cleaned.startswith("ร้าน") else answer)
    return None


def _extract_target_customer_answer(answer: str) -> str | None:
    cleaned = _strip_answer_prefix(answer, ["กลุ่มลูกค้า", "ลูกค้าเป้าหมาย", "ลูกค้า"])
    if cleaned != _clean_thai_answer(answer) and cleaned:
        return cleaned
    if _clean_thai_answer(answer) in _TARGET_CUSTOMER_SHORT_ANSWERS:
        return _clean_thai_answer(answer)
    return None


def _extract_promotion_answer(answer: str) -> str | None:
    cleaned = _clean_thai_answer(answer)
    if re.search(r"(?:โปร|โปรโมชั่น|ส่วนลด|ลด\s*\d|discount|promotion|offer)", cleaned, flags=re.IGNORECASE):
        return cleaned
    return None


def _answer_for_missing_field(field: str, answer: str) -> dict:
    if field == "product_or_business_type":
        business_type = _extract_business_type_answer(answer)
        if business_type:
            return {"business_type": business_type}
        product = _extract_product_answer(answer)
        return {"product": product} if product else {}
    if field == "product":
        product = _extract_product_answer(answer)
        return {"product": product} if product else {}
    if field == "business_type":
        business_type = _extract_business_type_answer(answer) or _clean_thai_answer(answer)
        return {"business_type": business_type} if business_type else {}
    if field == "target_customer":
        target_customer = _extract_target_customer_answer(answer) or _clean_thai_answer(answer)
        return {"target_customer": target_customer} if target_customer else {}
    if field == "promotion":
        promotion = _extract_promotion_answer(answer) or _clean_thai_answer(answer)
        return {"promotion": promotion} if promotion else {}
    return {}


def _direct_answer_fields(workflow: str, current: dict, user_message: str, extracted_fields: dict) -> dict:
    answer = str(user_message or "").strip()
    if not answer:
        return {}
    if not (current.get("collected_fields") or {}) and answer.lower() in _WORKFLOW_START_ONLY_MESSAGES.get(workflow, set()):
        return {}

    missing = list(current.get("missing_fields") or _missing_fields(workflow, current.get("collected_fields") or {}))
    explicit_fields = {}
    business_type = _extract_business_type_answer(answer)
    target_customer = _extract_target_customer_answer(answer)
    promotion = _extract_promotion_answer(answer)
    if business_type:
        explicit_fields["business_type"] = business_type
    if target_customer:
        explicit_fields["target_customer"] = target_customer
    if promotion:
        explicit_fields["promotion"] = promotion

    if not missing:
        return explicit_fields

    first_missing = missing[0]
    field_answer = _answer_for_missing_field(first_missing, answer)
    if field_answer:
        return {**explicit_fields, **field_answer}

    if extracted_fields:
        return {}

    if workflow == WORKFLOW_SALES_PLAN_7_DAY:
        if first_missing == "daily_capacity_or_available_quantity":
            amount = _first_number(answer)
            return {"daily_capacity": amount} if amount else {}
        if first_missing == "selling_window_or_sales_channel":
            return {"sales_channel": answer}
    if workflow == WORKFLOW_COST_CALCULATION and first_missing == "total_units":
        amount = _first_number(answer)
        return {"total_units": amount} if amount else {}
    return {}


def _first_number(value: str) -> float | int | None:
    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", str(value or ""))
    if not match:
        return None
    amount = float(match.group(0).replace(",", ""))
    return int(amount) if amount.is_integer() else amount


def update_workflow_state(
    current_state: dict | None,
    user_message: str,
    detected_workflow: str | None = None,
    canonical_entities: dict | None = None,
) -> tuple[dict, dict]:
    current = current_state or {}
    workflow = detected_workflow or current.get("workflow")
    if workflow is None:
        return new_workflow_state(None), {}
    if detected_workflow and detected_workflow != current.get("workflow"):
        current = new_workflow_state(detected_workflow)

    extracted = extract_workflow_fields(user_message, workflow=workflow, canonical_entities=canonical_entities)
    direct_answer = _direct_answer_fields(workflow, current, user_message, extracted)
    collected_fields = _merge_fields(current.get("collected_fields") or {}, {**extracted, **direct_answer})
    required_fields = list(current.get("required_fields") or REQUIRED_FIELDS.get(workflow, []))
    state = {
        **new_workflow_state(workflow),
        **current,
        "workflow": workflow,
        "required_fields": required_fields,
        "collected_fields": collected_fields,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    state["missing_fields"] = _missing_fields(workflow, collected_fields, required_fields)
    state["is_ready"] = is_workflow_ready(state) or (bool(required_fields) and not state["missing_fields"])
    state = _attach_workflow_diagnostics(state)
    if workflow in {WORKFLOW_DASHBOARD_REQUEST, WORKFLOW_RECEIPT_CAPTURE}:
        state["step"] = WORKFLOW_START_STEPS.get(workflow, "route")
        state["next_action"] = "route"
    elif state["is_ready"]:
        state["step"] = "ready_to_generate"
        state["next_action"] = "generate"
    else:
        state["step"] = WORKFLOW_START_STEPS.get(workflow, "collecting_fields")
        state["next_action"] = "ask_missing_field"
    state = attach_lifecycle_diagnostics(
        state,
        transition_reason="workflow ready for execution" if state.get("is_ready") else "workflow collecting missing fields",
    )
    return state, {**extracted, **direct_answer}
