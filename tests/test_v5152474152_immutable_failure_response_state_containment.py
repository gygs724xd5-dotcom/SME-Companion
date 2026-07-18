from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.immutable_failure_response_state_containment as owner
from test_v5152474151_verifiable_isolated_failure_containment_record import batch


@pytest.fixture(scope="module")
def binding():
    return owner.create_failure_response_state_containment_binding(batch())


def test_binding_status_counts_and_foundation_authority_separation(binding):
    assert owner.verify_failure_response_state_containment_binding(binding)
    assert binding.status == "RESPONSE_AND_STATE_CONTAINMENT_BOUND_NOT_ACCEPTED"
    assert (binding.isolated_bridge_denial_invocations,
        binding.isolated_admission_denial_invocations) == (2, 1)
    assert (binding.response_candidate_attempts, binding.final_resolution_attempts,
        binding.response_commit_attempts, binding.mutation_count,
        binding.persistence_count, binding.production_invocation_count) == (0,) * 6
    assert binding.state_containment_bound and binding.state_containment_verified
    assert binding.response_suppression_bound
    assert not any((binding.requirement_qualified, binding.containment_accepted,
        binding.production_failure_containment_accepted,
        binding.approval_evidence_permitted))


def test_exact_foundation_and_ordered_per_record_observations(binding):
    assert binding.source_batch_digest == owner.FOUNDATION_BATCH_DIGEST
    assert binding.source_topology_digest == owner.FOUNDATION_TOPOLOGY_DIGEST
    assert tuple(x.scenario_id for x in binding.observations) == owner.SCENARIO_ORDER
    for observation, record in zip(binding.observations, binding.source_batch.records):
        assert owner.verify_failure_response_state_containment_observation(observation, record)
        assert owner.verify_failure_response_suppression_decision(
            observation.suppression_decision, record)


def test_suppression_absence_state_and_actual_harness_instrumentation(binding):
    for value in binding.observations:
        assert value.suppression_decision.suppress_response
        assert not value.suppression_decision.success
        assert (value.response_candidate, value.final_resolution, value.response_commit,
            value.runtime_result, value.delivery_artifact) == (None,) * 5
        assert value.before_snapshot == value.after_snapshot
        assert value.before_snapshot is not value.after_snapshot
        assert value.state_unchanged and value.object_alias_isolated
        assert (value.response_candidate_attempts, value.final_resolution_attempts,
            value.response_commit_attempts, value.mutation_count,
            value.persistence_count, value.production_invocation_count) == (0,) * 6


@pytest.mark.parametrize("field,value", (
    ("failure_classification", "SUCCESS"), ("outcome_status", "SUCCEEDED"),
    ("success", True), ("suppress_response", False),
    ("response_candidate_count", 1), ("final_resolution_count", 1),
    ("response_commit_count", 1), ("downstream_artifact_digests", ("0" * 64,)),
    ("decision_digest", "0" * 64),
))
def test_suppression_decision_tampering_fails_closed(binding, field, value):
    observation = binding.observations[0]
    changed = dataclasses.replace(observation.suppression_decision, **{field: value})
    assert not owner.verify_failure_response_suppression_decision(
        changed, binding.source_batch.records[0])


@pytest.mark.parametrize("field,value", (
    ("chat_history", ()), ("conversation_memory", ()),
    ("application_conversation", ()), ("last_assistant_reply", "forged"),
    ("recent_assistant_replies", ("forged",)), ("response_commit_count", 5),
    ("unrelated_sentinel_state", ()), ("snapshot_digest", "0" * 64),
))
def test_state_material_and_digest_tampering_fails_closed(binding, field, value):
    changed = dataclasses.replace(binding.observations[0].before_snapshot, **{field: value})
    assert not owner.verify_failure_state_snapshot(changed)


@pytest.mark.parametrize("field,value", (
    ("state_unchanged", False), ("object_alias_isolated", False),
    ("response_candidate", object()), ("final_resolution", object()),
    ("response_commit", object()), ("runtime_result", object()),
    ("delivery_artifact", object()), ("response_candidate_attempts", 1),
    ("final_resolution_attempts", 1), ("response_commit_attempts", 1),
    ("mutation_count", 1), ("persistence_count", 1),
    ("production_invocation_count", 1), ("observation_topology_digest", "0" * 64),
    ("observation_digest", "0" * 64),
))
def test_observation_artifact_count_flag_and_digest_injection_fails_closed(binding, field, value):
    changed = dataclasses.replace(binding.observations[0], **{field: value})
    assert not owner.verify_failure_response_state_containment_observation(
        changed, binding.source_batch.records[0])


def test_after_equals_before_alias_forgery_rejected(binding):
    value = binding.observations[0]
    changed = dataclasses.replace(value, after_snapshot=value.before_snapshot)
    assert not owner.verify_failure_response_state_containment_observation(
        changed, binding.source_batch.records[0])


@pytest.mark.parametrize("change", (
    lambda x: dataclasses.replace(x, observations=tuple(reversed(x.observations))),
    lambda x: dataclasses.replace(x, observations=x.observations[:-1]),
    lambda x: dataclasses.replace(x, observations=(x.observations[0],) * 3),
    lambda x: dataclasses.replace(x, topology_digest="0" * 64),
    lambda x: dataclasses.replace(x, binding_digest="0" * 64),
    lambda x: dataclasses.replace(x, response_commit_attempts=1),
    lambda x: dataclasses.replace(x, persistence_count=1),
    lambda x: dataclasses.replace(x, containment_accepted=True),
    lambda x: dataclasses.replace(x, production_failure_containment_accepted=True),
))
def test_binding_reorder_drop_duplicate_count_digest_and_claim_injection(binding, change):
    assert not owner.verify_failure_response_state_containment_binding(change(binding))


def test_noncanonical_foundation_wrong_record_and_cross_record_mapping_rejected(binding):
    source = dataclasses.replace(binding.source_batch, batch_digest="0" * 64)
    assert owner.create_failure_response_state_containment_binding(source) is None
    first, second = binding.source_batch.records[:2]
    assert not owner.verify_failure_response_state_containment_observation(
        binding.observations[0], second)
    forged = dataclasses.replace(first, outcome=dataclasses.replace(first.outcome, success=True))
    assert not owner.verify_failure_response_state_containment_observation(
        binding.observations[0], forged)


def test_authority_permission_deployment_and_rollback_injection_rejected(binding):
    for name in owner.FailureResponseStateContainmentAuthorityBoundary.__dataclass_fields__:
        boundary = dataclasses.replace(binding.authority_boundary, **{name: True})
        assert not owner.verify_failure_response_state_containment_binding(
            dataclasses.replace(binding, authority_boundary=boundary))


def test_prohibited_production_entry_points_are_not_required(monkeypatch, binding):
    import brain.production_response_candidate as candidate
    import brain.production_final_response_resolution as resolution
    import brain.production_turn_commit_receipt as commit
    import brain.response_commit_boundary as app_owned
    def prohibited(*args, **kwargs):
        raise AssertionError("prohibited production entry point called")
    monkeypatch.setattr(candidate, "create_production_response_candidate", prohibited)
    monkeypatch.setattr(resolution, "create_production_final_response_resolution", prohibited)
    monkeypatch.setattr(commit, "create_production_turn_commit_receipt", prohibited)
    monkeypatch.setattr(app_owned, "commit_response_boundary", prohibited)
    assert owner.verify_failure_response_state_containment_binding(binding)
    assert owner.verify_failure_response_state_containment_binding(
        owner.create_failure_response_state_containment_binding(binding.source_batch))


def test_verifier_purity_does_not_rerun_containment_evaluation(monkeypatch, binding):
    monkeypatch.setattr(owner, "_evaluate", lambda *a: pytest.fail("evaluation rerun"))
    assert owner.verify_failure_response_state_containment_binding(binding)


def test_frozen_contracts_public_api_and_no_arbitrary_state_or_outcome_parameters():
    contracts = (owner.FailureResponseStateContainmentAuthorityBoundary,
        owner.FailureResponseSuppressionDecision, owner.FailureStateSnapshot,
        owner.FailureResponseStateContainmentObservation,
        owner.FailureResponseStateContainmentBinding)
    assert all(x.__dataclass_params__.frozen for x in contracts)
    assert tuple(inspect.signature(
        owner.create_failure_response_state_containment_binding).parameters) == ("source_batch",)


def test_static_no_app_environment_file_network_subprocess_session_or_commit_calls():
    source = Path(owner.__file__).read_text(encoding="utf-8")
    for forbidden in ("import app", "streamlit", "os.environ", "getenv(",
            "subprocess", "requests.", "socket", "open(", "session_state"):
        assert forbidden not in source
    tree = ast.parse(source)
    prohibited = {"create_production_response_candidate",
        "create_production_final_response_resolution", "create_production_turn_commit_receipt",
        "commit_response_boundary"}
    called = {node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not called.intersection(prohibited)


def test_wrong_types_fail_closed():
    assert owner.create_failure_response_state_containment_binding({}) is None
    assert not owner.verify_failure_response_suppression_decision({}, {})
    assert not owner.verify_failure_state_snapshot({})
    assert not owner.verify_failure_response_state_containment_observation({}, {})
    assert not owner.verify_failure_response_state_containment_binding({})
