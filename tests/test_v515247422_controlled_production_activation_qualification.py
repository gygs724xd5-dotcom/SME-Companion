from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.controlled_production_activation_qualification as qualification
from brain.immutable_failure_response_state_containment import create_failure_response_state_containment_binding
from brain.production_deployment_artifact_evidence_foundation import prepare_production_deployment_artifact_evidence
from brain.production_deployment_rollback_attestation_acceptance import evaluate_production_deployment_rollback_attestation_acceptance
from brain.production_deployment_rollback_attestation_foundation import prepare_production_deployment_rollback_attestation_foundation
from brain.production_failure_containment_acceptance import create_production_failure_containment_acceptance_report
from brain.production_feature_gate_owner import LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
from brain.production_feature_gate_release_owner import (
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
)
from brain.production_rollback_evidence_foundation import create_production_rollback_evidence_foundation
from brain.production_rollback_readiness_acceptance import evaluate_production_rollback_readiness
from test_v5152474151_verifiable_isolated_failure_containment_record import batch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "controlled_production_activation_qualification.py"


@pytest.fixture(scope="module")
def artifacts():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    failure_batch = batch()
    containment = create_production_failure_containment_acceptance_report(
        failure_batch, create_failure_response_state_containment_binding(failure_batch))
    rollback = create_production_rollback_evidence_foundation(owner, proposal, containment)
    readiness = evaluate_production_rollback_readiness(rollback)
    deployment = prepare_production_deployment_artifact_evidence(readiness)
    foundation = prepare_production_deployment_rollback_attestation_foundation(
        deployment, rollback, readiness, containment)
    acceptance = evaluate_production_deployment_rollback_attestation_acceptance(foundation)
    result = qualification.evaluate_controlled_production_activation_qualification(acceptance)
    assert qualification.verify_controlled_production_activation_qualification(result)
    return owner, acceptance, result


def test_canonical_acceptance_produces_qualification_only(artifacts):
    _, acceptance, result = artifacts
    assert result.status == qualification.QUALIFIED and result.qualified
    assert qualification.classify_controlled_production_activation_qualification(
        acceptance) == qualification.QUALIFIED
    assert not result.successful_activation


def test_repeated_construction_and_digest_stability(artifacts):
    duplicate = qualification.evaluate_controlled_production_activation_qualification(
        artifacts[1])
    assert duplicate == artifacts[2]
    assert duplicate.qualification_digest == artifacts[2].qualification_digest
    assert duplicate.topology_digest == artifacts[2].topology_digest


def test_canonical_policy_is_frozen_verified_and_complete(artifacts):
    policy = artifacts[2].policy
    assert policy is qualification.CANONICAL_QUALIFICATION_POLICY
    assert policy.identity == qualification.POLICY_IDENTITY
    assert policy.required_checks == qualification.CHECK_ORDER
    assert policy.required_false_boundaries == qualification.BOUNDARY_FIELDS
    assert qualification.verify_controlled_production_activation_qualification_policy(policy)
    with pytest.raises(dataclasses.FrozenInstanceError): policy.identity = "forged"


def test_exact_upstream_digest_and_identity_bindings(artifacts):
    acceptance, result = artifacts[1:]
    assert result.acceptance is acceptance
    assert result.acceptance_digest == acceptance.acceptance_digest
    assert result.attestation_digest == acceptance.foundation.foundation_digest
    assert result.deployment_digest == acceptance.deployment_artifact_evidence_digest
    assert result.rollback_digest == acceptance.rollback_evidence_digest
    assert result.readiness_digest == acceptance.rollback_readiness_acceptance_digest
    assert result.failure_containment_digest == acceptance.failure_containment_acceptance_digest
    assert result.proposal_digest == acceptance.proposal_digest
    assert result.revision_digest == acceptance.proposal_revision_digest
    assert result.gate_identity == acceptance.feature_gate_identity
    assert result.configuration_digest == acceptance.runtime_configuration_digest
    assert result.rollback_target_digest == acceptance.rollback_target_digest


def test_exact_ordered_unique_qualification_checks(artifacts):
    result = artifacts[2]
    assert tuple(item.check_id for item in result.checks) == qualification.CHECK_ORDER
    assert tuple(item.ordinal for item in result.checks) == tuple(range(1, 27))
    assert len(set(qualification.CHECK_ORDER)) == 26
    assert all(qualification.verify_controlled_production_activation_qualification_check(item)
        for item in result.checks)


def test_boundary_invariants_and_default_deny(artifacts):
    owner, _, result = artifacts
    assert not any(getattr(result, field) for field in qualification.BOUNDARY_FIELDS)
    assert result.executable_output is None and result.issues == ()
    assert owner.default_denied and not owner.activation_permitted


def test_immutable_contracts(artifacts):
    result = artifacts[2]
    for contract in (type(result), type(result.policy), type(result.checks[0])):
        assert contract.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError): result.status = qualification.REJECTED


@pytest.mark.parametrize("value", ({}, [], True, "qualified", object(), None))
def test_invalid_input_types_are_deterministically_rejected(value):
    assert qualification.evaluate_controlled_production_activation_qualification(value) is None
    assert qualification.classify_controlled_production_activation_qualification(
        value) == qualification.REJECTED


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"),
    ("status", "DEPLOYMENT_ROLLBACK_ATTESTATION_REJECTED"),
    ("policy_digest", "0" * 64), ("attestation_foundation_digest", "0" * 64),
    ("attestation_subject_digest", "0" * 64), ("acceptance_digest", "0" * 64),
    ("proposal_digest", "0" * 64), ("requested_state", False),
    ("proposal_revision", "forged"), ("feature_gate_identity", "OTHER"),
    ("runtime_configuration_digest", "0" * 64),
    ("rollback_target_digest", "0" * 64), ("accepted", False),
))
def test_invalid_acceptance_and_cross_binding_rejected(artifacts, field, value):
    forged = dataclasses.replace(artifacts[1], **{field: value})
    assert qualification.evaluate_controlled_production_activation_qualification(forged) is None


@pytest.mark.parametrize("path,field,value", (
    ("foundation", "foundation_digest", "0" * 64),
    ("foundation", "status", "DEPLOYMENT_ROLLBACK_ATTESTATION_REJECTED"),
    ("deployment_evidence", "evidence_digest", "0" * 64),
    ("rollback_evidence", "foundation_digest", "0" * 64),
    ("rollback_readiness", "acceptance_digest", "0" * 64),
    ("rollback_readiness", "accepted", False),
    ("failure_containment", "report_digest", "0" * 64),
    ("failure_containment", "accepted", False),
))
def test_forged_nested_verifier_evidence_rejected(artifacts, path, field, value):
    accepted = artifacts[1]
    if path == "foundation":
        changed = dataclasses.replace(accepted.foundation, **{field: value})
        forged = dataclasses.replace(accepted, foundation=changed)
    else:
        changed = dataclasses.replace(getattr(accepted.foundation, path), **{field: value})
        changed_foundation = dataclasses.replace(accepted.foundation, **{path: changed})
        forged = dataclasses.replace(accepted, foundation=changed_foundation)
    assert qualification.evaluate_controlled_production_activation_qualification(forged) is None


@pytest.mark.parametrize("field", (
    "transition_approved", "feature_gate_mutated", "deployment_executed",
    "rollback_executed", "activation_permitted", "approval_permitted",
    "runtime_mutated", "successful_attestation",
))
def test_caller_supplied_permission_or_operational_state_rejected(artifacts, field):
    forged = dataclasses.replace(artifacts[1], **{field: True})
    assert qualification.evaluate_controlled_production_activation_qualification(forged) is None


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("schema", "FORGED"), ("scope", "FORGED"),
    ("status", qualification.REJECTED), ("status", "PRODUCTION_ACTIVE"),
    ("policy_digest", "0" * 64), ("acceptance_digest", "0" * 64),
    ("attestation_digest", "0" * 64), ("deployment_digest", "0" * 64),
    ("rollback_digest", "0" * 64), ("readiness_digest", "0" * 64),
    ("failure_containment_digest", "0" * 64), ("proposal_digest", "0" * 64),
    ("revision_digest", "0" * 64), ("gate_identity", "OTHER"),
    ("configuration_digest", "0" * 64), ("rollback_target_digest", "0" * 64),
    ("issues", ("FORGED",)), ("qualified", False),
    ("topology_digest", "0" * 64), ("qualification_digest", "0" * 64),
))
def test_qualification_identity_binding_policy_and_digest_forgery_rejected(
        artifacts, field, value):
    forged = dataclasses.replace(artifacts[2], **{field: value})
    assert not qualification.verify_controlled_production_activation_qualification(forged)


@pytest.mark.parametrize("field", qualification.BOUNDARY_FIELDS)
def test_any_qualification_boundary_true_is_rejected(artifacts, field):
    forged = dataclasses.replace(artifacts[2], **{field: True})
    assert not qualification.verify_controlled_production_activation_qualification(forged)


def test_noncanonical_policy_rejected(artifacts):
    result = artifacts[2]
    for policy in (
        dataclasses.replace(result.policy, identity="forged"),
        dataclasses.replace(result.policy, version="0"),
        dataclasses.replace(result.policy, required_checks=result.policy.required_checks[::-1]),
        dataclasses.replace(result.policy, policy_digest="0" * 64),
    ):
        assert not qualification.verify_controlled_production_activation_qualification_policy(policy)
        assert not qualification.verify_controlled_production_activation_qualification(
            dataclasses.replace(result, policy=policy))


def test_missing_duplicate_reordered_extra_mutable_and_altered_checks_rejected(artifacts):
    result = artifacts[2]; checks = result.checks
    extra = dataclasses.replace(checks[-1], check_id="EXTRA", ordinal=27)
    for variant in (checks[:-1], checks + (extra,), (checks[0],) * len(checks),
            checks[::-1], list(checks),
            (dataclasses.replace(checks[0], verified=False),) + checks[1:],
            (dataclasses.replace(checks[0], evidence_digests=[]),) + checks[1:],
            (dataclasses.replace(checks[0], check_digest="0" * 64),) + checks[1:]):
        assert not qualification.verify_controlled_production_activation_qualification(
            dataclasses.replace(result, checks=variant))


def test_exact_type_and_subclass_spoofing_rejected(artifacts):
    result = artifacts[2]
    class QualificationSpoof(type(result)): pass
    spoof = QualificationSpoof(**{field.name: getattr(result, field.name)
        for field in dataclasses.fields(result)})
    assert not qualification.verify_controlled_production_activation_qualification(spoof)


def test_input_objects_and_gate_owner_are_not_mutated(artifacts):
    owner, accepted, _ = artifacts; before = accepted
    qualification.evaluate_controlled_production_activation_qualification(accepted)
    assert accepted == before and owner is get_production_feature_gate_release_owner()
    assert owner.default_denied and not owner.activation_permitted


def test_narrow_api_has_no_caller_permission_parameters():
    assert tuple(inspect.signature(
        qualification.evaluate_controlled_production_activation_qualification
        ).parameters) == ("attestation_acceptance",)


def test_static_no_environment_file_network_subprocess_or_operational_calls():
    source = MODULE.read_text(encoding="utf-8"); tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {"os", "pathlib", "socket", "subprocess", "requests", "urllib",
        "uuid", "random", "datetime"}.isdisjoint(imported)
    for forbidden in ("open(", "os.environ", "subprocess", "deploy(",
            "execute_rollback(", "activate_", "approve_"):
        assert forbidden not in source
