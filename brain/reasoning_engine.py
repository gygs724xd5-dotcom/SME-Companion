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


def _contains_any(message: str, terms: list[str]) -> bool:
    lowered = str(message or "").strip().lower()
    return any(term.lower() in lowered for term in terms)


def build_reasoning(application_state, user_message):
    state = application_state or {}
    receipt = state.get("receipt") or {}
    workflow = state.get("workflow") or {}
    developer = state.get("developer") or {}
    ui = state.get("ui") or {}

    receipt_uploaded = bool(receipt.get("receipt_uploaded"))
    workflow_ready = bool(workflow.get("is_ready") or (workflow.get("workflow_state_v2") or {}).get("is_ready"))
    current_workflow = (
        workflow.get("workflow")
        or workflow.get("current_workflow")
        or (workflow.get("workflow_state_v2") or {}).get("workflow")
    )
    llm_mode = ui.get("llm_response_mode") or developer.get("llm_response_mode") or "Workflow Only"

    result = {
        "action": "default_chat",
        "reason": "No higher-priority application state matched.",
        "workflow": current_workflow,
        "response_mode": "default_chat",
        "llm_needed": llm_mode == "LLM Only",
        "workflow_ready": workflow_ready,
    }

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
                "llm_needed": llm_mode == "Workflow + LLM",
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

    if llm_mode == "LLM Only":
        result.update(
            {
                "action": "llm",
                "reason": "Developer mode selected LLM Only response mode.",
                "response_mode": "llm",
                "llm_needed": True,
            }
        )
        return result

    return result

