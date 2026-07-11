"""Immutable V5.15.13 authority for controlled LIMITED_ACTIVE eligibility.

This module changes lifecycle metadata only.  It deliberately has no runtime,
qualification evaluator, selector, persistence, or response dependencies.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields, replace
from datetime import datetime
from typing import Iterable

from brain.business_skill import LIMITED_ACTIVE, SHADOW_AVAILABLE, STABLE, BusinessSkill


BUSINESS_SKILL_LIMITED_ACTIVATION_MANIFEST_VERSION = "5.15.13"
LIMITED_ACTIVATION_QUALIFICATION_VERSION = "5.15.12"
QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION = "QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION"
LIMITED_ACTIVE_PROMOTION = "LIMITED_ACTIVE_PROMOTION"

V5156_QUALIFICATION_TEST = "tests/test_v5156_business_skill_lifecycle_qualification.py"
V5157_PROMOTION_TEST = "tests/test_v5157_business_skill_lifecycle_promotion.py"
V5158_QUALIFICATION_TEST = "tests/test_v5158_business_skill_shadow_availability_qualification.py"
V5159_PROMOTION_TEST = "tests/test_v5159_business_skill_shadow_availability_promotion.py"
V51512_QUALIFICATION_TEST = "tests/test_v51512_business_skill_limited_activation_qualification.py"
V51513_PROMOTION_TEST = "tests/test_v51513_business_skill_limited_activation_promotion.py"

REQUIRED_AUDIT_REFERENCES = (
    V5156_QUALIFICATION_TEST, V5157_PROMOTION_TEST, V5158_QUALIFICATION_TEST,
    V5159_PROMOTION_TEST, V51512_QUALIFICATION_TEST, V51513_PROMOTION_TEST,
)
SOURCE_AUDIT_REFERENCES = REQUIRED_AUDIT_REFERENCES[:-2]
APPROVED_LIMITED_ACTIVATION_SKILL_IDS = (
    "cost.change_analysis.v1", "cost.per_unit_calculation.v1",
)


@dataclass(frozen=True)
class CanonicalGateEvidence:
    gate: str
    passed: bool


@dataclass(frozen=True)
class CanonicalLimitedActivationEvidence:
    qualification_id: str
    reference_time: str
    qualification_version: str
    registry_version: str
    skill_id: str
    recommendation: str
    gate_results: tuple[CanonicalGateEvidence, ...]


_GATES = (
    "SKILL_IDENTITY", "LIFECYCLE", "LIFECYCLE_HISTORY", "OBSERVATION_VOLUME",
    "EVALUATION_QUALITY", "COVERAGE", "DETERMINISM", "MUTATION_SAFETY",
    "AUTHORITY_BOUNDARY",
)
CANONICAL_QUALIFICATION_ID = "V5.15.12-LIMITED-ACTIVATION-QUALIFICATION"
CANONICAL_QUALIFICATION_REFERENCE_TIME = "2026-07-11T00:00:00+07:00"


def _evidence(skill_id: str) -> CanonicalLimitedActivationEvidence:
    return CanonicalLimitedActivationEvidence(
        CANONICAL_QUALIFICATION_ID, CANONICAL_QUALIFICATION_REFERENCE_TIME,
        LIMITED_ACTIVATION_QUALIFICATION_VERSION, "5.15.9.1", skill_id,
        QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION,
        tuple(CanonicalGateEvidence(gate, True) for gate in _GATES),
    )


@dataclass(frozen=True)
class BusinessSkillLimitedActivationPromotion:
    skill_id: str
    from_status: str
    to_status: str
    manifest_version: str
    qualification: CanonicalLimitedActivationEvidence
    audit_references: tuple[str, ...]
    promotion_type: str = LIMITED_ACTIVE_PROMOTION


APPROVED_LIMITED_ACTIVATION_PROMOTIONS = tuple(
    BusinessSkillLimitedActivationPromotion(
        skill_id, SHADOW_AVAILABLE, LIMITED_ACTIVE,
        BUSINESS_SKILL_LIMITED_ACTIVATION_MANIFEST_VERSION, _evidence(skill_id),
        REQUIRED_AUDIT_REFERENCES,
    ) for skill_id in APPROVED_LIMITED_ACTIVATION_SKILL_IDS
)


def _valid_explicit_reference(qualification_id: object, reference_time: object) -> bool:
    if not isinstance(qualification_id, str) or not qualification_id or qualification_id != qualification_id.strip():
        return False
    if not isinstance(reference_time, str) or not reference_time or reference_time != reference_time.strip():
        return False
    try:
        parsed = datetime.fromisoformat(reference_time)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _recommendation_value(result: object) -> object:
    value = getattr(result, "recommendation", None)
    return getattr(value, "recommendation", value)


def validate_limited_activation_promotion(promotion: object) -> dict:
    errors: list[str] = []
    if not isinstance(promotion, BusinessSkillLimitedActivationPromotion):
        errors.append("promotion must be a BusinessSkillLimitedActivationPromotion")
    skill_id = getattr(promotion, "skill_id", "")
    source = getattr(promotion, "from_status", "")
    target = getattr(promotion, "to_status", "")
    if skill_id not in APPROVED_LIMITED_ACTIVATION_SKILL_IDS:
        errors.append(f"unknown or unsupported Skill ID: {skill_id}")
    if source == target: errors.append("same-status transition is not allowed")
    if source == LIMITED_ACTIVE: errors.append("Skill is already LIMITED_ACTIVE")
    if target == STABLE: errors.append("promotion target STABLE is not allowed")
    if (source, target) != (SHADOW_AVAILABLE, LIMITED_ACTIVE):
        errors.append("V5.15.13 permits only SHADOW_AVAILABLE -> LIMITED_ACTIVE")
    if getattr(promotion, "manifest_version", "") != BUSINESS_SKILL_LIMITED_ACTIVATION_MANIFEST_VERSION:
        errors.append("registry/manifest version mismatch")
    if getattr(promotion, "promotion_type", "") != LIMITED_ACTIVE_PROMOTION:
        errors.append("malformed promotion type")
    evidence = getattr(promotion, "qualification", None)
    if evidence is None:
        errors.append("missing qualification result")
    else:
        if getattr(evidence, "skill_id", None) != skill_id: errors.append("qualification Skill ID mismatch")
        if getattr(evidence, "qualification_version", None) != LIMITED_ACTIVATION_QUALIFICATION_VERSION:
            errors.append("qualification version mismatch")
        if getattr(evidence, "registry_version", None) != "5.15.9.1":
            errors.append("qualification registry version mismatch")
        if _recommendation_value(evidence) != QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION:
            errors.append("qualification recommendation is not QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION")
        gates = getattr(evidence, "gate_results", ())
        if not isinstance(gates, tuple) or not gates or any(getattr(g, "passed", None) is not True for g in gates):
            errors.append("every qualification gate must pass")
        if tuple(getattr(g, "gate", None) for g in gates) != _GATES:
            errors.append("qualification gates are missing, duplicate, malformed, or out of order")
        if not _valid_explicit_reference(getattr(evidence, "qualification_id", None), getattr(evidence, "reference_time", None)):
            errors.append("qualification ID/reference time malformed")
    refs = getattr(promotion, "audit_references", ())
    if not isinstance(refs, tuple) or refs != REQUIRED_AUDIT_REFERENCES:
        errors.append("audit references are missing, duplicate, malformed, or out of order")
    return {"valid": not errors, "errors": errors, "warnings": []}


def validate_limited_activation_manifest(manifest=None, known_skill_ids=None) -> dict:
    entries = APPROVED_LIMITED_ACTIVATION_PROMOTIONS if manifest is None else tuple(manifest)
    ids = tuple(getattr(x, "skill_id", "") for x in entries)
    duplicates = tuple(sorted(x for x, count in Counter(ids).items() if count > 1))
    known = set(APPROVED_LIMITED_ACTIVATION_SKILL_IDS if known_skill_ids is None else tuple(known_skill_ids))
    unknown = tuple(sorted(set(ids) - known))
    errors = [f"duplicate promotion record: {x}" for x in duplicates]
    errors += [f"unknown Skill ID: {x}" for x in unknown]
    if ids != APPROVED_LIMITED_ACTIVATION_SKILL_IDS:
        errors.append("manifest must contain exactly two canonical promotions in deterministic order")
    for entry in entries:
        result = validate_limited_activation_promotion(entry)
        errors.extend(f"{getattr(entry, 'skill_id', '')}: {x}" for x in result["errors"])
    return {"valid": not errors, "errors": errors, "warnings": [],
            "manifest_version": BUSINESS_SKILL_LIMITED_ACTIVATION_MANIFEST_VERSION,
            "total_promotions": len(entries), "promoted_skill_ids": ids,
            "duplicate_skill_ids": duplicates, "unknown_skill_ids": unknown}


def get_limited_activation_promotion(skill_id: object, manifest=None):
    if not isinstance(skill_id, str): return None
    entries = APPROVED_LIMITED_ACTIVATION_PROMOTIONS if manifest is None else tuple(manifest)
    return next((x for x in entries if x.skill_id == skill_id), None)


def _validated(manifest, known):
    entries = APPROVED_LIMITED_ACTIVATION_PROMOTIONS if manifest is None else tuple(manifest)
    result = validate_limited_activation_manifest(entries, known)
    if not result["valid"]: raise ValueError("invalid V5.15.13 manifest: " + "; ".join(result["errors"]))
    return entries


def apply_approved_limited_activation_promotion(skill: BusinessSkill, manifest=None) -> BusinessSkill:
    if not isinstance(skill, BusinessSkill): raise TypeError("skill must be a BusinessSkill")
    entries = _validated(manifest, APPROVED_LIMITED_ACTIVATION_SKILL_IDS)
    promotion = get_limited_activation_promotion(skill.skill_id, entries)
    if promotion is None: return skill
    if skill.active_status != SHADOW_AVAILABLE:
        raise ValueError(f"source lifecycle must be SHADOW_AVAILABLE for {skill.skill_id}")
    refs = skill.tests_required
    if any(refs.count(ref) != 1 for ref in SOURCE_AUDIT_REFERENCES):
        raise ValueError(f"source audit history is missing, duplicate, or malformed for {skill.skill_id}")
    indexes = tuple(refs.index(ref) for ref in SOURCE_AUDIT_REFERENCES)
    if indexes != tuple(sorted(indexes)):
        raise ValueError(f"source audit history is out of order for {skill.skill_id}")
    return replace(skill, active_status=LIMITED_ACTIVE,
                   tests_required=(*refs, V51512_QUALIFICATION_TEST, V51513_PROMOTION_TEST))


def apply_approved_limited_activation_promotions(skills: Iterable[BusinessSkill], manifest=None) -> tuple[BusinessSkill, ...]:
    entries = tuple(skills)
    ids = tuple(x.skill_id for x in entries)
    if len(ids) != len(set(ids)): raise ValueError("duplicate source Skill IDs")
    promotions = _validated(manifest, ids)
    if set(x.skill_id for x in promotions) - set(ids): raise ValueError("promotion source is missing a Skill ID")
    return tuple(apply_approved_limited_activation_promotion(x, promotions) for x in entries)


def build_limited_activation_promotion_diagnostics(skills: Iterable[BusinessSkill]) -> dict:
    before = tuple(skills); after = apply_approved_limited_activation_promotions(before)
    old = {x.skill_id: x for x in before}
    return {"manifest_version": BUSINESS_SKILL_LIMITED_ACTIVATION_MANIFEST_VERSION,
            "registry_version": BUSINESS_SKILL_LIMITED_ACTIVATION_MANIFEST_VERSION,
            "applied_promotion_ids": [x.skill_id for x in after if old[x.skill_id] != x],
            "status_counts_before": dict(Counter(x.active_status for x in before)),
            "status_counts_after": dict(Counter(x.active_status for x in after)),
            "changed_field_names_by_skill": {x.skill_id: [f.name for f in fields(BusinessSkill) if getattr(old[x.skill_id], f.name) != getattr(x, f.name)] for x in after},
            "authorized": False, "executed": False, "reasoning_executed": False,
            "calculated": False, "runtime_routed": False, "tools_invoked": False,
            "follow_up_generated": False, "persisted": False,
            "response_committed": False, "response_generated": False,
            "boundary_statement": "LIMITED_ACTIVE is lifecycle eligibility only and grants no runtime or response authority."}
