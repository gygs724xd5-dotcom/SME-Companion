"""V5.15.24.7.4.13.5 bridge-record to historical-manifest binding.

This module is a pure, forward-only evidence binding.  It grants no admission,
runtime, delivery, transition, or production authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any, Mapping

from brain.business_skill_cost_runtime_integration_qualification import (
    ControlledRuntimeQualificationInput,
    qualify_controlled_runtime_integration,
    verify_controlled_runtime_integration_qualification,
)
from brain.business_skill_cost_runtime_integration_manifest import (
    create_controlled_integration_manifest,
    verify_controlled_integration_manifest,
)
from brain.business_skill_cost_response_runtime_bridge import FEATURE_GATE_NAME
from brain.verifiable_isolated_bridge_invocation_record import (
    IsolatedBridgeInvocationBatch,
    IsolatedBridgeInvocationRecord,
    verify_isolated_bridge_invocation_batch,
    verify_isolated_bridge_invocation_record,
)
from brain.versioned_cost_runtime_request_adapter import SUPPORTED_ADAPTER_SKILL_IDS

VERSION = "5.15.24.7.4.13.5"
SCOPE = "BRIDGE_RECORD_TO_HISTORICAL_RUNTIME_MANIFEST_BINDING_FOUNDATION"
STATUS = "QUALIFICATION_BOUND_FROM_BRIDGE_RECORD_NOT_ADMITTED"
MANIFEST_STATUS = "HISTORICAL_MANIFEST_BOUND_FROM_BRIDGE_RECORDS_NOT_ADMITTED"
TOPOLOGY = ("BRIDGE_INVOCATION_RECORD", "DELIVERY_QUALIFICATION", "BRIDGE_RESULT",
            "BRIDGE_HANDOFF_ANCESTRY", "CONTROLLED_RUNTIME_QUALIFICATION",
            "HISTORICAL_CONTROLLED_RUNTIME_MANIFEST")


@dataclass(frozen=True)
class BridgeRecordManifestBindingAuthorityBoundary:
    production_approval: bool = False
    application: bool = False
    activation: bool = False
    mutation: bool = False
    persistence: bool = False
    production_dispatch: bool = False
    admission: bool = False
    controlled_runtime: bool = False
    delivery: bool = False
    routing: bool = False
    commit: bool = False
    deployment: bool = False
    rollback: bool = False
    external_tools: bool = False
    network: bool = False


@dataclass(frozen=True)
class BridgeRecordQualificationBinding:
    version: str
    scope: str
    status: str
    skill_id: str
    bridge_record: IsolatedBridgeInvocationRecord
    source_request_id: str
    source_request_digest: str
    source_turn_digest: str
    source_reference_time_digest: str
    source_execution_record_digest: str
    source_bridge_request_binding_digest: str
    bridge_record_digest: str
    bridge_request: Any
    bridge_request_digest: str
    bridge_result: Any
    bridge_result_digest: str
    bridge_handoff: Any
    bridge_handoff_digest: str
    delivery_qualification: Any
    delivery_qualification_digest: str
    runtime_qualification: Any
    qualification_digest: str
    gate_identity: str
    gate_configured_state: bool
    gate_effective_state: bool
    gate_configuration_digest: str
    gate_evaluation_digest: str
    source_target_topology: tuple[str, ...]
    authority_boundary: BridgeRecordManifestBindingAuthorityBoundary
    binding_digest: str = ""


@dataclass(frozen=True)
class BridgeRecordRuntimeManifestBinding:
    version: str
    scope: str
    status: str
    skill_order: tuple[str, ...]
    source_batch: IsolatedBridgeInvocationBatch
    qualification_bindings: tuple[BridgeRecordQualificationBinding, ...]
    historical_qualifications: tuple[Any, ...]
    historical_manifest: Any
    manifest_version: str
    manifest_status: str
    manifest_digest: str
    manifest_request_digest_bindings: tuple[tuple[str, str], ...]
    bridge_record_digests: tuple[str, ...]
    qualification_binding_digests: tuple[str, ...]
    gate_identity_bindings: tuple[tuple[str, bool, bool, str, str], ...]
    topology_digest: str
    isolated_execution_invocations: int
    isolated_calculator_invocations: int
    isolated_bridge_invocations: int
    isolated_admission_invocations: int
    isolated_runtime_invocations: int
    production_execution_invocations: int = 0
    production_calculator_invocations: int = 0
    production_bridge_invocations: int = 0
    production_admission_invocations: int = 0
    production_runtime_invocations: int = 0
    production_delivery_invocations: int = 0
    production_response_commits: int = 0
    admission_invoked: bool = False
    admission_decision: None = None
    controlled_runtime_invoked: bool = False
    runtime_result: None = None
    production_application_permitted: bool = False
    activation_permitted: bool = False
    response_committed: bool = False
    authority_boundary: BridgeRecordManifestBindingAuthorityBoundary = BridgeRecordManifestBindingAuthorityBoundary()
    binding_digest: str = ""


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


def _without(value: Any, *names: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name not in names)


def _qualification_binding_material(value: BridgeRecordQualificationBinding) -> tuple[Any, ...]:
    return (value.version, value.scope, value.status, value.skill_id, value.source_request_id,
        value.source_request_digest, value.source_turn_digest, value.source_reference_time_digest,
        value.source_execution_record_digest, value.source_bridge_request_binding_digest,
        value.bridge_record_digest, value.bridge_request_digest, value.bridge_result_digest,
        value.bridge_handoff_digest, value.delivery_qualification_digest,
        value.qualification_digest, value.gate_identity, value.gate_configured_state,
        value.gate_effective_state, value.gate_configuration_digest,
        value.gate_evaluation_digest, value.source_target_topology, value.authority_boundary)


def _manifest_binding_material(value: BridgeRecordRuntimeManifestBinding) -> tuple[Any, ...]:
    return (value.version, value.scope, value.status, value.skill_order,
        value.source_batch.batch_digest, value.bridge_record_digests,
        value.qualification_binding_digests,
        tuple(x.qualification_digest for x in value.historical_qualifications),
        value.manifest_version, value.manifest_status, value.manifest_digest,
        value.manifest_request_digest_bindings, value.gate_identity_bindings,
        value.topology_digest, value.isolated_execution_invocations,
        value.isolated_calculator_invocations, value.isolated_bridge_invocations,
        value.isolated_admission_invocations, value.isolated_runtime_invocations,
        tuple(getattr(value, f.name) for f in fields(value) if f.name.startswith("production_")),
        value.admission_invoked, value.admission_decision, value.controlled_runtime_invoked,
        value.runtime_result, value.production_application_permitted,
        value.activation_permitted, value.response_committed, value.authority_boundary)


def _qualification_binding(record: IsolatedBridgeInvocationRecord):
    if not verify_isolated_bridge_invocation_record(record): return None
    source = record.source_binding
    qualification = qualify_controlled_runtime_integration(ControlledRuntimeQualificationInput(
        record.skill_id, source.delivery_qualification, record.bridge_result))
    if not verify_controlled_runtime_integration_qualification(qualification): return None
    # The historical builder consumes the result; retain and prove its exact handoff ancestry here.
    if record.bridge_handoff is not record.bridge_result.handoff: return None
    draft = BridgeRecordQualificationBinding(VERSION, SCOPE, STATUS, record.skill_id, record,
        source.source_request_id, source.source_request_digest, source.source_turn_digest,
        source.source_reference_time_digest, source.record_digest, source.binding_digest,
        record.record_digest, record.bridge_request, record.input_binding.request_digest,
        record.bridge_result, record.bridge_result_digest, record.bridge_handoff,
        record.bridge_handoff_digest, source.delivery_qualification,
        source.delivery_qualification.binding.qualification_digest, qualification,
        qualification.qualification_digest, record.gate_identity_binding,
        record.input_binding.gate_configured_state, record.input_binding.gate_effective_state,
        record.input_binding.gate_configuration_digest, record.input_binding.gate_evaluation_digest,
        TOPOLOGY, BridgeRecordManifestBindingAuthorityBoundary())
    return replace(draft, binding_digest=_digest("QUALIFICATION_BINDING", _qualification_binding_material(draft)))


def verify_bridge_record_qualification_binding(value: Any) -> bool:
    try:
        if type(value) is not BridgeRecordQualificationBinding: return False
        if value.binding_digest != _digest("QUALIFICATION_BINDING", _qualification_binding_material(value)): return False
        expected = _qualification_binding(value.bridge_record)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, KeyError, UnicodeEncodeError):
        return False


def create_bridge_record_runtime_manifest_binding(source: Any):
    if type(source) is not IsolatedBridgeInvocationBatch or not verify_isolated_bridge_invocation_batch(source): return None
    bindings = tuple(_qualification_binding(x) for x in source.records)
    if any(x is None for x in bindings) or tuple(x.skill_id for x in bindings) != SUPPORTED_ADAPTER_SKILL_IDS: return None
    qualifications = tuple(x.runtime_qualification for x in bindings)
    manifest = create_controlled_integration_manifest(qualifications)
    if not verify_controlled_integration_manifest(manifest): return None
    record_digests = tuple(x.bridge_record_digest for x in bindings)
    binding_digests = tuple(x.binding_digest for x in bindings)
    gates = tuple((x.gate_identity, x.gate_configured_state, x.gate_effective_state,
                   x.gate_configuration_digest, x.gate_evaluation_digest) for x in bindings)
    topology_digest = _digest("TOPOLOGY", (TOPOLOGY, source.batch_digest, record_digests,
        binding_digests, tuple(x.qualification_digest for x in bindings), manifest.manifest_digest))
    draft = BridgeRecordRuntimeManifestBinding(VERSION, SCOPE, MANIFEST_STATUS,
        SUPPORTED_ADAPTER_SKILL_IDS, source, bindings, qualifications, manifest,
        manifest.manifest_version, manifest.approval_status, manifest.manifest_digest,
        manifest.request_digest_bindings, record_digests, binding_digests, gates,
        topology_digest, source.isolated_execution_invocations,
        source.isolated_calculator_invocations, source.isolated_bridge_invocations,
        source.isolated_admission_invocations, source.isolated_runtime_invocations)
    return replace(draft, binding_digest=_digest("MANIFEST_BINDING", _manifest_binding_material(draft)))


def verify_bridge_record_runtime_manifest_binding(value: Any) -> bool:
    try:
        if type(value) is not BridgeRecordRuntimeManifestBinding: return False
        if value.binding_digest != _digest("MANIFEST_BINDING", _manifest_binding_material(value)): return False
        expected = create_bridge_record_runtime_manifest_binding(value.source_batch)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, KeyError, UnicodeEncodeError):
        return False


__all__ = ("VERSION", "SCOPE", "STATUS", "MANIFEST_STATUS", "TOPOLOGY",
    "BridgeRecordManifestBindingAuthorityBoundary", "BridgeRecordQualificationBinding",
    "BridgeRecordRuntimeManifestBinding", "create_bridge_record_runtime_manifest_binding",
    "verify_bridge_record_qualification_binding", "verify_bridge_record_runtime_manifest_binding")
