"""V5.15.24.7.4.16 canonical production-failure containment acceptance.

This passive report accepts only the exact isolated denial and immutable-state
foundations.  It does not invoke an operation, authorize production, or attest
deployment/rollback evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
from typing import Any, Mapping

from brain.immutable_failure_response_state_containment import (
    FOUNDATION_BATCH_DIGEST, FOUNDATION_TOPOLOGY_DIGEST,
    FailureResponseStateContainmentBinding,
    verify_failure_response_state_containment_binding,
    verify_failure_response_state_containment_observation,
    verify_failure_response_suppression_decision,
    verify_failure_state_snapshot,
)
from brain.production_feature_gate_owner import (
    GATE_MISSING_DEFAULT_DENY, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    PRODUCTION_FEATURE_GATE_OWNER_VERSION,
    exact_production_feature_gate_lookup,
    verify_production_feature_gate_configuration,
)
from brain.verifiable_isolated_failure_containment_record import (
    ADMISSION_SCENARIO, BRIDGE_SCENARIOS, IsolatedFailureContainmentBatch,
    verify_isolated_failure_containment_batch,
    verify_isolated_failure_containment_record,
)

VERSION = "5.15.24.7.4.16"
SCOPE = "INDEPENDENT_CANONICAL_PRODUCTION_FAILURE_CONTAINMENT_ACCEPTANCE"
REQUIREMENT = "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED"
STATUS = REQUIREMENT
DIAGNOSTIC = (
    "CANONICAL_ISOLATED_FAILURE_AND_STATE_CONTAINMENT_ACCEPTED_WITHOUT_"
    "PRODUCTION_ACTIVATION_DEPLOYMENT_OR_ROLLBACK_ATTESTATION"
)
EXPECTED_STATE_BINDING_TOPOLOGY_DIGEST = "cd83a8d96a4487787857dce64c01b5f2dec05ed3497a15439901a6944e86a61a"
EXPECTED_STATE_BINDING_DIGEST = "7e85d4ba07f546d553e0303ca17be586baabdbfb9c47d2bdfec3718cd0d1eaff"
EXPECTED_SNAPSHOT_DIGEST = "3470d67eb54233690bfac7fcb1cfda613c7188138fb5ff065e38eb7e077241d2"
EXPECTED_OBSERVATION_DIGESTS = (
    "e0de1fa21ed6ec6357412f25958186d711ab36756389b969e486bca273b4fe13",
    "88ee6a37d11dcc7d3cf1c3567652e3905368aaff319117da876f0b01a475efc1",
    "c9f648bb581e0451c1c0544568b73c10a14f5e7dc0aae2aef4ac4b09a0ebdf5e",
)

SCENARIO_ORDER = (
    "FOUNDATION_IDENTITY_AND_STRICT_VERIFICATION",
    "BRIDGE_CHANGE_ANALYSIS_DENIAL_INVOCATION",
    "BRIDGE_PER_UNIT_DENIAL_INVOCATION",
    "ADMISSION_UNSUPPORTED_SKILL_DENIAL_INVOCATION",
    "DENIAL_OUTCOME_INTEGRITY",
    "FAILURE_CLASSIFICATION_INTEGRITY",
    "DOWNSTREAM_HANDOFF_SUPPRESSION",
    "ADMISSION_RUNTIME_SUPPRESSION",
    "DELIVERY_OUTPUT_SUPPRESSION",
    "RESPONSE_CANDIDATE_SUPPRESSION",
    "FINAL_RESOLUTION_SUPPRESSION",
    "SINGLE_COMMIT_SUPPRESSION",
    "STATE_SNAPSHOT_INTEGRITY",
    "STATE_IMMUTABILITY",
    "MUTATION_PERSISTENCE_ISOLATION",
    "INVOCATION_ACCOUNTING_INTEGRITY",
    "PRODUCTION_DEFAULT_DENY_ISOLATION",
    "AUTHORITY_ISOLATION",
    "COVERED_BOUNDARY_DISCLOSURE",
    "UNCOVERED_BOUNDARY_DISCLOSURE",
    "DEPLOYMENT_ROLLBACK_SEPARATION",
)

COVERED_BOUNDARIES = (
    "ISOLATED_RUNTIME_BRIDGE_GATE_DISABLED_DENIAL:cost.change_analysis.v1",
    "ISOLATED_RUNTIME_BRIDGE_GATE_DISABLED_DENIAL:cost.per_unit_calculation.v1",
    "ISOLATED_CONTROLLED_RUNTIME_ADMISSION_UNSUPPORTED_SKILL_DENIAL",
    "DOWNSTREAM_HANDOFF_ADMISSION_RUNTIME_DELIVERY_OUTPUT_SUPPRESSION",
    "RESPONSE_CANDIDATE_FINAL_RESOLUTION_SINGLE_COMMIT_SUPPRESSION",
    "FIXED_STATE_SNAPSHOT_IMMUTABILITY",
    "MUTATION_AND_PERSISTENCE_ISOLATION",
    "PRODUCTION_EMPTY_CONFIGURATION_DEFAULT_DENY_ISOLATION",
)
UNCOVERED_BOUNDARIES = (
    "ACTUAL_EXECUTOR_OR_CALCULATOR_FAILURE",
    "ACTUAL_DELIVERY_FAILURE",
    "ACTUAL_PRODUCTION_RESPONSE_EXCEPTION",
    "DEPLOYED_PRODUCTION_INCIDENT",
    "SOURCE_OR_DEPLOYED_SHA_ATTESTATION",
    "DEPLOYMENT_ATTESTATION",
    "ROLLBACK_ATTESTATION",
)
EVIDENCE_TOPOLOGY = (
    "V5.15.24.7.4.15.1_EXACT_FAILURE_BATCH",
    "V5.15.24.7.4.15.1_ORDERED_BRIDGE_DENIAL_RECORDS",
    "V5.15.24.7.4.15.1_ORDERED_ADMISSION_DENIAL_RECORD",
    "V5.15.24.7.4.15.2_EXACT_STATE_CONTAINMENT_BINDING",
    "V5.15.24.7.4.15.2_ORDERED_SUPPRESSION_DECISIONS",
    "V5.15.24.7.4.15.2_ORDERED_BEFORE_AFTER_STATE_OBSERVATIONS",
    "PRODUCTION_EMPTY_CONFIGURATION_DEFAULT_DENY_ISOLATION",
    "V5.15.24.7.4.16_ACCEPTANCE_REPORT",
)


@dataclass(frozen=True)
class ProductionFailureContainmentAuthorityBoundary:
    transition_approval: bool = False
    production_application: bool = False
    activation: bool = False
    mutation: bool = False
    persistence: bool = False
    execution: bool = False
    dispatch: bool = False
    runtime: bool = False
    delivery: bool = False
    routing: bool = False
    response_commit: bool = False
    deployment: bool = False
    rollback: bool = False
    external_tools: bool = False
    network: bool = False
    source_sha_attestation: bool = False
    deployed_sha_attestation: bool = False


@dataclass(frozen=True)
class ProductionFailureContainmentScenario:
    scenario_id: str
    ordinal: int
    evidence_identities: tuple[str, ...]
    evidence_digests: tuple[str, ...]
    covered: bool
    verified: bool
    scenario_digest: str = ""


@dataclass(frozen=True)
class ProductionFailureContainmentObservation:
    scenario_id: str
    scenario_digest: str
    record_ids: tuple[str, ...]
    record_digests: tuple[str, ...]
    operation_identities: tuple[str, ...]
    operation_versions: tuple[str, ...]
    input_digests: tuple[str, ...]
    output_digests: tuple[str, ...]
    topology_digests: tuple[str, ...]
    denial_statuses: tuple[str, ...]
    denial_reasons: tuple[str, ...]
    invocation_classifications: tuple[str, ...]
    verified: bool
    observation_digest: str = ""


@dataclass(frozen=True)
class ProductionFailureContainmentAcceptanceReport:
    version: str
    scope: str
    requirement: str
    status: str
    diagnostic: str
    failure_batch: IsolatedFailureContainmentBatch
    state_binding: FailureResponseStateContainmentBinding
    foundation_version: str
    foundation_scope: str
    foundation_status: str
    foundation_batch_digest: str
    foundation_topology_digest: str
    record_ids: tuple[str, ...]
    record_digests: tuple[str, ...]
    state_binding_version: str
    state_binding_scope: str
    state_binding_status: str
    state_binding_digest: str
    state_binding_topology_digest: str
    suppression_decision_digests: tuple[str, ...]
    state_observation_digests: tuple[str, ...]
    before_snapshot_digests: tuple[str, ...]
    after_snapshot_digests: tuple[str, ...]
    production_configuration_identity: str
    production_configuration_digest: str
    production_evaluation_identity: str
    production_evaluation_digest: str
    production_gate_entries: tuple[tuple[str, bool], ...]
    production_configured: bool
    production_effective: bool
    production_default_denied: bool
    scenarios: tuple[ProductionFailureContainmentScenario, ...]
    observations: tuple[ProductionFailureContainmentObservation, ...]
    covered_boundaries: tuple[str, ...]
    uncovered_boundaries: tuple[str, ...]
    evidence_topology: tuple[str, ...]
    isolated_bridge_denial_invocations: int
    isolated_admission_denial_invocations: int
    executor_calculator_failure_invocations: int
    controlled_runtime_invocations: int
    response_candidate_attempts: int
    final_resolution_attempts: int
    response_commit_attempts: int
    mutation_count: int
    persistence_count: int
    production_invocation_count: int
    response_candidate_absent: bool
    final_resolution_absent: bool
    response_commit_absent: bool
    state_unchanged: bool
    object_alias_isolated: bool
    deployment_attestation: None
    rollback_attestation: None
    source_sha_attestation: None
    deployed_sha_attestation: None
    qualified: bool
    accepted: bool
    authority_boundary: ProductionFailureContainmentAuthorityBoundary
    topology_digest: str
    report_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[str(k), _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported acceptance material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _without(value: Any, *names: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name not in names)


def _authority_valid(value: Any) -> bool:
    return type(value) is ProductionFailureContainmentAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and not getattr(value, f.name) for f in fields(value))


def _exact_foundations(batch: Any, binding: Any) -> bool:
    if type(batch) is not IsolatedFailureContainmentBatch: return False
    if type(binding) is not FailureResponseStateContainmentBinding: return False
    if not verify_isolated_failure_containment_batch(batch): return False
    if not verify_failure_response_state_containment_binding(binding): return False
    if binding.source_batch != batch: return False
    if (batch.batch_digest, batch.topology_digest) != (
            FOUNDATION_BATCH_DIGEST, FOUNDATION_TOPOLOGY_DIGEST): return False
    if (binding.binding_digest, binding.topology_digest) != (
            EXPECTED_STATE_BINDING_DIGEST, EXPECTED_STATE_BINDING_TOPOLOGY_DIGEST): return False
    if tuple(x.observation_digest for x in binding.observations) != EXPECTED_OBSERVATION_DIGESTS: return False
    if any(x.before_snapshot_digest != EXPECTED_SNAPSHOT_DIGEST
           or x.after_snapshot_digest != EXPECTED_SNAPSHOT_DIGEST for x in binding.observations): return False
    return all(verify_isolated_failure_containment_record(x) for x in batch.records) and all(
        verify_failure_response_suppression_decision(o.suppression_decision, r)
        and verify_failure_state_snapshot(o.before_snapshot)
        and verify_failure_state_snapshot(o.after_snapshot)
        and verify_failure_response_state_containment_observation(o, r)
        for o, r in zip(binding.observations, batch.records))


def _scenario_material(batch: IsolatedFailureContainmentBatch,
                       binding: FailureResponseStateContainmentBinding, index: int):
    records = batch.records
    observations = binding.observations
    record_digests = tuple(x.record_digest for x in records)
    observation_digests = tuple(x.observation_digest for x in observations)
    if index == 0: return ((batch.scope, binding.scope), (batch.batch_digest, binding.binding_digest), True)
    if index in (1, 2, 3):
        position = index - 1
        return ((records[position].scenario_id,), (records[position].record_digest,), True)
    if index in (4, 5, 6, 7, 8): return (("DENIAL_AND_DOWNSTREAM_SUPPRESSION",), record_digests, True)
    if index in (9, 10, 11): return (("RESPONSE_SUPPRESSION",), observation_digests, True)
    if index in (12, 13): return (("FIXED_STATE_CONTAINMENT",), observation_digests, True)
    if index in (14, 15): return (("ZERO_SIDE_EFFECT_ACCOUNTING",), (binding.binding_digest,), True)
    if index == 16: return (("PRODUCTION_EMPTY_CONFIGURATION_DEFAULT_DENY",),
        (PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION.source_digest,), True)
    if index == 17: return (("ALL_AUTHORITY_FIELDS_FALSE",), (binding.binding_digest,), True)
    if index == 18: return (COVERED_BOUNDARIES, record_digests + observation_digests, True)
    if index == 19: return (UNCOVERED_BOUNDARIES, (), False)
    return (("DEPLOYMENT_AND_ROLLBACK_REMAIN_UNATTESTED",), (), False)


def _scenario(batch: IsolatedFailureContainmentBatch,
              binding: FailureResponseStateContainmentBinding, index: int):
    identities, digests, covered = _scenario_material(batch, binding, index)
    draft = ProductionFailureContainmentScenario(
        SCENARIO_ORDER[index], index + 1, tuple(identities), tuple(digests), covered, True)
    return replace(draft, scenario_digest=_digest("SCENARIO", _without(draft, "scenario_digest")))


def _observation(batch: IsolatedFailureContainmentBatch,
                 binding: FailureResponseStateContainmentBinding, index: int):
    record, state = batch.records[index], binding.observations[index]
    draft = ProductionFailureContainmentObservation(
        record.scenario_id, state.observation_digest, (record.scenario_id,),
        (record.record_digest,), (record.input_binding.operation_identity,),
        (record.input_binding.operation_version,), (record.input_binding.input_material_digest,),
        (record.outcome.output_digest,), (record.topology_digest,), (record.outcome.status,),
        record.outcome.reason_codes, (record.outcome.classification,), True)
    return replace(draft, observation_digest=_digest(
        "ACCEPTANCE_OBSERVATION", _without(draft, "observation_digest")))


def _build_report(batch: IsolatedFailureContainmentBatch,
                  binding: FailureResponseStateContainmentBinding):
    records, state = batch.records, binding.observations
    scenarios = tuple(_scenario(batch, binding, i) for i in range(len(SCENARIO_ORDER)))
    observations = tuple(_observation(batch, binding, i) for i in range(3))
    config = PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    configured = exact_production_feature_gate_lookup(config, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    evaluation_identity = (
        f"brain.production_feature_gate_owner:{PRODUCTION_FEATURE_GATE_OWNER_VERSION}:"
        f"{LIMITED_COST_RESPONSE_RUNTIME_BRIDGE}:{GATE_MISSING_DEFAULT_DENY}:READ_ONLY_DERIVATION"
    )
    evaluation_digest = _digest("PRODUCTION_DEFAULT_DENY_EVALUATION", (
        config.source_digest, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, configured,
        False, True, GATE_MISSING_DEFAULT_DENY))
    topology = _digest("REPORT_TOPOLOGY", (
        batch.batch_digest, binding.binding_digest,
        tuple(x.scenario_digest for x in scenarios),
        tuple(x.observation_digest for x in observations),
        config.source_digest, evaluation_digest, COVERED_BOUNDARIES, UNCOVERED_BOUNDARIES))
    draft = ProductionFailureContainmentAcceptanceReport(
        VERSION, SCOPE, REQUIREMENT, STATUS, DIAGNOSTIC,
        batch, binding,
        batch.version, batch.scope, batch.status, batch.batch_digest, batch.topology_digest,
        tuple(x.scenario_id for x in records), tuple(x.record_digest for x in records),
        binding.version, binding.scope, binding.status, binding.binding_digest,
        binding.topology_digest, tuple(x.suppression_decision_digest for x in state),
        tuple(x.observation_digest for x in state),
        tuple(x.before_snapshot_digest for x in state),
        tuple(x.after_snapshot_digest for x in state),
        f"brain.production_feature_gate_owner:{config.configuration_version}:{config.trusted_source_identity}",
        config.source_digest, evaluation_identity, evaluation_digest, config.gate_entries,
        False, False, True, scenarios, observations, COVERED_BOUNDARIES,
        UNCOVERED_BOUNDARIES, EVIDENCE_TOPOLOGY, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0,
        True, True, True, True, True, None, None, None, None, True, True,
        ProductionFailureContainmentAuthorityBoundary(), topology)
    return replace(draft, report_digest=_digest("REPORT", _without(draft, "report_digest")))


def create_production_failure_containment_acceptance_report(
    failure_batch: Any, state_binding: Any,
) -> ProductionFailureContainmentAcceptanceReport | None:
    """Create a conclusion from exact embedded evidence; no operation is invoked."""
    try:
        if not _exact_foundations(failure_batch, state_binding): return None
        if not verify_production_feature_gate_configuration(
                PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION): return None
        if exact_production_feature_gate_lookup(
                PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
                LIMITED_COST_RESPONSE_RUNTIME_BRIDGE) is not None: return None
        return _build_report(failure_batch, state_binding)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_production_failure_containment_observation(
    value: Any, failure_batch: Any, state_binding: Any,
) -> bool:
    """Pure verification over embedded artifacts; denial operations never rerun."""
    try:
        if not _exact_foundations(failure_batch, state_binding): return False
        if type(value) is not ProductionFailureContainmentObservation: return False
        matches = [i for i, item in enumerate(failure_batch.records)
                   if item.scenario_id == value.scenario_id]
        return len(matches) == 1 and value == _observation(
            failure_batch, state_binding, matches[0])
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def verify_production_failure_containment_acceptance_report(value: Any) -> bool:
    """Strictly reconstruct the report without reinvoking any operational path."""
    try:
        if type(value) is not ProductionFailureContainmentAcceptanceReport: return False
        if not _authority_valid(value.authority_boundary): return False
        if value.deployment_attestation is not None or value.rollback_attestation is not None: return False
        if value.source_sha_attestation is not None or value.deployed_sha_attestation is not None: return False
        if tuple(x.scenario_id for x in value.scenarios) != SCENARIO_ORDER: return False
        if tuple(x.ordinal for x in value.scenarios) != tuple(range(1, 22)): return False
        if len({x.scenario_id for x in value.scenarios}) != 21: return False
        if not all(type(x) is ProductionFailureContainmentScenario and x.verified is True
                   for x in value.scenarios): return False
        if not all(type(x) is ProductionFailureContainmentObservation
                   for x in value.observations): return False
        if (value.covered_boundaries, value.uncovered_boundaries,
                value.evidence_topology) != (COVERED_BOUNDARIES, UNCOVERED_BOUNDARIES,
                EVIDENCE_TOPOLOGY): return False
        if (value.isolated_bridge_denial_invocations,
                value.isolated_admission_denial_invocations,
                value.executor_calculator_failure_invocations,
                value.controlled_runtime_invocations,
                value.response_candidate_attempts, value.final_resolution_attempts,
                value.response_commit_attempts, value.mutation_count,
                value.persistence_count, value.production_invocation_count) != (
                2, 1, 0, 0, 0, 0, 0, 0, 0, 0): return False
        if not all((value.response_candidate_absent, value.final_resolution_absent,
                    value.response_commit_absent, value.state_unchanged,
                    value.object_alias_isolated, value.qualified, value.accepted)): return False
        if not _exact_foundations(value.failure_batch, value.state_binding): return False
        if not all(verify_production_failure_containment_observation(
                item, value.failure_batch, value.state_binding)
                for item in value.observations): return False
        expected = _build_report(value.failure_batch, value.state_binding)
        return value == expected and value.report_digest == _digest(
            "REPORT", _without(value, "report_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


__all__ = (
    "VERSION", "SCOPE", "REQUIREMENT", "STATUS", "DIAGNOSTIC",
    "SCENARIO_ORDER", "COVERED_BOUNDARIES", "UNCOVERED_BOUNDARIES", "EVIDENCE_TOPOLOGY",
    "ProductionFailureContainmentScenario", "ProductionFailureContainmentObservation",
    "ProductionFailureContainmentAcceptanceReport",
    "ProductionFailureContainmentAuthorityBoundary",
    "create_production_failure_containment_acceptance_report",
    "verify_production_failure_containment_observation",
    "verify_production_failure_containment_acceptance_report",
)
