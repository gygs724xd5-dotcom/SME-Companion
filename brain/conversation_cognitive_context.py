from __future__ import annotations

from dataclasses import asdict, dataclass, field


CONVERSATION_COGNITIVE_CONTEXT_VERSION = "5.9.4"


@dataclass
class ConversationCognitiveContext:
    active_topic_id: str = ""
    active_topic_label: str = ""
    topic_started_turn: int = 0
    last_relevant_turn: int = 0
    selected_frame_id: str = ""
    selected_knowledge_ids: list[str] = field(default_factory=list)
    selected_skill_id: str = ""
    unresolved_gap_ids: list[str] = field(default_factory=list)
    answered_gap_ids: list[str] = field(default_factory=list)
    workflow_state: dict = field(default_factory=dict)
    freshness_status: str = "UNKNOWN"
    continuity_strength: str = "WEAK"
    superseded_by_topic_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def context_from_bridge(bridge: dict | None, *, topic_id: str = "", topic_label: str = "", turn: int = 0, workflow_state: dict | None = None) -> dict:
    bridge = bridge or {}
    primary = bridge.get("primary_skill_candidate") or {}
    next_gap = bridge.get("next_shared_gap") or {}
    return ConversationCognitiveContext(
        active_topic_id=topic_id or f"topic::{primary.get('skill_id') or 'unknown'}",
        active_topic_label=topic_label or str(primary.get("skill_id") or ""),
        topic_started_turn=turn,
        last_relevant_turn=turn,
        selected_frame_id=str((primary.get("matched_frames") or [""])[0] if primary.get("matched_frames") else ""),
        selected_knowledge_ids=list(bridge.get("selected_knowledge_ids") or []),
        selected_skill_id=str(primary.get("skill_id") or ""),
        unresolved_gap_ids=[next_gap.get("metric_id")] if next_gap else [],
        workflow_state=workflow_state or {},
        freshness_status="CURRENT",
        continuity_strength="STRONG" if primary else "WEAK",
    ).to_dict()
