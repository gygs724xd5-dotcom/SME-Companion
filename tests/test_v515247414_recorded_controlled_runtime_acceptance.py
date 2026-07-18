"""V5.15.24.7.4.14 recorded controlled-runtime acceptance review."""
from dataclasses import fields, is_dataclass, replace
import ast
import inspect
from pathlib import Path

import pytest

import brain.recorded_controlled_runtime_acceptance as owner
from brain.bridge_record_runtime_manifest_binding import create_bridge_record_runtime_manifest_binding
from brain.verifiable_isolated_admission_invocation_record import create_isolated_admission_invocation_batch
from brain.verifiable_isolated_bridge_invocation_record import create_isolated_bridge_invocation_batch
from brain.versioned_controlled_runtime_admission_request_binding import (
    create_versioned_controlled_runtime_admission_request_bindings,
)
from test_v5152474133_execution_result_runtime_bridge_request_binding import _batch as execution_batch


@pytest.fixture(scope="module")
def canonical_batch():
    manifest = create_bridge_record_runtime_manifest_binding(
        create_isolated_bridge_invocation_batch(execution_batch()))
    bindings = create_versioned_controlled_runtime_admission_request_bindings(manifest)
    return create_isolated_admission_invocation_batch(bindings)


@pytest.fixture(scope="module")
def report(canonical_batch):
    return owner.create_recorded_controlled_runtime_acceptance_report(canonical_batch)


def test_canonical_report_strictly_verifies(report):
    assert owner.verify_recorded_controlled_runtime_acceptance_report(report)


def test_exact_acceptance_semantics_and_diagnostic(report):
    assert (report.requirement, report.status, report.qualified, report.accepted) == (
        owner.REQUIREMENT, owner.REQUIREMENT, True, True)
    assert report.diagnostic == owner.DIAGNOSTIC
    assert "WITHOUT_SEPARATE_RUNTIME_ENTRY_POINT" in report.diagnostic


def test_fixed_ordered_unique_scenario_matrix(report):
    assert tuple(x.scenario_id for x in report.scenarios) == owner.SCENARIO_IDS
    assert len(report.scenarios) == len(set(owner.SCENARIO_IDS)) == 18
    assert tuple(x.ordinal for x in report.scenarios) == tuple(range(1, 19))
    assert len(report.observations) == 18 and all(x.passed for x in report.observations)


def test_exact_record_derived_invocation_accounting(report):
    assert (report.isolated_execution_invocations, report.isolated_calculator_invocations,
        report.isolated_bridge_invocations, report.isolated_admission_invocations,
        report.separate_controlled_runtime_invocations) == (2, 2, 2, 2, 0)
    assert (report.production_execution_invocations, report.production_calculator_invocations,
        report.production_bridge_invocations, report.production_admission_invocations,
        report.production_runtime_invocations, report.production_delivery_invocations,
        report.production_response_commits) == (0,) * 7
    assert report.separate_controlled_runtime_invocations == report.source_batch.isolated_runtime_invocations


def test_full_exact_topology_and_digest_ancestry_are_bound(report):
    assert report.topology == owner.TOPOLOGY
    for observation in report.observations:
        assert len(observation.source_request_digests) == 2
        assert len(observation.execution_record_digests) == 2
        assert len(observation.bridge_record_digests) == 2
        assert len(observation.admission_record_digests) == 2
        assert len(observation.upstream_topology_digests) == 8


def test_underlying_requests_and_authority_remain_default_denied(report):
    execution = (report.source_batch.records[0].input_binding.source_binding
        .source_manifest_binding.source_batch.source_binding_batch.source_invocation_batch.records)
    for record in execution:
        request = record.source_request
        assert not any((request.requirement_qualified, request.execute_allowed,
            request.dispatch_permitted, request.application_permitted,
            request.activation_permitted, request.runtime_invocation_permitted))
        assert request.execution_result is None
    assert not any(getattr(report.authority_boundary, f.name) for f in fields(report.authority_boundary))


@pytest.mark.parametrize("field,value", (
    ("qualified", False), ("accepted", False), ("status", "FORGED"),
    ("diagnostic", "FORGED"), ("isolated_execution_invocations", 99),
    ("isolated_admission_invocations", 1), ("separate_controlled_runtime_invocations", 2),
    ("production_runtime_invocations", 1), ("topology_digest", "0" * 64),
    ("report_digest", "0" * 64),
))
def test_forged_outcomes_counts_status_diagnostic_and_digests_fail_closed(report, field, value):
    assert not owner.verify_recorded_controlled_runtime_acceptance_report(
        replace(report, **{field: value}))


def test_missing_reordered_duplicate_skills_and_scenarios_fail_closed(report):
    assert not owner.verify_recorded_controlled_runtime_acceptance_report(
        replace(report, scenarios=report.scenarios[:-1]))
    assert not owner.verify_recorded_controlled_runtime_acceptance_report(
        replace(report, scenarios=tuple(reversed(report.scenarios))))
    assert not owner.verify_recorded_controlled_runtime_acceptance_report(
        replace(report, scenarios=(report.scenarios[0],) + report.scenarios[1:-1] + (report.scenarios[0],)))
    assert owner.create_recorded_controlled_runtime_acceptance_report(object()) is None


def test_cross_skill_and_cross_stage_substitution_fail_closed(report):
    first, second = report.source_batch.records
    bad_record = replace(first, input_binding=second.input_binding)
    bad_batch = replace(report.source_batch, records=(bad_record, second))
    assert owner.create_recorded_controlled_runtime_acceptance_report(bad_batch) is None
    changed = replace(report.observations[0], bridge_record_digests=tuple(reversed(
        report.observations[0].bridge_record_digests)))
    assert not owner.verify_recorded_controlled_runtime_observation(changed, report.source_batch)


@pytest.mark.parametrize("field", (
    "source_request_digests", "turn_digests", "reference_time_digests",
    "configuration_digests", "evaluation_digests", "execution_result_digests",
    "execution_integrity_digests", "bridge_request_digests", "bridge_result_digests",
    "bridge_handoff_digests", "delivery_qualification_digests",
    "historical_qualification_digests", "admission_request_material_digests",
    "admission_binding_digests", "admission_decision_digests", "upstream_topology_digests",
))
def test_observation_continuity_tampering_fails_closed(report, field):
    observation = report.observations[0]
    original = getattr(observation, field)
    changed = ("0" * 64,) + tuple(original[1:])
    assert not owner.verify_recorded_controlled_runtime_observation(
        replace(observation, **{field: changed}), report.source_batch)


def test_runtime_result_permission_and_authority_injection_fail_closed(report):
    boundary = replace(report.authority_boundary, runtime=True)
    assert not owner.verify_recorded_controlled_runtime_acceptance_report(
        replace(report, authority_boundary=boundary))
    first, second = report.source_batch.records
    bad_batch = replace(report.source_batch, records=(replace(first, runtime_result=object()), second))
    assert owner.create_recorded_controlled_runtime_acceptance_report(bad_batch) is None


def test_verifiers_are_pure_and_do_not_reinvoke_executor_bridge_or_gateway(report, monkeypatch):
    import brain.verifiable_isolated_runtime_invocation_record as execution
    import brain.verifiable_isolated_bridge_invocation_record as bridge
    import brain.verifiable_isolated_admission_invocation_record as admission
    monkeypatch.setattr(execution, "execute_cost_skill", lambda *a, **k: pytest.fail("executor invoked"))
    monkeypatch.setattr(bridge, "bridge_prepared_cost_response", lambda *a, **k: pytest.fail("bridge invoked"))
    monkeypatch.setattr(admission._gateway, "decide_controlled_runtime_integration_admission",
        lambda *a, **k: pytest.fail("admission gateway invoked"))
    assert owner.verify_recorded_controlled_runtime_acceptance_report(report)


def test_public_api_has_no_caller_outcome_authority_mode_or_count_parameters():
    assert tuple(inspect.signature(owner.create_recorded_controlled_runtime_acceptance_report).parameters) == ("source",)
    assert tuple(inspect.signature(owner.verify_recorded_controlled_runtime_observation).parameters) == ("value", "source")
    assert tuple(inspect.signature(owner.verify_recorded_controlled_runtime_acceptance_report).parameters) == ("value",)
    forbidden = {"pass", "accepted", "trusted", "approval", "mode", "purpose", "permission", "count"}
    assert all(forbidden.isdisjoint(inspect.signature(fn).parameters) for fn in (
        owner.create_recorded_controlled_runtime_acceptance_report,
        owner.verify_recorded_controlled_runtime_observation,
        owner.verify_recorded_controlled_runtime_acceptance_report))


def test_contracts_frozen_and_module_has_no_invocation_or_production_api(report):
    assert all(getattr(type(x), "__dataclass_params__").frozen for x in (
        report, report.scenarios[0], report.observations[0], report.authority_boundary))
    public = set(owner.__all__)
    assert not any(word in name for name in public for word in (
        "invoke", "execute", "apply", "approve", "activate", "dispatch", "deliver"))


def test_static_isolation_has_no_app_environment_file_network_subprocess_or_response_path():
    path = Path(owner.__file__)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    forbidden_imports = {"app", "os", "pathlib", "socket", "subprocess", "requests", "urllib", "streamlit"}
    assert forbidden_imports.isdisjoint(imported)
    assert not any(token in source for token in (
        "session_state", "open(", "Path(", "response_commit(", "decide_controlled_runtime_integration_admission(",
        "bridge_prepared_cost_response(", "execute_cost_skill("))
