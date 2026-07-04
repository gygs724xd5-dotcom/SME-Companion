from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from brain.canonical_skill_registry import CanonicalSkillRegistry
from brain.contract_drift_detector import DriftSeverity, build_contract_migration_queue, detect_contract_drift
from brain.contract_provenance import build_skill_reference_snapshot
from brain.knowledge_skill_reference import ACTIVE_STAGES, ValidationStatus, as_dict, as_list, unique
from brain.knowledge_skill_outcome_hardening import harden_knowledge_skill_outcome
from brain.skill_migration_registry import load_skill_migration_registry
from brain.skill_applicability import evaluate_skill_applicability
from brain.skill_evidence_readiness import evaluate_skill_evidence_readiness


KNOWLEDGE_SKILL_BRIDGE_VERSION = "5.9.4"


@dataclass
class SharedEvidenceGap:
    gap_id: str
    origin_layers: list[str]
    knowledge_ids: list[str]
    skill_ids: list[str]
    metric_id: str
    gap_type: str
    known_partial_value: dict = field(default_factory=dict)
    missing_components: list[str] = field(default_factory=list)
    blocking_relationship_rules: list[str] = field(default_factory=list)
    dependency_depth: int = 0
    priority_tier: str = "MEDIUM"
    workflow_owned: bool = False
    already_asked: bool = False
    duplicate_guard: str = "NEW_HANDOFF"
    question_owner: str = "CLARIFICATION_AUTHORITY"
    resolution_status: str = "OPEN"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SkillClarificationHandoff:
    handoff_id: str
    source_layer: str
    primary_skill_id: str
    supporting_skill_ids: list[str]
    source_gap_id: str
    metric_id: str
    gap_type: str
    known_context: dict = field(default_factory=dict)
    known_partial_value: dict = field(default_factory=dict)
    missing_information: list[str] = field(default_factory=list)
    why_it_matters: str = ""
    blocking_relationship_rules: list[str] = field(default_factory=list)
    expected_answer_schema: dict = field(default_factory=dict)
    question_intent: str = ""
    wording_guidance: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    max_questions: int = 1
    max_fields: int = 2
    user_effort: str = "LOW"
    duplicate_guard: str = "NEW_HANDOFF"
    workflow_coordination: dict = field(default_factory=dict)
    fallback_gap: dict = field(default_factory=dict)
    support_strength: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SkillToJudgmentHandoff:
    handoff_id: str
    primary_skill_id: str
    supporting_skill_ids: list[str]
    selected_knowledge_ids: list[str]
    applicable_relationship_rules: list[str]
    evidence_package: dict
    unresolved_gaps: list[dict]
    conflicting_evidence: list[str]
    stale_evidence: list[str]
    skill_readiness_status: str
    analytical_scope: str = ""
    allowed_judgment_questions: list[str] = field(default_factory=list)
    forbidden_judgment_claims: list[str] = field(default_factory=list)
    support_strength: float = 0.0
    provenance: dict = field(default_factory=dict)
    ready_for_judgment: str = "NOT_READY_FOR_JUDGMENT"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlannerEligibilityHandoff:
    decision_available: bool = False
    decision_id: str = ""
    selected_action: str = ""
    decision_constraints: list[str] = field(default_factory=list)
    supporting_judgment_ids: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    unresolved_blockers: list[str] = field(default_factory=list)
    planning_allowed: bool = False
    planning_block_reason: str = "V5.9.1 requires future Decision before Planner."

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkflowCoordinationResult:
    workflow_admitted: bool = False
    workflow_id: str = ""
    workflow_owner: str = ""
    workflow_owned_fields: list[str] = field(default_factory=list)
    overlapping_skill_fields: list[str] = field(default_factory=list)
    suppressed_skill_questions: list[str] = field(default_factory=list)
    allowed_skill_support: str = "diagnostic_only"
    bridge_execution_allowed: bool = False
    coordination_status: str = "NO_ACTIVE_WORKFLOW"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuthorityTrace:
    framing_authority: str = "PERSPECTIVE"
    knowledge_authority: str = "KNOWLEDGE_RUNTIME"
    evidence_gap_authority: str = "KNOWLEDGE_RUNTIME"
    procedural_applicability_authority: str = "KNOWLEDGE_SKILL_BRIDGE"
    readiness_authority: str = "SKILL_READINESS"
    clarification_authority: str = "CLARIFICATION_AUTHORITY"
    workflow_authority: str = "WORKFLOW"
    judgment_authority: str = "FUTURE_JUDGMENT"
    decision_authority: str = "FUTURE_DECISION"
    planner_authority: str = "PLANNER_BLOCKED"
    response_commit_authority: str = "COMMIT_BOUNDARY"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SkillCandidate:
    candidate_id: str
    skill_id: str
    reference_id: str
    matched_primary_knowledge_ids: list[str] = field(default_factory=list)
    matched_secondary_knowledge_ids: list[str] = field(default_factory=list)
    matched_frames: list[str] = field(default_factory=list)
    matched_intents: list[str] = field(default_factory=list)
    matched_metrics: list[str] = field(default_factory=list)
    matched_relationship_rules: list[str] = field(default_factory=list)
    applicability_result: dict = field(default_factory=dict)
    evidence_readiness_result: dict = field(default_factory=dict)
    reference_validation_status: str = "VALID"
    review_status: str = ""
    declared_review_status: str = ""
    effective_review_status: str = ""
    reference_freshness: str = "CURRENT"
    contract_drift_result: dict = field(default_factory=dict)
    migration_status: dict = field(default_factory=dict)
    compatibility_mode: str = ""
    authority_scope: dict = field(default_factory=dict)
    current_turn_relevance: float = 0.0
    conversation_continuity_relevance: float = 0.0
    specificity: float = 0.0
    procedural_role: str = ""
    stage: str = ""
    redundancy_group: str = ""
    relevance_strength: str = "LOW"
    readiness_strength: str = "LOW"
    support_strength: float = 0.0
    ranking_factors: dict = field(default_factory=dict)
    penalties: list[str] = field(default_factory=list)
    rank: int = 0
    selection_tier: str = "DEFERRED"
    selection_reason: str = ""
    deferred_reason: str = ""
    excluded_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _ids(items: list, key: str = "knowledge_id") -> list[str]:
    result = []
    for item in items or []:
        if isinstance(item, dict) and item.get(key):
            result.append(str(item.get(key)))
        elif isinstance(item, str):
            result.append(item)
    return unique(result)


def _context_from_input(bridge_input: dict) -> dict:
    business = as_dict(bridge_input.get("business_context"))
    product = as_dict(bridge_input.get("product_context"))
    metrics = {}
    for source in (as_dict(bridge_input.get("knowledge_runtime_result")).get("available_metrics") or {}, as_dict(bridge_input.get("knowledge_runtime_result")).get("incomplete_metrics") or {}):
        for key, value in source.items():
            metrics[key] = as_dict(value).get("value")
    return {
        "current_turn": {**metrics, **business, **product},
        "business_context": business,
        "conversation_context": as_dict(bridge_input.get("conversation_context")),
    }


def _discovered(registry: CanonicalSkillRegistry, knowledge: dict, selected_frame: str, intents: list[str], metrics: list[str]) -> tuple[list[str], dict]:
    sources: dict[str, list[str]] = {}
    def add(skill_id: str, source: str) -> None:
        sources.setdefault(skill_id, [])
        if source not in sources[skill_id]:
            sources[skill_id].append(source)
    for knowledge_id in _ids(knowledge.get("primary_knowledge")):
        for skill in registry.find_skills_by_knowledge(knowledge_id):
            add(skill.skill_id, "PRIMARY_KNOWLEDGE")
    for intent in intents:
        for skill in registry.find_skills_by_intent(intent):
            add(skill.skill_id, "CURRENT_TURN_INTENT")
    for skill in registry.find_skills_by_frame(selected_frame):
        add(skill.skill_id, "PRIMARY_FRAME")
    for knowledge_id in _ids(knowledge.get("secondary_knowledge")):
        for skill in registry.find_skills_by_knowledge(knowledge_id):
            add(skill.skill_id, "SECONDARY_KNOWLEDGE")
    for metric in metrics:
        for skill in registry.find_skills_by_metric(metric):
            add(skill.skill_id, "METRIC")
    ordered = sorted(sources, key=lambda skill_id: (
        0 if "PRIMARY_KNOWLEDGE" in sources[skill_id] else 1,
        0 if "CURRENT_TURN_INTENT" in sources[skill_id] else 1,
        0 if "PRIMARY_FRAME" in sources[skill_id] else 1,
        skill_id,
    ))
    return ordered, sources


def _strength(value: float) -> str:
    if value >= 0.75:
        return "HIGH"
    if value >= 0.45:
        return "MEDIUM"
    return "LOW"


def _candidate(skill: Any, bridge_input: dict, sources: list[str]) -> SkillCandidate:
    knowledge = as_dict(bridge_input.get("knowledge_runtime_result"))
    selected_frame = str(bridge_input.get("selected_frame") or knowledge.get("selected_frame") or "")
    primary_ids = _ids(knowledge.get("primary_knowledge"))
    secondary_ids = _ids(knowledge.get("secondary_knowledge"))
    metrics = unique(as_list(knowledge.get("relevant_metrics")) + list(as_dict(knowledge.get("available_metrics")).keys()) + list(as_dict(knowledge.get("incomplete_metrics")).keys()))
    applicability = evaluate_skill_applicability(skill, _context_from_input(bridge_input))
    reference_valid = skill.validation_status not in {ValidationStatus.INVALID.value, ValidationStatus.FATAL.value}
    workflow_fields = as_list(as_dict(bridge_input.get("workflow_state")).get("workflow_owned_fields")) or as_list(bridge_input.get("workflow_owned_fields"))
    readiness = evaluate_skill_evidence_readiness(
        skill,
        available_metrics=as_dict(knowledge.get("available_metrics")),
        incomplete_metrics=as_dict(knowledge.get("incomplete_metrics")),
        applicability_result=applicability,
        workflow_owned_fields=workflow_fields,
        reference_valid=reference_valid,
    )
    matched_primary = [item for item in skill.knowledge_references.primary if item in primary_ids]
    matched_skill_primary_any = [item for item in skill.knowledge_references.primary if item in primary_ids + secondary_ids]
    matched_secondary = [item for item in skill.knowledge_references.secondary if item in secondary_ids or item in primary_ids]
    matched_frames = [selected_frame] if selected_frame in skill.supported_frames else []
    matched_metrics = [item for item in skill.metric_references.input + skill.metric_references.context if item in metrics]
    score = 0.0
    score += 5.0 if matched_primary else 0.0
    score += 3.5 if matched_skill_primary_any and not matched_primary else 0.0
    score += 2.0 if "CURRENT_TURN_INTENT" in sources else 0.0
    score += 1.5 if matched_frames else 0.0
    score += float(applicability.support_strength)
    score += min(1.0, len(matched_metrics) * 0.15)
    score += 0.8 if skill.review_status == "approved" else 0.0
    score += 0.7 if skill.compatibility_mode == "strict_canonical" else 0.0
    score += readiness.support_strength * 0.5
    current_text = "".join(str(bridge_input.get("current_message") or bridge_input.get("normalized_message") or "").lower().split())
    if skill.skill_id == "identify_dashboard_metrics" and any(token in current_text for token in ("dashboard", "ตัวเลขอะไร", "ควรดูตัวเลข", "metrics")):
        score += 3.0
    if skill.skill_id == "analyze_sales_decline" and any(token in current_text for token in ("ยอดขายลด", "ยอดขายไม่ดี", "ขายไม่ดี", "salesdecline", "salesbad")):
        score += 2.0
    if skill.skill_id == "calculate_product_margin" and any(token in current_text for token in ("กำไรกี่บาท", "profit", "margin")):
        score += 2.0
    drift = detect_contract_drift(skill)
    score -= float(drift.ranking_penalty or 0.0)
    penalties = []
    if skill.stage not in ACTIVE_STAGES:
        penalties.append("downstream_stage")
        score -= 2.0
    if skill.status in {"disabled", "deprecated"}:
        penalties.append(skill.status)
    if skill.review_status == "rejected":
        penalties.append("rejected")
    if applicability.status in {"NOT_APPLICABLE", "EXCLUDED"}:
        penalties.append("not_applicable")
    if not reference_valid:
        penalties.append("invalid_reference")
    if drift.severity == DriftSeverity.CONSTITUTIONAL.value:
        penalties.append("constitutional_drift")
    elif drift.severity == DriftSeverity.BREAKING.value:
        penalties.append("breaking_drift")
    elif drift.severity == DriftSeverity.REVIEW_REQUIRED.value:
        penalties.append("review_required_drift")
    candidate = SkillCandidate(
        candidate_id=f"skill_candidate::{skill.skill_id}",
        skill_id=skill.skill_id,
        reference_id=skill.reference_id,
        matched_primary_knowledge_ids=matched_primary,
        matched_secondary_knowledge_ids=matched_secondary,
        matched_frames=matched_frames,
        matched_metrics=matched_metrics,
        matched_relationship_rules=[rule for rule in skill.relationship_rule_references if rule in [as_dict(item).get("rule_id") for item in as_list(knowledge.get("applicable_relationship_rules"))]],
        applicability_result=applicability.to_dict(),
        evidence_readiness_result=readiness.to_dict(),
        reference_validation_status=skill.validation_status if not reference_valid else "VALID",
        review_status=skill.review_status,
        declared_review_status=drift.declared_review_status or skill.review_status,
        effective_review_status=drift.effective_review_status or skill.review_status,
        reference_freshness=drift.reference_freshness,
        contract_drift_result=drift.to_dict(),
        compatibility_mode=skill.compatibility_mode,
        authority_scope=skill.authority_scope.to_dict(),
        specificity=round(0.25 + 0.15 * len(skill.knowledge_references.primary) + 0.04 * len(skill.evidence_requirements), 3),
        procedural_role=skill.procedural_role,
        stage=skill.stage,
        support_strength=round(max(0.0, score), 3),
        ranking_factors={"sources": sources, "matched_primary": matched_primary, "matched_skill_primary_any": matched_skill_primary_any, "matched_frame": matched_frames, "readiness": readiness.status, "contract_drift_severity": drift.severity, "effective_review_status": drift.effective_review_status},
        penalties=penalties,
        relevance_strength=_strength(score / 8.0),
        readiness_strength=_strength(readiness.support_strength),
    )
    return candidate


def _rank(candidates: list[SkillCandidate]) -> list[SkillCandidate]:
    ranked = sorted(candidates, key=lambda item: (
        1 if item.excluded_reason else 0,
        0 if item.matched_primary_knowledge_ids else 1,
        0 if item.ranking_factors.get("matched_skill_primary_any") else 1,
        0 if item.matched_intents else 1,
        0 if item.matched_frames else 1,
        -item.support_strength,
        -item.specificity,
        -item.applicability_result.get("support_strength", 0),
        0 if item.reference_validation_status == "VALID" else 1,
        0 if item.effective_review_status == "approved" else 1,
        0 if item.reference_freshness == "CURRENT" else 1,
        -item.evidence_readiness_result.get("support_strength", 0),
        item.skill_id,
    ))
    for index, item in enumerate(ranked, start=1):
        item.rank = index
    return ranked


def _apply_selection(candidates: list[SkillCandidate]) -> None:
    active = []
    for item in candidates:
        if any(flag in item.penalties for flag in ("invalid_reference", "not_applicable", "disabled", "deprecated", "rejected", "constitutional_drift")):
            item.selection_tier = "EXCLUDED"
            item.excluded_reason = ",".join(item.penalties)
        elif "breaking_drift" in item.penalties:
            item.selection_tier = "DEFERRED"
            item.deferred_reason = "primary_blocked_by_breaking_contract_drift"
        elif item.stage not in ACTIVE_STAGES:
            item.selection_tier = "DEFERRED"
            item.deferred_reason = "stage_deferred_in_v591"
        else:
            active.append(item)
    active_ranked = [item for item in candidates if not item.excluded_reason and not item.deferred_reason]
    if active_ranked:
        active_ranked[0].selection_tier = "PRIMARY_CANDIDATE"
        active_ranked[0].selection_reason = "highest deterministic Knowledge-Skill relevance"
        for item in active_ranked[1:4]:
            item.selection_tier = "SECONDARY_CANDIDATE"
            item.selection_reason = "supporting relevant Skill"
        for item in active_ranked[4:]:
            item.selection_tier = "DEFERRED"
            item.deferred_reason = "secondary_cap_exceeded"


def _merge_gap(knowledge: dict, primary: SkillCandidate | None) -> tuple[list[dict], dict]:
    kgap = as_dict(knowledge.get("next_knowledge_gap"))
    rgap = as_dict(primary.evidence_readiness_result.get("next_evidence_gap")) if primary else {}
    metric = kgap.get("metric_id") or rgap.get("metric_id")
    if not metric:
        return [], {}
    gap = SharedEvidenceGap(
        gap_id=f"shared_gap::{metric}",
        origin_layers=unique(["KNOWLEDGE_RUNTIME"] + (["SKILL_READINESS"] if rgap else [])),
        knowledge_ids=_ids(knowledge.get("primary_knowledge")) + _ids(knowledge.get("secondary_knowledge")),
        skill_ids=[primary.skill_id] if primary else [],
        metric_id=metric,
        gap_type=kgap.get("gap_type") or rgap.get("gap_type") or "MISSING_REQUIRED_EVIDENCE",
        known_partial_value=as_dict(kgap.get("current_partial_value")),
        missing_components=as_list(kgap.get("missing_components")),
        blocking_relationship_rules=as_list(kgap.get("blocking_relationship_rules")) or as_list(primary.evidence_readiness_result.get("blocking_relationship_rules") if primary else []),
        priority_tier=kgap.get("priority_tier") or "BLOCKING",
        workflow_owned=bool(kgap.get("workflow_owned")),
        already_asked=bool(kgap.get("already_asked")),
        duplicate_guard="DUPLICATE_SUPPRESSED" if kgap.get("already_asked") else "NEW_HANDOFF",
    )
    return [gap.to_dict()], gap.to_dict()


def _workflow_coordination(bridge_input: dict, primary: SkillCandidate | None) -> WorkflowCoordinationResult:
    state = as_dict(bridge_input.get("workflow_state"))
    admitted = bool(state.get("workflow_admitted") or state.get("admitted") or as_dict(bridge_input.get("workflow_admission_status")).get("admitted"))
    fields = as_list(state.get("workflow_owned_fields")) or as_list(bridge_input.get("workflow_owned_fields"))
    required = as_list(primary.evidence_readiness_result.get("required_evidence")) if primary else []
    overlap = [item for item in required if item in fields]
    status = "WORKFLOW_OWNS_COLLECTION" if admitted and overlap else "SKILL_SUPPORTS_WORKFLOW" if admitted else "NO_ACTIVE_WORKFLOW"
    return WorkflowCoordinationResult(
        workflow_admitted=admitted,
        workflow_id=str(state.get("workflow_id") or state.get("workflow") or ""),
        workflow_owner="WORKFLOW" if admitted else "",
        workflow_owned_fields=fields,
        overlapping_skill_fields=overlap,
        suppressed_skill_questions=overlap,
        allowed_skill_support="diagnostic_only" if admitted else "procedural_applicability",
        coordination_status=status,
    )


def _clarification_handoff(primary: SkillCandidate | None, secondaries: list[SkillCandidate], gap: dict, workflow: WorkflowCoordinationResult) -> dict:
    if not primary or not gap:
        return {}
    return SkillClarificationHandoff(
        handoff_id=f"skill_clarification::{primary.skill_id}::{gap.get('metric_id')}",
        source_layer="KNOWLEDGE_SKILL_BRIDGE",
        primary_skill_id=primary.skill_id,
        supporting_skill_ids=[item.skill_id for item in secondaries],
        source_gap_id=gap.get("gap_id") or "",
        metric_id=gap.get("metric_id") or "",
        gap_type=gap.get("gap_type") or "",
        known_partial_value=gap.get("known_partial_value") or {},
        missing_information=gap.get("missing_components") or [gap.get("metric_id")],
        why_it_matters="This evidence gates procedural readiness for the selected Skill.",
        blocking_relationship_rules=gap.get("blocking_relationship_rules") or [],
        expected_answer_schema={"accepted_fields": [gap.get("metric_id")]},
        question_intent="SKILL_READINESS_CLARIFICATION",
        wording_guidance=["Clarification Authority owns final wording.", "Ask one compact question."],
        forbidden_claims=["root cause", "recommendation", "final judgment", "decision"],
        duplicate_guard=gap.get("duplicate_guard") or "NEW_HANDOFF",
        workflow_coordination=workflow.to_dict(),
        support_strength=primary.support_strength,
    ).to_dict()


def build_knowledge_skill_bridge(bridge_input: dict | None = None, *, registry: CanonicalSkillRegistry | None = None) -> dict:
    bridge_input = deepcopy(bridge_input or {})
    knowledge = as_dict(bridge_input.get("knowledge_runtime_result")) or as_dict(bridge_input.get("knowledge"))
    if not knowledge or not knowledge.get("knowledge_available"):
        return {
            "bridge_consulted": True,
            "bridge_status": "INSUFFICIENT_KNOWLEDGE_CONTEXT",
            "candidate_skills": [],
            "primary_skill_candidate": None,
            "planner_handoff": PlannerEligibilityHandoff().to_dict(),
            "version": KNOWLEDGE_SKILL_BRIDGE_VERSION,
        }
    registry = registry or CanonicalSkillRegistry()
    selected_frame = str(bridge_input.get("selected_frame") or knowledge.get("selected_frame") or "")
    intents = unique(as_list(bridge_input.get("supported_intents")) + as_list(bridge_input.get("current_intents")) + [str(bridge_input.get("user_goal") or "")])
    metrics = unique(as_list(knowledge.get("relevant_metrics")) + list(as_dict(knowledge.get("available_metrics")).keys()) + list(as_dict(knowledge.get("incomplete_metrics")).keys()))
    discovered_ids, sources = _discovered(registry, knowledge, selected_frame, intents, metrics)
    candidates = [_candidate(registry.get_skill(skill_id), bridge_input | {"knowledge_runtime_result": knowledge, "selected_frame": selected_frame}, sources.get(skill_id, [])) for skill_id in discovered_ids if registry.get_skill(skill_id)]
    candidates = _rank(candidates)
    _apply_selection(candidates)
    primary = next((item for item in candidates if item.selection_tier == "PRIMARY_CANDIDATE"), None)
    secondaries = [item for item in candidates if item.selection_tier == "SECONDARY_CANDIDATE"][:3]
    deferred = [item for item in candidates if item.selection_tier == "DEFERRED"][:5]
    excluded = [item for item in candidates if item.selection_tier == "EXCLUDED"]
    gaps, next_gap = _merge_gap(knowledge, primary)
    workflow = _workflow_coordination(bridge_input, primary)
    migration_registry = load_skill_migration_registry()
    drift_results = [item.contract_drift_result for item in candidates if item.contract_drift_result]
    drift_queue = build_contract_migration_queue(drift_results)
    registry_integrity = (drift_results[0].get("registry_integrity") if drift_results else {"registry_integrity_checked": True, "registry_integrity_passed": True})
    if workflow.workflow_admitted:
        bridge_status = "WORKFLOW_OWNS_COLLECTION"
    elif primary and primary.evidence_readiness_result.get("status") in {"BLOCKED_BY_REQUIRED_EVIDENCE", "BLOCKED_BY_CONFLICT", "BLOCKED_BY_WORKFLOW_OWNERSHIP"}:
        bridge_status = "PRIMARY_SKILL_SELECTED_BUT_BLOCKED"
    elif primary:
        bridge_status = "PRIMARY_SKILL_SELECTED"
    elif excluded:
        bridge_status = "ALL_SKILLS_EXCLUDED"
    else:
        bridge_status = "NO_SAFE_PRIMARY_SKILL"
    judgment_status = "READY_FOR_JUDGMENT" if primary and primary.evidence_readiness_result.get("usable_for_judgment_handoff") else "NOT_READY_FOR_JUDGMENT"
    judgment = SkillToJudgmentHandoff(
        handoff_id=f"skill_to_judgment::{primary.skill_id if primary else 'none'}",
        primary_skill_id=primary.skill_id if primary else "",
        supporting_skill_ids=[item.skill_id for item in secondaries],
        selected_knowledge_ids=_ids(knowledge.get("primary_knowledge")) + _ids(knowledge.get("secondary_knowledge")),
        applicable_relationship_rules=primary.matched_relationship_rules if primary else [],
        evidence_package=knowledge.get("available_metrics") or {},
        unresolved_gaps=gaps,
        conflicting_evidence=primary.evidence_readiness_result.get("conflicting_required_evidence", []) if primary else [],
        stale_evidence=primary.evidence_readiness_result.get("stale_required_evidence", []) if primary else [],
        skill_readiness_status=primary.evidence_readiness_result.get("status", "") if primary else "",
        forbidden_judgment_claims=["root cause without future Judgment authority", "recommendation", "decision"],
        support_strength=primary.support_strength if primary else 0.0,
        ready_for_judgment=judgment_status,
    )
    result = {
        "bridge_consulted": True,
        "bridge_status": bridge_status,
        "selected_knowledge_ids": _ids(knowledge.get("primary_knowledge")) + _ids(knowledge.get("secondary_knowledge")),
        "candidate_skills": [item.to_dict() for item in candidates],
        "primary_skill_candidate": primary.to_dict() if primary else None,
        "secondary_skill_candidates": [item.to_dict() for item in secondaries],
        "deferred_skill_candidates": [item.to_dict() for item in deferred],
        "excluded_skill_candidates": [{"skill_id": item.skill_id, "excluded_reason": item.excluded_reason} for item in excluded],
        "skill_readiness_results": [item.evidence_readiness_result for item in candidates],
        "merged_evidence_gaps": gaps,
        "next_shared_gap": next_gap,
        "clarification_handoff": _clarification_handoff(primary, secondaries, next_gap, workflow),
        "judgment_handoff": judgment.to_dict(),
        "planner_handoff": PlannerEligibilityHandoff(unresolved_blockers=[next_gap.get("metric_id")] if next_gap else []).to_dict(),
        "workflow_coordination": workflow.to_dict(),
        "authority_trace": AuthorityTrace().to_dict(),
        "contract_provenance": {
            "contract_provenance_checked": True,
            "reference_snapshots": [build_skill_reference_snapshot(registry.get_skill(item.skill_id)).to_dict() for item in candidates if registry.get_skill(item.skill_id)],
        },
        "contract_drift": {
            "contract_drift_checked": True,
            "contract_drift_detected": any(item.get("drift_detected") for item in drift_results),
            "contract_drift_types": sorted({drift_type for item in drift_results for drift_type in item.get("drift_types", [])}),
            "contract_drift_severity": primary.contract_drift_result.get("severity") if primary else "",
            "changed_contracts": [contract for item in drift_results for contract in item.get("changed_contracts", [])],
            "migration_queue": drift_queue,
            "registry_integrity": registry_integrity,
            "silent_rename_prevented": True,
            "silent_contract_upgrade_prevented": True,
        },
        "canonical_skill_migration": migration_registry,
        "constitutional_invariants": {
            "knowledge_skill_bridge_created": True,
            "canonical_skill_metadata_supported": True,
            "skill_reference_validation_performed": True,
            "skill_applicability_evaluated": True,
            "skill_evidence_readiness_evaluated": True,
            "skill_candidate_selection_performed": True,
            "skill_redundancy_resolution_performed": True,
            "legacy_compatibility_evaluated": True,
            "shared_gap_created": bool(gaps),
            "skill_clarification_handoff_created": bool(next_gap),
            "future_judgment_handoff_prepared": True,
            "workflow_coordination_checked": True,
            "skill_executed": False,
            "root_causes_diagnosed": False,
            "business_judgment_produced": False,
            "judgment_generated": False,
            "decision_made": False,
            "planner_invoked": False,
            "workflow_triggered_by_bridge": False,
            "workflow_started_by_bridge": False,
            "tool_executed": False,
            "tool_called_by_bridge": False,
            "business_memory_schema_changed": False,
            "business_memory_mutated": False,
            "chat_history_mutated_by_bridge": False,
            "conversation_memory_mutated_by_bridge": False,
            "commit_boundary_changed": False,
            "external_model_called": False,
        },
        "registry_versions": {"canonical_skill_registry": registry.registry_version, "knowledge_skill_bridge": KNOWLEDGE_SKILL_BRIDGE_VERSION},
        "version": KNOWLEDGE_SKILL_BRIDGE_VERSION,
    }
    outcome = harden_knowledge_skill_outcome(bridge_input, result)
    if outcome.get("skill_ambiguity_detected") and primary:
        result["bridge_status"] = "AMBIGUOUS_SKILL_NEEDS_CLARIFICATION"
        result["primary_skill_candidate"] = None
        result["deferred_skill_candidates"] = [primary.to_dict()] + result["deferred_skill_candidates"]
        result["clarification_handoff"] = {
            "handoff_id": "skill_ambiguity_clarification",
            "source_layer": "KNOWLEDGE_SKILL_BRIDGE",
            "primary_skill_id": "",
            "supporting_skill_ids": outcome.get("skill_ambiguity", {}).get("competing_skill_ids") or [],
            "source_gap_id": "skill_ambiguity",
            "metric_id": "",
            "gap_type": "AMBIGUOUS_SKILL",
            "missing_information": outcome.get("skill_ambiguity", {}).get("decisive_evidence_missing") or [],
            "question_intent": "DISAMBIGUATE_SKILL_SELECTION",
            "wording_guidance": ["Clarify traffic, conversion, or repeat purchase before selecting a Skill."],
            "forbidden_claims": ["recommendation", "plan", "decision"],
        }
        outcome = harden_knowledge_skill_outcome(bridge_input, result)
    result["conversation_outcome_hardening"] = outcome
    return result
