from __future__ import annotations

from brain.natural_response_engine import contains_structured_noise, naturalize_response
from brain.response_mode_engine import ASK_NEXT_FIELD, GENERATE_OUTPUT, determine_response_mode
from brain.workflow_lifecycle import variant_instruction_from_message
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)

CONTENT_REQUIRED_FIELDS = ("product", "target_customer")
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


def _content_post_from_fields(fields: dict, *, variant: dict | None = None) -> str:
    variant = variant or {}
    product = fields.get("product") or fields.get("business_type") or "\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32"
    target = fields.get("target_customer") or "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32"
    tone = str(fields.get("tone") or "Friendly")
    if variant.get("luxury"):
        tone = "Luxury"
    elif variant.get("friendly"):
        tone = "\u0e40\u0e1b\u0e47\u0e19\u0e01\u0e31\u0e19\u0e40\u0e2d\u0e07"
    if variant.get("short"):
        return (
            "\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22\u0e04\u0e23\u0e31\u0e1a\n\n"
            f"{product} \u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a{target} "
            f"\u0e1e\u0e23\u0e49\u0e2d\u0e21\u0e43\u0e2b\u0e49\u0e25\u0e2d\u0e07\u0e41\u0e25\u0e49\u0e27\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49 "
            f"\u0e17\u0e31\u0e01\u0e41\u0e0a\u0e17\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e2a\u0e31\u0e48\u0e07\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22"
        )
    if variant.get("youth"):
        target = "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19"
    selling_line = (
        f"{product}\u0e19\u0e35\u0e49\u0e0a\u0e48\u0e27\u0e22\u0e43\u0e2b\u0e49{target}\u0e15\u0e31\u0e14\u0e2a\u0e34\u0e19\u0e43\u0e08\u0e07\u0e48\u0e32\u0e22\u0e02\u0e36\u0e49\u0e19 "
        f"\u0e40\u0e1e\u0e23\u0e32\u0e30\u0e44\u0e14\u0e49\u0e17\u0e31\u0e49\u0e07\u0e04\u0e27\u0e32\u0e21\u0e04\u0e38\u0e49\u0e21 \u0e04\u0e27\u0e32\u0e21\u0e2a\u0e30\u0e14\u0e27\u0e01 \u0e41\u0e25\u0e30\u0e04\u0e27\u0e32\u0e21\u0e19\u0e48\u0e32\u0e25\u0e2d\u0e07"
        if variant.get("stronger_sales")
        else f"{product}\u0e15\u0e31\u0e27\u0e19\u0e35\u0e49\u0e15\u0e2d\u0e1a\u0e42\u0e08\u0e17\u0e22\u0e4c\u0e04\u0e23\u0e31\u0e1a"
    )
    hook = "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a" if variant.get("generate_variant") else "\u0e42\u0e1e\u0e2a\u0e15\u0e4c"
    body = (
        "\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22\u0e04\u0e23\u0e31\u0e1a\n\n"
        f"{hook}\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a{product}\n\n"
        f"\u0e16\u0e49\u0e32{target}\u0e01\u0e33\u0e25\u0e31\u0e07\u0e21\u0e2d\u0e07\u0e2b\u0e32\u0e2d\u0e30\u0e44\u0e23\u0e17\u0e35\u0e48\u0e0b\u0e37\u0e49\u0e2d\u0e07\u0e48\u0e32\u0e22 \u0e43\u0e0a\u0e49\u0e44\u0e14\u0e49\u0e08\u0e23\u0e34\u0e07 \u0e41\u0e25\u0e30\u0e14\u0e39\u0e04\u0e38\u0e49\u0e21 "
        f"{selling_line}\n\n"
        f"\u0e42\u0e17\u0e19: {tone}\n"
        f"\u0e17\u0e31\u0e01\u0e41\u0e0a\u0e17\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e2a\u0e31\u0e48\u0e07\u0e2b\u0e23\u0e37\u0e2d\u0e16\u0e32\u0e21\u0e23\u0e32\u0e22\u0e25\u0e30\u0e40\u0e2d\u0e35\u0e22\u0e14\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22"
    )
    if variant.get("long"):
        body += (
            "\n\n"
            f"\u0e40\u0e2b\u0e21\u0e32\u0e30\u0e01\u0e31\u0e1a{target}\u0e17\u0e35\u0e48\u0e2d\u0e22\u0e32\u0e01\u0e44\u0e14\u0e49\u0e2d\u0e30\u0e44\u0e23\u0e17\u0e35\u0e48\u0e0b\u0e37\u0e49\u0e2d\u0e41\u0e25\u0e49\u0e27\u0e23\u0e39\u0e49\u0e2a\u0e36\u0e01\u0e04\u0e38\u0e49\u0e21 "
            "\u0e43\u0e0a\u0e49\u0e44\u0e14\u0e49\u0e1a\u0e48\u0e2d\u0e22 \u0e41\u0e25\u0e30\u0e44\u0e21\u0e48\u0e15\u0e49\u0e2d\u0e07\u0e04\u0e34\u0e14\u0e19\u0e32\u0e19"
        )
    return body


def completed_workflow_followup_reply(
    completed_workflow: dict | None,
    user_message: str | None,
    *,
    workflow_variant_mode: str | None = None,
) -> dict | None:
    return None


def completed_workflow_output_stop_condition(
    *,
    workflow_state: dict | None = None,
    workflow_decision: dict | None = None,
    response_mode: str | None = None,
) -> dict:
    state = workflow_state or {}
    decision = workflow_decision or {}
    missing_fields = list(
        state.get("missing_fields")
        or decision.get("missing_fields")
        or decision.get("missing_entities")
        or decision.get("readiness_missing_fields")
        or []
    )
    workflow_complete = bool(
        state.get("workflow_complete")
        or state.get("step") == "completed"
        or decision.get("workflow_complete")
    )
    workflow_action = decision.get("workflow_action") or state.get("workflow_action")
    render_result_only = bool(
        workflow_complete
        and workflow_action == "complete"
        and not missing_fields
        and (response_mode in (None, GENERATE_OUTPUT, "WORKFLOW_COMPLETE"))
    )
    return {
        "render_result_only": render_result_only,
        "clarification_allowed": not render_result_only,
        "ask_next_field_allowed": not render_result_only,
        "proactive_followup_allowed": not render_result_only,
        "generic_followup_allowed": not render_result_only,
        "proactive_recommendation_allowed": not render_result_only,
        "llm_rewrite_allowed": not render_result_only,
        "append_question_allowed": not render_result_only,
        "missing_fields": missing_fields,
        "workflow_complete": workflow_complete,
        "workflow_action": workflow_action,
        "response_mode": response_mode,
    }


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
