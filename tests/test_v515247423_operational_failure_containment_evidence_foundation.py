from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.operational_failure_containment_evidence_foundation as foundation
from brain.immutable_failure_response_state_containment import (
    create_failure_response_state_containment_binding,
)
from brain.production_deployment_artifact_evidence_foundation import (
    prepare_production_deployment_artifact_evidence,
)
from brain.production_failure_containment_acceptance import (
    create_production_failure_containment_acceptance_report,
)
from brain.production_feature_gate_release_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
)
from brain.production_rollback_evidence_foundation import (
    create_production_rollback_evidence_foundation,
)
from brain.production_rollback_readiness_acceptance import (
    evaluate_production_rollback_readiness,
)
from test_v5152474151_verifiable_isolated_failure_containment_record import batch


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "operational_failure_containment_evidence_foundation.py"


@pytest.fixture(scope="module")
def artifacts():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    failure_batch = batch()
    state = create_failure_response_state_containment_binding(failure_batch)
    containment = create_production_failure_containment_acceptance_report(
        failure_batch, state)
    rollback = create_production_rollback_evidence_foundation(
        owner, proposal, containment)
    readiness = evaluate_production_rollback_readiness(rollback)
    deployment = prepare_production_deployment_artifact_evidence(readiness)
    result = foundation.prepare_operational_failure_containment_evidence_foundation(
        "RUNTIME_EXCEPTION", deployment, containment)
    assert foundation.verify_operational_failure_containment_evidence_foundation(result)
    return deployment, containment, result


@pytest.mark.parametrize("incident_type", foundation.INCIDENT_TYPES)
def test_all_canonical_incident_types_prepare(artifacts, incident_type):
    deployment, containment, _ = artifacts
    result = foundation.prepare_operational_failure_containment_evidence_foundation(
        incident_type, deployment, containment)
    assert result.status == foundation.FOUNDATION_PREPARED
    assert result.evidence.incident_identity.incident_type == incident_type
    assert foundation.verify_operational_failure_containment_evidence_foundation(result)


def test_prepared_is_evidence_only_and_has_no_executable_output(artifacts):
    result = artifacts[2]
    assert result.status == foundation.FOUNDATION_PREPARED
    assert result.executable_output is None
    assert result.issues == ()
    assert result.evidence.incident_observed is False
    assert result.evidence.containment_executed is False


def test_all_authority_and_mutation_boundaries_remain_false(artifacts):
    result = artifacts[2]
    assert not any(getattr(result, name) for name in foundation.BOUNDARY_FIELDS)


def test_exact_canonical_upstream_bindings(artifacts):
    deployment, containment, result = artifacts
    evidence = result.evidence
    assert evidence.proposal_digest == deployment.proposal_id
    assert evidence.requested_state is deployment.requested_state
    assert evidence.release_revision_id == deployment.proposal_revision
    assert evidence.release_revision_digest == deployment.proposal_revision_digest
    assert evidence.runtime_configuration_identity == deployment.runtime_configuration_identity
    assert evidence.runtime_configuration_digest == deployment.runtime_configuration_digest
    assert evidence.feature_gate_identity == deployment.feature_gate_name
    assert evidence.feature_gate_state is deployment.feature_gate_requested_state
    assert evidence.deployment_artifact_identity == deployment.deployment_artifact_identity
    assert evidence.deployment_artifact_digest == deployment.deployment_artifact_digest
    assert evidence.deployment_evidence_digest == deployment.evidence_digest
    assert evidence.failure_containment_acceptance_digest == containment.report_digest
    assert evidence.failure_containment_topology_digest == containment.topology_digest


def test_incident_identity_is_a_deterministic_binding_not_an_observation(artifacts):
    deployment, _, result = artifacts
    identity = result.evidence.incident_identity
    assert identity.proposal_digest == deployment.proposal_id
    assert identity.release_revision_id == deployment.proposal_revision
    assert identity.deployment_artifact_identity == deployment.deployment_artifact_identity
    assert foundation.verify_operational_failure_incident_identity(identity, deployment)


def test_repeated_construction_is_identical(artifacts):
    deployment, containment, result = artifacts
    duplicate = foundation.prepare_operational_failure_containment_evidence_foundation(
        "RUNTIME_EXCEPTION", deployment, containment)
    assert duplicate == result
    assert duplicate.foundation_digest == result.foundation_digest
    assert duplicate.topology_digest == result.topology_digest


def test_exact_ordered_unique_checks(artifacts):
    checks = artifacts[2].checks
    assert tuple(item.check_id for item in checks) == foundation.CHECK_ORDER
    assert tuple(item.ordinal for item in checks) == tuple(range(1, 13))
    assert len(set(foundation.CHECK_ORDER)) == 12
    assert all(foundation.verify_operational_failure_containment_evidence_check(item)
        for item in checks)


@pytest.mark.parametrize("digest", (
    "policy_digest", "incident_identity_digest", "deployment_evidence_digest",
    "containment_acceptance_digest", "topology_digest", "foundation_digest",
))
def test_foundation_digests_are_lowercase_sha256(artifacts, digest):
    value = getattr(artifacts[2], digest)
    assert len(value) == 64
    assert value == value.lower()
    int(value, 16)


def test_all_contracts_are_frozen_and_sequences_are_tuples(artifacts):
    result = artifacts[2]
    for value in (result, result.policy, result.evidence,
                  result.evidence.incident_identity, result.checks[0]):
        assert value.__dataclass_params__.frozen
        with pytest.raises(dataclasses.FrozenInstanceError):
            value.schema = "forged"
    assert isinstance(result.checks, tuple)
    assert isinstance(result.issues, tuple)
    assert isinstance(result.policy.incident_types, tuple)


@pytest.mark.parametrize("value", (
    None, object(), {}, [], (), True, 1, "pass", "RUNTIME_EXCEPTION ",
    "runtime_exception", "UNLISTED_FAILURE",
))
def test_wrong_or_unknown_incident_is_rejected(artifacts, value):
    deployment, containment, _ = artifacts
    assert foundation.prepare_operational_failure_containment_evidence_foundation(
        value, deployment, containment) is None
    assert foundation.classify_operational_failure_containment_evidence_foundation(
        value, deployment, containment) == foundation.FOUNDATION_REJECTED


@pytest.mark.parametrize("value", (None, object(), {}, [], True, "accepted"))
def test_wrong_deployment_evidence_is_rejected(artifacts, value):
    containment = artifacts[1]
    assert foundation.prepare_operational_failure_containment_evidence_foundation(
        "RUNTIME_EXCEPTION", value, containment) is None


@pytest.mark.parametrize("value", (None, object(), {}, [], True, "accepted"))
def test_wrong_containment_acceptance_is_rejected(artifacts, value):
    deployment = artifacts[0]
    assert foundation.prepare_operational_failure_containment_evidence_foundation(
        "RUNTIME_EXCEPTION", deployment, value) is None


@pytest.mark.parametrize("field,value", (
    ("version", "5.15.24.7.4.24"),
    ("schema", "forged/schema"),
    ("status", foundation.FOUNDATION_REJECTED),
    ("issues", ("caller-supplied-pass",)),
    ("executable_output", "execute"),
    ("policy_digest", "0" * 64),
    ("incident_identity_digest", "0" * 64),
    ("deployment_evidence_digest", "0" * 64),
    ("containment_acceptance_digest", "0" * 64),
    ("topology_digest", "0" * 64),
    ("foundation_digest", "0" * 64),
))
def test_strict_verifier_rejects_foundation_tampering(artifacts, field, value):
    forged = dataclasses.replace(artifacts[2], **{field: value})
    assert not foundation.verify_operational_failure_containment_evidence_foundation(forged)


@pytest.mark.parametrize("field", foundation.BOUNDARY_FIELDS)
def test_caller_cannot_supply_authority_or_execution_flags(artifacts, field):
    forged = dataclasses.replace(artifacts[2], **{field: True})
    assert not foundation.verify_operational_failure_containment_evidence_foundation(forged)


@pytest.mark.parametrize("field,value", (
    ("proposal_digest", "0" * 64),
    ("requested_state", False),
    ("release_revision_id", "forged-revision"),
    ("release_revision_digest", "0" * 64),
    ("runtime_configuration_identity", "forged-configuration"),
    ("runtime_configuration_digest", "0" * 64),
    ("feature_gate_identity", "forged-gate"),
    ("feature_gate_state", False),
    ("deployment_artifact_identity", "forged-artifact"),
    ("deployment_artifact_digest", "0" * 64),
    ("deployment_evidence_digest", "0" * 64),
    ("failure_containment_acceptance_digest", "0" * 64),
    ("failure_containment_topology_digest", "0" * 64),
    ("incident_observed", True),
    ("containment_executed", True),
    ("evidence_digest", "0" * 64),
))
def test_strict_verifier_rejects_evidence_tampering(artifacts, field, value):
    forged_evidence = dataclasses.replace(artifacts[2].evidence, **{field: value})
    forged = dataclasses.replace(artifacts[2], evidence=forged_evidence)
    assert not foundation.verify_operational_failure_containment_evidence_foundation(forged)


@pytest.mark.parametrize("field,value", (
    ("schema", "forged"),
    ("incident_type", "UNLISTED_FAILURE"),
    ("proposal_digest", "0" * 64),
    ("release_revision_id", "forged"),
    ("deployment_artifact_identity", "forged"),
    ("identity_digest", "0" * 64),
))
def test_strict_verifier_rejects_incident_identity_tampering(artifacts, field, value):
    result = artifacts[2]
    forged_identity = dataclasses.replace(
        result.evidence.incident_identity, **{field: value})
    forged_evidence = dataclasses.replace(result.evidence,
        incident_identity=forged_identity)
    forged = dataclasses.replace(result, evidence=forged_evidence)
    assert not foundation.verify_operational_failure_containment_evidence_foundation(forged)


@pytest.mark.parametrize("field,value", (
    ("check_id", "UNKNOWN_CHECK"), ("ordinal", 99),
    ("evidence_digests", ("0" * 64,)), ("verified", False),
    ("check_digest", "0" * 64),
))
def test_strict_verifier_rejects_check_tampering(artifacts, field, value):
    result = artifacts[2]
    forged_check = dataclasses.replace(result.checks[0], **{field: value})
    forged = dataclasses.replace(result, checks=(forged_check,) + result.checks[1:])
    assert not foundation.verify_operational_failure_containment_evidence_foundation(forged)


def test_strict_verifier_rejects_reordered_duplicate_or_missing_checks(artifacts):
    result = artifacts[2]
    variants = (result.checks[::-1], result.checks[:-1],
                (result.checks[0],) + result.checks)
    for checks in variants:
        assert not foundation.verify_operational_failure_containment_evidence_foundation(
            dataclasses.replace(result, checks=checks))


def test_strict_verifier_rejects_noncanonical_policy(artifacts):
    result = artifacts[2]
    forged_policy = dataclasses.replace(result.policy, version="caller-policy")
    forged = dataclasses.replace(result, policy=forged_policy)
    assert not foundation.verify_operational_failure_containment_evidence_foundation(forged)
    assert not foundation.verify_operational_failure_containment_evidence_policy(forged_policy)


def test_strict_verifier_rejects_subclasses(artifacts):
    class FoundationSpoof(foundation.OperationalFailureContainmentEvidenceFoundation):
        pass

    class IdentitySpoof(foundation.OperationalFailureIncidentIdentity):
        pass

    result = artifacts[2]
    spoof = FoundationSpoof(**{field.name: getattr(result, field.name)
        for field in dataclasses.fields(result)})
    identity = result.evidence.incident_identity
    identity_spoof = IdentitySpoof(**{field.name: getattr(identity, field.name)
        for field in dataclasses.fields(identity)})
    assert not foundation.verify_operational_failure_containment_evidence_foundation(spoof)
    assert not foundation.verify_operational_failure_incident_identity(
        identity_spoof, artifacts[0])


def test_public_construction_surface_has_no_trust_or_authority_parameters():
    assert tuple(inspect.signature(
        foundation.prepare_operational_failure_containment_evidence_foundation
    ).parameters) == ("incident_type", "deployment_evidence", "containment_acceptance")
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_parameters = {"passed", "accepted", "approved", "authority",
                            "activation_permitted", "transition_approved"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert forbidden_parameters.isdisjoint(arg.arg for arg in node.args.args)


def test_module_has_no_time_random_environment_thread_process_or_execution_imports():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    forbidden = {"datetime", "time", "uuid", "random", "os", "socket",
                 "threading", "multiprocessing", "subprocess", "traceback"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert forbidden.isdisjoint(imported)


def test_module_does_not_retain_mutable_caller_collections(artifacts):
    result = artifacts[2]
    for value in dataclasses.astuple(result.policy):
        assert not isinstance(value, (list, dict, set))
    assert not isinstance(result.checks, (list, dict, set))
    assert not isinstance(result.issues, (list, dict, set))

