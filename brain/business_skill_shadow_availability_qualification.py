"""Pure V5.15.8 qualification of the canonical diagnostic shadow path."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from brain.business_skill import SHADOW_AVAILABLE, UNIT_TESTED, BusinessSkill, validate_business_skill
from brain.business_skill_candidate_matcher import match_business_skill_candidates
from brain.business_skill_evidence_mapper import map_candidate_skill_evidence
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_shadow_selector import (
    AMBIGUOUS_CANDIDATES,
    SHADOW_SELECTED,
    select_shadow_business_skill,
)


BUSINESS_SKILL_SHADOW_AVAILABILITY_QUALIFICATION_VERSION = "5.15.8"
SHADOW_AVAILABILITY_QUALIFICATION_TARGET_SKILL_IDS = (
    "cost.change_analysis.v1",
    "cost.per_unit_calculation.v1",
)

QUALIFIED = "QUALIFIED"
NOT_QUALIFIED = "NOT_QUALIFIED"
UNKNOWN_SKILL = "UNKNOWN_SKILL"
UNSUPPORTED_SKILL = "UNSUPPORTED_SKILL"
INVALID_SOURCE_LIFECYCLE = "INVALID_SOURCE_LIFECYCLE"
INVALID_SKILL_CONTRACT = "INVALID_SKILL_CONTRACT"

AUTHORITY_BOUNDARY_STATUS = "DIAGNOSTIC_ONLY_NO_AUTHORITY"
_BOUNDARY_STATEMENT = (
    "Shadow-availability qualification proves only the pure diagnostic path. It does not authorize, "
    "execute, reason, invoke tools, ask follow-up questions, generate or commit a response, activate "
    "a skill, mutate lifecycle, or modify runtime or application state."
)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze(item) for item in value))
    return value


@dataclass(frozen=True)
class BusinessSkillShadowAvailabilityQualification:
    qualification_version: str
    skill_id: str | None
    qualification_status: str
    qualified: bool
    source_lifecycle: str | None
    evaluated_lifecycle: str | None
    candidate_gate: bool
    evidence_gate: bool
    lifecycle_gate: bool
    confidence_gate: bool
    ambiguity_gate: bool
    shadow_selection_result: str | None
    shadow_selected_skill_id: str | None
    promotion_recommended: bool
    recommended_next_status: str | None
    candidate_results: tuple[Any, ...]
    evidence_results: tuple[Any, ...]
    selector_diagnostics: Any
    diagnostic_reasons: tuple[str, ...]
    authority_boundary_status: str = AUTHORITY_BOUNDARY_STATUS
    lifecycle_mutated: bool = False
    authorized: bool = False
    executed: bool = False
    reasoning_executed: bool = False
    tools_invoked: bool = False
    follow_up_generated: bool = False
    response_generated: bool = False
    runtime_activated: bool = False
    boundary_statement: str = _BOUNDARY_STATEMENT


@dataclass(frozen=True)
class BusinessSkillShadowAvailabilityQualificationBatch:
    qualification_version: str
    reports: tuple[BusinessSkillShadowAvailabilityQualification, ...]
    qualified_skill_ids: tuple[str, ...]
    failed_skill_ids: tuple[str, ...]
    recommended_promotion_ids: tuple[str, ...]
    canonical_status_counts: Any
    lifecycle_mutations_applied: int = 0
    authority_boundary_status: str = AUTHORITY_BOUNDARY_STATUS


def get_shadow_availability_qualification_target(skill_id: object) -> BusinessSkill | None:
    """Return an exact-ID canonical target; no normalization is performed."""
    if not isinstance(skill_id, str) or skill_id not in SHADOW_AVAILABILITY_QUALIFICATION_TARGET_SKILL_IDS:
        return None
    return next((skill for skill in get_business_skill_registry() if skill.skill_id == skill_id), None)


def _base_failure(skill_id: str | None, status: str, source_lifecycle: str | None, reason: str):
    return BusinessSkillShadowAvailabilityQualification(
        BUSINESS_SKILL_SHADOW_AVAILABILITY_QUALIFICATION_VERSION, skill_id, status, False,
        source_lifecycle, None, False, False, False, False, False, None, None, False, None,
        (), (), MappingProxyType({}), (reason,),
    )


def qualify_business_skill_shadow_availability(
    skill: object,
    current_message: object,
    available_evidence_by_skill: object,
    registry: Iterable[BusinessSkill] | None = None,
    *,
    business_domain: object | None = None,
    minimum_candidate_score: int | float | None = None,
    minimum_candidate_confidence: float | None = None,
    minimum_confidence_margin: float | None = None,
) -> BusinessSkillShadowAvailabilityQualification:
    """Orchestrate matcher -> mapper -> selector against isolated lifecycle copies."""
    source_lifecycle = getattr(skill, "active_status", None)
    skill_id = getattr(skill, "skill_id", None)
    skill_id = skill_id if isinstance(skill_id, str) and skill_id else None
    entries = tuple(get_business_skill_registry() if registry is None else registry)
    canonical = next((item for item in entries if isinstance(item, BusinessSkill) and item.skill_id == skill_id), None)
    if canonical is None:
        return _base_failure(skill_id, UNKNOWN_SKILL, source_lifecycle, "exact canonical skill was not found")
    if skill_id not in SHADOW_AVAILABILITY_QUALIFICATION_TARGET_SKILL_IDS:
        return _base_failure(skill_id, UNSUPPORTED_SKILL, source_lifecycle, "skill is outside V5.15.8 qualification scope")
    if not isinstance(skill, BusinessSkill) or validate_business_skill(skill)["valid"] is not True:
        return _base_failure(skill_id, INVALID_SKILL_CONTRACT, source_lifecycle, "source skill contract is invalid")
    if source_lifecycle != UNIT_TESTED or canonical.active_status != UNIT_TESTED:
        return _base_failure(skill_id, INVALID_SOURCE_LIFECYCLE, source_lifecycle, "source and canonical lifecycle must both be UNIT_TESTED")

    # Both approved targets are copied so canonical ranking, competition, and ambiguity can be exercised.
    isolated = tuple(
        replace(skill if item.skill_id == skill_id else item, active_status=SHADOW_AVAILABLE)
        if item.skill_id in SHADOW_AVAILABILITY_QUALIFICATION_TARGET_SKILL_IDS else item
        for item in entries
    )
    candidates = match_business_skill_candidates(
        current_message, isolated, business_domain, limit=None, minimum_score=minimum_candidate_score
    )
    supplied = deepcopy(dict(available_evidence_by_skill)) if isinstance(available_evidence_by_skill, Mapping) else {}
    # A plain evidence field mapping is convenient for the requested skill; an ID map supports competitors.
    is_by_skill = any(key in SHADOW_AVAILABILITY_QUALIFICATION_TARGET_SKILL_IDS for key in supplied)
    evidence_results = []
    for candidate in candidates:
        raw = supplied.get(candidate["skill_id"], {}) if is_by_skill else (supplied if candidate["skill_id"] == skill_id else {})
        evidence_results.append(map_candidate_skill_evidence(candidate, raw, isolated))
    decision = select_shadow_business_skill(
        candidates, evidence_results, isolated, minimum_candidate_confidence, minimum_confidence_margin
    )
    target_candidate = next((item for item in candidates if item["skill_id"] == skill_id), None)
    target_evidence = next((item for item in evidence_results if item.get("skill_id") == skill_id), None)
    target_eligibility = next((item for item in decision["candidate_eligibility"] if item["skill_id"] == skill_id), None)
    candidate_gate = bool(target_candidate and candidates[0]["skill_id"] == skill_id)
    evidence_gate = bool(target_evidence and target_evidence.get("evidence_ready") is True)
    lifecycle_gate = bool(target_eligibility and target_eligibility["lifecycle_eligible"])
    confidence_gate = bool(target_eligibility and target_eligibility["candidate_confidence_sufficient"])
    ambiguity_gate = decision["selection_status"] != AMBIGUOUS_CANDIDATES
    qualified = bool(
        candidate_gate and evidence_gate and lifecycle_gate and confidence_gate and ambiguity_gate
        and decision["selection_status"] == SHADOW_SELECTED
        and decision["shadow_selected_skill_id"] == skill_id
    )
    reasons = []
    for name, passed in (
        ("candidate_gate", candidate_gate), ("evidence_gate", evidence_gate),
        ("lifecycle_gate", lifecycle_gate), ("confidence_gate", confidence_gate),
        ("ambiguity_gate", ambiguity_gate),
    ):
        if not passed:
            reasons.append(f"{name}_failed")
    if not qualified and decision["selection_status"]:
        reasons.append(f"shadow_selection:{decision['selection_status']}")
    return BusinessSkillShadowAvailabilityQualification(
        BUSINESS_SKILL_SHADOW_AVAILABILITY_QUALIFICATION_VERSION, skill_id,
        QUALIFIED if qualified else NOT_QUALIFIED, qualified, source_lifecycle, SHADOW_AVAILABLE,
        candidate_gate, evidence_gate, lifecycle_gate, confidence_gate, ambiguity_gate,
        decision["selection_status"], decision["shadow_selected_skill_id"], qualified,
        SHADOW_AVAILABLE if qualified else None, tuple(_freeze(candidates)), tuple(_freeze(evidence_results)),
        _freeze(decision), tuple(reasons),
    )


def qualify_business_skills_shadow_availability(
    qualification_inputs_by_skill: object,
    registry: Iterable[BusinessSkill] | None = None,
) -> BusinessSkillShadowAvailabilityQualificationBatch:
    """Qualify supported IDs in fixed canonical order."""
    entries = tuple(get_business_skill_registry() if registry is None else registry)
    inputs = qualification_inputs_by_skill if isinstance(qualification_inputs_by_skill, Mapping) else {}
    reports = []
    for skill_id in SHADOW_AVAILABILITY_QUALIFICATION_TARGET_SKILL_IDS:
        source = next((item for item in entries if isinstance(item, BusinessSkill) and item.skill_id == skill_id), {"skill_id": skill_id})
        item = inputs.get(skill_id, {})
        item = dict(item) if isinstance(item, Mapping) else {}
        reports.append(qualify_business_skill_shadow_availability(
            source, item.get("current_message"), item.get("available_evidence_by_skill", item.get("evidence", {})),
            entries, business_domain=item.get("business_domain"),
            minimum_candidate_score=item.get("minimum_candidate_score"),
            minimum_candidate_confidence=item.get("minimum_candidate_confidence"),
            minimum_confidence_margin=item.get("minimum_confidence_margin"),
        ))
    qualified = tuple(report.skill_id for report in reports if report.qualified and report.skill_id)
    failed = tuple(report.skill_id for report in reports if not report.qualified and report.skill_id)
    return BusinessSkillShadowAvailabilityQualificationBatch(
        BUSINESS_SKILL_SHADOW_AVAILABILITY_QUALIFICATION_VERSION, tuple(reports), qualified, failed,
        qualified, _freeze(dict(Counter(skill.active_status for skill in entries))),
    )

