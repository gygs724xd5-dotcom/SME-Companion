from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.production_failure_containment_acceptance as owner
from brain.immutable_failure_response_state_containment import (
    create_failure_response_state_containment_binding,
)
from test_v5152474151_verifiable_isolated_failure_containment_record import batch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_failure_containment_acceptance.py"


@pytest.fixture(scope="module")
def foundations():
    failure_batch = batch()
    state_binding = create_failure_response_state_containment_binding(failure_batch)
    return failure_batch, state_binding


@pytest.fixture(scope="module")
def report(foundations):
    value = owner.create_production_failure_containment_acceptance_report(*foundations)
    assert owner.verify_production_failure_containment_acceptance_report(value)
    return value


def test_exact_foundations_and_independent_acceptance_result(report):
    assert report.requirement == "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED"
    assert report.status == "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED"
    assert report.qualified is report.accepted is True
    assert report.diagnostic == (
        "CANONICAL_ISOLATED_FAILURE_AND_STATE_CONTAINMENT_ACCEPTED_WITHOUT_"
        "PRODUCTION_ACTIVATION_DEPLOYMENT_OR_ROLLBACK_ATTESTATION")
    assert report.foundation_batch_digest == owner.FOUNDATION_BATCH_DIGEST
    assert report.foundation_topology_digest == owner.FOUNDATION_TOPOLOGY_DIGEST
    assert report.state_binding_digest == owner.EXPECTED_STATE_BINDING_DIGEST
    assert report.state_binding_topology_digest == owner.EXPECTED_STATE_BINDING_TOPOLOGY_DIGEST


def test_exact_state_observation_snapshot_and_suppression_digests(report):
    assert report.state_observation_digests == owner.EXPECTED_OBSERVATION_DIGESTS
    assert report.before_snapshot_digests == (owner.EXPECTED_SNAPSHOT_DIGEST,) * 3
    assert report.after_snapshot_digests == (owner.EXPECTED_SNAPSHOT_DIGEST,) * 3
    assert report.suppression_decision_digests == tuple(
        x.suppression_decision_digest for x in report.state_binding.observations)


def test_fixed_ordered_unique_scenarios_and_topology(report):
    assert tuple(x.scenario_id for x in report.scenarios) == owner.SCENARIO_ORDER
    assert tuple(x.ordinal for x in report.scenarios) == tuple(range(1, 22))
    assert len(set(owner.SCENARIO_ORDER)) == 21
    assert all(x.verified for x in report.scenarios)
    assert report.evidence_topology == owner.EVIDENCE_TOPOLOGY


def test_actual_denial_invocations_and_strict_observations(report):
    assert (report.isolated_bridge_denial_invocations,
        report.isolated_admission_denial_invocations) == (2, 1)
    assert tuple(x.scenario_id for x in report.observations) == tuple(
        x.scenario_id for x in report.failure_batch.records)
    assert all(owner.verify_production_failure_containment_observation(
        observation, report.failure_batch, report.state_binding)
        for observation in report.observations)
    assert report.observations[0].denial_statuses == ("RUNTIME_HANDOFF_DENIED",)
    assert report.observations[1].denial_statuses == ("RUNTIME_HANDOFF_DENIED",)
    assert report.observations[2].denial_statuses == ("ADMISSION_DENIED",)


def test_boundary_diversity_and_success_artifacts_excluded(report):
    assert report.record_ids[:2] == owner.BRIDGE_SCENARIOS
    assert report.record_ids[2] == owner.ADMISSION_SCENARIO
    assert tuple(x.operation_identities[0] for x in report.observations) == tuple(
        x.input_binding.operation_identity for x in report.failure_batch.records)
    assert all(not x.output_artifact.handoff for x in report.failure_batch.records[:2])
    assert report.failure_batch.records[2].output_artifact.executable_output is None


def test_downstream_response_and_state_suppression(report):
    assert (report.executor_calculator_failure_invocations,
        report.controlled_runtime_invocations, report.response_candidate_attempts,
        report.final_resolution_attempts, report.response_commit_attempts,
        report.mutation_count, report.persistence_count) == (0,) * 7
    assert report.response_candidate_absent
    assert report.final_resolution_absent
    assert report.response_commit_absent
    assert report.state_unchanged and report.object_alias_isolated
    for value in report.state_binding.observations:
        assert (value.response_candidate, value.final_resolution, value.response_commit,
            value.runtime_result, value.delivery_artifact) == (None,) * 5
        assert value.before_snapshot == value.after_snapshot
        assert value.before_snapshot is not value.after_snapshot


def test_production_default_deny_isolation_without_activation(report):
    assert report.production_gate_entries == ()
    assert not report.production_configured and not report.production_effective
    assert report.production_default_denied
    assert report.production_invocation_count == 0
    assert "GATE_MISSING_DEFAULT_DENY" in report.production_evaluation_identity
    assert report.production_configuration_digest == (
        owner.PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION.source_digest)


def test_scope_honesty_covered_and_uncovered_disclosures(report):
    assert report.covered_boundaries == owner.COVERED_BOUNDARIES
    assert report.uncovered_boundaries == owner.UNCOVERED_BOUNDARIES
    assert "ACTUAL_EXECUTOR_OR_CALCULATOR_FAILURE" in report.uncovered_boundaries
    assert "DEPLOYED_PRODUCTION_INCIDENT" in report.uncovered_boundaries
    assert report.deployment_attestation is None
    assert report.rollback_attestation is None
    assert report.source_sha_attestation is None
    assert report.deployed_sha_attestation is None


def test_authority_boundary_all_false_and_acceptance_is_not_permission(report):
    assert all(getattr(report.authority_boundary, name) is False
        for name in report.authority_boundary.__dataclass_fields__)


@pytest.mark.parametrize("value", ({}, True, "accepted", object(), None))
def test_wrong_report_concrete_type_fails_closed(value):
    assert not owner.verify_production_failure_containment_acceptance_report(value)


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"), ("requirement", "FORGED"),
    ("status", "NOT_ACCEPTED"), ("diagnostic", "DEPLOYED_INCIDENT_ACCEPTED"),
    ("qualified", False), ("accepted", False),
    ("topology_digest", "0" * 64), ("report_digest", "0" * 64),
))
def test_report_identity_decision_and_digest_tampering_fails_closed(report, field, value):
    assert not owner.verify_production_failure_containment_acceptance_report(
        dataclasses.replace(report, **{field: value}))


@pytest.mark.parametrize("field,value", (
    ("isolated_bridge_denial_invocations", 3),
    ("isolated_admission_denial_invocations", 2),
    ("executor_calculator_failure_invocations", 1),
    ("controlled_runtime_invocations", 1),
    ("response_candidate_attempts", 1), ("final_resolution_attempts", 1),
    ("response_commit_attempts", 1), ("mutation_count", 1),
    ("persistence_count", 1), ("production_invocation_count", 1),
))
def test_forged_invocation_attempt_mutation_and_persistence_counts_fail_closed(report, field, value):
    assert not owner.verify_production_failure_containment_acceptance_report(
        dataclasses.replace(report, **{field: value}))


@pytest.mark.parametrize("field", (
    "response_candidate_absent", "final_resolution_absent", "response_commit_absent",
    "state_unchanged", "object_alias_isolated",
))
def test_containment_flag_forgery_fails_closed(report, field):
    assert not owner.verify_production_failure_containment_acceptance_report(
        dataclasses.replace(report, **{field: False}))


@pytest.mark.parametrize("field,value", (
    ("production_gate_entries", ((owner.LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),)),
    ("production_configured", True), ("production_effective", True),
    ("production_default_denied", False),
    ("production_configuration_digest", "0" * 64),
    ("production_evaluation_identity", "GATE_CONFIGURED_ENABLED"),
    ("production_evaluation_digest", "0" * 64),
))
def test_production_configuration_and_default_deny_tampering_fails_closed(report, field, value):
    assert not owner.verify_production_failure_containment_acceptance_report(
        dataclasses.replace(report, **{field: value}))


@pytest.mark.parametrize("field", (
    "deployment_attestation", "rollback_attestation",
    "source_sha_attestation", "deployed_sha_attestation",
))
def test_source_deployment_and_rollback_claim_injection_fails_closed(report, field):
    assert not owner.verify_production_failure_containment_acceptance_report(
        dataclasses.replace(report, **{field: object()}))


def test_scenario_reorder_drop_duplicate_unknown_and_disclosure_tampering_fail_closed(report):
    scenarios = report.scenarios
    variants = (
        scenarios[::-1], scenarios[:-1], (scenarios[0],) * 21,
        (dataclasses.replace(scenarios[0], scenario_id="UNKNOWN"),) + scenarios[1:],
        (dataclasses.replace(scenarios[0], scenario_digest="0" * 64),) + scenarios[1:],
    )
    for value in variants:
        assert not owner.verify_production_failure_containment_acceptance_report(
            dataclasses.replace(report, scenarios=value))
    assert not owner.verify_production_failure_containment_acceptance_report(
        dataclasses.replace(report, covered_boundaries=report.covered_boundaries[::-1]))
    assert not owner.verify_production_failure_containment_acceptance_report(
        dataclasses.replace(report, uncovered_boundaries=report.uncovered_boundaries[:-1]))


@pytest.mark.parametrize("field,value", (
    ("operation_identities", ("forged.operation",)),
    ("operation_versions", ("0",)), ("input_digests", ("0" * 64,)),
    ("output_digests", ("0" * 64,)), ("topology_digests", ("0" * 64,)),
    ("denial_statuses", ("SUCCEEDED",)), ("denial_reasons", ("FORGED",)),
    ("invocation_classifications", ("SUCCESS",)), ("verified", False),
    ("observation_digest", "0" * 64),
))
def test_observation_operation_status_reason_classification_and_digest_tampering(
        report, field, value):
    changed = dataclasses.replace(report.observations[0], **{field: value})
    forged = dataclasses.replace(report, observations=(changed,) + report.observations[1:])
    assert not owner.verify_production_failure_containment_acceptance_report(forged)


def test_cross_skill_record_and_state_observation_substitution_fails_closed(report):
    first, second = report.failure_batch.records[:2]
    records = (dataclasses.replace(first, output_artifact=second.output_artifact),) + report.failure_batch.records[1:]
    forged_batch = dataclasses.replace(report.failure_batch, records=records)
    assert owner.create_production_failure_containment_acceptance_report(
        forged_batch, report.state_binding) is None
    states = (report.state_binding.observations[1], report.state_binding.observations[0],
        report.state_binding.observations[2])
    forged_binding = dataclasses.replace(report.state_binding, observations=states)
    assert owner.create_production_failure_containment_acceptance_report(
        report.failure_batch, forged_binding) is None


def test_nested_foundation_binding_snapshot_alias_and_response_injection_rejected(report):
    forged_batch = dataclasses.replace(report.failure_batch, batch_digest="0" * 64)
    assert owner.create_production_failure_containment_acceptance_report(
        forged_batch, report.state_binding) is None
    first = report.state_binding.observations[0]
    forged_observation = dataclasses.replace(first, response_candidate=object())
    forged_binding = dataclasses.replace(report.state_binding,
        observations=(forged_observation,) + report.state_binding.observations[1:])
    assert owner.create_production_failure_containment_acceptance_report(
        report.failure_batch, forged_binding) is None
    alias = dataclasses.replace(first, after_snapshot=first.before_snapshot)
    alias_binding = dataclasses.replace(report.state_binding,
        observations=(alias,) + report.state_binding.observations[1:])
    assert owner.create_production_failure_containment_acceptance_report(
        report.failure_batch, alias_binding) is None


def test_authority_permission_injection_fails_closed(report):
    for name in owner.ProductionFailureContainmentAuthorityBoundary.__dataclass_fields__:
        boundary = dataclasses.replace(report.authority_boundary, **{name: True})
        assert not owner.verify_production_failure_containment_acceptance_report(
            dataclasses.replace(report, authority_boundary=boundary))


def test_verifiers_remain_pure_when_operational_entry_points_raise(monkeypatch, report):
    import brain.verifiable_isolated_failure_containment_record as foundation
    import brain.immutable_failure_response_state_containment as state
    monkeypatch.setattr(foundation, "bridge_prepared_cost_response",
        lambda *a, **k: pytest.fail("bridge reinvoked"))
    monkeypatch.setattr(foundation, "decide_controlled_runtime_integration_admission",
        lambda *a, **k: pytest.fail("admission reinvoked"))
    monkeypatch.setattr(state, "_evaluate", lambda *a, **k: pytest.fail("state rerun"))
    assert owner.verify_production_failure_containment_acceptance_report(report)


def test_approval_remains_eight_of_ten_with_same_primary_denial():
    from test_v515247415_controlled_runtime_approval_binding import artifacts
    from brain.production_feature_gate_controlled_runtime_approval_binding import (
        evaluate_production_feature_gate_controlled_runtime_bound_approval,
        verify_production_feature_gate_controlled_runtime_bound_decision,
    )
    decision = evaluate_production_feature_gate_controlled_runtime_bound_approval(artifacts()[3])
    assert verify_production_feature_gate_controlled_runtime_bound_decision(decision)
    assert (decision.verified_requirement_count, decision.missing_requirement_count) == (8, 2)
    assert decision.status == "TRANSITION_NOT_APPROVED"
    assert decision.primary_denial == "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED"
    assert not any((decision.transition_approved, decision.application_permitted,
        decision.activation_permitted, decision.transition_applied))


def test_frozen_contracts_narrow_public_api_and_no_caller_outcomes():
    contracts = (owner.ProductionFailureContainmentScenario,
        owner.ProductionFailureContainmentObservation,
        owner.ProductionFailureContainmentAcceptanceReport,
        owner.ProductionFailureContainmentAuthorityBoundary)
    assert all(value.__dataclass_params__.frozen for value in contracts)
    assert tuple(inspect.signature(
        owner.create_production_failure_containment_acceptance_report).parameters) == (
        "failure_batch", "state_binding")
    assert tuple(inspect.signature(
        owner.verify_production_failure_containment_observation).parameters) == (
        "value", "failure_batch", "state_binding")
    assert tuple(inspect.signature(
        owner.verify_production_failure_containment_acceptance_report).parameters) == ("value",)


def test_static_no_app_environment_file_network_subprocess_session_or_operations():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {"app", "os", "pathlib", "socket", "subprocess", "requests", "urllib",
        "streamlit"}.isdisjoint(imported)
    for forbidden in ("session_state", "open(", "os.environ", "subprocess",
            "bridge_prepared_cost_response(", "decide_controlled_runtime_integration_admission(",
            "create_production_response_candidate(", "create_production_final_response_resolution(",
            "create_production_turn_commit_receipt(", "commit_response_boundary("):
        assert forbidden not in source
    assert not any(name.startswith(("invoke_", "execute_", "apply_", "approve_",
        "activate_", "dispatch_", "deliver_", "commit_")) for name in vars(owner))


def test_wrong_foundation_and_binding_types_fail_closed(foundations):
    failure_batch, state_binding = foundations
    assert owner.create_production_failure_containment_acceptance_report({}, state_binding) is None
    assert owner.create_production_failure_containment_acceptance_report(failure_batch, {}) is None
    assert not owner.verify_production_failure_containment_observation({}, failure_batch, state_binding)
