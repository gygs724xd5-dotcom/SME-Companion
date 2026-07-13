"""V5.15.23 isolated admission decision for controlled cost integration."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION
from brain.business_skill_cost_response_runtime_bridge import (
    COST_RUNTIME_BRIDGE_VERSION, FEATURE_GATE_NAME,
    verify_cost_runtime_bridge_result_integrity, verify_cost_runtime_handoff_integrity,
)
from brain.business_skill_cost_runtime_integration_qualification import (
    QUALIFICATION_VERSION, SUPPORTED_SKILL_IDS,
    verify_controlled_runtime_integration_qualification,
)
from brain.business_skill_cost_runtime_integration_manifest import (
    AuthorityBoundary, CONTROLLED_COST_RESPONSE_RUNTIME_INTEGRATION,
    CONTROLLED_INTEGRATION_APPROVED, CONTROLLED_RUNTIME_INTEGRATION_MANIFEST_VERSION,
    get_controlled_integration_skill, verify_controlled_integration_approval,
    verify_controlled_integration_manifest,
)

CONTROLLED_RUNTIME_INTEGRATION_ADMISSION_GATEWAY_VERSION = "5.15.23"
ADMISSION_GATE_ORDER = ("REQUEST_IDENTITY", "SKILL_LIFECYCLE", "MANIFEST_INTEGRITY",
    "APPROVAL_MEMBERSHIP", "QUALIFICATION_INTEGRITY", "RUNTIME_BRIDGE_INTEGRITY",
    "REQUEST_INTEGRITY", "FEATURE_GATE_INTEGRITY", "DELIVERY_BINDING",
    "PROVENANCE_BINDING", "SUBSTITUTION_RESISTANCE", "AUTHORITY_BOUNDARY",
    "INTEGRATION_SCOPE", "ADMISSION_ISOLATION")
ADMISSION_GRANTED = "CONTROLLED_INTEGRATION_ADMISSION_GRANTED"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_DENIALS = ("UNSUPPORTED_OR_MALFORMED_SKILL_ID", "REGISTRY_OR_LIFECYCLE_MISMATCH",
    "INVALID_OR_NONCANONICAL_MANIFEST", "APPROVAL_NOT_MEMBER_OF_VERIFIED_MANIFEST",
    "INVALID_OR_UNQUALIFIED_QUALIFICATION", "INVALID_RUNTIME_BRIDGE_CHAIN",
    "REQUEST_INTEGRITY_MISMATCH", "FEATURE_GATE_IDENTITY_OR_STATE_MISMATCH",
    "DELIVERY_BINDING_MISMATCH", "PROVENANCE_BINDING_MISMATCH",
    "ARTIFACT_SUBSTITUTION_DETECTED", "AUTHORITY_ESCALATION",
    "INTEGRATION_SCOPE_MISMATCH", "ADMISSION_ISOLATION_VIOLATION")

@dataclass(frozen=True)
class ControlledRuntimeIntegrationAdmissionRequest:
    skill_id: Any
    manifest: Any

@dataclass(frozen=True)
class AdmissionGateResult:
    gate: str
    passed: bool
    reason: str

@dataclass(frozen=True)
class ControlledRuntimeIntegrationAdmissionDecision:
    gateway_version: str; registry_version: str; skill_id: str
    manifest_version: str; manifest_digest: str; approval_digest: str
    qualification_version: str; qualification_digest: str; integration_scope: str
    bridge_version: str; feature_gate_name: str; feature_gate_state: bool
    request_id: str; request_digest: str; payload_digest: str
    delivery_qualification_digest: str; handoff_digest: str; result_digest: str
    provenance_verified: bool; gate_results: tuple[AdmissionGateResult, ...]
    admitted: bool; reasons: tuple[str, ...]
    primary_denial_code: str | None; primary_denial_reason: str | None
    authority_boundary: AuthorityBoundary; executable_output: None
    decision_digest: str

def _digest(value: Any) -> str:
    try:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError, UnicodeEncodeError):
        return ""

def _material(x: ControlledRuntimeIntegrationAdmissionDecision):
    return tuple((f, tuple((g.gate,g.passed,g.reason) for g in x.gate_results)
        if f == "gate_results" else tuple(getattr(x.authority_boundary,n)
        for n in x.authority_boundary.__dataclass_fields__) if f == "authority_boundary"
        else getattr(x,f)) for f in x.__dataclass_fields__ if f != "decision_digest")

def _evaluate(request: Any) -> ControlledRuntimeIntegrationAdmissionDecision:
    typed = type(request) is ControlledRuntimeIntegrationAdmissionRequest
    skill_id = request.skill_id if typed and type(request.skill_id) is str else ""
    manifest = request.manifest if typed else None
    manifest_ok = verify_controlled_integration_manifest(manifest)
    approvals = manifest.approvals if manifest_ok else ()
    matches = tuple(a for a in approvals if a.skill_id == skill_id)
    approval = matches[0] if len(matches) == 1 else None
    qualification = approval.qualification if approval is not None else None
    bridge = qualification.runtime_bridge_result if qualification is not None else None
    handoff = bridge.handoff if bridge is not None else None
    delivery = qualification.delivery_qualification if qualification is not None else None
    binding = delivery.binding if delivery is not None else None
    skill = get_controlled_integration_skill(skill_id)
    approval_ok = approval is not None and verify_controlled_integration_approval(approval)
    qualification_ok = approval_ok and verify_controlled_runtime_integration_qualification(qualification)
    bridge_ok = qualification_ok and verify_cost_runtime_bridge_result_integrity(bridge) and verify_cost_runtime_handoff_integrity(handoff)
    request_ok = bool(bridge_ok and _HEX.fullmatch(bridge.request_digest) and bridge.canonical_request is not None
        and bridge.request_digest == handoff.request_digest == qualification.request_digest == approval.request_digest
        and (skill_id, bridge.request_digest) in manifest.request_digest_bindings
        and bridge.request_digest not in (handoff.request_id, handoff.payload_digest))
    delivery_ok = bool(request_ok and binding is not None and
        (binding.qualification_digest,binding.payload_digest,binding.payload_request_id,binding.skill_id) ==
        (qualification.delivery_qualification_digest,handoff.payload_digest,handoff.request_id,skill_id))
    provenance_ok = bool(delivery_ok and qualification.provenance_verified and approval.provenance_verified)
    substitution_ok = bool(provenance_ok and
        (approval.skill_id,approval.request_id,approval.payload_digest,approval.handoff_digest,approval.result_digest) ==
        (skill_id,handoff.request_id,handoff.payload_digest,handoff.handoff_digest,bridge.result_digest))
    authority_ok = bool(substitution_ok and approval.authority_boundary == AuthorityBoundary()
        and qualification.authority_boundary_verified)
    checks = (skill_id in SUPPORTED_SKILL_IDS,
        skill is not None and skill.active_status == LIMITED_ACTIVE and BUSINESS_SKILL_REGISTRY_VERSION == "5.15.13",
        manifest_ok, approval_ok, qualification_ok and qualification.qualified, bridge_ok,
        request_ok, bool(request_ok and bridge.feature_gate_name == FEATURE_GATE_NAME
            and bridge.feature_gate_passed is True and handoff.feature_gate_name == FEATURE_GATE_NAME
            and handoff.feature_gate_passed is True), delivery_ok, provenance_ok,
        substitution_ok, authority_ok,
        bool(authority_ok and manifest.integration_scope == approval.integration_scope == CONTROLLED_COST_RESPONSE_RUNTIME_INTEGRATION),
        typed)
    gates=tuple(AdmissionGateResult(g,ok,"PASSED" if ok else code)
        for g,ok,code in zip(ADMISSION_GATE_ORDER,checks,_DENIALS))
    failed=next((g for g in gates if not g.passed),None)
    admitted=failed is None
    reasons=(ADMISSION_GRANTED,) if admitted else tuple(g.reason for g in gates if not g.passed)
    values=dict(gateway_version=CONTROLLED_RUNTIME_INTEGRATION_ADMISSION_GATEWAY_VERSION,
        registry_version=getattr(manifest,"registry_version","") if manifest_ok else "",
        skill_id=skill_id, manifest_version=getattr(manifest,"manifest_version","") if manifest_ok else "",
        manifest_digest=getattr(manifest,"manifest_digest","") if manifest_ok else "",
        approval_digest=getattr(approval,"approval_digest","") if approval_ok else "",
        qualification_version=getattr(qualification,"qualification_version","") if qualification_ok else "",
        qualification_digest=getattr(qualification,"qualification_digest","") if qualification_ok else "",
        integration_scope=getattr(manifest,"integration_scope","") if manifest_ok else "",
        bridge_version=getattr(bridge,"bridge_version","") if bridge_ok else "",
        feature_gate_name=getattr(bridge,"feature_gate_name","") if bridge_ok else "",
        feature_gate_state=getattr(bridge,"feature_gate_passed",False) is True if bridge_ok else False,
        request_id=getattr(handoff,"request_id","") if bridge_ok else "",
        request_digest=getattr(bridge,"request_digest","") if request_ok else "",
        payload_digest=getattr(handoff,"payload_digest","") if bridge_ok else "",
        delivery_qualification_digest=getattr(qualification,"delivery_qualification_digest","") if qualification_ok else "",
        handoff_digest=getattr(handoff,"handoff_digest","") if bridge_ok else "",
        result_digest=getattr(bridge,"result_digest","") if bridge_ok else "",
        provenance_verified=provenance_ok,gate_results=gates,admitted=admitted,reasons=reasons,
        primary_denial_code=None if admitted else failed.reason,
        primary_denial_reason=None if admitted else failed.reason,
        authority_boundary=AuthorityBoundary(),executable_output=None)
    draft=ControlledRuntimeIntegrationAdmissionDecision(**values,decision_digest="")
    return ControlledRuntimeIntegrationAdmissionDecision(**values,decision_digest=_digest(_material(draft)))

def decide_controlled_runtime_integration_admission(request: Any):
    return _evaluate(request)

def verify_controlled_runtime_integration_admission_decision(decision: Any, request: Any) -> bool:
    try:
        return (type(decision) is ControlledRuntimeIntegrationAdmissionDecision
            and _HEX.fullmatch(decision.decision_digest) is not None
            and decision == _evaluate(request)
            and decision.decision_digest == _digest(_material(decision)))
    except (AttributeError, TypeError, ValueError, KeyError):
        return False
