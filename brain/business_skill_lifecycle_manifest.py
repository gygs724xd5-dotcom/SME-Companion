"""Immutable, pure lifecycle promotion authority for SME Companion V5.15.7."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields, replace
from typing import Iterable

from brain.business_skill import (
    ACCEPTANCE_GUARDED,
    CONTRACTED,
    DRAFT,
    LIMITED_ACTIVE,
    RUNTIME_AUDITED,
    SHADOW_AVAILABLE,
    SKILL_LIFECYCLE_STATUSES,
    STABLE,
    UNIT_TESTED,
    BusinessSkill,
)


BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION = "5.15.7"
UNIT_TEST_QUALIFICATION = "UNIT_TEST_QUALIFICATION"
V5156_QUALIFICATION_TEST = "tests/test_v5156_business_skill_lifecycle_qualification.py"
V5157_PROMOTION_TEST = "tests/test_v5157_business_skill_lifecycle_promotion.py"

LIFECYCLE_PATH = (
    DRAFT,
    CONTRACTED,
    UNIT_TESTED,
    SHADOW_AVAILABLE,
    ACCEPTANCE_GUARDED,
    RUNTIME_AUDITED,
    LIMITED_ACTIVE,
    STABLE,
)

APPROVED_PROMOTION_SKILL_IDS = (
    "cost.change_analysis.v1",
    "cost.per_unit_calculation.v1",
)


@dataclass(frozen=True)
class BusinessSkillLifecyclePromotion:
    skill_id: str
    from_status: str
    to_status: str
    qualification_version: str
    qualification_type: str
    qualification_test_files: tuple[str, ...]
    approval_reason: str


APPROVED_LIFECYCLE_PROMOTIONS = (
    BusinessSkillLifecyclePromotion(
        skill_id="cost.change_analysis.v1",
        from_status=CONTRACTED,
        to_status=UNIT_TESTED,
        qualification_version="5.15.6",
        qualification_type=UNIT_TEST_QUALIFICATION,
        qualification_test_files=(V5156_QUALIFICATION_TEST,),
        approval_reason="V5.15.6 deterministic unit-test qualification passed all required gates for Cost Change Analysis.",
    ),
    BusinessSkillLifecyclePromotion(
        skill_id="cost.per_unit_calculation.v1",
        from_status=CONTRACTED,
        to_status=UNIT_TESTED,
        qualification_version="5.15.6",
        qualification_type=UNIT_TEST_QUALIFICATION,
        qualification_test_files=(V5156_QUALIFICATION_TEST,),
        approval_reason="V5.15.6 deterministic unit-test qualification passed all required gates for Cost Per Unit Calculation.",
    ),
)


def get_lifecycle_promotion(
    skill_id: str, manifest: Iterable[BusinessSkillLifecyclePromotion] | None = None
) -> BusinessSkillLifecyclePromotion | None:
    """Return an exact-ID promotion record; no normalization is performed."""
    if not isinstance(skill_id, str):
        return None
    for promotion in APPROVED_LIFECYCLE_PROMOTIONS if manifest is None else tuple(manifest):
        if promotion.skill_id == skill_id:
            return promotion
    return None


def validate_lifecycle_promotion(promotion: object) -> dict:
    errors: list[str] = []
    skill_id = getattr(promotion, "skill_id", "")
    from_status = getattr(promotion, "from_status", "")
    to_status = getattr(promotion, "to_status", "")
    if not isinstance(promotion, BusinessSkillLifecyclePromotion):
        errors.append("promotion must be a BusinessSkillLifecyclePromotion")
    if skill_id not in APPROVED_PROMOTION_SKILL_IDS:
        errors.append(f"promotion is outside V5.15.7 approved scope: {skill_id}")
    if from_status not in SKILL_LIFECYCLE_STATUSES:
        errors.append(f"unknown from_status: {from_status}")
    if to_status not in SKILL_LIFECYCLE_STATUSES:
        errors.append(f"unknown to_status: {to_status}")
    if from_status in LIFECYCLE_PATH and to_status in LIFECYCLE_PATH:
        difference = LIFECYCLE_PATH.index(to_status) - LIFECYCLE_PATH.index(from_status)
        if difference == 0:
            errors.append("same-status lifecycle transition is not allowed")
        elif difference < 0:
            errors.append("backward lifecycle transition is not allowed")
        elif difference > 1:
            errors.append("lifecycle skip is not allowed")
    if (from_status, to_status) != (CONTRACTED, UNIT_TESTED):
        errors.append("V5.15.7 permits only CONTRACTED -> UNIT_TESTED")
    if getattr(promotion, "qualification_version", "") != "5.15.6":
        errors.append("qualification_version must be 5.15.6")
    if getattr(promotion, "qualification_type", "") != UNIT_TEST_QUALIFICATION:
        errors.append("qualification_type must be UNIT_TEST_QUALIFICATION")
    test_files = getattr(promotion, "qualification_test_files", ())
    if V5156_QUALIFICATION_TEST not in test_files:
        errors.append("V5.15.6 qualification test reference is required")
    if not str(getattr(promotion, "approval_reason", "") or "").strip():
        errors.append("approval_reason is required")
    return {"valid": not errors, "errors": errors, "warnings": []}


def validate_lifecycle_promotion_manifest(
    manifest: Iterable[BusinessSkillLifecyclePromotion] | None = None,
    known_skill_ids: Iterable[str] | None = None,
) -> dict:
    promotions = APPROVED_LIFECYCLE_PROMOTIONS if manifest is None else tuple(manifest)
    ids = [getattr(item, "skill_id", "") for item in promotions]
    counts = Counter(ids)
    duplicates = sorted(skill_id for skill_id, count in counts.items() if count > 1)
    known = set(APPROVED_PROMOTION_SKILL_IDS if known_skill_ids is None else known_skill_ids)
    unknown = sorted(set(ids) - known)
    invalid = []
    errors = []
    for promotion in promotions:
        result = validate_lifecycle_promotion(promotion)
        if not result["valid"]:
            invalid.append(getattr(promotion, "skill_id", ""))
            errors.extend(f"{getattr(promotion, 'skill_id', '')}: {error}" for error in result["errors"])
    errors.extend(f"duplicate promotion skill_id: {skill_id}" for skill_id in duplicates)
    errors.extend(f"unknown skill_id: {skill_id}" for skill_id in unknown)
    target_counts = dict(Counter(getattr(item, "to_status", "") for item in promotions))
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": [],
        "manifest_version": BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION,
        "total_promotions": len(promotions),
        "promoted_skill_ids": ids,
        "duplicate_skill_ids": duplicates,
        "invalid_transition_skill_ids": sorted(set(invalid)),
        "unknown_skill_ids": unknown,
        "target_status_counts": target_counts,
    }


def _validated_manifest(manifest, known_skill_ids):
    promotions = APPROVED_LIFECYCLE_PROMOTIONS if manifest is None else tuple(manifest)
    result = validate_lifecycle_promotion_manifest(promotions, known_skill_ids)
    if not result["valid"]:
        raise ValueError("invalid lifecycle promotion manifest: " + "; ".join(result["errors"]))
    return promotions


def apply_approved_lifecycle_promotion(
    skill: BusinessSkill, manifest: Iterable[BusinessSkillLifecyclePromotion] | None = None
) -> BusinessSkill:
    if not isinstance(skill, BusinessSkill):
        raise TypeError("skill must be a BusinessSkill")
    promotions = _validated_manifest(manifest, APPROVED_PROMOTION_SKILL_IDS)
    promotion = get_lifecycle_promotion(skill.skill_id, promotions)
    if promotion is None:
        return skill
    if skill.active_status != promotion.from_status:
        raise ValueError(
            f"current status mismatch for {skill.skill_id}: expected {promotion.from_status}, got {skill.active_status}"
        )
    additions = (*promotion.qualification_test_files, V5157_PROMOTION_TEST)
    tests_required = tuple(dict.fromkeys((*skill.tests_required, *additions)))
    return replace(skill, active_status=promotion.to_status, tests_required=tests_required)


def apply_approved_lifecycle_promotions(
    skills: Iterable[BusinessSkill], manifest: Iterable[BusinessSkillLifecyclePromotion] | None = None
) -> tuple[BusinessSkill, ...]:
    entries = tuple(skills)
    ids = tuple(skill.skill_id for skill in entries)
    promotions = _validated_manifest(manifest, ids)
    missing = sorted(set(item.skill_id for item in promotions) - set(ids))
    if missing:
        raise ValueError("unknown skill IDs in promotion application: " + ", ".join(missing))
    return tuple(apply_approved_lifecycle_promotion(skill, promotions) for skill in entries)


def build_lifecycle_promotion_diagnostics(
    skills: Iterable[BusinessSkill], manifest: Iterable[BusinessSkillLifecyclePromotion] | None = None
) -> dict:
    before = tuple(skills)
    promotions = APPROVED_LIFECYCLE_PROMOTIONS if manifest is None else tuple(manifest)
    after = apply_approved_lifecycle_promotions(before, promotions)
    before_map = {skill.skill_id: skill.active_status for skill in before}
    after_map = {skill.skill_id: skill.active_status for skill in after}
    requested = [item.skill_id for item in promotions]
    applied = [skill.skill_id for skill in after if before_map[skill.skill_id] != skill.active_status]
    changed = {}
    preserved = {}
    tests_added = {}
    field_names = tuple(field.name for field in fields(BusinessSkill))
    before_by_id = {skill.skill_id: skill for skill in before}
    for skill in after:
        original = before_by_id[skill.skill_id]
        changed[skill.skill_id] = [name for name in field_names if getattr(original, name) != getattr(skill, name)]
        preserved[skill.skill_id] = [name for name in field_names if getattr(original, name) == getattr(skill, name)]
        tests_added[skill.skill_id] = [item for item in skill.tests_required if item not in original.tests_required]
    return {
        "manifest_version": BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION,
        "registry_version": "5.15.7",
        "requested_promotion_ids": requested,
        "applied_promotion_ids": applied,
        "rejected_promotion_ids": [skill_id for skill_id in requested if skill_id not in applied],
        "before_status_map": before_map,
        "after_status_map": after_map,
        "changed_field_names_by_skill": changed,
        "preserved_field_names_by_skill": preserved,
        "tests_required_added_by_skill": tests_added,
        "status_counts_before": dict(Counter(before_map.values())),
        "status_counts_after": dict(Counter(after_map.values())),
        "shadow_available_ids": [skill.skill_id for skill in after if skill.active_status == SHADOW_AVAILABLE],
        "lifecycle_mutation_count": len(applied),
        "authorized_skill_id": None,
        "executed_skill_id": None,
        "response_authority": None,
        "shadow_available": False,
        "shadow_selected": False,
        "authorized": False,
        "executed": False,
        "reasoning_executed": False,
        "response_generated": False,
        "boundary_statement": "UNIT_TESTED records qualification only; it grants no shadow availability, selection, authorization, execution, reasoning, workflow, response authority, or response generation.",
    }
