from __future__ import annotations

from dataclasses import asdict, dataclass


WORKFLOW_INTERRUPTION_VERSION = "5.9.4"


@dataclass
class WorkflowInterruptionResult:
    interruption_detected: bool = False
    interruption_type: str = "WORKFLOW_CONTINUATION"
    workflow_paused: bool = False
    workflow_preserved: bool = False
    new_topic_started: bool = False
    return_possible: bool = False
    response_owner: str = "WORKFLOW"

    def to_dict(self) -> dict:
        return asdict(self)


def detect_workflow_interruption(user_message: str, workflow_state: dict | None = None) -> dict:
    workflow_state = workflow_state or {}
    admitted = bool(workflow_state.get("workflow_admitted") or workflow_state.get("admitted") or workflow_state.get("workflow_id"))
    compact = "".join(str(user_message or "").lower().split())
    if not admitted:
        return WorkflowInterruptionResult(response_owner="COGNITIVE_RUNTIME").to_dict()
    if any(token in compact for token in ["ยกเลิก", "cancel"]):
        kind = "WORKFLOW_CANCEL"
    elif any(token in compact for token in ["ไม่ใช่", "แก้", "actually"]):
        kind = "WORKFLOW_CORRECTION"
    elif any(token in compact for token in ["กำไรลด", "ยอดขาย", "ลูกค้าเพิ่ม", "เปิดร้าน", "stock", "lowerprofit", "morecustomers", "sales", "startup"]):
        kind = "RELATED_QUESTION" if any(token in compact for token in ["กำไร", "ยอดขาย", "ลูกค้า"]) else "UNRELATED_TOPIC"
    else:
        kind = "WORKFLOW_CONTINUATION"
    interrupted = kind != "WORKFLOW_CONTINUATION"
    return WorkflowInterruptionResult(
        interruption_detected=interrupted,
        interruption_type=kind,
        workflow_paused=interrupted and kind != "WORKFLOW_CANCEL",
        workflow_preserved=kind != "WORKFLOW_CANCEL",
        new_topic_started=kind in {"RELATED_QUESTION", "UNRELATED_TOPIC"},
        return_possible=kind != "WORKFLOW_CANCEL",
        response_owner="WORKFLOW" if not interrupted else "WORKFLOW_PRESERVED_WITH_COGNITIVE_TOPIC",
    ).to_dict()
