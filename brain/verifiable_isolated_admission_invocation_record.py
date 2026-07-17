"""V5.15.24.7.4.13.7 verifiable isolated admission invocation records.

The builder invokes only the historical admission gateway.  A valid historical
admission decision is evidence of that isolated evaluation, not production or
controlled-runtime authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any, Mapping

import brain.business_skill_cost_runtime_integration_admission_gateway as _gateway
from brain.business_skill_cost_runtime_integration_admission_gateway import (
    CONTROLLED_RUNTIME_INTEGRATION_ADMISSION_GATEWAY_VERSION,
    ControlledRuntimeIntegrationAdmissionDecision,
    ControlledRuntimeIntegrationAdmissionRequest,
    verify_controlled_runtime_integration_admission_decision,
)
from brain.versioned_controlled_runtime_admission_request_binding import (
    VersionedControlledRuntimeAdmissionRequestBatch,
    VersionedControlledRuntimeAdmissionRequestBinding,
    verify_versioned_controlled_runtime_admission_request_binding,
    verify_versioned_controlled_runtime_admission_request_bindings,
)
from brain.versioned_cost_runtime_request_adapter import SUPPORTED_ADAPTER_SKILL_IDS

VERSION = "5.15.24.7.4.13.7"
SCOPE = "VERIFIABLE_ISOLATED_ADMISSION_INVOCATION_RECORD_FOUNDATION"
STAGE = "HISTORICAL_CONTROLLED_RUNTIME_INTEGRATION_ADMISSION_GATEWAY_INVOCATION"
GATEWAY_IDENTITY = (
    "brain.business_skill_cost_runtime_integration_admission_gateway."
    "decide_controlled_runtime_integration_admission"
)


@dataclass(frozen=True)
class IsolatedAdmissionInvocationAuthorityBoundary:
    production_admission: bool = False
    production_application: bool = False
    production_activation: bool = False
    mutation: bool = False
    persistence: bool = False
    production_dispatch: bool = False
    controlled_runtime_permission: bool = False
    delivery: bool = False
    routing: bool = False
    response_commit: bool = False
    deployment: bool = False
    rollback: bool = False
    external_tools: bool = False
    network: bool = False


@dataclass(frozen=True)
class IsolatedAdmissionInvocationInputBinding:
    source_binding: VersionedControlledRuntimeAdmissionRequestBinding
    source_binding_digest: str
    target_request: ControlledRuntimeIntegrationAdmissionRequest
    target_request_material_digest: str
    manifest_binding_digest: str
    manifest_digest: str
    bridge_record_digest: str
    qualification_binding_digest: str


@dataclass(frozen=True)
class IsolatedAdmissionInvocationRecord:
    version: str
    scope: str
    stage: str
    skill_id: str
    input_binding: IsolatedAdmissionInvocationInputBinding
    gateway_identity: str
    gateway_version: str
    decision: ControlledRuntimeIntegrationAdmissionDecision
    decision_status: str
    decision_reasons: tuple[str, ...]
    admitted: bool
    decision_digest: str
    invocation_outcome: str
    runtime_invoked: bool
    runtime_result: None
    production_admission: bool
    authority_boundary: IsolatedAdmissionInvocationAuthorityBoundary
    record_id: str = ""
    record_digest: str = ""


@dataclass(frozen=True)
class IsolatedAdmissionInvocationBatch:
    version: str
    scope: str
    stage: str
    skill_order: tuple[str, ...]
    records: tuple[IsolatedAdmissionInvocationRecord, ...]
    record_ids: tuple[str, ...]
    record_digests: tuple[str, ...]
    decision_digests: tuple[str, ...]
    admitted_count: int
    denied_count: int
    isolated_execution_invocations: int
    isolated_calculator_invocations: int
    isolated_bridge_invocations: int
    isolated_admission_invocations: int
    isolated_runtime_invocations: int
    production_admission_invocations: int
    production_runtime_invocations: int
    production_delivery_invocations: int
    production_commit_invocations: int
    topology_digest: str
    authority_boundary: IsolatedAdmissionInvocationAuthorityBoundary
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
    raise ValueError("unsupported invocation material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _record_material(value: IsolatedAdmissionInvocationRecord):
    return tuple(getattr(value, f.name) for f in fields(value)
        if f.name not in ("record_id", "record_digest"))


def _input(source: VersionedControlledRuntimeAdmissionRequestBinding):
    return IsolatedAdmissionInvocationInputBinding(source, source.binding_digest,
        source.target_request, source.target_request_material_digest,
        source.source_manifest_binding_digest, source.manifest_digest,
        source.source_bridge_record_digest, source.source_qualification_binding_digest)


def _create_record(source: Any, *, source_verified: bool = False):
    if (type(source) is not VersionedControlledRuntimeAdmissionRequestBinding or
            (not source_verified and
             not verify_versioned_controlled_runtime_admission_request_binding(source))):
        return None
    request = source.target_request
    decision = _gateway.decide_controlled_runtime_integration_admission(request)
    if not verify_controlled_runtime_integration_admission_decision(decision, request):
        return None
    status = "ADMITTED" if decision.admitted else "DENIED"
    draft = IsolatedAdmissionInvocationRecord(VERSION, SCOPE, STAGE, source.skill_id,
        _input(source), GATEWAY_IDENTITY,
        CONTROLLED_RUNTIME_INTEGRATION_ADMISSION_GATEWAY_VERSION, decision, status,
        decision.reasons, decision.admitted, decision.decision_digest,
        "DECISION_RETURNED", False, None, False,
        IsolatedAdmissionInvocationAuthorityBoundary())
    record_id = _digest("INVOCATION_RECORD_ID", (source.binding_digest,
        decision.decision_digest, GATEWAY_IDENTITY))
    with_id = replace(draft, record_id=record_id)
    return replace(with_id, record_digest=_digest("INVOCATION_RECORD", _record_material(with_id)))


def create_isolated_admission_invocation_record(source: Any):
    return _create_record(source)


def verify_isolated_admission_invocation_record(value: Any) -> bool:
    try:
        if type(value) is not IsolatedAdmissionInvocationRecord: return False
        source = value.input_binding.source_binding
        if value.input_binding != _input(source): return False
        if type(value.decision) is not ControlledRuntimeIntegrationAdmissionDecision: return False
        expected_status = "ADMITTED" if value.decision.admitted else "DENIED"
        expected_id = _digest("INVOCATION_RECORD_ID", (source.binding_digest,
            value.decision.decision_digest, GATEWAY_IDENTITY))
        expected = replace(value, version=VERSION, scope=SCOPE, stage=STAGE,
            skill_id=source.skill_id, gateway_identity=GATEWAY_IDENTITY,
            gateway_version=CONTROLLED_RUNTIME_INTEGRATION_ADMISSION_GATEWAY_VERSION,
            decision_status=expected_status, decision_reasons=value.decision.reasons,
            admitted=value.decision.admitted, decision_digest=value.decision.decision_digest,
            invocation_outcome="DECISION_RETURNED", runtime_invoked=False,
            runtime_result=None, production_admission=False,
            authority_boundary=IsolatedAdmissionInvocationAuthorityBoundary(),
            record_id=expected_id, record_digest="")
        expected = replace(expected, record_digest=_digest("INVOCATION_RECORD", _record_material(expected)))
        if value != expected: return False
        if not verify_versioned_controlled_runtime_admission_request_binding(source): return False
        return verify_controlled_runtime_integration_admission_decision(
            value.decision, source.target_request)
    except (AttributeError, TypeError, ValueError, KeyError, UnicodeEncodeError):
        return False


def _batch_material(value: IsolatedAdmissionInvocationBatch):
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != "batch_digest")


def create_isolated_admission_invocation_batch(source: Any):
    if (type(source) is not VersionedControlledRuntimeAdmissionRequestBatch or
            not verify_versioned_controlled_runtime_admission_request_bindings(source)):
        return None
    records = tuple(_create_record(x, source_verified=True) for x in source.bindings)
    if (any(x is None for x in records) or
            tuple(x.skill_id for x in records) != SUPPORTED_ADAPTER_SKILL_IDS):
        return None
    count = len(records)
    admitted = sum(x.admitted for x in records)
    record_ids = tuple(x.record_id for x in records)
    record_digests = tuple(x.record_digest for x in records)
    decision_digests = tuple(x.decision_digest for x in records)
    topology = _digest("INVOCATION_BATCH_TOPOLOGY", (source.source_manifest_binding_digest,
        record_ids, record_digests, decision_digests))
    draft = IsolatedAdmissionInvocationBatch(VERSION, SCOPE, STAGE,
        SUPPORTED_ADAPTER_SKILL_IDS, records, record_ids, record_digests,
        decision_digests, admitted, count - admitted, count, count, count, count, 0,
        0, 0, 0, 0, topology, IsolatedAdmissionInvocationAuthorityBoundary())
    return replace(draft, batch_digest=_digest("INVOCATION_BATCH", _batch_material(draft)))


def verify_isolated_admission_invocation_batch(value: Any) -> bool:
    try:
        if type(value) is not IsolatedAdmissionInvocationBatch: return False
        records = value.records
        if tuple(x.skill_id for x in records) != SUPPORTED_ADAPTER_SKILL_IDS: return False
        if len({x.record_id for x in records}) != len(records): return False
        count = len(records); admitted = sum(x.admitted for x in records)
        ids = tuple(x.record_id for x in records); digests = tuple(x.record_digest for x in records)
        decisions = tuple(x.decision_digest for x in records)
        manifest_binding = records[0].input_binding.manifest_binding_digest
        if any(x.input_binding.manifest_binding_digest != manifest_binding for x in records): return False
        topology = _digest("INVOCATION_BATCH_TOPOLOGY", (manifest_binding, ids, digests, decisions))
        expected = IsolatedAdmissionInvocationBatch(VERSION, SCOPE, STAGE,
            SUPPORTED_ADAPTER_SKILL_IDS, records, ids, digests, decisions,
            admitted, count - admitted, count, count, count, count, 0, 0, 0, 0, 0,
            topology, IsolatedAdmissionInvocationAuthorityBoundary())
        expected = replace(expected, batch_digest=_digest("INVOCATION_BATCH", _batch_material(expected)))
        if value != expected: return False
        return all(verify_isolated_admission_invocation_record(x) for x in records)
    except (AttributeError, TypeError, ValueError, KeyError, UnicodeEncodeError, IndexError):
        return False


__all__ = ("VERSION", "SCOPE", "STAGE", "GATEWAY_IDENTITY",
    "IsolatedAdmissionInvocationAuthorityBoundary",
    "IsolatedAdmissionInvocationInputBinding", "IsolatedAdmissionInvocationRecord",
    "IsolatedAdmissionInvocationBatch", "create_isolated_admission_invocation_record",
    "verify_isolated_admission_invocation_record",
    "create_isolated_admission_invocation_batch",
    "verify_isolated_admission_invocation_batch")
