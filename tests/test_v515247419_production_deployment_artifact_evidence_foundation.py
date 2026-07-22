from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.production_deployment_artifact_evidence_foundation as evidence
from brain.immutable_failure_response_state_containment import (
    create_failure_response_state_containment_binding,
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
MODULE = ROOT / "brain" / "production_deployment_artifact_evidence_foundation.py"


@pytest.fixture(scope="module")
def artifacts():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    failure_batch = batch()
    state = create_failure_response_state_containment_binding(failure_batch)
    containment = create_production_failure_containment_acceptance_report(failure_batch, state)
    rollback = create_production_rollback_evidence_foundation(owner, proposal, containment)
    readiness = evaluate_production_rollback_readiness(rollback)
    result = evidence.prepare_production_deployment_artifact_evidence(readiness)
    assert evidence.verify_production_deployment_artifact_evidence(result)
    return readiness, result


def test_canonical_happy_path_is_prepared_only(artifacts):
    readiness, result = artifacts
    assert result.status == evidence.PREPARED
    assert evidence.classify_production_deployment_artifact_evidence(readiness) == evidence.PREPARED
    assert not any((result.deployment_executed, result.feature_gate_mutated,
        result.transition_approved, result.deployment_attested,
        result.rollback_executed, result.approval_permitted))
    assert result.executable_output is None


def test_deterministic_repeated_construction_and_stable_digests(artifacts):
    readiness, result = artifacts
    duplicate = evidence.prepare_production_deployment_artifact_evidence(readiness)
    assert duplicate == result
    assert duplicate.deployment_artifact_identity == result.deployment_artifact_identity
    assert duplicate.deployment_artifact_digest == result.deployment_artifact_digest
    assert duplicate.evidence_digest == result.evidence_digest


def test_explicit_canonical_deployment_artifact_identity(artifacts):
    readiness, result = artifacts
    artifact = result.artifact
    assert artifact.schema == evidence.ARTIFACT_SCHEMA
    assert artifact.artifact_type == evidence.ARTIFACT_TYPE
    assert artifact.logical_name == f"{readiness.feature_gate_identity}:deployment-artifact"
    assert artifact.artifact_revision == readiness.release_revision_id
    assert artifact.proposal_digest == readiness.proposal_digest
    assert artifact.feature_gate_name == readiness.feature_gate_identity
    assert artifact.feature_gate_requested_state is True
    assert artifact.runtime_configuration_digest == readiness.rollback_configuration_digest
    assert evidence.verify_production_deployment_artifact_identity(artifact, readiness)


def test_exact_proposal_revision_state_gate_and_configuration_bindings(artifacts):
    readiness, result = artifacts
    assert result.proposal_id == readiness.proposal_digest
    assert result.requested_state is True
    assert result.proposal_revision == readiness.release_revision_id
    assert result.proposal_revision_digest == readiness.release_revision_digest
    assert result.feature_gate_name == readiness.feature_gate_identity
    assert result.feature_gate_requested_state is True
    assert result.runtime_configuration_identity == readiness.rollback_configuration_identity
    assert result.runtime_configuration_digest == readiness.rollback_configuration_digest


def test_binding_digests_are_distinct_and_canonical(artifacts):
    result = artifacts[1]
    bindings = (result.artifact_to_proposal_binding_digest,
        result.artifact_to_revision_binding_digest,
        result.artifact_to_gate_binding_digest,
        result.artifact_to_runtime_configuration_binding_digest)
    assert len(set(bindings)) == 4
    assert all(len(item) == 64 and item == item.lower() for item in bindings)


def test_exact_ordered_unique_checks(artifacts):
    result = artifacts[1]
    assert tuple(item.check_id for item in result.checks) == evidence.CHECK_ORDER
    assert tuple(item.ordinal for item in result.checks) == tuple(range(1, 17))
    assert len(set(evidence.CHECK_ORDER)) == 16
    assert all(evidence.verify_production_deployment_artifact_evidence_check(item)
        for item in result.checks)


def test_immutable_result_and_artifact(artifacts):
    result = artifacts[1]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "DEPLOYED"
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.artifact.artifact_type = "ROLLBACK_ARTIFACT"
    assert result.__dataclass_params__.frozen
    assert result.artifact.__dataclass_params__.frozen


@pytest.mark.parametrize("value", ({}, [], True, "pass", object(), None))
def test_wrong_or_missing_upstream_is_deterministically_rejected(value):
    assert evidence.prepare_production_deployment_artifact_evidence(value) is None
    assert evidence.classify_production_deployment_artifact_evidence(value) == evidence.REJECTED


@pytest.mark.parametrize("field,value", (
    ("proposal_digest", "0" * 64), ("release_revision_id", "forged"),
    ("release_revision_digest", "0" * 64), ("requested_target_state", False),
    ("feature_gate_identity", "OTHER"),
    ("rollback_configuration_identity", "FORGED"),
    ("rollback_configuration_digest", "0" * 64),
    ("acceptance_digest", "0" * 64), ("accepted", False),
    ("readiness_evidence_permitted", False),
))
def test_mismatched_upstream_binding_rejected(artifacts, field, value):
    forged = dataclasses.replace(artifacts[0], **{field: value})
    assert evidence.prepare_production_deployment_artifact_evidence(forged) is None
    assert evidence.classify_production_deployment_artifact_evidence(forged) == evidence.REJECTED


@pytest.mark.parametrize("field,value", (
    ("schema", "rollback-artifact/v1"), ("artifact_type", "ROLLBACK_ARTIFACT"),
    ("logical_name", "forged"), ("artifact_revision", "forged"),
    ("content_digest", "0" * 64), ("proposal_digest", "0" * 64),
    ("feature_gate_name", "OTHER"), ("feature_gate_requested_state", False),
    ("runtime_configuration_digest", "0" * 64), ("identity_digest", "0" * 64),
))
def test_forged_identity_digest_and_rollback_substitution_rejected(
        artifacts, field, value):
    readiness, result = artifacts
    forged = dataclasses.replace(result.artifact, **{field: value})
    assert not evidence.verify_production_deployment_artifact_identity(forged, readiness)
    changed = dataclasses.replace(result, artifact=forged)
    assert not evidence.verify_production_deployment_artifact_evidence(changed)


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"), ("status", evidence.REJECTED),
    ("status", "DEPLOYED"), ("readiness_acceptance_digest", "0" * 64),
    ("proposal_id", "0" * 64), ("requested_state", False),
    ("proposal_revision", "forged"), ("proposal_revision_digest", "0" * 64),
    ("feature_gate_name", "OTHER"), ("feature_gate_requested_state", False),
    ("runtime_configuration_identity", "FORGED"),
    ("runtime_configuration_digest", "0" * 64),
    ("deployment_artifact_identity", "0" * 64),
    ("deployment_artifact_digest", "0" * 64),
    ("artifact_to_proposal_binding_digest", "0" * 64),
    ("artifact_to_revision_binding_digest", "0" * 64),
    ("artifact_to_gate_binding_digest", "0" * 64),
    ("artifact_to_runtime_configuration_binding_digest", "0" * 64),
    ("issues", ("FORGED",)), ("topology_digest", "0" * 64),
    ("evidence_digest", "0" * 64),
))
def test_result_identity_binding_status_and_digest_tampering_rejected(
        artifacts, field, value):
    forged = dataclasses.replace(artifacts[1], **{field: value})
    assert not evidence.verify_production_deployment_artifact_evidence(forged)


@pytest.mark.parametrize("field", (
    "deployment_executed", "feature_gate_mutated", "transition_approved",
    "deployment_attested", "rollback_executed", "approval_permitted",
))
def test_caller_supplied_pass_approval_attestation_and_execution_rejected(
        artifacts, field):
    forged = dataclasses.replace(artifacts[1], **{field: True})
    assert not evidence.verify_production_deployment_artifact_evidence(forged)


def test_missing_extra_duplicate_reordered_and_tampered_checks_rejected(artifacts):
    result = artifacts[1]
    checks = result.checks
    extra = dataclasses.replace(checks[-1], check_id="EXTRA", ordinal=17)
    variants = (
        checks[:-1], checks + (extra,), (checks[0],) * len(checks), checks[::-1],
        (dataclasses.replace(checks[0], check_digest="0" * 64),) + checks[1:],
        (dataclasses.replace(checks[0], verified=False),) + checks[1:],
        (dataclasses.replace(checks[0], evidence_digests=[]),) + checks[1:],
    )
    for variant in variants:
        assert not evidence.verify_production_deployment_artifact_evidence(
            dataclasses.replace(result, checks=variant))


def test_exact_type_and_subclass_spoofing_rejected(artifacts):
    class ArtifactSpoof(evidence.ProductionDeploymentArtifactIdentity):
        pass
    class ResultSpoof(evidence.ProductionDeploymentArtifactEvidence):
        pass
    readiness, result = artifacts
    spoof_artifact = ArtifactSpoof(**{
        field.name: getattr(result.artifact, field.name)
        for field in dataclasses.fields(result.artifact)})
    assert not evidence.verify_production_deployment_artifact_identity(
        spoof_artifact, readiness)
    spoof_result = ResultSpoof(**{
        field.name: getattr(result, field.name) for field in dataclasses.fields(result)})
    assert not evidence.verify_production_deployment_artifact_evidence(spoof_result)


def test_upstream_objects_are_not_mutated(artifacts):
    readiness, _ = artifacts
    before = readiness
    evidence.prepare_production_deployment_artifact_evidence(readiness)
    assert readiness == before


def test_narrow_api_has_no_caller_identity_pass_or_approval_fields():
    assert tuple(inspect.signature(
        evidence.prepare_production_deployment_artifact_evidence).parameters) == (
        "readiness_acceptance",)
    assert tuple(inspect.signature(
        evidence.verify_production_deployment_artifact_identity).parameters) == (
        "value", "readiness_acceptance")


def test_static_no_environment_path_network_random_or_operational_calls():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {"os", "pathlib", "socket", "subprocess", "requests", "urllib",
        "uuid", "random", "datetime"}.isdisjoint(imported)
    for forbidden in ("open(", "os.environ", "subprocess", "execute_rollback(",
            "deploy(", "activate_", "approve_", "rollback_artifact_identity"):
        assert forbidden not in source
