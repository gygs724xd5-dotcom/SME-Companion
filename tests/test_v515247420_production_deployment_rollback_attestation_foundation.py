from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.production_deployment_rollback_attestation_foundation as attestation
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
MODULE = ROOT / "brain" / "production_deployment_rollback_attestation_foundation.py"


@pytest.fixture(scope="module")
def chain():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    failure_batch = batch()
    state = create_failure_response_state_containment_binding(failure_batch)
    containment = create_production_failure_containment_acceptance_report(failure_batch, state)
    rollback = create_production_rollback_evidence_foundation(owner, proposal, containment)
    readiness = evaluate_production_rollback_readiness(rollback)
    deployment = prepare_production_deployment_artifact_evidence(readiness)
    result = attestation.prepare_production_deployment_rollback_attestation_foundation(
        deployment, rollback, readiness, containment)
    assert attestation.verify_production_deployment_rollback_attestation_foundation(result)
    return deployment, rollback, readiness, containment, result


def test_canonical_chain_prepares_foundation_only(chain):
    deployment, rollback, readiness, containment, result = chain
    assert result.status == attestation.PREPARED
    assert attestation.classify_production_deployment_rollback_attestation_foundation(
        deployment, rollback, readiness, containment) == attestation.PREPARED
    assert not result.successful_attestation


def test_repeated_construction_subject_and_foundation_digests_are_stable(chain):
    deployment, rollback, readiness, containment, result = chain
    duplicate = attestation.prepare_production_deployment_rollback_attestation_foundation(
        deployment, rollback, readiness, containment)
    assert duplicate == result
    assert duplicate.subject_digest == result.subject_digest
    assert duplicate.foundation_digest == result.foundation_digest


def test_policy_is_canonical_immutable_and_deterministic(chain):
    policy = chain[4].policy
    assert policy is attestation.CANONICAL_ATTESTATION_POLICY
    assert policy.identity == attestation.POLICY_IDENTITY
    assert policy.version == attestation.POLICY_VERSION
    assert policy.required_checks == attestation.CHECK_ORDER
    assert attestation.verify_production_deployment_rollback_attestation_policy(policy)
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.identity = "forged"


def test_subject_binds_exact_deployment_and_rollback_chain(chain):
    deployment, rollback, readiness, containment, result = chain
    subject = result.subject
    assert subject.proposal_digest == deployment.proposal_id == rollback.proposal_digest
    assert subject.requested_state is True
    assert subject.proposal_revision == deployment.proposal_revision == rollback.release_revision_id
    assert subject.feature_gate_identity == deployment.feature_gate_name == rollback.feature_gate_identity
    assert subject.runtime_configuration_identity == deployment.runtime_configuration_identity == rollback.rollback_configuration_identity
    assert subject.runtime_configuration_digest == deployment.runtime_configuration_digest == rollback.rollback_configuration_digest
    assert subject.deployment_artifact_identity == deployment.deployment_artifact_identity
    assert subject.deployment_artifact_digest == deployment.deployment_artifact_digest
    assert subject.rollback_artifact_identity == rollback.rollback_artifact_identity
    assert subject.rollback_artifact_digest == rollback.rollback_artifact_digest
    assert subject.rollback_target_digest == rollback.rollback_target_digest
    assert subject.rollback_readiness_acceptance_digest == readiness.acceptance_digest
    assert subject.failure_containment_acceptance_digest == containment.report_digest
    assert attestation.verify_production_deployment_rollback_attestation_subject(
        subject, deployment, rollback, readiness, containment)


def test_exact_ordered_unique_attestation_checks(chain):
    result = chain[4]
    assert tuple(item.check_id for item in result.checks) == attestation.CHECK_ORDER
    assert tuple(item.ordinal for item in result.checks) == tuple(range(1, 27))
    assert len(set(attestation.CHECK_ORDER)) == 26
    assert all(attestation.verify_production_deployment_rollback_attestation_check(item)
        for item in result.checks)


def test_boundary_invariants_all_remain_false(chain):
    result = chain[4]
    assert not any((result.transition_approved, result.feature_gate_mutated,
        result.deployment_executed, result.rollback_executed,
        result.activation_permitted, result.approval_permitted,
        result.runtime_mutated, result.successful_attestation))
    assert result.executable_output is None
    assert result.issues == ()


def test_all_contracts_are_frozen(chain):
    result = chain[4]
    for contract in (type(result), type(result.policy), type(result.subject),
            type(result.checks[0])):
        assert contract.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = attestation.REJECTED


@pytest.mark.parametrize("index", range(4))
def test_missing_wrong_or_noncanonical_upstream_is_rejected(chain, index):
    values = list(chain[:4])
    values[index] = None
    assert attestation.prepare_production_deployment_rollback_attestation_foundation(
        *values) is None
    assert attestation.classify_production_deployment_rollback_attestation_foundation(
        *values) == attestation.REJECTED


@pytest.mark.parametrize("field,value", (
    ("proposal_id", "0" * 64), ("requested_state", False),
    ("proposal_revision", "forged"), ("proposal_revision_digest", "0" * 64),
    ("feature_gate_name", "OTHER"), ("feature_gate_requested_state", False),
    ("runtime_configuration_identity", "FORGED"),
    ("runtime_configuration_digest", "0" * 64),
    ("deployment_artifact_identity", "0" * 64),
    ("deployment_artifact_digest", "0" * 64),
    ("evidence_digest", "0" * 64), ("status", "DEPLOYED"),
))
def test_invalid_deployment_evidence_and_cross_bindings_rejected(chain, field, value):
    deployment, rollback, readiness, containment, _ = chain
    changed = dataclasses.replace(deployment, **{field: value})
    assert attestation.prepare_production_deployment_rollback_attestation_foundation(
        changed, rollback, readiness, containment) is None


@pytest.mark.parametrize("field,value", (
    ("proposal_digest", "0" * 64), ("requested_target_state", False),
    ("release_revision_id", "forged"), ("release_revision_digest", "0" * 64),
    ("feature_gate_identity", "OTHER"),
    ("rollback_configuration_identity", "FORGED"),
    ("rollback_configuration_digest", "0" * 64),
    ("rollback_target_identity", "FORGED"), ("rollback_target_digest", "0" * 64),
    ("rollback_artifact_identity", "FORGED"),
    ("rollback_artifact_digest", "0" * 64),
    ("foundation_digest", "0" * 64),
))
def test_invalid_rollback_evidence_target_artifact_and_cross_bindings_rejected(
        chain, field, value):
    deployment, rollback, readiness, containment, _ = chain
    changed = dataclasses.replace(rollback, **{field: value})
    assert attestation.prepare_production_deployment_rollback_attestation_foundation(
        deployment, changed, readiness, containment) is None


@pytest.mark.parametrize("field,value", (
    ("status", "ROLLBACK_READINESS_REJECTED"), ("accepted", False),
    ("proposal_digest", "0" * 64), ("release_revision_id", "forged"),
    ("feature_gate_identity", "OTHER"),
    ("rollback_configuration_identity", "FORGED"),
    ("rollback_configuration_digest", "0" * 64),
    ("rollback_target_digest", "0" * 64),
    ("rollback_artifact_digest", "0" * 64),
    ("acceptance_digest", "0" * 64),
))
def test_invalid_readiness_status_digest_and_cross_bindings_rejected(
        chain, field, value):
    deployment, rollback, readiness, containment, _ = chain
    changed = dataclasses.replace(readiness, **{field: value})
    assert attestation.prepare_production_deployment_rollback_attestation_foundation(
        deployment, rollback, changed, containment) is None


@pytest.mark.parametrize("field,value", (
    ("report_digest", "0" * 64), ("topology_digest", "0" * 64),
    ("accepted", False), ("production_default_denied", False),
))
def test_invalid_failure_containment_lineage_rejected(chain, field, value):
    deployment, rollback, readiness, containment, _ = chain
    changed = dataclasses.replace(containment, **{field: value})
    assert attestation.prepare_production_deployment_rollback_attestation_foundation(
        deployment, rollback, readiness, changed) is None


def test_equal_but_nonidentical_nested_chain_substitution_rejected(chain):
    deployment, rollback, readiness, containment, _ = chain
    copied_readiness = dataclasses.replace(readiness)
    copied_deployment = dataclasses.replace(deployment, readiness_acceptance=copied_readiness)
    assert attestation.prepare_production_deployment_rollback_attestation_foundation(
        copied_deployment, rollback, readiness, containment) is None
    copied_rollback = dataclasses.replace(rollback)
    copied_readiness = dataclasses.replace(readiness, foundation=copied_rollback)
    assert attestation.prepare_production_deployment_rollback_attestation_foundation(
        deployment, rollback, copied_readiness, containment) is None


@pytest.mark.parametrize("field,value", (
    ("schema", "forged"), ("policy_identity", "forged"),
    ("policy_version", "0"), ("proposal_digest", "0" * 64),
    ("requested_state", False), ("proposal_revision", "forged"),
    ("proposal_revision_digest", "0" * 64),
    ("feature_gate_identity", "OTHER"), ("feature_gate_requested_state", False),
    ("runtime_configuration_identity", "FORGED"),
    ("runtime_configuration_digest", "0" * 64),
    ("deployment_artifact_identity", "0" * 64),
    ("deployment_artifact_digest", "0" * 64),
    ("deployment_artifact_evidence_digest", "0" * 64),
    ("rollback_artifact_identity", "FORGED"),
    ("rollback_artifact_digest", "0" * 64),
    ("rollback_evidence_digest", "0" * 64),
    ("rollback_target_identity", "FORGED"),
    ("rollback_target_digest", "0" * 64),
    ("rollback_readiness_acceptance_digest", "0" * 64),
    ("failure_containment_acceptance_digest", "0" * 64),
    ("subject_digest", "0" * 64),
))
def test_subject_binding_and_digest_tampering_rejected(chain, field, value):
    deployment, rollback, readiness, containment, result = chain
    changed = dataclasses.replace(result.subject, **{field: value})
    assert not attestation.verify_production_deployment_rollback_attestation_subject(
        changed, deployment, rollback, readiness, containment)
    assert not attestation.verify_production_deployment_rollback_attestation_foundation(
        dataclasses.replace(result, subject=changed))


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"), ("status", attestation.REJECTED),
    ("status", "SUCCESSFUL_ATTESTATION"), ("policy_digest", "0" * 64),
    ("subject_digest", "0" * 64), ("deployment_evidence_digest", "0" * 64),
    ("rollback_evidence_digest", "0" * 64),
    ("rollback_readiness_digest", "0" * 64),
    ("failure_containment_digest", "0" * 64), ("issues", ("FORGED",)),
    ("topology_digest", "0" * 64), ("foundation_digest", "0" * 64),
))
def test_foundation_status_lineage_and_digest_tampering_rejected(chain, field, value):
    forged = dataclasses.replace(chain[4], **{field: value})
    assert not attestation.verify_production_deployment_rollback_attestation_foundation(forged)


@pytest.mark.parametrize("field", (
    "transition_approved", "feature_gate_mutated", "deployment_executed",
    "rollback_executed", "activation_permitted", "approval_permitted",
    "runtime_mutated", "successful_attestation",
))
def test_caller_supplied_pass_approval_attestation_and_execution_rejected(chain, field):
    forged = dataclasses.replace(chain[4], **{field: True})
    assert not attestation.verify_production_deployment_rollback_attestation_foundation(forged)


def test_noncanonical_policy_rejected(chain):
    result = chain[4]
    variants = (
        dataclasses.replace(result.policy, identity="forged"),
        dataclasses.replace(result.policy, version="0"),
        dataclasses.replace(result.policy, required_checks=result.policy.required_checks[::-1]),
        dataclasses.replace(result.policy, policy_digest="0" * 64),
    )
    for policy in variants:
        assert not attestation.verify_production_deployment_rollback_attestation_policy(policy)
        assert not attestation.verify_production_deployment_rollback_attestation_foundation(
            dataclasses.replace(result, policy=policy))


def test_missing_extra_duplicate_reordered_mutable_and_altered_checks_rejected(chain):
    result = chain[4]
    checks = result.checks
    extra = dataclasses.replace(checks[-1], check_id="EXTRA", ordinal=27)
    variants = (
        checks[:-1], checks + (extra,), (checks[0],) * len(checks), checks[::-1],
        list(checks),
        (dataclasses.replace(checks[0], verified=False),) + checks[1:],
        (dataclasses.replace(checks[0], evidence_digests=[]),) + checks[1:],
        (dataclasses.replace(checks[0], check_digest="0" * 64),) + checks[1:],
    )
    for variant in variants:
        assert not attestation.verify_production_deployment_rollback_attestation_foundation(
            dataclasses.replace(result, checks=variant))


def test_exact_type_and_subclass_spoofing_rejected(chain):
    class SubjectSpoof(attestation.ProductionDeploymentRollbackAttestationSubject):
        pass
    class FoundationSpoof(attestation.ProductionDeploymentRollbackAttestationFoundation):
        pass
    deployment, rollback, readiness, containment, result = chain
    subject = SubjectSpoof(**{field.name: getattr(result.subject, field.name)
        for field in dataclasses.fields(result.subject)})
    assert not attestation.verify_production_deployment_rollback_attestation_subject(
        subject, deployment, rollback, readiness, containment)
    foundation = FoundationSpoof(**{field.name: getattr(result, field.name)
        for field in dataclasses.fields(result)})
    assert not attestation.verify_production_deployment_rollback_attestation_foundation(foundation)


def test_upstream_objects_and_gate_owner_are_not_mutated(chain):
    deployment, rollback, readiness, containment, _ = chain
    before = (deployment, rollback, readiness, containment)
    owner = get_production_feature_gate_release_owner()
    attestation.prepare_production_deployment_rollback_attestation_foundation(*before)
    assert before == (deployment, rollback, readiness, containment)
    assert owner is get_production_feature_gate_release_owner()
    assert owner.default_denied and not owner.activation_permitted


def test_narrow_constructor_has_no_raw_pass_approval_attestation_fields():
    assert tuple(inspect.signature(
        attestation.prepare_production_deployment_rollback_attestation_foundation
        ).parameters) == ("deployment_evidence", "rollback_evidence",
            "rollback_readiness", "failure_containment")


def test_static_no_environment_file_network_subprocess_or_operational_calls():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {"os", "pathlib", "socket", "subprocess", "requests", "urllib",
        "uuid", "random", "datetime"}.isdisjoint(imported)
    for forbidden in ("open(", "os.environ", "subprocess", "deploy(",
            "execute_rollback(", "activate_", "approve_"):
        assert forbidden not in source
