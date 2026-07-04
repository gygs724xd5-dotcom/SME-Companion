from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


COGNITIVE_AUTHORITY_AUDIT_VERSION = "5.8.2"
COGNITIVE_AUTHORITY_AUDIT_SOURCE = "cognitive_authority_audit"


class AuthorityStage(str, Enum):
    USER_INPUT = "USER_INPUT"
    CONVERSATION_UNDERSTANDING = "CONVERSATION_UNDERSTANDING"
    INTENT_RESOLUTION = "INTENT_RESOLUTION"
    PLANNER = "PLANNER"
    ROUTER = "ROUTER"
    WORKFLOW_ADMISSION = "WORKFLOW_ADMISSION"
    CLARIFICATION_AUTHORITY = "CLARIFICATION_AUTHORITY"
    KNOWLEDGE_RUNTIME = "KNOWLEDGE_RUNTIME"
    KNOWLEDGE_GAP_PRIORITIZATION = "KNOWLEDGE_GAP_PRIORITIZATION"
    CLARIFICATION_HANDOFF = "CLARIFICATION_HANDOFF"
    WORKFLOW_RUNTIME = "WORKFLOW_RUNTIME"
    COGNITIVE_RUNTIME = "COGNITIVE_RUNTIME"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"
    FALLBACK = "FALLBACK"
    RESPONSE_GUARD = "RESPONSE_GUARD"
    COMMIT = "COMMIT"


class AuthorityRole(str, Enum):
    OBSERVED = "OBSERVED"
    ADVISORY = "ADVISORY"
    AUTHORITATIVE = "AUTHORITATIVE"
    OVERRIDDEN = "OVERRIDDEN"
    NOT_CONSULTED = "NOT_CONSULTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ResponseMode(str, Enum):
    DIRECT_CONVERSATION = "DIRECT_CONVERSATION"
    GENERAL_BUSINESS_ANALYSIS = "GENERAL_BUSINESS_ANALYSIS"
    CLARIFICATION = "CLARIFICATION"
    WORKFLOW = "WORKFLOW"
    FALLBACK = "FALLBACK"
    UNKNOWN = "UNKNOWN"


LOW_CONFIDENCE_CONFLICT = "LOW_CONFIDENCE_UNDERSTANDING_OVERRIDDEN_BY_HIGH_CONFIDENCE_RESOLVER"
WORKFLOW_UNCERTAINTY_CONFLICT = "WORKFLOW_ADMITTED_DESPITE_COGNITIVE_UNCERTAINTY"
COGNITIVE_CLARIFICATION_CONFLICT = "COGNITIVE_CLARIFICATION_NOT_AUTHORITATIVE"
PERSPECTIVE_NOT_AUTHORITATIVE_CONFLICT = "PERSPECTIVE_PRESENT_NOT_AUTHORITATIVE"
WORKFLOW_AMBIGUITY_CONFLICT = "WORKFLOW_ADMITTED_DESPITE_AMBIGUITY"


STAGE_ORDER = (
    AuthorityStage.USER_INPUT,
    AuthorityStage.CONVERSATION_UNDERSTANDING,
    AuthorityStage.INTENT_RESOLUTION,
    AuthorityStage.PLANNER,
    AuthorityStage.ROUTER,
    AuthorityStage.WORKFLOW_ADMISSION,
    AuthorityStage.CLARIFICATION_AUTHORITY,
    AuthorityStage.WORKFLOW_RUNTIME,
    AuthorityStage.COGNITIVE_RUNTIME,
    AuthorityStage.RESPONSE_GENERATION,
    AuthorityStage.FALLBACK,
    AuthorityStage.RESPONSE_GUARD,
    AuthorityStage.COMMIT,
)


def _audit_id() -> str:
    return f"cognitive_authority_audit_{uuid4().hex}"


def _plain(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if hasattr(value, "__dataclass_fields__"):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, set):
        return [_plain(item) for item in sorted(value, key=str)]
    return deepcopy(value)


def _as_dict(value: Any) -> dict:
    plain = _plain(value)
    return plain if isinstance(plain, dict) else {}


def _as_list(value: Any) -> list:
    plain = _plain(value)
    if isinstance(plain, list):
        return plain
    if plain in (None, "", {}, ()):
        return []
    return [plain]


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


def _confidence_score(value: Any, fallback: Any = None) -> float | None:
    raw = value if value not in (None, "", [], {}) else fallback
    if isinstance(raw, (int, float)):
        return max(0.0, min(1.0, float(raw)))
    text = str(raw or "").strip().upper()
    if text == "HIGH":
        return 0.86
    if text == "MEDIUM":
        return 0.65
    if text == "LOW":
        return 0.25
    return None


def _confidence_label(value: Any, fallback: Any = None) -> str:
    raw = value if value not in (None, "", [], {}) else fallback
    if isinstance(raw, str) and raw.strip():
        return raw.strip().upper()
    score = _confidence_score(raw)
    if score is None:
        return "UNKNOWN"
    if score >= 0.75:
        return "HIGH"
    if score >= 0.55:
        return "MEDIUM"
    return "LOW"


def _is_high(value: Any, fallback: Any = None) -> bool:
    return _confidence_label(value, fallback) == "HIGH" or (_confidence_score(value, fallback) or 0.0) >= 0.75


def _is_low(value: Any, fallback: Any = None) -> bool:
    return _confidence_label(value, fallback) == "LOW" or (_confidence_score(value, fallback) or 0.0) < 0.55


def _workflow_id(workflow: dict) -> str | None:
    state = _as_dict(workflow.get("workflow_state"))
    return (
        workflow.get("workflow_candidate")
        or workflow.get("workflow_id")
        or state.get("workflow_id")
        or state.get("workflow")
        or state.get("current_workflow")
    )


def _workflow_admitted(workflow: dict, selected_workflow: str | None) -> bool:
    action = workflow.get("workflow_action")
    if action in {"start_new", "continue", "complete", "resume"} and bool(selected_workflow or _workflow_id(workflow)):
        return True
    return False


def _workflow_executable(workflow: dict) -> bool:
    readiness = _as_dict(workflow.get("readiness_decision") or workflow.get("workflow_readiness_decision"))
    if "workflow_executable" in readiness:
        return bool(readiness.get("workflow_executable"))
    if workflow.get("workflow_complete"):
        return True
    required = _as_list(workflow.get("required_entities"))
    missing = _as_list(workflow.get("missing_entities"))
    return bool(required and not missing)


def _workflow_admission_gate(route: dict, workflow: dict) -> dict:
    gate = _as_dict(route.get("workflow_admission_gate")) or _as_dict(workflow.get("workflow_admission_gate"))
    return gate


def _response_mode(route: dict, workflow_admitted: bool, fallback_selected: bool) -> tuple[str, str, str, float | None]:
    source = _first_present(route.get("response_source"), route.get("response_source_after_gate"), route.get("response_source_before_gate"), default="")
    raw_mode = _first_present(route.get("selected_response_mode"), route.get("response_mode"), route.get("response_generation_mode"), route.get("reasoning_mode"), default="")
    if source == "clarification_authority":
        return "SITUATION_AWARE_CLARIFICATION", "clarification_authority", "Clarification Authority selected a situation-aware clarification.", 0.88
    if fallback_selected or "fallback" in str(source):
        return ResponseMode.FALLBACK.value, "response_pipeline", "fallback response source selected", 0.8
    if workflow_admitted or source == "workflow_response":
        return ResponseMode.WORKFLOW.value, "workflow_path", "workflow candidate admitted by current route", 0.8
    if source in {"direct_conversation_response", "planner_first_response"}:
        return ResponseMode.DIRECT_CONVERSATION.value, "response_pipeline", f"{source} selected", 0.75
    if raw_mode:
        return str(raw_mode).upper(), "response_pipeline", "response mode from existing diagnostics", None
    if route.get("llm_needed"):
        return ResponseMode.GENERAL_BUSINESS_ANALYSIS.value, "llm_orchestrator", "LLM needed by current route", 0.65
    return ResponseMode.UNKNOWN.value, "unknown", "response mode not available at audit time", None


def _cognitive_runtime_state(business_situation: dict) -> dict:
    diagnostics = _as_dict(business_situation.get("diagnostics"))
    evidence = _as_dict(diagnostics.get("evidence"))
    truth = _as_dict(diagnostics.get("truth"))
    evidence_gap = _as_dict(diagnostics.get("evidence_gap"))
    perspective = _as_dict(diagnostics.get("perspective"))
    consulted = any(bool(item) for item in (business_situation, evidence, truth, evidence_gap, perspective))
    authoritative = False
    material_uncertainty = _as_list(business_situation.get("material_uncertainty"))
    evidence_missing = _as_list(evidence.get("missing_evidence"))
    gap_missing = _as_list(evidence_gap.get("missing_evidence"))
    next_question = _as_dict(evidence_gap.get("next_best_question"))
    perspective_present = bool(perspective)
    perspective_frame_confidence = perspective.get("frame_confidence")
    perspective_selected_frame = perspective.get("selected_frame")
    return {
        "consulted": consulted,
        "authoritative": authoritative,
        "override_reason": "diagnostics_only_runtime_not_used_for_routing_planner_workflow_response_or_commit"
        if consulted
        else "cognitive_runtime_not_available",
        "material_uncertainty": material_uncertainty,
        "material_uncertainty_present": bool(material_uncertainty or evidence_missing or gap_missing),
        "evidence_gap_next_best_question_present": bool(next_question),
        "perspective_present": perspective_present,
        "perspective_diagnostic_only": bool(perspective.get("diagnostic_only") or (_as_dict(perspective.get("diagnostics")).get("diagnostic_only"))),
        "perspective_frame_status": perspective.get("frame_status"),
        "perspective_selected_frame": perspective_selected_frame,
        "perspective_candidate_frames": perspective.get("candidate_frames") or [],
        "perspective_frame_confidence": perspective_frame_confidence,
        "perspective_classification_performed": bool(perspective.get("classification_performed") or (_as_dict(perspective.get("diagnostics")).get("classification_performed"))),
    }


@dataclass
class AuthorityDecisionRecord:
    stage: str
    component: str
    input_summary: Any = None
    decision: Any = None
    authority_role: str = AuthorityRole.OBSERVED.value
    confidence: float | None = None
    reason: str = ""
    overrode: list = field(default_factory=list)
    overridden_by: str | None = None
    diagnostic_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CognitiveAuthorityAudit:
    audit_id: str = field(default_factory=_audit_id)
    audit_version: str = COGNITIVE_AUTHORITY_AUDIT_VERSION
    audit_source: str = COGNITIVE_AUTHORITY_AUDIT_SOURCE
    user_message: str = ""
    authority_chain: list = field(default_factory=list)
    winning_authority: str = "unknown"
    winning_stage: str = AuthorityStage.USER_INPUT.value
    selected_intent: str | None = None
    selected_workflow: str | None = None
    selected_response_mode: str = ResponseMode.UNKNOWN.value
    response_mode_selected_by: str = "unknown"
    response_mode_reason: str = ""
    response_mode_confidence: float | None = None
    workflow_candidate: str | None = None
    workflow_admission_gate_consulted: bool = False
    workflow_admission_gate_decision: str | None = None
    workflow_admission_gate_reason: str | None = None
    workflow_admission_gate_authoritative: bool = False
    workflow_candidate_rejected: bool = False
    workflow_candidate_deferred: bool = False
    workflow_admitted: bool = False
    workflow_admitted_by: str | None = None
    workflow_admission_reason: str = ""
    workflow_required_entities: list = field(default_factory=list)
    workflow_missing_entities: list = field(default_factory=list)
    workflow_executable: bool = False
    language_normalization_consulted: bool = False
    language_normalization_applied: bool = False
    normalized_user_message: str = ""
    clarification_authority_consulted: bool = False
    clarification_authority_used: bool = False
    clarification_decision: str | None = None
    clarification_reason: str | None = None
    clarification_requested_fields: list = field(default_factory=list)
    generic_fallback_avoided: bool = False
    workflow_started_before_intent_disambiguation: bool = False
    workflow_started_despite_low_understanding_confidence: bool = False
    cognitive_runtime_consulted: bool = False
    cognitive_runtime_authoritative: bool = False
    cognitive_runtime_override_reason: str = ""
    perspective_classification_performed: bool = False
    perspective_selected_frame: str | None = None
    perspective_candidate_frames: list = field(default_factory=list)
    perspective_frame_confidence: float = 0.0
    perspective_frame_status: str | None = None
    perspective_consulted_by_clarification: bool = False
    perspective_authoritative_for_framing: bool = False
    perspective_authoritative_for_routing: bool = False
    perspective_authoritative_for_workflow: bool = False
    perspective_authoritative_for_response: bool = False
    knowledge_runtime_consulted: bool = False
    knowledge_available: bool = False
    knowledge_primary_ids: list = field(default_factory=list)
    knowledge_secondary_ids: list = field(default_factory=list)
    knowledge_deferred_ids: list = field(default_factory=list)
    knowledge_selection_support: float = 0.0
    knowledge_selection_reason: str = ""
    knowledge_required_metrics: list = field(default_factory=list)
    knowledge_available_metrics: list = field(default_factory=list)
    knowledge_incomplete_metrics: list = field(default_factory=list)
    knowledge_missing_metrics: list = field(default_factory=list)
    knowledge_gap_count: int = 0
    knowledge_next_gap: dict = field(default_factory=dict)
    knowledge_used_by_clarification: bool = False
    knowledge_authoritative_for_relevance: bool = False
    knowledge_authoritative_for_judgment: bool = False
    knowledge_authoritative_for_decision: bool = False
    knowledge_authoritative_for_recommendation: bool = False
    knowledge_gap_prioritization_consulted: bool = False
    knowledge_gap_selected: bool = False
    knowledge_gap_priority_tier: str = ""
    knowledge_skill_bridge_consulted: bool = False
    knowledge_skill_bridge_available: bool = False
    bridge_status: str = ""
    candidate_skill_count: int = 0
    primary_skill_candidate: str | None = None
    secondary_skill_candidates: list = field(default_factory=list)
    deferred_skill_candidates: list = field(default_factory=list)
    excluded_skill_count: int = 0
    skill_selection_status: str = ""
    skill_selection_reason: str = ""
    skill_relevance_strength: str = ""
    skill_readiness_strength: str = ""
    skill_reference_validation_consulted: bool = False
    skill_reference_validation_status: str = ""
    skill_reference_error_count: int = 0
    skill_reference_warning_count: int = 0
    canonical_reference_valid: bool = False
    authority_scope_valid: bool = False
    skill_applicability_evaluated: bool = False
    skill_applicability_status: str = ""
    skill_readiness_evaluated: bool = False
    skill_readiness_status: str = ""
    skill_required_evidence_count: int = 0
    skill_missing_required_evidence: list = field(default_factory=list)
    skill_conflicting_evidence: list = field(default_factory=list)
    skill_stale_evidence: list = field(default_factory=list)
    skill_next_gap: dict = field(default_factory=dict)
    shared_gap_created: bool = False
    shared_gap_origin_layers: list = field(default_factory=list)
    shared_gap_owner: str = ""
    legacy_compatibility_consulted: bool = False
    legacy_skill_detected: bool = False
    legacy_skill_classification: str = ""
    legacy_skill_selected: bool = False
    legacy_fallback_used: bool = False
    legacy_primary_prevented: bool = False
    canonical_replacement_found: bool = False
    legacy_inference_used: bool = False
    legacy_inference_confidence: str = ""
    legacy_authority_restricted: bool = False
    silent_upgrade_prevented: bool = True
    skill_redundancy_detected: bool = False
    skill_redundancy_resolved: bool = False
    skill_dependency_order_applied: bool = False
    generalist_skill_suppressed: bool = False
    workflow_coordination_consulted: bool = False
    workflow_field_overlap_detected: bool = False
    workflow_field_overlap_suppressed: bool = False
    workflow_ownership_preserved: bool = False
    skill_to_clarification_handoff_created: bool = False
    skill_to_judgment_handoff_prepared: bool = False
    judgment_handoff_ready: bool = False
    planner_handoff_blocked: bool = True
    response_owner_selected: str = ""
    authority_trace_complete: bool = False
    authority_conflict_detected: bool = False
    authority_conflict_blocked: bool = False
    cognitive_stop_condition: str = ""
    skill_execution_triggered: bool = False
    judgment_produced: bool = False
    decision_made: bool = False
    planner_invoked: bool = False
    clarification_handoff_created: bool = False
    clarification_handoff_type: str = ""
    clarification_question_intent: str = ""
    clarification_handoff_used: bool = False
    duplicate_question_suppressed: bool = False
    workflow_field_conflict_avoided: bool = False
    fallback_selected: bool = False
    fallback_source: str | None = None
    response_source: str | None = None
    commit_source: str | None = None
    authority_conflicts: list = field(default_factory=list)
    diagnostic_summary: dict = field(default_factory=dict)
    constitutional_invariants: dict = field(default_factory=dict)
    runtime_mode: str = "diagnostics_only"
    diagnostic_only: bool = True
    runtime_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _constitutional_invariants() -> dict:
    return {
        "routing_changed": False,
        "workflow_admission_changed": True,
        "language_understanding_input_changed": True,
        "clarification_response_changed": True,
        "response_source_for_blocked_workflow_changed": True,
        "generic_fallback_avoidance_changed": True,
        "routing_outcome_for_blocked_workflow_candidates_changed": True,
        "planner_changed": False,
        "planner_logic_changed": False,
        "workflow_changed": False,
        "workflow_internal_logic_changed": False,
        "responses_changed": False,
        "fallback_changed": False,
        "execution_changed": False,
        "execution_engine_changed": False,
        "commit_changed": False,
        "commit_boundary_changed": False,
        "business_memory_changed": False,
        "business_memory_schema_changed": False,
        "business_situation_changed": False,
        "cognitive_authority_changed": False,
        "perspective_logic_changed": False,
        "perspective_classification_changed": True,
        "perspective_runtime_behavior_changed": True,
        "clarification_context_changed": True,
        "knowledge_invoked": False,
        "judgment_invoked": False,
        "decision_invoked": False,
        "recommendations_generated": False,
        "root_causes_diagnosed": False,
    }


def _records_for_route(
    route: dict,
    *,
    user_message: str,
    selected_intent: str | None,
    selected_workflow: str | None,
    workflow_admitted: bool,
    workflow_executable: bool,
    cognitive: dict,
    selected_response_mode: str,
    response_source: str | None,
    fallback_selected: bool,
    commit_source: str | None,
) -> list[dict]:
    understanding = _as_dict(route.get("conversation_understanding"))
    intent_resolution = _as_dict(route.get("intent_resolution"))
    planner = _as_dict(route.get("planner_output"))
    workflow = _as_dict(route.get("business_workflow"))
    admission_gate = _workflow_admission_gate(route, workflow)
    clarification = _as_dict(route.get("clarification_authority"))
    business_situation = _as_dict(route.get("business_situation") or planner.get("business_situation"))
    knowledge = _as_dict(_as_dict(business_situation.get("diagnostics")).get("knowledge"))
    next_gap = _as_dict(knowledge.get("next_knowledge_gap"))
    handoff = _as_dict(knowledge.get("clarification_handoff"))
    gate = {
        "final_response_gate": route.get("final_response_gate"),
        "workflow_response_allowed": route.get("workflow_response_allowed"),
        "workflow_response_blocked_reason": route.get("workflow_response_blocked_reason"),
    }
    records = [
        AuthorityDecisionRecord(
            stage=AuthorityStage.USER_INPUT.value,
            component="runtime_input",
            input_summary=user_message,
            decision="message_observed" if user_message else "missing_message",
            authority_role=AuthorityRole.OBSERVED.value,
            confidence=1.0 if user_message else 0.0,
            reason="User message is the observed reality input.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.CONVERSATION_UNDERSTANDING.value,
            component="conversation_understanding_engine",
            input_summary=understanding.get("raw_text"),
            decision=understanding.get("detected_intent"),
            authority_role=AuthorityRole.OVERRIDDEN.value if selected_intent and selected_intent != understanding.get("detected_intent") else AuthorityRole.ADVISORY.value,
            confidence=_confidence_score(understanding.get("confidence_score"), understanding.get("confidence")),
            reason="Conversation Understanding normalizes the turn but does not own final routing.",
            overridden_by=AuthorityStage.INTENT_RESOLUTION.value if selected_intent and selected_intent != understanding.get("detected_intent") else None,
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.INTENT_RESOLUTION.value,
            component=intent_resolution.get("source") or "intent_resolver",
            input_summary={
                "understanding_intent": understanding.get("detected_intent"),
                "business_context_intent": (_as_dict(route.get("business_context"))).get("detected_intent"),
            },
            decision=selected_intent,
            authority_role=AuthorityRole.AUTHORITATIVE.value if selected_intent else AuthorityRole.NOT_APPLICABLE.value,
            confidence=_confidence_score(intent_resolution.get("confidence_score"), intent_resolution.get("confidence")),
            reason="Resolver-selected intent is used by planner and workflow path.",
            overrode=[AuthorityStage.CONVERSATION_UNDERSTANDING.value] if selected_intent and selected_intent != understanding.get("detected_intent") else [],
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.PLANNER.value,
            component="planner_engine",
            input_summary=intent_resolution.get("planner_message"),
            decision={"task_type": planner.get("task_type"), "workflow": planner.get("workflow")},
            authority_role=AuthorityRole.AUTHORITATIVE.value if planner else AuthorityRole.NOT_CONSULTED.value,
            confidence=_confidence_score(planner.get("confidence")),
            reason="Existing planner output remains authoritative for task and workflow candidate.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.ROUTER.value,
            component="task_router.workflow_response_gate",
            input_summary=gate,
            decision=gate.get("final_response_gate"),
            authority_role=AuthorityRole.AUTHORITATIVE.value,
            confidence=None,
            reason="Existing router/gate diagnostics are observed without changing route decisions.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.WORKFLOW_ADMISSION.value,
            component="workflow_admission_gate" if admission_gate else "business_workflow_engine",
            input_summary={"candidate": selected_workflow, "action": workflow.get("workflow_action")},
            decision={
                "workflow_admitted": workflow_admitted,
                "workflow_executable": workflow_executable,
                "gate_decision": admission_gate.get("decision"),
            },
            authority_role=AuthorityRole.AUTHORITATIVE.value if workflow_admitted or admission_gate.get("decision") in {"REJECT_TO_CONVERSATION", "DEFER_FOR_CLARIFICATION"} else AuthorityRole.NOT_APPLICABLE.value,
            confidence=_confidence_score(admission_gate.get("admission_confidence"), workflow.get("workflow_confidence")),
            reason=admission_gate.get("reason") or workflow.get("workflow_reason") or "No workflow admission reason recorded.",
            diagnostic_only=False if admission_gate else True,
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.CLARIFICATION_AUTHORITY.value,
            component="clarification_authority",
            input_summary={
                "gate_decision": admission_gate.get("decision"),
                "gate_reason": admission_gate.get("reason"),
                "requested_fields": clarification.get("requested_fields") or [],
            },
            decision=clarification.get("decision") or "not_consulted",
            authority_role=AuthorityRole.AUTHORITATIVE.value
            if clarification.get("decision") == "USE_SPECIFIC_CLARIFICATION"
            else AuthorityRole.NOT_APPLICABLE.value,
            confidence=_confidence_score(clarification.get("response_confidence")),
            reason=clarification.get("reason") or "Clarification Authority not used.",
            diagnostic_only=False if clarification.get("decision") == "USE_SPECIFIC_CLARIFICATION" else True,
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.KNOWLEDGE_RUNTIME.value,
            component="knowledge_runtime",
            input_summary={"selected_frame": knowledge.get("selected_frame")},
            decision={
                "primary_knowledge": [item.get("knowledge_id") for item in _as_list(knowledge.get("primary_knowledge")) if isinstance(item, dict)],
                "secondary_knowledge": [item.get("knowledge_id") for item in _as_list(knowledge.get("secondary_knowledge")) if isinstance(item, dict)],
            },
            authority_role=AuthorityRole.AUTHORITATIVE.value if knowledge.get("knowledge_available") else AuthorityRole.NOT_CONSULTED.value,
            confidence=_confidence_score(knowledge.get("selection_support_strength")),
            reason="Knowledge is authoritative for relevance and evidence requirements only.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.KNOWLEDGE_GAP_PRIORITIZATION.value,
            component="knowledge_runtime.gap_prioritization",
            input_summary={"gap_count": len(_as_list(knowledge.get("knowledge_gaps")))},
            decision=next_gap,
            authority_role=AuthorityRole.AUTHORITATIVE.value if next_gap else AuthorityRole.NOT_APPLICABLE.value,
            confidence=_confidence_score(next_gap.get("priority_strength")),
            reason="Knowledge Gap Prioritization is authoritative for the next evidence need only.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.CLARIFICATION_HANDOFF.value,
            component="knowledge_runtime.clarification_handoff",
            input_summary={"source_gap_id": handoff.get("source_gap_id")},
            decision={"handoff_type": handoff.get("handoff_type"), "question_intent": handoff.get("question_intent")},
            authority_role=AuthorityRole.ADVISORY.value if handoff and handoff.get("handoff_type") != "NO_CLARIFICATION_NEEDED" else AuthorityRole.NOT_APPLICABLE.value,
            confidence=_confidence_score(handoff.get("handoff_support_strength")),
            reason="Clarification handoff supplies context; Clarification Authority owns wording.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.WORKFLOW_RUNTIME.value,
            component="workflow_runtime",
            input_summary=_as_dict(workflow.get("workflow_state")),
            decision={
                "required_entities": workflow.get("required_entities") or [],
                "missing_entities": workflow.get("missing_entities") or [],
                "workflow_complete": bool(workflow.get("workflow_complete")),
            },
            authority_role=AuthorityRole.AUTHORITATIVE.value if workflow_admitted else AuthorityRole.NOT_APPLICABLE.value,
            confidence=_confidence_score(workflow.get("workflow_confidence")),
            reason="Current workflow runtime computes entity progress and next collection state.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.COGNITIVE_RUNTIME.value,
            component="business_situation_diagnostics",
            input_summary={
                "material_uncertainty_present": cognitive["material_uncertainty_present"],
                "evidence_gap_next_best_question_present": cognitive["evidence_gap_next_best_question_present"],
                "perspective_present": cognitive["perspective_present"],
            },
            decision="diagnostics_only_non_authoritative" if cognitive["consulted"] else "not_consulted",
            authority_role=AuthorityRole.ADVISORY.value if cognitive["consulted"] else AuthorityRole.NOT_CONSULTED.value,
            confidence=None,
            reason=cognitive["override_reason"],
            overridden_by=AuthorityStage.WORKFLOW_ADMISSION.value if workflow_admitted else AuthorityStage.RESPONSE_GENERATION.value,
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.RESPONSE_GENERATION.value,
            component="response_pipeline",
            input_summary={"response_source": response_source, "response_mode": selected_response_mode},
            decision=selected_response_mode,
            authority_role=AuthorityRole.AUTHORITATIVE.value if response_source or selected_response_mode != ResponseMode.UNKNOWN.value else AuthorityRole.NOT_APPLICABLE.value,
            confidence=None,
            reason="Current response source/mode is recorded after existing selection.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.FALLBACK.value,
            component="fallback_pipeline",
            input_summary={"fallback_selected": fallback_selected},
            decision=response_source if fallback_selected else None,
            authority_role=AuthorityRole.AUTHORITATIVE.value if fallback_selected else AuthorityRole.NOT_APPLICABLE.value,
            confidence=None,
            reason="Fallback is observed only when existing response source indicates fallback.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.RESPONSE_GUARD.value,
            component="response_guard",
            input_summary={"response_gate_applied": bool(route.get("response_gate_applied"))},
            decision=route.get("response_source_after_gate") or response_source,
            authority_role=AuthorityRole.AUTHORITATIVE.value if route.get("response_gate_applied") else AuthorityRole.NOT_APPLICABLE.value,
            confidence=None,
            reason="Response guard/gate is observed when existing diagnostics say it changed source.",
        ),
        AuthorityDecisionRecord(
            stage=AuthorityStage.COMMIT.value,
            component="response_commit_boundary",
            input_summary={"commit_source": commit_source},
            decision=commit_source,
            authority_role=AuthorityRole.AUTHORITATIVE.value if commit_source else AuthorityRole.NOT_APPLICABLE.value,
            confidence=None,
            reason="Commit source is populated after the existing commit boundary runs.",
        ),
    ]
    return [record.to_dict() for record in records]


def _conflicts(
    route: dict,
    *,
    selected_intent: str | None,
    selected_workflow: str | None,
    workflow_admitted: bool,
    workflow_executable: bool,
    cognitive: dict,
) -> list[dict]:
    understanding = _as_dict(route.get("conversation_understanding"))
    intent_resolution = _as_dict(route.get("intent_resolution"))
    conflicts: list[dict] = []
    understanding_intent = understanding.get("detected_intent")
    if (
        understanding_intent
        and selected_intent
        and understanding_intent != selected_intent
        and _is_low(understanding.get("confidence_score"), understanding.get("confidence"))
        and _is_high(intent_resolution.get("confidence_score"), intent_resolution.get("confidence"))
        and not workflow_executable
    ):
        conflicts.append(
            {
                "authority_conflict_type": LOW_CONFIDENCE_CONFLICT,
                "from_stage": AuthorityStage.CONVERSATION_UNDERSTANDING.value,
                "to_stage": AuthorityStage.INTENT_RESOLUTION.value,
                "diagnostic_only": True,
                "details": {
                    "conversation_understanding": understanding_intent,
                    "understanding_confidence": understanding.get("confidence"),
                    "intent_resolution": selected_intent,
                    "resolver_confidence": intent_resolution.get("confidence"),
                },
            }
        )
    ambiguous = bool(
        understanding.get("clarification_required")
        or _is_low(understanding.get("confidence_score"), understanding.get("confidence"))
        or understanding_intent in {None, "", "unknown"}
    )
    if workflow_admitted and ambiguous and not workflow_executable:
        conflicts.append(
            {
                "authority_conflict_type": WORKFLOW_AMBIGUITY_CONFLICT,
                "from_stage": AuthorityStage.CONVERSATION_UNDERSTANDING.value,
                "to_stage": AuthorityStage.WORKFLOW_ADMISSION.value,
                "diagnostic_only": True,
                "details": {
                    "understanding_intent": understanding_intent,
                    "understanding_confidence": understanding.get("confidence"),
                    "selected_workflow": selected_workflow,
                    "workflow_executable": workflow_executable,
                },
            }
        )
    if workflow_admitted and cognitive["material_uncertainty_present"] and not workflow_executable:
        conflicts.append(
            {
                "authority_conflict_type": WORKFLOW_UNCERTAINTY_CONFLICT,
                "from_stage": AuthorityStage.COGNITIVE_RUNTIME.value,
                "to_stage": AuthorityStage.WORKFLOW_ADMISSION.value,
                "diagnostic_only": True,
                "details": {"selected_workflow": selected_workflow},
            }
        )
    if workflow_admitted and cognitive["evidence_gap_next_best_question_present"] and not workflow_executable:
        conflicts.append(
            {
                "authority_conflict_type": COGNITIVE_CLARIFICATION_CONFLICT,
                "from_stage": AuthorityStage.COGNITIVE_RUNTIME.value,
                "to_stage": AuthorityStage.WORKFLOW_ADMISSION.value,
                "diagnostic_only": True,
                "details": {"selected_workflow": selected_workflow},
            }
        )
    if cognitive["perspective_present"] and cognitive["perspective_diagnostic_only"]:
        conflicts.append(
            {
                "authority_conflict_type": PERSPECTIVE_NOT_AUTHORITATIVE_CONFLICT,
                "from_stage": "Perspective",
                "to_stage": AuthorityStage.RESPONSE_GENERATION.value,
                "diagnostic_only": True,
                "details": {"frame_status": cognitive.get("perspective_frame_status")},
            }
        )
    return conflicts


def _winning_authority(
    *,
    commit_source: str | None,
    response_source: str | None,
    workflow_admitted: bool,
    selected_workflow: str | None,
    planner_workflow: str | None,
    selected_intent: str | None,
    workflow_admission_gate: dict | None = None,
    clarification_authority: dict | None = None,
) -> tuple[str, str]:
    if commit_source:
        return commit_source, AuthorityStage.COMMIT.value
    clarification = clarification_authority or {}
    if (
        clarification.get("decision") == "USE_SPECIFIC_CLARIFICATION"
        and clarification.get("reason") == "ANALYTICAL_RELATIONSHIP_NEEDS_EVIDENCE"
    ):
        return "clarification_authority", AuthorityStage.CLARIFICATION_AUTHORITY.value
    gate = workflow_admission_gate or {}
    if (
        response_source == "clarification_authority"
        and gate.get("decision") in {"REJECT_TO_CONVERSATION", "DEFER_FOR_CLARIFICATION"}
        and gate.get("workflow_candidate")
    ):
        return "workflow_admission_gate", AuthorityStage.WORKFLOW_ADMISSION.value
    if response_source:
        return response_source, AuthorityStage.RESPONSE_GENERATION.value
    if gate.get("decision") in {"REJECT_TO_CONVERSATION", "DEFER_FOR_CLARIFICATION"} and gate.get("workflow_candidate"):
        return "workflow_admission_gate", AuthorityStage.WORKFLOW_ADMISSION.value
    if workflow_admitted:
        return "workflow_path", AuthorityStage.WORKFLOW_ADMISSION.value
    if planner_workflow:
        return "planner", AuthorityStage.PLANNER.value
    if selected_workflow:
        return "workflow_candidate", AuthorityStage.PLANNER.value
    if selected_intent:
        return "intent_resolver", AuthorityStage.INTENT_RESOLUTION.value
    return "conversation_understanding", AuthorityStage.CONVERSATION_UNDERSTANDING.value


def build_cognitive_authority_audit(task_route: dict | None = None, **overrides: Any) -> dict:
    """Build diagnostics-only authority handoff audit from an existing route.

    The audit reads already-produced decisions. It must not classify, route,
    plan, admit workflows, generate responses, execute, or commit.
    """

    route = _as_dict(task_route)
    understanding = _as_dict(route.get("conversation_understanding"))
    intent_resolution = _as_dict(route.get("intent_resolution"))
    planner = _as_dict(route.get("planner_output"))
    workflow = _as_dict(route.get("business_workflow"))
    admission_gate = _workflow_admission_gate(route, workflow)
    language_normalization = _as_dict(route.get("language_normalization"))
    clarification_authority = _as_dict(route.get("clarification_authority"))
    business_situation = _as_dict(route.get("business_situation") or planner.get("business_situation"))
    knowledge_runtime = _as_dict(_as_dict(business_situation.get("diagnostics")).get("knowledge"))
    knowledge_skill_bridge = _as_dict(_as_dict(business_situation.get("diagnostics")).get("knowledge_skill_bridge"))
    knowledge_diagnostics = _as_dict(knowledge_runtime.get("diagnostics"))
    knowledge_next_gap = _as_dict(knowledge_runtime.get("next_knowledge_gap"))
    clarification_handoff = _as_dict(knowledge_runtime.get("clarification_handoff"))
    primary_skill = _as_dict(knowledge_skill_bridge.get("primary_skill_candidate"))
    primary_readiness = _as_dict(primary_skill.get("evidence_readiness_result"))
    primary_applicability = _as_dict(primary_skill.get("applicability_result"))
    next_shared_gap = _as_dict(knowledge_skill_bridge.get("next_shared_gap"))
    bridge_workflow = _as_dict(knowledge_skill_bridge.get("workflow_coordination"))
    bridge_judgment = _as_dict(knowledge_skill_bridge.get("judgment_handoff"))
    bridge_planner = _as_dict(knowledge_skill_bridge.get("planner_handoff"))
    bridge_issues = _as_list(primary_skill.get("validation_issues"))
    user_message = str(_first_present(overrides.get("user_message"), route.get("user_message"), understanding.get("raw_text"), default="") or "")
    selected_intent = _first_present(overrides.get("selected_intent"), intent_resolution.get("resolved_intent"), default=None)
    selected_workflow = _first_present(
        overrides.get("selected_workflow"),
        planner.get("workflow"),
        intent_resolution.get("resolved_workflow"),
        _workflow_id(workflow),
        default=None,
    )
    workflow_candidate = _first_present(overrides.get("workflow_candidate"), selected_workflow, _workflow_id(workflow), default=None)
    admitted = bool(overrides.get("workflow_admitted")) if "workflow_admitted" in overrides else _workflow_admitted(workflow, selected_workflow)
    executable = bool(overrides.get("workflow_executable")) if "workflow_executable" in overrides else _workflow_executable(workflow)
    required_entities = _as_list(_first_present(workflow.get("required_entities"), (_as_dict(workflow.get("workflow_state"))).get("required_entities"), default=[]))
    missing_entities = _as_list(_first_present(workflow.get("missing_entities"), (_as_dict(workflow.get("readiness_decision"))).get("missing_fields"), default=[]))
    response_source = _first_present(
        overrides.get("response_source"),
        route.get("response_source"),
        route.get("response_source_after_gate"),
        route.get("response_source_before_gate"),
        default=None,
    )
    fallback_selected = bool(overrides.get("fallback_selected")) if "fallback_selected" in overrides else "fallback" in str(response_source or "")
    fallback_source = _first_present(overrides.get("fallback_source"), response_source if fallback_selected else None, default=None)
    commit_source = _first_present(overrides.get("commit_source"), route.get("commit_source"), default=None)
    cognitive = _cognitive_runtime_state(business_situation)
    response_mode, response_mode_by, response_mode_reason, response_mode_confidence = _response_mode(route, admitted, fallback_selected)
    if overrides.get("selected_response_mode"):
        response_mode = str(overrides.get("selected_response_mode"))
    if overrides.get("response_mode_selected_by"):
        response_mode_by = str(overrides.get("response_mode_selected_by"))
    winning_authority, winning_stage = _winning_authority(
        commit_source=commit_source,
        response_source=response_source,
        workflow_admitted=admitted,
        selected_workflow=selected_workflow,
        planner_workflow=planner.get("workflow"),
        selected_intent=selected_intent,
        workflow_admission_gate=admission_gate,
        clarification_authority=clarification_authority,
    )
    chain = _records_for_route(
        route,
        user_message=user_message,
        selected_intent=selected_intent,
        selected_workflow=selected_workflow,
        workflow_admitted=admitted,
        workflow_executable=executable,
        cognitive=cognitive,
        selected_response_mode=response_mode,
        response_source=response_source,
        fallback_selected=fallback_selected,
        commit_source=commit_source,
    )
    conflicts = _conflicts(
        route,
        selected_intent=selected_intent,
        selected_workflow=selected_workflow,
        workflow_admitted=admitted,
        workflow_executable=executable,
        cognitive=cognitive,
    )
    low_understanding = _is_low(understanding.get("confidence_score"), understanding.get("confidence"))
    audit = CognitiveAuthorityAudit(
        user_message=user_message,
        authority_chain=chain,
        winning_authority=winning_authority,
        winning_stage=winning_stage,
        selected_intent=selected_intent,
        selected_workflow=selected_workflow,
        selected_response_mode=response_mode,
        response_mode_selected_by=response_mode_by,
        response_mode_reason=response_mode_reason,
        response_mode_confidence=response_mode_confidence,
        workflow_candidate=workflow_candidate,
        workflow_admission_gate_consulted=bool(admission_gate),
        workflow_admission_gate_decision=admission_gate.get("decision"),
        workflow_admission_gate_reason=admission_gate.get("reason"),
        workflow_admission_gate_authoritative=bool(admission_gate.get("decision") in {"ADMIT", "REJECT_TO_CONVERSATION", "DEFER_FOR_CLARIFICATION"}),
        workflow_candidate_rejected=admission_gate.get("decision") == "REJECT_TO_CONVERSATION",
        workflow_candidate_deferred=admission_gate.get("decision") == "DEFER_FOR_CLARIFICATION",
        workflow_admitted=admitted,
        workflow_admitted_by="workflow_admission_gate" if admitted and admission_gate else "business_workflow_engine" if admitted else None,
        workflow_admission_reason=admission_gate.get("reason") or workflow.get("workflow_reason") or "",
        workflow_required_entities=required_entities,
        workflow_missing_entities=missing_entities,
        workflow_executable=executable,
        language_normalization_consulted=bool(language_normalization),
        language_normalization_applied=bool(language_normalization.get("normalization_count")),
        normalized_user_message=language_normalization.get("normalized_text") or "",
        clarification_authority_consulted=bool(clarification_authority),
        clarification_authority_used=clarification_authority.get("decision") == "USE_SPECIFIC_CLARIFICATION",
        clarification_decision=clarification_authority.get("decision"),
        clarification_reason=clarification_authority.get("reason"),
        clarification_requested_fields=clarification_authority.get("requested_fields") or [],
        generic_fallback_avoided=bool(
            clarification_authority.get("decision") == "USE_SPECIFIC_CLARIFICATION"
            and not clarification_authority.get("fallback_used")
        ),
        workflow_started_before_intent_disambiguation=bool(admitted and understanding.get("clarification_required")),
        workflow_started_despite_low_understanding_confidence=bool(admitted and low_understanding),
        cognitive_runtime_consulted=bool(cognitive["consulted"]),
        cognitive_runtime_authoritative=bool(cognitive["authoritative"]),
        cognitive_runtime_override_reason=cognitive["override_reason"],
        perspective_classification_performed=bool(cognitive.get("perspective_classification_performed")),
        perspective_selected_frame=cognitive.get("perspective_selected_frame"),
        perspective_candidate_frames=cognitive.get("perspective_candidate_frames") or [],
        perspective_frame_confidence=float(cognitive.get("perspective_frame_confidence") or 0.0),
        perspective_frame_status=cognitive.get("perspective_frame_status"),
        perspective_consulted_by_clarification=bool(clarification_authority.get("perspective_consulted")),
        perspective_authoritative_for_framing=bool(cognitive.get("perspective_selected_frame") and cognitive.get("perspective_selected_frame") != "UNKNOWN_SITUATION"),
        perspective_authoritative_for_routing=False,
        perspective_authoritative_for_workflow=False,
        perspective_authoritative_for_response=bool(
            clarification_authority.get("decision") == "USE_SPECIFIC_CLARIFICATION"
            and clarification_authority.get("perspective_used_for_framing")
        ),
        knowledge_runtime_consulted=bool(knowledge_runtime),
        knowledge_available=bool(knowledge_runtime.get("knowledge_available")),
        knowledge_primary_ids=[item.get("knowledge_id") for item in _as_list(knowledge_runtime.get("primary_knowledge")) if isinstance(item, dict)],
        knowledge_secondary_ids=[item.get("knowledge_id") for item in _as_list(knowledge_runtime.get("secondary_knowledge")) if isinstance(item, dict)],
        knowledge_deferred_ids=[item.get("knowledge_id") for item in _as_list(knowledge_runtime.get("deferred_knowledge")) if isinstance(item, dict)],
        knowledge_selection_support=float(knowledge_runtime.get("selection_support_strength") or 0.0),
        knowledge_selection_reason=knowledge_runtime.get("selection_reason") or "",
        knowledge_required_metrics=knowledge_runtime.get("relevant_metrics") or [],
        knowledge_available_metrics=sorted((_as_dict(knowledge_runtime.get("available_metrics"))).keys()),
        knowledge_incomplete_metrics=sorted((_as_dict(knowledge_runtime.get("incomplete_metrics"))).keys()),
        knowledge_missing_metrics=knowledge_runtime.get("missing_metrics") or [],
        knowledge_gap_count=len(_as_list(knowledge_runtime.get("knowledge_gaps"))),
        knowledge_next_gap=knowledge_next_gap,
        knowledge_used_by_clarification=bool(clarification_authority.get("knowledge_used_for_gap")),
        knowledge_authoritative_for_relevance=bool(knowledge_runtime),
        knowledge_authoritative_for_judgment=False,
        knowledge_authoritative_for_decision=False,
        knowledge_authoritative_for_recommendation=False,
        knowledge_gap_prioritization_consulted=bool(knowledge_runtime),
        knowledge_gap_selected=bool(knowledge_next_gap),
        knowledge_gap_priority_tier=knowledge_next_gap.get("priority_tier") or "",
        knowledge_skill_bridge_consulted=bool(knowledge_skill_bridge.get("bridge_consulted")),
        knowledge_skill_bridge_available=bool(knowledge_skill_bridge),
        bridge_status=knowledge_skill_bridge.get("bridge_status") or "",
        candidate_skill_count=len(_as_list(knowledge_skill_bridge.get("candidate_skills"))),
        primary_skill_candidate=primary_skill.get("skill_id"),
        secondary_skill_candidates=[item.get("skill_id") for item in _as_list(knowledge_skill_bridge.get("secondary_skill_candidates")) if isinstance(item, dict)],
        deferred_skill_candidates=[item.get("skill_id") for item in _as_list(knowledge_skill_bridge.get("deferred_skill_candidates")) if isinstance(item, dict)],
        excluded_skill_count=len(_as_list(knowledge_skill_bridge.get("excluded_skill_candidates"))),
        skill_selection_status="PRIMARY_SELECTED_BUT_BLOCKED" if knowledge_skill_bridge.get("bridge_status") == "PRIMARY_SKILL_SELECTED_BUT_BLOCKED" else "PRIMARY_SELECTED" if primary_skill else "NO_SAFE_PRIMARY_CANDIDATE",
        skill_selection_reason=primary_skill.get("selection_reason") or knowledge_skill_bridge.get("bridge_status") or "",
        skill_relevance_strength=primary_skill.get("relevance_strength") or "",
        skill_readiness_strength=primary_skill.get("readiness_strength") or "",
        skill_reference_validation_consulted=bool(knowledge_skill_bridge),
        skill_reference_validation_status=primary_skill.get("reference_validation_status") or "",
        skill_reference_error_count=len([item for item in bridge_issues if isinstance(item, dict) and item.get("severity") == "ERROR"]),
        skill_reference_warning_count=len([item for item in bridge_issues if isinstance(item, dict) and item.get("severity") == "WARNING"]),
        canonical_reference_valid=bool(primary_skill and primary_skill.get("reference_validation_status") == "VALID"),
        authority_scope_valid=bool(primary_skill and primary_skill.get("authority_scope")),
        skill_applicability_evaluated=bool(primary_applicability),
        skill_applicability_status=primary_applicability.get("status") or "",
        skill_readiness_evaluated=bool(primary_readiness),
        skill_readiness_status=primary_readiness.get("status") or "",
        skill_required_evidence_count=len(_as_list(primary_readiness.get("required_evidence"))),
        skill_missing_required_evidence=_as_list(primary_readiness.get("missing_required_evidence")),
        skill_conflicting_evidence=_as_list(primary_readiness.get("conflicting_required_evidence")),
        skill_stale_evidence=_as_list(primary_readiness.get("stale_required_evidence")),
        skill_next_gap=_as_dict(primary_readiness.get("next_evidence_gap")),
        shared_gap_created=bool(next_shared_gap),
        shared_gap_origin_layers=_as_list(next_shared_gap.get("origin_layers")),
        shared_gap_owner=next_shared_gap.get("question_owner") or "",
        legacy_compatibility_consulted=True,
        workflow_coordination_consulted=bool(bridge_workflow),
        workflow_field_overlap_detected=bool(bridge_workflow.get("overlapping_skill_fields")),
        workflow_field_overlap_suppressed=bool(bridge_workflow.get("suppressed_skill_questions")),
        workflow_ownership_preserved=bool(bridge_workflow.get("coordination_status") in {"WORKFLOW_OWNS_COLLECTION", "SKILL_SUPPORTS_WORKFLOW", "NO_ACTIVE_WORKFLOW"}),
        skill_to_clarification_handoff_created=bool(knowledge_skill_bridge.get("clarification_handoff")),
        skill_to_judgment_handoff_prepared=bool(bridge_judgment),
        judgment_handoff_ready=bridge_judgment.get("ready_for_judgment") == "READY_FOR_JUDGMENT",
        planner_handoff_blocked=not bool(bridge_planner.get("planning_allowed")),
        response_owner_selected="CLARIFICATION_AUTHORITY" if clarification_authority.get("decision") == "USE_SPECIFIC_CLARIFICATION" else "WORKFLOW" if admitted else "SYSTEM",
        authority_trace_complete=bool(knowledge_skill_bridge.get("authority_trace")),
        cognitive_stop_condition=knowledge_skill_bridge.get("bridge_status") or "",
        skill_execution_triggered=False,
        judgment_produced=False,
        decision_made=False,
        planner_invoked=False,
        clarification_handoff_created=bool(clarification_handoff and clarification_handoff.get("handoff_type") != "NO_CLARIFICATION_NEEDED"),
        clarification_handoff_type=clarification_handoff.get("handoff_type") or "",
        clarification_question_intent=clarification_handoff.get("question_intent") or "",
        clarification_handoff_used=bool(clarification_authority.get("knowledge_used_for_gap")),
        duplicate_question_suppressed=bool(clarification_authority.get("duplicate_guard_applied")),
        workflow_field_conflict_avoided=bool(
            clarification_authority.get("decision") == "NO_CLARIFICATION_NEEDED"
            and admission_gate.get("decision") == "ADMIT"
        ),
        fallback_selected=fallback_selected,
        fallback_source=fallback_source,
        response_source=response_source,
        commit_source=commit_source,
        authority_conflicts=conflicts,
        diagnostic_summary={
            "conversation_understanding": {
                "detected_intent": understanding.get("detected_intent"),
                "confidence": understanding.get("confidence"),
                "confidence_score": understanding.get("confidence_score"),
                "clarification_required": bool(understanding.get("clarification_required")),
            },
            "intent_resolution": {
                "resolved_intent": selected_intent,
                "confidence": intent_resolution.get("confidence"),
                "confidence_score": intent_resolution.get("confidence_score"),
                "resolved_workflow": intent_resolution.get("resolved_workflow"),
            },
            "planner_authority": {
                "task_type": planner.get("task_type"),
                "workflow": planner.get("workflow"),
                "next_step": planner.get("next_step"),
            },
            "workflow_path": {
                "workflow_candidate": workflow_candidate,
                "workflow_admitted": admitted,
                "workflow_executable": executable,
                "missing_entities": missing_entities,
            },
            "workflow_admission_gate": {
                "consulted": bool(admission_gate),
                "decision": admission_gate.get("decision"),
                "reason": admission_gate.get("reason"),
                "authoritative": bool(admission_gate.get("decision") in {"ADMIT", "REJECT_TO_CONVERSATION", "DEFER_FOR_CLARIFICATION"}),
                "workflow_candidate_rejected": admission_gate.get("decision") == "REJECT_TO_CONVERSATION",
                "workflow_candidate_deferred": admission_gate.get("decision") == "DEFER_FOR_CLARIFICATION",
                "admitted": admission_gate.get("admitted"),
                "executable_request_detected": admission_gate.get("executable_request_detected"),
                "analytical_question_detected": admission_gate.get("analytical_question_detected"),
                "business_level_scope_detected": admission_gate.get("business_level_scope_detected"),
                "keyword_only_match_detected": admission_gate.get("keyword_only_match_detected"),
                "fallback_target": admission_gate.get("fallback_target"),
            },
            "language_normalization": {
                "consulted": bool(language_normalization),
                "applied": bool(language_normalization.get("normalization_count")),
                "original_text": language_normalization.get("original_text"),
                "normalized_text": language_normalization.get("normalized_text"),
                "normalizations_applied": language_normalization.get("normalizations_applied") or [],
            },
            "clarification_authority": {
                "consulted": bool(clarification_authority),
                "used": clarification_authority.get("decision") == "USE_SPECIFIC_CLARIFICATION",
                "decision": clarification_authority.get("decision"),
                "reason": clarification_authority.get("reason"),
                "requested_fields": clarification_authority.get("requested_fields") or [],
                "generic_fallback_avoided": bool(
                    clarification_authority.get("decision") == "USE_SPECIFIC_CLARIFICATION"
                    and not clarification_authority.get("fallback_used")
                ),
            },
            "knowledge_runtime": {
                "consulted": bool(knowledge_runtime),
                "knowledge_available": bool(knowledge_runtime.get("knowledge_available")),
                "primary_ids": [item.get("knowledge_id") for item in _as_list(knowledge_runtime.get("primary_knowledge")) if isinstance(item, dict)],
                "secondary_ids": [item.get("knowledge_id") for item in _as_list(knowledge_runtime.get("secondary_knowledge")) if isinstance(item, dict)],
                "next_gap": knowledge_next_gap,
                "handoff_type": clarification_handoff.get("handoff_type"),
                "authoritative_for_relevance": bool(knowledge_runtime),
                "authoritative_for_judgment": False,
                "authoritative_for_decision": False,
                "authoritative_for_recommendation": False,
                "diagnostics": knowledge_diagnostics,
            },
            "cognitive_runtime": {
                "consulted": cognitive["consulted"],
                "authoritative": cognitive["authoritative"],
                "material_uncertainty_present": cognitive["material_uncertainty_present"],
                "perspective_present": cognitive["perspective_present"],
                "perspective_classification_performed": cognitive.get("perspective_classification_performed"),
                "perspective_selected_frame": cognitive.get("perspective_selected_frame"),
                "perspective_frame_confidence": cognitive.get("perspective_frame_confidence"),
                "perspective_frame_status": cognitive.get("perspective_frame_status"),
            },
        },
        constitutional_invariants=_constitutional_invariants(),
    )
    return audit.to_dict()


def attach_cognitive_authority_audit(task_route: dict | None, **overrides: Any) -> dict:
    route = task_route if isinstance(task_route, dict) else {}
    audit = build_cognitive_authority_audit(route, **overrides)
    business_situations = [route.get("business_situation")]
    planner_output = route.get("planner_output") if isinstance(route.get("planner_output"), dict) else {}
    planner_situation = planner_output.get("business_situation")
    if planner_situation is not business_situations[0]:
        business_situations.append(planner_situation)
    for business_situation in business_situations:
        if isinstance(business_situation, dict):
            diagnostics = business_situation.setdefault("diagnostics", {})
            diagnostics["cognitive_authority_audit"] = audit
    route["cognitive_authority_audit"] = audit
    return route


def cognitive_authority_trace(audit_or_route: dict | None) -> dict:
    source = _as_dict(audit_or_route)
    audit = source.get("cognitive_authority_audit") or source
    if not isinstance(audit, dict) or not audit.get("audit_version"):
        audit = build_cognitive_authority_audit(source)
    summary = _as_dict(audit.get("diagnostic_summary"))
    return {
        "user_message": audit.get("user_message"),
        "conversation_understanding": summary.get("conversation_understanding") or {},
        "intent_resolution": summary.get("intent_resolution") or {},
        "planner_authority": summary.get("planner_authority") or {},
        "router_authority": {
            "winning_stage": audit.get("winning_stage"),
            "winning_authority": audit.get("winning_authority"),
        },
        "workflow_candidate": audit.get("workflow_candidate"),
        "workflow_admission_gate": summary.get("workflow_admission_gate") or {},
        "workflow_admission_gate_consulted": audit.get("workflow_admission_gate_consulted"),
        "workflow_admission_gate_decision": audit.get("workflow_admission_gate_decision"),
        "workflow_admission_gate_reason": audit.get("workflow_admission_gate_reason"),
        "workflow_admitted": audit.get("workflow_admitted"),
        "language_normalization_consulted": audit.get("language_normalization_consulted"),
        "language_normalization_applied": audit.get("language_normalization_applied"),
        "normalized_user_message": audit.get("normalized_user_message"),
        "clarification_authority_consulted": audit.get("clarification_authority_consulted"),
        "clarification_authority_used": audit.get("clarification_authority_used"),
        "clarification_decision": audit.get("clarification_decision"),
        "clarification_reason": audit.get("clarification_reason"),
        "clarification_requested_fields": audit.get("clarification_requested_fields") or [],
        "generic_fallback_avoided": audit.get("generic_fallback_avoided"),
        "knowledge_runtime_consulted": audit.get("knowledge_runtime_consulted"),
        "knowledge_available": audit.get("knowledge_available"),
        "knowledge_primary_ids": audit.get("knowledge_primary_ids") or [],
        "knowledge_secondary_ids": audit.get("knowledge_secondary_ids") or [],
        "knowledge_next_gap": audit.get("knowledge_next_gap") or {},
        "knowledge_used_by_clarification": audit.get("knowledge_used_by_clarification"),
        "clarification_handoff_type": audit.get("clarification_handoff_type"),
        "response_mode": audit.get("selected_response_mode"),
        "cognitive_runtime_consulted": audit.get("cognitive_runtime_consulted"),
        "cognitive_runtime_authoritative": audit.get("cognitive_runtime_authoritative"),
        "winning_authority": audit.get("winning_authority"),
        "authority_conflicts": [
            item.get("authority_conflict_type")
            for item in _as_list(audit.get("authority_conflicts"))
            if isinstance(item, dict)
        ],
        "response_source": audit.get("response_source"),
        "commit_source": audit.get("commit_source"),
    }
