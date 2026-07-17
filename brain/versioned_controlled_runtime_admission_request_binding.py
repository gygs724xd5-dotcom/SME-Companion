"""V5.15.24.7.4.13.6 deterministic admission-request binding foundation.

This pure module constructs historical request values.  It never evaluates an
admission request and grants no admission, runtime, transition, or production
authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any, Mapping

from brain.bridge_record_runtime_manifest_binding import (
    BridgeRecordQualificationBinding, BridgeRecordRuntimeManifestBinding,
    verify_bridge_record_qualification_binding,
    verify_bridge_record_runtime_manifest_binding,
)
from brain.business_skill_cost_runtime_integration_admission_gateway import (
    ControlledRuntimeIntegrationAdmissionRequest,
)
from brain.business_skill_cost_runtime_integration_manifest import (
    verify_controlled_integration_manifest,
)
from brain.versioned_cost_runtime_request_adapter import SUPPORTED_ADAPTER_SKILL_IDS

VERSION = "5.15.24.7.4.13.6"
SCOPE = "VERSIONED_CONTROLLED_RUNTIME_ADMISSION_REQUEST_BINDING_FOUNDATION"
STATUS = "ADMISSION_REQUEST_BOUND_NOT_INVOKED"
TOPOLOGY = ("BRIDGE_RECORD_RUNTIME_MANIFEST_BINDING", "HISTORICAL_MANIFEST",
    "PER_SKILL_QUALIFICATION_BINDING", "HISTORICAL_ADMISSION_REQUEST")


@dataclass(frozen=True)
class ControlledRuntimeAdmissionRequestBindingAuthorityBoundary:
    production_approval: bool = False
    transition_application: bool = False
    activation: bool = False
    mutation: bool = False
    persistence: bool = False
    production_dispatch: bool = False
    admission: bool = False
    runtime: bool = False
    delivery: bool = False
    routing: bool = False
    commit: bool = False
    deployment: bool = False
    rollback: bool = False
    external_tools: bool = False
    network: bool = False


@dataclass(frozen=True)
class VersionedControlledRuntimeAdmissionRequestBinding:
    version: str
    scope: str
    status: str
    skill_id: str
    source_manifest_binding: BridgeRecordRuntimeManifestBinding
    source_manifest_binding_digest: str
    historical_manifest: Any
    manifest_digest: str
    source_qualification_binding: BridgeRecordQualificationBinding
    source_qualification_binding_digest: str
    source_bridge_record: Any
    source_bridge_record_digest: str
    source_bridge_request_digest: str
    source_bridge_result_digest: str
    source_bridge_handoff_digest: str
    source_request_id: str
    source_request_digest: str
    source_execution_record_digest: str
    source_turn_digest: str
    source_reference_time_digest: str
    gate_identity: str
    gate_configuration_digest: str
    gate_evaluation_digest: str
    target_request: ControlledRuntimeIntegrationAdmissionRequest
    target_request_material_digest: str
    ancestry_topology: tuple[str, ...]
    authority_boundary: ControlledRuntimeAdmissionRequestBindingAuthorityBoundary
    binding_digest: str = ""


@dataclass(frozen=True)
class VersionedControlledRuntimeAdmissionRequestBatch:
    version: str
    scope: str
    status: str
    skill_order: tuple[str, ...]
    bindings: tuple[VersionedControlledRuntimeAdmissionRequestBinding, ...]
    source_manifest_binding: BridgeRecordRuntimeManifestBinding
    source_manifest_binding_digest: str
    historical_manifest: Any
    manifest_digest: str
    topology_digest: str
    isolated_execution_invocations: int
    isolated_calculator_invocations: int
    isolated_bridge_invocations: int
    isolated_admission_invocations: int
    isolated_runtime_invocations: int
    production_invocations: int = 0
    admission_invoked: bool = False
    admission_decisions: tuple[Any, ...] = ()
    controlled_runtime_invoked: bool = False
    runtime_results: tuple[Any, ...] = ()
    production_application_permitted: bool = False
    activation_permitted: bool = False
    response_committed: bool = False
    authority_boundary: ControlledRuntimeAdmissionRequestBindingAuthorityBoundary = ControlledRuntimeAdmissionRequestBindingAuthorityBoundary()
    batch_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal: return {"$decimal": str(value)}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[str(k), _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported binding material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _binding_material(x: VersionedControlledRuntimeAdmissionRequestBinding):
    return tuple(getattr(x, f.name) for f in fields(x)
        if f.name not in ("binding_digest", "source_manifest_binding", "historical_manifest",
                          "source_qualification_binding", "source_bridge_record", "target_request"))


def _make_binding(source: BridgeRecordRuntimeManifestBinding,
                  qualification: BridgeRecordQualificationBinding, *, verified: bool = False):
    if not verified and not verify_bridge_record_runtime_manifest_binding(source): return None
    if not verified and not verify_bridge_record_qualification_binding(qualification): return None
    matches = tuple(x for x in source.qualification_bindings if x is qualification)
    if len(matches) != 1: return None
    skill = qualification.skill_id
    if skill not in SUPPORTED_ADAPTER_SKILL_IDS: return None
    manifest = source.historical_manifest
    if not verify_controlled_integration_manifest(manifest): return None
    if tuple(x.skill_id for x in manifest.approvals) != SUPPORTED_ADAPTER_SKILL_IDS: return None
    if len(tuple(x for x in manifest.approvals if x.skill_id == skill)) != 1: return None
    request = ControlledRuntimeIntegrationAdmissionRequest(skill, manifest)
    request_digest = _digest("TARGET_REQUEST_MATERIAL", (request.skill_id, request.manifest.manifest_digest))
    draft = VersionedControlledRuntimeAdmissionRequestBinding(VERSION, SCOPE, STATUS, skill,
        source, source.binding_digest, manifest, source.manifest_digest, qualification,
        qualification.binding_digest, qualification.bridge_record,
        qualification.bridge_record_digest, qualification.bridge_request_digest,
        qualification.bridge_result_digest, qualification.bridge_handoff_digest,
        qualification.source_request_id, qualification.source_request_digest,
        qualification.source_execution_record_digest, qualification.source_turn_digest,
        qualification.source_reference_time_digest, qualification.gate_identity,
        qualification.gate_configuration_digest, qualification.gate_evaluation_digest,
        request, request_digest, TOPOLOGY,
        ControlledRuntimeAdmissionRequestBindingAuthorityBoundary())
    return replace(draft, binding_digest=_digest("REQUEST_BINDING", _binding_material(draft)))


def create_versioned_controlled_runtime_admission_request_binding(source: Any, qualification: Any):
    if type(source) is not BridgeRecordRuntimeManifestBinding: return None
    if type(qualification) is not BridgeRecordQualificationBinding: return None
    return _make_binding(source, qualification)


def verify_versioned_controlled_runtime_admission_request_binding(value: Any) -> bool:
    try:
        if type(value) is not VersionedControlledRuntimeAdmissionRequestBinding: return False
        if value.binding_digest != _digest("REQUEST_BINDING", _binding_material(value)): return False
        expected = _make_binding(value.source_manifest_binding, value.source_qualification_binding)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, KeyError, UnicodeEncodeError):
        return False


def _batch_material(x: VersionedControlledRuntimeAdmissionRequestBatch):
    return (x.version, x.scope, x.status, x.skill_order,
        tuple(b.binding_digest for b in x.bindings), x.source_manifest_binding_digest,
        x.manifest_digest, x.topology_digest, x.isolated_execution_invocations,
        x.isolated_calculator_invocations, x.isolated_bridge_invocations,
        x.isolated_admission_invocations, x.isolated_runtime_invocations,
        x.production_invocations, x.admission_invoked, x.admission_decisions,
        x.controlled_runtime_invoked, x.runtime_results,
        x.production_application_permitted, x.activation_permitted,
        x.response_committed, x.authority_boundary)


def create_versioned_controlled_runtime_admission_request_bindings(source: Any):
    if type(source) is not BridgeRecordRuntimeManifestBinding or not verify_bridge_record_runtime_manifest_binding(source): return None
    bindings = tuple(_make_binding(source, q, verified=True) for q in source.qualification_bindings)
    if any(x is None for x in bindings) or tuple(x.skill_id for x in bindings) != SUPPORTED_ADAPTER_SKILL_IDS: return None
    topology = _digest("BATCH_TOPOLOGY", (TOPOLOGY, source.binding_digest,
        tuple(x.binding_digest for x in bindings)))
    draft = VersionedControlledRuntimeAdmissionRequestBatch(VERSION, SCOPE, STATUS,
        SUPPORTED_ADAPTER_SKILL_IDS, bindings, source, source.binding_digest,
        source.historical_manifest, source.manifest_digest, topology,
        source.isolated_execution_invocations, source.isolated_calculator_invocations,
        source.isolated_bridge_invocations, source.isolated_admission_invocations,
        source.isolated_runtime_invocations)
    return replace(draft, batch_digest=_digest("REQUEST_BATCH", _batch_material(draft)))


def verify_versioned_controlled_runtime_admission_request_bindings(value: Any) -> bool:
    try:
        if type(value) is not VersionedControlledRuntimeAdmissionRequestBatch: return False
        if value.batch_digest != _digest("REQUEST_BATCH", _batch_material(value)): return False
        expected = create_versioned_controlled_runtime_admission_request_bindings(value.source_manifest_binding)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, KeyError, UnicodeEncodeError):
        return False


__all__ = ("VERSION", "SCOPE", "STATUS", "TOPOLOGY",
    "ControlledRuntimeAdmissionRequestBindingAuthorityBoundary",
    "VersionedControlledRuntimeAdmissionRequestBinding",
    "VersionedControlledRuntimeAdmissionRequestBatch",
    "create_versioned_controlled_runtime_admission_request_binding",
    "verify_versioned_controlled_runtime_admission_request_binding",
    "create_versioned_controlled_runtime_admission_request_bindings",
    "verify_versioned_controlled_runtime_admission_request_bindings")
