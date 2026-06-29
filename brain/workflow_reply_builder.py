from __future__ import annotations

from brain.natural_response_engine import contains_structured_noise, naturalize_response
from brain.response_mode_engine import ASK_NEXT_FIELD, GENERATE_OUTPUT, determine_response_mode
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)


CONTENT_REQUIRED_FIELDS = ("product", "target_customer", "promotion")
CONTENT_OPTIONAL_DEFAULTS = {"tone": "Friendly"}

WORKFLOW_REPLY_TEMPLATES = {
    WORKFLOW_CONTENT_PLAN: {
        "product": "อยากโปรโมตสินค้าอะไรครับ",
        "target_customer": "ลูกค้าหลักเป็นใครครับ",
        "promotion": "มีโปรโมชั่นอะไรอยู่ไหมครับ",
        "tone": "อยากได้โทนแบบไหนครับ\n\nFriendly\nLuxury\nFunny\nProfessional",
        "generate": "ข้อมูลครบแล้วครับ\n\nกำลังสร้างโพสต์ให้...",
    },
    WORKFLOW_SALES_PLAN_7_DAY: {
        "product": "ขอชื่อสินค้าที่ต้องการทำแผนขายครับ",
        "daily_capacity_or_available_quantity": "สินค้านี้ทำได้วันละกี่ชิ้น หรือมีพร้อมขายกี่ชิ้นครับ",
        "selling_window_or_sales_channel": "ขายช่วงเวลาไหน หรือขายผ่านช่องทางไหนครับ",
        "generate": "ข้อมูลครบแล้วครับ\n\nกำลังทำแผนขายให้...",
    },
    WORKFLOW_COST_CALCULATION: {
        "ingredients_costs": "ขอราคาวัตถุดิบแต่ละอย่างครับ เช่น แป้ง 40 ไข่ 30 น้ำตาล 20",
        "total_units": "รวมแล้วทำได้ทั้งหมดกี่ชิ้นครับ",
        "generate": "ข้อมูลครบแล้วครับ\n\nกำลังคำนวณให้...",
    },
    WORKFLOW_RECEIPT_CAPTURE: {
        "upload": "ส่งไฟล์บิลหรือสลิปได้เลยครับ",
    },
    WORKFLOW_DASHBOARD_REQUEST: {
        "generate": "ได้ครับ กำลังดูภาพรวมร้านให้...",
    },
}


def _content_missing_fields(fields: dict) -> list[str]:
    return [field for field in CONTENT_REQUIRED_FIELDS if not fields.get(field)]


def next_workflow_field(workflow_state: dict | None) -> str | None:
    state = workflow_state or {}
    workflow = state.get("workflow")
    fields = state.get("collected_fields") or {}
    if workflow == WORKFLOW_CONTENT_PLAN:
        missing = _content_missing_fields(fields)
        return missing[0] if missing else None
    missing = state.get("missing_fields") or []
    return missing[0] if missing else None


def build_next_field_reply(workflow_state: dict | None) -> str:
    state = workflow_state or {}
    workflow = state.get("workflow")
    field = next_workflow_field(state)
    template = (WORKFLOW_REPLY_TEMPLATES.get(workflow) or {}).get(field)
    return template or "ขอข้อมูลอีกนิดครับ"


def prepare_content_collection_state(workflow_state: dict) -> dict:
    """Keep create-post UX collecting natural fields without editing the state machine."""
    if (workflow_state or {}).get("workflow") != WORKFLOW_CONTENT_PLAN:
        return workflow_state
    state = dict(workflow_state or {})
    fields = dict(state.get("collected_fields") or {})
    missing = _content_missing_fields(fields)
    if missing:
        state["collected_fields"] = fields
        state["missing_fields"] = missing
        state["is_ready"] = False
        state["next_action"] = "ask_missing_field"
        state["step"] = "collecting_content_inputs"
        return state
    for key, value in CONTENT_OPTIONAL_DEFAULTS.items():
        fields.setdefault(key, value)
    state["collected_fields"] = fields
    state["missing_fields"] = []
    state["is_ready"] = True
    state["next_action"] = "generate"
    state["step"] = "ready_to_generate"
    return state


def build_workflow_reply(
    workflow_state: dict | None,
    *,
    generated_reply: str | None = None,
    planner: dict | None = None,
    reasoning: dict | None = None,
) -> dict:
    state = workflow_state or {}
    mode_decision = determine_response_mode(
        workflow_state=state,
        planner=planner,
        reasoning=reasoning,
        reply_kind=GENERATE_OUTPUT if generated_reply else None,
    )
    builder = "workflow_reply_builder"
    if mode_decision.mode == ASK_NEXT_FIELD:
        raw_reply = build_next_field_reply(state)
        reply = naturalize_response(raw_reply, ASK_NEXT_FIELD)
    else:
        raw_reply = generated_reply or (WORKFLOW_REPLY_TEMPLATES.get(state.get("workflow")) or {}).get("generate") or ""
        reply = naturalize_response(raw_reply, mode_decision.mode, preserve_structured=True)

    return {
        "reply": reply,
        "response_mode": mode_decision.mode,
        "reply_builder": builder,
        "natural_response": not contains_structured_noise(reply),
        "reason": mode_decision.reason,
    }
