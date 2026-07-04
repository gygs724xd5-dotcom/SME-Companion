from __future__ import annotations

from dataclasses import asdict, dataclass, field


CONTEXT_FRESHNESS_VERSION = "5.9.4"

VOLATILE_EVIDENCE = {"current_stock", "daily_orders", "cash_balance", "backlog", "current_output", "current_order_volume", "output_quantity"}
DURABLE_EVIDENCE = {"business_model", "product_category", "location_model"}
MODERATE_EVIDENCE = {"equipment_count", "staffing_level", "supplier"}


@dataclass
class ContextFreshnessResult:
    context_id: str
    freshness_status: str = "UNKNOWN"
    turn_distance: int = 0
    topic_distance: int = 0
    observed_at: str = ""
    evidence_type: str = "UNKNOWN"
    reusable: bool = False
    reuse_constraints: list[str] = field(default_factory=list)
    expiration_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_context_freshness(context_id: str, *, turn_distance: int = 0, topic_distance: int = 0, superseded: bool = False, observed_at: str = "") -> dict:
    evidence_type = "DURABLE" if context_id in DURABLE_EVIDENCE else "MODERATE" if context_id in MODERATE_EVIDENCE else "VOLATILE" if context_id in VOLATILE_EVIDENCE else "UNKNOWN"
    if superseded:
        status = "SUPERSEDED"
    elif evidence_type == "VOLATILE" and (turn_distance > 2 or topic_distance > 0):
        status = "STALE"
    elif evidence_type == "MODERATE" and turn_distance > 6:
        status = "STALE"
    elif turn_distance <= 1:
        status = "CURRENT"
    else:
        status = "RECENT"
    return ContextFreshnessResult(
        context_id=context_id,
        freshness_status=status,
        turn_distance=turn_distance,
        topic_distance=topic_distance,
        observed_at=observed_at,
        evidence_type=evidence_type,
        reusable=status in {"CURRENT", "RECENT"} and not (evidence_type == "VOLATILE" and topic_distance > 0),
        reuse_constraints=["confirm_current_value"] if status in {"STALE", "UNKNOWN"} else [],
        expiration_reason="superseded_by_current_turn" if superseded else "volatile_context_expired" if status == "STALE" and evidence_type == "VOLATILE" else "",
    ).to_dict()
