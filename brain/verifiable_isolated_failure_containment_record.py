"""V5.15.24.7.4.15.1 isolated failure-containment record foundation.

The builders invoke only two fixed historical operations with canonical inputs:
the cost bridge with its feature gate disabled and the admission gateway with a
well-formed but unsupported skill identity.  Records grant no acceptance,
production, runtime, response, deployment, or rollback authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.business_skill_cost_response_runtime_bridge import (
    COST_RUNTIME_BRIDGE_VERSION, FEATURE_GATE_NAME, RUNTIME_HANDOFF_DENIED,
    CostRuntimeBridgeRequest, CostRuntimeBridgeResult,
    bridge_prepared_cost_response, compute_cost_runtime_bridge_request_digest,
    verify_cost_runtime_bridge_result_integrity,
)
from brain.business_skill_cost_runtime_integration_admission_gateway import (
    CONTROLLED_RUNTIME_INTEGRATION_ADMISSION_GATEWAY_VERSION,
    ControlledRuntimeIntegrationAdmissionDecision,
    ControlledRuntimeIntegrationAdmissionRequest,
    decide_controlled_runtime_integration_admission,
    verify_controlled_runtime_integration_admission_decision,
)
from brain.execution_result_runtime_bridge_request_binding import (
    ExecutionResultRuntimeBridgeRequestBatch,
    verify_execution_result_runtime_bridge_request_bindings,
)
from brain.versioned_controlled_runtime_admission_request_binding import (
    VersionedControlledRuntimeAdmissionRequestBatch,
    verify_versioned_controlled_runtime_admission_request_bindings,
)
from brain.versioned_cost_runtime_request_adapter import SUPPORTED_ADAPTER_SKILL_IDS

VERSION = "5.15.24.7.4.15.1"
SCOPE = "VERIFIABLE_ISOLATED_FAILURE_CONTAINMENT_FOUNDATION"
STATUS = "FAILURE_CONTAINMENT_FOUNDATION_RECORDED_NOT_ACCEPTED"
STATE_STATUS = "STATE_CONTAINMENT_NOT_YET_BOUND"
BRIDGE_CLASS = "ACTUAL_CANONICAL_DENIAL_INVOCATION"
ADMISSION_CLASS = "ACTUAL_CANONICAL_DENIAL_INVOCATION"
BRIDGE_OPERATION = "brain.business_skill_cost_response_runtime_bridge.bridge_prepared_cost_response"
ADMISSION_OPERATION = "brain.business_skill_cost_runtime_integration_admission_gateway.decide_controlled_runtime_integration_admission"
BRIDGE_SCENARIOS = tuple(f"BRIDGE_GATE_DISABLED:{skill}" for skill in SUPPORTED_ADAPTER_SKILL_IDS)
ADMISSION_SCENARIO = "ADMISSION_UNSUPPORTED_SKILL"
SCENARIO_ORDER = BRIDGE_SCENARIOS + (ADMISSION_SCENARIO,)
BRIDGE_DENIAL_REASONS = ("FEATURE_GATE_DISABLED", "HANDOFF_NOT_CONSTRUCTED",
                         "RUNTIME_ISOLATION_NOT_ESTABLISHED")
UNSUPPORTED_SKILL = "cost.unsupported.canonical-denial.v1"
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class IsolatedFailureContainmentAuthorityBoundary:
    production_application_permitted: bool = False
    activation_permitted: bool = False
    dispatch_permitted: bool = False
    runtime_invocation_permitted: bool = False
    delivery_permitted: bool = False
    response_commit_permitted: bool = False
    approval_evidence_permitted: bool = False
    deployment_attested: bool = False
    rollback_attested: bool = False
    external_tools: bool = False
    network: bool = False
    persistence: bool = False


@dataclass(frozen=True)
class IsolatedFailureContainmentInputBinding:
    scenario_id: str
    source_batch_digest: str
    source_record_digest: str
    source_skill_id: str
    operation_identity: str
    operation_version: str
    input_artifact: Any
    input_material_digest: str
    ancestry_digests: tuple[str, ...]
    binding_digest: str = ""


@dataclass(frozen=True)
class IsolatedFailureContainmentOutcome:
    classification: str
    status: str
    reason_codes: tuple[str, ...]
    primary_reason: str
    output_type: str
    output_digest: str
    invocation_attempted: bool
    invocation_completed: bool
    success: bool
    downstream_stage_identities: tuple[str, ...]
    downstream_artifact_digests: tuple[str, ...]
    downstream_invocation_count: int
    mutation_count: int
    persistence_count: int
    response_commit_count: int
    state_containment_status: str
    state_containment_verified: bool


@dataclass(frozen=True)
class IsolatedFailureContainmentRecord:
    version: str
    scope: str
    scenario_id: str
    boundary_identity: str
    skill_id: str
    input_binding: IsolatedFailureContainmentInputBinding
    output_artifact: Any
    outcome: IsolatedFailureContainmentOutcome
    isolated_bridge_invocations: int
    isolated_admission_invocations: int
    production_invocation_count: int
    authority_boundary: IsolatedFailureContainmentAuthorityBoundary
    topology_digest: str
    record_digest: str = ""


@dataclass(frozen=True)
class IsolatedFailureContainmentBatch:
    version: str
    scope: str
    status: str
    scenario_order: tuple[str, ...]
    records: tuple[IsolatedFailureContainmentRecord, ...]
    isolated_bridge_invocations: int
    isolated_admission_invocations: int
    verifier_rejection_invocations: int
    production_invocation_count: int
    artifact_validity_claim: bool
    requirement_qualified: bool
    containment_accepted: bool
    production_failure_containment_accepted: bool
    approval_evidence_permitted: bool
    state_containment_status: str
    state_containment_verified: bool
    authority_boundary: IsolatedFailureContainmentAuthorityBoundary
    topology_digest: str
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
    raise ValueError("unsupported containment material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _without(value: Any, *names: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name not in names)


def _boundary_valid(value: Any) -> bool:
    return type(value) is IsolatedFailureContainmentAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and not getattr(value, f.name) for f in fields(value))


def _bind(scenario: str, batch_digest: str, record_digest: str, skill: str,
          operation: str, operation_version: str, artifact: Any,
          ancestry: tuple[str, ...]) -> IsolatedFailureContainmentInputBinding:
    material = _digest("INPUT_MATERIAL", artifact)
    draft = IsolatedFailureContainmentInputBinding(scenario, batch_digest, record_digest,
        skill, operation, operation_version, artifact, material, ancestry)
    return replace(draft, binding_digest=_digest("INPUT_BINDING", _without(draft, "binding_digest")))


def _bridge_record(source: ExecutionResultRuntimeBridgeRequestBatch, index: int):
    binding = source.bindings[index]
    request = replace(binding.bridge_request, feature_gates={FEATURE_GATE_NAME: False})
    inp = _bind(BRIDGE_SCENARIOS[index], source.batch_digest, binding.binding_digest,
        binding.skill_id, BRIDGE_OPERATION, COST_RUNTIME_BRIDGE_VERSION, request,
        (binding.record_digest, binding.execution_result_integrity_digest,
         binding.gate_configuration_digest, binding.gate_evaluation_digest))
    result = bridge_prepared_cost_response(request)
    if (type(result) is not CostRuntimeBridgeResult
            or not verify_cost_runtime_bridge_result_integrity(result)
            or result.outcome != RUNTIME_HANDOFF_DENIED
            or result.reason_codes != BRIDGE_DENIAL_REASONS
            or result.handoff is not None
            or result.request_digest != compute_cost_runtime_bridge_request_digest(request)):
        return None
    downstream = ("CONTROLLED_RUNTIME_ADMISSION", "CONTROLLED_RUNTIME",
                  "DELIVERY", "PRODUCTION_RESPONSE_COMMIT")
    outcome = IsolatedFailureContainmentOutcome(BRIDGE_CLASS, result.outcome,
        result.reason_codes, result.denial.first_failed_gate, type(result).__name__,
        result.result_digest, True, True, False, downstream, (), 0, 0, 0, 0,
        STATE_STATUS, False)
    topology = _digest("RECORD_TOPOLOGY", (inp.binding_digest, result.result_digest, downstream))
    draft = IsolatedFailureContainmentRecord(VERSION, SCOPE, BRIDGE_SCENARIOS[index],
        "ISOLATED_RUNTIME_BRIDGE", binding.skill_id, inp, result, outcome, 1, 0, 0,
        IsolatedFailureContainmentAuthorityBoundary(), topology)
    return replace(draft, record_digest=_digest("RECORD", _without(draft, "record_digest")))


def _admission_record(source: VersionedControlledRuntimeAdmissionRequestBatch):
    request = ControlledRuntimeIntegrationAdmissionRequest(UNSUPPORTED_SKILL, source.historical_manifest)
    inp = _bind(ADMISSION_SCENARIO, source.batch_digest, source.source_manifest_binding_digest,
        UNSUPPORTED_SKILL, ADMISSION_OPERATION,
        CONTROLLED_RUNTIME_INTEGRATION_ADMISSION_GATEWAY_VERSION, request,
        (source.manifest_digest, source.topology_digest))
    decision = decide_controlled_runtime_integration_admission(request)
    if (type(decision) is not ControlledRuntimeIntegrationAdmissionDecision
            or not verify_controlled_runtime_integration_admission_decision(decision, request)
            or decision.admitted or decision.primary_denial_code != "UNSUPPORTED_OR_MALFORMED_SKILL_ID"
            or decision.executable_output is not None):
        return None
    downstream = ("CONTROLLED_RUNTIME", "DELIVERY", "PRODUCTION_RESPONSE_COMMIT")
    outcome = IsolatedFailureContainmentOutcome(ADMISSION_CLASS, "ADMISSION_DENIED",
        decision.reasons, decision.primary_denial_code, type(decision).__name__,
        decision.decision_digest, True, True, False, downstream, (), 0, 0, 0, 0,
        STATE_STATUS, False)
    topology = _digest("RECORD_TOPOLOGY", (inp.binding_digest, decision.decision_digest, downstream))
    draft = IsolatedFailureContainmentRecord(VERSION, SCOPE, ADMISSION_SCENARIO,
        "ISOLATED_CONTROLLED_RUNTIME_ADMISSION", UNSUPPORTED_SKILL, inp, decision,
        outcome, 0, 1, 0, IsolatedFailureContainmentAuthorityBoundary(), topology)
    return replace(draft, record_digest=_digest("RECORD", _without(draft, "record_digest")))


def create_isolated_failure_containment_record(source: Any, scenario_id: Any):
    if type(scenario_id) is not str or scenario_id not in SCENARIO_ORDER: return None
    if scenario_id in BRIDGE_SCENARIOS:
        if (type(source) is not ExecutionResultRuntimeBridgeRequestBatch
                or not verify_execution_result_runtime_bridge_request_bindings(source)): return None
        return _bridge_record(source, BRIDGE_SCENARIOS.index(scenario_id))
    if (type(source) is not VersionedControlledRuntimeAdmissionRequestBatch
            or not verify_versioned_controlled_runtime_admission_request_bindings(source)): return None
    return _admission_record(source)


def verify_isolated_failure_containment_record(value: Any) -> bool:
    """Pure verification; historical operations are never invoked here."""
    try:
        if type(value) is not IsolatedFailureContainmentRecord or value.scenario_id not in SCENARIO_ORDER: return False
        if (value.version, value.scope, value.production_invocation_count) != (VERSION, SCOPE, 0): return False
        if not _boundary_valid(value.authority_boundary): return False
        inp, out = value.input_binding, value.outcome
        if type(inp) is not IsolatedFailureContainmentInputBinding or type(out) is not IsolatedFailureContainmentOutcome: return False
        if inp.scenario_id != value.scenario_id or inp.input_material_digest != _digest("INPUT_MATERIAL", inp.input_artifact): return False
        if inp.binding_digest != _digest("INPUT_BINDING", _without(inp, "binding_digest")): return False
        if not (out.invocation_attempted and out.invocation_completed) or out.success: return False
        if (out.downstream_artifact_digests or out.downstream_invocation_count or out.mutation_count
                or out.persistence_count or out.response_commit_count): return False
        if out.state_containment_status != STATE_STATUS or out.state_containment_verified: return False
        if value.scenario_id in BRIDGE_SCENARIOS:
            result = value.output_artifact
            if (type(inp.input_artifact) is not CostRuntimeBridgeRequest
                    or inp.input_artifact.feature_gates != {FEATURE_GATE_NAME: False}
                    or type(result) is not CostRuntimeBridgeResult
                    or not verify_cost_runtime_bridge_result_integrity(result)
                    or result.outcome != RUNTIME_HANDOFF_DENIED or result.handoff is not None
                    or result.reason_codes != BRIDGE_DENIAL_REASONS
                    or out.output_digest != result.result_digest
                    or (value.isolated_bridge_invocations, value.isolated_admission_invocations) != (1, 0)):
                return False
        else:
            request, decision = inp.input_artifact, value.output_artifact
            if (type(request) is not ControlledRuntimeIntegrationAdmissionRequest
                    or request.skill_id != UNSUPPORTED_SKILL
                    or type(decision) is not ControlledRuntimeIntegrationAdmissionDecision
                    or not verify_controlled_runtime_integration_admission_decision(decision, request)
                    or decision.admitted or decision.executable_output is not None
                    or decision.primary_denial_code != "UNSUPPORTED_OR_MALFORMED_SKILL_ID"
                    or out.output_digest != decision.decision_digest
                    or (value.isolated_bridge_invocations, value.isolated_admission_invocations) != (0, 1)):
                return False
        topology = _digest("RECORD_TOPOLOGY", (inp.binding_digest, out.output_digest,
            out.downstream_stage_identities))
        return (value.topology_digest == topology
            and value.record_digest == _digest("RECORD", _without(value, "record_digest")))
    except (AttributeError, TypeError, ValueError, KeyError, UnicodeEncodeError): return False


def create_isolated_failure_containment_batch(bridge_source: Any, admission_source: Any):
    if (type(bridge_source) is not ExecutionResultRuntimeBridgeRequestBatch
            or not verify_execution_result_runtime_bridge_request_bindings(bridge_source)
            or type(admission_source) is not VersionedControlledRuntimeAdmissionRequestBatch
            or not verify_versioned_controlled_runtime_admission_request_bindings(admission_source)):
        return None
    records = tuple(create_isolated_failure_containment_record(
        bridge_source if scenario in BRIDGE_SCENARIOS else admission_source, scenario)
        for scenario in SCENARIO_ORDER)
    if any(x is None or not verify_isolated_failure_containment_record(x) for x in records): return None
    topology = _digest("BATCH_TOPOLOGY", tuple(x.record_digest for x in records))
    draft = IsolatedFailureContainmentBatch(VERSION, SCOPE, STATUS, SCENARIO_ORDER,
        records, 2, 1, 0, 0, False, False, False, False, False, STATE_STATUS,
        False, IsolatedFailureContainmentAuthorityBoundary(), topology)
    return replace(draft, batch_digest=_digest("BATCH", _without(draft, "batch_digest")))


def verify_isolated_failure_containment_batch(value: Any) -> bool:
    try:
        if type(value) is not IsolatedFailureContainmentBatch: return False
        if (value.version, value.scope, value.status, value.scenario_order) != (VERSION, SCOPE, STATUS, SCENARIO_ORDER): return False
        if tuple(x.scenario_id for x in value.records) != SCENARIO_ORDER or len({x.scenario_id for x in value.records}) != 3: return False
        if not all(verify_isolated_failure_containment_record(x) for x in value.records): return False
        if (value.isolated_bridge_invocations, value.isolated_admission_invocations,
                value.verifier_rejection_invocations, value.production_invocation_count) != (2, 1, 0, 0): return False
        if any((value.artifact_validity_claim, value.requirement_qualified,
                value.containment_accepted, value.production_failure_containment_accepted,
                value.approval_evidence_permitted, value.state_containment_verified)): return False
        if value.state_containment_status != STATE_STATUS or not _boundary_valid(value.authority_boundary): return False
        topology = _digest("BATCH_TOPOLOGY", tuple(x.record_digest for x in value.records))
        return value.topology_digest == topology and value.batch_digest == _digest("BATCH", _without(value, "batch_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


__all__ = ("VERSION", "SCOPE", "STATUS", "STATE_STATUS", "SCENARIO_ORDER",
    "IsolatedFailureContainmentAuthorityBoundary", "IsolatedFailureContainmentInputBinding",
    "IsolatedFailureContainmentOutcome", "IsolatedFailureContainmentRecord",
    "IsolatedFailureContainmentBatch", "create_isolated_failure_containment_record",
    "verify_isolated_failure_containment_record", "create_isolated_failure_containment_batch",
    "verify_isolated_failure_containment_batch")
