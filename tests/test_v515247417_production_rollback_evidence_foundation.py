from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

import brain.production_rollback_evidence_foundation as foundation
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
from test_v5152474151_verifiable_isolated_failure_containment_record import batch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_rollback_evidence_foundation.py"


@pytest.fixture(scope="module")
def artifacts():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    failure_batch = batch()
    binding = create_failure_response_state_containment_binding(failure_batch)
    containment = create_production_failure_containment_acceptance_report(
        failure_batch, binding)
    value = foundation.create_production_rollback_evidence_foundation(
        owner, proposal, containment)
    assert foundation.verify_production_rollback_evidence_foundation(value)
    return owner, proposal, containment, value


def test_canonical_valid_deterministic_construction(artifacts):
    owner, proposal, containment, value = artifacts
    duplicate = foundation.create_production_rollback_evidence_foundation(
        owner, proposal, containment)
    assert duplicate == value
    assert duplicate.foundation_digest == value.foundation_digest
    assert value.status == "ROLLBACK_EVIDENCE_BOUND_NOT_ATTESTED"


def test_exact_proposal_revision_gate_and_target_binding(artifacts):
    owner, proposal, _, value = artifacts
    assert value.release_owner_digest == owner.owner_digest
    assert value.release_revision_id == owner.release_revision.revision_id
    assert value.release_revision_digest == owner.release_revision.revision_digest
    assert value.proposal_digest == proposal.proposal_digest
    assert value.feature_gate_identity == LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
    assert value.requested_target_state is True
    assert value.rollback_target_digest == owner.rollback_target.rollback_digest


def test_artifact_configuration_and_default_deny_are_digest_bound(artifacts):
    owner, _, _, value = artifacts
    assert value.rollback_artifact_kind == foundation.ROLLBACK_ARTIFACT_KIND
    assert value.rollback_artifact_identity
    assert len(value.rollback_artifact_digest) == 64
    assert value.rollback_configuration_digest == owner.configuration_digest
    assert value.rollback_entries == ()
    assert value.default_deny_restoration is True


def test_containment_lineage_and_verification_requirements_are_exact(artifacts):
    _, _, containment, value = artifacts
    assert value.containment_report_digest == containment.report_digest
    assert value.containment_topology_digest == containment.topology_digest
    assert value.in_flight_policy == foundation.IN_FLIGHT_POLICY
    assert value.verification_requirements == foundation.VERIFICATION_REQUIREMENTS
    assert value.evidence_lineage[-2:] == (
        containment.report_digest, containment.topology_digest)


def test_foundation_is_not_readiness_attestation_approval_or_execution(artifacts):
    value = artifacts[3]
    assert not any((value.rollback_attested, value.deployment_attested,
        value.readiness_accepted, value.approval_evidence_permitted,
        value.activation_permitted, value.mutation_permitted,
        value.rollback_executed))
    assert value.executable_output is None
    assert all(not getattr(value.authority_boundary, name)
        for name in value.authority_boundary.__dataclass_fields__)


def test_immutable_contracts(artifacts):
    value = artifacts[3]
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.status = "FORGED"
    assert foundation.ProductionRollbackEvidenceFoundation.__dataclass_params__.frozen
    assert foundation.ProductionRollbackEvidenceAuthorityBoundary.__dataclass_params__.frozen


@pytest.mark.parametrize("value", ({}, [], True, "accepted", object(), None))
def test_wrong_types_fail_closed(value):
    assert not foundation.verify_production_rollback_evidence_foundation(value)


@pytest.mark.parametrize("field,value", (
    ("version", "0"), ("scope", "FORGED"), ("status", "READY"),
    ("release_owner_digest", "0" * 64), ("release_revision_id", "forged"),
    ("release_revision_digest", "0" * 64), ("proposal_digest", "0" * 64),
    ("feature_gate_identity", "OTHER"), ("requested_target_state", False),
    ("rollback_target_identity", "FORGED"), ("rollback_target_digest", "0" * 64),
    ("rollback_artifact_kind", "FORGED"), ("rollback_artifact_identity", "FORGED"),
    ("rollback_artifact_digest", "0" * 64),
    ("rollback_configuration_identity", "FORGED"),
    ("rollback_configuration_digest", "0" * 64),
    ("rollback_entries", ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),)),
    ("default_deny_restoration", False), ("in_flight_policy", "FORGED"),
    ("containment_report_digest", "0" * 64),
    ("containment_topology_digest", "0" * 64),
    ("foundation_digest", "0" * 64),
))
def test_material_and_digest_tampering_fails_closed(artifacts, field, value):
    forged = dataclasses.replace(artifacts[3], **{field: value})
    assert not foundation.verify_production_rollback_evidence_foundation(forged)


@pytest.mark.parametrize("field", (
    "rollback_attested", "deployment_attested", "readiness_accepted",
    "approval_evidence_permitted", "activation_permitted", "mutation_permitted",
    "rollback_executed",
))
def test_caller_supplied_outcomes_and_authority_rejected(artifacts, field):
    forged = dataclasses.replace(artifacts[3], **{field: True})
    assert not foundation.verify_production_rollback_evidence_foundation(forged)


def test_authority_boundary_injection_rejected(artifacts):
    value = artifacts[3]
    for field in value.authority_boundary.__dataclass_fields__:
        boundary = dataclasses.replace(value.authority_boundary, **{field: True})
        forged = dataclasses.replace(value, authority_boundary=boundary)
        assert not foundation.verify_production_rollback_evidence_foundation(forged)


def test_missing_or_tampered_upstream_evidence_is_not_reconstructed(artifacts):
    owner, proposal, containment, _ = artifacts
    assert foundation.create_production_rollback_evidence_foundation(
        None, proposal, containment) is None
    assert foundation.create_production_rollback_evidence_foundation(
        owner, None, containment) is None
    assert foundation.create_production_rollback_evidence_foundation(
        owner, proposal, None) is None
    bad_containment = dataclasses.replace(containment, report_digest="0" * 64)
    assert foundation.create_production_rollback_evidence_foundation(
        owner, proposal, bad_containment) is None


def test_wrong_gate_or_disabled_proposal_rejected(artifacts):
    owner, _, containment, _ = artifacts
    disabled = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, False)
    assert foundation.create_production_rollback_evidence_foundation(
        owner, disabled, containment) is None
    forged = dataclasses.replace(artifacts[1], requested_gate_name="OTHER")
    assert foundation.create_production_rollback_evidence_foundation(
        owner, forged, containment) is None


def test_upstream_artifacts_not_mutated(artifacts):
    owner, proposal, containment, _ = artifacts
    before = (owner, proposal, containment)
    foundation.create_production_rollback_evidence_foundation(*before)
    assert before == (owner, proposal, containment)
    assert owner is get_production_feature_gate_release_owner()


def test_verification_order_and_lineage_tampering_rejected(artifacts):
    value = artifacts[3]
    for change in (
        dataclasses.replace(value, verification_requirements=value.verification_requirements[::-1]),
        dataclasses.replace(value, evidence_lineage=value.evidence_lineage[::-1]),
        dataclasses.replace(value, evidence_lineage=value.evidence_lineage[:-1]),
    ):
        assert not foundation.verify_production_rollback_evidence_foundation(change)


def test_narrow_public_constructor_has_no_caller_outcome_fields():
    assert tuple(inspect.signature(
        foundation.create_production_rollback_evidence_foundation).parameters) == (
        "release_owner", "proposal", "failure_containment")
    assert tuple(inspect.signature(
        foundation.verify_production_rollback_evidence_foundation).parameters) == ("value",)


def test_static_no_file_network_environment_subprocess_or_operational_entry_points():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {"os", "pathlib", "socket", "subprocess", "requests", "urllib"}.isdisjoint(imported)
    for forbidden in ("open(", "os.environ", "subprocess", "execute_rollback(",
            "apply_rollback(", "activate_", "approve_", "git "):
        assert forbidden not in source
    assert not any(name.startswith(("execute_", "apply_", "activate_", "approve_"))
        for name in vars(foundation))
