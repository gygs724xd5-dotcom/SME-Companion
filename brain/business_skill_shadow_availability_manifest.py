"""Immutable, pure V5.15.9 authority for controlled shadow availability."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields, replace
from typing import Iterable

from brain.business_skill import (
    SHADOW_AVAILABLE,
    SKILL_LIFECYCLE_STATUSES,
    UNIT_TESTED,
    BusinessSkill,
)


BUSINESS_SKILL_SHADOW_AVAILABILITY_MANIFEST_VERSION = "5.15.9"
SHADOW_AVAILABILITY_QUALIFICATION = "SHADOW_AVAILABILITY_QUALIFICATION"
V5158_QUALIFICATION_TEST = "tests/test_v5158_business_skill_shadow_availability_qualification.py"
V5159_PROMOTION_TEST = "tests/test_v5159_business_skill_shadow_availability_promotion.py"

APPROVED_SHADOW_AVAILABILITY_SKILL_IDS = (
    "cost.change_analysis.v1",
    "cost.per_unit_calculation.v1",
)

KNOWN_BUSINESS_SKILL_IDS = (
    "cost.change_analysis.v1",
    "cost.per_unit_calculation.v1",
    "pricing.promotion_margin_check.v1",
    "pricing.basic_price_suggestion.v1",
    "profitability.gross_margin_explanation.v1",
    "inventory.low_stock_explanation.v1",
    "sales.daily_sales_summary.v1",
    "cashflow.warning_explanation.v1",
    "customer.complaint_triage.v1",
    "operations.daily_task_checklist.v1",
)


@dataclass(frozen=True)
class BusinessSkillShadowAvailabilityPromotion:
    skill_id: str
    from_status: str
    to_status: str
    qualification_version: str
    qualification_type: str
    qualification_test_files: tuple[str, ...]
    approval_reason: str


APPROVED_SHADOW_AVAILABILITY_PROMOTIONS = (
    BusinessSkillShadowAvailabilityPromotion(
        skill_id="cost.change_analysis.v1",
        from_status=UNIT_TESTED,
        to_status=SHADOW_AVAILABLE,
        qualification_version="5.15.8",
        qualification_type=SHADOW_AVAILABILITY_QUALIFICATION,
        qualification_test_files=(V5158_QUALIFICATION_TEST,),
        approval_reason="V5.15.8 isolated Shadow Availability Qualification passed the complete diagnostic path for Cost Change Analysis.",
    ),
    BusinessSkillShadowAvailabilityPromotion(
        skill_id="cost.per_unit_calculation.v1",
        from_status=UNIT_TESTED,
        to_status=SHADOW_AVAILABLE,
        qualification_version="5.15.8",
        qualification_type=SHADOW_AVAILABILITY_QUALIFICATION,
        qualification_test_files=(V5158_QUALIFICATION_TEST,),
        approval_reason="V5.15.8 isolated Shadow Availability Qualification passed the complete diagnostic path for Cost Per Unit Calculation.",
    ),
)


def get_shadow_availability_promotion(
    skill_id: object,
    manifest: Iterable[BusinessSkillShadowAvailabilityPromotion] | None = None,
) -> BusinessSkillShadowAvailabilityPromotion | None:
    """Return an exact-ID authorization; no normalization is performed."""
    if not isinstance(skill_id, str):
        return None
    entries = APPROVED_SHADOW_AVAILABILITY_PROMOTIONS if manifest is None else tuple(manifest)
    return next((item for item in entries if item.skill_id == skill_id), None)


def validate_shadow_availability_promotion(promotion: object) -> dict:
    errors: list[str] = []
    skill_id = getattr(promotion, "skill_id", "")
    from_status = getattr(promotion, "from_status", "")
    to_status = getattr(promotion, "to_status", "")
    if not isinstance(promotion, BusinessSkillShadowAvailabilityPromotion):
        errors.append("promotion must be a BusinessSkillShadowAvailabilityPromotion")
    if skill_id not in APPROVED_SHADOW_AVAILABILITY_SKILL_IDS:
        errors.append(f"promotion is outside V5.15.9 approved scope: {skill_id}")
    if from_status not in SKILL_LIFECYCLE_STATUSES:
        errors.append(f"unknown from_status: {from_status}")
    if to_status not in SKILL_LIFECYCLE_STATUSES:
        errors.append(f"unknown to_status: {to_status}")
    if (from_status, to_status) != (UNIT_TESTED, SHADOW_AVAILABLE):
        errors.append("V5.15.9 permits only UNIT_TESTED -> SHADOW_AVAILABLE")
    if getattr(promotion, "qualification_version", "") != "5.15.8":
        errors.append("qualification_version must be 5.15.8")
    if getattr(promotion, "qualification_type", "") != SHADOW_AVAILABILITY_QUALIFICATION:
        errors.append("qualification_type must be SHADOW_AVAILABILITY_QUALIFICATION")
    test_files = getattr(promotion, "qualification_test_files", ())
    if not isinstance(test_files, tuple):
        errors.append("qualification_test_files must be an immutable tuple")
    elif test_files != (V5158_QUALIFICATION_TEST,):
        errors.append("qualification_test_files must contain exactly the V5.15.8 qualification reference once")
    if not str(getattr(promotion, "approval_reason", "") or "").strip():
        errors.append("approval_reason is required")
    return {"valid": not errors, "errors": errors, "warnings": []}


def validate_shadow_availability_manifest(
    manifest: Iterable[BusinessSkillShadowAvailabilityPromotion] | None = None,
    known_skill_ids: Iterable[str] | None = None,
) -> dict:
    entries = APPROVED_SHADOW_AVAILABILITY_PROMOTIONS if manifest is None else tuple(manifest)
    ids = [getattr(item, "skill_id", "") for item in entries]
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    known = set(APPROVED_SHADOW_AVAILABILITY_SKILL_IDS if known_skill_ids is None else known_skill_ids)
    unknown = sorted(set(ids) - known)
    errors = [f"duplicate promotion skill_id: {item}" for item in duplicates]
    errors.extend(f"unknown skill_id: {item}" for item in unknown)
    invalid = []
    for item in entries:
        result = validate_shadow_availability_promotion(item)
        if not result["valid"]:
            invalid.append(getattr(item, "skill_id", ""))
            errors.extend(f"{getattr(item, 'skill_id', '')}: {error}" for error in result["errors"])
    if tuple(ids) != APPROVED_SHADOW_AVAILABILITY_SKILL_IDS:
        errors.append("manifest must authorize exactly the two V5.15.9 Cost Skills in canonical order")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": [],
        "manifest_version": BUSINESS_SKILL_SHADOW_AVAILABILITY_MANIFEST_VERSION,
        "total_promotions": len(entries),
        "promoted_skill_ids": ids,
        "duplicate_skill_ids": duplicates,
        "invalid_transition_skill_ids": sorted(set(invalid)),
        "unknown_skill_ids": unknown,
        "target_status_counts": dict(Counter(getattr(item, "to_status", "") for item in entries)),
    }


def _validated_manifest(manifest, known_skill_ids):
    entries = APPROVED_SHADOW_AVAILABILITY_PROMOTIONS if manifest is None else tuple(manifest)
    result = validate_shadow_availability_manifest(entries, known_skill_ids)
    if not result["valid"]:
        raise ValueError("invalid V5.15.9 shadow availability manifest: " + "; ".join(result["errors"]))
    return entries


def apply_approved_shadow_availability_promotion(
    skill: BusinessSkill,
    manifest: Iterable[BusinessSkillShadowAvailabilityPromotion] | None = None,
) -> BusinessSkill:
    if not isinstance(skill, BusinessSkill):
        raise TypeError("skill must be a BusinessSkill")
    if skill.skill_id not in KNOWN_BUSINESS_SKILL_IDS:
        raise ValueError(f"unknown Business Skill ID: {skill.skill_id}")
    if (
        not isinstance(skill.tests_required, tuple)
        or len(skill.tests_required) != len(set(skill.tests_required))
        or any(not isinstance(item, str) or not item.startswith("tests/test_") or not item.endswith(".py")
               for item in skill.tests_required)
    ):
        raise ValueError(f"malformed or duplicate test audit references for {skill.skill_id}")
    entries = _validated_manifest(manifest, APPROVED_SHADOW_AVAILABILITY_SKILL_IDS)
    promotion = get_shadow_availability_promotion(skill.skill_id, entries)
    if promotion is None:
        return skill
    if skill.active_status != promotion.from_status:
        raise ValueError(
            f"current status mismatch for {skill.skill_id}: expected {promotion.from_status}, got {skill.active_status}"
        )
    additions = (*promotion.qualification_test_files, V5159_PROMOTION_TEST)
    tests_required = tuple(dict.fromkeys((*skill.tests_required, *additions)))
    return replace(skill, active_status=promotion.to_status, tests_required=tests_required)


def apply_approved_shadow_availability_promotions(
    skills: Iterable[BusinessSkill],
    manifest: Iterable[BusinessSkillShadowAvailabilityPromotion] | None = None,
) -> tuple[BusinessSkill, ...]:
    entries = tuple(skills)
    ids = tuple(skill.skill_id for skill in entries)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate Business Skill IDs in promotion source")
    unknown_sources = sorted(set(ids) - set(KNOWN_BUSINESS_SKILL_IDS))
    if unknown_sources:
        raise ValueError("unknown Business Skill IDs in promotion source: " + ", ".join(unknown_sources))
    promotions = _validated_manifest(manifest, (skill.skill_id for skill in entries))
    missing = sorted(set(item.skill_id for item in promotions) - {skill.skill_id for skill in entries})
    if missing:
        raise ValueError("unknown skill IDs in promotion application: " + ", ".join(missing))
    return tuple(apply_approved_shadow_availability_promotion(skill, promotions) for skill in entries)


def build_shadow_availability_promotion_diagnostics(skills: Iterable[BusinessSkill]) -> dict:
    before = tuple(skills)
    after = apply_approved_shadow_availability_promotions(before)
    before_by_id = {skill.skill_id: skill for skill in before}
    changed = {
        skill.skill_id: [
            field.name for field in fields(BusinessSkill)
            if getattr(before_by_id[skill.skill_id], field.name) != getattr(skill, field.name)
        ] for skill in after
    }
    applied = [skill.skill_id for skill in after if before_by_id[skill.skill_id].active_status != skill.active_status]
    return {
        "manifest_version": BUSINESS_SKILL_SHADOW_AVAILABILITY_MANIFEST_VERSION,
        "registry_version": "5.15.9",
        "applied_promotion_ids": applied,
        "changed_field_names_by_skill": changed,
        "status_counts_before": dict(Counter(skill.active_status for skill in before)),
        "status_counts_after": dict(Counter(skill.active_status for skill in after)),
        "shadow_available_ids": [skill.skill_id for skill in after if skill.active_status == SHADOW_AVAILABLE],
        "lifecycle_mutation_count": len(applied),
        "authorized": False,
        "executed": False,
        "reasoning_executed": False,
        "tools_invoked": False,
        "follow_up_generated": False,
        "workflow_altered": False,
        "response_generated": False,
        "runtime_activated": False,
        "boundary_statement": "SHADOW_AVAILABLE is diagnostic-only and grants no reasoning, execution, tool, follow-up, workflow, or response authority.",
    }
