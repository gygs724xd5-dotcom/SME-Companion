"""V5.15.21 controlled runtime-integration qualification evidence only."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_cost_response_delivery_qualification import (
    COST_DELIVERY_QUALIFICATION_VERSION, CostDeliveryQualificationResult,
    verify_cost_delivery_qualification_result_integrity,
)
from brain.business_skill_cost_response_runtime_bridge import (
    COST_RUNTIME_BRIDGE_VERSION, FEATURE_GATE_NAME, RUNTIME_HANDOFF_PREPARED,
    CostRuntimeBridgeResult, verify_cost_runtime_bridge_result_integrity,
    verify_cost_runtime_handoff_integrity,
)

QUALIFICATION_VERSION = "5.15.21"
REGISTRY_VERSION = "5.15.13"
SUPPORTED_SKILL_IDS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")
QUALIFIED_FOR_CONTROLLED_INTEGRATION = "QUALIFIED_FOR_CONTROLLED_INTEGRATION"
GATE_ORDER = ("SKILL_IDENTITY", "LIFECYCLE_REGISTRY", "DELIVERY_QUALIFICATION",
    "DELIVERY_PAYLOAD_BINDING", "RUNTIME_BRIDGE_VERSION", "FEATURE_GATE_IDENTITY",
    "RUNTIME_HANDOFF", "RUNTIME_RESULT", "PROVENANCE_BINDING",
    "SUBSTITUTION_RESISTANCE", "AUTHORITY_BOUNDARY", "QUALIFICATION_ISOLATION")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_FALSE_FLAGS = ("runtime_routed", "response_generated", "response_delivered",
    "response_committed", "persisted", "tools_invoked", "follow_up_generated",
    "business_reasoning_executed", "skill_executed", "calculated",
    "presentation_generated", "response_authorized")

@dataclass(frozen=True)
class ControlledRuntimeQualificationInput:
    skill_id: Any
    delivery_qualification: Any
    runtime_bridge_result: Any

@dataclass(frozen=True)
class QualificationGateResult:
    gate: str
    passed: bool
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class ControlledRuntimeIntegrationQualification:
    qualification_version: str
    registry_version: str
    qualified_skill_ids: tuple[str, ...]
    skill_id: str
    delivery_qualification_version: str
    delivery_qualification_id: str
    delivery_qualification_digest: str
    runtime_bridge_version: str
    feature_gate_name: str
    feature_gate_passed: bool
    handoff_digest: str
    result_digest: str
    request_id: str
    payload_digest: str
    provenance_verified: bool
    authority_boundary_verified: bool
    gate_results: tuple[QualificationGateResult, ...]
    qualified: bool
    reasons: tuple[str, ...]
    diagnostics: tuple[tuple[str, str], ...]
    delivery_qualification: Any
    runtime_bridge_result: Any
    qualification_digest: str

@dataclass(frozen=True)
class ControlledRuntimeIntegrationQualificationBatch:
    qualification_version: str
    results: tuple[ControlledRuntimeIntegrationQualification, ...]

def _digest(material):
    return hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()

def _gate(name, reasons):
    codes = tuple(dict.fromkeys(reasons))
    return QualificationGateResult(name, not codes, codes or ("PASSED",))

def _snapshot(value):
    return {
        "qualification_version": value.qualification_version,
        "registry_version": value.registry_version,
        "qualified_skill_ids": value.qualified_skill_ids, "skill_id": value.skill_id,
        "delivery_qualification_version": value.delivery_qualification_version,
        "delivery_qualification_id": value.delivery_qualification_id,
        "delivery_qualification_digest": value.delivery_qualification_digest,
        "runtime_bridge_version": value.runtime_bridge_version,
        "feature_gate_name": value.feature_gate_name,
        "feature_gate_passed": value.feature_gate_passed,
        "handoff_digest": value.handoff_digest, "result_digest": value.result_digest,
        "request_id": value.request_id, "payload_digest": value.payload_digest,
        "provenance_verified": value.provenance_verified,
        "authority_boundary_verified": value.authority_boundary_verified,
        "gate_results": tuple((g.gate, g.passed, g.reasons) for g in value.gate_results),
        "qualified": value.qualified, "reasons": value.reasons,
        "diagnostics": value.diagnostics,
    }

def _evaluate(item):
    typed = type(item) is ControlledRuntimeQualificationInput
    skill = item.skill_id if typed and type(item.skill_id) is str else ""
    delivery = item.delivery_qualification if typed else None
    bridge = item.runtime_bridge_result if typed else None
    binding = delivery.binding if type(delivery) is CostDeliveryQualificationResult else None
    handoff = bridge.handoff if type(bridge) is CostRuntimeBridgeResult else None
    canonical = {x.skill_id: x for x in get_business_skill_registry()}
    groups = []
    groups.append([] if skill in SUPPORTED_SKILL_IDS else ["UNSUPPORTED_OR_MALFORMED_SKILL_ID"])
    groups.append([] if BUSINESS_SKILL_REGISTRY_VERSION == REGISTRY_VERSION and
        skill in canonical and canonical[skill].active_status == LIMITED_ACTIVE else ["REGISTRY_OR_LIFECYCLE_MISMATCH"])
    delivery_ok = verify_cost_delivery_qualification_result_integrity(delivery)
    groups.append([] if delivery_ok and binding is not None and
        binding.qualification_version == COST_DELIVERY_QUALIFICATION_VERSION else ["INVALID_DELIVERY_QUALIFICATION"])
    groups.append([] if delivery_ok and binding is not None and binding.skill_id == skill else ["DELIVERY_PAYLOAD_BINDING_MISMATCH"])
    groups.append([] if type(bridge) is CostRuntimeBridgeResult and bridge.bridge_version == COST_RUNTIME_BRIDGE_VERSION else ["HISTORICAL_OR_INVALID_BRIDGE_VERSION"])
    groups.append([] if type(bridge) is CostRuntimeBridgeResult and bridge.feature_gate_name == FEATURE_GATE_NAME and bridge.feature_gate_passed is True and
        handoff is not None and handoff.feature_gate_name == FEATURE_GATE_NAME and handoff.feature_gate_passed is True else ["FEATURE_GATE_IDENTITY_OR_STATE_MISMATCH"])
    handoff_ok = verify_cost_runtime_handoff_integrity(handoff)
    groups.append([] if handoff_ok else ["INVALID_OR_MISSING_RUNTIME_HANDOFF"])
    result_ok = verify_cost_runtime_bridge_result_integrity(bridge)
    groups.append([] if result_ok and bridge.outcome == RUNTIME_HANDOFF_PREPARED else ["INVALID_RUNTIME_BRIDGE_RESULT"])
    provenance = bool(delivery_ok and result_ok and binding is not None and handoff is not None and
        (handoff.qualification_id, handoff.qualification_digest, handoff.skill_id,
         handoff.payload_digest, handoff.request_id) ==
        (binding.qualification_id, binding.qualification_digest, binding.skill_id,
         binding.payload_digest, binding.payload_request_id))
    groups.append([] if provenance else ["PROVENANCE_MISMATCH"])
    substitution = bool(provenance and handoff.adapter_request_id == binding.adapter_request_id and
        handoff.presentation_digest == binding.presentation_digest and handoff.draft_digest == binding.draft_digest)
    groups.append([] if substitution else ["REQUEST_SKILL_OR_PAYLOAD_SUBSTITUTION"])
    authority = bool(result_ok and handoff_ok and not any(getattr(bridge, x) for x in _FALSE_FLAGS)
        and not any(getattr(handoff, x) for x in _FALSE_FLAGS))
    groups.append([] if authority else ["AUTHORITY_ESCALATION"])
    groups.append([] if typed else ["CALLER_INPUT_MALFORMED"])
    gates = tuple(_gate(name, reasons) for name, reasons in zip(GATE_ORDER, groups))
    reasons = tuple(code for gate in gates for code in gate.reasons if code != "PASSED")
    qualified = not reasons
    reasons = (QUALIFIED_FOR_CONTROLLED_INTEGRATION,) if qualified else reasons
    values = dict(qualification_version=QUALIFICATION_VERSION, registry_version=REGISTRY_VERSION,
        qualified_skill_ids=SUPPORTED_SKILL_IDS, skill_id=skill,
        delivery_qualification_version=getattr(binding, "qualification_version", ""),
        delivery_qualification_id=getattr(binding, "qualification_id", ""),
        delivery_qualification_digest=getattr(binding, "qualification_digest", ""),
        runtime_bridge_version=getattr(bridge, "bridge_version", ""),
        feature_gate_name=getattr(bridge, "feature_gate_name", "") or "",
        feature_gate_passed=getattr(bridge, "feature_gate_passed", False) is True,
        handoff_digest=getattr(handoff, "handoff_digest", ""), result_digest=getattr(bridge, "result_digest", ""),
        request_id=getattr(handoff, "request_id", ""), payload_digest=getattr(handoff, "payload_digest", ""),
        provenance_verified=provenance, authority_boundary_verified=authority,
        gate_results=gates, qualified=qualified, reasons=reasons,
        diagnostics=(("semantics", "QUALIFICATION_EVIDENCE_ONLY"),
            ("integration_authority", "NONE"), ("feature_gate_mutated", "FALSE")),
        delivery_qualification=delivery, runtime_bridge_result=bridge)
    draft = ControlledRuntimeIntegrationQualification(**values, qualification_digest="")
    return ControlledRuntimeIntegrationQualification(**values, qualification_digest=_digest(_snapshot(draft)))

def qualify_controlled_runtime_integration(item: Any):
    return _evaluate(item)

def qualify_controlled_runtime_integrations(items: Iterable[Any]):
    try: source = tuple(items)
    except TypeError: source = (items,)
    ids = [x.skill_id for x in source if type(x) is ControlledRuntimeQualificationInput]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate skill IDs are forbidden")
    results = tuple(sorted((_evaluate(x) for x in source), key=lambda x: x.skill_id))
    return ControlledRuntimeIntegrationQualificationBatch(QUALIFICATION_VERSION, results)

def verify_controlled_runtime_integration_qualification(value: Any) -> bool:
    try:
        if type(value) is not ControlledRuntimeIntegrationQualification: return False
        if not _HEX.fullmatch(value.qualification_digest): return False
        if (value.qualification_version != QUALIFICATION_VERSION or
            value.registry_version != REGISTRY_VERSION or
            value.qualified_skill_ids != SUPPORTED_SKILL_IDS or
            value.runtime_bridge_version != COST_RUNTIME_BRIDGE_VERSION or
            value.delivery_qualification_version != COST_DELIVERY_QUALIFICATION_VERSION or
            value.feature_gate_name != FEATURE_GATE_NAME or value.feature_gate_passed is not True or
            not value.qualified or not value.provenance_verified or
            not value.authority_boundary_verified or
            any(not _HEX.fullmatch(x) for x in (value.delivery_qualification_digest,
                value.handoff_digest, value.result_digest, value.payload_digest))): return False
        expected = _evaluate(ControlledRuntimeQualificationInput(value.skill_id,
            value.delivery_qualification, value.runtime_bridge_result))
        return value == expected and value.qualification_digest == _digest(_snapshot(value))
    except (AttributeError, TypeError, ValueError, KeyError):
        return False
