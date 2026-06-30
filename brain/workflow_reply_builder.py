from __future__ import annotations

import re

from brain.natural_response_engine import contains_structured_noise, naturalize_response
from brain.response_mode_engine import ASK_NEXT_FIELD, GENERATE_OUTPUT, determine_response_mode
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)
from brain.workflow_state_machine import cost_calculation_trace


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


def _format_number(value) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.2f}".rstrip("0").rstrip(".")


def _extract_profit_percent(message: str | None) -> float | None:
    text = str(message or "")
    patterns = (
        r"(?:\u0e01\u0e33\u0e44\u0e23|profit|markup)\s*(\d+(?:\.\d+)?)\s*%?",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:\u0e01\u0e33\u0e44\u0e23|profit|markup)?",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def pricing_followup_reply(completed_workflow: dict | None, user_message: str | None = None) -> dict | None:
    fields = (completed_workflow or {}).get("collected_fields") or {}
    trace = cost_calculation_trace(fields)
    cost_per_unit = trace.get("computed_cost_per_unit")
    if cost_per_unit in (None, "", [], {}):
        return None

    base = float(cost_per_unit)
    profit_percent = _extract_profit_percent(user_message)
    if profit_percent is not None:
        selling_price = round(base * (1 + (profit_percent / 100)), 2)
        profit = round(selling_price - base, 2)
        reason = "profit_markup_from_completed_cost"
        reply = (
            f"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 {_format_number(base)} \u0e1a\u0e32\u0e17 "
            f"\u0e16\u0e49\u0e32\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23\u0e01\u0e33\u0e44\u0e23 {_format_number(profit_percent)}% "
            f"\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22\u0e04\u0e37\u0e2d {_format_number(selling_price)} \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\n\n"
            f"\u0e01\u0e33\u0e44\u0e23\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e1b\u0e23\u0e30\u0e21\u0e32\u0e13 {_format_number(profit)} \u0e1a\u0e32\u0e17"
        )
    else:
        selling_price = round(base / 0.65, 2)
        profit = round(selling_price - base, 2)
        reason = "default_35_percent_margin_from_completed_cost"
        reply = (
            f"\u0e08\u0e32\u0e01\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 {_format_number(base)} \u0e1a\u0e32\u0e17 "
            f"\u0e41\u0e19\u0e30\u0e19\u0e33\u0e15\u0e31\u0e49\u0e07\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22\u0e1b\u0e23\u0e30\u0e21\u0e32\u0e13 {_format_number(selling_price)} \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\n\n"
            f"\u0e08\u0e30\u0e40\u0e2b\u0e25\u0e37\u0e2d\u0e01\u0e33\u0e44\u0e23\u0e02\u0e31\u0e49\u0e19\u0e15\u0e49\u0e19\u0e1b\u0e23\u0e30\u0e21\u0e32\u0e13 {_format_number(profit)} \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19"
        )

    return {
        "reply": reply,
        "response_reason": reason,
        "calculation_trace": {
            **trace,
            "requested_profit_percent": profit_percent,
            "computed_selling_price": selling_price,
            "computed_profit_per_unit": profit,
        },
    }


def _content_post_from_fields(fields: dict, *, variant: dict | None = None) -> str:
    variant = variant or {}
    product = fields.get("product") or fields.get("business_type") or "\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32"
    target = fields.get("target_customer") or "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32"
    tone = str(fields.get("tone") or "Friendly")
    if variant.get("short"):
        return (
            f"{product} \u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a{target}\n"
            f"\u0e1e\u0e23\u0e49\u0e2d\u0e21\u0e43\u0e2b\u0e49\u0e25\u0e2d\u0e07\u0e41\u0e25\u0e49\u0e27\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49 "
            f"\u0e17\u0e31\u0e01\u0e41\u0e0a\u0e17\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e2a\u0e31\u0e48\u0e07\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22"
        )
    if variant.get("youth"):
        target = "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19"
    hook = "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a" if variant.get("generate_variant") else "\u0e42\u0e1e\u0e2a\u0e15\u0e4c"
    return (
        f"{hook}\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a{product}\n\n"
        f"\u0e16\u0e49\u0e32{target}\u0e01\u0e33\u0e25\u0e31\u0e07\u0e21\u0e2d\u0e07\u0e2b\u0e32\u0e2d\u0e30\u0e44\u0e23\u0e17\u0e35\u0e48\u0e0b\u0e37\u0e49\u0e2d\u0e07\u0e48\u0e32\u0e22 \u0e43\u0e0a\u0e49\u0e44\u0e14\u0e49\u0e08\u0e23\u0e34\u0e07 \u0e41\u0e25\u0e30\u0e14\u0e39\u0e04\u0e38\u0e49\u0e21 "
        f"{product}\u0e15\u0e31\u0e27\u0e19\u0e35\u0e49\u0e15\u0e2d\u0e1a\u0e42\u0e08\u0e17\u0e22\u0e4c\u0e04\u0e23\u0e31\u0e1a\n\n"
        f"\u0e42\u0e17\u0e19: {tone}\n"
        f"\u0e17\u0e31\u0e01\u0e41\u0e0a\u0e17\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e2a\u0e31\u0e48\u0e07\u0e2b\u0e23\u0e37\u0e2d\u0e16\u0e32\u0e21\u0e23\u0e32\u0e22\u0e25\u0e30\u0e40\u0e2d\u0e35\u0e22\u0e14\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22"
    )


def completed_workflow_followup_reply(
    completed_workflow: dict | None,
    user_message: str | None,
    *,
    workflow_variant_mode: str | None = None,
) -> dict | None:
    completed = completed_workflow or {}
    workflow_id = completed.get("workflow_id")
    fields = dict(completed.get("collected_fields") or {})
    variant = {
        "short": bool(re.search(r"\u0e2a\u0e31\u0e49\u0e19|short", str(user_message or ""), flags=re.IGNORECASE)),
        "youth": bool(re.search(r"\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19|teen|young", str(user_message or ""), flags=re.IGNORECASE)),
        "generate_variant": bool(workflow_variant_mode),
    }

    if workflow_id == WORKFLOW_COST_CALCULATION:
        pricing = pricing_followup_reply(completed, user_message)
        if pricing:
            return {
                **pricing,
                "response_type": "pricing_followup",
                "response_source": "completed_workflow",
                "variant_source": None,
                "composer_trace": ["completed_workflow", "cost_pricing_followup"],
            }
        return None

    if workflow_id == WORKFLOW_CONTENT_PLAN:
        if variant.get("youth"):
            fields["target_customer"] = "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19"
        reply = _content_post_from_fields(fields, variant=variant)
        return {
            "reply": reply,
            "response_type": "content_short_version" if variant.get("short") else "content_variant",
            "response_source": "completed_workflow",
            "response_reason": "summarized_previous_generated_content" if variant.get("short") else "generated_variant_from_completed_content_workflow",
            "variant_source": "previous_completed_content",
            "composer_trace": ["completed_workflow", "content_fields", "short_version" if variant.get("short") else "variant"],
        }

    return None


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
