from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.operational_failure_containment_evidence_acceptance as acceptance
from brain.immutable_failure_response_state_containment import (
    create_failure_response_state_containment_binding,
)
from brain.operational_failure_containment_evidence_foundation import (
    prepare_operational_failure_containment_evidence_foundation,
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
MODULE = ROOT / "brain" / "operational_failure_containment_evidence_acceptance.py"


@pytest.fixture(scope="module")
def artifacts():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    failure_batch = batch()
    state = create_failure_response_state_containment_binding(failure_batch)
    containment = create_production_failure_containment_acceptance_report(
        failure_batch, state)
    rollback = create_production_rollback_evidence_foundation(owner, proposal, containment)
    readiness = evaluate_production_rollback_readiness(rollback)
    deployment = prepare_production_deployment_artifact_evidence(readiness)
    foundation = prepare_operational_failure_containment_evidence_foundation(
        "RUNTIME_EXCEPTION", deployment, containment)
    result = acceptance.evaluate_operational_failure_containment_evidence_acceptance(
        foundation)
    assert acceptance.verify_operational_failure_containment_evidence_acceptance(result)
    return owner, foundation, result


def test_canonical_foundation_is_deterministically_accepted(artifacts):
    foundation, result = artifacts[1:]
    duplicate = acceptance.evaluate_operational_failure_containment_evidence_acceptance(
        foundation)
    assert duplicate == result
    assert result.status == acceptance.ACCEPTED and result.accepted is True
    assert acceptance.classify_operational_failure_containment_evidence_acceptance(
        foundation) == acceptance.ACCEPTED


def test_policy_and_exact_foundation_evidence_bindings(artifacts):
    foundation, result = artifacts[1:]
    evidence = foundation.evidence
    assert result.policy is acceptance.CANONICAL_ACCEPTANCE_POLICY
    assert acceptance.verify_operational_failure_containment_evidence_acceptance_policy(
        result.policy)
    assert result.foundation is foundation
    assert result.foundation_digest == foundation.foundation_digest
    assert result.foundation_topology_digest == foundation.topology_digest
    assert result.incident_identity_digest == foundation.incident_identity_digest
    assert result.incident_type == evidence.incident_identity.incident_type
    for field in ("proposal_digest", "requested_state", "release_revision_id",
            "release_revision_digest", "runtime_configuration_identity",
            "runtime_configuration_digest", "feature_gate_identity",
            "feature_gate_state", "deployment_artifact_identity",
            "deployment_artifact_digest", "deployment_evidence_digest",
            "failure_containment_acceptance_digest",
            "failure_containment_topology_digest", "evidence_digest"):
        assert getattr(result, field) == getattr(evidence, field)


def test_ordered_unique_checks_and_passive_boundaries(artifacts):
    result = artifacts[2]
    assert tuple(item.check_id for item in result.checks) == acceptance.CHECK_ORDER
    assert tuple(item.ordinal for item in result.checks) == tuple(
        range(1, len(acceptance.CHECK_ORDER) + 1))
    assert len(set(acceptance.CHECK_ORDER)) == len(acceptance.CHECK_ORDER)
    assert all(acceptance.verify_operational_failure_containment_evidence_acceptance_check(
        item) for item in result.checks)
    assert not any(getattr(result, name) for name in acceptance.BOUNDARY_FIELDS)
    assert result.executable_output is None and result.issues == ()


def test_contracts_are_frozen(artifacts):
    result = artifacts[2]
    for value in (result, result.policy, result.checks[0]):
        assert value.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.accepted = False


@pytest.mark.parametrize("value", ({}, [], True, "accepted", object(), None))
def test_wrong_types_fail_closed(value):
    assert acceptance.evaluate_operational_failure_containment_evidence_acceptance(
        value) is None
    assert acceptance.classify_operational_failure_containment_evidence_acceptance(
        value) == acceptance.REJECTED
    assert not acceptance.verify_operational_failure_containment_evidence_acceptance(value)


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("status", "FORGED"), ("foundation_digest", "0" * 64),
    ("topology_digest", "0" * 64), ("policy_digest", "0" * 64),
    ("incident_identity_digest", "0" * 64),
))
def test_forged_foundation_rejected(artifacts, field, value):
    forged = dataclasses.replace(artifacts[1], **{field: value})
    assert acceptance.evaluate_operational_failure_containment_evidence_acceptance(
        forged) is None


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"), ("status", acceptance.REJECTED),
    ("accepted", False), ("issues", ("FORGED",)),
    ("foundation_digest", "0" * 64), ("incident_type", "FORGED"),
    ("proposal_digest", "0" * 64), ("evidence_digest", "0" * 64),
    ("topology_digest", "0" * 64), ("acceptance_digest", "0" * 64),
))
def test_acceptance_identity_and_digest_tampering_rejected(artifacts, field, value):
    assert not acceptance.verify_operational_failure_containment_evidence_acceptance(
        dataclasses.replace(artifacts[2], **{field: value}))


@pytest.mark.parametrize("field", acceptance.BOUNDARY_FIELDS)
def test_caller_authority_and_operational_claims_rejected(artifacts, field):
    forged = dataclasses.replace(artifacts[2], **{field: True})
    assert not acceptance.verify_operational_failure_containment_evidence_acceptance(forged)


def test_check_and_policy_tampering_rejected(artifacts):
    result = artifacts[2]
    checks = result.checks
    variants = (checks[:-1], checks[::-1], list(checks),
        (checks[0],) * len(checks),
        (dataclasses.replace(checks[0], verified=False),) + checks[1:],
        (dataclasses.replace(checks[0], evidence_digests=[]),) + checks[1:],
        (dataclasses.replace(checks[0], check_digest="0" * 64),) + checks[1:])
    for variant in variants:
        assert not acceptance.verify_operational_failure_containment_evidence_acceptance(
            dataclasses.replace(result, checks=variant))
    forged_policy = dataclasses.replace(result.policy, identity="FORGED")
    assert not acceptance.verify_operational_failure_containment_evidence_acceptance_policy(
        forged_policy)
    assert not acceptance.verify_operational_failure_containment_evidence_acceptance(
        dataclasses.replace(result, policy=forged_policy))


def test_nested_foundation_tampering_and_subclasses_rejected(artifacts):
    foundation = artifacts[1]
    nested = dataclasses.replace(foundation.evidence, incident_observed=True)
    assert acceptance.evaluate_operational_failure_containment_evidence_acceptance(
        dataclasses.replace(foundation, evidence=nested)) is None

    class FoundationSpoof(type(foundation)):
        pass
    spoof = FoundationSpoof(**{field.name: getattr(foundation, field.name)
        for field in dataclasses.fields(foundation)})
    assert acceptance.evaluate_operational_failure_containment_evidence_acceptance(spoof) is None


def test_evaluation_does_not_mutate_foundation_or_owner(artifacts):
    owner, foundation, _ = artifacts
    before = foundation
    acceptance.evaluate_operational_failure_containment_evidence_acceptance(foundation)
    assert foundation == before
    assert owner is get_production_feature_gate_release_owner()
    assert owner.default_denied and not owner.activation_permitted


def test_narrow_api_and_static_non_operational_module():
    assert tuple(inspect.signature(
        acceptance.evaluate_operational_failure_containment_evidence_acceptance
        ).parameters) == ("evidence_foundation",)
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree)
        if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)}
    assert {"os", "pathlib", "socket", "subprocess", "requests", "urllib",
        "uuid", "random", "datetime"}.isdisjoint(imported)
    for forbidden in ("open(", "os.environ", "subprocess", "execute_",
            "deploy(", "activate_", "approve_"):
        assert forbidden not in source
