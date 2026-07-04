from __future__ import annotations

from typing import Any

from brain.knowledge_skill_reference import (
    IssueSeverity,
    PROTECTED_FORBIDDEN_AUTHORITIES,
    SUPPORTED_ALLOWED_AUTHORITIES,
    as_dict,
    as_list,
    issue,
    status_from_issues,
)


SKILL_AUTHORITY_VALIDATOR_VERSION = "5.9.1"


def validate_skill_authority(skill_or_metadata: Any) -> dict:
    if hasattr(skill_or_metadata, "metadata"):
        metadata = as_dict(skill_or_metadata.metadata)
    elif isinstance(skill_or_metadata, dict) and "metadata" in skill_or_metadata:
        metadata = as_dict(skill_or_metadata.get("metadata"))
    else:
        metadata = as_dict(skill_or_metadata)
    authority = as_dict(metadata.get("authority"))
    allowed = as_list(authority.get("allowed"))
    forbidden = as_list(authority.get("forbidden"))
    issues = []
    for value in allowed:
        if value not in SUPPORTED_ALLOWED_AUTHORITIES:
            issues.append(issue("AUTHORITY_OVERREACH", IssueSeverity.ERROR.value, "authority.allowed", raw_value=value))
        if value in PROTECTED_FORBIDDEN_AUTHORITIES:
            issues.append(issue(PROTECTED_FORBIDDEN_AUTHORITIES[value], IssueSeverity.ERROR.value, "authority.allowed", raw_value=value))
    for value in forbidden:
        if value in allowed:
            issues.append(issue("ALLOWED_FORBIDDEN_CONFLICT", IssueSeverity.ERROR.value, "authority", raw_value=value))
    for protected, code in PROTECTED_FORBIDDEN_AUTHORITIES.items():
        if protected in allowed:
            issues.append(issue(code, IssueSeverity.ERROR.value, "authority.allowed", raw_value=protected))
    return {
        "validation_status": status_from_issues(issues),
        "validation_issues": [item.to_dict() for item in issues],
        "authority_scope_valid": not any(item.severity in {"ERROR", "FATAL"} for item in issues),
        "validator_version": SKILL_AUTHORITY_VALIDATOR_VERSION,
    }
