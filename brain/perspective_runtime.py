from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from brain.perspective_frame_registry import (
    PERSPECTIVE_FRAME_REGISTRY_VERSION,
    PerspectiveFrameRegistry,
)

PERSPECTIVE_RUNTIME_VERSION = "5.8.5"
PERSPECTIVE_RUNTIME_SOURCE = "perspective_runtime"
PERSPECTIVE_DIAGNOSTICS_VERSION = "5.8.5"
UNKNOWN_SITUATION_FRAME = "UNKNOWN_SITUATION"
PERSPECTIVE_FOUNDATION_REASON = "Perspective frame recognition has insufficient supported signals."


class PerspectiveFrameStatus(str, Enum):
    FOUNDATION_ONLY = "FOUNDATION_ONLY"
    FRAME_RECOGNIZED = "FRAME_RECOGNIZED"
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_SIGNALS = "CONFLICTING_SIGNALS"
    UNKNOWN_SITUATION = "UNKNOWN_SITUATION"


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _source_layers(
    business_situation: dict,
    evidence_runtime: dict,
    truth_runtime: dict,
    evidence_gap_runtime: dict,
) -> dict:
    return {
        "business_situation": bool(business_situation),
        "evidence_runtime": bool(evidence_runtime),
        "truth_runtime": bool(truth_runtime),
        "evidence_gap_runtime": bool(evidence_gap_runtime),
    }


def _constitutional_invariants() -> dict:
    return {
        "routing_changed": False,
        "planner_changed": False,
        "workflow_changed": False,
        "responses_changed": False,
        "execution_changed": False,
        "commit_changed": False,
        "business_memory_changed": False,
        "business_situation_changed": False,
        "evidence_runtime_changed": False,
        "truth_runtime_changed": False,
        "evidence_gap_runtime_changed": False,
        "perspective_classification_changed": True,
        "perspective_runtime_behavior_changed": True,
        "clarification_context_changed": False,
        "knowledge_invoked": False,
        "judgment_invoked": False,
        "decision_invoked": False,
        "recommendations_generated": False,
        "root_causes_diagnosed": False,
    }


@dataclass
class PerspectiveCandidateFrame:
    frame_id: str = ""
    frame_name: str = ""
    confidence: float = 0.0
    supporting_signals: list = field(default_factory=list)
    contradictory_signals: list = field(default_factory=list)
    selection_reason: str = PERSPECTIVE_FOUNDATION_REASON
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PerspectiveRuntime:
    selected_frame: str = UNKNOWN_SITUATION_FRAME
    candidate_frames: list = field(default_factory=list)
    frame_confidence: float = 0.0
    frame_selection_reason: str = PERSPECTIVE_FOUNDATION_REASON
    frame_status: str = PerspectiveFrameStatus.FOUNDATION_ONLY.value
    frame_evidence: dict = field(default_factory=dict)
    frame_contradictions: dict = field(default_factory=dict)
    frame_source_signals: list = field(default_factory=list)
    frame_registry_version: str = PERSPECTIVE_FRAME_REGISTRY_VERSION
    classification_performed: bool = True
    classification_method: str = "deterministic_signal_registry_v1"
    source_layers: dict = field(default_factory=dict)
    diagnostics_version: str = PERSPECTIVE_DIAGNOSTICS_VERSION
    constitutional_invariants: dict = field(default_factory=_constitutional_invariants)
    diagnostics: dict = field(default_factory=dict)
    version: str = PERSPECTIVE_RUNTIME_VERSION
    source: str = PERSPECTIVE_RUNTIME_SOURCE
    runtime_only: bool = True
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _compact(text: str) -> str:
    return "".join(str(text or "").lower().split())


def _contains_any(text: str, patterns: list[str]) -> bool:
    compact = _compact(text)
    return any(pattern in text or _compact(pattern) in compact for pattern in patterns)


def _message_from_inputs(situation: dict, evidence: dict, truth: dict, evidence_gap: dict) -> str:
    values: list[str] = []
    for key in ("objective", "current_focus", "current_problem", "business_topic"):
        if situation.get(key) not in (None, "", [], {}):
            values.append(str(situation.get(key)))
    for item in situation.get("known_evidence") or []:
        if isinstance(item, dict) and item.get("summary") not in (None, "", [], {}):
            values.append(str(item.get("summary")))
    values.extend([str(evidence.get("evidence_summary") or ""), str(truth.get("truth_summary") or ""), str(evidence_gap.get("gap_summary") or "")])
    return " ".join(value for value in values if value)


def _source_signal(signal_id: str, source_text: str) -> dict:
    return {"signal_id": signal_id, "source": "validated_reality_text", "evidence": source_text, "confidence": 1.0}


def extract_perspective_signals(source_text: str) -> list[dict]:
    text = str(source_text or "").lower()
    signals: list[dict] = []

    rules = {
        "profit_decrease": ["กำไรลด", "กำไรน้อยลง", "กำไรน้อย", "profit down", "profit decline", "lower profit"],
        "profit_increase": ["กำไรเพิ่ม", "กำไรดีขึ้น", "profit increase"],
        "customer_increase": ["ลูกค้าเพิ่ม", "ลูกค้ามากขึ้น", "customers increasing", "more customers"],
        "demand_increase": ["ดีมานด์เพิ่ม", "ความต้องการเพิ่ม", "ขายดี", "demand increase", "demand surge"],
        "orders_increase": ["ออเดอร์เพิ่ม", "ออเดอร์เยอะ", "ยอดสั่งเพิ่ม", "orders increasing", "more orders"],
        "sudden_growth": ["เพิ่มขึ้นมาก", "พุ่ง", "surge", "spike"],
        "sales_increase": ["ยอดขายเพิ่ม", "ยอดขายดีขึ้น", "ขายดี", "sales increase", "sales up"],
        "revenue_stable_or_increase": ["รายได้เพิ่ม", "ยอดขายดี", "ยอดขายมี", "revenue stable", "revenue increase"],
        "selling_activity_high": ["ขายดี", "ขายได้", "ยอดขายมี", "selling well"],
        "sales_decrease": ["ยอดขายลด", "ยอดตก", "ขายได้น้อยกว่า", "ขายน้อยลง", "sales decline", "sales down"],
        "revenue_decrease": ["รายได้ลด", "revenue decline", "revenue down"],
        "continuous_decline": ["ต่อเนื่อง", "หลายเดือน", "continuous", "month over month"],
        "prior_period_lower": ["น้อยกว่าเดือนก่อน", "ต่ำกว่าเดือนก่อน", "compared with last month"],
        "stock_low": ["เหลือแค่", "เหลือน้อย", "สต๊อกเหลือน้อย", "สต็อกเหลือน้อย", "low stock"],
        "stock_near_zero": ["กำลังจะหมด", "ใกล้หมด", "หมดสต๊อก", "out of stock"],
        "inventory_insufficient": ["ของไม่พอขาย", "สินค้าไม่พอ", "inventory insufficient", "not enough stock"],
        "stock_abundant": ["ของเหลือเยอะ", "สต๊อกเยอะ", "stock abundant"],
        "sales_exist": ["ขายได้", "ยอดขายมี", "sales exist"],
        "revenue_exists": ["รายได้มี", "ยอดขายมี", "revenue exists"],
        "cash_insufficient": ["ไม่มีเงินสด", "เงินสดไม่พอ", "เงินหมุนไม่พอ", "cash insufficient", "no cash"],
        "money_not_remaining": ["เงินไม่เหลือ", "ไม่มีเงินเหลือ", "money not left"],
        "cannot_pay": ["จ่ายไม่ไหว", "ไม่มีเงินจ่าย", "cannot pay"],
        "cash_abundant": ["เงินสดพอ", "cash available"],
        "demand_decrease": ["ดีมานด์ลด", "ความต้องการลด", "demand decrease"],
        "orders_decrease": ["ออเดอร์ลด", "orders decline"],
        "customer_decrease": ["ลูกค้าน้อยลง", "ลูกค้าลด", "customers decline"],
        "traffic_decrease": ["คนเข้าร้านน้อยลง", "traffic decline"],
        "orders_backlog": ["ออเดอร์ค้าง", "งานค้าง", "backlog"],
        "queue_increase": ["คิวเยอะ", "คิวยาว", "queue"],
        "process_stuck": ["งานติด", "กระบวนการติด", "process stuck"],
        "delay": ["ล่าช้า", "ช้า", "delay"],
        "capacity_exceeded": ["ผลิตไม่ทัน", "ทำไม่ทัน", "รับไม่ไหว", "capacity exceeded"],
        "cannot_keep_up": ["ทำไม่ทัน", "ไม่ทันยอดสั่ง", "cannot keep up"],
        "staff_capacity_limited": ["พนักงานไม่พอ", "คนไม่พอ", "staff shortage"],
        "equipment_capacity_limited": ["เครื่องไม่พอ", "equipment capacity"],
        "max_output_reached": ["เต็มกำลัง", "กำลังผลิตเต็ม", "max output"],
        "supplier_late": ["ซัพพลายเออร์ส่งของช้า", "supplier late", "supplier delay"],
        "material_unavailable": ["วัตถุดิบขาด", "ของจากซัพพลายเออร์ไม่มี", "material unavailable"],
        "supplier_interrupted": ["ซัพพลายเออร์หยุดส่ง", "supplier interrupted"],
        "price_resistance": ["ลูกค้าบอกแพง", "ลูกค้าไม่รับราคา", "price resistance"],
        "competitor_undercut": ["คู่แข่งถูกกว่า", "competitor cheaper", "undercut"],
        "price_margin_constraint": ["ราคาคลุมต้นทุนไม่พอ", "margin pressure"],
        "repeat_customer_decline": ["ลูกค้าประจำลด", "repeat customers decline"],
        "customers_do_not_return": ["ลูกค้าไม่กลับมาซื้อซ้ำ", "ไม่กลับมาซื้อซ้ำ", "customers do not return"],
        "churn": ["ลูกค้าหาย", "churn"],
        "loyalty_weakness": ["ความภักดีลด", "loyalty weakness"],
        "room_to_serve": ["ยังรับเพิ่มได้", "มีที่รองรับ", "room to serve"],
    }
    for signal_id, patterns in rules.items():
        if _contains_any(text, patterns):
            signals.append(_source_signal(signal_id, source_text))
    seen = set()
    unique = []
    for signal in signals:
        if signal["signal_id"] not in seen:
            seen.add(signal["signal_id"])
            unique.append(signal)
    return unique


def _group_satisfied(group: list[str], signal_ids: set[str]) -> bool:
    return any(signal in signal_ids for signal in group)


def _frame_supported(frame: Any, signal_ids: set[str]) -> bool:
    if frame.frame_id == UNKNOWN_SITUATION_FRAME:
        return False
    if not frame.required_signal_groups:
        return False
    return all(_group_satisfied(group, signal_ids) for group in frame.required_signal_groups)


def _confidence_for(frame: Any, supporting: list[dict], contradictory: list[dict]) -> float:
    confidence = 0.42 + min(0.36, len(supporting) * 0.09)
    required_bonus = 0.1 if len(supporting) >= 2 else 0.0
    confidence += required_bonus
    confidence -= min(0.25, len(contradictory) * 0.12)
    confidence = max(confidence, frame.minimum_confidence)
    return round(max(0.0, min(1.0, confidence)), 2)


FRAME_PRIORITY = {
    "PROFIT_COMPRESSION": 100,
    "CASH_FLOW_STRESS": 92,
    "CAPACITY_CONSTRAINT": 88,
    "OPERATIONAL_BOTTLENECK": 84,
    "INVENTORY_RISK": 80,
    "SUPPLIER_DISRUPTION": 90,
    "SALES_DECLINE": 72,
    "CUSTOMER_RETENTION_RISK": 68,
    "PRICING_PRESSURE": 64,
    "DEMAND_WEAKNESS": 60,
    "DEMAND_SURGE": 56,
    "GROWTH_OPPORTUNITY": 40,
}


def classify_perspective_frames(source_text: str, registry: PerspectiveFrameRegistry | None = None) -> list[dict]:
    registry = registry or PerspectiveFrameRegistry()
    signals = extract_perspective_signals(source_text)
    signal_ids = {signal["signal_id"] for signal in signals}
    candidates: list[dict] = []
    for frame in registry.list():
        if not _frame_supported(frame, signal_ids):
            continue
        supporting = [signal for signal in signals if signal["signal_id"] in frame.recognition_signals]
        contradictory = [signal for signal in signals if signal["signal_id"] in frame.contradictory_signals]
        confidence = _confidence_for(frame, supporting, contradictory)
        if confidence < frame.minimum_confidence:
            continue
        candidates.append(
            PerspectiveCandidateFrame(
                frame_id=frame.frame_id,
                frame_name=frame.display_name,
                confidence=confidence,
                supporting_signals=supporting,
                contradictory_signals=contradictory,
                selection_reason=f"{frame.frame_id} supported by {len(supporting)} deterministic signal(s).",
            ).to_dict()
        )
    return candidates


def rank_candidate_frames(candidates: list[dict]) -> list[dict]:
    return sorted(
        deepcopy(candidates),
        key=lambda item: (
            -float(item.get("confidence") or 0.0),
            -FRAME_PRIORITY.get(str(item.get("frame_id") or ""), 0),
            str(item.get("frame_id") or ""),
        ),
    )


def _status_for(selected: str, candidates: list[dict]) -> str:
    if selected == UNKNOWN_SITUATION_FRAME:
        return PerspectiveFrameStatus.FOUNDATION_ONLY.value
    if any(item.get("contradictory_signals") for item in candidates):
        return PerspectiveFrameStatus.CONFLICTING_SIGNALS.value
    if len(candidates) > 1:
        return PerspectiveFrameStatus.MULTIPLE_CANDIDATES.value
    return PerspectiveFrameStatus.FRAME_RECOGNIZED.value


def build_perspective_runtime(
    *,
    business_situation: dict | None = None,
    evidence_runtime: dict | None = None,
    truth_runtime: dict | None = None,
    evidence_gap_runtime: dict | None = None,
) -> dict:
    """Create deterministic diagnostics-only Perspective Runtime framing."""

    situation = _as_dict(business_situation)
    situation_diagnostics = _as_dict(situation.get("diagnostics"))
    evidence = _as_dict(evidence_runtime) or _as_dict(situation_diagnostics.get("evidence"))
    truth = _as_dict(truth_runtime) or _as_dict(situation_diagnostics.get("truth"))
    evidence_gap = _as_dict(evidence_gap_runtime) or _as_dict(situation_diagnostics.get("evidence_gap"))
    invariants = _constitutional_invariants()
    sources = _source_layers(situation, evidence, truth, evidence_gap)
    source_text = _message_from_inputs(situation, evidence, truth, evidence_gap)
    source_signals = extract_perspective_signals(source_text)
    ranked_candidates = rank_candidate_frames(classify_perspective_frames(source_text))
    selected = ranked_candidates[0] if ranked_candidates else {}
    selected_frame = selected.get("frame_id") or UNKNOWN_SITUATION_FRAME
    confidence = float(selected.get("confidence") or 0.0)
    reason = (
        f"{selected_frame} selected as the highest-ranked supported situation frame."
        if selected
        else PERSPECTIVE_FOUNDATION_REASON
    )
    frame_status = _status_for(selected_frame, ranked_candidates)
    frame_evidence = {
        item.get("frame_id"): item.get("supporting_signals") or []
        for item in ranked_candidates
    }
    frame_contradictions = {
        item.get("frame_id"): item.get("contradictory_signals") or []
        for item in ranked_candidates
        if item.get("contradictory_signals")
    }
    registry = PerspectiveFrameRegistry()
    diagnostics = {
        "perspective_runtime_created": True,
        "perspective_runtime_version": PERSPECTIVE_RUNTIME_VERSION,
        "perspective_runtime_source": PERSPECTIVE_RUNTIME_SOURCE,
        "diagnostics_version": PERSPECTIVE_DIAGNOSTICS_VERSION,
        "selected_frame": selected_frame,
        "candidate_frame_count": len(ranked_candidates),
        "candidate_frames": deepcopy(ranked_candidates),
        "frame_confidence": confidence,
        "frame_selection_reason": reason,
        "frame_status": frame_status,
        "frame_evidence": deepcopy(frame_evidence),
        "frame_contradictions": deepcopy(frame_contradictions),
        "frame_source_signals": deepcopy(source_signals),
        "frame_registry_version": registry.version,
        "registered_frame_count": len(registry.ids()),
        "registered_frame_ids": registry.ids(),
        "registry_version": registry.version,
        "source_layers": deepcopy(sources),
        "constitutional_invariants": deepcopy(invariants),
        "diagnostic_only": True,
        "runtime_only": True,
        "reads_business_situation_diagnostics": True,
        "reads_evidence_runtime_diagnostics": True,
        "reads_truth_runtime_diagnostics": True,
        "reads_evidence_gap_runtime_diagnostics": True,
        "frame_recognition_implemented": True,
        "classification_performed": True,
        "classification_method": "deterministic_signal_registry_v1",
        "knowledge_invoked": False,
        "judgment_invoked": False,
        "decision_invoked": False,
        "recommendations_generated": False,
        "root_causes_diagnosed": False,
        **invariants,
    }
    runtime = PerspectiveRuntime(
        selected_frame=selected_frame,
        candidate_frames=ranked_candidates,
        frame_confidence=confidence,
        frame_selection_reason=reason,
        frame_status=frame_status,
        frame_evidence=frame_evidence,
        frame_contradictions=frame_contradictions,
        frame_source_signals=source_signals,
        frame_registry_version=registry.version,
        classification_performed=True,
        classification_method="deterministic_signal_registry_v1",
        source_layers=sources,
        constitutional_invariants=invariants,
        diagnostics=diagnostics,
    )
    return runtime.to_dict()
