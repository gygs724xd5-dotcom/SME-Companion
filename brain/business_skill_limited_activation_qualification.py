"""V5.15.12 deterministic, diagnostic-only limited-activation qualification.

This module evaluates readiness.  It cannot promote, activate, route, execute,
persist, or produce a business response.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from brain.business_skill import LIMITED_ACTIVE, SHADOW_AVAILABLE, BusinessSkill
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_shadow_evaluation import (
    FALSE_NEGATIVE, FALSE_POSITIVE, MISCLASSIFICATION, ShadowEvaluationCase,
    evaluate_business_skill_shadows,
)

BUSINESS_SKILL_LIMITED_ACTIVATION_QUALIFICATION_VERSION = "5.15.12"
QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION = "QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION"
NOT_QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION = "NOT_QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION"
QUALIFICATION_SKILL_IDS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")

REQUIRED_COVERAGE_CATEGORIES = (
    "THAI_POSITIVE", "ENGLISH_POSITIVE", "CORRECT_ABSTENTION",
    "MISSING_INCOMPLETE_EVIDENCE", "INVALID_EVIDENCE", "STALE_EVIDENCE",
    "ASSUMED_EVIDENCE", "LOW_CONFIDENCE", "COMPETING_CANDIDATE_OR_AMBIGUITY",
    "HISTORICAL_CONTEXT_ONLY_PROTECTION",
)
REQUIRED_HISTORY = (
    "tests/test_v5156_business_skill_lifecycle_qualification.py",
    "tests/test_v5157_business_skill_lifecycle_promotion.py",
    "tests/test_v5158_business_skill_shadow_availability_qualification.py",
    "tests/test_v5159_business_skill_shadow_availability_promotion.py",
)
GATE_ORDER = ("SKILL_IDENTITY", "LIFECYCLE", "LIFECYCLE_HISTORY", "OBSERVATION_VOLUME",
              "EVALUATION_QUALITY", "COVERAGE", "DETERMINISM", "MUTATION_SAFETY",
              "AUTHORITY_BOUNDARY")


def get_v51512_shadow_registry() -> tuple[BusinessSkill, ...]:
    """Return the isolated historical input view used by V5.15.12."""
    return tuple(
        replace(skill, active_status=SHADOW_AVAILABLE,
                tests_required=tuple(ref for ref in skill.tests_required
                                     if "test_v51512_" not in ref and "test_v51513_" not in ref))
        if skill.skill_id in QUALIFICATION_SKILL_IDS and skill.active_status == LIMITED_ACTIVE else skill
        for skill in get_business_skill_registry()
    )


@dataclass(frozen=True)
class LimitedActivationQualificationPolicy:
    minimum_observations_per_skill: int = 10
    minimum_pass_rate: float = 1.0
    maximum_false_positives: int = 0
    maximum_false_negatives: int = 0
    maximum_misclassifications: int = 0
    maximum_unexpected_drift_findings: int = 0
    required_coverage_categories: tuple[str, ...] = REQUIRED_COVERAGE_CATEGORIES

    def __post_init__(self) -> None:
        cats = tuple(self.required_coverage_categories)
        object.__setattr__(self, "required_coverage_categories", cats)
        if self.minimum_observations_per_skill < 1:
            raise ValueError("minimum_observations_per_skill must be positive")
        if not 0 <= self.minimum_pass_rate <= 1:
            raise ValueError("minimum_pass_rate must be between zero and one")
        limits = (self.maximum_false_positives, self.maximum_false_negatives,
                  self.maximum_misclassifications, self.maximum_unexpected_drift_findings)
        if any(not isinstance(x, int) or x < 0 for x in limits):
            raise ValueError("error thresholds must be non-negative integers")
        if not cats or len(cats) != len(set(cats)) or any(x not in REQUIRED_COVERAGE_CATEGORIES for x in cats):
            raise ValueError("required coverage categories are malformed")
        # Qualification explicitly requires a clean dataset; permissive limits are impossible policy.
        if any(limits):
            raise ValueError("limited activation qualification requires zero error and drift thresholds")


@dataclass(frozen=True)
class LimitedActivationLabeledCase:
    coverage_category: str
    evaluation_case: ShadowEvaluationCase

    def __post_init__(self) -> None:
        if self.coverage_category not in REQUIRED_COVERAGE_CATEGORIES:
            raise ValueError("unknown coverage category")
        if not isinstance(self.evaluation_case, ShadowEvaluationCase):
            raise ValueError("evaluation_case must be a canonical ShadowEvaluationCase")


@dataclass(frozen=True)
class LimitedActivationQualificationInput:
    skill: BusinessSkill
    lifecycle_history: tuple[str, ...]
    labeled_cases: tuple[LimitedActivationLabeledCase, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "lifecycle_history", tuple(self.lifecycle_history))
        object.__setattr__(self, "labeled_cases", tuple(self.labeled_cases))


@dataclass(frozen=True)
class LimitedActivationGateResult:
    gate: str
    passed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class LimitedActivationRecommendation:
    skill_id: str
    recommendation: str


@dataclass(frozen=True)
class LimitedActivationQualificationResult:
    qualification_id: str
    reference_time: str
    skill_id: str
    registry_version: str
    observation_count: int
    evaluation_count: int
    passed_evaluation_count: int
    coverage_counts: tuple[tuple[str, int], ...]
    gate_results: tuple[LimitedActivationGateResult, ...]
    reason_codes: tuple[str, ...]
    recommendation: LimitedActivationRecommendation


@dataclass(frozen=True)
class LimitedActivationQualificationBatch:
    qualification_version: str
    qualification_id: str
    reference_time: str
    registry_version: str
    results: tuple[LimitedActivationQualificationResult, ...]


def _gate(name: str, reasons: Iterable[str]) -> LimitedActivationGateResult:
    codes = tuple(dict.fromkeys(reasons))
    return LimitedActivationGateResult(name, not codes, codes or ("PASSED",))


def _qualify_one(item: LimitedActivationQualificationInput, qualification_id: str,
                 reference_time: str, policy: LimitedActivationQualificationPolicy,
                 duplicate_ids: set[str]) -> LimitedActivationQualificationResult:
    skill = item.skill
    skill_id = getattr(skill, "skill_id", "")
    canonical = {x.skill_id: x for x in get_v51512_shadow_registry()}.get(skill_id)
    identity = []
    if skill_id not in QUALIFICATION_SKILL_IDS: identity.append("UNKNOWN_OR_UNSUPPORTED_SKILL")
    if skill_id in duplicate_ids: identity.append("DUPLICATE_OR_CONFLICTING_SKILL_INPUT")
    if canonical is not None and skill != canonical: identity.append("CONFLICTING_CANONICAL_SKILL")
    lifecycle = [] if canonical is not None and skill == canonical and skill.active_status == SHADOW_AVAILABLE else ["LIFECYCLE_NOT_SHADOW_AVAILABLE"]
    history = []
    if tuple(item.lifecycle_history) != REQUIRED_HISTORY: history.append("MALFORMED_OR_OUT_OF_ORDER_LIFECYCLE_HISTORY")
    if len(item.lifecycle_history) != len(set(item.lifecycle_history)): history.append("DUPLICATE_LIFECYCLE_HISTORY_REFERENCE")
    if canonical is not None and not all(ref in canonical.tests_required for ref in REQUIRED_HISTORY): history.append("CANONICAL_LIFECYCLE_HISTORY_MISSING")

    cases = tuple(x.evaluation_case for x in item.labeled_cases)
    case_ids = tuple(x.case_id for x in cases)
    volume = []
    if len(case_ids) != len(set(case_ids)): volume.append("DUPLICATE_OBSERVATION_OR_CASE_ID")
    if len(cases) < policy.minimum_observations_per_skill: volume.append("INSUFFICIENT_OBSERVATIONS")
    cross = any(c.expected.skill_id not in (None, skill_id) for c in cases)
    if cross: volume.append("CROSS_SKILL_CONTAMINATION")

    summary = None
    quality = []
    try:
        summary = evaluate_business_skill_shadows(cases)
    except (TypeError, ValueError):
        quality.append("MALFORMED_EVALUATION_DATASET")
    if summary is not None:
        rate = summary.passed_cases / summary.total_cases if summary.total_cases else 0.0
        if rate < policy.minimum_pass_rate: quality.append("PASS_RATE_BELOW_THRESHOLD")
        if summary.false_positive_count: quality.append("FALSE_POSITIVE_PRESENT")
        if summary.false_negative_count: quality.append("FALSE_NEGATIVE_PRESENT")
        if summary.misclassification_count: quality.append("MISCLASSIFICATION_PRESENT")
        if summary.drift_findings: quality.append("UNEXPECTED_DRIFT_PRESENT")
        if tuple(x.case_id for x in summary.results) != tuple(sorted(case_ids)):
            quality.append("EVALUATION_CASE_RELATIONSHIP_INVALID")

    counts = tuple((cat, sum(x.coverage_category == cat for x in item.labeled_cases))
                   for cat in policy.required_coverage_categories)
    coverage = ["MISSING_REQUIRED_COVERAGE:" + cat for cat, count in counts if not count]
    gates = (
        _gate(GATE_ORDER[0], identity), _gate(GATE_ORDER[1], lifecycle),
        _gate(GATE_ORDER[2], history), _gate(GATE_ORDER[3], volume),
        _gate(GATE_ORDER[4], quality), _gate(GATE_ORDER[5], coverage),
        _gate(GATE_ORDER[6], ()), _gate(GATE_ORDER[7], ()), _gate(GATE_ORDER[8], ()),
    )
    passed = all(x.passed for x in gates)
    recommendation = QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION if passed else NOT_QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION
    reasons = tuple(code for gate in gates for code in gate.reason_codes if code != "PASSED") or ("ALL_QUALIFICATION_GATES_PASSED",)
    return LimitedActivationQualificationResult(
        qualification_id, reference_time, skill_id, BUSINESS_SKILL_REGISTRY_VERSION,
        len(cases), summary.total_cases if summary else 0, summary.passed_cases if summary else 0,
        counts, gates, reasons, LimitedActivationRecommendation(skill_id, recommendation),
    )


def qualify_limited_activation(inputs: Iterable[LimitedActivationQualificationInput], *,
                               qualification_id: str, reference_time: str,
                               policy: LimitedActivationQualificationPolicy | None = None,
                               ) -> LimitedActivationQualificationBatch:
    """Return readiness diagnostics only; canonical lifecycle remains untouched."""
    if not isinstance(qualification_id, str) or not qualification_id.strip() or qualification_id != qualification_id.strip():
        raise ValueError("explicit normalized qualification_id is required")
    if not isinstance(reference_time, str) or not reference_time.strip() or reference_time != reference_time.strip():
        raise ValueError("explicit normalized reference_time is required")
    policy = LimitedActivationQualificationPolicy() if policy is None else policy
    if not isinstance(policy, LimitedActivationQualificationPolicy):
        raise ValueError("policy must be LimitedActivationQualificationPolicy")
    try: items = tuple(inputs)
    except TypeError as exc: raise ValueError("inputs must be iterable") from exc
    if any(not isinstance(x, LimitedActivationQualificationInput) for x in items):
        raise ValueError("all inputs must be LimitedActivationQualificationInput")
    ids = [getattr(x.skill, "skill_id", "") for x in items]
    duplicates = {x for x in ids if ids.count(x) > 1}
    results = tuple(_qualify_one(x, qualification_id, reference_time, policy, duplicates)
                    for x in sorted(items, key=lambda x: getattr(x.skill, "skill_id", "")))
    return LimitedActivationQualificationBatch(
        BUSINESS_SKILL_LIMITED_ACTIVATION_QUALIFICATION_VERSION, qualification_id,
        reference_time, BUSINESS_SKILL_REGISTRY_VERSION, results)
