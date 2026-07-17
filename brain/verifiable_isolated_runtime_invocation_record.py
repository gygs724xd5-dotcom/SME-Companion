"""V5.15.24.7.4.13.2 verifiable isolated execution invocation records.

This module owns one narrowly-scoped acceptance-harness invocation of the
historical cost executor.  It grants no production authority and records no
downstream stage because 7.4.13.1 has no canonical binding for those inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.business_skill_cost_execution import (
    COST_EXECUTION_VERSION, EXECUTED, CostExecutionRequest, CostExecutionResult,
    execute_cost_skill,
)
from brain.cost_execution_result_integrity import (
    CostExecutionResultIntegrity, create_cost_execution_result_integrity,
    verify_cost_execution_result_integrity,
)
from brain.versioned_cost_runtime_request_adapter import (
    SUPPORTED_ADAPTER_SKILL_IDS, VersionedCostRuntimeRequestBinding,
    verify_versioned_cost_runtime_request_binding,
)

VERSION = "5.15.24.7.4.13.2"
SCOPE = "VERIFIABLE_ISOLATED_EXECUTION_INVOCATION_RECORD_FOUNDATION"
STAGE = "ISOLATED_HISTORICAL_COST_EXECUTION"
OPERATION = "brain.business_skill_cost_execution.execute_cost_skill"
OPERATION_VERSION = COST_EXECUTION_VERSION
OUTCOME_SUCCEEDED = "SUCCEEDED"
NOT_RECORDED = "NOT_RECORDED"
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class IsolatedRuntimeInvocationAuthorityBoundary:
    boundary_id: str = "CANONICAL_TEST_ACCEPTANCE_HARNESS_ONLY"
    production_application: bool = False
    production_activation: bool = False
    production_mutation: bool = False
    production_persistence: bool = False
    production_dispatch: bool = False
    response_routing: bool = False
    response_commit: bool = False
    deployment: bool = False
    rollback_execution: bool = False
    external_tools: bool = False
    external_network: bool = False
    arbitrary_calculator: bool = False
    caller_selected_operation: bool = False


@dataclass(frozen=True)
class IsolatedRuntimeInvocationInputBinding:
    source_request_id: str
    source_request_digest: str
    source_skill_id: str
    adapter_digest: str
    target_request: CostExecutionRequest
    target_material_digest: str
    canonical_execution_request_digest: str
    input_binding_digest: str = ""


@dataclass(frozen=True)
class IsolatedRuntimeInvocationRecord:
    version: str
    scope: str
    stage: str
    skill_id: str
    source_request: Any
    source_request_id: str
    source_request_digest: str
    adapter_binding: VersionedCostRuntimeRequestBinding
    adapter_digest: str
    input_binding: IsolatedRuntimeInvocationInputBinding
    target_request: CostExecutionRequest
    target_material_digest: str
    invoked_operation: str
    invoked_operation_version: str
    output_artifact: CostExecutionResult
    output_result_digest: str
    output_integrity: CostExecutionResultIntegrity
    invocation_outcome: str
    failure_diagnostic: None
    previous_record_digest: str
    authority_boundary: IsolatedRuntimeInvocationAuthorityBoundary
    record_id: str
    record_digest: str = ""


@dataclass(frozen=True)
class IsolatedRuntimeInvocationBatch:
    version: str
    scope: str
    records: tuple[IsolatedRuntimeInvocationRecord, ...]
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
    batch_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal:
        item = value.as_tuple(); return {"$decimal": [item.sign, list(item.digits), item.exponent]}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[k, _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported invocation record material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
                     allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _without(value: Any, name: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != name)


def _boundary_valid(value: Any) -> bool:
    return (type(value) is IsolatedRuntimeInvocationAuthorityBoundary
            and value.boundary_id == "CANONICAL_TEST_ACCEPTANCE_HARNESS_ONLY"
            and all(type(getattr(value, f.name)) is bool and not getattr(value, f.name)
                    for f in fields(value) if f.name != "boundary_id"))


def _input(binding: VersionedCostRuntimeRequestBinding) -> IsolatedRuntimeInvocationInputBinding:
    draft = IsolatedRuntimeInvocationInputBinding(
        binding.source_request_id, binding.source_request_digest, binding.source_skill_id,
        binding.adapter_digest, binding.target_request, binding.target_material_digest,
        binding.source_request.canonical_execution_request_digest,
    )
    return replace(draft, input_binding_digest=_digest("INVOCATION_INPUT_BINDING", _without(draft, "input_binding_digest")))


def _create(binding: Any, previous_record_digest: str) -> IsolatedRuntimeInvocationRecord | None:
    try:
        if (type(binding) is not VersionedCostRuntimeRequestBinding
                or not verify_versioned_cost_runtime_request_binding(binding)
                or binding.source_skill_id not in SUPPORTED_ADAPTER_SKILL_IDS
                or (previous_record_digest and not _HEX.fullmatch(previous_record_digest))):
            return None
        before_source, before_target = binding.source_request, binding.target_request
        input_binding = _input(binding)
        # The sole actual invocation owned by this foundation.
        output = execute_cost_skill(binding.target_request)
        if (binding.source_request != before_source or binding.target_request != before_target
                or type(output) is not CostExecutionResult or output.outcome != EXECUTED
                or output.executed is not True or output.calculated is not True):
            return None
        integrity = create_cost_execution_result_integrity(binding.target_request, output)
        if integrity is None or not verify_cost_execution_result_integrity(integrity): return None
        record_id = _digest("INVOCATION_ID", (
            STAGE, binding.source_skill_id, binding.source_request_digest,
            binding.adapter_digest, input_binding.input_binding_digest, previous_record_digest))
        draft = IsolatedRuntimeInvocationRecord(
            VERSION, SCOPE, STAGE, binding.source_skill_id, binding.source_request,
            binding.source_request_id, binding.source_request_digest, binding,
            binding.adapter_digest, input_binding, binding.target_request,
            binding.target_material_digest, OPERATION, OPERATION_VERSION, output,
            integrity.result_snapshot_digest, integrity, OUTCOME_SUCCEEDED, None,
            previous_record_digest, IsolatedRuntimeInvocationAuthorityBoundary(), record_id,
        )
        return replace(draft, record_digest=_digest("INVOCATION_RECORD", _without(draft, "record_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def create_isolated_execution_invocation_record(binding: Any) -> IsolatedRuntimeInvocationRecord | None:
    """Invoke the exact adapter target once; callers cannot supply authority or output."""
    return _create(binding, "")


def verify_isolated_execution_invocation_record(value: Any) -> bool:
    """Pure integrity verification; this function never invokes the executor."""
    try:
        if type(value) is not IsolatedRuntimeInvocationRecord: return False
        if (value.version, value.scope, value.stage, value.invoked_operation,
                value.invoked_operation_version, value.invocation_outcome, value.failure_diagnostic) != (
                VERSION, SCOPE, STAGE, OPERATION, OPERATION_VERSION, OUTCOME_SUCCEEDED, None): return False
        if not (_HEX.fullmatch(value.record_id) and _HEX.fullmatch(value.record_digest)
                and _HEX.fullmatch(value.output_result_digest)): return False
        if not _boundary_valid(value.authority_boundary): return False
        binding = value.adapter_binding
        if not verify_versioned_cost_runtime_request_binding(binding): return False
        expected_input = _input(binding)
        if (value.skill_id != binding.source_skill_id or value.source_request != binding.source_request
                or value.source_request_id != binding.source_request_id
                or value.source_request_digest != binding.source_request_digest
                or value.adapter_digest != binding.adapter_digest or value.input_binding != expected_input
                or value.target_request != binding.target_request
                or value.target_material_digest != binding.target_material_digest): return False
        if not verify_cost_execution_result_integrity(value.output_integrity): return False
        if (value.output_artifact != value.output_integrity.execution_result
                or value.target_request != value.output_integrity.execution_request
                or value.output_result_digest != value.output_integrity.result_snapshot_digest): return False
        expected_id = _digest("INVOCATION_ID", (
            STAGE, value.skill_id, value.source_request_digest, value.adapter_digest,
            value.input_binding.input_binding_digest, value.previous_record_digest))
        return (value.record_id == expected_id
                and value.record_digest == _digest("INVOCATION_RECORD", _without(value, "record_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def create_isolated_runtime_invocation_batch(bindings: Any) -> IsolatedRuntimeInvocationBatch | None:
    try:
        if type(bindings) is not tuple or tuple(x.source_skill_id for x in bindings) != SUPPORTED_ADAPTER_SKILL_IDS:
            return None
        records = []
        previous = ""
        for binding in bindings:
            record = _create(binding, previous)
            if record is None: return None
            records.append(record); previous = record.record_digest
        concrete = tuple(records)
        count = sum(type(x) is IsolatedRuntimeInvocationRecord and x.stage == STAGE for x in concrete)
        draft = IsolatedRuntimeInvocationBatch(
            VERSION, SCOPE, concrete, count, count, 0, 0, 0,
            NOT_RECORDED, NOT_RECORDED, NOT_RECORDED,
        )
        return replace(draft, batch_digest=_digest("INVOCATION_BATCH", _without(draft, "batch_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_isolated_runtime_invocation_batch(value: Any) -> bool:
    try:
        if type(value) is not IsolatedRuntimeInvocationBatch: return False
        records = value.records
        if (type(records) is not tuple
                or tuple(x.skill_id for x in records) != SUPPORTED_ADAPTER_SKILL_IDS
                or len({x.record_id for x in records}) != len(records)
                or not all(verify_isolated_execution_invocation_record(x) for x in records)): return False
        if any(x.previous_record_digest != ("" if i == 0 else records[i-1].record_digest)
               for i, x in enumerate(records)): return False
        count = sum(type(x) is IsolatedRuntimeInvocationRecord and x.stage == STAGE for x in records)
        if (value.isolated_execution_invocations, value.isolated_calculator_invocations,
                value.isolated_bridge_invocations, value.isolated_admission_invocations,
                value.isolated_runtime_invocations) != (count, count, 0, 0, 0): return False
        if (value.bridge_status, value.admission_status, value.runtime_status) != (NOT_RECORDED,) * 3: return False
        production = tuple(getattr(value, f.name) for f in fields(value) if f.name.startswith("production_"))
        return (production == (0,) * 7
                and value.batch_digest == _digest("INVOCATION_BATCH", _without(value, "batch_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


__all__ = (
    "VERSION", "SCOPE", "STAGE", "OPERATION", "OPERATION_VERSION", "OUTCOME_SUCCEEDED", "NOT_RECORDED",
    "IsolatedRuntimeInvocationAuthorityBoundary", "IsolatedRuntimeInvocationInputBinding",
    "IsolatedRuntimeInvocationRecord", "IsolatedRuntimeInvocationBatch",
    "create_isolated_execution_invocation_record", "verify_isolated_execution_invocation_record",
    "create_isolated_runtime_invocation_batch", "verify_isolated_runtime_invocation_batch",
)
