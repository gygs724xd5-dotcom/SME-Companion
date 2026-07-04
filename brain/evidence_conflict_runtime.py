from __future__ import annotations

from dataclasses import asdict, dataclass, field


EVIDENCE_CONFLICT_RUNTIME_VERSION = "5.9.4"


@dataclass
class EvidenceConflictSet:
    conflict_id: str
    metric_id: str
    competing_values: list = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    timestamps: list[str] = field(default_factory=list)
    truth_statuses: list[str] = field(default_factory=list)
    freshness_statuses: list[str] = field(default_factory=list)
    active_topic: str = ""
    conflict_type: str = "VALUE_CONFLICT"
    resolution_required: bool = True
    preferred_resolution_method: str = "ASK_USER_CONFIRM_CURRENT_VALUE"

    def to_dict(self) -> dict:
        return asdict(self)


def detect_evidence_conflicts(metric_id: str, values: list[dict], *, active_topic: str = "") -> dict:
    concrete = [item for item in values if item.get("value") not in (None, "", [], {})]
    distinct = []
    for item in concrete:
        if item.get("value") not in distinct:
            distinct.append(item.get("value"))
    conflict_type = "VALUE_CONFLICT"
    if len({str(item.get("timeframe") or "") for item in concrete if item.get("timeframe")}) > 1:
        conflict_type = "TIMEFRAME_CONFLICT"
    if len({str(item.get("unit") or "") for item in concrete if item.get("unit")}) > 1:
        conflict_type = "UNIT_CONFLICT"
    if len(distinct) <= 1 and conflict_type == "VALUE_CONFLICT":
        return {}
    return EvidenceConflictSet(
        conflict_id=f"conflict::{metric_id}",
        metric_id=metric_id,
        competing_values=distinct,
        sources=[str(item.get("source") or "") for item in concrete],
        timestamps=[str(item.get("observed_at") or "") for item in concrete],
        truth_statuses=[str(item.get("truth_classification") or "") for item in concrete],
        freshness_statuses=[str(item.get("freshness") or item.get("freshness_status") or "") for item in concrete],
        active_topic=active_topic,
        conflict_type=conflict_type,
    ).to_dict()


def detect_current_correction(user_message: str, previous_metric_id: str, previous_value: object, current_value: object) -> dict:
    compact = "".join(str(user_message or "").lower().split())
    correction = any(token in compact for token in ["ไม่ใช่", "ตอนนี้", "actually", "now"])
    if not correction or current_value in (None, "", [], {}):
        return {}
    return EvidenceConflictSet(
        conflict_id=f"correction::{previous_metric_id}",
        metric_id=previous_metric_id,
        competing_values=[previous_value, current_value],
        sources=["previous_context", "current_user_correction"],
        freshness_statuses=["SUPERSEDED", "CURRENT"],
        conflict_type="CURRENT_VS_HISTORICAL",
        resolution_required=False,
        preferred_resolution_method="USE_CURRENT_TURN_VALUE_FOR_RUNTIME_ONLY",
    ).to_dict()
