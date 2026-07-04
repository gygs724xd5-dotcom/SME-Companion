from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


KNOWLEDGE_SKILL_REFERENCE_VERSION = "5.9.1"
SUPPORTED_SKILL_SCHEMA_VERSIONS = {"5.9.1"}


class IssueSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    REFERENCE_PARTIAL = "REFERENCE_PARTIAL"
    LEGACY_COMPATIBLE = "LEGACY_COMPATIBLE"
    STALE_REFERENCE = "STALE_REFERENCE"
    INVALID = "INVALID"
    FATAL = "FATAL"


class CompatibilityMode(str, Enum):
    STRICT_CANONICAL = "strict_canonical"
    TRANSITIONAL = "transitional"
    LEGACY_COMPATIBILITY = "legacy_compatibility"


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    DRAFT = "draft"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"


ACTIVE_STAGES = {"DISCOVERY", "EVIDENCE_STRUCTURING", "ANALYSIS_PREPARATION"}
SUPPORTED_STAGES = ACTIVE_STAGES | {"JUDGMENT_SUPPORT", "DECISION_SUPPORT", "PLANNING_SUPPORT", "EXECUTION_SUPPORT"}
SUPPORTED_PROCEDURAL_ROLES = {
    "SITUATION_ANALYSIS",
    "METRIC_CALCULATION",
    "EVIDENCE_COLLECTION",
    "COMPARISON",
    "READINESS_ASSESSMENT",
    "PLANNING_SUPPORT",
    "WORKFLOW_SUPPORT",
    "ANALYSIS_PREPARATION",
}
SUPPORTED_SKILL_STATUS = {"draft", "active", "deprecated", "disabled", "replaced"}

PROTECTED_FORBIDDEN_AUTHORITIES = {
    "root_cause_diagnosis": "FINAL_JUDGMENT_NOT_ALLOWED",
    "final_judgment": "FINAL_JUDGMENT_NOT_ALLOWED",
    "final_decision": "FINAL_DECISION_NOT_ALLOWED",
    "planner_invocation": "PLANNER_INVOCATION_NOT_ALLOWED",
    "workflow_execution": "WORKFLOW_EXECUTION_NOT_ALLOWED",
    "business_memory_mutation": "BUSINESS_MEMORY_MUTATION_NOT_ALLOWED",
}
SUPPORTED_ALLOWED_AUTHORITIES = {"procedural_analysis", "evidence_sequence", "clarification_support", "workflow_support"}


def unique(values: list[Any]) -> list:
    result = []
    seen = set()
    for value in values or []:
        if value in (None, "", [], {}):
            continue
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def as_list(value: Any) -> list:
    if isinstance(value, list):
        return deepcopy(value)
    if value in (None, "", {}, ()):
        return []
    return [deepcopy(value)]


def as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


@dataclass(frozen=True)
class ReferenceValidationIssue:
    code: str
    severity: str
    field: str = ""
    message: str = ""
    raw_value: Any = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceRequirement:
    evidence_id: str
    requirement_level: str = "REQUIRED"
    accepted_metric_ids: list[str] = field(default_factory=list)
    acceptable_truth_statuses: list[str] = field(default_factory=lambda: ["REPORTED", "VERIFIED"])
    minimum_completeness_status: str = "AVAILABLE_COMPLETE"
    freshness_policy: str = "NO_FRESHNESS_REQUIREMENT"
    timeframe_policy: str = "OPTIONAL"
    source_policy: str = "conversation_or_structured"
    applicability_condition: dict = field(default_factory=dict)
    dependency_ids: list[str] = field(default_factory=list)
    conflict_policy: str = "block"
    workflow_ownership_policy: str = "defer_to_workflow"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeReferences:
    primary: list[str] = field(default_factory=list)
    secondary: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MetricReferences:
    input: list[str] = field(default_factory=list)
    derived: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AuthorityScope:
    allowed: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceProvenance:
    source: str = "skill_front_matter"
    authoritative: bool = True
    source_path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceReview:
    status: str = ReviewStatus.UNREVIEWED.value
    reviewed_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KnowledgeSkillReference:
    reference_id: str
    skill_id: str
    skill_version: str
    schema_version: str
    knowledge_ids: KnowledgeReferences = field(default_factory=KnowledgeReferences)
    metric_ids: MetricReferences = field(default_factory=MetricReferences)
    relationship_rule_ids: list[str] = field(default_factory=list)
    required_evidence_ids: list[str] = field(default_factory=list)
    conditionally_required_evidence_ids: list[str] = field(default_factory=list)
    optional_evidence_ids: list[str] = field(default_factory=list)
    supported_frames: list[str] = field(default_factory=list)
    supported_intents: list[str] = field(default_factory=list)
    applicability_conditions: dict = field(default_factory=dict)
    exclusion_conditions: dict = field(default_factory=dict)
    readiness_policy: dict = field(default_factory=dict)
    authority_scope: AuthorityScope = field(default_factory=AuthorityScope)
    misuse_constraints: list[str] = field(default_factory=list)
    reference_status: str = "active"
    validation_status: str = ValidationStatus.VALID.value
    validation_issues: list[dict] = field(default_factory=list)
    provenance: ReferenceProvenance = field(default_factory=ReferenceProvenance)
    review_status: str = ReviewStatus.UNREVIEWED.value
    compatibility_mode: str = CompatibilityMode.STRICT_CANONICAL.value
    version: str = KNOWLEDGE_SKILL_REFERENCE_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CanonicalSkillDefinition:
    skill_id: str
    display_name: str
    skill_version: str
    schema_version: str
    status: str
    domain: str
    procedural_role: str
    stage: str
    knowledge_references: KnowledgeReferences
    metric_references: MetricReferences
    relationship_rule_references: list[str]
    evidence_requirements: list[EvidenceRequirement]
    supported_frames: list[str]
    supported_intents: list[str]
    applicability: dict = field(default_factory=dict)
    exclusion_conditions: dict = field(default_factory=dict)
    readiness_policy: dict = field(default_factory=dict)
    authority_scope: AuthorityScope = field(default_factory=AuthorityScope)
    compatibility_mode: str = CompatibilityMode.STRICT_CANONICAL.value
    review_status: str = ReviewStatus.UNREVIEWED.value
    procedural_sections: dict = field(default_factory=dict)
    source_path: str = ""
    provenance: ReferenceProvenance = field(default_factory=ReferenceProvenance)
    validation_status: str = ValidationStatus.VALID.value
    validation_issues: list[dict] = field(default_factory=list)
    content: str = ""

    @property
    def reference_id(self) -> str:
        return f"knowledge_skill_ref::{self.skill_id}::v1"

    def to_dict(self) -> dict:
        return asdict(self)


def issue(code: str, severity: str, field: str = "", message: str = "", raw_value: Any = None) -> ReferenceValidationIssue:
    return ReferenceValidationIssue(code=code, severity=severity, field=field, message=message or code, raw_value=raw_value)


def status_from_issues(issues: list[ReferenceValidationIssue | dict], *, valid_status: str = ValidationStatus.VALID.value) -> str:
    severities = {item.get("severity") if isinstance(item, dict) else item.severity for item in issues}
    if IssueSeverity.FATAL.value in severities:
        return ValidationStatus.FATAL.value
    if IssueSeverity.ERROR.value in severities:
        return ValidationStatus.INVALID.value
    if IssueSeverity.WARNING.value in severities:
        return ValidationStatus.VALID_WITH_WARNINGS.value
    return valid_status
