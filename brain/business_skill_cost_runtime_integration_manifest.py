"""Immutable V5.15.22 governance approval; grants no runtime authority."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_cost_runtime_integration_qualification import (
    QUALIFICATION_VERSION, SUPPORTED_SKILL_IDS,
    ControlledRuntimeIntegrationQualification,
    verify_controlled_runtime_integration_qualification,
)
from brain.business_skill_cost_response_runtime_bridge import COST_RUNTIME_BRIDGE_VERSION, FEATURE_GATE_NAME

CONTROLLED_RUNTIME_INTEGRATION_MANIFEST_VERSION = "5.15.22"
CONTROLLED_COST_RESPONSE_RUNTIME_INTEGRATION = "CONTROLLED_COST_RESPONSE_RUNTIME_INTEGRATION"
CONTROLLED_INTEGRATION_APPROVED = "CONTROLLED_INTEGRATION_APPROVED"
APPROVAL_REASON = "CANONICAL_V5_15_21_QUALIFICATION_APPROVED"
DIAGNOSTICS = (("authority", "GOVERNANCE_ONLY"), ("runtime_execution", "FALSE"),
               ("feature_gate_mutated", "FALSE"), ("production_activation", "FALSE"))
_HEX = re.compile(r"^[0-9a-f]{64}$")

@dataclass(frozen=True)
class AuthorityBoundary:
    routing: bool = False
    response_selection: bool = False
    delivery_or_commit: bool = False
    persistence: bool = False
    tool_execution: bool = False
    feature_gate_mutation: bool = False
    production_activation: bool = False

@dataclass(frozen=True)
class ControlledRuntimeIntegrationApproval:
    manifest_version: str; registry_version: str; skill_id: str
    lifecycle_status: str; integration_scope: str; approval_status: str
    approval_reason: str; qualification_version: str; qualification_digest: str
    delivery_qualification_version: str; delivery_qualification_id: str
    delivery_qualification_digest: str; runtime_bridge_version: str
    feature_gate_name: str; feature_gate_passed: bool; handoff_digest: str
    result_digest: str; request_id: str; payload_digest: str
    provenance_verified: bool; authority_boundary_verified: bool
    authority_boundary: AuthorityBoundary; diagnostics: tuple[tuple[str, str], ...]
    qualification: ControlledRuntimeIntegrationQualification; approval_digest: str

@dataclass(frozen=True)
class ControlledRuntimeIntegrationManifest:
    manifest_version: str; registry_version: str; integration_scope: str
    approved_skill_ids: tuple[str, ...]
    approvals: tuple[ControlledRuntimeIntegrationApproval, ...]
    approval_status: str; diagnostics: tuple[tuple[str, str], ...]
    manifest_digest: str

def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def _approval_material(x: ControlledRuntimeIntegrationApproval):
    values = []
    for field in x.__dataclass_fields__:
        if field in ("qualification", "approval_digest"): continue
        value = getattr(x, field)
        if type(value) is AuthorityBoundary:
            value = tuple(getattr(value, name) for name in value.__dataclass_fields__)
        values.append(value)
    return tuple(values)

def _manifest_material(x: ControlledRuntimeIntegrationManifest):
    return (x.manifest_version, x.registry_version, x.integration_scope,
        x.approved_skill_ids, tuple(a.approval_digest for a in x.approvals),
        x.approval_status, x.diagnostics)

def get_controlled_integration_skill(skill_id: object):
    if type(skill_id) is not str or skill_id not in SUPPORTED_SKILL_IDS: return None
    return next((x for x in get_business_skill_registry() if x.skill_id == skill_id), None)

def create_controlled_integration_approval(qualification: Any):
    if not verify_controlled_runtime_integration_qualification(qualification):
        raise ValueError("canonical V5.15.21 qualification is required")
    skill = get_controlled_integration_skill(qualification.skill_id)
    if skill is None or skill.active_status != LIMITED_ACTIVE or BUSINESS_SKILL_REGISTRY_VERSION != "5.15.13":
        raise ValueError("canonical registry/lifecycle mismatch")
    q = qualification
    values = dict(manifest_version=CONTROLLED_RUNTIME_INTEGRATION_MANIFEST_VERSION,
        registry_version=BUSINESS_SKILL_REGISTRY_VERSION, skill_id=q.skill_id,
        lifecycle_status=LIMITED_ACTIVE, integration_scope=CONTROLLED_COST_RESPONSE_RUNTIME_INTEGRATION,
        approval_status=CONTROLLED_INTEGRATION_APPROVED, approval_reason=APPROVAL_REASON,
        qualification_version=q.qualification_version, qualification_digest=q.qualification_digest,
        delivery_qualification_version=q.delivery_qualification_version,
        delivery_qualification_id=q.delivery_qualification_id,
        delivery_qualification_digest=q.delivery_qualification_digest,
        runtime_bridge_version=q.runtime_bridge_version, feature_gate_name=q.feature_gate_name,
        feature_gate_passed=q.feature_gate_passed, handoff_digest=q.handoff_digest,
        result_digest=q.result_digest, request_id=q.request_id, payload_digest=q.payload_digest,
        provenance_verified=q.provenance_verified,
        authority_boundary_verified=q.authority_boundary_verified,
        authority_boundary=AuthorityBoundary(), diagnostics=DIAGNOSTICS, qualification=q)
    draft = ControlledRuntimeIntegrationApproval(**values, approval_digest="")
    return ControlledRuntimeIntegrationApproval(**values, approval_digest=_digest(_approval_material(draft)))

def verify_controlled_integration_approval(value: Any) -> bool:
    try:
        if type(value) is not ControlledRuntimeIntegrationApproval or not _HEX.fullmatch(value.approval_digest): return False
        expected = create_controlled_integration_approval(value.qualification)
        return value == expected and value.approval_digest == _digest(_approval_material(value))
    except (AttributeError, TypeError, ValueError): return False

def create_controlled_integration_manifest(qualifications: Iterable[Any]):
    source = tuple(qualifications)
    ids = tuple(getattr(x, "skill_id", None) for x in source)
    if ids != SUPPORTED_SKILL_IDS or len(set(ids)) != len(ids):
        raise ValueError("a full canonically ordered qualification batch is required")
    approvals = tuple(create_controlled_integration_approval(x) for x in source)
    values = dict(manifest_version=CONTROLLED_RUNTIME_INTEGRATION_MANIFEST_VERSION,
        registry_version=BUSINESS_SKILL_REGISTRY_VERSION,
        integration_scope=CONTROLLED_COST_RESPONSE_RUNTIME_INTEGRATION,
        approved_skill_ids=SUPPORTED_SKILL_IDS, approvals=approvals,
        approval_status=CONTROLLED_INTEGRATION_APPROVED, diagnostics=DIAGNOSTICS)
    draft = ControlledRuntimeIntegrationManifest(**values, manifest_digest="")
    return ControlledRuntimeIntegrationManifest(**values, manifest_digest=_digest(_manifest_material(draft)))

def verify_controlled_integration_manifest(value: Any) -> bool:
    try:
        if type(value) is not ControlledRuntimeIntegrationManifest or not _HEX.fullmatch(value.manifest_digest): return False
        if value.approved_skill_ids != SUPPORTED_SKILL_IDS or tuple(a.skill_id for a in value.approvals) != SUPPORTED_SKILL_IDS: return False
        if not all(verify_controlled_integration_approval(a) for a in value.approvals): return False
        expected = create_controlled_integration_manifest(tuple(a.qualification for a in value.approvals))
        return value == expected and value.manifest_digest == _digest(_manifest_material(value))
    except (AttributeError, TypeError, ValueError): return False
