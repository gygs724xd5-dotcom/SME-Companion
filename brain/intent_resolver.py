from __future__ import annotations

from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_SALES_PLAN_7_DAY,
)


INTENT_TO_PLANNER_MESSAGE = {
    "business_context_update": "update business context",
    "business_planning": "business dashboard daily business planning",
    "content_planning": "content plan create content",
    "marketing_strategy": "marketing campaign strategy",
    "sales_planning": "sales plan increase sales",
    "pricing_question": "sales plan pricing recommendation",
    "cost_calculation": "cost calculation unit cost profit margin",
    "continue_previous_workflow": "continue previous workflow",
    "follow_up_edit": "continue previous output edit",
    "reference_resolution": "resolve previous conversation reference",
    "general_business_help": "general business help",
}

FOLLOW_UP_TERMS = ["ทำต่อ", "ต่อเลย", "ไปต่อ", "ช่วยต่อ", "continue"]
VARIANT_TERMS = ["ขออีกแบบ", "อีกแบบ", "อีกอัน", "แบบใหม่"]
SHORTEN_TERMS = ["ย่อให้สั้น", "สั้นลง", "สรุปสั้น", "ขอสั้น"]
EMOJI_TERMS = ["เพิ่มอีโมจิ", "ใส่อีโมจิ", "emoji"]
TRANSLATE_TERMS = ["แปล", "translate", "ภาษาอังกฤษ", "ภาษาไทย"]
PROFESSIONAL_TERMS = ["มืออาชีพ", "professional", "ทางการ"]
REFERENCE_TERMS = ["อันนี้", "ตัวนี้", "แบบเดิม", "อันบน", "ข้างบน", "อันนั้น"]
CONTEXT_UPDATE_TERMS = ["ร้านขายชา", "ร้านชา", "ชานม", "ชาไทย", "ร้านกาแฟ", "ร้านอาหาร", "ร้านขนม", "เบเกอรี่"]
EXTRA_CONTEXT_UPDATE_TERMS = ["\u0e23\u0e49\u0e32\u0e19\u0e02\u0e32\u0e22\u0e04\u0e23\u0e35\u0e21", "\u0e23\u0e49\u0e32\u0e19\u0e04\u0e23\u0e35\u0e21", "\u0e04\u0e23\u0e35\u0e21", "cosmetic store", "beauty shop"]
PRICE_TERMS = ["ราคาเท่าไร", "เท่าไร", "กี่บาท", "ขายเท่าไร", "ตั้งราคา"]
TODAY_TERMS = ["วันนี้ควรทำอะไร", "วันนี้ทำอะไร", "ทำอะไรดีวันนี้", "ควรทำอะไร"]
CONTENT_TERMS = ["โพสต์", "คอนเทนต์", "แคปชั่น", "caption", "content"]
MARKETING_TERMS = ["โปร", "โปรโมชัน", "โปรโมชั่น", "แคมเปญ", "campaign"]
SALES_TERMS = ["ยอดขาย", "เพิ่มยอด", "ขายดีขึ้น", "ขายอะไรดี", "ไม่มีออเดอร์"]
COST_TERMS = ["ต้นทุน", "กำไร", "margin", "cost"]


def _contains_any(message: str, terms: list[str]) -> bool:
    lowered = str(message or "").strip().lower()
    return any(term.lower() in lowered for term in terms)


def _active_workflow(memory: dict | None) -> str | None:
    return (memory or {}).get("last_workflow") or (memory or {}).get("previous_workflow")


def _add(scores: dict[str, int], intent: str, amount: int) -> None:
    scores[intent] = min(99, scores.get(intent, 0) + amount)


def _workflow_for_intent(intent: str, memory: dict | None) -> str | None:
    if intent == "business_planning":
        return WORKFLOW_DASHBOARD_REQUEST
    if intent == "content_planning":
        return WORKFLOW_CONTENT_PLAN
    if intent in {"sales_planning", "pricing_question"}:
        return WORKFLOW_SALES_PLAN_7_DAY
    if intent == "cost_calculation":
        return WORKFLOW_COST_CALCULATION
    if intent in {"continue_previous_workflow", "follow_up_edit"}:
        return _active_workflow(memory)
    return None


def _planner_message(intent: str, message: str, memory: dict | None, business_context: dict | None) -> str:
    base = INTENT_TO_PLANNER_MESSAGE.get(intent) or str(message or "").strip()
    workflow = _workflow_for_intent(intent, memory)
    business_type = (business_context or {}).get("business_type")
    product = (business_context or {}).get("current_product")
    topic = (business_context or {}).get("current_discussion_topic")
    parts = [base]
    if workflow:
        parts.append(str(workflow))
    if business_type:
        parts.append(f"business_type={business_type}")
    if product:
        parts.append(f"product={product}")
    if topic:
        parts.append(f"topic={topic}")
    return " ".join(parts)


def _reference_resolution(message: str, memory: dict | None) -> dict:
    if not _contains_any(message, REFERENCE_TERMS + FOLLOW_UP_TERMS + VARIANT_TERMS):
        return {}
    if _contains_any(message, ["อันบน", "ข้างบน"]):
        target = "last_assistant_reply"
    elif _contains_any(message, FOLLOW_UP_TERMS):
        target = "last_workflow"
    else:
        target = "last_assistant_reply"
    return {
        "target": target,
        "value": (memory or {}).get(target),
        "last_user_message": (memory or {}).get("last_user_message"),
    }


def resolve_intent(
    understanding: dict | None,
    conversation_memory: dict | None,
    business_context: dict | None,
) -> dict:
    """Score possible intents from understanding, memory, and business context."""
    message = (understanding or {}).get("raw_text") or ""
    detected = (understanding or {}).get("detected_intent")
    memory = conversation_memory or {}
    context = business_context or {}
    scores: dict[str, int] = {"general_business_help": 35}

    if context.get("business_type") or context.get("current_product"):
        _add(scores, "business_planning", 28)
        _add(scores, "content_planning", 18)
        _add(scores, "marketing_strategy", 14)
        if _contains_any(message, CONTEXT_UPDATE_TERMS + EXTRA_CONTEXT_UPDATE_TERMS) and not any(
            _contains_any(message, terms)
            for terms in [
                TODAY_TERMS,
                CONTENT_TERMS,
                MARKETING_TERMS,
                SALES_TERMS,
                PRICE_TERMS,
                COST_TERMS,
                FOLLOW_UP_TERMS,
                VARIANT_TERMS,
                SHORTEN_TERMS,
                EMOJI_TERMS,
                TRANSLATE_TERMS,
                PROFESSIONAL_TERMS,
                REFERENCE_TERMS,
            ]
        ):
            _add(scores, "business_context_update", 62)

    if detected == "pricing_question" or _contains_any(message, PRICE_TERMS):
        _add(scores, "pricing_question", 58)
        _add(scores, "sales_planning", 35)
    if detected == "cost_question" or _contains_any(message, COST_TERMS):
        _add(scores, "cost_calculation", 62)
    if detected == "continue_previous_workflow" or _contains_any(message, FOLLOW_UP_TERMS):
        _add(scores, "continue_previous_workflow", 62 if _active_workflow(memory) else 42)
    if _contains_any(message, VARIANT_TERMS + SHORTEN_TERMS + EMOJI_TERMS + TRANSLATE_TERMS + PROFESSIONAL_TERMS):
        _add(scores, "follow_up_edit", 66 if memory.get("last_assistant_reply") else 45)
    if _contains_any(message, REFERENCE_TERMS):
        _add(scores, "reference_resolution", 58 if memory.get("last_assistant_reply") else 34)
        if _contains_any(message, PRICE_TERMS):
            _add(scores, "pricing_question", 35)
    if _contains_any(message, TODAY_TERMS):
        _add(scores, "business_planning", 54)
        _add(scores, "content_planning", 41)
        _add(scores, "marketing_strategy", 26)
    if _contains_any(message, CONTENT_TERMS):
        _add(scores, "content_planning", 58)
    if _contains_any(message, MARKETING_TERMS):
        _add(scores, "marketing_strategy", 58)
    if _contains_any(message, SALES_TERMS):
        _add(scores, "sales_planning", 55)
    if context.get("current_goal") == "today_action":
        _add(scores, "business_planning", 22)
    if context.get("current_goal") == "create_content":
        _add(scores, "content_planning", 20)
    if context.get("current_goal") == "set_price":
        _add(scores, "pricing_question", 22)

    if detected in {"store_summary", "business_status"}:
        _add(scores, "business_planning", 45)
    elif detected in {"receipt_reference", "image_reference"}:
        _add(scores, "reference_resolution", 35)
    elif detected and detected != "unknown":
        _add(scores, "general_business_help", 10)

    candidates = sorted(
        [{"intent": intent, "score": score} for intent, score in scores.items()],
        key=lambda item: item["score"],
        reverse=True,
    )
    winner = candidates[0] if candidates else {"intent": "general_business_help", "score": 35}
    confidence_score = max(0.0, min(0.99, winner["score"] / 100))
    if confidence_score >= 0.75:
        confidence = "HIGH"
    elif confidence_score >= 0.55:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    resolved_intent = winner["intent"]
    return {
        "resolved_intent": resolved_intent,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "alternative_candidates": candidates[1:4],
        "candidates": candidates,
        "resolved_workflow": _workflow_for_intent(resolved_intent, memory),
        "resolved_references": _reference_resolution(message, memory),
        "planner_message": _planner_message(resolved_intent, message, memory, context),
        "source": "conversation_intelligence",
    }
