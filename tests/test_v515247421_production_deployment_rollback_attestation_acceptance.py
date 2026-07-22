from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.production_deployment_rollback_attestation_acceptance as acceptance
from brain.immutable_failure_response_state_containment import (
    create_failure_response_state_containment_binding,
)
from brain.production_deployment_artifact_evidence_foundation import (
    prepare_production_deployment_artifact_evidence,
)
from brain.production_deployment_rollback_attestation_foundation import (
    prepare_production_deployment_rollback_attestation_foundation,
)
from brain.production_failure_containment_acceptance import (
    create_production_failure_containment_acceptance_report,
)
from brain.production_feature_gate_release_owner import (
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
)
from brain.production_feature_gate_owner import LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
from brain.production_rollback_evidence_foundation import (
    create_production_rollback_evidence_foundation,
)
from brain.production_rollback_readiness_acceptance import (
    evaluate_production_rollback_readiness,
)
from test_v5152474151_verifiable_isolated_failure_containment_record import batch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_deployment_rollback_attestation_acceptance.py"


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
    deployment = prepare_production_deployment_artifact_evidence(readiness)
    foundation = prepare_production_deployment_rollback_attestation_foundation(
        deployment, rollback, readiness, containment)
    result = acceptance.evaluate_production_deployment_rollback_attestation_acceptance(
        foundation)
    assert acceptance.verify_production_deployment_rollback_attestation_acceptance(result)
    return owner, foundation, result


def test_canonical_prepared_foundation_is_accepted_policy_only(artifacts):
    _, foundation, result = artifacts
    assert result.status == acceptance.ACCEPTED
    assert result.accepted is True
    assert acceptance.classify_production_deployment_rollback_attestation_acceptance(
        foundation) == acceptance.ACCEPTED
    assert not result.successful_attestation


def test_repeated_construction_and_acceptance_digest_are_stable(artifacts):
    result = artifacts[2]
    duplicate = acceptance.evaluate_production_deployment_rollback_attestation_acceptance(
        artifacts[1])
    assert duplicate == result
    assert duplicate.acceptance_digest == result.acceptance_digest
    assert duplicate.topology_digest == result.topology_digest


def test_canonical_acceptance_policy_is_frozen_and_verified(artifacts):
    policy = artifacts[2].policy
    assert policy is acceptance.CANONICAL_ACCEPTANCE_POLICY
    assert policy.identity == acceptance.POLICY_IDENTITY
    assert policy.version == acceptance.POLICY_VERSION
    assert policy.required_checks == acceptance.CHECK_ORDER
    assert acceptance.verify_production_deployment_rollback_attestation_acceptance_policy(policy)
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.identity = "forged"


def test_exact_foundation_subject_policy_and_lineage_bindings(artifacts):
    foundation, result = artifacts[1:]
    subject = foundation.subject
    assert result.foundation is foundation
    assert result.attestation_foundation_digest == foundation.foundation_digest
    assert result.attestation_subject_digest == foundation.subject_digest
    assert result.attestation_policy_digest == foundation.policy_digest
    assert result.proposal_digest == subject.proposal_digest
    assert result.requested_state is subject.requested_state is True
    assert result.proposal_revision == subject.proposal_revision
    assert result.feature_gate_identity == subject.feature_gate_identity
    assert result.runtime_configuration_digest == subject.runtime_configuration_digest
    assert result.deployment_artifact_evidence_digest == subject.deployment_artifact_evidence_digest
    assert result.rollback_evidence_digest == subject.rollback_evidence_digest
    assert result.rollback_target_digest == subject.rollback_target_digest
    assert result.rollback_readiness_acceptance_digest == subject.rollback_readiness_acceptance_digest
    assert result.failure_containment_acceptance_digest == subject.failure_containment_acceptance_digest


def test_exact_ordered_unique_acceptance_checks(artifacts):
    result = artifacts[2]
    assert tuple(item.check_id for item in result.checks) == acceptance.CHECK_ORDER
    assert tuple(item.ordinal for item in result.checks) == tuple(range(1, 38))
    assert len(set(acceptance.CHECK_ORDER)) == 37
    assert all(acceptance.verify_production_deployment_rollback_attestation_acceptance_check(item)
        for item in result.checks)


def test_acceptance_boundary_invariants_remain_false(artifacts):
    result = artifacts[2]
    assert not any((result.transition_approved, result.feature_gate_mutated,
        result.deployment_executed, result.rollback_executed,
        result.activation_permitted, result.approval_permitted,
        result.runtime_mutated, result.successful_attestation))
    assert result.executable_output is None and result.issues == ()


def test_acceptance_result_is_immutable(artifacts):
    result = artifacts[2]
    assert result.__dataclass_params__.frozen
    assert result.checks[0].__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = acceptance.REJECTED


@pytest.mark.parametrize("value", ({}, [], True, "accepted", object(), None))
def test_invalid_foundation_types_are_deterministically_rejected(value):
    assert acceptance.evaluate_production_deployment_rollback_attestation_acceptance(value) is None
    assert acceptance.classify_production_deployment_rollback_attestation_acceptance(
        value) == acceptance.REJECTED


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"),
    ("status", "DEPLOYMENT_ROLLBACK_ATTESTATION_REJECTED"),
    ("policy_digest", "0" * 64), ("subject_digest", "0" * 64),
    ("deployment_evidence_digest", "0" * 64),
    ("rollback_evidence_digest", "0" * 64),
    ("rollback_readiness_digest", "0" * 64),
    ("failure_containment_digest", "0" * 64),
    ("foundation_digest", "0" * 64),
))
def test_forged_foundation_schema_status_and_lineage_rejected(artifacts, field, value):
    forged = dataclasses.replace(artifacts[1], **{field: value})
    assert acceptance.evaluate_production_deployment_rollback_attestation_acceptance(forged) is None


def test_subclassed_foundation_rejected(artifacts):
    foundation = artifacts[1]
    class FoundationSpoof(type(foundation)):
        pass
    spoof = FoundationSpoof(**{field.name: getattr(foundation, field.name)
        for field in dataclasses.fields(foundation)})
    assert acceptance.evaluate_production_deployment_rollback_attestation_acceptance(spoof) is None


def test_missing_extra_duplicate_reordered_and_altered_foundation_checks_rejected(artifacts):
    foundation = artifacts[1]
    checks = foundation.checks
    extra = dataclasses.replace(checks[-1], check_id="EXTRA", ordinal=27)
    variants = (
        checks[:-1], checks + (extra,), (checks[0],) * len(checks), checks[::-1],
        (dataclasses.replace(checks[0], verified=False),) + checks[1:],
        (dataclasses.replace(checks[0], check_digest="0" * 64),) + checks[1:],
    )
    for variant in variants:
        forged = dataclasses.replace(foundation, checks=variant)
        assert acceptance.evaluate_production_deployment_rollback_attestation_acceptance(
            forged) is None


@pytest.mark.parametrize("field", (
    "transition_approved", "feature_gate_mutated", "deployment_executed",
    "rollback_executed", "activation_permitted", "approval_permitted",
    "runtime_mutated", "successful_attestation",
))
def test_altered_foundation_boundary_flag_rejected(artifacts, field):
    forged = dataclasses.replace(artifacts[1], **{field: True})
    assert acceptance.evaluate_production_deployment_rollback_attestation_acceptance(forged) is None


@pytest.mark.parametrize("path,field,value", (
    ("deployment_evidence", "evidence_digest", "0" * 64),
    ("deployment_evidence", "proposal_id", "0" * 64),
    ("deployment_evidence", "feature_gate_name", "OTHER"),
    ("deployment_evidence", "runtime_configuration_digest", "0" * 64),
    ("rollback_evidence", "foundation_digest", "0" * 64),
    ("rollback_evidence", "proposal_digest", "0" * 64),
    ("rollback_evidence", "rollback_artifact_digest", "0" * 64),
    ("rollback_evidence", "rollback_target_digest", "0" * 64),
    ("rollback_readiness", "acceptance_digest", "0" * 64),
    ("rollback_readiness", "status", "ROLLBACK_READINESS_REJECTED"),
    ("rollback_readiness", "accepted", False),
    ("failure_containment", "report_digest", "0" * 64),
    ("failure_containment", "accepted", False),
))
def test_invalid_nested_upstream_and_cross_bindings_rejected(
        artifacts, path, field, value):
    foundation = artifacts[1]
    nested = dataclasses.replace(getattr(foundation, path), **{field: value})
    forged = dataclasses.replace(foundation, **{path: nested})
    assert acceptance.evaluate_production_deployment_rollback_attestation_acceptance(forged) is None


@pytest.mark.parametrize("field,value", (
    ("policy_identity", "FORGED"), ("policy_version", "0"),
    ("policy_digest", "0" * 64), ("attestation_foundation_digest", "0" * 64),
    ("attestation_subject_digest", "0" * 64),
    ("attestation_policy_digest", "0" * 64), ("proposal_digest", "0" * 64),
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
    ("rollback_target_identity", "FORGED"), ("rollback_target_digest", "0" * 64),
    ("rollback_readiness_acceptance_digest", "0" * 64),
    ("failure_containment_acceptance_digest", "0" * 64),
    ("topology_digest", "0" * 64), ("acceptance_digest", "0" * 64),
))
def test_acceptance_binding_policy_and_digest_tampering_rejected(
        artifacts, field, value):
    forged = dataclasses.replace(artifacts[2], **{field: value})
    assert not acceptance.verify_production_deployment_rollback_attestation_acceptance(forged)


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"), ("status", acceptance.REJECTED),
    ("status", "SUCCESSFUL_OPERATIONAL_ATTESTATION"),
    ("accepted", False), ("issues", ("FORGED",)),
))
def test_noncanonical_acceptance_identity_status_and_result_rejected(
        artifacts, field, value):
    forged = dataclasses.replace(artifacts[2], **{field: value})
    assert not acceptance.verify_production_deployment_rollback_attestation_acceptance(forged)


@pytest.mark.parametrize("field", (
    "transition_approved", "feature_gate_mutated", "deployment_executed",
    "rollback_executed", "activation_permitted", "approval_permitted",
    "runtime_mutated", "successful_attestation",
))
def test_caller_supplied_pass_approval_attestation_activation_rejected(artifacts, field):
    forged = dataclasses.replace(artifacts[2], **{field: True})
    assert not acceptance.verify_production_deployment_rollback_attestation_acceptance(forged)


def test_noncanonical_acceptance_policy_rejected(artifacts):
    result = artifacts[2]
    variants = (
        dataclasses.replace(result.policy, identity="forged"),
        dataclasses.replace(result.policy, version="0"),
        dataclasses.replace(result.policy, required_checks=result.policy.required_checks[::-1]),
        dataclasses.replace(result.policy, policy_digest="0" * 64),
    )
    for policy in variants:
        assert not acceptance.verify_production_deployment_rollback_attestation_acceptance_policy(policy)
        assert not acceptance.verify_production_deployment_rollback_attestation_acceptance(
            dataclasses.replace(result, policy=policy))


def test_missing_extra_duplicate_reordered_mutable_and_altered_acceptance_checks_rejected(
        artifacts):
    result = artifacts[2]
    checks = result.checks
    extra = dataclasses.replace(checks[-1], check_id="EXTRA", ordinal=38)
    variants = (
        checks[:-1], checks + (extra,), (checks[0],) * len(checks), checks[::-1],
        list(checks), (dataclasses.replace(checks[0], verified=False),) + checks[1:],
        (dataclasses.replace(checks[0], evidence_digests=[]),) + checks[1:],
        (dataclasses.replace(checks[0], check_digest="0" * 64),) + checks[1:],
    )
    for variant in variants:
        assert not acceptance.verify_production_deployment_rollback_attestation_acceptance(
            dataclasses.replace(result, checks=variant))


def test_acceptance_subclass_spoofing_rejected(artifacts):
    result = artifacts[2]
    class AcceptanceSpoof(type(result)):
        pass
    spoof = AcceptanceSpoof(**{field.name: getattr(result, field.name)
        for field in dataclasses.fields(result)})
    assert not acceptance.verify_production_deployment_rollback_attestation_acceptance(spoof)


def test_foundation_upstream_and_gate_owner_not_mutated(artifacts):
    owner, foundation, _ = artifacts
    before = foundation
    acceptance.evaluate_production_deployment_rollback_attestation_acceptance(foundation)
    assert foundation == before
    assert owner is get_production_feature_gate_release_owner()
    assert owner.default_denied and not owner.activation_permitted


def test_narrow_constructor_accepts_only_canonical_foundation():
    assert tuple(inspect.signature(
        acceptance.evaluate_production_deployment_rollback_attestation_acceptance
        ).parameters) == ("attestation_foundation",)


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
