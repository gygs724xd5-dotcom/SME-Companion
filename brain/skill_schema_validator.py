from __future__ import annotations

import re
from typing import Any

from brain.knowledge_skill_reference import (
    CompatibilityMode,
    IssueSeverity,
    ReviewStatus,
    SUPPORTED_PROCEDURAL_ROLES,
    SUPPORTED_SKILL_SCHEMA_VERSIONS,
    SUPPORTED_SKILL_STATUS,
    SUPPORTED_STAGES,
    ValidationStatus,
    as_dict,
    as_list,
    issue,
    status_from_issues,
    unique,
)


SKILL_SCHEMA_VALIDATOR_VERSION = "5.9.1"


def _is_semver(value: Any) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+$", str(value or "")))


def _strings(values: Any) -> bool:
    return all(isinstance(item, str) and bool(item) for item in as_list(values))


def _dupes(values: list[str]) -> list[str]:
    seen, duplicates = set(), []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def validate_skill_schema(parsed_document: Any) -> dict:
    metadata = as_dict(getattr(parsed_document, "metadata", parsed_document.get("metadata") if isinstance(parsed_document, dict) else {}))
    parse_status = getattr(parsed_document, "parse_status", parsed_document.get("parse_status") if isinstance(parsed_document, dict) else "")
    issues = []
    if parse_status == "EMPTY_DOCUMENT":
        issues.append(issue("EMPTY_DOCUMENT", IssueSeverity.FATAL.value, message="Skill document is empty."))
    if parse_status == "INVALID_FRONT_MATTER":
        issues.append(issue("INVALID_FRONT_MATTER", IssueSeverity.FATAL.value))
    if parse_status == "LEGACY_NO_FRONT_MATTER":
        return {
            "validation_status": ValidationStatus.LEGACY_COMPATIBLE.value,
            "validation_issues": [issue("LEGACY_NO_FRONT_MATTER", IssueSeverity.INFO.value).to_dict()],
            "validator_version": SKILL_SCHEMA_VALIDATOR_VERSION,
        }

    required = [
        "skill_id", "display_name", "skill_version", "schema_version", "status", "domain",
        "procedural_role", "stage", "canonical_references", "authority", "compatibility", "review",
    ]
    for field in required:
        if metadata.get(field) in (None, "", [], {}):
            issues.append(issue("MISSING_REQUIRED_FIELD", IssueSeverity.ERROR.value, field, raw_value=metadata.get(field)))
    if metadata.get("schema_version") not in SUPPORTED_SKILL_SCHEMA_VERSIONS:
        issues.append(issue("UNSUPPORTED_SCHEMA_VERSION", IssueSeverity.ERROR.value, "schema_version", raw_value=metadata.get("schema_version")))
    if metadata.get("skill_version") and not _is_semver(metadata.get("skill_version")):
        issues.append(issue("INVALID_SKILL_VERSION", IssueSeverity.ERROR.value, "skill_version", raw_value=metadata.get("skill_version")))
    if metadata.get("status") and metadata.get("status") not in SUPPORTED_SKILL_STATUS:
        issues.append(issue("INVALID_STATUS", IssueSeverity.ERROR.value, "status", raw_value=metadata.get("status")))
    if metadata.get("procedural_role") and metadata.get("procedural_role") not in SUPPORTED_PROCEDURAL_ROLES:
        issues.append(issue("INVALID_PROCEDURAL_ROLE", IssueSeverity.ERROR.value, "procedural_role", raw_value=metadata.get("procedural_role")))
    if metadata.get("stage") and metadata.get("stage") not in SUPPORTED_STAGES:
        issues.append(issue("INVALID_STAGE", IssueSeverity.ERROR.value, "stage", raw_value=metadata.get("stage")))

    references = as_dict(metadata.get("canonical_references"))
    knowledge = as_dict(references.get("knowledge"))
    metrics = as_dict(references.get("metrics"))
    evidence = as_dict(references.get("evidence"))
    primary = as_list(knowledge.get("primary"))
    secondary = as_list(knowledge.get("secondary"))
    if as_dict(metadata.get("compatibility")).get("mode") == CompatibilityMode.STRICT_CANONICAL.value and not primary:
        issues.append(issue("STRICT_MODE_REQUIRES_PRIMARY_KNOWLEDGE", IssueSeverity.ERROR.value, "canonical_references.knowledge.primary"))
    if set(primary).intersection(secondary):
        issues.append(issue("PRIMARY_SECONDARY_OVERLAP", IssueSeverity.ERROR.value, "canonical_references.knowledge"))
    for field_name, values in {
        "canonical_references.knowledge.primary": primary,
        "canonical_references.knowledge.secondary": secondary,
        "canonical_references.metrics.input": as_list(metrics.get("input")),
        "canonical_references.metrics.derived": as_list(metrics.get("derived")),
        "canonical_references.metrics.context": as_list(metrics.get("context")),
        "canonical_references.relationship_rules": as_list(references.get("relationship_rules")),
        "canonical_references.evidence.required": as_list(evidence.get("required")),
        "canonical_references.evidence.conditionally_required": as_list(evidence.get("conditionally_required")),
        "canonical_references.evidence.optional": as_list(evidence.get("optional")),
    }.items():
        if not _strings(values):
            issues.append(issue("NON_STRING_REFERENCE", IssueSeverity.ERROR.value, field_name, raw_value=values))
        for duplicate in _dupes([str(item) for item in values]):
            issues.append(issue("DUPLICATE_REFERENCE", IssueSeverity.ERROR.value, field_name, raw_value=duplicate))

    metric_pool = set(as_list(metrics.get("input")) + as_list(metrics.get("context")))
    derived = set(as_list(metrics.get("derived")))
    for required_evidence in as_list(evidence.get("required")):
        if required_evidence in derived:
            issues.append(issue("DERIVED_METRIC_DIRECTLY_REQUIRED", IssueSeverity.ERROR.value, "canonical_references.evidence.required", raw_value=required_evidence))
        if required_evidence not in metric_pool:
            issues.append(issue("REQUIRED_EVIDENCE_NOT_REFERENCED_AS_INPUT_OR_CONTEXT", IssueSeverity.ERROR.value, "canonical_references.evidence.required", raw_value=required_evidence))

    authority = as_dict(metadata.get("authority"))
    allowed = as_list(authority.get("allowed"))
    forbidden = as_list(authority.get("forbidden"))
    if set(allowed).intersection(forbidden):
        issues.append(issue("ALLOWED_FORBIDDEN_CONFLICT", IssueSeverity.ERROR.value, "authority"))
    compatibility_mode = as_dict(metadata.get("compatibility")).get("mode")
    if compatibility_mode and compatibility_mode not in {item.value for item in CompatibilityMode}:
        issues.append(issue("INVALID_COMPATIBILITY_MODE", IssueSeverity.ERROR.value, "compatibility.mode", raw_value=compatibility_mode))
    review_status = as_dict(metadata.get("review")).get("status")
    if review_status and review_status not in {item.value for item in ReviewStatus}:
        issues.append(issue("INVALID_REVIEW_STATUS", IssueSeverity.ERROR.value, "review.status", raw_value=review_status))
    readiness = as_dict(metadata.get("readiness"))
    if readiness:
        if readiness.get("required_evidence_policy") not in (None, "all", "any"):
            issues.append(issue("INVALID_READINESS_POLICY", IssueSeverity.ERROR.value, "readiness.required_evidence_policy"))
        if readiness.get("conflict_policy") not in (None, "block", "partial", "allow"):
            issues.append(issue("INVALID_READINESS_POLICY", IssueSeverity.ERROR.value, "readiness.conflict_policy"))

    return {
        "validation_status": status_from_issues(issues),
        "validation_issues": [item.to_dict() for item in issues],
        "normalized_references": {
            "knowledge_primary": unique(primary),
            "knowledge_secondary": unique(secondary),
            "metric_input": unique(as_list(metrics.get("input"))),
            "metric_derived": unique(as_list(metrics.get("derived"))),
            "metric_context": unique(as_list(metrics.get("context"))),
        },
        "validator_version": SKILL_SCHEMA_VALIDATOR_VERSION,
    }
