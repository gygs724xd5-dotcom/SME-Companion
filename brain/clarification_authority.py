from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


CLARIFICATION_AUTHORITY_VERSION = "5.8.4"
CLARIFICATION_RESPONSE_SOURCE = "clarification_authority"
SITUATION_AWARE_CLARIFICATION_MODE = "SITUATION_AWARE_CLARIFICATION"


class ClarificationDecision(str, Enum):
    USE_SPECIFIC_CLARIFICATION = "USE_SPECIFIC_CLARIFICATION"
    USE_EXISTING_CONVERSATION_RESPONSE = "USE_EXISTING_CONVERSATION_RESPONSE"
    NO_CLARIFICATION_NEEDED = "NO_CLARIFICATION_NEEDED"


class ClarificationReason(str, Enum):
    BUSINESS_ASSESSMENT_NEEDS_METRICS = "BUSINESS_ASSESSMENT_NEEDS_METRICS"
    ANALYTICAL_RELATIONSHIP_NEEDS_EVIDENCE = "ANALYTICAL_RELATIONSHIP_NEEDS_EVIDENCE"
    WORKFLOW_REQUEST_NEEDS_REQUIRED_FIELDS = "WORKFLOW_REQUEST_NEEDS_REQUIRED_FIELDS"
    INVENTORY_QUERY_NEEDS_CURRENT_DATA = "INVENTORY_QUERY_NEEDS_CURRENT_DATA"
    TIMEFRAME_REQUIRED = "TIMEFRAME_REQUIRED"
    AMBIGUOUS_BUSINESS_SCOPE = "AMBIGUOUS_BUSINESS_SCOPE"
    NO_ACTIONABLE_GAP = "NO_ACTIONABLE_GAP"
    GENERIC_FALLBACK_ONLY = "GENERIC_FALLBACK_ONLY"


@dataclass(frozen=True)
class ClarificationResult:
    decision: str
    reason: str
    clarification_text: str = ""
    question_intent: str = ""
    requested_fields: list[str] = field(default_factory=list)
    source_gap_ids: list[str] = field(default_factory=list)
    source_layers: list[str] = field(default_factory=list)
    duplicate_guard_applied: bool = False
    duplicate_guard_reason: str = ""
    suppressed_question: str = ""
    replacement_question: str = ""
    previous_questions_checked: list[str] = field(default_factory=list)
    response_confidence: float = 0.0
    fallback_used: bool = False
    response_source: str | None = None
    selected_response_mode: str | None = None
    perspective_selected_frame: str | None = None
    perspective_candidate_frames: list = field(default_factory=list)
    perspective_frame_confidence: float = 0.0
    perspective_consulted: bool = False
    perspective_used_for_framing: bool = False
    version: str = CLARIFICATION_AUTHORITY_VERSION
    diagnostic_only: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def build_clarification_response(
    *,
    user_message: str | None = None,
    normalized_user_message: str | None = None,
    workflow_admission_gate: dict | None = None,
    business_situation: dict | None = None,
    evidence_gap: dict | None = None,
    conversation_memory: dict | None = None,
    application_state: dict | None = None,
) -> dict:
    """Select the smallest useful clarification for blocked/deferred workflow paths."""

    gate = workflow_admission_gate or {}
    if gate.get("decision") == "ADMIT":
        return _result(
            ClarificationDecision.NO_CLARIFICATION_NEEDED,
            ClarificationReason.NO_ACTIONABLE_GAP,
            source_layers=["workflow_admission_gate"],
            response_confidence=0.99,
        )

    text = str(normalized_user_message or user_message or "").strip()
    lowered = text.lower()
    source_layers = _source_layers(business_situation, evidence_gap, gate)
    perspective = _perspective_context(business_situation)
    if perspective.get("selected_frame"):
        source_layers = source_layers + ["perspective"]
    previous_questions = _previous_assistant_questions(application_state, conversation_memory)
    supplied = _supplied_fields(text, application_state, conversation_memory)

    if _is_inventory_query(lowered):
        if _has_inventory_data(application_state):
            return _result(
                ClarificationDecision.NO_CLARIFICATION_NEEDED,
                ClarificationReason.NO_ACTIONABLE_GAP,
                source_layers=source_layers,
                response_confidence=0.9,
            )
        return _specific(
            reason=ClarificationReason.INVENTORY_QUERY_NEEDS_CURRENT_DATA,
            text="ตอนนี้ผมยังไม่มีข้อมูลสต๊อกล่าสุดครับ ส่งรายการสินค้า หรืออัปโหลดข้อมูลสต๊อกมาได้ แล้วผมจะช่วยสรุปสินค้าที่เหลือน้อยให้ครับ",
            question_intent="request_current_inventory_data",
            requested_fields=["inventory_list"],
            source_layers=source_layers,
            previous_questions=previous_questions,
        )

    if _is_business_profit_assessment(lowered, gate):
        fields = _remaining(["timeframe", "revenue", "cost", "expenses"], supplied)
        if "timeframe" in supplied:
            question = "ในช่วงนั้นยอดขายรวม ต้นทุนสินค้า และค่าใช้จ่ายประมาณเท่าไรครับ?"
        else:
            question = (
                "ตอนนี้ยังสรุปไม่ได้ครับ เพราะต้องดูรายได้ ต้นทุนสินค้า ค่าใช้จ่าย และช่วงเวลาเดียวกัน "
                "คุณอยากวิเคราะห์รายวัน รายสัปดาห์ หรือรายเดือนครับ?"
            )
        replacement = "ในช่วงนั้นยอดขายรวม ต้นทุนสินค้า และค่าใช้จ่ายประมาณเท่าไรครับ?"
        return _specific_with_duplicate_guard(
            reason=ClarificationReason.BUSINESS_ASSESSMENT_NEEDS_METRICS,
            question=question,
            replacement=replacement,
            question_intent="request_business_profit_assessment_scope",
            requested_fields=fields or ["revenue", "cost", "expenses"],
            source_layers=source_layers,
            previous_questions=previous_questions,
        )

    if _is_analytical_relationship(lowered, gate):
        fields = _remaining(["average_order_value", "revenue", "cost", "promotion", "waste", "timeframe"], supplied)
        question = (
            "จำนวนลูกค้าที่เพิ่มขึ้นยังไม่ได้เปลี่ยนเป็นกำไรครับ เพื่อเทียบภาพให้ชัด "
            "ขอข้อมูลยอดขายเฉลี่ยต่อบิล ต้นทุน โปรโมชั่น หรือของเสียของช่วงก่อนกับช่วงปัจจุบันได้ไหมครับ?"
        )
        replacement = "ขอเทียบช่วงก่อนกับช่วงปัจจุบันก่อนครับ ในแต่ละช่วงยอดขายรวม ต้นทุน และโปรโมชั่นประมาณเท่าไรครับ?"
        return _specific_with_duplicate_guard(
            reason=ClarificationReason.ANALYTICAL_RELATIONSHIP_NEEDS_EVIDENCE,
            question=question,
            replacement=replacement,
            question_intent="request_profit_relationship_evidence",
            requested_fields=fields or ["revenue", "cost", "timeframe"],
            source_layers=source_layers,
            previous_questions=previous_questions,
            perspective=perspective,
        )

    if gate.get("decision") in {"REJECT_TO_CONVERSATION", "DEFER_FOR_CLARIFICATION"} and _has_partial_business_topic(lowered, gate, business_situation):
        return _result(
            ClarificationDecision.USE_EXISTING_CONVERSATION_RESPONSE,
            ClarificationReason.GENERIC_FALLBACK_ONLY,
            source_layers=source_layers,
            previous_questions_checked=previous_questions,
            response_confidence=0.45,
            fallback_used=True,
        )

    return _result(
        ClarificationDecision.USE_EXISTING_CONVERSATION_RESPONSE,
        ClarificationReason.NO_ACTIONABLE_GAP,
        source_layers=source_layers,
        previous_questions_checked=previous_questions,
        response_confidence=0.35,
        fallback_used=True,
    )


def _specific(
    *,
    reason: ClarificationReason,
    text: str,
    question_intent: str,
    requested_fields: list[str],
    source_layers: list[str],
    previous_questions: list[str],
    duplicate_guard_applied: bool = False,
    duplicate_guard_reason: str = "",
    suppressed_question: str = "",
    replacement_question: str = "",
    perspective: dict | None = None,
) -> dict:
    perspective = perspective or {}
    return _result(
        ClarificationDecision.USE_SPECIFIC_CLARIFICATION,
        reason,
        clarification_text=text,
        question_intent=question_intent,
        requested_fields=requested_fields,
        source_layers=source_layers,
        duplicate_guard_applied=duplicate_guard_applied,
        duplicate_guard_reason=duplicate_guard_reason,
        suppressed_question=suppressed_question,
        replacement_question=replacement_question,
        previous_questions_checked=previous_questions,
        response_confidence=0.88,
        response_source=CLARIFICATION_RESPONSE_SOURCE,
        selected_response_mode=SITUATION_AWARE_CLARIFICATION_MODE,
        perspective_selected_frame=perspective.get("selected_frame"),
        perspective_candidate_frames=perspective.get("candidate_frames") or [],
        perspective_frame_confidence=float(perspective.get("frame_confidence") or 0.0),
        perspective_consulted=bool(perspective),
        perspective_used_for_framing=bool(_strong_frame(perspective, str(perspective.get("selected_frame") or ""))),
    )


def _specific_with_duplicate_guard(
    *,
    reason: ClarificationReason,
    question: str,
    replacement: str,
    question_intent: str,
    requested_fields: list[str],
    source_layers: list[str],
    previous_questions: list[str],
    perspective: dict | None = None,
) -> dict:
    duplicate = _similar_question_already_asked(question, previous_questions)
    if duplicate:
        return _specific(
            reason=reason,
            text=replacement,
            question_intent=question_intent,
            requested_fields=requested_fields,
            source_layers=source_layers,
            previous_questions=previous_questions,
            duplicate_guard_applied=True,
            duplicate_guard_reason="highest_priority_question_already_asked",
            suppressed_question=question,
            replacement_question=replacement,
            perspective=perspective,
        )
    return _specific(
        reason=reason,
        text=question,
        question_intent=question_intent,
        requested_fields=requested_fields,
        source_layers=source_layers,
        previous_questions=previous_questions,
        perspective=perspective,
    )


def _result(
    decision: ClarificationDecision,
    reason: ClarificationReason,
    **values: Any,
) -> dict:
    payload = ClarificationResult(
        decision=decision.value,
        reason=reason.value,
        **values,
    )
    return payload.to_dict()


def _source_layers(business_situation: dict | None, evidence_gap: dict | None, gate: dict | None) -> list[str]:
    layers = ["workflow_admission_gate"] if gate else []
    if business_situation:
        layers.append("business_situation")
    if evidence_gap:
        layers.append("evidence_gap")
    return layers


def _perspective_context(business_situation: dict | None) -> dict:
    diagnostics = (business_situation or {}).get("diagnostics") or {}
    perspective = diagnostics.get("perspective") or {}
    if not isinstance(perspective, dict):
        return {}
    return {
        "selected_frame": perspective.get("selected_frame"),
        "candidate_frames": perspective.get("candidate_frames") or [],
        "frame_confidence": float(perspective.get("frame_confidence") or 0.0),
    }


def _strong_frame(perspective: dict | None, frame_id: str) -> bool:
    perspective = perspective or {}
    return bool(
        perspective.get("selected_frame") == frame_id
        and float(perspective.get("frame_confidence") or 0.0) >= 0.65
    )


def _is_business_profit_assessment(text: str, gate: dict) -> bool:
    return bool(
        gate.get("reason") == "AMBIGUOUS_BUSINESS_ASSESSMENT"
        or (("กำไรดีไหม" in text or "กำไรโอเคไหม" in text or "ทำกำไรดี" in text) and ("ร้าน" in text or "ธุรกิจ" in text))
    )


def _is_analytical_relationship(text: str, gate: dict) -> bool:
    if gate.get("reason") == "ANALYTICAL_QUESTION_NOT_EXECUTABLE":
        return True
    return bool(
        ("ลูกค้า" in text and "เพิ่ม" in text and "กำไร" in text and "ลด" in text)
        or ("ยอดขาย" in text and "เพิ่ม" in text and "เงินไม่เหลือ" in text)
        or ("ขายดี" in text and "กำไร" in text)
    )


def _is_inventory_query(text: str) -> bool:
    return bool(("สต๊อก" in text or "สต็อก" in text or "stock" in text or "inventory" in text) and ("เหลือ" in text or "อะไร" in text or "current" in text))


def _has_inventory_data(application_state: dict | None) -> bool:
    state = application_state or {}
    for key in ("inventory", "stock", "inventory_data", "stock_items"):
        value = state.get(key)
        if value not in (None, "", [], {}):
            return True
    store = state.get("store") or {}
    return bool((store.get("inventory") or store.get("stock")) not in (None, "", [], {}))


def _has_partial_business_topic(text: str, gate: dict, business_situation: dict | None) -> bool:
    situation = business_situation or {}
    return bool(
        gate.get("workflow_candidate")
        or situation.get("business_topic") not in (None, "", "general_business")
        or any(token in text for token in ("กำไร", "ต้นทุน", "ยอดขาย", "ลูกค้า", "สต๊อก", "ธุรกิจ", "ร้าน"))
    )


def _previous_assistant_questions(application_state: dict | None, conversation_memory: dict | None) -> list[str]:
    questions: list[str] = []
    history = ((application_state or {}).get("conversation") or {}).get("chat_history") or []
    for item in history[-8:]:
        if isinstance(item, dict) and item.get("role") == "assistant" and item.get("content"):
            content = str(item.get("content"))
            if "?" in content or "ครับ" in content:
                questions.append(content)
    for key in ("last_assistant_reply", "latest_assistant_message"):
        value = (conversation_memory or {}).get(key)
        if value:
            questions.append(str(value))
    return questions


def _similar_question_already_asked(question: str, previous_questions: list[str]) -> bool:
    normalized_question = _compact(question)
    anchors = [
        "รายวันรายสัปดาห์หรือรายเดือน",
        "ยอดขายเฉลี่ยต่อบิลต้นทุนโปรโมชั่นหรือของเสีย",
    ]
    return any(
        _compact(previous) == normalized_question
        or any(anchor in _compact(previous) and anchor in normalized_question for anchor in anchors)
        for previous in previous_questions
    )


def _supplied_fields(text: str, application_state: dict | None, conversation_memory: dict | None) -> set[str]:
    supplied: set[str] = set()
    combined = " ".join(
        [
            text,
            str((conversation_memory or {}).get("last_user_message") or ""),
            str(((application_state or {}).get("conversation") or {}).get("last_user_message") or ""),
        ]
    )
    if any(token in combined for token in ("รายวัน", "รายสัปดาห์", "รายเดือน", "วันนี้", "สัปดาห์", "เดือน")):
        supplied.add("timeframe")
    if "ยอดขาย" in combined or "รายได้" in combined:
        supplied.add("revenue")
    if "ต้นทุน" in combined:
        supplied.add("cost")
    if "ค่าใช้จ่าย" in combined:
        supplied.add("expenses")
    if "โปรโมชั่น" in combined or "โปร" in combined:
        supplied.add("promotion")
    if "ของเสีย" in combined or "เสีย" in combined:
        supplied.add("waste")
    if "เฉลี่ยต่อบิล" in combined or "ต่อบิล" in combined:
        supplied.add("average_order_value")
    return supplied


def _remaining(fields: list[str], supplied: set[str]) -> list[str]:
    return [field for field in fields if field not in supplied]


def _compact(text: str) -> str:
    return "".join(str(text or "").split()).lower()
