from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


BUSINESS_JUDGMENT_VERSION = "5.10.4"


class JudgmentType(str, Enum):
    EXPLANATORY = "EXPLANATORY"
    COMPARATIVE = "COMPARATIVE"
    CONDITION_ASSESSMENT = "CONDITION_ASSESSMENT"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"


class JudgmentEligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    ELIGIBLE_WITH_LIMITATIONS = "ELIGIBLE_WITH_LIMITATIONS"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    BLOCKED_BY_EVIDENCE = "BLOCKED_BY_EVIDENCE"
    BLOCKED_BY_CONFLICT = "BLOCKED_BY_CONFLICT"
    BLOCKED_BY_AUTHORITY = "BLOCKED_BY_AUTHORITY"


class JudgmentStatus(str, Enum):
    JUDGMENT_SUPPORTED = "JUDGMENT_SUPPORTED"
    JUDGMENT_TENTATIVE = "JUDGMENT_TENTATIVE"
    MULTIPLE_PLAUSIBLE_EXPLANATIONS = "MULTIPLE_PLAUSIBLE_EXPLANATIONS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICT_BLOCKED = "CONFLICT_BLOCKED"
    NO_SAFE_JUDGMENT = "NO_SAFE_JUDGMENT"


class ConfidenceClass(str, Enum):
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MEDIUM_CONFIDENCE = "MEDIUM_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_RELIABLE_JUDGMENT = "NO_RELIABLE_JUDGMENT"


class SupportStrength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INSUFFICIENT = "INSUFFICIENT"
    CONTRADICTED = "CONTRADICTED"


class CausalClaimLevel(str, Enum):
    OBSERVATION = "OBSERVATION"
    ASSOCIATION = "ASSOCIATION"
    CONTRIBUTING_FACTOR = "CONTRIBUTING_FACTOR"
    LIKELY_DRIVER = "LIKELY_DRIVER"
    PRIMARY_DRIVER = "PRIMARY_DRIVER"
    CONFIRMED_CAUSE = "CONFIRMED_CAUSE"


class CandidateReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    NEEDS_REVISION = "NEEDS_REVISION"
    DEPRECATED = "DEPRECATED"
    REJECTED = "REJECTED"


class CandidateRuntimeStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIALLY_APPLICABLE = "PARTIALLY_APPLICABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    EXCLUDED = "EXCLUDED"
    DEPRECATED = "DEPRECATED"


class CandidateSpecificity(str, Enum):
    SPECIFIC = "SPECIFIC"
    MODERATELY_SPECIFIC = "MODERATELY_SPECIFIC"
    GENERAL = "GENERAL"
    TOO_GENERAL = "TOO_GENERAL"


class EvidenceRole(str, Enum):
    CORE_SUPPORT = "CORE_SUPPORT"
    SECONDARY_SUPPORT = "SECONDARY_SUPPORT"
    CONTRADICTION_CHECK = "CONTRADICTION_CHECK"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    ALTERNATIVE_SEPARATOR = "ALTERNATIVE_SEPARATOR"


class WeightClass(str, Enum):
    DECISIVE = "DECISIVE"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    NOT_USABLE = "NOT_USABLE"
    CONFLICTED = "CONFLICTED"


class ComparisonStatus(str, Enum):
    CLEAR_LEADER = "CLEAR_LEADER"
    MODERATE_LEADER = "MODERATE_LEADER"
    MULTIPLE_COEXISTING = "MULTIPLE_COEXISTING"
    MULTIPLE_PLAUSIBLE = "MULTIPLE_PLAUSIBLE"
    INSUFFICIENT_SEPARATION = "INSUFFICIENT_SEPARATION"
    CONFLICT_BLOCKED = "CONFLICT_BLOCKED"
    NO_SUPPORTED_CANDIDATE = "NO_SUPPORTED_CANDIDATE"


class OutcomeStatus(str, Enum):
    SUPPORTED_JUDGMENT = "SUPPORTED_JUDGMENT"
    TENTATIVE_JUDGMENT = "TENTATIVE_JUDGMENT"
    MULTIPLE_CONTRIBUTING_FACTORS = "MULTIPLE_CONTRIBUTING_FACTORS"
    MULTIPLE_PLAUSIBLE_EXPLANATIONS = "MULTIPLE_PLAUSIBLE_EXPLANATIONS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICT_BLOCKED = "CONFLICT_BLOCKED"
    SUPERSEDED_JUDGMENT = "SUPERSEDED_JUDGMENT"
    WITHDRAWN_JUDGMENT = "WITHDRAWN_JUDGMENT"
    NO_APPLICABLE_JUDGMENT = "NO_APPLICABLE_JUDGMENT"
    JUDGMENT_NOT_AUTHORIZED = "JUDGMENT_NOT_AUTHORIZED"


class ResponseMode(str, Enum):
    DIRECT_JUDGMENT = "DIRECT_JUDGMENT"
    TENTATIVE_JUDGMENT = "TENTATIVE_JUDGMENT"
    MULTI_FACTOR_JUDGMENT = "MULTI_FACTOR_JUDGMENT"
    PLAUSIBILITY_SUMMARY = "PLAUSIBILITY_SUMMARY"
    EVIDENCE_LIMITATION = "EVIDENCE_LIMITATION"
    CONFLICT_NOTICE = "CONFLICT_NOTICE"
    REVISION_NOTICE = "REVISION_NOTICE"
    NO_JUDGMENT = "NO_JUDGMENT"


class RevisionStatus(str, Enum):
    UNCHANGED = "UNCHANGED"
    STRENGTHENED = "STRENGTHENED"
    WEAKENED = "WEAKENED"
    REVISED = "REVISED"
    EXPANDED = "EXPANDED"
    NARROWED = "NARROWED"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"
    BLOCKED = "BLOCKED"


def to_dict(value: Any) -> dict:
    return asdict(value)


@dataclass(frozen=True)
class BusinessJudgmentInput:
    active_topic: str = ""
    active_topic_id: str = ""
    selected_frame: str = "UNKNOWN_SITUATION"
    primary_knowledge_ids: list[str] = field(default_factory=list)
    secondary_knowledge_ids: list[str] = field(default_factory=list)
    primary_skill_id: str = ""
    skill_readiness: dict = field(default_factory=dict)
    applicable_relationship_rules: list = field(default_factory=list)
    evidence_package: dict = field(default_factory=dict)
    truth_runtime_result: dict = field(default_factory=dict)
    shared_gaps: list = field(default_factory=list)
    unresolved_conflicts: list = field(default_factory=list)
    conversation_context: dict = field(default_factory=dict)
    workflow_outputs: dict = field(default_factory=dict)
    judgment_policy: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JudgmentEligibility:
    eligible: bool = False
    status: str = JudgmentEligibilityStatus.NOT_ELIGIBLE.value
    blocking_gaps: list = field(default_factory=list)
    blocking_conflicts: list = field(default_factory=list)
    missing_requirements: list = field(default_factory=list)
    allowed_judgment_types: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JudgmentEvidenceRequirement:
    requirement_id: str
    metric_id: str
    role: str
    minimum_completeness: str = "AVAILABLE_COMPLETE"
    acceptable_truth_statuses: list[str] = field(default_factory=lambda: ["OBSERVED", "REPORTED", "DERIVED", "OFFICIAL", "RUNTIME"])
    freshness_policy: str = "RECENT"
    timeframe_policy: str = "MATCHED"
    comparison_required: bool = False
    source_policy: str = "ANY_CANONICAL"
    weight_class: str = WeightClass.MODERATE.value
    blocking: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JudgmentEvidenceRule:
    rule_id: str
    rule_type: str
    input_metrics: list[str]
    operator: str
    threshold_policy: str = ""
    expected_direction: str = ""
    comparison_scope: str = ""
    support_effect: str = "SUPPORTS"
    claim_limit: str = CausalClaimLevel.CONTRIBUTING_FACTOR.value

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JudgmentCandidateDefinition:
    candidate_id: str
    display_name: str
    description: str
    judgment_type: str
    business_domain: str
    applicable_frames: list[str] = field(default_factory=list)
    required_knowledge_ids: list[str] = field(default_factory=list)
    supporting_knowledge_ids: list[str] = field(default_factory=list)
    required_relationship_rule_ids: list[str] = field(default_factory=list)
    required_metric_ids: list[str] = field(default_factory=list)
    optional_metric_ids: list[str] = field(default_factory=list)
    supporting_evidence_rules: list[JudgmentEvidenceRule] = field(default_factory=list)
    contradicting_evidence_rules: list[JudgmentEvidenceRule] = field(default_factory=list)
    exclusion_rules: list[str] = field(default_factory=list)
    applicability_conditions: list[str] = field(default_factory=list)
    minimum_evidence_coverage: float = 0.5
    maximum_claim_level: str = CausalClaimLevel.CONTRIBUTING_FACTOR.value
    default_status: str = CandidateRuntimeStatus.AVAILABLE.value
    misuse_constraints: list[str] = field(default_factory=list)
    allowed_outputs: list[str] = field(default_factory=list)
    forbidden_outputs: list[str] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)
    review_status: str = CandidateReviewStatus.DRAFT.value
    specificity: str = CandidateSpecificity.SPECIFIC.value
    priority: int = 50
    version: str = BUSINESS_JUDGMENT_VERSION

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["supporting_evidence_rules"] = [rule.to_dict() for rule in self.supporting_evidence_rules]
        payload["contradicting_evidence_rules"] = [rule.to_dict() for rule in self.contradicting_evidence_rules]
        return payload


@dataclass(frozen=True)
class JudgmentCandidateConflict:
    candidate_a: str
    candidate_b: str
    conflict_type: str
    coexistence_allowed: bool
    resolution_metrics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JudgmentCandidate:
    candidate_id: str
    explanation: str = ""
    knowledge_ids: list[str] = field(default_factory=list)
    relationship_rule_ids: list[str] = field(default_factory=list)
    required_evidence: list = field(default_factory=list)
    supporting_evidence: list = field(default_factory=list)
    contradicting_evidence: list = field(default_factory=list)
    missing_evidence: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    support_strength: str = SupportStrength.INSUFFICIENT.value
    contradiction_strength: str = SupportStrength.INSUFFICIENT.value
    evidence_coverage: float = 0.0
    specificity: str = CandidateSpecificity.SPECIFIC.value
    causal_claim_level: str = CausalClaimLevel.CONTRIBUTING_FACTOR.value
    status: str = "INSUFFICIENT_EVIDENCE"
    rank: int = 0
    selection_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AlternativeExplanation:
    explanation_id: str
    description: str
    current_support: str
    missing_evidence: list = field(default_factory=list)
    contradiction: list = field(default_factory=list)
    why_not_selected: str = ""
    still_plausible: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BusinessJudgment:
    judgment_id: str
    judgment_type: str
    active_topic: str
    active_topic_id: str
    selected_frame: str
    selected_knowledge_ids: list[str]
    primary_skill_id: str
    candidate_explanations: list = field(default_factory=list)
    selected_explanation: dict | None = None
    alternative_explanations: list = field(default_factory=list)
    supporting_evidence: list = field(default_factory=list)
    contradicting_evidence: list = field(default_factory=list)
    missing_evidence: list = field(default_factory=list)
    unresolved_conflicts: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    confidence_class: str = ConfidenceClass.NO_RELIABLE_JUDGMENT.value
    support_strength: str = SupportStrength.INSUFFICIENT.value
    limitation_summary: str = ""
    allowed_claims: list = field(default_factory=list)
    forbidden_claims: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    authority_trace: list[str] = field(default_factory=list)
    version: str = BUSINESS_JUDGMENT_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BusinessJudgmentResult:
    judgment_available: bool = False
    judgment_status: str = JudgmentStatus.NO_SAFE_JUDGMENT.value
    selected_judgment: dict | None = None
    candidate_judgments: list = field(default_factory=list)
    alternative_explanations: list = field(default_factory=list)
    evidence_summary: dict = field(default_factory=dict)
    contradictions: list = field(default_factory=list)
    limitations: list = field(default_factory=list)
    confidence_class: str = ConfidenceClass.NO_RELIABLE_JUDGMENT.value
    support_strength: str = SupportStrength.INSUFFICIENT.value
    next_evidence_need: dict = field(default_factory=dict)
    decision_handoff: dict = field(default_factory=dict)
    response_handoff: dict = field(default_factory=dict)
    authority_trace: list[str] = field(default_factory=list)
    constitutional_invariants: dict = field(default_factory=dict)
    version: str = BUSINESS_JUDGMENT_VERSION

    def to_dict(self) -> dict:
        return asdict(self)

