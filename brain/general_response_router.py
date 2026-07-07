from __future__ import annotations

import re

from brain.task_router import workflow_response_gate


GENERAL_RESPONSE_SOURCE = "general_response"

GENERAL_INTENTS = {
    "general_question",
    "unknown_with_question",
    "label_explanation",
}

GENERAL_TASKS = {
    "General Business Help",
}


def select_general_response_route(route: dict | None, conversation_intent: str | None = None) -> dict:
    """Select executable General Response when Planner did not authorize workflow."""
    route = route or {}
    plan = route.get("planner_output") or {}
    intent_resolution = route.get("intent_resolution") or {}
    business_context = route.get("business_context") or {}
    workflow = plan.get("workflow") or intent_resolution.get("resolved_workflow")
    workflow_decision = (
        route.get("business_workflow")
        or business_context.get("workflow_intelligence")
        or {}
    )
    gate = workflow_response_gate(route)
    planner_authorized_workflow = plan.get("workflow")

    task_type = plan.get("task_type")
    estimated_mode = plan.get("estimated_response_mode")
    resolved_intent = intent_resolution.get("resolved_intent")
    current_message_intent = business_context.get("current_message_intent") or business_context.get("detected_intent")
    detected_intent = ((route.get("detected_intent") or {}).get("detected_intent"))

    general_by_planner = (
        not workflow
        and task_type in GENERAL_TASKS
        and estimated_mode == "llm"
    )
    general_by_intent = (
        resolved_intent in GENERAL_INTENTS
        or current_message_intent in GENERAL_INTENTS
        or detected_intent in GENERAL_INTENTS
        or conversation_intent in {"GENERAL_CHAT", "OTHER"}
    )
    workflow_detected_general = (
        workflow_decision.get("detected_intent") in {"general_business_help", *GENERAL_INTENTS}
        or workflow_decision.get("workflow_reason") in {"general_question", "unknown_with_question"}
    )

    if planner_authorized_workflow:
        return {"handled": False, "reason": "planner_authorized_workflow"}

    if workflow and gate.get("workflow_response_allowed") and not workflow_detected_general:
        return {"handled": False, "reason": "workflow_response_allowed"}

    if general_by_planner or general_by_intent or workflow_detected_general:
        return {
            "handled": True,
            "response_route": GENERAL_RESPONSE_SOURCE,
            "response_mode": "llm",
            "reason": "planner_general_response",
            "task_type": task_type,
            "intent": resolved_intent or current_message_intent or detected_intent or conversation_intent,
        }

    return {"handled": False, "reason": "not_general_response"}

def _build_cost_change_direct_response(user_message: str | None) -> str | None:
    text = str(user_message or "").strip()
    if not text:
        return None

    normalized = text.lower()

    if "ต้นทุน" not in normalized:
        return None

    correction_detected = any(
        marker in normalized
        for marker in ("แก้ใหม่", "จริง ๆ", "จริงๆ", "เท่าเดิม", "ยัง")
    )

    if correction_detected:
        numbers = [float(match.replace(",", "")) for match in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text)]
        if numbers:
            value = numbers[-1]
            if value.is_integer():
                value_text = str(int(value))
            else:
                value_text = f"{value:g}"
            if "เท่าเดิม" in normalized or "ยัง" in normalized:
                return f"รับทราบครับ ผมจะถือว่าต้นทุนที่ถูกต้องคือ {value_text} บาทเท่าเดิม"
            return f"รับทราบครับ ผมจะอัปเดตว่าต้นทุนที่ถูกต้องคือ {value_text} บาท"
        return "รับทราบครับ ผมจะยึดข้อมูลต้นทุนที่แก้ไขล่าสุดนี้เป็นข้อมูลที่ถูกต้อง"

    change_match = re.search(
        r"ต้นทุน\s*(เพิ่ม|ลด|เปลี่ยน)?\s*(?:จาก)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:บาท)?\s*(?:เป็น|เหลือ|ไปเป็น|มาเป็น)\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
        normalized,
    )
    if not change_match:
        return None

    direction_word = change_match.group(1)
    old_value = float(change_match.group(2).replace(",", ""))
    new_value = float(change_match.group(3).replace(",", ""))

    diff = new_value - old_value
    abs_diff = abs(diff)
    percent = (abs_diff / old_value * 100) if old_value else 0

    def fmt(value: float) -> str:
        return str(int(value)) if float(value).is_integer() else f"{value:g}"

    if diff > 0:
        direction = "เพิ่มขึ้น"
    elif diff < 0:
        direction = "ลดลง"
    elif direction_word:
        direction = "ไม่เปลี่ยนแปลง"
    else:
        direction = "เปลี่ยนแปลง"

    if diff == 0:
        return f"รับทราบครับ ต้นทุนยังอยู่ที่ {fmt(new_value)} บาท เท่าเดิม"

    return (
        f"รับทราบครับ ต้นทุนเปลี่ยนจาก {fmt(old_value)} บาทเป็น {fmt(new_value)} บาท "
        f"{direction} {fmt(abs_diff)} บาท หรือประมาณ {percent:.1f}%"
    )


def build_general_direct_response(user_message: str | None) -> str | None:
    """Small deterministic answers for stable general questions when LLM is unavailable."""
    text = str(user_message or "").strip()
    normalized = text.lower()
    if not normalized:
        return None

    cost_change_reply = _build_cost_change_direct_response(user_message)

    if cost_change_reply:
        return cost_change_reply

    if "ประเทศไทย" in normalized and "กี่จังหวัด" in normalized:
        return "ประเทศไทยมี 77 จังหวัดครับ"

    if "เล่าเรื่องแมว" in normalized or "เรื่องแมว" in normalized:
        sentence_count = 2 if re.search(r"\b2\b|๒|สอง", normalized) else 3
        sentences = [
            "แมวตัวหนึ่งชอบนั่งมองแดดยามเช้าตรงขอบหน้าต่าง",
            "ทุกครั้งที่เจ้าของกลับบ้าน มันจะเดินมาคลอเคลียเหมือนเล่าเรื่องทั้งวันให้ฟัง",
            "คืนหนึ่งมันพบกล่องใบใหม่และตัดสินใจว่านั่นคือปราสาทส่วนตัวของมัน",
        ]
        return " ".join(sentences[:sentence_count])

    return None
