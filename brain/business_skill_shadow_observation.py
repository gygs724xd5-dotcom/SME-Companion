"""Pure deterministic V5.15.10 Business Skill shadow observation harness.

The harness composes the canonical candidate matcher, evidence mapper, and
shadow selector.  It records their diagnostic facts but owns none of their
decision policy and has no runtime, authority, response, or persistence path.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from brain.business_skill_candidate_matcher import (
    BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
    match_business_skill_candidates,
)
from brain.business_skill_evidence_mapper import (
    ASSUMABLE,
    CONFIRMATION_REQUIRED,
    INVALID,
    LOW_CONFIDENCE,
    MISSING,
    STALE,
    BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION,
    map_candidate_skill_evidence,
)
from brain.business_skill_registry import (
    BUSINESS_SKILL_REGISTRY_VERSION,
    get_business_skill_registry,
)
from brain.business_skill_shadow_selector import (
    AMBIGUOUS_CANDIDATES,
    BELOW_CONFIDENCE_THRESHOLD,
    EVIDENCE_MISSING,
    EVIDENCE_NOT_READY,
    INVALID_CANDIDATE,
    LIFECYCLE_INELIGIBLE,
    NO_CANDIDATES,
    SHADOW_SELECTED as SELECTOR_SHADOW_SELECTED,
    UNKNOWN_SKILL,
    BUSINESS_SKILL_SHADOW_SELECTOR_VERSION,
    select_shadow_business_skill,
)


BUSINESS_SKILL_SHADOW_OBSERVATION_VERSION = "5.15.10"

SHADOW_SELECTED = "SHADOW_SELECTED"
NO_CANDIDATE = "NO_CANDIDATE"
CANDIDATE_REJECTED = "CANDIDATE_REJECTED"
EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
EVIDENCE_INVALID = "EVIDENCE_INVALID"
EVIDENCE_STALE = "EVIDENCE_STALE"
CONFIDENCE_BLOCKED = "CONFIDENCE_BLOCKED"
AMBIGUITY_BLOCKED = "AMBIGUITY_BLOCKED"
LIFECYCLE_BLOCKED = "LIFECYCLE_BLOCKED"
NO_SHADOW_SELECTION = "NO_SHADOW_SELECTION"

SHADOW_OBSERVATION_OUTCOMES = (
    SHADOW_SELECTED, NO_CANDIDATE, CANDIDATE_REJECTED,
    EVIDENCE_INCOMPLETE, EVIDENCE_INVALID, EVIDENCE_STALE,
    CONFIDENCE_BLOCKED, AMBIGUITY_BLOCKED, LIFECYCLE_BLOCKED,
    NO_SHADOW_SELECTION,
)

DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"
NO_RUNTIME_AUTHORITY = "NO_RUNTIME_AUTHORITY"


def _freeze(value: Any) -> Any:
    """Make caller-owned values equality-safe without retaining aliases."""
    if isinstance(value, Mapping):
        return tuple((str(key), _freeze(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    try:
        return deepcopy(value)
    except Exception:
        return repr(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value):
            return {key: _thaw(item) for key, item in value}
        return [_thaw(item) for item in value]
    return deepcopy(value)


@dataclass(frozen=True)
class ShadowEvidenceInput:
    field_name: str
    value: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_name", str(self.field_name))
        object.__setattr__(self, "value", _freeze(self.value))


@dataclass(frozen=True)
class ShadowObservationRequest:
    """One independent current-message observation input."""

    current_message: Any
    available_evidence: tuple[ShadowEvidenceInput, ...] = ()
    reference_time: str | None = None

    def __post_init__(self) -> None:
        message = self.current_message if isinstance(self.current_message, str) else _freeze(self.current_message)
        object.__setattr__(self, "current_message", message)
        object.__setattr__(self, "available_evidence", tuple(self.available_evidence))
        object.__setattr__(self, "reference_time", None if self.reference_time is None else str(self.reference_time))

    @classmethod
    def from_mapping(
        cls, current_message: Any, available_evidence: Any = None,
        *, reference_time: str | None = None,
    ) -> "ShadowObservationRequest":
        items = ()
        if isinstance(available_evidence, Mapping):
            items = tuple(ShadowEvidenceInput(str(key), value) for key, value in available_evidence.items())
        return cls(current_message=current_message, available_evidence=items, reference_time=reference_time)


@dataclass(frozen=True)
class CandidateObservation:
    skill_id: str
    rank: int
    score: int | float
    confidence: float
    lifecycle_status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceObservation:
    field_name: str
    mapping_status: str
    required: bool
    blocking: bool
    confidence: float | None
    assumed: bool
    user_confirmed: bool
    validation_status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ShadowObservation:
    observation_version: str
    registry_version: str
    matcher_version: str
    evidence_mapper_version: str
    selector_version: str
    reference_time: str | None
    current_message: Any
    outcome: str
    reason_codes: tuple[str, ...]
    candidates: tuple[CandidateObservation, ...]
    intended_candidate_id: str | None
    top_candidate_id: str | None
    candidate_confidence: float | None
    competing_candidate_ids: tuple[str, ...]
    candidate_gate_passed: bool
    evidence_ready: bool
    evidence: tuple[EvidenceObservation, ...]
    missing_evidence: tuple[str, ...]
    invalid_evidence: tuple[str, ...]
    stale_evidence: tuple[str, ...]
    assumption_status: str
    confirmation_status: str
    evidence_confidence: float | None
    canonical_lifecycle_status: str | None
    lifecycle_gate_passed: bool
    confidence_gate_passed: bool
    ambiguity_gate_passed: bool
    selector_status: str
    selector_confidence: float | None
    selected_shadow_skill_id: str | None
    diagnostic_status: str = DIAGNOSTIC_ONLY
    authority_boundary_status: str = NO_RUNTIME_AUTHORITY
    authorized: bool = False
    executed: bool = False
    reasoning_executed: bool = False
    response_generated: bool = False
    follow_up_generated: bool = False
    persisted: bool = False


@dataclass(frozen=True)
class ShadowObservationBatch:
    observation_version: str
    observations: tuple[ShadowObservation, ...]


def _evidence_mapping(request: ShadowObservationRequest) -> dict[str, Any]:
    return {item.field_name: _thaw(item.value) for item in request.available_evidence}


def _outcome(selector_status: str, mappings: tuple[EvidenceObservation, ...]) -> str:
    statuses = {item.mapping_status for item in mappings if item.required}
    # Evidence detail is canonical mapper output; ordering here only chooses the
    # requested observation label and never changes selector eligibility.
    if selector_status == SELECTOR_SHADOW_SELECTED:
        return SHADOW_SELECTED
    if selector_status == NO_CANDIDATES:
        return NO_CANDIDATE
    if selector_status == AMBIGUOUS_CANDIDATES:
        return AMBIGUITY_BLOCKED
    if selector_status == LIFECYCLE_INELIGIBLE:
        return LIFECYCLE_BLOCKED
    if selector_status == BELOW_CONFIDENCE_THRESHOLD:
        return CONFIDENCE_BLOCKED
    if selector_status in {INVALID_CANDIDATE, UNKNOWN_SKILL}:
        return CANDIDATE_REJECTED
    if INVALID in statuses:
        return EVIDENCE_INVALID
    if STALE in statuses:
        return EVIDENCE_STALE
    if MISSING in statuses or ASSUMABLE in statuses or CONFIRMATION_REQUIRED in statuses:
        return EVIDENCE_INCOMPLETE
    if LOW_CONFIDENCE in statuses:
        return CONFIDENCE_BLOCKED
    if selector_status in {EVIDENCE_MISSING, EVIDENCE_NOT_READY}:
        return EVIDENCE_INCOMPLETE
    return NO_SHADOW_SELECTION


def observe_business_skill_shadow(request: Any) -> ShadowObservation:
    """Run one pure canonical shadow path and return an immutable observation."""
    request_valid = (
        isinstance(request, ShadowObservationRequest)
        and isinstance(request.current_message, str)
        and all(isinstance(item, ShadowEvidenceInput) for item in request.available_evidence)
    )
    reference_time_required = bool(request_valid and request.available_evidence)
    reference_time_missing = bool(reference_time_required and not request.reference_time)
    malformed = not request_valid or reference_time_missing
    registry = get_business_skill_registry()
    if malformed:
        request = request if isinstance(request, ShadowObservationRequest) else ShadowObservationRequest(request)
        candidates_raw: list[dict[str, Any]] = []
    else:
        candidates_raw = match_business_skill_candidates(request.current_message, registry, limit=None)

    evidence_input = _evidence_mapping(request) if all(
        isinstance(item, ShadowEvidenceInput) for item in request.available_evidence
    ) else {}
    mapped_raw = [map_candidate_skill_evidence(item, evidence_input, registry) for item in candidates_raw]
    selection = select_shadow_business_skill(candidates_raw, mapped_raw, registry)

    candidates = tuple(CandidateObservation(
        skill_id=item["skill_id"], rank=item["candidate_rank"], score=item["candidate_score"],
        confidence=item["candidate_confidence"], lifecycle_status=item["active_status"],
        reasons=tuple(item["candidate_reasons"]),
    ) for item in candidates_raw)
    top_map = mapped_raw[0] if mapped_raw else {}
    evidence = tuple(EvidenceObservation(
        field_name=item["field_name"], mapping_status=item["mapping_status"],
        required=item["required"], blocking=item["blocking"],
        confidence=item["observed_confidence"], assumed=item["assumed"],
        user_confirmed=item["user_confirmed"], validation_status=item["validation_status"],
        reasons=tuple(item["reasons"]),
    ) for item in top_map.get("evidence_mappings", ()))
    eligibility = selection["candidate_eligibility"][0] if selection["candidate_eligibility"] else {}
    selector_status = selection["selection_status"]
    reason_codes: list[str] = []
    if malformed:
        reason_codes.append("REFERENCE_TIME_REQUIRED" if reference_time_missing else "MALFORMED_INPUT")
    reason_codes.extend(str(code) for code in eligibility.get("eligibility_failures", ()))
    reason_codes.extend(f"EVIDENCE_{item.mapping_status}:{item.field_name}" for item in evidence if item.blocking)
    if selector_status == AMBIGUOUS_CANDIDATES:
        reason_codes.append(AMBIGUOUS_CANDIDATES)
    if selector_status == SELECTOR_SHADOW_SELECTED:
        reason_codes.append(SELECTOR_SHADOW_SELECTED)
    elif not reason_codes:
        reason_codes.append(selector_status)

    required = tuple(item for item in evidence if item.required)
    confirmation_required = any(item.mapping_status == CONFIRMATION_REQUIRED for item in required)
    assumption_used = any(item.assumed for item in required)
    return ShadowObservation(
        observation_version=BUSINESS_SKILL_SHADOW_OBSERVATION_VERSION,
        registry_version=BUSINESS_SKILL_REGISTRY_VERSION,
        matcher_version=BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
        evidence_mapper_version=BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION,
        selector_version=BUSINESS_SKILL_SHADOW_SELECTOR_VERSION,
        reference_time=request.reference_time,
        current_message=request.current_message,
        outcome=CANDIDATE_REJECTED if malformed else _outcome(selector_status, evidence),
        reason_codes=tuple(dict.fromkeys(reason_codes)), candidates=candidates,
        intended_candidate_id=candidates[0].skill_id if candidates else None,
        top_candidate_id=candidates[0].skill_id if candidates else None,
        candidate_confidence=candidates[0].confidence if candidates else None,
        competing_candidate_ids=tuple(item.skill_id for item in candidates[1:]),
        candidate_gate_passed=bool(candidates and eligibility.get("candidate_valid")),
        evidence_ready=bool(top_map.get("evidence_ready")), evidence=evidence,
        missing_evidence=tuple(top_map.get("missing_required_evidence", ())),
        invalid_evidence=tuple(top_map.get("invalid_required_evidence", ())),
        stale_evidence=tuple(top_map.get("stale_required_evidence", ())),
        assumption_status="ASSUMED" if assumption_used else "NOT_ASSUMED",
        confirmation_status="REQUIRED" if confirmation_required else "SATISFIED_OR_NOT_REQUIRED",
        evidence_confidence=top_map.get("evidence_confidence_floor"),
        canonical_lifecycle_status=eligibility.get("lifecycle_status"),
        lifecycle_gate_passed=bool(eligibility.get("lifecycle_eligible")),
        confidence_gate_passed=bool(eligibility.get("candidate_confidence_sufficient")),
        ambiguity_gate_passed=selector_status != AMBIGUOUS_CANDIDATES,
        selector_status=selector_status,
        selector_confidence=selection["top_eligible_confidence"],
        selected_shadow_skill_id=selection["shadow_selected_skill_id"],
    )


def observe_business_skill_shadows(requests: Iterable[Any]) -> ShadowObservationBatch:
    """Observe independent inputs in caller order; items share no state."""
    try:
        observations = tuple(observe_business_skill_shadow(item) for item in requests)
    except TypeError:
        observations = (observe_business_skill_shadow(requests),)
    return ShadowObservationBatch(BUSINESS_SKILL_SHADOW_OBSERVATION_VERSION, observations)
