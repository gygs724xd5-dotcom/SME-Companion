from __future__ import annotations

from feedback.product_classifier import classify_product_feedback


WORKFLOW_COST_CALCULATION = "WORKFLOW_COST_CALCULATION"
WORKFLOW_DASHBOARD_REQUEST = "WORKFLOW_DASHBOARD_REQUEST"
WORKFLOW_RECEIPT_CAPTURE = "WORKFLOW_RECEIPT_CAPTURE"
WORKFLOW_CONTENT_PLAN = "WORKFLOW_CONTENT_PLAN"
WORKFLOW_SALES_ANALYSIS = "WORKFLOW_SALES_ANALYSIS"
WORKFLOW_PRODUCT_FEEDBACK = "WORKFLOW_PRODUCT_FEEDBACK"


WORKFLOW_TRIGGERS = {
    WORKFLOW_COST_CALCULATION: [
        "คำนวณต้นทุน",
        "ต้นทุนต่อชิ้น",
        "กำไรต่อชิ้น",
        "ราคาขาย",
        "margin",
        "มาร์จิ้น",
        "ขายได้กี่ชิ้น",
        "ต้นทุนขนม",
        "ต้นทุนอาหาร",
    ],
    WORKFLOW_DASHBOARD_REQUEST: [
        "อยากได้แดชบอร์ด",
        "สร้างแดชบอร์ด",
        "dashboard ร้าน",
        "แดชบอร์ดร้านค้า",
    ],
    WORKFLOW_RECEIPT_CAPTURE: [
        "ส่งบิล",
        "อ่านบิล",
        "ถ่ายบิล",
        "อัปโหลดบิล",
        "ใบเสร็จ",
        "สลิป",
        "ถ่ายสลิป",
        "รูปบิล",
        "ส่งรูป",
    ],
    WORKFLOW_CONTENT_PLAN: [
        "โพสต์อะไรดี",
        "คิดคอนเทนต์",
        "แคปชั่น",
        "โปรโมชัน",
        "ขายยังไง",
    ],
    WORKFLOW_SALES_ANALYSIS: [
        "ยอดขาย",
        "ขายไม่ดี",
        "ไม่มีลูกค้า",
        "ลูกค้าไม่เข้า",
        "เพิ่มยอดขาย",
    ],
}


def _normalize(message: str) -> str:
    return str(message or "").strip().lower()


def _trigger_score(message: str, triggers: list[str]) -> tuple[int, str | None]:
    matched = [trigger for trigger in triggers if trigger in message]
    if not matched:
        return 0, None
    return len(matched), max(matched, key=len)


def detect_workflow(user_message: str, is_product_feedback: bool = False) -> dict:
    message = _normalize(user_message)
    if not message:
        return {
            "workflow": None,
            "confidence": 0.0,
            "should_skip_generic_companion": False,
        }

    best_workflow = None
    best_count = 0
    best_trigger = None
    for workflow, triggers in WORKFLOW_TRIGGERS.items():
        count, trigger = _trigger_score(message, triggers)
        if count > best_count or (count == best_count and trigger and best_trigger and len(trigger) > len(best_trigger)):
            best_workflow = workflow
            best_count = count
            best_trigger = trigger

    if not best_workflow:
        if is_product_feedback:
            classification = classify_product_feedback(message)
            return {
                "workflow": WORKFLOW_PRODUCT_FEEDBACK,
                "confidence": 0.95 if classification.get("category") != "Other" else 0.8,
                "should_skip_generic_companion": True,
            }
        return {
            "workflow": None,
            "confidence": 0.0,
            "should_skip_generic_companion": False,
        }

    confidence = min(0.95, 0.7 + (0.1 * best_count))
    if best_trigger and len(best_trigger) >= 10:
        confidence = min(0.98, confidence + 0.1)

    return {
        "workflow": best_workflow,
        "confidence": confidence,
        "should_skip_generic_companion": best_workflow
        in {
            WORKFLOW_COST_CALCULATION,
            WORKFLOW_DASHBOARD_REQUEST,
            WORKFLOW_RECEIPT_CAPTURE,
            WORKFLOW_PRODUCT_FEEDBACK,
        },
    }
