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
    raw_mode = _first_present(route.get("response_mode"), route.get("response_generation_mode"), route.get("reasoning_mode"), default="")
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
    workflow_started_before_intent_disambiguation: bool = False
    workflow_started_despite_low_understanding_confidence: bool = False
    cognitive_runtime_consulted: bool = False
    cognitive_runtime_authoritative: bool = False
    cognitive_runtime_override_reason: str = ""
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
) -> tuple[str, str]:
    if commit_source:
        return commit_source, AuthorityStage.COMMIT.value
    if response_source:
        return response_source, AuthorityStage.RESPONSE_GENERATION.value
    gate = workflow_admission_gate or {}
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
    business_situation = _as_dict(route.get("business_situation") or planner.get("business_situation"))
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
        workflow_started_before_intent_disambiguation=bool(admitted and understanding.get("clarification_required")),
        workflow_started_despite_low_understanding_confidence=bool(admitted and low_understanding),
        cognitive_runtime_consulted=bool(cognitive["consulted"]),
        cognitive_runtime_authoritative=bool(cognitive["authoritative"]),
        cognitive_runtime_override_reason=cognitive["override_reason"],
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
            "cognitive_runtime": {
                "consulted": cognitive["consulted"],
                "authoritative": cognitive["authoritative"],
                "material_uncertainty_present": cognitive["material_uncertainty_present"],
                "perspective_present": cognitive["perspective_present"],
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
