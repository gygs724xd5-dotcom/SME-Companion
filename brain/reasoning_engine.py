from __future__ import annotations


RECEIPT_CONFIRMATION_TERMS = [
    "ส่งแล้ว",
    "เห็นไหม",
    "อัปโหลดแล้ว",
    "upload",
    "uploaded",
]

RECEIPT_ANALYSIS_TERMS = [
    "คำนวณต้นทุน",
    "คำนวนต้นทุน",
    "อ่านบิล",
    "วิเคราะห์บิล",
    "ต้นทุน",
    "กำไร",
]

BUSINESS_REASONING_CONFIDENCE_THRESHOLD = 0.6


def _contains_any(message: str, terms: list[str]) -> bool:
    lowered = str(message or "").strip().lower()
    return any(term.lower() in lowered for term in terms)


def build_reasoning(application_state, user_message):
    state = application_state or {}
    receipt = state.get("receipt") or {}
    workflow = state.get("workflow") or {}
    developer = state.get("developer") or {}
    business_intelligence = (
        state.get("business_intelligence")
        or ((state.get("conversation") or {}).get("business_intelligence"))
        or {}
    )

    receipt_uploaded = bool(receipt.get("receipt_uploaded"))
    workflow_ready = bool(workflow.get("is_ready") or (workflow.get("workflow_state_v2") or {}).get("is_ready"))
    current_workflow = (
        workflow.get("workflow")
        or workflow.get("current_workflow")
        or (workflow.get("workflow_state_v2") or {}).get("workflow")
    )
    result = {
        "action": "default_chat",
        "reason": "No higher-priority application state matched.",
        "workflow": current_workflow,
        "response_mode": "default_chat",
        "llm_needed": False,
        "workflow_ready": workflow_ready,
    }

    if (
        business_intelligence.get("bridge_used")
        and float(business_intelligence.get("confidence") or 0.0) >= BUSINESS_REASONING_CONFIDENCE_THRESHOLD
    ):
        business_reasoning = business_intelligence.get("business_reasoning") or {}
        result.update(
            {
                "action": "business_reasoning",
                "reason": business_reasoning.get("reasoning_summary") or "Business Intelligence Bridge matched a business skill.",
                "workflow": business_intelligence.get("workflow") or current_workflow,
                "response_mode": business_intelligence.get("response_mode") or business_reasoning.get("response_mode") or "business_reasoning",
                "llm_needed": True,
                "business_skill_id": ((business_intelligence.get("matched_skill") or {}).get("skill_id")),
                "matched_skill": business_intelligence.get("matched_skill"),
                "matched_domain": business_intelligence.get("matched_domain"),
                "business_reasoning": business_reasoning,
                "business_principle": business_intelligence.get("business_principle"),
                "thinking_pattern": business_intelligence.get("thinking_pattern"),
                "decision_tree": business_intelligence.get("decision_tree") or [],
                "questions_to_ask": business_intelligence.get("questions_to_ask") or [],
                "memory_tags": business_intelligence.get("memory_tags") or [],
                "confidence": business_intelligence.get("confidence"),
                "bridge_used": True,
                "fallback_used": False,
            }
        )
        return result

    if receipt_uploaded and _contains_any(user_message, RECEIPT_CONFIRMATION_TERMS):
        result.update(
            {
                "action": "receipt_uploaded_ack",
                "reason": "Receipt already exists in shared application state.",
                "workflow": "RECEIPT_CAPTURE",
                "response_mode": "deterministic_receipt",
                "llm_needed": False,
            }
        )
        return result

    if receipt_uploaded and _contains_any(user_message, RECEIPT_ANALYSIS_TERMS):
        result.update(
            {
                "action": "receipt_ocr_pending",
                "reason": "Receipt is uploaded but OCR and analysis hooks are not implemented.",
                "workflow": "RECEIPT_CAPTURE",
                "response_mode": "deterministic_receipt",
                "llm_needed": False,
            }
        )
        return result

    if workflow_ready:
        result.update(
            {
                "action": "continue_workflow",
                "reason": "Workflow has enough information to generate a deterministic result.",
                "response_mode": "workflow",
                "llm_needed": False,
            }
        )
        return result

    if current_workflow:
        result.update(
            {
                "action": "continue_workflow",
                "reason": "An active workflow is present in shared application state.",
                "response_mode": "workflow",
                "llm_needed": False,
            }
        )
        return result

    if developer.get("developer_mode") and developer.get("developer_intent"):
        result.update(
            {
                "action": "developer_intelligence",
                "reason": "Developer mode has an explicit developer intent.",
                "response_mode": "developer",
                "llm_needed": False,
            }
        )
        return result

    return result
