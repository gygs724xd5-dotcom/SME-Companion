"""V5.15.24.7.4.13.3 pure execution-result to bridge-request binding.

This module only constructs and verifies immutable historical artifacts.  It
does not call the runtime bridge or grant delivery, application, or activation
authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any, Mapping

from brain.business_skill_cost_result_presenter import (
    INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION, SUPPORTED_LOCALE,
    CostPresentationRequest, present_cost_result,
)
from brain.business_skill_cost_response_authorization import (
    AUTHORIZATION_POLICY_VERSION, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE,
    CostResponseAuthorizationRequest, authorize_cost_response,
)
from brain.business_skill_cost_response_adapter import (
    PREPARED_ONLY, CostResponseAdapterRequest, adapt_authorized_cost_response,
)
from brain.business_skill_cost_response_delivery_qualification import (
    CostDeliveryQualificationCase, qualify_cost_response_delivery,
)
from brain.business_skill_cost_response_runtime_bridge import (
    FEATURE_GATE_NAME, FEATURE_GATED_HANDOFF_ONLY, CostRuntimeBridgeRequest,
    compute_cost_runtime_bridge_request_digest,
)
from brain.cost_rendered_delivery_provenance_integrity import (
    create_cost_presentation_result_integrity, verify_cost_presentation_result_integrity,
    create_cost_authorization_decision_integrity, verify_cost_authorization_decision_integrity,
    create_cost_adapter_result_integrity, verify_cost_adapter_result_integrity,
    create_cost_delivery_provenance_integrity, verify_cost_delivery_provenance_integrity,
)
from brain.verifiable_isolated_runtime_invocation_record import (
    IsolatedRuntimeInvocationRecord, IsolatedRuntimeInvocationBatch,
    verify_isolated_execution_invocation_record, verify_isolated_runtime_invocation_batch,
)
from brain.versioned_cost_runtime_request_adapter import SUPPORTED_ADAPTER_SKILL_IDS

VERSION = "5.15.24.7.4.13.3"
SCOPE = "EXECUTION_RESULT_RUNTIME_BRIDGE_REQUEST_BINDING_FOUNDATION"
STATUS = "BRIDGE_REQUEST_BOUND_NOT_INVOKED"
NOT_INVOKED = "NOT_INVOKED"
STAGE_IDS = ("EXECUTION_RESULT_INTEGRITY", "RESULT_PRESENTATION", "RESPONSE_AUTHORIZATION",
             "RESPONSE_ADAPTER", "DELIVERY_QUALIFICATION", "RUNTIME_BRIDGE_REQUEST")
OPERATIONS = (
    "brain.cost_execution_result_integrity.verify_cost_execution_result_integrity",
    "brain.business_skill_cost_result_presenter.present_cost_result",
    "brain.business_skill_cost_response_authorization.authorize_cost_response",
    "brain.business_skill_cost_response_adapter.adapt_authorized_cost_response",
    "brain.business_skill_cost_response_delivery_qualification.qualify_cost_response_delivery",
    "brain.business_skill_cost_response_runtime_bridge.CostRuntimeBridgeRequest",
)


@dataclass(frozen=True)
class ExecutionResultBridgeBindingAuthorityBoundary:
    bridge_invoked: bool = False
    admission_invoked: bool = False
    runtime_invoked: bool = False
    production_delivery_invoked: bool = False
    response_routed: bool = False
    response_committed: bool = False
    application_permitted: bool = False
    activation_permitted: bool = False
    production_dispatch_permitted: bool = False
    persistence: bool = False
    network: bool = False
    environment: bool = False
    session: bool = False


@dataclass(frozen=True)
class ExecutionResultBridgeStageBinding:
    stage_id: str
    operation_identity: str
    operation_version: str
    input_type_identity: str
    input_digest: str
    output_type_identity: str
    output_digest: str
    previous_stage_digest: str
    pure_transformation: bool = True
    invocation: bool = False
    stage_digest: str = ""


@dataclass(frozen=True)
class ExecutionResultRuntimeBridgeRequestBinding:
    version: str
    scope: str
    status: str
    skill_id: str
    invocation_record: IsolatedRuntimeInvocationRecord
    record_id: str
    record_digest: str
    source_request_id: str
    source_request_digest: str
    source_turn_digest: str
    source_reference_time_digest: str
    source_adapter_digest: str
    target_execution_request_material_digest: str
    execution_result: Any
    execution_result_integrity_digest: str
    presentation_request: Any
    presentation_result: Any
    presentation_integrity: Any
    authorization_request: Any
    authorization_decision: Any
    authorization_integrity: Any
    adapter_request: Any
    adapter_result: Any
    adapter_integrity: Any
    delivery_case: Any
    delivery_qualification: Any
    delivery_integrity: Any
    gate_identity: str
    gate_configured_state: bool
    gate_effective_state: bool
    gate_configuration_digest: str
    gate_evaluation_digest: str
    bridge_request: CostRuntimeBridgeRequest
    bridge_request_target_material_digest: str
    stage_bindings: tuple[ExecutionResultBridgeStageBinding, ...]
    authority_boundary: ExecutionResultBridgeBindingAuthorityBoundary
    bridge_result: None
    bridge_handoff: None
    admission_decision: None
    runtime_result: None
    binding_digest: str = ""


@dataclass(frozen=True)
class ExecutionResultRuntimeBridgeRequestBatch:
    version: str
    scope: str
    status: str
    skill_order: tuple[str, ...]
    source_invocation_batch: IsolatedRuntimeInvocationBatch
    bindings: tuple[ExecutionResultRuntimeBridgeRequestBinding, ...]
    topology_digest: str
    isolated_execution_invocations: int
    isolated_calculator_invocations: int
    isolated_bridge_invocations: int
    isolated_admission_invocations: int
    isolated_runtime_invocations: int
    bridge_status: str
    admission_status: str
    runtime_status: str
    production_execution_invocations: int = 0
    production_calculator_invocations: int = 0
    production_bridge_invocations: int = 0
    production_admission_invocations: int = 0
    production_runtime_invocations: int = 0
    production_delivery_invocations: int = 0
    production_response_commits: int = 0
    bridge_invoked: bool = False
    bridge_result: None = None
    bridge_handoff: None = None
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


def _without(value: Any, name: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != name)


def _id(prefix: str, record: IsolatedRuntimeInvocationRecord) -> str:
    return prefix + "-" + record.record_digest[:32]


def _gate(record: IsolatedRuntimeInvocationRecord) -> Any:
    return record.adapter_binding.source_observation.foundation.configuration_binding


def _artifact_digest(label: str, value: Any) -> str:
    return _digest(label, value)


def _stage(stage_id: str, operation: str, version: str, source: Any, source_digest: str,
           target: Any, target_digest: str, previous: str) -> ExecutionResultBridgeStageBinding:
    draft = ExecutionResultBridgeStageBinding(stage_id, operation, version,
        type(source).__name__, source_digest, type(target).__name__, target_digest, previous)
    return replace(draft, stage_digest=_digest("STAGE", _without(draft, "stage_digest")))


def _create(record: Any) -> ExecutionResultRuntimeBridgeRequestBinding | None:
    try:
        if type(record) is not IsolatedRuntimeInvocationRecord or not verify_isolated_execution_invocation_record(record): return None
        gate = _gate(record)
        if (gate.gate_name != FEATURE_GATE_NAME or gate.ordered_gate_entries != ((FEATURE_GATE_NAME, True),)
                or gate.configured_state is not True or gate.effective_state is not True): return None
        result = record.output_artifact
        preq = CostPresentationRequest(_id("presentation", record), result.execution_id, result.request_id,
            record.skill_id, result, SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION)
        presentation = present_cost_result(preq)
        pint = create_cost_presentation_result_integrity(record.output_integrity, preq, presentation)
        if pint is None or not verify_cost_presentation_result_integrity(pint): return None
        areq = CostResponseAuthorizationRequest(_id("authorization", record), preq.presentation_id,
            result.execution_id, result.request_id, record.skill_id, presentation,
            LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE, AUTHORIZATION_POLICY_VERSION)
        authorization = authorize_cost_response(areq)
        aint = create_cost_authorization_decision_integrity(pint, areq, authorization)
        if aint is None or not verify_cost_authorization_decision_integrity(aint): return None
        adreq = CostResponseAdapterRequest(_id("adapter", record), authorization)
        adapter = adapt_authorized_cost_response(adreq)
        adint = create_cost_adapter_result_integrity(aint, adreq, adapter)
        if adint is None or not verify_cost_adapter_result_integrity(adint): return None
        case = CostDeliveryQualificationCase(_id("case", record), result.request_id, record.skill_id,
            result.execution_id, preq.presentation_id, areq.authorization_id, adreq.adapter_request_id,
            authorization, adapter, adapter)
        reference = gate.reference_time.accepted_at_iso
        delivery_batch = qualify_cost_response_delivery((case,), qualification_id=_id("qualification", record), reference_time=reference)
        if len(delivery_batch.results) != 1: return None
        delivery = delivery_batch.results[0]
        dint = create_cost_delivery_provenance_integrity(adint, case, delivery)
        if dint is None or not verify_cost_delivery_provenance_integrity(dint): return None
        bridge = CostRuntimeBridgeRequest(_id("bridge", record), {FEATURE_GATE_NAME: gate.effective_state},
            adapter, delivery, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE, PREPARED_ONLY, FEATURE_GATED_HANDOFF_ONLY)
        bridge_digest = compute_cost_runtime_bridge_request_digest(bridge)
        if not bridge_digest: return None
        artifacts = ((record.output_integrity, record.output_integrity.integrity_digest, result, record.output_result_digest),
            (result, record.output_result_digest, presentation, pint.integrity_digest),
            (presentation, pint.integrity_digest, authorization, aint.integrity_digest),
            (authorization, aint.integrity_digest, adapter, adint.integrity_digest),
            (adapter, adint.integrity_digest, delivery, dint.integrity_digest),
            (delivery, dint.integrity_digest, bridge, bridge_digest))
        versions = (record.invoked_operation_version, PRESENTATION_VERSION, AUTHORIZATION_POLICY_VERSION,
                    adapter.payload.adapter_version, delivery.binding.qualification_version, "5.15.22.1")
        stages=[]; previous=""
        for sid, op, ver, (src, sd, out, od) in zip(STAGE_IDS, OPERATIONS, versions, artifacts):
            item=_stage(sid, op, ver, src, sd, out, od, previous); stages.append(item); previous=item.stage_digest
        draft = ExecutionResultRuntimeBridgeRequestBinding(VERSION, SCOPE, STATUS, record.skill_id,
            record, record.record_id, record.record_digest, record.source_request_id, record.source_request_digest,
            record.adapter_binding.source_turn_digest, record.adapter_binding.source_reference_time_digest,
            record.adapter_digest, record.target_material_digest, result, record.output_integrity.integrity_digest,
            preq, presentation, pint, areq, authorization, aint, adreq, adapter, adint, case, delivery, dint,
            FEATURE_GATE_NAME, gate.configured_state, gate.effective_state, gate.configuration_digest,
            gate.evaluation_digest, bridge, bridge_digest, tuple(stages),
            ExecutionResultBridgeBindingAuthorityBoundary(), None, None, None, None)
        return replace(draft, binding_digest=_digest("BINDING", _without(draft, "binding_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError, KeyError): return None


def create_execution_result_runtime_bridge_request_binding(record: Any) -> ExecutionResultRuntimeBridgeRequestBinding | None:
    return _create(record)


def verify_execution_result_runtime_bridge_request_binding(value: Any) -> bool:
    try:
        return (type(value) is ExecutionResultRuntimeBridgeRequestBinding
                and value.authority_boundary == ExecutionResultBridgeBindingAuthorityBoundary()
                and value.bridge_result is value.bridge_handoff is value.admission_decision is value.runtime_result is None
                and value == _create(value.invocation_record))
    except (AttributeError, TypeError, ValueError): return False


def create_execution_result_runtime_bridge_request_bindings(source: Any) -> ExecutionResultRuntimeBridgeRequestBatch | None:
    try:
        if type(source) is not IsolatedRuntimeInvocationBatch or not verify_isolated_runtime_invocation_batch(source): return None
        bindings=tuple(_create(x) for x in source.records)
        if any(x is None for x in bindings) or tuple(x.skill_id for x in bindings) != SUPPORTED_ADAPTER_SKILL_IDS: return None
        topology=_digest("TOPOLOGY", tuple((x.skill_id, tuple(s.stage_digest for s in x.stage_bindings), x.binding_digest) for x in bindings))
        draft=ExecutionResultRuntimeBridgeRequestBatch(VERSION, SCOPE, STATUS, SUPPORTED_ADAPTER_SKILL_IDS,
            source, bindings, topology, source.isolated_execution_invocations, source.isolated_calculator_invocations,
            0, 0, 0, NOT_INVOKED, NOT_INVOKED, NOT_INVOKED)
        return replace(draft, batch_digest=_digest("BATCH", _without(draft, "batch_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_execution_result_runtime_bridge_request_bindings(value: Any) -> bool:
    try:
        if type(value) is not ExecutionResultRuntimeBridgeRequestBatch: return False
        if not all(verify_execution_result_runtime_bridge_request_binding(x) for x in value.bindings): return False
        if not verify_isolated_runtime_invocation_batch(value.source_invocation_batch): return False
        if tuple(x.invocation_record for x in value.bindings) != value.source_invocation_batch.records: return False
        return value == create_execution_result_runtime_bridge_request_bindings(value.source_invocation_batch)
    except (AttributeError, TypeError, ValueError): return False


__all__ = ("VERSION", "SCOPE", "STATUS", "NOT_INVOKED", "STAGE_IDS", "OPERATIONS",
    "ExecutionResultBridgeBindingAuthorityBoundary", "ExecutionResultBridgeStageBinding",
    "ExecutionResultRuntimeBridgeRequestBinding", "ExecutionResultRuntimeBridgeRequestBatch",
    "create_execution_result_runtime_bridge_request_binding", "verify_execution_result_runtime_bridge_request_binding",
    "create_execution_result_runtime_bridge_request_bindings", "verify_execution_result_runtime_bridge_request_bindings")
