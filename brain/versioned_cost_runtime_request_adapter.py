"""V5.15.24.7.4.13.1 passive versioned request-to-runtime adapter foundation.

The adapter binds an exact 7.4.11.1 request to the historical execution-entry
request that was already used to derive its canonical execution digest.  It
does not execute, dispatch, admit, bridge, deliver, persist, or grant authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.business_skill_cost_execution import CostExecutionRequest
from brain.cost_execution_result_integrity import (
    SUPPORTED_SKILL_IDS, compute_execution_request_integrity_digest,
    derive_canonical_execution_operands,
)
from brain.isolated_executable_request_qualification import (
    IsolatedExecutableRequestObservation,
    verify_isolated_executable_request_observation,
)
from brain.versioned_cost_executable_request import (
    VersionedCostExecutableRequest, verify_versioned_cost_executable_request,
)

VERSION = "5.15.24.7.4.13.1"
SCOPE = "VERSIONED_COST_RUNTIME_REQUEST_ADAPTER_FOUNDATION"
STATUS = "ADAPTER_BOUND_NOT_INVOKED"
SUPPORTED_ADAPTER_SKILL_IDS = SUPPORTED_SKILL_IDS
FIELD_PROVENANCE_TOPOLOGY = (
    "execution_id<-source.pre_execution_result_digest",
    "request_id<-source.limited_activation_decision.request_id",
    "requested_skill_id<-source.skill_id",
    "decision<-source.limited_activation_decision",
    "authority_inputs<-fixed.empty_non_authority_tuple",
)
TOPOLOGY = (
    "VERSIONED_COST_EXECUTABLE_REQUEST", "STRICT_SOURCE_REQUEST_VERIFICATION",
    "BOUND_LIMITED_ACTIVATION_DECISION", "HISTORICAL_COST_EXECUTION_REQUEST",
    "FORWARD_TARGET_MATERIAL_DIGEST", "PASSIVE_ADAPTER_BINDING",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class VersionedCostRuntimeAdapterAuthorityBoundary:
    approval: bool = False
    application: bool = False
    activation: bool = False
    execution: bool = False
    dispatch: bool = False
    calculator: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    delivery: bool = False
    mutation: bool = False
    persistence: bool = False
    network: bool = False
    tools: bool = False
    response_commit: bool = False


@dataclass(frozen=True)
class VersionedCostRuntimeFieldProvenance:
    target_field: str
    source_identity: str
    derivation_policy: str
    material_digest: str


@dataclass(frozen=True)
class VersionedCostRuntimeRequestBinding:
    version: str
    scope: str
    source_observation: IsolatedExecutableRequestObservation
    source_request: VersionedCostExecutableRequest
    source_request_id: str
    source_request_digest: str
    source_topology_digest: str
    source_skill_id: str
    source_turn_digest: str
    source_reference_time_digest: str
    source_gate_id: str
    source_configuration_digest: str
    source_evaluation_digest: str
    source_evidence_envelope_digest: str
    source_limited_activation_digest: str
    source_pre_execution_result_digest: str
    source_preauth_report_digest: str
    source_operand_digests: tuple[str, ...]
    source_formula_digest: str
    source_policy_digest: str
    target_request: CostExecutionRequest
    target_material_digest: str
    field_provenance: tuple[VersionedCostRuntimeFieldProvenance, ...]
    field_provenance_topology: tuple[str, ...]
    topology: tuple[str, ...]
    topology_digest: str
    status: str
    adapter_verified: bool
    execution_permitted: bool
    dispatch_permitted: bool
    application_permitted: bool
    activation_permitted: bool
    runtime_invocation_permitted: bool
    invocation_record: None
    execution_result: None
    isolated_calculator_invocations: int
    isolated_bridge_invocations: int
    isolated_admission_invocations: int
    isolated_runtime_invocations: int
    production_calculator_invocations: int
    production_bridge_invocations: int
    production_admission_invocations: int
    production_runtime_invocations: int
    production_delivery_invocations: int
    production_response_commits: int
    authority_boundary: VersionedCostRuntimeAdapterAuthorityBoundary
    adapter_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal:
        item = value.as_tuple()
        return {"$decimal": [item.sign, list(item.digits), item.exponent]}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[k, _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported adapter material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
                     allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _without(value: Any, name: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != name)


def _boundary_false(value: Any) -> bool:
    return type(value) is VersionedCostRuntimeAdapterAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and not getattr(value, f.name) for f in fields(value))


def _target(source: VersionedCostExecutableRequest, observation: IsolatedExecutableRequestObservation) -> CostExecutionRequest:
    decision = observation.foundation.limited_activation_binding.canonical_limited_activation_material.limited_activation_decision
    return CostExecutionRequest("foundation-" + source.pre_execution_result_digest[:32],
                                decision.request_id, source.skill_id, decision, ())


def _provenance(source: VersionedCostExecutableRequest, target: CostExecutionRequest) -> tuple[VersionedCostRuntimeFieldProvenance, ...]:
    material = (target.execution_id, target.request_id, target.requested_skill_id,
                target.decision, target.authority_inputs)
    policies = ("PREFIX_AND_FIRST_32_HEX", "EXACT_COPY", "EXACT_COPY", "EXACT_BOUND_OBJECT", "FIXED_EMPTY_TUPLE")
    return tuple(VersionedCostRuntimeFieldProvenance(
        topology.split("<-", 1)[0], topology.split("<-", 1)[1], policy,
        _digest("TARGET_FIELD_MATERIAL", (topology.split("<-", 1)[0], value)))
        for topology, policy, value in zip(FIELD_PROVENANCE_TOPOLOGY, policies, material))


def create_versioned_cost_runtime_request_binding(source_observation: Any) -> VersionedCostRuntimeRequestBinding | None:
    """Bind one strictly verified 7.4.12 observation without invoking runtime."""
    try:
        if (type(source_observation) is not IsolatedExecutableRequestObservation
                or not verify_isolated_executable_request_observation(source_observation)): return None
        source = source_observation.request
        if (type(source) is not VersionedCostExecutableRequest
                or source.skill_id not in SUPPORTED_ADAPTER_SKILL_IDS
                or not verify_versioned_cost_executable_request(
                    source, source_observation.foundation, source_observation.preauth_report)): return None
        target = _target(source, source_observation)
        operands = derive_canonical_execution_operands(target)
        if operands != source.operands: return None
        if compute_execution_request_integrity_digest(target, operands) != source.canonical_execution_request_digest: return None
        provenance = _provenance(source, target)
        target_digest = _digest("FORWARD_TARGET_MATERIAL", _without(target, "__never__"))
        topo_digest = _digest("TOPOLOGY", TOPOLOGY)
        draft = VersionedCostRuntimeRequestBinding(
            VERSION, SCOPE, source_observation, source, source.request_id, source.request_digest,
            source.topology_digest, source.skill_id, source.turn_digest, source.reference_time_digest,
            source.gate_id, source.configuration_digest, source.evaluation_digest,
            source.evidence_envelope_digest, source.limited_activation_digest,
            source.pre_execution_result_digest, source.preauth_report_digest,
            tuple(x.operand_digest for x in source.operands), source.formula.formula_digest,
            source.policy.policy_digest, target, target_digest, provenance,
            FIELD_PROVENANCE_TOPOLOGY, TOPOLOGY, topo_digest, STATUS, True,
            False, False, False, False, False, None, None, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0,
            VersionedCostRuntimeAdapterAuthorityBoundary(),
        )
        return replace(draft, adapter_digest=_digest("ADAPTER_BINDING", _without(draft, "adapter_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_versioned_cost_runtime_request_binding(value: Any) -> bool:
    """Reconstruct and compare the exact target; never call an executor."""
    try:
        if type(value) is not VersionedCostRuntimeRequestBinding or not _HEX.fullmatch(value.adapter_digest): return False
        if value.adapter_digest != _digest("ADAPTER_BINDING", _without(value, "adapter_digest")): return False
        if not _boundary_false(value.authority_boundary): return False
        if any((value.execution_permitted, value.dispatch_permitted, value.application_permitted,
                value.activation_permitted, value.runtime_invocation_permitted)): return False
        if value.invocation_record is not None or value.execution_result is not None: return False
        if (value.isolated_calculator_invocations, value.isolated_bridge_invocations,
                value.isolated_admission_invocations, value.isolated_runtime_invocations,
                value.production_calculator_invocations, value.production_bridge_invocations,
                value.production_admission_invocations, value.production_runtime_invocations,
                value.production_delivery_invocations, value.production_response_commits
                ) != (0, 0, 0, 0, 0, 0, 0, 0, 0, 0): return False
        expected = create_versioned_cost_runtime_request_binding(value.source_observation)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def create_versioned_cost_runtime_request_bindings(observations: Any) -> tuple[VersionedCostRuntimeRequestBinding, ...] | None:
    try:
        if type(observations) is not tuple: return None
        bindings = tuple(create_versioned_cost_runtime_request_binding(x) for x in observations)
        if any(x is None for x in bindings): return None
        if tuple(x.source_skill_id for x in bindings) != SUPPORTED_ADAPTER_SKILL_IDS: return None
        return bindings
    except (AttributeError, TypeError, ValueError): return None


def verify_versioned_cost_runtime_request_bindings(value: Any) -> bool:
    try:
        return (type(value) is tuple and tuple(x.source_skill_id for x in value) == SUPPORTED_ADAPTER_SKILL_IDS
                and all(verify_versioned_cost_runtime_request_binding(x) for x in value)
                and create_versioned_cost_runtime_request_bindings(tuple(x.source_observation for x in value)) == value)
    except (AttributeError, TypeError, ValueError): return False


__all__ = ("VERSION", "SCOPE", "STATUS", "SUPPORTED_ADAPTER_SKILL_IDS",
           "FIELD_PROVENANCE_TOPOLOGY", "TOPOLOGY",
           "VersionedCostRuntimeAdapterAuthorityBoundary", "VersionedCostRuntimeFieldProvenance",
           "VersionedCostRuntimeRequestBinding", "create_versioned_cost_runtime_request_binding",
           "verify_versioned_cost_runtime_request_binding", "create_versioned_cost_runtime_request_bindings",
           "verify_versioned_cost_runtime_request_bindings")
