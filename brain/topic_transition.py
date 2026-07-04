from __future__ import annotations

from dataclasses import asdict, dataclass, field


TOPIC_TRANSITION_VERSION = "5.9.4"


@dataclass
class TopicTransitionResult:
    previous_topic_id: str = ""
    current_topic_id: str = ""
    transition_type: str = "CONTINUATION"
    transition_reason: str = ""
    previous_context_reusable: bool = True
    reusable_fields: list[str] = field(default_factory=list)
    superseded_fields: list[str] = field(default_factory=list)
    stale_gaps: list[str] = field(default_factory=list)
    old_skill_superseded: bool = False
    old_handoff_superseded: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _topic(text: str) -> str:
    compact = "".join(str(text or "").lower().split())
    if any(token in compact for token in ["กลับมาเรื่องสต๊อก", "กลับมาเรื่องสต็อก", "stockagain", "กลับมาเรื่องกำลังผลิต"]):
        return "RETURN"
    if any(token in compact for token in ["เปิดร้าน", "startup", "ต้นทุนเปิดร้าน"]):
        return "STARTUP_COST_STRUCTURE"
    if any(token in compact for token in ["สต๊อก", "สต็อก", "ของเหลือ", "stock", "inventory"]):
        return "INVENTORY_HEALTH"
    if any(token in compact for token in ["กำลังผลิต", "ทำได้", "ออเดอร์", "capacity"]):
        return "OPERATING_CAPACITY"
    if any(token in compact for token in ["ยอดขาย", "ขายลด", "sales"]):
        return "SALES_FUNNEL"
    if any(token in compact for token in ["กำไร", "profit"]):
        return "PROFITABILITY_STRUCTURE"
    if any(token in compact for token in ["dashboard", "ตัวเลขอะไร", "metrics"]):
        return "DASHBOARD_METRICS"
    return ""


def detect_topic_transition(user_message: str, previous_context: dict | None = None) -> dict:
    previous_context = previous_context or {}
    previous = str(previous_context.get("active_topic_id") or previous_context.get("active_topic_label") or "")
    current = _topic(user_message) or previous
    if _topic(user_message) == "RETURN":
        current = "INVENTORY_HEALTH" if "สต" in user_message or "stock" in user_message.lower() else "OPERATING_CAPACITY"
        transition = "TOPIC_RETURN"
    elif previous and current and current != previous and current not in previous:
        transition = "TOPIC_SWITCH"
    elif previous and current == previous:
        transition = "CONTINUATION"
    elif previous and not _topic(user_message):
        transition = "CONTINUATION"
    else:
        transition = "CONTINUATION"
    switched = transition in {"TOPIC_SWITCH", "TOPIC_RETURN", "INTERRUPTION"}
    return TopicTransitionResult(
        previous_topic_id=previous,
        current_topic_id=current,
        transition_type=transition,
        transition_reason="current_turn_topic_signal" if switched else "current_turn_continuity",
        previous_context_reusable=not switched or transition == "TOPIC_RETURN",
        reusable_fields=[] if transition == "TOPIC_SWITCH" else ["durable_business_context"],
        superseded_fields=["volatile_runtime_evidence", "active_gap"] if switched else [],
        stale_gaps=list(previous_context.get("unresolved_gap_ids") or []) if switched else [],
        old_skill_superseded=switched,
        old_handoff_superseded=switched,
    ).to_dict()
