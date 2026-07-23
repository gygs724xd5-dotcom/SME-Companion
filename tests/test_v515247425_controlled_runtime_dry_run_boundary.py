from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.controlled_runtime_dry_run_boundary as dry_run


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "controlled_runtime_dry_run_boundary.py"


@pytest.fixture
def dry_request():
    return dry_run.ControlledRuntimeDryRunRequest(
        schema=dry_run.SCHEMA,
        planner_identity="canonical-planner/v1",
        selected_skill_identity="business-skill/cost-analysis/v1",
        validated_skill_contract="skill-contract:cost-analysis:v1",
        evidence_digest="1" * 64,
        operational_failure_acceptance_digest="2" * 64,
        runtime_policy_digest=dry_run.CANONICAL_DRY_RUN_POLICY.policy_digest,
    )


@pytest.fixture
def result(dry_request):
    value = dry_run.simulate_controlled_runtime_dry_run(dry_request)
    assert value is not None
    return value


def test_positive_dry_run_and_digest_determinism(dry_request, result):
    duplicate = dry_run.simulate_controlled_runtime_dry_run(dry_request)
    assert duplicate == result
    assert duplicate.runtime_result_digest == result.runtime_result_digest
    assert result.dry_run_status == dry_run.DRY_RUN_COMPLETED
    assert dry_run.classify_controlled_runtime_dry_run(dry_request) == dry_run.DRY_RUN_COMPLETED
    assert dry_run.verify_controlled_runtime_dry_run_result(dry_request, result)


@pytest.mark.parametrize(
    "field,value",
    (
        ("planner_identity", "wrong planner"),
        ("selected_skill_identity", "wrong skill"),
        ("evidence_digest", "3" * 64),
        ("operational_failure_acceptance_digest", "4" * 64),
        ("runtime_policy_digest", "5" * 64),
        ("schema", "wrong/schema"),
    ),
)
def test_request_mismatches_are_rejected(dry_request, field, value):
    forged = dataclasses.replace(dry_request, **{field: value})
    if field in ("evidence_digest", "operational_failure_acceptance_digest"):
        result = dry_run.simulate_controlled_runtime_dry_run(dry_request)
        assert result is not None
        assert not dry_run.verify_controlled_runtime_dry_run_result(forged, result)
        assert dry_run.classify_controlled_runtime_dry_run(forged) == dry_run.DRY_RUN_COMPLETED
    else:
        assert dry_run.simulate_controlled_runtime_dry_run(forged) is None
        assert dry_run.classify_controlled_runtime_dry_run(forged) == dry_run.DRY_RUN_REJECTED


def test_result_identity_contract_and_digest_mismatches(dry_request, result):
    for field, value in (
        ("planner_identity", "other-planner/v1"),
        ("selected_skill_identity", "other-skill/v1"),
        ("validated_skill_contract", "skill-contract:other:v1"),
        ("evidence_digest", "3" * 64),
        ("operational_failure_acceptance_digest", "4" * 64),
        ("runtime_policy_digest", "5" * 64),
        ("runtime_result_digest", "6" * 64),
    ):
        assert not dry_run.verify_controlled_runtime_dry_run_result(
            dry_request, dataclasses.replace(result, **{field: value})
        )


def test_wrong_policy_and_schema_are_rejected(dry_request, result):
    policy = dataclasses.replace(
        dry_run.CANONICAL_DRY_RUN_POLICY, identity="forged-policy"
    )
    verifier = dataclasses.replace(dry_run.CANONICAL_DRY_RUN_VERIFIER, policy=policy)
    assert not dry_run.verify_controlled_runtime_dry_run_policy(policy)
    assert not dry_run.verify_controlled_runtime_dry_run_result(
        dry_request, result, verifier
    )
    assert dry_run.simulate_controlled_runtime_dry_run(
        dataclasses.replace(dry_request, schema="forged")
    ) is None


@pytest.mark.parametrize("value", ({}, [], set(), object(), None))
def test_mutable_and_wrong_schema_substitutions_are_rejected(value):
    assert dry_run.simulate_controlled_runtime_dry_run(value) is None
    assert not dry_run.verify_controlled_runtime_dry_run_request(value)


def test_mutable_field_substitution_is_rejected(dry_request):
    for field in (
        "planner_identity",
        "selected_skill_identity",
        "validated_skill_contract",
        "evidence_digest",
        "operational_failure_acceptance_digest",
    ):
        assert dry_run.simulate_controlled_runtime_dry_run(
            dataclasses.replace(dry_request, **{field: [getattr(dry_request, field)]})
        ) is None


def test_subclasses_are_rejected(dry_request, result):
    class RequestSpoof(dry_run.ControlledRuntimeDryRunRequest):
        pass

    class ResultSpoof(dry_run.ControlledRuntimeDryRunResult):
        pass

    spoof_request = RequestSpoof(
        **{field.name: getattr(dry_request, field.name) for field in dataclasses.fields(dry_request)}
    )
    spoof_result = ResultSpoof(
        **{field.name: getattr(result, field.name) for field in dataclasses.fields(result)}
    )
    assert dry_run.simulate_controlled_runtime_dry_run(spoof_request) is None
    assert not dry_run.verify_controlled_runtime_dry_run_result(dry_request, spoof_result)


@pytest.mark.parametrize(
    "field",
    (
        "execution_requested",
        "deployment_requested",
        "activation_requested",
        "external_call_attempted",
        "runtime_mutation_requested",
    ),
)
def test_authority_and_side_effect_requests_are_rejected(dry_request, field):
    forged = dataclasses.replace(dry_request, **{field: True})
    assert dry_run.simulate_controlled_runtime_dry_run(forged) is None
    assert dry_run.classify_controlled_runtime_dry_run(forged) == dry_run.DRY_RUN_REJECTED


@pytest.mark.parametrize("field", dry_run.BOUNDARY_FIELDS)
def test_all_boundary_invariants_are_permanently_false(dry_request, result, field):
    assert getattr(result, field) is False
    assert not dry_run.verify_controlled_runtime_dry_run_result(
        dry_request, dataclasses.replace(result, **{field: True})
    )


def test_contracts_are_frozen_and_checks_are_ordered(dry_request, result):
    for value in (
        dry_run.CANONICAL_DRY_RUN_POLICY,
        dry_request,
        result,
        dry_run.CANONICAL_DRY_RUN_VERIFIER,
    ):
        assert value.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.runtime_mutated = True
    assert len(dry_run.CHECK_ORDER) >= 14
    assert len(set(dry_run.CHECK_ORDER)) == len(dry_run.CHECK_ORDER)
    assert dry_run.CANONICAL_DRY_RUN_POLICY.required_checks == dry_run.CHECK_ORDER
    assert dry_run.CANONICAL_DRY_RUN_VERIFIER.ordered_checks == dry_run.CHECK_ORDER


def test_only_allowed_runtime_states_exist():
    assert dry_run.RUNTIME_STATES == (
        "DRY_RUN_READY",
        "DRY_RUN_COMPLETED",
        "DRY_RUN_REJECTED",
    )
    assert {"EXECUTING", "ACTIVATED", "DEPLOYED"}.isdisjoint(dry_run.RUNTIME_STATES)


def test_narrow_static_non_operational_boundary():
    assert tuple(inspect.signature(dry_run.simulate_controlled_runtime_dry_run).parameters) == (
        "request",
    )
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert {
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "requests",
        "urllib",
        "uuid",
        "random",
        "datetime",
    }.isdisjoint(imported)
    assert not any(isinstance(node, (ast.Call,)) and isinstance(node.func, ast.Name)
                   and node.func.id == "open" for node in ast.walk(tree))
    for forbidden in ("EXECUTING", "ACTIVATED", "DEPLOYED"):
        assert forbidden not in source
