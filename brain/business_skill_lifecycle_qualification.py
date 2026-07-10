"""Pure unit-test qualification diagnostics for canonical Business Skills.

Qualification recommends a lifecycle transition; it never applies one.
Evidence supplied here is an explicit record produced by tests outside this
module.  This module does not discover, execute, or otherwise verify tests.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Iterable, Mapping

from brain.business_skill import CONTRACTED, SHADOW_AVAILABLE, UNIT_TESTED, BusinessSkill, validate_business_skill
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_shadow_selector import SHADOW_SELECTION_ELIGIBLE_STATUSES


BUSINESS_SKILL_LIFECYCLE_QUALIFICATION_VERSION = "5.15.6"
UNIT_TEST_QUALIFICATION = "UNIT_TEST_QUALIFICATION"
QUALIFICATION_TARGET_SKILL_IDS = (
    "cost.change_analysis.v1",
    "cost.per_unit_calculation.v1",
)

QUALIFICATION_PASSED = "QUALIFICATION_PASSED"
QUALIFICATION_FAILED = "QUALIFICATION_FAILED"
UNKNOWN_SKILL = "UNKNOWN_SKILL"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
INVALID_SKILL_CONTRACT = "INVALID_SKILL_CONTRACT"
INVALID_CURRENT_STATUS = "INVALID_CURRENT_STATUS"
INCOMPLETE_QUALIFICATION_EVIDENCE = "INCOMPLETE_QUALIFICATION_EVIDENCE"

_BOOLEAN_GATES = (
    "targeted_tests_passed",
    "candidate_positive_cases_passed",
    "candidate_negative_cases_passed",
    "evidence_complete_cases_passed",
    "evidence_missing_cases_passed",
    "evidence_invalid_cases_passed",
    "determinism_cases_passed",
    "mutation_safety_cases_passed",
    "boundary_cases_passed",
    "regression_tests_passed",
    "full_suite_passed",
    "py_compile_passed",
    "diff_check_passed",
)
_REQUIRED_EVIDENCE_FIELDS = ("declared_test_files", *_BOOLEAN_GATES, "full_suite_test_count")
_BOUNDARY_STATEMENT = (
    "Unit-test qualification is diagnostic evidence only: it does not mutate lifecycle, make a skill "
    "shadow-available, select or authorize a skill, execute reasoning, generate a follow-up, or generate a response."
)


def _registry_entries(registry: Any) -> tuple[Any, ...]:
    source = get_business_skill_registry() if registry is None else registry
    source = source.values() if isinstance(source, Mapping) else source
    try:
        return tuple(source)
    except TypeError:
        return ()


def _registry_index(registry: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    duplicates: set[str] = set()
    for skill in _registry_entries(registry):
        skill_id = getattr(skill, "skill_id", None)
        if skill_id is None and isinstance(skill, Mapping):
            skill_id = skill.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id:
            continue
        if skill_id in result:
            duplicates.add(skill_id)
        else:
            result[skill_id] = skill
    for skill_id in duplicates:
        result.pop(skill_id, None)
    return result


def _skill_id(skill: Any) -> str | None:
    value = skill.get("skill_id") if isinstance(skill, Mapping) else getattr(skill, "skill_id", None)
    return value if isinstance(value, str) and value else None


def _normalize_evidence(value: Any) -> dict[str, Any]:
    evidence = deepcopy(dict(value)) if isinstance(value, Mapping) else {}
    files = evidence.get("declared_test_files")
    evidence["declared_test_files"] = (
        [item for item in deepcopy(list(files)) if isinstance(item, str) and item.strip()]
        if isinstance(files, (list, tuple)) else []
    )
    return evidence


def evaluate_unit_test_qualification(
    skill: Any,
    qualification_evidence: Any,
    registry: Any = None,
) -> dict[str, Any]:
    """Evaluate explicit evidence without mutating the skill or registry."""
    skill_id = _skill_id(skill)
    canonical = _registry_index(registry).get(skill_id) if skill_id else None
    evidence = _normalize_evidence(qualification_evidence)
    scope_allowed = skill_id in QUALIFICATION_TARGET_SKILL_IDS
    validation = validate_business_skill(skill) if canonical is not None else {"valid": False, "errors": []}
    contract_valid = validation["valid"] is True
    current_status = getattr(canonical, "active_status", None)
    if current_status is None and isinstance(canonical, Mapping):
        current_status = canonical.get("active_status")
    tests_required = getattr(canonical, "tests_required", ()) if canonical is not None else ()
    if isinstance(canonical, Mapping):
        tests_required = canonical.get("tests_required", ())

    missing = [name for name in _REQUIRED_EVIDENCE_FIELDS if name not in evidence]
    passed_gates: list[str] = []
    failed_gates: list[str] = []
    reasons: list[str] = []

    def gate(name: str, passed: bool, reason: str) -> None:
        (passed_gates if passed else failed_gates).append(name)
        if not passed:
            reasons.append(reason)

    gate("canonical_skill_exists", canonical is not None, "exact canonical skill was not found")
    gate("qualification_scope", scope_allowed, "skill is outside the V5.15.6 qualification scope")
    gate("valid_skill_contract", contract_valid, "canonical skill contract is invalid")
    gate("current_status_contracted", current_status == CONTRACTED, "current lifecycle status must be CONTRACTED")
    gate("tests_required_non_empty", isinstance(tests_required, (list, tuple)) and bool(tests_required), "skill tests_required must be non-empty")
    gate("declared_test_files_non_empty", bool(evidence["declared_test_files"]), "declared_test_files must contain a non-empty file name")
    for name in _BOOLEAN_GATES:
        gate(name, evidence.get(name) is True, f"{name} must be the bool value True")
    count = evidence.get("full_suite_test_count")
    gate(
        "full_suite_test_count_positive_integer",
        isinstance(count, int) and not isinstance(count, bool) and count > 0,
        "full_suite_test_count must be a positive integer and not bool",
    )

    if canonical is None:
        status = UNKNOWN_SKILL
    elif not scope_allowed:
        status = OUT_OF_SCOPE
    elif not contract_valid:
        status = INVALID_SKILL_CONTRACT
    elif current_status != CONTRACTED:
        status = INVALID_CURRENT_STATUS
    elif missing:
        status = INCOMPLETE_QUALIFICATION_EVIDENCE
    elif failed_gates:
        status = QUALIFICATION_FAILED
    else:
        status = QUALIFICATION_PASSED
    qualified = status == QUALIFICATION_PASSED

    return {
        "skill_id": skill_id,
        "canonical_skill_found": canonical is not None,
        "qualification_scope_allowed": scope_allowed,
        "skill_contract_valid": contract_valid,
        "current_status": current_status,
        "expected_current_status": CONTRACTED,
        "recommended_next_status": UNIT_TESTED if qualified else None,
        "qualification_passed": qualified,
        "qualification_status": status,
        "passed_gates": passed_gates,
        "failed_gates": failed_gates,
        "missing_qualification_evidence": missing,
        "declared_test_files": evidence["declared_test_files"],
        "full_suite_test_count": count,
        "lifecycle_mutated": False,
        "shadow_available": False,
        "shadow_selected": False,
        "authorized": False,
        "executed": False,
        "response_generated": False,
        "qualification_reasons": reasons,
    }


def qualify_seed_business_skills(
    qualification_evidence_by_skill: Any,
    registry: Any = None,
    target_skill_ids: Any = None,
) -> dict[str, Any]:
    """Evaluate only configured targets and report diagnostic proposed counts."""
    entries = _registry_entries(registry)
    index = _registry_index(entries)
    requested = QUALIFICATION_TARGET_SKILL_IDS if target_skill_ids is None else tuple(target_skill_ids)
    targets = tuple(skill_id for skill_id in QUALIFICATION_TARGET_SKILL_IDS if skill_id in requested)
    evidence_by_id = qualification_evidence_by_skill if isinstance(qualification_evidence_by_skill, Mapping) else {}
    results = [evaluate_unit_test_qualification(index.get(skill_id, {"skill_id": skill_id}), evidence_by_id.get(skill_id), entries) for skill_id in targets]
    passed = [item["skill_id"] for item in results if item["qualification_passed"]]
    failed = [item["skill_id"] for item in results if not item["qualification_passed"]]
    actual_statuses = [getattr(skill, "active_status", None) for skill in entries]
    proposed = list(actual_statuses)
    for skill_id in passed:
        if skill_id in index:
            proposed[entries.index(index[skill_id])] = UNIT_TESTED
    return {
        "qualification_version": BUSINESS_SKILL_LIFECYCLE_QUALIFICATION_VERSION,
        "target_skill_ids": list(targets),
        "evaluated_skill_ids": [item["skill_id"] for item in results],
        "passed_qualification_skill_ids": passed,
        "failed_qualification_skill_ids": failed,
        "out_of_scope_skill_ids": [skill_id for skill_id in index if skill_id not in targets],
        "recommended_unit_tested_skill_ids": list(passed),
        "qualification_results": results,
        "current_registry_status_counts": dict(Counter(actual_statuses)),
        "proposed_status_counts": dict(Counter(proposed)),
        "lifecycle_mutations_applied": 0,
        "all_registry_skills_unchanged": all(getattr(skill, "active_status", None) == status for skill, status in zip(entries, actual_statuses)),
    }


def build_business_skill_qualification_diagnostics(
    qualification_evidence_by_skill: Any,
    registry: Any = None,
    target_skill_ids: Any = None,
) -> dict[str, Any]:
    entries = _registry_entries(registry)
    batch = qualify_seed_business_skills(qualification_evidence_by_skill, entries, target_skill_ids)
    actual = {getattr(skill, "skill_id", ""): getattr(skill, "active_status", None) for skill in entries}
    return {
        "qualification_version": BUSINESS_SKILL_LIFECYCLE_QUALIFICATION_VERSION,
        "registry_version": BUSINESS_SKILL_REGISTRY_VERSION,
        "target_skill_ids": batch["target_skill_ids"],
        "qualification_results": batch["qualification_results"],
        "recommended_promotion_ids": batch["recommended_unit_tested_skill_ids"],
        "actual_lifecycle_status_by_skill_id": actual,
        "shadow_eligible_ids": [skill_id for skill_id, status in actual.items() if status in SHADOW_SELECTION_ELIGIBLE_STATUSES],
        "lifecycle_mutation_count": 0,
        "selected_skill_id": None,
        "authorized_skill_id": None,
        "executed_skill_id": None,
        "boundary_statement": _BOUNDARY_STATEMENT,
    }
