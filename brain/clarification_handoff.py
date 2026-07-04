from __future__ import annotations

from dataclasses import asdict, dataclass, field


CLARIFICATION_HANDOFF_VERSION = "5.9.0"


@dataclass(frozen=True)
class ClarificationHandoff:
    handoff_id: str
    source_authority: str = "knowledge_runtime"
    source_knowledge_ids: list[str] = field(default_factory=list)
    source_gap_id: str = ""
    source_metric_id: str = ""
    handoff_type: str = "NO_CLARIFICATION_NEEDED"
    question_intent: str = ""
    user_goal: str = ""
    active_business_topic: str = ""
    known_context: dict = field(default_factory=dict)
    known_partial_value: dict = field(default_factory=dict)
    missing_information: list[str] = field(default_factory=list)
    why_it_matters: str = ""
    blocking_relationship_rules: list[str] = field(default_factory=list)
    expected_answer_schema: dict = field(default_factory=dict)
    suggested_question_focus: str = ""
    wording_guidance: list[str] = field(default_factory=list)
    safe_wording_constraints: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    conversation_constraints: dict = field(default_factory=dict)
    duplicate_guard: dict = field(default_factory=dict)
    workflow_coordination: dict = field(default_factory=dict)
    fallback_strategy: dict = field(default_factory=dict)
    handoff_support_strength: float = 0.0
    authority_trace: list[str] = field(default_factory=list)
    version: str = CLARIFICATION_HANDOFF_VERSION

    def to_dict(self) -> dict:
        return asdict(self)
