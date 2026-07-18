"""V5.15.24.7.4.14 recorded controlled-runtime acceptance evidence.

This is a pure, isolated report over already-recorded canonical invocations.  In
the historical architecture a strictly verified admission decision is the
terminal controlled-runtime acceptance decision.  No separate post-admission
runtime entry point exists or is claimed here.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any, Mapping

from brain.verifiable_isolated_admission_invocation_record import (
    IsolatedAdmissionInvocationBatch,
    verify_isolated_admission_invocation_batch,
)
from brain.versioned_cost_runtime_request_adapter import SUPPORTED_ADAPTER_SKILL_IDS

VERSION = "5.15.24.7.4.14"
SCOPE = "RECORDED_CONTROLLED_RUNTIME_ACCEPTANCE_COMPATIBILITY_REPORT"
REQUIREMENT = "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED"
STATUS = REQUIREMENT
DIAGNOSTIC = "RECORDED_CONTROLLED_RUNTIME_CHAIN_ACCEPTED_WITHOUT_SEPARATE_RUNTIME_ENTRY_POINT"
SCENARIO_IDS = (
    "01.supported_inventory_identity", "02.execution_record_integrity",
    "03.calculator_operation_identity", "04.bridge_request_continuity",
    "05.bridge_invocation_integrity", "06.result_handoff_integrity",
    "07.qualification_continuity", "08.manifest_continuity",
    "09.admission_request_continuity", "10.admission_invocation_integrity",
    "11.admitted_decision_integrity", "12.gate_configuration_evaluation_continuity",
    "13.turn_reference_continuity", "14.cross_stage_digest_ancestry",
    "15.invocation_accounting", "16.separate_runtime_non_invention",
    "17.production_isolation", "18.authority_persistence_isolation",
)
TOPOLOGY = (
    "V5.15.24.7.4.13.2_EXECUTION_INVOCATION_RECORDS",
    "V5.15.24.7.4.13.3_BRIDGE_REQUEST_BINDINGS",
    "V5.15.24.7.4.13.4_BRIDGE_INVOCATION_RECORDS",
    "V5.15.24.7.4.13.5_QUALIFICATION_MANIFEST_BINDING",
    "V5.15.24.7.4.13.6_ADMISSION_REQUEST_BINDINGS",
    "V5.15.24.7.4.13.7_ADMISSION_INVOCATION_RECORDS",
    "V5.15.24.7.4.14_RECORDED_ACCEPTANCE_REPORT",
)


@dataclass(frozen=True)
class RecordedControlledRuntimeAcceptanceAuthorityBoundary:
    approval: bool = False
    application: bool = False
    activation: bool = False
    execution: bool = False
    dispatch: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    delivery: bool = False
    routing: bool = False
    response_commit: bool = False
    mutation: bool = False
    persistence: bool = False
    production: bool = False
    deployment: bool = False
    external_tools: bool = False
    network: bool = False


@dataclass(frozen=True)
class RecordedControlledRuntimeScenario:
    scenario_id: str
    ordinal: int
    scenario_digest: str = ""


@dataclass(frozen=True)
class RecordedControlledRuntimeObservation:
    version: str
    scope: str
    scenario: RecordedControlledRuntimeScenario
    source_batch_digest: str
    supported_skill_ids: tuple[str, ...]
    source_request_ids: tuple[str, ...]
    source_request_digests: tuple[str, ...]
    turn_digests: tuple[str, ...]
    reference_time_digests: tuple[str, ...]
    configuration_digests: tuple[str, ...]
    evaluation_digests: tuple[str, ...]
    execution_record_digests: tuple[str, ...]
    execution_result_digests: tuple[str, ...]
    execution_integrity_digests: tuple[str, ...]
    bridge_request_digests: tuple[str, ...]
    bridge_result_digests: tuple[str, ...]
    bridge_handoff_digests: tuple[str, ...]
    bridge_record_digests: tuple[str, ...]
    delivery_qualification_digests: tuple[str, ...]
    historical_qualification_digests: tuple[str, ...]
    historical_manifest_digest: str
    admission_request_material_digests: tuple[str, ...]
    admission_binding_digests: tuple[str, ...]
    admission_decision_digests: tuple[str, ...]
    admission_record_digests: tuple[str, ...]
    upstream_topology_digests: tuple[str, ...]
    passed: bool
    diagnostic: str
    authority_boundary: RecordedControlledRuntimeAcceptanceAuthorityBoundary
    observation_digest: str = ""


@dataclass(frozen=True)
class RecordedControlledRuntimeAcceptanceReport:
    version: str
    scope: str
    requirement: str
    status: str
    qualified: bool
    accepted: bool
    source_batch: IsolatedAdmissionInvocationBatch
    supported_skill_ids: tuple[str, ...]
    topology: tuple[str, ...]
    scenarios: tuple[RecordedControlledRuntimeScenario, ...]
    observations: tuple[RecordedControlledRuntimeObservation, ...]
    observation_digests: tuple[str, ...]
    isolated_execution_invocations: int
    isolated_calculator_invocations: int
    isolated_bridge_invocations: int
    isolated_admission_invocations: int
    separate_controlled_runtime_invocations: int
    production_execution_invocations: int
    production_calculator_invocations: int
    production_bridge_invocations: int
    production_admission_invocations: int
    production_runtime_invocations: int
    production_delivery_invocations: int
    production_response_commits: int
    diagnostic: str
    topology_digest: str
    authority_boundary: RecordedControlledRuntimeAcceptanceAuthorityBoundary
    report_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal: return {"$decimal": str(value)}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[str(k), _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported recorded acceptance material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _material(value: Any, omitted: str):
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != omitted)


def _scenario(identifier: str, ordinal: int):
    draft = RecordedControlledRuntimeScenario(identifier, ordinal)
    return replace(draft, scenario_digest=_digest("SCENARIO", (identifier, ordinal)))


def _lineage(batch: IsolatedAdmissionInvocationBatch):
    admission = batch.records
    admission_bindings = tuple(x.input_binding.source_binding for x in admission)
    manifest_binding = admission_bindings[0].source_manifest_binding
    bridge_batch = manifest_binding.source_batch
    request_batch = bridge_batch.source_binding_batch
    execution_batch = request_batch.source_invocation_batch
    execution = execution_batch.records
    bridge = bridge_batch.records
    return admission, admission_bindings, manifest_binding, bridge_batch, request_batch, execution_batch, execution, bridge


def _create_observation(batch: IsolatedAdmissionInvocationBatch,
        scenario: RecordedControlledRuntimeScenario):
    admission, bindings, manifest, bridge_batch, request_batch, execution_batch, execution, bridge = _lineage(batch)
    bridge_bindings = request_batch.bindings
    values = dict(
        version=VERSION, scope=SCOPE, scenario=scenario, source_batch_digest=batch.batch_digest,
        supported_skill_ids=SUPPORTED_ADAPTER_SKILL_IDS,
        source_request_ids=tuple(x.source_request_id for x in execution),
        source_request_digests=tuple(x.source_request_digest for x in execution),
        turn_digests=tuple(x.source_request.turn_digest for x in execution),
        reference_time_digests=tuple(x.source_request.reference_time_digest for x in execution),
        configuration_digests=tuple(x.source_request.configuration_digest for x in execution),
        evaluation_digests=tuple(x.source_request.evaluation_digest for x in execution),
        execution_record_digests=tuple(x.record_digest for x in execution),
        execution_result_digests=tuple(x.output_result_digest for x in execution),
        execution_integrity_digests=tuple(x.output_integrity.integrity_digest for x in execution),
        bridge_request_digests=tuple(x.source_bridge_request_digest for x in bindings),
        bridge_result_digests=tuple(x.bridge_result.result_digest for x in bridge),
        bridge_handoff_digests=tuple(x.bridge_handoff.handoff_digest for x in bridge),
        bridge_record_digests=tuple(x.record_digest for x in bridge),
        delivery_qualification_digests=tuple(x.delivery_qualification.binding.qualification_digest for x in bridge_bindings),
        historical_qualification_digests=tuple(x.qualification_digest for x in manifest.historical_qualifications),
        historical_manifest_digest=manifest.manifest_digest,
        admission_request_material_digests=tuple(x.target_request_material_digest for x in bindings),
        admission_binding_digests=tuple(x.binding_digest for x in bindings),
        admission_decision_digests=tuple(x.decision_digest for x in admission),
        admission_record_digests=tuple(x.record_digest for x in admission),
        upstream_topology_digests=(execution_batch.batch_digest, request_batch.topology_digest,
            request_batch.batch_digest, bridge_batch.batch_digest, manifest.topology_digest,
            manifest.binding_digest, batch.topology_digest, batch.batch_digest),
        passed=True, diagnostic=DIAGNOSTIC,
        authority_boundary=RecordedControlledRuntimeAcceptanceAuthorityBoundary())
    draft = RecordedControlledRuntimeObservation(**values)
    return replace(draft, observation_digest=_digest("OBSERVATION", _material(draft, "observation_digest")))


def create_recorded_controlled_runtime_acceptance_report(source: Any):
    if type(source) is not IsolatedAdmissionInvocationBatch or not verify_isolated_admission_invocation_batch(source):
        return None
    if (source.skill_order != SUPPORTED_ADAPTER_SKILL_IDS or source.admitted_count != 2
            or source.denied_count != 0 or any(not x.admitted or x.runtime_invoked
            or x.runtime_result is not None for x in source.records)): return None
    scenarios = tuple(_scenario(x, i + 1) for i, x in enumerate(SCENARIO_IDS))
    observations = tuple(_create_observation(source, x) for x in scenarios)
    topology_digest = _digest("TOPOLOGY", (TOPOLOGY, source.topology_digest,
        source.batch_digest, tuple(x.observation_digest for x in observations)))
    draft = RecordedControlledRuntimeAcceptanceReport(
        VERSION, SCOPE, REQUIREMENT, STATUS, True, True, source,
        SUPPORTED_ADAPTER_SKILL_IDS, TOPOLOGY, scenarios, observations,
        tuple(x.observation_digest for x in observations),
        source.isolated_execution_invocations, source.isolated_calculator_invocations,
        source.isolated_bridge_invocations, source.isolated_admission_invocations,
        source.isolated_runtime_invocations, 0, 0, 0,
        source.production_admission_invocations, source.production_runtime_invocations,
        source.production_delivery_invocations, source.production_commit_invocations,
        DIAGNOSTIC, topology_digest, RecordedControlledRuntimeAcceptanceAuthorityBoundary())
    return replace(draft, report_digest=_digest("REPORT", _material(draft, "report_digest")))


def verify_recorded_controlled_runtime_observation(value: Any, source: Any) -> bool:
    try:
        if type(value) is not RecordedControlledRuntimeObservation: return False
        if value.observation_digest != _digest("OBSERVATION", _material(value, "observation_digest")): return False
        if type(source) is not IsolatedAdmissionInvocationBatch: return False
        if value.source_batch_digest != source.batch_digest: return False
        if not verify_isolated_admission_invocation_batch(source): return False
        if value.scenario != _scenario(value.scenario.scenario_id, value.scenario.ordinal): return False
        if value.scenario.scenario_id not in SCENARIO_IDS: return False
        return value == _create_observation(source, value.scenario)
    except (AttributeError, TypeError, ValueError, IndexError, UnicodeEncodeError): return False


def verify_recorded_controlled_runtime_acceptance_report(value: Any) -> bool:
    try:
        if type(value) is not RecordedControlledRuntimeAcceptanceReport: return False
        if type(value.source_batch) is not IsolatedAdmissionInvocationBatch: return False
        if (value.version, value.scope, value.requirement, value.status,
                value.qualified, value.accepted, value.supported_skill_ids,
                value.topology, value.diagnostic) != (VERSION, SCOPE, REQUIREMENT,
                STATUS, True, True, SUPPORTED_ADAPTER_SKILL_IDS, TOPOLOGY, DIAGNOSTIC): return False
        if tuple(x.scenario_id for x in value.scenarios) != SCENARIO_IDS: return False
        if value.observation_digests != tuple(x.observation_digest for x in value.observations): return False
        if value.report_digest != _digest("REPORT", _material(value, "report_digest")): return False
        expected = create_recorded_controlled_runtime_acceptance_report(value.source_batch)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, IndexError, UnicodeEncodeError): return False


__all__ = ("VERSION", "SCOPE", "REQUIREMENT", "STATUS", "DIAGNOSTIC",
    "SCENARIO_IDS", "TOPOLOGY", "RecordedControlledRuntimeScenario",
    "RecordedControlledRuntimeObservation", "RecordedControlledRuntimeAcceptanceReport",
    "RecordedControlledRuntimeAcceptanceAuthorityBoundary",
    "create_recorded_controlled_runtime_acceptance_report",
    "verify_recorded_controlled_runtime_observation",
    "verify_recorded_controlled_runtime_acceptance_report")
