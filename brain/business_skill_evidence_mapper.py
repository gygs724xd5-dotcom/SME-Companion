"""Pure canonical Business Skill evidence mapping for SME Companion V5.15.4.

The mapper evaluates explicitly supplied values.  It does not discover evidence,
select or authorize skills, execute reasoning, or produce user-facing responses.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from typing import Any, Iterable, Mapping

from brain.business_skill import BusinessSkill, normalize_business_skill, validate_business_skill
from brain.business_skill_registry import (
    BUSINESS_SKILL_REGISTRY_VERSION,
    get_business_skill_registry,
)


BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION = "5.15.4"

PRESENT = "PRESENT"
MISSING = "MISSING"
ASSUMABLE = "ASSUMABLE"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
LOW_CONFIDENCE = "LOW_CONFIDENCE"
STALE = "STALE"
INVALID = "INVALID"
OPTIONAL_MISSING = "OPTIONAL_MISSING"

EVIDENCE_MAPPING_STATUSES = (
    PRESENT,
    MISSING,
    ASSUMABLE,
    CONFIRMATION_REQUIRED,
    LOW_CONFIDENCE,
    STALE,
    INVALID,
    OPTIONAL_MISSING,
)

_OBSERVATION_KEYS = {
    "value", "confidence", "source", "freshness", "user_confirmed",
    "assumed", "sensitive", "validation_status", "validation_errors",
}


def _value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _confidence(value: Any) -> tuple[float, list[str]]:
    if isinstance(value, bool):
        return 0.0, ["confidence must be a number between 0 and 1"]
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0, ["confidence must be a number between 0 and 1"]
    if number < 0 or number > 1:
        return min(1.0, max(0.0, number)), ["confidence was clamped to the range 0..1"]
    return number, []


def normalize_available_evidence(available_evidence: Any) -> dict[str, dict[str, Any]]:
    """Copy and normalize raw values and enriched observations.

    Raw-value defaults (1.0, explicit_input, current) are mapper conventions,
    not claims about the historical origin of a value.
    """
    if not isinstance(available_evidence, Mapping):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for original_name, supplied in available_evidence.items():
        field_name = str(original_name)
        enriched = isinstance(supplied, Mapping) and bool(_OBSERVATION_KEYS.intersection(supplied))
        source = deepcopy(dict(supplied)) if enriched else {}
        value = deepcopy(source.get("value")) if enriched else deepcopy(supplied)
        confidence, confidence_errors = _confidence(source.get("confidence", 1.0))
        inherited_errors = source.get("validation_errors", [])
        if not isinstance(inherited_errors, (list, tuple)):
            inherited_errors = [str(inherited_errors)] if inherited_errors else []
        errors = [str(item) for item in inherited_errors] + confidence_errors
        normalized[field_name] = {
            "field_name": field_name,
            "value": value,
            "value_present": _value_present(value),
            "confidence": confidence,
            "source": str(source.get("source", "explicit_input") or "unknown").strip().lower(),
            "freshness": str(source.get("freshness", "current") or "unknown").strip().lower(),
            "user_confirmed": bool(source.get("user_confirmed", False)),
            "assumed": bool(source.get("assumed", False)),
            "sensitive": bool(source.get("sensitive", False)),
            "validation_status": str(source.get("validation_status", "NOT_VALIDATED") or "NOT_VALIDATED"),
            "validation_errors": errors,
        }
    return normalized


def _type_validation(value: Any, field_type: str) -> tuple[str, list[str]]:
    kind = str(field_type or "").strip().lower().replace("string", "text")
    number = isinstance(value, (int, float)) and not isinstance(value, bool)
    checks = {
        "number": number,
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "text": isinstance(value, str) and bool(value.strip()),
        "boolean": isinstance(value, bool),
        "list": isinstance(value, (list, tuple, set)),
        "sequence": isinstance(value, (list, tuple, set)),
        "mapping": isinstance(value, Mapping),
        "dict": isinstance(value, Mapping),
        "date": _value_present(value),
        "datetime": _value_present(value),
        "date_or_text": _value_present(value),
        "boolean_or_text": isinstance(value, bool) or (isinstance(value, str) and bool(value.strip())),
    }
    if kind not in checks:
        return "UNVALIDATED", [f"unknown field_type: {field_type}"]
    if not checks[kind]:
        return "INVALID", [f"value does not satisfy field_type: {field_type}"]
    return "VALID", []


def _rule_validation(value: Any, rule: str) -> list[str]:
    rule = str(rule or "").strip().lower()
    if not rule or rule == "number":
        return []
    number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if rule == "positive_number" and (not number or value <= 0):
        return ["value must be a positive number"]
    if rule == "non_negative_number" and (not number or value < 0):
        return ["value must be a non-negative number"]
    if rule == "percentage_or_decimal" and (not number or value < 0 or value > 100):
        return ["value must be a percentage or decimal between 0 and 100"]
    if rule not in {"positive_number", "non_negative_number", "percentage_or_decimal", "number"}:
        return [f"unknown validation_rule: {rule}"]
    return []


def _source_satisfies(observed: str, required: str) -> bool:
    required = str(required or "").strip().lower()
    observed = str(observed or "unknown").strip().lower()
    if not required or required in {"any", "not_applicable"}:
        return True
    if observed == required:
        return True
    allowed = set(required.replace("|", "_or_").split("_or_"))
    if observed == "explicit_input":
        observed = "current_turn"
    return observed in allowed


def _freshness_satisfies(observed: str, required: str) -> bool:
    observed = str(observed or "unknown").strip().lower()
    required = str(required or "").strip().lower()
    if not required or required in {"any", "not_applicable"}:
        return True
    allowed = {
        "current": {"current"},
        "recent": {"recent"},
        "current_or_recent": {"current", "recent"},
    }
    return observed in allowed.get(required, {required})


def map_required_evidence(evidence_contract: Any, available_evidence: Any) -> dict[str, Any]:
    """Map one required/optional contract against normalized or raw evidence."""
    contract = asdict(evidence_contract) if is_dataclass(evidence_contract) else deepcopy(evidence_contract)
    if not isinstance(contract, dict):
        contract = {}
    field_name = str(contract.get("field_name", "") or "").strip()
    required = bool(contract.get("required", True))
    observations = available_evidence
    if not (isinstance(observations, dict) and all(
        isinstance(item, dict) and "field_name" in item and "value_present" in item
        for item in observations.values()
    )):
        observations = normalize_available_evidence(available_evidence)
    observation = deepcopy(observations.get(field_name)) if isinstance(observations, dict) else None
    present = bool(observation and observation.get("value_present"))
    confidence_required, contract_confidence_errors = _confidence(contract.get("confidence_required", 0.0))
    can_assume = bool(contract.get("can_assume", False))
    assumption_default = deepcopy(contract.get("assumption_default"))
    sensitive = bool(contract.get("sensitive", False))
    confirmation_required = bool(contract.get("user_confirmation_required", False))
    reasons: list[str] = []
    assumed = False

    if not present:
        if can_assume and _value_present(assumption_default) and not sensitive:
            assumed = True
            status = CONFIRMATION_REQUIRED if confirmation_required else ASSUMABLE
            reasons.append("usable assumption default proposed" if not confirmation_required else "assumption requires user confirmation")
        else:
            status = MISSING if required else OPTIONAL_MISSING
            reasons.append("evidence value is missing")
            if can_assume and sensitive:
                reasons.append("sensitive evidence cannot be automatically assumed")
            elif can_assume:
                reasons.append("no usable assumption default")
    else:
        value = observation["value"]
        validation_status, validation_errors = _type_validation(value, contract.get("field_type", ""))
        rule_errors = _rule_validation(value, contract.get("validation_rule", ""))
        errors = list(observation.get("validation_errors", [])) + contract_confidence_errors + validation_errors + rule_errors
        observation["validation_errors"] = errors
        observation["validation_status"] = "INVALID" if errors or validation_status != "VALID" else "VALID"
        source_ok = _source_satisfies(observation.get("source", "unknown"), contract.get("source", ""))
        freshness_ok = _freshness_satisfies(observation.get("freshness", "unknown"), contract.get("freshness", ""))
        confidence_ok = observation.get("confidence", 0.0) >= confidence_required
        if observation.get("assumed") and not can_assume:
            status = INVALID
            reasons.append("assumed evidence is disallowed by the evidence contract")
        elif errors or validation_status != "VALID":
            status = INVALID
            reasons.extend(errors or ["field type could not be validated"])
        elif not source_ok:
            status = INVALID
            reasons.append("observed source does not satisfy source requirement")
        elif not freshness_ok:
            status = STALE
            reasons.append("observed freshness does not satisfy freshness requirement")
        elif not confidence_ok:
            status = LOW_CONFIDENCE
            reasons.append("observed confidence is below required confidence")
        elif confirmation_required and not observation.get("user_confirmed"):
            status = CONFIRMATION_REQUIRED
            reasons.append("user confirmation is required")
        else:
            status = PRESENT
            reasons.append("evidence satisfies contract")

    observed_confidence = observation.get("confidence") if observation else None
    source_ok = _source_satisfies(observation.get("source", "unknown"), contract.get("source", "")) if present else False
    freshness_ok = _freshness_satisfies(observation.get("freshness", "unknown"), contract.get("freshness", "")) if present else False
    confidence_ok = bool(present and observed_confidence >= confidence_required)
    blocking = required and status != PRESENT
    return {
        "field_name": field_name,
        "expected_field_type": str(contract.get("field_type", "") or ""),
        "required": required,
        "observed_value": deepcopy(observation.get("value")) if observation else None,
        "value_present": present,
        "source_requirement": str(contract.get("source", "") or ""),
        "observed_source": observation.get("source") if observation else None,
        "source_sufficient": source_ok,
        "freshness_requirement": str(contract.get("freshness", "") or ""),
        "observed_freshness": observation.get("freshness") if observation else None,
        "freshness_sufficient": freshness_ok,
        "confidence_required": confidence_required,
        "observed_confidence": observed_confidence,
        "confidence_sufficient": confidence_ok,
        "can_assume": can_assume,
        "assumption_default": assumption_default,
        "assumed": assumed,
        "sensitive": sensitive,
        "user_confirmation_required": confirmation_required,
        "user_confirmed": bool(observation and observation.get("user_confirmed")),
        "validation_rule": str(contract.get("validation_rule", "") or ""),
        "validation_status": observation.get("validation_status", "NOT_VALIDATED") if observation else "NOT_VALIDATED",
        "validation_errors": list(observation.get("validation_errors", [])) if observation else [],
        "mapping_status": status,
        "blocking": blocking,
        "reasons": reasons,
    }


def map_business_skill_evidence(skill: BusinessSkill | dict, available_evidence: Any = None) -> dict[str, Any]:
    validation = validate_business_skill(skill)
    normalized_skill = validation["normalized"]
    observations = normalize_available_evidence(available_evidence)
    mappings = [map_required_evidence(item, observations) for item in normalized_skill["required_evidence"]]
    mappings += [map_required_evidence({**item, "required": False}, observations) for item in normalized_skill["optional_evidence"]]
    required_mappings = [item for item in mappings if item["required"]]
    optional_mappings = [item for item in mappings if not item["required"]]
    by_status = lambda status: [item["field_name"] for item in required_mappings if item["mapping_status"] == status]
    confidence_values = [
        item["observed_confidence"] for item in required_mappings
        if item["value_present"] and isinstance(item["observed_confidence"], (int, float))
    ]
    blocking = [item["field_name"] for item in mappings if item["blocking"]]
    return {
        "skill_id": normalized_skill["skill_id"],
        "skill_valid": bool(validation["valid"]),
        "evidence_mapping_valid": bool(validation["valid"] and all(item["field_name"] for item in mappings)),
        "required_evidence_count": len(required_mappings),
        "optional_evidence_count": len(optional_mappings),
        "present_required_evidence": by_status(PRESENT),
        "missing_required_evidence": by_status(MISSING),
        "assumable_required_evidence": by_status(ASSUMABLE),
        "low_confidence_required_evidence": by_status(LOW_CONFIDENCE),
        "stale_required_evidence": by_status(STALE),
        "invalid_required_evidence": by_status(INVALID),
        "confirmation_required_evidence": by_status(CONFIRMATION_REQUIRED),
        "optional_evidence_present": [item["field_name"] for item in optional_mappings if item["mapping_status"] == PRESENT],
        "optional_evidence_missing": [item["field_name"] for item in optional_mappings if item["mapping_status"] == OPTIONAL_MISSING],
        "blocking_evidence": blocking,
        "evidence_ready": bool(validation["valid"] and not blocking),
        "evidence_confidence_floor": min(confidence_values) if confidence_values else None,
        "evidence_mappings": mappings,
        "evidence_shadow_mode": True,
        "evidence_selected": False,
        "evidence_authorized": False,
        "evidence_executed": False,
    }


def _registry_entries(registry: Iterable[BusinessSkill] | None) -> tuple[Any, ...]:
    if registry is None:
        return tuple(get_business_skill_registry())
    try:
        return tuple(registry)
    except TypeError:
        return ()


def map_candidate_skill_evidence(candidate: Any, available_evidence: Any = None, registry: Iterable[BusinessSkill] | None = None) -> dict[str, Any]:
    candidate_copy = deepcopy(candidate) if isinstance(candidate, dict) else {}
    skill_id = candidate_copy.get("skill_id")
    skill = next((item for item in _registry_entries(registry) if isinstance(skill_id, str) and getattr(item, "skill_id", None) == skill_id), None)
    if skill is None:
        return {
            "candidate": candidate_copy, "candidate_skill_id": skill_id, "candidate_mapped": False,
            "unmapped_reason": "unknown_or_invalid_exact_skill_id", "evidence_ready": False,
            "evidence_shadow_mode": True, "evidence_selected": False,
            "evidence_authorized": False, "evidence_executed": False,
        }
    result = map_business_skill_evidence(skill, available_evidence)
    return {"candidate": candidate_copy, "candidate_skill_id": skill_id, "candidate_mapped": True, **result}


def build_business_skill_evidence_diagnostics(skill: BusinessSkill | dict, available_evidence: Any = None) -> dict[str, Any]:
    normalized_skill = normalize_business_skill(skill)
    mapped = map_business_skill_evidence(normalized_skill, available_evidence)
    safe_mappings = []
    for item in mapped["evidence_mappings"]:
        safe = deepcopy(item)
        safe["observed_value"] = "[REDACTED]" if safe["sensitive"] and safe["value_present"] else None
        safe["assumption_default"] = "[REDACTED]" if safe["sensitive"] and _value_present(safe["assumption_default"]) else None
        safe_mappings.append(safe)
    return {
        "mapper_version": BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION,
        "registry_version": BUSINESS_SKILL_REGISTRY_VERSION,
        "skill_id": mapped["skill_id"],
        "skill_lifecycle_status": normalized_skill["active_status"],
        "evidence_input_field_names": list(normalize_available_evidence(available_evidence)),
        "required_evidence_field_names": [item["field_name"] for item in normalized_skill["required_evidence"]],
        "optional_evidence_field_names": [item["field_name"] for item in normalized_skill["optional_evidence"]],
        "mapped_evidence_statuses": {item["field_name"]: item["mapping_status"] for item in safe_mappings},
        "blocking_evidence_field_names": list(mapped["blocking_evidence"]),
        "evidence_ready": mapped["evidence_ready"],
        "evidence_confidence_floor": mapped["evidence_confidence_floor"],
        "shadow_mode": True,
        "selected_skill_id": None,
        "authorized_skill_id": None,
        "executed_skill_id": None,
        "evidence_mappings": safe_mappings,
        "boundary_statement": (
            "Evidence mapping is not extraction, selection, authorization, reasoning, execution, "
            "question generation, response authority, or response generation."
        ),
    }
