from __future__ import annotations

from copy import deepcopy

from brain.conversation_intent_engine import (
    BUSINESS_ANALYSIS,
    FOLLOW_UP,
    GENERAL_CHAT,
    GREETING,
    OTHER,
    SALES,
)


HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"

CAPABILITY_DISCOVERY = "capability_discovery"
STORE_SUMMARY = "store_summary"
BUSINESS_STATUS = "business_status"
CONTINUE_PREVIOUS_WORKFLOW = "continue_previous_workflow"
IMAGE_REFERENCE = "image_reference"
RECEIPT_REFERENCE = "receipt_reference"
PRICING_QUESTION = "pricing_question"
COST_QUESTION = "cost_question"
GREETING_INTENT = "greeting"
EXPLANATION_REQUEST = "explanation_request"
FOLLOW_UP_REFERENCE = "follow_up_reference"
UNKNOWN = "unknown"


_CAPABILITY_KEYWORDS = [
    "ช่วยอะไรได้บ้าง",
    "ทำอะไรได้บ้าง",
    "whatทำได้บ้าง",
    "what can you do",
    "capabilities",
    "ความสามารถ",
]
_STORE_SUMMARY_KEYWORDS = [
    "ร้านนี้มีอะไร",
    "ร้านนี้เป็นยังไง",
    "ร้านผมขายอะไร",
    "ร้านฉันขายอะไร",
    "ร้านผมเป็นยังไง",
    "ร้านเราเป็นยังไง",
]
_BUSINESS_STATUS_KEYWORDS = ["ร้านเป็นยังไง", "ธุรกิจตอนนี้โอเคไหม", "ธุรกิจโอเคไหม", "คะแนนต่ำ", "ทำไมคะแนนต่ำ"]
_CONTINUE_KEYWORDS = ["ต่อ", "ช่วยต่อ", "ทำต่อ", "ไปต่อ", "continue", "ต่อเลย"]
_IMAGE_KEYWORDS = ["ดูในรูป", "ดูภาพนี้", "รูปนี้", "ภาพนี้", "รูปล่าสุด", "ภาพล่าสุด"]
_RECEIPT_KEYWORDS = ["ใบเสร็จนี้", "ราคาจากบิล", "ต้นทุนจากบิล", "บิลนี้", "สลิปนี้", "receipt"]
_PRICING_KEYWORDS = ["ราคาเท่าไร", "ขายเท่าไรดี", "ตั้งราคา", "ราคาขาย", "price"]
_COST_KEYWORDS = ["ต้นทุนเท่าไร", "กำไรเท่าไร", "คำนวณต้นทุน", "margin", "cost"]
_GREETING_KEYWORDS = ["สวัสดี", "หวัดดี", "hello", "hi"]
_GREETING_EXACT = {"ไง", "ดีไหม"}
_EXPLAIN_KEYWORDS = ["ช่วยอธิบายหน่อย", "อธิบายหน่อย", "ทำไม", "เพราะอะไร", "แปลว่าอะไร"]
_REFERENCE_KEYWORDS = ["อันนี้", "อันนั้น", "มัน", "เขา", "ล่าสุด", "เรื่องนี้"]


def _normalize(message: str) -> str:
    return str(message or "").strip().lower()


def _contains_any(message: str, keywords: list[str]) -> bool:
    return any(keyword in message for keyword in keywords)


def _clean_dict(data: dict | None) -> dict:
    return {key: value for key, value in (data or {}).items() if value not in (None, "", [], {})}


def _store_profile(application_state: dict) -> dict:
    store = (application_state or {}).get("store") or {}
    if isinstance(store.get("profile"), dict):
        return store.get("profile") or {}
    return store


def _latest_assistant_message(chat_history: list[dict]) -> str | None:
    for message in reversed(chat_history or []):
        if message.get("role") == "assistant" and message.get("content"):
            return str(message.get("content"))
    return None


def _active_workflow(application_state: dict) -> dict:
    workflow = (application_state or {}).get("workflow") or {}
    workflow_state = workflow.get("workflow_state_v2") or {}
    return _clean_dict(
        {
            "workflow": workflow_state.get("workflow") or workflow.get("workflow") or workflow.get("current_workflow"),
            "step": workflow_state.get("step") or workflow.get("step") or workflow.get("workflow_step"),
            "missing_fields": workflow_state.get("missing_fields"),
            "is_ready": workflow_state.get("is_ready") or workflow.get("is_ready"),
        }
    )


def _receipt_reference(application_state: dict) -> dict:
    receipt = (application_state or {}).get("receipt") or {}
    return _clean_dict(
        {
            "available": bool(receipt.get("receipt_uploaded")),
            "filename": receipt.get("receipt_filename"),
            "uploaded_time": receipt.get("receipt_uploaded_time"),
            "ocr_status": receipt.get("ocr_status"),
            "analysis_status": receipt.get("analysis_status"),
            "state": receipt.get("state"),
        }
    )


def _detect_intent(message: str, application_state: dict) -> tuple[str, str, float]:
    if not message:
        return UNKNOWN, LOW, 0.1
    if _contains_any(message, _CAPABILITY_KEYWORDS):
        return CAPABILITY_DISCOVERY, HIGH, 0.96
    if _contains_any(message, _RECEIPT_KEYWORDS):
        receipt = _receipt_reference(application_state)
        return RECEIPT_REFERENCE, HIGH if receipt.get("available") else MEDIUM, 0.9 if receipt.get("available") else 0.68
    if _contains_any(message, _IMAGE_KEYWORDS):
        receipt = _receipt_reference(application_state)
        return IMAGE_REFERENCE, HIGH if receipt.get("available") else MEDIUM, 0.88 if receipt.get("available") else 0.64
    if message in _CONTINUE_KEYWORDS or _contains_any(message, _CONTINUE_KEYWORDS):
        workflow = _active_workflow(application_state)
        return CONTINUE_PREVIOUS_WORKFLOW, HIGH if workflow.get("workflow") else MEDIUM, 0.9 if workflow.get("workflow") else 0.65
    if _contains_any(message, _STORE_SUMMARY_KEYWORDS):
        profile = _store_profile(application_state)
        return STORE_SUMMARY, HIGH if profile else MEDIUM, 0.88 if profile else 0.62
    if _contains_any(message, _BUSINESS_STATUS_KEYWORDS):
        return BUSINESS_STATUS, HIGH, 0.86
    if _contains_any(message, _PRICING_KEYWORDS):
        return PRICING_QUESTION, HIGH, 0.86
    if _contains_any(message, _COST_KEYWORDS):
        return COST_QUESTION, HIGH, 0.88
    if message in _GREETING_EXACT or message in _GREETING_KEYWORDS or _contains_any(message, _GREETING_KEYWORDS):
        return GREETING_INTENT, HIGH, 0.95
    if _contains_any(message, _EXPLAIN_KEYWORDS):
        return EXPLANATION_REQUEST, MEDIUM, 0.72
    if message in _REFERENCE_KEYWORDS or _contains_any(message, _REFERENCE_KEYWORDS):
        history = ((application_state or {}).get("conversation") or {}).get("chat_history") or []
        return FOLLOW_UP_REFERENCE, MEDIUM if history else LOW, 0.7 if history else 0.35
    return UNKNOWN, LOW, 0.25


def _legacy_intent(intent: str) -> str:
    return {
        CAPABILITY_DISCOVERY: GENERAL_CHAT,
        STORE_SUMMARY: BUSINESS_ANALYSIS,
        BUSINESS_STATUS: BUSINESS_ANALYSIS,
        CONTINUE_PREVIOUS_WORKFLOW: FOLLOW_UP,
        IMAGE_REFERENCE: GENERAL_CHAT,
        RECEIPT_REFERENCE: GENERAL_CHAT,
        PRICING_QUESTION: SALES,
        COST_QUESTION: SALES,
        GREETING_INTENT: GREETING,
        EXPLANATION_REQUEST: GENERAL_CHAT,
        FOLLOW_UP_REFERENCE: FOLLOW_UP,
    }.get(intent, OTHER)


def _planner_message(intent: str, user_message: str, application_state: dict) -> str:
    workflow = _active_workflow(application_state).get("workflow")
    if intent == STORE_SUMMARY:
        return "business dashboard store overview"
    if intent == BUSINESS_STATUS:
        return "business dashboard business health score"
    if intent == RECEIPT_REFERENCE:
        return "receipt upload read latest receipt"
    if intent == IMAGE_REFERENCE:
        return "receipt upload read latest uploaded image"
    if intent == COST_QUESTION:
        return "cost calculation unit cost profit margin"
    if intent == PRICING_QUESTION:
        return "sales plan pricing recommendation"
    if intent == CONTINUE_PREVIOUS_WORKFLOW and workflow:
        return f"continue active workflow {workflow}"
    if intent == CAPABILITY_DISCOVERY:
        return "general business help capability discovery"
    return str(user_message or "").strip()


def _resolved_references(intent: str, application_state: dict) -> dict:
    conversation = (application_state or {}).get("conversation") or {}
    history = conversation.get("chat_history") or []
    receipt = _receipt_reference(application_state)
    references = {
        "store": _clean_dict(_store_profile(application_state)),
        "active_workflow": _active_workflow(application_state),
        "latest_assistant_message": _latest_assistant_message(history),
        "receipt": receipt,
        "conversation_topic": conversation.get("current_topic"),
        "recent_planner_output": ((application_state or {}).get("developer") or {}).get("planner_output"),
    }
    if intent == IMAGE_REFERENCE and receipt:
        references["latest_uploaded_file"] = deepcopy(receipt)
    return _clean_dict(references)


def understand_conversation(user_message: str, application_state: dict | None = None) -> dict:
    """Normalize one user turn into a structured interpretation for planning."""
    state = application_state or {}
    normalized = _normalize(user_message)
    intent, confidence, score = _detect_intent(normalized, state)
    resolved = _resolved_references(intent, state)
    referenced_objects = []
    for key in ["store", "active_workflow", "latest_uploaded_file", "receipt", "latest_assistant_message"]:
        if resolved.get(key):
            referenced_objects.append(key)

    needs_clarification = confidence == LOW
    clarification_question = None
    if needs_clarification:
        clarification_question = "อยากให้ผมช่วยเรื่องร้าน คอนเทนต์ ราคา หรือต้นทุนครับ?"

    return {
        "raw_text": str(user_message or ""),
        "normalized_text": normalized,
        "planner_message": _planner_message(intent, user_message, state),
        "detected_intent": intent,
        "legacy_intent": _legacy_intent(intent),
        "referenced_objects": referenced_objects,
        "resolved_references": resolved,
        "conversation_context": _clean_dict(
            {
                "current_topic": ((state.get("conversation") or {}).get("current_topic")),
                "previous_intent": ((state.get("conversation") or {}).get("previous_intent")),
                "last_intent": ((state.get("conversation") or {}).get("last_intent")),
            }
        ),
        "store_context": _clean_dict(_store_profile(state)),
        "confidence": confidence,
        "confidence_score": score,
        "clarification_required": needs_clarification,
        "clarification_question": clarification_question,
    }


def should_answer_directly(interpretation: dict | None) -> bool:
    intent = (interpretation or {}).get("detected_intent")
    confidence = (interpretation or {}).get("confidence")
    return intent in {
        CAPABILITY_DISCOVERY,
        STORE_SUMMARY,
        BUSINESS_STATUS,
        IMAGE_REFERENCE,
        RECEIPT_REFERENCE,
        EXPLANATION_REQUEST,
        FOLLOW_UP_REFERENCE,
    } and confidence in {HIGH, MEDIUM}


def build_direct_reply(
    interpretation: dict,
    profile: dict | None = None,
    diagnosis: dict | None = None,
    goal_status: dict | None = None,
    business_os_state: dict | None = None,
) -> str | None:
    intent = (interpretation or {}).get("detected_intent")
    refs = (interpretation or {}).get("resolved_references") or {}
    store = profile or refs.get("store") or {}
    store_name = store.get("store_name") or "ร้านของคุณ"
    store_type = store.get("store_type") or "ธุรกิจนี้"
    product = store.get("product") or "สินค้า/บริการหลัก"
    target = store.get("target_customer") or "ลูกค้าเป้าหมาย"

    if intent == CAPABILITY_DISCOVERY:
        return (
            "ผมช่วย SME ได้หลักๆ 6 เรื่องครับ\n\n"
            "1. สรุปภาพรวมร้านและสถานะธุรกิจ\n"
            "2. คิดคอนเทนต์ แคปชัน โปรโมชัน และแผนขาย\n"
            "3. ช่วยตั้งราคาและคิดมุมขายจากข้อมูลร้าน\n"
            "4. ช่วยคำนวณต้นทุน/กำไรเมื่อมีตัวเลขวัตถุดิบหรือบิล\n"
            "5. จำบริบทบทสนทนา เช่น ต่อจากงานเดิม รูปนี้ บิลล่าสุด\n"
            "6. รับฟีดแบ็กเกี่ยวกับระบบเพื่อส่งต่อเป็นข้อมูลพัฒนา\n\n"
            "ถามมาแบบสั้นๆ ได้เลย เช่น ร้านนี้เป็นยังไง, ขายเท่าไรดี, ต้นทุนเท่าไร, หรือช่วยต่อ"
        )
    if intent == STORE_SUMMARY:
        return (
            f"จากข้อมูลที่มีตอนนี้ {store_name} เป็น{store_type} ขาย {product} ให้กลุ่ม {target}\n\n"
            "ภาพรวมที่ควรใช้คุยกับลูกค้าคือทำให้เห็นชัดว่า สินค้าช่วยแก้ปัญหาอะไร เหมาะกับใคร และทำไมควรซื้อจากร้านนี้\n\n"
            "ถ้าจะเดินหน้าต่อ ผมแนะนำให้ดู 3 จุดก่อน: สินค้าหลักที่ควรดัน, ข้อเสนอที่ทำให้ตัดสินใจง่าย, และคอนเทนต์ที่สร้างความเชื่อมั่น"
        )
    if intent == BUSINESS_STATUS:
        urgency = (diagnosis or {}).get("urgency_level")
        recommended = (diagnosis or {}).get("recommended_fix") or (business_os_state or {}).get("today_action")
        goal = (goal_status or {}).get("goal_label") or (business_os_state or {}).get("active_goal")
        lines = [f"ตอนนี้ผมมอง {store_name} จากข้อมูลร้านและสัญญาณธุรกิจที่มีครับ"]
        if urgency:
            lines.append(f"ระดับที่ควรโฟกัส: {urgency}")
        if goal:
            lines.append(f"เป้าหมายปัจจุบัน: {goal}")
        if recommended:
            lines.append(f"สิ่งที่ควรทำก่อน: {recommended}")
        if len(lines) == 1:
            lines.append("ยังไม่มีสัญญาณตัวเลขครบพอให้ฟันธง แต่จากโปรไฟล์ร้านควรเริ่มจากทำข้อเสนอและคอนเทนต์ให้ลูกค้าเข้าใจคุณค่าของสินค้าหลักก่อน")
        return "\n\n".join(lines)
    if intent in {IMAGE_REFERENCE, RECEIPT_REFERENCE}:
        receipt = refs.get("receipt") or {}
        if receipt.get("available"):
            filename = receipt.get("filename") or "ไฟล์ล่าสุด"
            return (
                f"เจอไฟล์ล่าสุดแล้วครับ: {filename}\n\n"
                "ตอนนี้ระบบบันทึกไฟล์ไว้แล้ว แต่ OCR ยังเป็นขั้นรออ่านข้อมูล ดังนั้นผมยังไม่ควรสรุปตัวเลขจากรูปแบบฟันธง\n\n"
                "ถ้าต้องการคำนวณตอนนี้ ส่งตัวเลขรายการสินค้า/วัตถุดิบกับยอดรวมมาได้เลย ผมจะช่วยคิดต้นทุนหรือกำไรต่อให้"
            )
        return "ยังไม่เจอรูปหรือบิลล่าสุดในระบบครับ ส่งไฟล์ที่ช่องอัปโหลดบิล/สลิปก่อน แล้วพิมพ์ว่า ดูในรูป หรือ ต้นทุนจากบิล ได้เลย"
    if intent == EXPLANATION_REQUEST:
        latest = refs.get("latest_assistant_message")
        if latest:
            return "ได้ครับ สรุปให้ง่ายขึ้นคือ คำตอบก่อนหน้ากำลังชี้ว่าให้เริ่มจากจุดที่เปลี่ยนผลลัพธ์เร็วที่สุดก่อน แล้วค่อยทำขั้นต่อไปจากข้อมูลที่มี"
        return "ได้ครับ ผมอธิบายได้ แต่ขออ้างอิงจากเรื่องล่าสุดในร้านก่อน: เราจะดูว่าเป้าหมายคือยอดขาย ต้นทุน ราคา หรือคอนเทนต์ แล้วตอบเฉพาะจุดนั้น"
    if intent == FOLLOW_UP_REFERENCE:
        latest = refs.get("latest_assistant_message")
        if latest:
            return "อันนี้ผมอ้างอิงจากคำตอบล่าสุดครับ ถ้าจะต่อให้เป็นงานใช้งานจริง ขั้นถัดไปคือเลือกว่าจะให้ผมทำเป็นแผนขาย แคปชัน โปร หรือคำนวณต้นทุน"
        return "ยังไม่มีเรื่องก่อนหน้าให้ผมอ้างอิงชัดเจนครับ ถามเป็นเรื่องร้าน ราคา ต้นทุน หรือคอนเทนต์ได้เลย"
    return None
