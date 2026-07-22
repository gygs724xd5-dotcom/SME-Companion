from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.production_rollback_readiness_acceptance as acceptance
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
from test_v5152474151_verifiable_isolated_failure_containment_record import batch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_rollback_readiness_acceptance.py"


@pytest.fixture(scope="module")
def artifacts():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    failure_batch = batch()
    state = create_failure_response_state_containment_binding(failure_batch)
    containment = create_production_failure_containment_acceptance_report(failure_batch, state)
    foundation = create_production_rollback_evidence_foundation(owner, proposal, containment)
    result = acceptance.evaluate_production_rollback_readiness(foundation)
    assert acceptance.verify_production_rollback_readiness_acceptance(result)
    return foundation, result


def test_canonical_acceptance_and_deterministic_digest(artifacts):
    foundation, result = artifacts
    duplicate = acceptance.evaluate_production_rollback_readiness(foundation)
    assert duplicate == result
    assert duplicate.acceptance_digest == result.acceptance_digest
    assert result.status == acceptance.ACCEPTED
    assert result.accepted and result.readiness_evidence_permitted
    assert acceptance.classify_production_rollback_readiness(foundation) == acceptance.ACCEPTED


def test_exact_foundation_proposal_revision_and_gate_binding(artifacts):
    foundation, result = artifacts
    assert result.foundation is foundation
    assert result.foundation_digest == foundation.foundation_digest
    assert result.release_owner_digest == foundation.release_owner_digest
    assert result.release_revision_id == foundation.release_revision_id
    assert result.release_revision_digest == foundation.release_revision_digest
    assert result.proposal_digest == foundation.proposal_digest
    assert result.feature_gate_identity == LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
    assert result.requested_target_state is True


def test_exact_rollback_target_artifact_and_configuration_binding(artifacts):
    foundation, result = artifacts
    for field in ("rollback_target_identity", "rollback_target_digest",
            "rollback_artifact_identity", "rollback_artifact_digest",
            "rollback_configuration_identity", "rollback_configuration_digest"):
        assert getattr(result, field) == getattr(foundation, field)


def test_failure_containment_lineage_is_bound(artifacts):
    foundation, result = artifacts
    assert result.containment_report_digest == foundation.containment_report_digest
    assert result.containment_topology_digest == foundation.containment_topology_digest
    assert result.checks[8].evidence_digests == (
        foundation.containment_report_digest, foundation.containment_topology_digest)


def test_ordered_unique_verified_checks(artifacts):
    result = artifacts[1]
    assert tuple(item.check_id for item in result.checks) == acceptance.CHECK_ORDER
    assert tuple(item.ordinal for item in result.checks) == tuple(range(1, 12))
    assert len(set(acceptance.CHECK_ORDER)) == 11
    assert all(item.verified and acceptance.verify_production_rollback_readiness_check(item)
        for item in result.checks)
    assert result.issues == ()


def test_readiness_is_not_deployment_approval_activation_or_rollback(artifacts):
    result = artifacts[1]
    assert not any((result.deployment_attested, result.rollback_executed,
        result.transition_approved, result.activation_permitted,
        result.mutation_permitted))
    assert result.executable_output is None
    assert all(not getattr(result.authority_boundary, field)
        for field in result.authority_boundary.__dataclass_fields__)


def test_frozen_contracts(artifacts):
    result = artifacts[1]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = acceptance.REJECTED
    assert acceptance.ProductionRollbackReadinessCheck.__dataclass_params__.frozen
    assert acceptance.ProductionRollbackReadinessAcceptance.__dataclass_params__.frozen
    assert acceptance.ProductionRollbackReadinessAuthorityBoundary.__dataclass_params__.frozen


@pytest.mark.parametrize("value", ({}, [], True, "accepted", object(), None))
def test_wrong_types_fail_closed(value):
    assert acceptance.evaluate_production_rollback_readiness(value) is None
    assert acceptance.classify_production_rollback_readiness(value) == acceptance.REJECTED
    assert not acceptance.verify_production_rollback_readiness_acceptance(value)


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"), ("foundation_digest", "0" * 64),
    ("release_owner_digest", "0" * 64), ("release_revision_id", "forged"),
    ("release_revision_digest", "0" * 64), ("proposal_digest", "0" * 64),
    ("feature_gate_identity", "OTHER"), ("requested_target_state", False),
    ("rollback_target_identity", "FORGED"), ("rollback_target_digest", "0" * 64),
    ("rollback_artifact_identity", "FORGED"), ("rollback_artifact_digest", "0" * 64),
    ("rollback_configuration_identity", "FORGED"),
    ("rollback_configuration_digest", "0" * 64),
    ("containment_report_digest", "0" * 64),
    ("containment_topology_digest", "0" * 64),
    ("topology_digest", "0" * 64), ("acceptance_digest", "0" * 64),
))
def test_identity_binding_and_digest_tampering_rejected(artifacts, field, value):
    forged = dataclasses.replace(artifacts[1], **{field: value})
    assert not acceptance.verify_production_rollback_readiness_acceptance(forged)


@pytest.mark.parametrize("field,value", (
    ("status", acceptance.REJECTED), ("accepted", False),
    ("readiness_evidence_permitted", False),
    ("issues", ("FORGED",)), ("deployment_attested", True),
    ("rollback_executed", True), ("transition_approved", True),
    ("activation_permitted", True), ("mutation_permitted", True),
    ("executable_output", object()),
))
def test_decision_authority_and_execution_tampering_rejected(artifacts, field, value):
    forged = dataclasses.replace(artifacts[1], **{field: value})
    assert not acceptance.verify_production_rollback_readiness_acceptance(forged)


def test_check_reorder_drop_duplicate_unknown_and_tamper_rejected(artifacts):
    result = artifacts[1]
    checks = result.checks
    variants = (
        checks[::-1], checks[:-1], (checks[0],) * len(checks),
        (dataclasses.replace(checks[0], check_id="UNKNOWN"),) + checks[1:],
        (dataclasses.replace(checks[0], ordinal=2),) + checks[1:],
        (dataclasses.replace(checks[0], verified=False),) + checks[1:],
        (dataclasses.replace(checks[0], evidence_digests=()),) + checks[1:],
        (dataclasses.replace(checks[0], reason=""),) + checks[1:],
        (dataclasses.replace(checks[0], check_digest="0" * 64),) + checks[1:],
    )
    for variant in variants:
        assert not acceptance.verify_production_rollback_readiness_acceptance(
            dataclasses.replace(result, checks=variant))


def test_nested_foundation_tampering_is_not_reconstructed(artifacts):
    foundation, _ = artifacts
    for field, value in (
        ("foundation_digest", "0" * 64),
        ("rollback_artifact_digest", "0" * 64),
        ("default_deny_restoration", False),
        ("readiness_accepted", True),
        ("rollback_executed", True),
    ):
        changed = dataclasses.replace(foundation, **{field: value})
        assert acceptance.evaluate_production_rollback_readiness(changed) is None


def test_authority_boundary_injection_rejected(artifacts):
    result = artifacts[1]
    for field in result.authority_boundary.__dataclass_fields__:
        boundary = dataclasses.replace(result.authority_boundary, **{field: True})
        assert not acceptance.verify_production_rollback_readiness_acceptance(
            dataclasses.replace(result, authority_boundary=boundary))


def test_module_does_not_mutate_foundation(artifacts):
    foundation, _ = artifacts
    before = foundation
    acceptance.evaluate_production_rollback_readiness(foundation)
    assert foundation == before


def test_narrow_api_has_no_caller_pass_approval_or_acceptance():
    assert tuple(inspect.signature(
        acceptance.evaluate_production_rollback_readiness).parameters) == (
        "evidence_foundation",)
    assert tuple(inspect.signature(
        acceptance.verify_production_rollback_readiness_acceptance).parameters) == ("value",)
    assert tuple(inspect.signature(
        acceptance.classify_production_rollback_readiness).parameters) == (
        "evidence_foundation",)


def test_static_no_environment_file_network_subprocess_or_operational_calls():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {"os", "pathlib", "socket", "subprocess", "requests", "urllib"}.isdisjoint(imported)
    for forbidden in ("open(", "os.environ", "subprocess", "execute_rollback(",
            "apply_rollback(", "activate_", "approve_", "git "):
        assert forbidden not in source
    assert not any(name.startswith(("execute_", "apply_", "activate_", "approve_"))
        for name in vars(acceptance))
