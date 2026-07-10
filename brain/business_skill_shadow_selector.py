"""Pure diagnostic shadow selection for canonical Business Skills (V5.15.5).

This module consumes candidate and evidence diagnostics.  It performs no
matching, evidence mapping, reasoning, authorization, execution, or response
generation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from brain.business_skill import (
    ACCEPTANCE_GUARDED,
    LIMITED_ACTIVE,
    RUNTIME_AUDITED,
    SHADOW_AVAILABLE,
    STABLE,
    BusinessSkill,
)
from brain.business_skill_registry import (
    BUSINESS_SKILL_REGISTRY_VERSION,
    get_business_skill_registry,
)


BUSINESS_SKILL_SHADOW_SELECTOR_VERSION = "5.15.5"

SHADOW_SELECTION_ELIGIBLE_STATUSES = frozenset({
    SHADOW_AVAILABLE,
    ACCEPTANCE_GUARDED,
    RUNTIME_AUDITED,
    LIMITED_ACTIVE,
    STABLE,
})

DEFAULT_MINIMUM_SHADOW_CANDIDATE_CONFIDENCE = 0.50
DEFAULT_MINIMUM_SHADOW_CONFIDENCE_MARGIN = 0.10

NO_CANDIDATES = "NO_CANDIDATES"
INVALID_CANDIDATE = "INVALID_CANDIDATE"
UNKNOWN_SKILL = "UNKNOWN_SKILL"
LIFECYCLE_INELIGIBLE = "LIFECYCLE_INELIGIBLE"
BELOW_CONFIDENCE_THRESHOLD = "BELOW_CONFIDENCE_THRESHOLD"
EVIDENCE_MISSING = "EVIDENCE_MISSING"
EVIDENCE_NOT_READY = "EVIDENCE_NOT_READY"
AMBIGUOUS_CANDIDATES = "AMBIGUOUS_CANDIDATES"
SHADOW_SELECTED = "SHADOW_SELECTED"

SHADOW_SELECTION_STATUSES = (
    NO_CANDIDATES,
    INVALID_CANDIDATE,
    UNKNOWN_SKILL,
    LIFECYCLE_INELIGIBLE,
    BELOW_CONFIDENCE_THRESHOLD,
    EVIDENCE_MISSING,
    EVIDENCE_NOT_READY,
    AMBIGUOUS_CANDIDATES,
    SHADOW_SELECTED,
)

_BOUNDARY_STATEMENT = (
    "Shadow selection chooses only a diagnostic hypothesis; it does not select "
    "for runtime, authorize, execute, reason, ask, respond, or advance lifecycle."
)


def _registry_by_id(registry: Iterable[BusinessSkill] | Mapping[str, BusinessSkill] | None) -> dict[str, BusinessSkill]:
    source: Any = get_business_skill_registry() if registry is None else registry
    entries = source.values() if isinstance(source, Mapping) else source
    try:
        copied = tuple(entries)
    except TypeError:
        copied = ()
    result: dict[str, BusinessSkill] = {}
    duplicates: set[str] = set()
    for skill in copied:
        if isinstance(skill, BusinessSkill) and isinstance(skill.skill_id, str) and skill.skill_id:
            if skill.skill_id in result:
                duplicates.add(skill.skill_id)
            else:
                result[skill.skill_id] = skill
    for skill_id in duplicates:
        result.pop(skill_id, None)
    return result


def _valid_confidence(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1


def _policy_value(value: Any, default: float) -> float:
    return float(value) if _valid_confidence(value) else default


def _evidence_index(evidence_mappings: Any) -> tuple[dict[str, dict], set[str]]:
    index: dict[str, dict] = {}
    duplicates: set[str] = set()
    if isinstance(evidence_mappings, Mapping):
        items = tuple(evidence_mappings.items())
        for key, value in items:
            if not isinstance(key, str) or not isinstance(value, Mapping):
                continue
            item = deepcopy(dict(value))
            # The key is lookup metadata, never a substitute for artifact identity.
            identity = item.get("skill_id")
            if key in index:
                duplicates.add(key)
            else:
                index[key] = item
            if identity != key:
                item["_identity_mismatch"] = True
    elif isinstance(evidence_mappings, (list, tuple)):
        for value in evidence_mappings:
            if not isinstance(value, Mapping):
                continue
            item = deepcopy(dict(value))
            skill_id = item.get("skill_id")
            if not isinstance(skill_id, str) or not skill_id:
                continue
            if skill_id in index:
                duplicates.add(skill_id)
            else:
                index[skill_id] = item
    return index, duplicates


def evaluate_shadow_candidate_eligibility(
    candidate: Any,
    evidence_mapping: Any,
    registry: Iterable[BusinessSkill] | Mapping[str, BusinessSkill] | None = None,
    minimum_candidate_confidence: float | None = None,
) -> dict[str, Any]:
    """Evaluate one supplied candidate/evidence pair without producing it."""
    threshold = _policy_value(
        minimum_candidate_confidence,
        DEFAULT_MINIMUM_SHADOW_CANDIDATE_CONFIDENCE,
    )
    item = deepcopy(dict(candidate)) if isinstance(candidate, Mapping) else {}
    evidence = deepcopy(dict(evidence_mapping)) if isinstance(evidence_mapping, Mapping) else None
    skill_id = item.get("skill_id") if isinstance(item.get("skill_id"), str) else None
    canonical = _registry_by_id(registry).get(skill_id) if skill_id else None
    confidence = item.get("candidate_confidence")
    confidence_valid = _valid_confidence(confidence)
    confidence_sufficient = bool(confidence_valid and confidence >= threshold)
    lifecycle_status = canonical.active_status if canonical else None
    lifecycle_agrees = bool(canonical and item.get("active_status") == lifecycle_status)
    lifecycle_eligible = bool(lifecycle_agrees and lifecycle_status in SHADOW_SELECTION_ELIGIBLE_STATUSES)
    blocking = evidence.get("blocking_evidence") if evidence else []
    blocking_valid = isinstance(blocking, (list, tuple))
    blocking_fields = list(blocking) if blocking_valid else []
    evidence_id_matches = bool(
        evidence
        and evidence.get("skill_id") == skill_id
        and not evidence.get("_identity_mismatch", False)
    )

    candidate_valid = bool(
        isinstance(candidate, Mapping)
        and skill_id
        and item.get("candidate_shadow_mode") is True
        and item.get("candidate_selected") is False
        and item.get("candidate_authorized") is False
        and item.get("candidate_reasoning_ready") is None
        and confidence_valid
        and isinstance(item.get("active_status"), str)
    )
    evidence_valid = bool(
        evidence_id_matches
        and evidence.get("evidence_mapping_valid") is True
        and evidence.get("evidence_shadow_mode") is True
        and evidence.get("evidence_selected") is False
        and evidence.get("evidence_authorized") is False
        and evidence.get("evidence_executed") is False
        and isinstance(evidence.get("evidence_ready"), bool)
        and blocking_valid
    )

    failures: list[str] = []
    reasons: list[str] = []
    def fail(code: str, reason: str) -> None:
        if code not in failures:
            failures.append(code)
            reasons.append(reason)

    if not isinstance(candidate, Mapping) or not skill_id:
        fail(INVALID_CANDIDATE, "candidate must be a mapping with a non-empty exact skill_id")
    if skill_id and canonical is None:
        fail(UNKNOWN_SKILL, "candidate skill_id does not exactly identify a canonical skill")
    if item.get("candidate_shadow_mode") is not True:
        fail(INVALID_CANDIDATE, "candidate_shadow_mode must be True")
    if item.get("candidate_selected") is not False:
        fail(INVALID_CANDIDATE, "candidate_selected must be False")
    if item.get("candidate_authorized") is not False:
        fail(INVALID_CANDIDATE, "candidate_authorized must be False")
    if item.get("candidate_reasoning_ready") is not None:
        fail(INVALID_CANDIDATE, "candidate_reasoning_ready must remain None")
    if not confidence_valid:
        fail(INVALID_CANDIDATE, "candidate confidence must be numeric, not bool, and between 0 and 1")
    elif not confidence_sufficient:
        fail(BELOW_CONFIDENCE_THRESHOLD, "candidate confidence is below the shadow threshold")
    if canonical and not lifecycle_agrees:
        fail(LIFECYCLE_INELIGIBLE, "candidate lifecycle does not agree with canonical lifecycle")
    elif canonical and not lifecycle_eligible:
        fail(LIFECYCLE_INELIGIBLE, "canonical lifecycle is not shadow-selection eligible")
    if evidence is None:
        fail(EVIDENCE_MISSING, "no unique evidence mapping was supplied for the candidate")
    elif not evidence_id_matches:
        fail(EVIDENCE_MISSING, "evidence skill_id does not exactly match candidate skill_id")
    else:
        if not evidence_valid:
            fail(EVIDENCE_NOT_READY, "evidence mapping boundary flags or validity are not eligible")
        if evidence.get("evidence_ready") is not True:
            fail(EVIDENCE_NOT_READY, "evidence_ready must be True")
        if not blocking_valid or blocking_fields:
            fail(EVIDENCE_NOT_READY, "blocking_evidence must be an empty list or tuple")

    return {
        "skill_id": skill_id,
        "canonical_skill_found": canonical is not None,
        "candidate_valid": candidate_valid,
        "candidate_confidence": confidence,
        "candidate_confidence_valid": confidence_valid,
        "candidate_confidence_sufficient": confidence_sufficient,
        "lifecycle_status": lifecycle_status,
        "candidate_lifecycle_status": item.get("active_status"),
        "lifecycle_agrees": lifecycle_agrees,
        "lifecycle_eligible": lifecycle_eligible,
        "evidence_mapping_found": evidence is not None,
        "evidence_mapping_valid": evidence_valid,
        "evidence_ready": bool(evidence and evidence.get("evidence_ready") is True),
        "evidence_blocking_fields": blocking_fields,
        "shadow_eligible": not failures,
        "eligibility_failures": failures,
        "eligibility_reasons": reasons,
    }


def _empty_decision(status: str) -> dict[str, Any]:
    return {
        "selection_status": status,
        "shadow_selected": False,
        "shadow_selected_skill_id": None,
        "shadow_selected_candidate": None,
        "considered_candidate_ids": [],
        "eligible_candidate_ids": [],
        "rejected_candidate_ids": [],
        "candidate_eligibility": [],
        "top_eligible_confidence": None,
        "second_eligible_confidence": None,
        "confidence_margin": None,
        "confidence_margin_sufficient": None,
        "shadow_mode": True,
        "authorized": False,
        "executed": False,
        "reasoning_executed": False,
        "response_generated": False,
        "follow_up_generated": False,
        "lifecycle_advanced": False,
    }


def select_shadow_business_skill(
    candidates: Any,
    evidence_mappings: Any,
    registry: Iterable[BusinessSkill] | Mapping[str, BusinessSkill] | None = None,
    minimum_candidate_confidence: float | None = None,
    minimum_confidence_margin: float | None = None,
) -> dict[str, Any]:
    """Choose at most one already-produced diagnostic shadow hypothesis."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        return _empty_decision(NO_CANDIDATES)
    candidate_copies = deepcopy(list(candidates))
    evidence_index, duplicates = _evidence_index(evidence_mappings)
    results: list[dict[str, Any]] = []
    for candidate in candidate_copies:
        skill_id = candidate.get("skill_id") if isinstance(candidate, Mapping) else None
        evidence = None if skill_id in duplicates else evidence_index.get(skill_id)
        result = evaluate_shadow_candidate_eligibility(
            candidate, evidence, registry, minimum_candidate_confidence
        )
        if skill_id in duplicates:
            result["evidence_mapping_found"] = True
            result["evidence_mapping_valid"] = False
            result["shadow_eligible"] = False
            result["eligibility_failures"] = [
                failure for failure in result["eligibility_failures"]
                if failure != EVIDENCE_MISSING
            ]
            result["eligibility_failures"] = list(dict.fromkeys(result["eligibility_failures"] + [EVIDENCE_NOT_READY]))
            result["eligibility_reasons"] = result["eligibility_reasons"] + ["duplicate evidence mappings make identity ambiguous"]
        results.append(result)

    eligible_indexes = [index for index, result in enumerate(results) if result["shadow_eligible"]]
    if eligible_indexes and all(
        isinstance(candidate_copies[index].get("candidate_rank"), int)
        and not isinstance(candidate_copies[index].get("candidate_rank"), bool)
        and candidate_copies[index]["candidate_rank"] > 0
        for index in eligible_indexes
    ):
        eligible_indexes.sort(key=lambda index: candidate_copies[index]["candidate_rank"])
    else:
        eligible_indexes.sort(key=lambda index: -results[index]["candidate_confidence"])

    decision = _empty_decision(INVALID_CANDIDATE)
    decision["considered_candidate_ids"] = [result["skill_id"] for result in results]
    decision["eligible_candidate_ids"] = [results[index]["skill_id"] for index in eligible_indexes]
    decision["rejected_candidate_ids"] = [result["skill_id"] for result in results if not result["shadow_eligible"]]
    decision["candidate_eligibility"] = results
    if not eligible_indexes:
        priority = (
            UNKNOWN_SKILL, LIFECYCLE_INELIGIBLE, INVALID_CANDIDATE,
            BELOW_CONFIDENCE_THRESHOLD, EVIDENCE_MISSING, EVIDENCE_NOT_READY,
        )
        failures = {failure for result in results for failure in result["eligibility_failures"]}
        decision["selection_status"] = next((status for status in priority if status in failures), INVALID_CANDIDATE)
        return decision

    top_index = eligible_indexes[0]
    top_confidence = results[top_index]["candidate_confidence"]
    decision["top_eligible_confidence"] = top_confidence
    if len(eligible_indexes) > 1:
        second_confidence = results[eligible_indexes[1]]["candidate_confidence"]
        margin = round(top_confidence - second_confidence, 10)
        required_margin = _policy_value(minimum_confidence_margin, DEFAULT_MINIMUM_SHADOW_CONFIDENCE_MARGIN)
        decision["second_eligible_confidence"] = second_confidence
        decision["confidence_margin"] = margin
        decision["confidence_margin_sufficient"] = margin >= required_margin
        if margin < required_margin:
            decision["selection_status"] = AMBIGUOUS_CANDIDATES
            return decision

    decision.update({
        "selection_status": SHADOW_SELECTED,
        "shadow_selected": True,
        "shadow_selected_skill_id": results[top_index]["skill_id"],
        "shadow_selected_candidate": deepcopy(candidate_copies[top_index]),
        "confidence_margin_sufficient": True,
    })
    return decision


def build_business_skill_shadow_selection_diagnostics(
    candidates: Any,
    evidence_mappings: Any,
    registry: Iterable[BusinessSkill] | Mapping[str, BusinessSkill] | None = None,
    minimum_candidate_confidence: float | None = None,
    minimum_confidence_margin: float | None = None,
    candidate_matcher_version: str | None = "5.15.3",
    evidence_mapper_version: str | None = "5.15.4",
) -> dict[str, Any]:
    decision = select_shadow_business_skill(
        candidates, evidence_mappings, registry,
        minimum_candidate_confidence, minimum_confidence_margin,
    )
    return {
        "selector_version": BUSINESS_SKILL_SHADOW_SELECTOR_VERSION,
        "registry_version": BUSINESS_SKILL_REGISTRY_VERSION,
        "candidate_matcher_version": candidate_matcher_version,
        "evidence_mapper_version": evidence_mapper_version,
        "selection_status": decision["selection_status"],
        "considered_candidate_count": len(decision["candidate_eligibility"]),
        "eligible_candidate_count": len(decision["eligible_candidate_ids"]),
        "rejected_candidate_count": len(decision["rejected_candidate_ids"]),
        "shadow_selected_skill_id": decision["shadow_selected_skill_id"],
        "lifecycle_gate_applied": True,
        "ambiguity_gate_applied": True,
        "evidence_gate_applied": True,
        "confidence_gate_applied": True,
        "selected_skill_id_for_runtime": None,
        "authorized_skill_id": None,
        "executed_skill_id": None,
        "response_authority": None,
        "boundary_statement": _BOUNDARY_STATEMENT,
        "selection": decision,
    }
