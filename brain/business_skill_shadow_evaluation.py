"""Immutable deterministic V5.15.11 shadow evaluation and drift diagnostics."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION
from brain.business_skill_shadow_observation import (
    AMBIGUITY_BLOCKED,
    CONFIDENCE_BLOCKED,
    EVIDENCE_INCOMPLETE,
    EVIDENCE_INVALID,
    EVIDENCE_STALE,
    LIFECYCLE_BLOCKED,
    SHADOW_SELECTED,
    ShadowObservation,
    ShadowObservationRequest,
    observe_business_skill_shadow,
)

BUSINESS_SKILL_SHADOW_EVALUATION_VERSION = "5.15.11"
EVALUATED_SKILL_IDS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")

TRUE_POSITIVE = "TRUE_POSITIVE"
TRUE_NEGATIVE = "TRUE_NEGATIVE"
FALSE_POSITIVE = "FALSE_POSITIVE"
FALSE_NEGATIVE = "FALSE_NEGATIVE"
MISCLASSIFICATION = "MISCLASSIFICATION"
EXPECTED_AMBIGUITY_BLOCK = "EXPECTED_AMBIGUITY_BLOCK"
EXPECTED_EVIDENCE_BLOCK = "EXPECTED_EVIDENCE_BLOCK"
EXPECTED_LIFECYCLE_BLOCK = "EXPECTED_LIFECYCLE_BLOCK"
EXPECTED_LOW_CONFIDENCE_BLOCK = "EXPECTED_LOW_CONFIDENCE_BLOCK"

EVALUATION_LABELS = (
    TRUE_POSITIVE, TRUE_NEGATIVE, FALSE_POSITIVE, FALSE_NEGATIVE,
    MISCLASSIFICATION, EXPECTED_AMBIGUITY_BLOCK, EXPECTED_EVIDENCE_BLOCK,
    EXPECTED_LIFECYCLE_BLOCK, EXPECTED_LOW_CONFIDENCE_BLOCK,
)
_BLOCK_LABELS = {
    AMBIGUITY_BLOCKED: EXPECTED_AMBIGUITY_BLOCK,
    EVIDENCE_INCOMPLETE: EXPECTED_EVIDENCE_BLOCK,
    EVIDENCE_INVALID: EXPECTED_EVIDENCE_BLOCK,
    EVIDENCE_STALE: EXPECTED_EVIDENCE_BLOCK,
    LIFECYCLE_BLOCKED: EXPECTED_LIFECYCLE_BLOCK,
    CONFIDENCE_BLOCKED: EXPECTED_LOW_CONFIDENCE_BLOCK,
}


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple((str(k), _freeze(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze(v) for v in value), key=repr))
    try:
        return deepcopy(value)
    except Exception:
        return repr(value)


@dataclass(frozen=True)
class ExpectedShadowOutcome:
    label: str
    skill_id: str | None = None

    def __post_init__(self) -> None:
        if self.label not in EVALUATION_LABELS:
            raise ValueError("invalid expected shadow label")
        if self.skill_id is not None and self.skill_id not in EVALUATED_SKILL_IDS:
            raise ValueError("expected skill_id is outside the evaluated Cost skills")
        requires_skill = self.label in {TRUE_POSITIVE, FALSE_NEGATIVE, MISCLASSIFICATION}
        if requires_skill != bool(self.skill_id):
            raise ValueError("expected label and skill_id conflict")


@dataclass(frozen=True)
class ShadowEvaluationCase:
    case_id: str
    request: ShadowObservationRequest
    expected: ExpectedShadowOutcome

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip() or self.case_id != self.case_id.strip():
            raise ValueError("case_id must be an explicit non-empty normalized string")
        if not isinstance(self.request, ShadowObservationRequest):
            raise ValueError("request must be ShadowObservationRequest")
        if not isinstance(self.expected, ExpectedShadowOutcome):
            raise ValueError("expected must be ExpectedShadowOutcome")
        if self.request.available_evidence and not self.request.reference_time:
            raise ValueError("evidence-bearing case requires explicit reference_time")


@dataclass(frozen=True)
class ShadowDriftFinding:
    case_id: str
    expected_label: str
    expected_skill_id: str | None
    observed_label: str
    observed_outcome: str
    observed_skill_id: str | None


@dataclass(frozen=True)
class ShadowEvaluationResult:
    case_id: str
    expected: ExpectedShadowOutcome
    observed_label: str
    passed: bool
    observation: ShadowObservation
    drift_finding: ShadowDriftFinding | None


@dataclass(frozen=True)
class ShadowSkillTotal:
    skill_id: str
    expected_count: int
    selected_count: int


@dataclass(frozen=True)
class ShadowEvaluationSummary:
    evaluation_version: str
    registry_version: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    selected_count: int
    abstained_count: int
    true_positive_count: int
    true_negative_count: int
    false_positive_count: int
    false_negative_count: int
    misclassification_count: int
    ambiguity_block_count: int
    evidence_block_count: int
    lifecycle_block_count: int
    low_confidence_block_count: int
    per_skill_totals: tuple[ShadowSkillTotal, ...]
    results: tuple[ShadowEvaluationResult, ...]
    drift_findings: tuple[ShadowDriftFinding, ...]
    authorized: bool = False
    executed: bool = False
    reasoning_executed: bool = False
    response_generated: bool = False
    follow_up_generated: bool = False
    persisted: bool = False


def _observed_label(expected: ExpectedShadowOutcome, observation: ShadowObservation) -> str:
    selected = observation.selected_shadow_skill_id
    if observation.outcome == SHADOW_SELECTED and selected:
        if expected.skill_id:
            return TRUE_POSITIVE if selected == expected.skill_id else MISCLASSIFICATION
        return FALSE_POSITIVE
    if expected.skill_id:
        return FALSE_NEGATIVE
    return _BLOCK_LABELS.get(observation.outcome, TRUE_NEGATIVE)


def evaluate_business_skill_shadows(cases: Iterable[ShadowEvaluationCase]) -> ShadowEvaluationSummary:
    """Evaluate independent labeled fixtures through the V5.15.10 harness."""
    try:
        items = tuple(cases)
    except TypeError as exc:
        raise ValueError("cases must be iterable") from exc
    if any(not isinstance(case, ShadowEvaluationCase) for case in items):
        raise ValueError("all cases must be ShadowEvaluationCase")
    ids = [case.case_id for case in items]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case_id")

    results = []
    for case in sorted(items, key=lambda item: item.case_id):
        observation = observe_business_skill_shadow(case.request)
        label = _observed_label(case.expected, observation)
        passed = label == case.expected.label
        finding = None if passed else ShadowDriftFinding(
            case.case_id, case.expected.label, case.expected.skill_id, label,
            observation.outcome, observation.selected_shadow_skill_id,
        )
        results.append(ShadowEvaluationResult(case.case_id, case.expected, label, passed, observation, finding))

    labels = [result.observed_label for result in results]
    selected = sum(result.observation.outcome == SHADOW_SELECTED for result in results)
    per_skill = tuple(ShadowSkillTotal(
        skill_id,
        sum(result.expected.skill_id == skill_id for result in results),
        sum(result.observation.selected_shadow_skill_id == skill_id for result in results),
    ) for skill_id in EVALUATED_SKILL_IDS)
    findings = tuple(result.drift_finding for result in results if result.drift_finding is not None)
    return ShadowEvaluationSummary(
        BUSINESS_SKILL_SHADOW_EVALUATION_VERSION, BUSINESS_SKILL_REGISTRY_VERSION,
        len(results), sum(result.passed for result in results), sum(not result.passed for result in results),
        selected, len(results) - selected,
        labels.count(TRUE_POSITIVE), labels.count(TRUE_NEGATIVE), labels.count(FALSE_POSITIVE),
        labels.count(FALSE_NEGATIVE), labels.count(MISCLASSIFICATION),
        labels.count(EXPECTED_AMBIGUITY_BLOCK), labels.count(EXPECTED_EVIDENCE_BLOCK),
        labels.count(EXPECTED_LIFECYCLE_BLOCK), labels.count(EXPECTED_LOW_CONFIDENCE_BLOCK),
        per_skill, tuple(results), findings,
    )
