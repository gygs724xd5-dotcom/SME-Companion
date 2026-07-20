"""V5.15.24.7.4.13.4 isolated bridge-invocation record foundation.

The builder invokes the historical bridge exactly once.  Verification is pure
and grants no admission, controlled-runtime, delivery, or production authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
from datetime import datetime
import hashlib
import json
from typing import Any, Mapping

from brain.business_skill_cost_response_runtime_bridge import (
    COST_RUNTIME_BRIDGE_VERSION, FEATURE_GATE_NAME, RUNTIME_HANDOFF_PREPARED,
    CostRuntimeBridgeRequest, CostRuntimeBridgeResult, CostRuntimeHandoff,
    bridge_prepared_cost_response, compute_cost_runtime_bridge_request_digest,
    verify_cost_runtime_bridge_result_integrity, verify_cost_runtime_handoff_integrity,
)
from brain.execution_result_runtime_bridge_request_binding import (
    ExecutionResultRuntimeBridgeRequestBinding, ExecutionResultRuntimeBridgeRequestBatch,
    verify_execution_result_runtime_bridge_request_binding,
    verify_execution_result_runtime_bridge_request_bindings,
)
from brain.versioned_cost_runtime_request_adapter import SUPPORTED_ADAPTER_SKILL_IDS

VERSION = "5.15.24.7.4.13.4"
SCOPE = "VERIFIABLE_ISOLATED_BRIDGE_INVOCATION_RECORD_FOUNDATION"
STAGE_IDENTITY = "ISOLATED_RUNTIME_BRIDGE_INVOCATION"
OUTCOME = "BRIDGE_INVOKED_HANDOFF_PREPARED"
OPERATION_IDENTITY = "brain.business_skill_cost_response_runtime_bridge.bridge_prepared_cost_response"
OPERATION_VERSION = COST_RUNTIME_BRIDGE_VERSION


@dataclass(frozen=True)
class IsolatedBridgeInvocationAuthorityBoundary:
    isolated_bridge_invocation: bool = True
    production_application: bool = False
    activation: bool = False
    mutation: bool = False
    persistence: bool = False
    production_dispatch: bool = False
    admission_permission: bool = False
    controlled_runtime_permission: bool = False
    delivery: bool = False
    response_routing: bool = False
    response_commit: bool = False
    deployment: bool = False
    rollback: bool = False
    external_tools: bool = False
    network: bool = False
    environment: bool = False
    session: bool = False


@dataclass(frozen=True)
class IsolatedBridgeInvocationInputBinding:
    source_binding_digest: str
    source_execution_record_digest: str
    request_digest: str
    request_target_material_digest: str
    gate_identity: str
    gate_configured_state: bool
    gate_effective_state: bool
    gate_configuration_digest: str
    gate_evaluation_digest: str
    input_binding_digest: str = ""


@dataclass(frozen=True)
class IsolatedBridgeInvocationRecord:
    version: str
    scope: str
    stage_identity: str
    skill_id: str
    source_binding: ExecutionResultRuntimeBridgeRequestBinding
    input_binding: IsolatedBridgeInvocationInputBinding
    bridge_request: CostRuntimeBridgeRequest
    invoked_operation_identity: str
    invoked_operation_version: str
    bridge_result: CostRuntimeBridgeResult
    bridge_result_digest: str
    bridge_handoff: CostRuntimeHandoff
    bridge_handoff_digest: str
    gate_identity_binding: str
    invocation_outcome: str
    admission_invoked: bool
    runtime_invoked: bool
    delivery_invoked: bool
    response_committed: bool
    authority_boundary: IsolatedBridgeInvocationAuthorityBoundary
    record_id: str = ""
    record_digest: str = ""


@dataclass(frozen=True)
class IsolatedBridgeInvocationBatch:
    version: str
    scope: str
    stage_identity: str
    skill_order: tuple[str, ...]
    source_binding_batch: ExecutionResultRuntimeBridgeRequestBatch
    records: tuple[IsolatedBridgeInvocationRecord, ...]
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
    raw=json.dumps(_canonical((VERSION,label,value)),ensure_ascii=False,allow_nan=False,
                   separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _without(value: Any, *names: str) -> tuple[Any, ...]:
    return tuple(getattr(value,f.name) for f in fields(value) if f.name not in names)


def _input(source: ExecutionResultRuntimeBridgeRequestBinding) -> IsolatedBridgeInvocationInputBinding:
    draft=IsolatedBridgeInvocationInputBinding(source.binding_digest, source.record_digest,
        source.bridge_request_target_material_digest, source.bridge_request_target_material_digest,
        source.gate_identity, source.gate_configured_state, source.gate_effective_state,
        source.gate_configuration_digest, source.gate_evaluation_digest)
    return replace(draft,input_binding_digest=_digest("INPUT_BINDING",_without(draft,"input_binding_digest")))


def _request_continuity(record: IsolatedBridgeInvocationRecord) -> bool:
    request=record.bridge_request; result=record.bridge_result; evidence=result.canonical_request
    try:
        return (request is record.source_binding.bridge_request
            and compute_cost_runtime_bridge_request_digest(request)==record.input_binding.request_digest
            and result.request_digest==record.input_binding.request_digest
            and evidence is not None and evidence.bridge_request_id==request.bridge_request_id
            and evidence.feature_gates==((FEATURE_GATE_NAME,request.feature_gates[FEATURE_GATE_NAME]),)
            and evidence.adapter_result==request.adapter_result
            and evidence.qualification_result==request.qualification_result
            and all(getattr(evidence,x)==getattr(request,x) for x in (
                "scope","channel","input_mode","handoff_mode","runtime_routed","response_generated",
                "response_delivered","response_committed","persisted","tools_invoked","follow_up_generated",
                "business_reasoning_executed","skill_executed","calculated","presentation_generated","response_authorized"))
            and record.bridge_handoff is result.handoff
            and record.bridge_handoff.request_digest==result.request_digest
            and record.bridge_handoff.skill_id==record.skill_id
            and record.bridge_handoff.text==request.adapter_result.payload.text
            and record.bridge_handoff.payload_digest==request.adapter_result.payload.payload_digest)
    except (AttributeError,KeyError,TypeError): return False


def _create_record(source: Any, *, source_verified: bool = False):
    if type(source) is not ExecutionResultRuntimeBridgeRequestBinding: return None
    if not source_verified and not verify_execution_result_runtime_bridge_request_binding(source): return None
    request=source.bridge_request
    result=bridge_prepared_cost_response(request)
    if (type(result) is not CostRuntimeBridgeResult or not verify_cost_runtime_bridge_result_integrity(result)
            or result.outcome!=RUNTIME_HANDOFF_PREPARED or type(result.handoff) is not CostRuntimeHandoff
            or not verify_cost_runtime_handoff_integrity(result.handoff)): return None
    inp=_input(source)
    draft=IsolatedBridgeInvocationRecord(VERSION,SCOPE,STAGE_IDENTITY,source.skill_id,source,inp,request,
        OPERATION_IDENTITY,OPERATION_VERSION,result,result.result_digest,result.handoff,result.handoff.handoff_digest,
        source.gate_identity,OUTCOME,False,False,False,False,IsolatedBridgeInvocationAuthorityBoundary())
    rid="bridge-invocation-"+_digest("RECORD_ID",(source.binding_digest,result.result_digest))[:32]
    draft=replace(draft,record_id=rid)
    candidate=replace(draft,record_digest=_digest("RECORD",_without(draft,"record_digest")))
    return candidate if _request_continuity(candidate) else None


def create_isolated_bridge_invocation_record(source: Any):
    return _create_record(source)


def _verify_record(value: Any, *, source_verified: bool = False) -> bool:
    try:
        if type(value) is not IsolatedBridgeInvocationRecord: return False
        if not source_verified and not verify_execution_result_runtime_bridge_request_binding(value.source_binding): return False
        expected_input=_input(value.source_binding)
        if value.input_binding!=expected_input or value.bridge_request is not value.source_binding.bridge_request: return False
        if not verify_cost_runtime_bridge_result_integrity(value.bridge_result): return False
        if not verify_cost_runtime_handoff_integrity(value.bridge_handoff): return False
        if not _request_continuity(value): return False
        rid="bridge-invocation-"+_digest("RECORD_ID",(value.source_binding.binding_digest,value.bridge_result.result_digest))[:32]
        fixed=(value.version,value.scope,value.stage_identity,value.skill_id,value.invoked_operation_identity,
            value.invoked_operation_version,value.bridge_result_digest,value.bridge_handoff_digest,
            value.gate_identity_binding,value.invocation_outcome,value.admission_invoked,value.runtime_invoked,
            value.delivery_invoked,value.response_committed,value.authority_boundary,value.record_id)
        expected=(VERSION,SCOPE,STAGE_IDENTITY,value.source_binding.skill_id,OPERATION_IDENTITY,OPERATION_VERSION,
            value.bridge_result.result_digest,value.bridge_handoff.handoff_digest,FEATURE_GATE_NAME,OUTCOME,
            False,False,False,False,IsolatedBridgeInvocationAuthorityBoundary(),rid)
        return fixed==expected and value.record_digest==_digest("RECORD",_without(value,"record_digest"))
    except (AttributeError,TypeError,ValueError,UnicodeEncodeError): return False


def verify_isolated_bridge_invocation_record(value: Any) -> bool:
    return _verify_record(value)


def create_isolated_bridge_invocation_batch(source: Any):
    if type(source) is not ExecutionResultRuntimeBridgeRequestBatch or not verify_execution_result_runtime_bridge_request_bindings(source): return None
    records=tuple(_create_record(x, source_verified=True) for x in source.bindings)
    if any(x is None for x in records) or tuple(x.skill_id for x in records)!=SUPPORTED_ADAPTER_SKILL_IDS: return None
    verified=tuple(x for x in records if _verify_record(x, source_verified=True))
    if len(verified)!=len(records): return None
    draft=IsolatedBridgeInvocationBatch(VERSION,SCOPE,STAGE_IDENTITY,SUPPORTED_ADAPTER_SKILL_IDS,source,records,
        sum(x.invocation_record is not None for x in source.bindings),
        sum(x.invocation_record.output_artifact is not None for x in source.bindings),
        sum(x.stage_identity==STAGE_IDENTITY for x in verified),0,0)
    return replace(draft,batch_digest=_digest("BATCH",_without(draft,"batch_digest")))


def verify_isolated_bridge_invocation_batch(value: Any) -> bool:
    try:
        if type(value) is not IsolatedBridgeInvocationBatch: return False
        if not verify_execution_result_runtime_bridge_request_bindings(value.source_binding_batch): return False
        if tuple(x.source_binding for x in value.records)!=value.source_binding_batch.bindings: return False
        if tuple(x.skill_id for x in value.records)!=SUPPORTED_ADAPTER_SKILL_IDS: return False
        if len({x.record_digest for x in value.records})!=len(SUPPORTED_ADAPTER_SKILL_IDS): return False
        if not all(_verify_record(x, source_verified=True) for x in value.records): return False
        counts=(sum(x.invocation_record is not None for x in value.source_binding_batch.bindings),
            sum(x.invocation_record.output_artifact is not None for x in value.source_binding_batch.bindings),
            sum(x.stage_identity==STAGE_IDENTITY for x in value.records),0,0)
        actual=(value.isolated_execution_invocations,value.isolated_calculator_invocations,
            value.isolated_bridge_invocations,value.isolated_admission_invocations,value.isolated_runtime_invocations)
        if actual!=counts or any(getattr(value,f.name) for f in fields(value) if f.name.startswith("production_")): return False
        fixed=(value.version,value.scope,value.stage_identity,value.skill_order)
        return fixed==(VERSION,SCOPE,STAGE_IDENTITY,SUPPORTED_ADAPTER_SKILL_IDS) and value.batch_digest==_digest("BATCH",_without(value,"batch_digest"))
    except (AttributeError,TypeError,ValueError,UnicodeEncodeError): return False


__all__=("VERSION","SCOPE","STAGE_IDENTITY","OUTCOME","OPERATION_IDENTITY","OPERATION_VERSION",
    "IsolatedBridgeInvocationAuthorityBoundary","IsolatedBridgeInvocationInputBinding",
    "IsolatedBridgeInvocationRecord","IsolatedBridgeInvocationBatch",
    "create_isolated_bridge_invocation_record","verify_isolated_bridge_invocation_record",
    "create_isolated_bridge_invocation_batch","verify_isolated_bridge_invocation_batch")
