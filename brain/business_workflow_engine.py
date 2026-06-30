from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any

from brain.business_entity_extractor import REQUIRED_BY_INTENT
from brain.conversation_manager import active_workflow_state, ensure_conversation_os_state
from brain.workflow_registry import get_workflow_definition, get_workflow_registry


ACTION_CONTINUE = "continue"
ACTION_INTERRUPT = "interrupt"
ACTION_RESUME = "resume"
ACTION_COMPLETE = "complete"
ACTION_CANCEL = "cancel"
ACTION_START_NEW = "start_new"

WORKFLOW_STATUS_DONE = {"END", "CANCELLED", "TIMEOUT"}

WORKFLOW_INTENTS = {
    "profit_calculation",
    "pricing_question",
    "sales_summary",
    "cost_calculation",
    "inventory_check",
}

OVERRIDE_INTENTS = {
    "general_question",
    "label_explanation",
    "customer_reply",
    "customer_says_expensive",
    "marketing_content",
    "business_advice",
    "unknown_with_question",
}

REQUIRED_ENTITIES_BY_INTENT = {
    "profit_calculation": ("product", "price", "cost", "quantity"),
    "pricing_question": ("product",),
    "sales_summary": ("date",),
    "cost_calculation": ("product", "cost"),
    "inventory_check": ("product",),
}

REQUIRED_ENTITIES_BY_WORKFLOW = {
    "PROFIT_CALCULATION": ("product", "price", "cost", "quantity"),
    "COST_CALCULATION": ("cost", "quantity"),
    "SALES_PLAN_7_DAY": ("product", "daily_capacity_or_available_quantity", "selling_window_or_sales_channel"),
    "CONTENT_PLAN": ("product_or_business_type",),
    "DASHBOARD_REQUEST": (),
    "RECEIPT_CAPTURE": (),
    "GENERAL_BUSINESS_HELP": (),
}

QUESTION_BY_ENTITY = {
    "product": "สินค้าหรือเมนูอะไรครับ",
    "product_or_business_type": "อยากโฟกัสสินค้าหรือประเภทร้านอะไรครับ",
    "price": "ขายราคากี่บาทครับ",
    "cost": "ต้นทุนต่อชิ้นกี่บาทครับ",
    "quantity": "ขายทั้งหมดกี่ชิ้นครับ",
    "date": "ต้องการดูช่วงวันไหนครับ",
    "daily_capacity_or_available_quantity": "สินค้านี้ทำได้วันละกี่ชิ้น หรือมีพร้อมขายกี่ชิ้นครับ",
    "selling_window_or_sales_channel": "ขายช่วงเวลาไหน หรือขายผ่านช่องทางไหนครับ",
}

CANCEL_TRIGGERS = ("cancel", "stop", "ยกเลิก", "หยุด", "เลิกทำ")
RESUME_TRIGGERS = ("resume", "continue", "ต่อ", "ทำต่อ", "กลับมา", "กลับมาคำนวณ", "คำนวณต่อ")
EXPLANATION_TRIGGERS = ("คืออะไร", "หมายถึงอะไร", "แปลว่าอะไร", "what is", "explain")
GENERAL_QUESTION_TRIGGERS = ("กี่โมง", "เวลาเท่าไร", "what time", "คืออะไร", "ทำไม", "อย่างไร", "?")
BUSINESS_ADVICE_TRIGGERS = ("แนะนำ", "ควร", "ดีไหม", "ทำยังไง", "strategy", "advice")


def decide_business_workflow(
    user_message: str | None,
    business_intent: dict | None = None,
    entity_result: dict | None = None,
    application_state: dict | None = None,
) -> dict:
    """Decide whether the current message should collect, pause, resume, or bypass workflow."""
    message = str(user_message or "").strip()
    state = application_state if application_state is not None else {}
    intent = str((business_intent or {}).get("detected_intent") or "unknown")
    intent = _refine_intent(intent, message, entity_result)
    intent_confidence = float((business_intent or {}).get("intent_confidence") or 0.0)
    entities = (entity_result or {}).get("extracted_entities") or {}
    active = active_workflow_state(state)
    paused = _paused_workflow_state(state)
    active_or_paused = active or paused
    active_workflow_id = _workflow_id(active)
    resume_available = bool(paused or _conversation_stack(state))

    base = _build_payload(
        workflow_action=ACTION_CONTINUE if active else ACTION_START_NEW,
        workflow_state=active_or_paused,
        user_message=message,
        detected_intent=intent,
        workflow_confidence=max(intent_confidence, 0.55 if active else 0.4),
        workflow_reason="workflow decision initialized",
        entity_result=entity_result,
        current_entities=entities,
    )

    if _is_cancel(message):
        return _with_decision(
            base,
            workflow_action=ACTION_CANCEL,
            workflow_state=active,
            workflow_confidence=0.95,
            workflow_reason="user requested workflow cancellation",
            workflow_interrupted=False,
        )

    if _is_resume(message) and resume_available:
        return _with_decision(
            _build_payload(
                workflow_action=ACTION_RESUME,
                workflow_state=paused or active,
                user_message=message,
                detected_intent=intent,
                workflow_confidence=0.92,
                workflow_reason="user requested workflow resume",
                entity_result=entity_result,
                current_entities=entities,
            ),
            workflow_interrupted=False,
        )

    if active and _override_reason(intent, message):
        return _with_decision(
            _build_payload(
                workflow_action=ACTION_INTERRUPT,
                workflow_state=active,
                user_message=message,
                detected_intent=intent,
                workflow_confidence=0.9,
                workflow_reason=_override_reason(intent, message),
                entity_result=entity_result,
                current_entities=entities,
            ),
            workflow_interrupted=True,
        )

    if active:
        workflow_payload = _build_payload(
            workflow_action=ACTION_CONTINUE,
            workflow_state=active,
            user_message=message,
            detected_intent=intent,
            workflow_confidence=max(intent_confidence, 0.74),
            workflow_reason="current message continues active workflow",
            entity_result=entity_result,
            current_entities=entities,
        )
        if workflow_payload["workflow_complete"]:
            return _with_decision(
                workflow_payload,
                workflow_action=ACTION_CONTINUE,
                workflow_confidence=max(workflow_payload["workflow_confidence"], 0.88),
                workflow_reason="required entities are complete",
            )
        if _supplies_missing_information(message, workflow_payload):
            return workflow_payload
        if intent in WORKFLOW_INTENTS and _intent_to_workflow(intent) != active_workflow_id:
            return _with_decision(
                workflow_payload,
                workflow_action=ACTION_START_NEW,
                workflow_confidence=max(intent_confidence, 0.78),
                workflow_reason="user requested a different business workflow",
                workflow_interrupted=True,
            )
        return _with_decision(
            workflow_payload,
            workflow_action=ACTION_INTERRUPT if _looks_like_question(message) else ACTION_CONTINUE,
            workflow_confidence=0.62,
            workflow_reason="message does not clearly provide missing workflow information" if _looks_like_question(message) else "short answer treated as workflow continuation",
            workflow_interrupted=_looks_like_question(message),
        )

    if intent in WORKFLOW_INTENTS:
        workflow_state = _synthetic_workflow_state(intent, entities)
        workflow_payload = _build_payload(
            workflow_action=ACTION_START_NEW,
            workflow_state=workflow_state,
            user_message=message,
            detected_intent=intent,
            workflow_confidence=max(intent_confidence, 0.7),
            workflow_reason="business intent starts a workflow",
            entity_result=entity_result,
            current_entities=entities,
        )
        if workflow_payload["workflow_complete"]:
            return _with_decision(
                workflow_payload,
                workflow_action=ACTION_COMPLETE,
                workflow_confidence=max(workflow_payload["workflow_confidence"], 0.9),
                workflow_reason="all required entities were supplied in the current message",
            )
        return workflow_payload

    if paused and _is_resume(message):
        return _with_decision(
            _build_payload(
                workflow_action=ACTION_RESUME,
                workflow_state=paused,
                user_message=message,
                detected_intent=intent,
                workflow_confidence=0.88,
                workflow_reason="paused workflow is available and user asked to continue",
                entity_result=entity_result,
                current_entities=entities,
            ),
            workflow_interrupted=False,
        )

    return _with_decision(
        base,
        workflow_action=ACTION_INTERRUPT if _override_reason(intent, message) else ACTION_CONTINUE,
        workflow_state=None,
        workflow_confidence=max(intent_confidence, 0.45),
        workflow_reason=_override_reason(intent, message) or "no active business workflow",
        workflow_interrupted=False,
    )


def smart_question_for_missing(missing_entities: list[str] | tuple[str, ...] | None) -> str | None:
    for entity in missing_entities or []:
        question = QUESTION_BY_ENTITY.get(str(entity))
        if question:
            return question
    return None


def _build_payload(
    *,
    workflow_action: str,
    workflow_state: dict | None,
    user_message: str,
    detected_intent: str,
    workflow_confidence: float,
    workflow_reason: str,
    entity_result: dict | None,
    current_entities: dict,
) -> dict:
    workflow = _workflow_id(workflow_state) or _intent_to_workflow(detected_intent)
    current_entities, mapping_trace = _normalize_workflow_entities(workflow, current_entities, user_message)
    required_entities = list(_required_entities(workflow, detected_intent, workflow_state))
    completed_entities = _completed_entities(workflow_state, current_entities, required_entities, user_message)
    missing_entities = [entity for entity in required_entities if entity not in completed_entities]
    progress = _progress(completed_entities, required_entities)
    complete = bool(required_entities) and not missing_entities
    stage = _workflow_stage(workflow_state, complete, missing_entities)
    compact_state = _compact_workflow_state(workflow_state, workflow, completed_entities, missing_entities)
    return {
        "workflow_action": workflow_action,
        "workflow_state": compact_state,
        "workflow_stage": stage,
        "workflow_progress": progress,
        "workflow_confidence": round(max(0.0, min(0.99, workflow_confidence)), 2),
        "workflow_complete": complete,
        "workflow_reason": workflow_reason,
        "workflow_interrupted": workflow_action == ACTION_INTERRUPT,
        "workflow_resume_available": bool(_paused_workflow_state_for_payload(workflow_state)),
        "required_entities": required_entities,
        "completed_entities": completed_entities,
        "missing_entities": missing_entities,
        "entity_completeness": progress,
        "next_question": None if complete else smart_question_for_missing(missing_entities),
        "detected_intent": detected_intent,
        "extracted_entities": deepcopy(current_entities),
        "raw_missing_entities": list((entity_result or {}).get("missing_entities") or []),
        "entity_mapping_trace": mapping_trace,
        "workflow_readiness_decision": {
            "workflow_id": workflow,
            "required_entities": required_entities,
            "completed_entities": completed_entities,
            "missing_entities": missing_entities,
            "workflow_complete": complete,
            "reason_by_field": _readiness_reason_by_field(required_entities, current_entities, missing_entities),
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _with_decision(payload: dict, **updates) -> dict:
    result = {**payload, **updates}
    if result.get("workflow_action") == ACTION_INTERRUPT:
        result["workflow_interrupted"] = True
        result["workflow_resume_available"] = bool(result.get("workflow_state"))
    if result.get("workflow_action") == ACTION_COMPLETE:
        result["workflow_complete"] = True
    return result


def _required_entities(workflow: str | None, intent: str, workflow_state: dict | None) -> tuple[str, ...]:
    state_required = tuple(_canonical_entity(field) for field in ((workflow_state or {}).get("required_entities") or ()))
    if state_required:
        return state_required
    if workflow in REQUIRED_ENTITIES_BY_WORKFLOW:
        return REQUIRED_ENTITIES_BY_WORKFLOW[workflow]
    if intent in REQUIRED_ENTITIES_BY_INTENT:
        return REQUIRED_ENTITIES_BY_INTENT[intent]
    required = tuple(REQUIRED_BY_INTENT.get(intent, ()))
    return tuple(_canonical_entity(field) for field in required)


def _completed_entities(workflow_state: dict | None, current_entities: dict, required_entities: list[str], user_message: str = "") -> list[str]:
    completed = set()
    collected = _collected_fields(workflow_state)
    for entity in required_entities:
        if _has_entity(entity, collected) or _has_entity(entity, current_entities):
            completed.add(entity)
    remaining = [entity for entity in required_entities if entity not in completed]
    if (
        remaining
        and len(remaining) == 1
        and workflow_state
        and not workflow_state.get("__synthetic")
        and _looks_like_numeric_or_field_answer(user_message)
    ):
        completed.add(remaining[0])
    return [entity for entity in required_entities if entity in completed]


def _normalize_workflow_entities(workflow: str | None, entities: dict | None, user_message: str = "") -> tuple[dict, list[dict]]:
    data = deepcopy(entities or {})
    trace = list(data.get("entity_mapping_trace") or [])
    if workflow != "COST_CALCULATION":
        return data, trace

    unit_cost = _unit_cost_from_message(user_message)
    if unit_cost not in (None, "", [], {}):
        for field in ("cost", "unit_cost", "cost_per_unit"):
            if data.get(field) in (None, "", [], {}):
                data[field] = unit_cost
        if not data.get("costs"):
            data["costs"] = [{"amount": unit_cost, "currency": "THB", "raw": "บาทต่อชิ้น"}]
        trace.append(
            {
                "field": "cost",
                "aliases": ["price", "unit_cost", "cost_per_unit"],
                "source": "workflow_normalization: amount + บาทต่อชิ้น",
                "value": unit_cost,
            }
        )

    quantity = _quantity_from_entities_or_message(data, user_message)
    if quantity not in (None, "", [], {}):
        for field in ("quantity", "total_units"):
            if data.get(field) in (None, "", [], {}):
                data[field] = quantity
        trace.append(
            {
                "field": "quantity",
                "aliases": ["quantities", "total_units", "units"],
                "source": "workflow_normalization: quantity/unit pattern",
                "value": quantity,
            }
        )
    data["entity_mapping_trace"] = trace
    return data, trace


def _unit_cost_from_message(message: str) -> float | int | None:
    match = re.search(
        r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)\s*(?:\u0e15\u0e48\u0e2d|/)\s*(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|pcs?|units?)",
        str(message or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    return int(amount) if amount.is_integer() else amount


def _quantity_from_entities_or_message(entities: dict, message: str) -> float | int | None:
    for item in entities.get("quantities") or []:
        if isinstance(item, dict) and item.get("amount") not in (None, "", [], {}):
            return item.get("amount")
    match = re.search(
        r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|pcs?|units?)",
        str(message or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    return int(amount) if amount.is_integer() else amount


def _has_entity(entity: str, values: dict | None) -> bool:
    data = values or {}
    aliases = {
        "product": ("product", "product_or_service", "product_or_service_names", "business_type", "product_name"),
        "product_or_business_type": ("product_or_business_type", "product", "business_type", "product_or_service_names"),
        "price": ("price", "prices", "selling_price"),
        "cost": ("cost", "costs", "ingredients_costs", "unit_cost", "cost_per_unit"),
        "quantity": ("quantity", "quantities", "total_units", "units", "daily_capacity", "available_quantity"),
        "date": ("date", "dates"),
        "daily_capacity_or_available_quantity": ("daily_capacity_or_available_quantity", "daily_capacity", "available_quantity", "quantities"),
        "selling_window_or_sales_channel": ("selling_window_or_sales_channel", "selling_window", "sales_channel"),
    }.get(entity, (entity,))
    return any(data.get(alias) not in (None, "", [], {}) for alias in aliases)


def _readiness_reason_by_field(required_entities: list[str], entities: dict, missing_entities: list[str]) -> dict:
    reasons = {}
    for entity in required_entities:
        aliases = _entity_aliases(entity)
        matched_aliases = [alias for alias in aliases if (entities or {}).get(alias) not in (None, "", [], {})]
        reasons[entity] = {
            "status": "missing" if entity in missing_entities else "completed",
            "aliases_checked": list(aliases),
            "matched_aliases": matched_aliases,
            "reason": "no alias had a value" if entity in missing_entities else "matched alias value before readiness",
        }
    return reasons


def _entity_aliases(entity: str) -> tuple[str, ...]:
    return {
        "product": ("product", "product_or_service", "product_or_service_names", "business_type", "product_name"),
        "product_or_business_type": ("product_or_business_type", "product", "business_type", "product_or_service_names"),
        "price": ("price", "prices", "selling_price"),
        "cost": ("cost", "costs", "ingredients_costs", "unit_cost", "cost_per_unit"),
        "quantity": ("quantity", "quantities", "total_units", "units", "daily_capacity", "available_quantity"),
        "date": ("date", "dates"),
        "daily_capacity_or_available_quantity": ("daily_capacity_or_available_quantity", "daily_capacity", "available_quantity", "quantities"),
        "selling_window_or_sales_channel": ("selling_window_or_sales_channel", "selling_window", "sales_channel"),
    }.get(entity, (entity,))


def _collected_fields(workflow_state: dict | None) -> dict:
    state = workflow_state or {}
    collected = dict(state.get("collected_fields") or {})
    if state.get("workflow_data"):
        collected.update({k: v for k, v in (state.get("workflow_data") or {}).items() if v not in (None, "", [], {})})
    machine = state.get("state_machine") or state.get("workflow_state_v2") or {}
    if isinstance(machine, dict):
        collected.update({k: v for k, v in (machine.get("collected_fields") or {}).items() if v not in (None, "", [], {})})
    return collected


def _compact_workflow_state(
    workflow_state: dict | None,
    workflow: str | None,
    completed_entities: list[str],
    missing_entities: list[str],
) -> dict:
    state = deepcopy(workflow_state or {})
    if not state and not workflow:
        return {}
    return {
        "workflow_id": _workflow_id(state) or workflow,
        "workflow_name": state.get("workflow_name") or _workflow_name(workflow),
        "workflow_status": state.get("workflow_status"),
        "current_step": state.get("current_step") or state.get("step"),
        "collected_fields": _collected_fields(state),
        "required_entities": list(_required_entities(workflow, "", state)),
        "completed_entities": completed_entities,
        "missing_entities": missing_entities,
        "missing_fields": list(state.get("missing_fields") or missing_entities),
    }


def _workflow_id(workflow_state: dict | None) -> str | None:
    state = workflow_state or {}
    return state.get("workflow_id") or state.get("workflow") or state.get("current_workflow")


def _workflow_name(workflow_id: str | None) -> str | None:
    definition = get_workflow_definition(workflow_id)
    return definition.workflow_name if definition else workflow_id


def _workflow_stage(workflow_state: dict | None, complete: bool, missing: list[str]) -> str:
    if complete:
        return "ready_to_reason"
    state = workflow_state or {}
    return state.get("current_step") or state.get("step") or ("collecting_entities" if missing else "idle")


def _progress(completed: list[str], required: list[str]) -> dict:
    total = len(required)
    done = len(completed)
    percent = 1.0 if total == 0 else round(done / total, 2)
    return {"completed": done, "required": total, "percent": percent}


def _canonical_entity(field: str) -> str:
    mapping = {
        "product_or_service": "product",
        "product_or_service_names": "product",
        "prices": "price",
        "costs": "cost",
        "quantities": "quantity",
        "dates": "date",
        "ingredients_costs": "cost",
        "total_units": "quantity",
    }
    return mapping.get(str(field), str(field))


def _intent_to_workflow(intent: str | None) -> str | None:
    mapping = {
        "profit_calculation": "PROFIT_CALCULATION",
        "pricing_question": "SALES_PLAN_7_DAY",
        "sales_summary": "DASHBOARD_REQUEST",
        "cost_calculation": "COST_CALCULATION",
        "inventory_check": "INVENTORY_CHECK",
        "marketing_content": "CONTENT_PLAN",
    }
    return mapping.get(str(intent or ""))


def _synthetic_workflow_state(intent: str, entities: dict) -> dict:
    workflow = _intent_to_workflow(intent)
    definition = get_workflow_definition(workflow)
    required_entities = REQUIRED_ENTITIES_BY_WORKFLOW.get(workflow, REQUIRED_ENTITIES_BY_INTENT.get(intent, ()))
    return {
        "__synthetic": True,
        "workflow_id": workflow,
        "workflow_name": definition.workflow_name if definition else intent,
        "workflow_status": "COLLECT",
        "current_step": "collecting_entities",
        "collected_fields": _entities_to_fields(entities),
        "required_entities": list(required_entities),
    }


def _entities_to_fields(entities: dict | None) -> dict:
    data = entities or {}
    fields = {}
    if data.get("product_or_service_names"):
        fields["product"] = data["product_or_service_names"][0]
    if data.get("prices"):
        fields["price"] = data["prices"][0]
    if data.get("costs"):
        fields["cost"] = data["costs"][0]
    if data.get("cost"):
        fields["cost"] = data["cost"]
    if data.get("unit_cost"):
        fields["unit_cost"] = data["unit_cost"]
    if data.get("cost_per_unit"):
        fields["cost_per_unit"] = data["cost_per_unit"]
    if data.get("quantities"):
        fields["quantity"] = data["quantities"][0]
    if data.get("quantity"):
        fields["quantity"] = data["quantity"]
    if data.get("total_units"):
        fields["total_units"] = data["total_units"]
    if data.get("dates"):
        fields["date"] = data["dates"][0]
    return fields


def _paused_workflow_state(state: dict | None) -> dict | None:
    source = state if state is not None else {}
    os_state = ensure_conversation_os_state(source)
    paused_id = os_state.get("last_paused_workflow_id")
    if paused_id:
        candidate = (os_state.get("workflow_states") or {}).get(paused_id)
        if candidate and candidate.get("workflow_status") == "PAUSED":
            return candidate
    for candidate in reversed(os_state.get("conversation_stack") or []):
        if candidate.get("workflow_status") not in WORKFLOW_STATUS_DONE:
            return candidate
    return None


def _paused_workflow_state_for_payload(workflow_state: dict | None) -> dict | None:
    if workflow_state and (workflow_state.get("workflow_status") == "PAUSED"):
        return workflow_state
    return None


def _conversation_stack(state: dict | None) -> list:
    os_state = ensure_conversation_os_state(state if state is not None else {})
    return list(os_state.get("conversation_stack") or [])


def _refine_intent(intent: str, message: str, entity_result: dict | None) -> str:
    normalized = message.lower()
    if _is_label_explanation(normalized):
        return "label_explanation"
    if intent == "unknown" and _looks_like_customer_reply(message, entity_result):
        return "customer_reply"
    if intent == "unknown" and _looks_like_question(message):
        if any(trigger in normalized for trigger in BUSINESS_ADVICE_TRIGGERS):
            return "business_advice"
        if any(trigger in normalized for trigger in GENERAL_QUESTION_TRIGGERS):
            return "general_question"
        return "unknown_with_question"
    return intent


def _override_reason(intent: str, message: str) -> str | None:
    normalized = message.lower()
    if intent in {"customer_reply", "customer_says_expensive"}:
        return "customer_reply intent overrides workflow"
    if intent == "label_explanation" or _is_label_explanation(normalized):
        return "label_explanation"
    if intent in OVERRIDE_INTENTS:
        return intent
    if _looks_like_question(message) and not _looks_like_numeric_or_field_answer(message):
        return "general_question"
    return None


def _is_cancel(message: str) -> bool:
    normalized = message.lower()
    return any(trigger in normalized for trigger in CANCEL_TRIGGERS)


def _is_resume(message: str) -> bool:
    normalized = message.lower()
    return any(trigger in normalized for trigger in RESUME_TRIGGERS)


def _is_label_explanation(normalized: str) -> bool:
    return bool(re.search(r"\b[a-z][a-z0-9_]{2,}\s+(?:คืออะไร|means?|mean|คือ)\b", normalized)) or any(
        trigger in normalized for trigger in EXPLANATION_TRIGGERS
    ) and bool(re.search(r"[a-z_]{3,}", normalized))


def _looks_like_customer_reply(message: str, entity_result: dict | None) -> bool:
    entities = (entity_result or {}).get("extracted_entities") or {}
    if entities.get("customer_phrases"):
        return True
    normalized = message.lower()
    return any(token in normalized for token in ("ลูกค้าบอก", "ลูกค้าถาม", "ตอบลูกค้า", "customer says", "customer asked"))


def _looks_like_question(message: str) -> bool:
    normalized = message.lower()
    return "?" in message or any(token in normalized for token in ("ไหม", "อะไร", "ทำไม", "อย่างไร", "เท่าไร", "how", "what", "why"))


def _looks_like_numeric_or_field_answer(message: str) -> bool:
    normalized = message.lower().strip()
    if re.fullmatch(r"[\d,.\s]+", normalized):
        return True
    return bool(re.search(r"\d", normalized)) and len(normalized.split()) <= 8


def _supplies_missing_information(message: str, workflow_payload: dict) -> bool:
    if not message:
        return False
    if set(workflow_payload.get("completed_entities") or set()):
        return True
    return _looks_like_numeric_or_field_answer(message) or (len(message) <= 80 and not _looks_like_question(message))
