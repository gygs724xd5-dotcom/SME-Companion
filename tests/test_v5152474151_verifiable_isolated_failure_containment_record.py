from __future__ import annotations

import ast
import dataclasses
import inspect
from functools import lru_cache
from pathlib import Path

import pytest

import brain.verifiable_isolated_failure_containment_record as owner
from brain.bridge_record_runtime_manifest_binding import create_bridge_record_runtime_manifest_binding
from brain.verifiable_isolated_bridge_invocation_record import create_isolated_bridge_invocation_batch
from brain.versioned_controlled_runtime_admission_request_binding import (
    create_versioned_controlled_runtime_admission_request_bindings,
)
from test_v5152474133_execution_result_runtime_bridge_request_binding import _batch as bridge_requests


@lru_cache(maxsize=1)
def sources():
    bridge = bridge_requests()
    manifest = create_bridge_record_runtime_manifest_binding(
        create_isolated_bridge_invocation_batch(bridge))
    admission = create_versioned_controlled_runtime_admission_request_bindings(manifest)
    return bridge, admission


@lru_cache(maxsize=1)
def batch():
    return owner.create_isolated_failure_containment_batch(*sources())


def test_fixed_inventory_actual_denial_invocations_and_not_accepted():
    value = batch()
    assert owner.verify_isolated_failure_containment_batch(value)
    assert value.status == "FAILURE_CONTAINMENT_FOUNDATION_RECORDED_NOT_ACCEPTED"
    assert value.scenario_order == owner.SCENARIO_ORDER
    assert (value.isolated_bridge_invocations, value.isolated_admission_invocations) == (2, 1)
    assert value.production_invocation_count == value.verifier_rejection_invocations == 0
    assert not any((value.artifact_validity_claim, value.requirement_qualified,
        value.containment_accepted, value.production_failure_containment_accepted,
        value.approval_evidence_permitted, value.state_containment_verified))
    assert value.state_containment_status == "STATE_CONTAINMENT_NOT_YET_BOUND"


def test_bridge_records_bind_real_denials_and_suppress_downstream():
    for record in batch().records[:2]:
        assert record.outcome.classification == "ACTUAL_CANONICAL_DENIAL_INVOCATION"
        assert record.outcome.status == "RUNTIME_HANDOFF_DENIED"
        assert record.outcome.reason_codes == owner.BRIDGE_DENIAL_REASONS
        assert record.output_artifact.handoff is None
        assert record.outcome.invocation_attempted and record.outcome.invocation_completed
        assert not record.outcome.success and record.outcome.downstream_invocation_count == 0
        assert record.outcome.downstream_artifact_digests == ()


def test_admission_record_binds_real_denial_and_no_runtime_output():
    record = batch().records[2]
    decision = record.output_artifact
    assert record.outcome.classification == "ACTUAL_CANONICAL_DENIAL_INVOCATION"
    assert decision.primary_denial_code == "UNSUPPORTED_OR_MALFORMED_SKILL_ID"
    assert not decision.admitted and decision.executable_output is None
    assert record.outcome.downstream_invocation_count == 0


def test_per_record_input_output_topology_and_record_digests_are_distinct():
    records = batch().records
    assert len({x.input_binding.input_material_digest for x in records}) == 3
    assert len({x.outcome.output_digest for x in records}) == 3
    assert len({x.topology_digest for x in records}) == 3
    assert len({x.record_digest for x in records}) == 3
    assert all(owner.verify_isolated_failure_containment_record(x) for x in records)


@pytest.mark.parametrize("field,value", (
    ("scenario_id", "UNKNOWN"), ("boundary_identity", "OTHER"),
    ("skill_id", "other"), ("topology_digest", "0" * 64),
    ("record_digest", "0" * 64), ("production_invocation_count", 1),
    ("isolated_bridge_invocations", 9), ("isolated_admission_invocations", 9),
))
def test_record_identity_count_and_digest_tampering_fails_closed(field, value):
    assert not owner.verify_isolated_failure_containment_record(
        dataclasses.replace(batch().records[0], **{field: value}))


@pytest.mark.parametrize("field,value", (
    ("classification", "STRICT_VERIFIER_REJECTION"), ("status", "SUCCEEDED"),
    ("reason_codes", ("FORGED",)), ("primary_reason", "FORGED"),
    ("output_digest", "0" * 64), ("invocation_attempted", False),
    ("invocation_completed", False), ("success", True),
    ("downstream_artifact_digests", ("0" * 64,)),
    ("downstream_invocation_count", 1), ("mutation_count", 1),
    ("persistence_count", 1), ("response_commit_count", 1),
    ("state_containment_status", "VERIFIED"), ("state_containment_verified", True),
))
def test_outcome_reason_invocation_suppression_state_tampering_fails_closed(field, value):
    record = batch().records[0]
    changed = dataclasses.replace(record.outcome, **{field: value})
    assert not owner.verify_isolated_failure_containment_record(
        dataclasses.replace(record, outcome=changed))


@pytest.mark.parametrize("field,value", (
    ("source_batch_digest", "0" * 64), ("source_record_digest", "0" * 64),
    ("operation_identity", "caller.operation"), ("operation_version", "0"),
    ("input_material_digest", "0" * 64), ("ancestry_digests", ()),
    ("binding_digest", "0" * 64),
))
def test_input_operation_ancestry_digest_tampering_fails_closed(field, value):
    record = batch().records[0]
    changed = dataclasses.replace(record.input_binding, **{field: value})
    assert not owner.verify_isolated_failure_containment_record(
        dataclasses.replace(record, input_binding=changed))


def test_success_artifact_cross_stage_and_cross_skill_substitution_rejected():
    first, second, admission = batch().records
    assert not owner.verify_isolated_failure_containment_record(
        dataclasses.replace(first, output_artifact=second.output_artifact))
    assert not owner.verify_isolated_failure_containment_record(
        dataclasses.replace(first, output_artifact=admission.output_artifact))
    success = sources()[0].bindings[0].execution_result
    assert not owner.verify_isolated_failure_containment_record(
        dataclasses.replace(first, output_artifact=success))


@pytest.mark.parametrize("change", (
    lambda x: dataclasses.replace(x, records=tuple(reversed(x.records))),
    lambda x: dataclasses.replace(x, records=x.records[:-1]),
    lambda x: dataclasses.replace(x, records=(x.records[0],) * 3),
    lambda x: dataclasses.replace(x, scenario_order=tuple(reversed(x.scenario_order))),
    lambda x: dataclasses.replace(x, topology_digest="0" * 64),
    lambda x: dataclasses.replace(x, batch_digest="0" * 64),
    lambda x: dataclasses.replace(x, production_invocation_count=1),
    lambda x: dataclasses.replace(x, containment_accepted=True),
    lambda x: dataclasses.replace(x, requirement_qualified=True),
))
def test_batch_reorder_drop_duplicate_digest_count_and_claim_injection_rejected(change):
    assert not owner.verify_isolated_failure_containment_batch(change(batch()))


def test_authority_permission_and_deployment_rollback_injection_rejected():
    record = batch().records[0]
    for name in owner.IsolatedFailureContainmentAuthorityBoundary.__dataclass_fields__:
        boundary = dataclasses.replace(record.authority_boundary, **{name: True})
        assert not owner.verify_isolated_failure_containment_record(
            dataclasses.replace(record, authority_boundary=boundary))


def test_unexpected_exception_returns_no_synthetic_record(monkeypatch):
    monkeypatch.setattr(owner, "bridge_prepared_cost_response",
        lambda request: (_ for _ in ()).throw(RuntimeError("unexpected")))
    with pytest.raises(RuntimeError, match="unexpected"):
        owner.create_isolated_failure_containment_record(sources()[0], owner.BRIDGE_SCENARIOS[0])


def test_verifiers_are_pure_and_do_not_reinvoke(monkeypatch):
    monkeypatch.setattr(owner, "bridge_prepared_cost_response",
        lambda *a, **k: pytest.fail("bridge reinvoked"))
    monkeypatch.setattr(owner, "decide_controlled_runtime_integration_admission",
        lambda *a, **k: pytest.fail("admission reinvoked"))
    assert all(owner.verify_isolated_failure_containment_record(x) for x in batch().records)
    assert owner.verify_isolated_failure_containment_batch(batch())


def test_frozen_contracts_public_apis_and_no_caller_outcome_parameters():
    contracts = (owner.IsolatedFailureContainmentAuthorityBoundary,
        owner.IsolatedFailureContainmentInputBinding, owner.IsolatedFailureContainmentOutcome,
        owner.IsolatedFailureContainmentRecord, owner.IsolatedFailureContainmentBatch)
    assert all(x.__dataclass_params__.frozen for x in contracts)
    assert tuple(inspect.signature(owner.create_isolated_failure_containment_record).parameters) == (
        "source", "scenario_id")
    assert tuple(inspect.signature(owner.create_isolated_failure_containment_batch).parameters) == (
        "bridge_source", "admission_source")


def test_static_isolation_no_app_environment_file_network_subprocess_or_session_access():
    source = Path(owner.__file__).read_text(encoding="utf-8")
    for forbidden in ("import app", "session_state", "os.environ", "getenv(",
                      "subprocess", "requests.", "socket", "open(", "streamlit"):
        assert forbidden not in source
    tree = ast.parse(source)
    verifier_names = {"verify_isolated_failure_containment_record",
                      "verify_isolated_failure_containment_batch"}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in verifier_names:
            called = {x.func.id for x in ast.walk(node)
                if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)}
            assert not called.intersection({"bridge_prepared_cost_response",
                "decide_controlled_runtime_integration_admission"})


def test_wrong_types_unknown_scenario_and_cross_source_fail_closed():
    assert owner.create_isolated_failure_containment_record({}, owner.BRIDGE_SCENARIOS[0]) is None
    assert owner.create_isolated_failure_containment_record(sources()[0], "UNKNOWN") is None
    assert owner.create_isolated_failure_containment_record(sources()[1], owner.BRIDGE_SCENARIOS[0]) is None
    assert owner.create_isolated_failure_containment_record(sources()[0], owner.ADMISSION_SCENARIO) is None
    assert not owner.verify_isolated_failure_containment_record({})
    assert not owner.verify_isolated_failure_containment_batch({})
