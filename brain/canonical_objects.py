from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import uuid4
from copy import deepcopy


T = TypeVar("T", bound="_CanonicalObject")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return deepcopy(value) if isinstance(value, list) else []


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class _CanonicalObject:
    """Shared dict serialization for V5 canonical runtime objects."""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls: type[T], data: dict | None) -> T:
        source = data or {}
        allowed = {item.name for item in fields(cls)}
        values = {key: deepcopy(value) for key, value in source.items() if key in allowed}
        return cls(**values)


@dataclass
class ConversationFrame(_CanonicalObject):
    turn_id: str = field(default_factory=lambda: _new_id("turn"))
    user_message: str = ""
    normalized_message: str = ""
    conversation_act: str = "unknown"
    store_id: str = ""
    timestamp: str = field(default_factory=_utc_now)
    active_workflow_hint: dict = field(default_factory=dict)
    resolved_references: dict = field(default_factory=dict)
    candidate_entities: dict = field(default_factory=dict)
    ambiguity_flags: list = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)
    uploaded_files: list = field(default_factory=list)
    ui_surface: str = ""
    prior_turn_reference: dict = field(default_factory=dict)
    interruption_signal: dict = field(default_factory=dict)
    correction_target: dict = field(default_factory=dict)
    confirmation_target: dict = field(default_factory=dict)
    language: str = ""
    user_role: str = ""


@dataclass
class KnowledgeContext(_CanonicalObject):
    knowledge_context_id: str = field(default_factory=lambda: _new_id("knowledge"))
    conversation_frame_id: str = ""
    candidate_domains: list = field(default_factory=list)
    candidate_skills: list = field(default_factory=list)
    selected_domain_hint: str = ""
    required_entities: list = field(default_factory=list)
    required_memory: list = field(default_factory=list)
    business_rules: list = field(default_factory=list)
    reasoning_patterns: list = field(default_factory=list)
    response_guidance: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)
    workflow_links: list = field(default_factory=list)
    tool_requirements: list = field(default_factory=list)
    examples: list = field(default_factory=list)
    domain_vocabulary: dict = field(default_factory=dict)
    reject_reasons: list = field(default_factory=list)
    knowledge_gaps: list = field(default_factory=list)
    version: str = "5.1.1"


@dataclass
class ReasoningDecision(_CanonicalObject):
    reasoning_decision_id: str = field(default_factory=lambda: _new_id("reasoning"))
    conversation_frame_id: str = ""
    knowledge_context_id: str = ""
    business_goal: str = ""
    decision_type: str = "unknown"
    selected_domain: str = ""
    selected_skill_id: str = ""
    known_facts: dict = field(default_factory=dict)
    missing_facts: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    recommended_action: str = ""
    confidence: float = 0.0
    diagnostics: dict = field(default_factory=dict)
    risk: dict = field(default_factory=dict)
    opportunity: dict = field(default_factory=dict)
    business_stage: str = ""
    rule_applications: list = field(default_factory=list)
    rejected_actions: list = field(default_factory=list)
    memory_requirements: list = field(default_factory=list)
    workflow_recommendation: dict = field(default_factory=dict)
    tool_recommendation: dict = field(default_factory=dict)
    response_mode: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> "ReasoningDecision":
        item = super().from_dict(data)
        item.confidence = _float(item.confidence)
        return item


@dataclass
class PlannerDecision(_CanonicalObject):
    planner_decision_id: str = field(default_factory=lambda: _new_id("planner"))
    conversation_frame_id: str = ""
    reasoning_decision_id: str = ""
    primary_action: str = ""
    primary_engine_path: list = field(default_factory=list)
    fallback_path: list = field(default_factory=list)
    workflow_action: dict = field(default_factory=dict)
    memory_actions: list = field(default_factory=list)
    llm_action: dict = field(default_factory=dict)
    response_expectation: dict = field(default_factory=dict)
    confidence: float = 0.0
    diagnostics: dict = field(default_factory=dict)
    tool_actions: list = field(default_factory=list)
    transformation_action: dict = field(default_factory=dict)
    compatibility_path: str = "v4_dict_runtime"
    guard_action: dict = field(default_factory=dict)
    interruption_handling: dict = field(default_factory=dict)
    execution_constraints: list = field(default_factory=list)
    deferred_actions: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | None) -> "PlannerDecision":
        item = super().from_dict(data)
        item.confidence = _float(item.confidence)
        return item


@dataclass
class WorkflowState(_CanonicalObject):
    workflow_id: str = ""
    workflow_instance_id: str = field(default_factory=lambda: _new_id("workflow"))
    owner_domain: str = ""
    owner_skill_id: str = ""
    status: str = "new"
    required_fields: list = field(default_factory=list)
    collected_fields: dict = field(default_factory=dict)
    missing_fields: list = field(default_factory=list)
    last_transition: str = ""
    next_required_action: str = ""
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    diagnostics: dict = field(default_factory=dict)
    paused_reason: str = ""
    interruption_context: dict = field(default_factory=dict)
    validation_errors: list = field(default_factory=list)
    completion_result: dict = field(default_factory=dict)
    completion_memory_proposals: list = field(default_factory=list)
    chained_workflow_id: str = ""
    cancel_reason: str = ""
    failure_reason: str = ""
    history: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | None) -> "WorkflowState":
        source = dict(data or {})
        if "workflow_id" not in source and source.get("workflow"):
            source["workflow_id"] = source["workflow"]
        if "status" not in source and source.get("step"):
            source["status"] = source["step"]
        if "next_required_action" not in source and source.get("next_action"):
            source["next_required_action"] = source["next_action"]
        if "updated_at" not in source and source.get("last_updated"):
            source["updated_at"] = source["last_updated"]
        item = super().from_dict(source)
        diagnostics = _dict(item.diagnostics)
        legacy_fields = {
            key: deepcopy(source[key])
            for key in ("workflow", "step", "is_ready", "next_action", "last_updated")
            if key in source
        }
        if legacy_fields:
            diagnostics.setdefault("legacy_fields", legacy_fields)
        item.diagnostics = diagnostics
        return item


@dataclass
class BusinessMemoryItem(_CanonicalObject):
    memory_id: str = field(default_factory=lambda: _new_id("memory"))
    store_id: str = ""
    memory_type: str = "unknown"
    owner: str = ""
    subject: str = ""
    content: dict = field(default_factory=dict)
    source: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    freshness: str = "unknown"
    provenance: dict = field(default_factory=dict)
    expires_at: str = ""
    related_domain: str = ""
    related_skill_id: str = ""
    related_workflow_id: str = ""
    entities: dict = field(default_factory=dict)
    tags: list = field(default_factory=list)
    supersedes: list = field(default_factory=list)
    superseded_by: str = ""
    confirmation_status: str = "unconfirmed"
    diagnostics: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict | None) -> "BusinessMemoryItem":
        item = super().from_dict(data)
        item.confidence = _float(item.confidence)
        return item


@dataclass
class TransformationResult(_CanonicalObject):
    transformation_id: str = field(default_factory=lambda: _new_id("transformation"))
    source_reference: dict = field(default_factory=dict)
    target_schema: dict = field(default_factory=dict)
    result_type: str = "unknown"
    structured_output: dict = field(default_factory=dict)
    validation_status: str = "unknown"
    confidence: float = 0.0
    provenance: dict = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)
    diagnostics: dict = field(default_factory=dict)
    raw_extraction: dict = field(default_factory=dict)
    normalized_entities: dict = field(default_factory=dict)
    correction_required: bool = False
    validation_errors: list = field(default_factory=list)
    llm_assisted: bool = False
    workflow_instance_id: str = ""
    memory_write_proposals: list = field(default_factory=list)
    rendering_hints: dict = field(default_factory=dict)
    version: str = "5.1.1"

    @classmethod
    def from_dict(cls, data: dict | None) -> "TransformationResult":
        item = super().from_dict(data)
        item.confidence = _float(item.confidence)
        item.correction_required = bool(item.correction_required)
        item.llm_assisted = bool(item.llm_assisted)
        return item


@dataclass
class ResponseEnvelope(_CanonicalObject):
    response_id: str = field(default_factory=lambda: _new_id("response"))
    turn_id: str = ""
    text: str = ""
    source: str = "unknown"
    domain: str = ""
    skill_id: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=_utc_now)
    diagnostics: dict = field(default_factory=dict)
    workflow: dict = field(default_factory=dict)
    memory: dict = field(default_factory=dict)
    reasoning_summary: dict = field(default_factory=dict)
    follow_up: str = ""
    assumptions: list = field(default_factory=list)
    rendering_hints: dict = field(default_factory=dict)
    fallback_used: bool = False
    transformation_result_id: str = ""
    llm_diagnostics: dict = field(default_factory=dict)
    developer_trace: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict | None) -> "ResponseEnvelope":
        item = super().from_dict(data)
        item.confidence = _float(item.confidence)
        item.fallback_used = bool(item.fallback_used)
        return item


def to_canonical_dict(value: _CanonicalObject | dict | None) -> dict:
    if isinstance(value, _CanonicalObject):
        return value.to_dict()
    return deepcopy(value) if isinstance(value, dict) else {}


def workflow_state_from_legacy(data: dict | None) -> WorkflowState:
    return WorkflowState.from_dict(data)
