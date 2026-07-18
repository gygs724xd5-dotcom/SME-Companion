from __future__ import annotations

import ast
import dataclasses
import inspect
from functools import lru_cache
from pathlib import Path

import pytest

import brain.production_feature_gate_controlled_runtime_approval_binding as binding
from brain.production_feature_gate_controlled_runtime_approval_binding import *
from brain.production_feature_gate_executable_request_approval_binding import (
    evaluate_production_feature_gate_executable_request_bound_approval,
)
from brain.bridge_record_runtime_manifest_binding import create_bridge_record_runtime_manifest_binding
from brain.recorded_controlled_runtime_acceptance import create_recorded_controlled_runtime_acceptance_report
from brain.verifiable_isolated_admission_invocation_record import create_isolated_admission_invocation_batch
from brain.verifiable_isolated_bridge_invocation_record import create_isolated_bridge_invocation_batch
from brain.versioned_controlled_runtime_admission_request_binding import create_versioned_controlled_runtime_admission_request_bindings
from test_v515247413_executable_request_approval_binding import artifacts as executable_artifacts
from test_v5152474133_execution_result_runtime_bridge_request_binding import _batch as execution_batch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_feature_gate_controlled_runtime_approval_binding.py"


@lru_cache(maxsize=1)
def artifacts():
    old_bundle = executable_artifacts()[3]
    old_decision = evaluate_production_feature_gate_executable_request_bound_approval(old_bundle)
    manifest = create_bridge_record_runtime_manifest_binding(create_isolated_bridge_invocation_batch(execution_batch()))
    admission = create_isolated_admission_invocation_batch(
        create_versioned_controlled_runtime_admission_request_bindings(manifest))
    report = create_recorded_controlled_runtime_acceptance_report(admission)
    bundle = create_production_feature_gate_controlled_runtime_evidence_bundle(old_bundle, old_decision, report)
    return old_bundle, old_decision, report, bundle


def test_canonical_bundle_and_evidence_strictly_verify():
    _, old, report, bundle = artifacts()
    assert old.decision_digest == binding.EXPECTED_PREVIOUS_DECISION_DIGEST
    assert (report.report_digest, report.topology_digest, report.source_batch.batch_digest) == (
        binding.EXPECTED_REPORT_DIGEST, binding.EXPECTED_TOPOLOGY_DIGEST,
        binding.EXPECTED_ADMISSION_BATCH_DIGEST)
    assert verify_production_feature_gate_controlled_runtime_evidence(bundle.evidence)
    assert verify_production_feature_gate_controlled_runtime_evidence_bundle(bundle)


def test_fixed_mapping_is_eight_verified_and_two_genuinely_missing():
    decision = evaluate_production_feature_gate_controlled_runtime_bound_approval(artifacts()[3])
    assert tuple(x.requirement_id for x in decision.requirements) == REQUIREMENT_IDS
    assert all(x.verified for x in decision.requirements[:8])
    assert all(not x.verified and x.evidence_digest is None and x.report_digest is None
        and x.topology_digest is None for x in decision.requirements[8:])


def test_decision_remains_fail_closed_with_expected_primary_denial():
    decision = evaluate_production_feature_gate_controlled_runtime_bound_approval(artifacts()[3])
    assert verify_production_feature_gate_controlled_runtime_bound_decision(decision)
    assert (decision.verified_requirement_count, decision.missing_requirement_count) == (8, 2)
    assert decision.status == "TRANSITION_NOT_APPROVED"
    assert decision.primary_denial == "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED"
    assert not any((decision.transition_approved, decision.application_permitted,
        decision.activation_permitted, decision.transition_applied))
    assert decision.executable_output is None


def test_report_accounting_is_preserved_without_invention():
    report = artifacts()[2]
    assert artifacts()[3].evidence.isolated_invocation_counts == (2, 2, 2, 2, 0)
    assert artifacts()[3].evidence.production_invocation_counts == (0,) * 7
    assert report.separate_controlled_runtime_invocations == 0 and report.accepted


@pytest.mark.parametrize("value", ({}, True, "accepted", object()))
def test_wrong_report_concrete_types_fail_closed(value):
    old_bundle, old_decision, _, _ = artifacts()
    assert create_production_feature_gate_controlled_runtime_evidence_bundle(
        old_bundle, old_decision, value) is None


@pytest.mark.parametrize("field,value", (
    ("status", "FORGED"), ("requirement", "FORGED"), ("accepted", False),
    ("qualified", False), ("report_digest", "0" * 64), ("topology_digest", "0" * 64),
    ("separate_controlled_runtime_invocations", 1), ("production_runtime_invocations", 1),
    ("observation_digests", ()),
))
def test_report_substitution_status_digest_count_and_observation_tampering_fail_closed(field, value):
    old_bundle, old_decision, report, _ = artifacts()
    forged = dataclasses.replace(report, **{field: value})
    assert create_production_feature_gate_controlled_runtime_evidence_bundle(
        old_bundle, old_decision, forged) is None


def test_noncanonical_previous_chain_and_ancestry_substitution_fail_closed():
    old_bundle, old_decision, report, _ = artifacts()
    assert create_production_feature_gate_controlled_runtime_evidence_bundle({}, old_decision, report) is None
    assert create_production_feature_gate_controlled_runtime_evidence_bundle(old_bundle, {}, report) is None
    observation = dataclasses.replace(report.observations[0], upstream_topology_digests=("0" * 64,))
    forged = dataclasses.replace(report, observations=(observation,) + report.observations[1:])
    assert create_production_feature_gate_controlled_runtime_evidence_bundle(old_bundle, old_decision, forged) is None


@pytest.mark.parametrize("field,value", (
    ("requirement_ids", REQUIREMENT_IDS[::-1]), ("evidence_topology", EVIDENCE_TOPOLOGY[::-1]),
    ("ordered_evidence_digests", ()), ("release_revision_id", "forged"),
    ("transition_proposal_digest", "0" * 64), ("rollback_digest", "0" * 64),
    ("bundle_digest", "0" * 64),
    ("authority_boundary", ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary(production=True)),
))
def test_bundle_identity_topology_digest_and_authority_tampering_fail_closed(field, value):
    forged = dataclasses.replace(artifacts()[3], **{field: value})
    assert not verify_production_feature_gate_controlled_runtime_evidence_bundle(forged)


def test_requirement_reorder_duplicate_unknown_forged_missing_and_fake_digest_fail_closed():
    decision = evaluate_production_feature_gate_controlled_runtime_bound_approval(artifacts()[3])
    missing = decision.requirements[8]
    variants = (decision.requirements[::-1], decision.requirements[:-1],
        decision.requirements + (decision.requirements[0],),
        decision.requirements[:8] + (dataclasses.replace(missing, requirement_id="UNKNOWN"),) + decision.requirements[9:],
        decision.requirements[:8] + (dataclasses.replace(missing, verified=True),) + decision.requirements[9:],
        decision.requirements[:8] + (dataclasses.replace(missing, evidence_digest="0" * 64),) + decision.requirements[9:])
    for requirements in variants:
        assert not verify_production_feature_gate_controlled_runtime_bound_decision(
            dataclasses.replace(decision, requirements=requirements))


@pytest.mark.parametrize("field,value", (
    ("status", "APPROVED"), ("primary_denial", "FORGED"),
    ("verified_requirement_count", 10), ("missing_requirement_count", 0),
    ("transition_approved", True), ("application_permitted", True),
    ("activation_permitted", True), ("transition_applied", True),
    ("executable_output", object()), ("decision_digest", "0" * 64),
    ("authority_boundary", ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary(network=True)),
))
def test_decision_outcome_count_permission_output_and_authority_tampering_fail_closed(field, value):
    decision = evaluate_production_feature_gate_controlled_runtime_bound_approval(artifacts()[3])
    assert not verify_production_feature_gate_controlled_runtime_bound_decision(
        dataclasses.replace(decision, **{field: value}))


def test_verification_is_pure_when_execution_bridge_and_gateway_raise(monkeypatch):
    import brain.verifiable_isolated_runtime_invocation_record as execution
    import brain.verifiable_isolated_bridge_invocation_record as bridge
    import brain.verifiable_isolated_admission_invocation_record as admission
    monkeypatch.setattr(execution, "execute_cost_skill", lambda *a, **k: pytest.fail("executor invoked"))
    monkeypatch.setattr(bridge, "bridge_prepared_cost_response", lambda *a, **k: pytest.fail("bridge invoked"))
    monkeypatch.setattr(admission._gateway, "decide_controlled_runtime_integration_admission",
        lambda *a, **k: pytest.fail("gateway invoked"))
    assert verify_production_feature_gate_controlled_runtime_evidence_bundle(artifacts()[3])


def test_frozen_contracts_narrow_api_and_static_isolation():
    for contract in (ProductionFeatureGateControlledRuntimeApprovalEvidence,
        ProductionFeatureGateControlledRuntimeEvidenceBundle,
        ProductionFeatureGateControlledRuntimeBoundRequirement,
        ProductionFeatureGateControlledRuntimeBoundDecision,
        ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary):
        assert contract.__dataclass_params__.frozen
    assert tuple(inspect.signature(create_production_feature_gate_controlled_runtime_evidence_bundle).parameters) == (
        "previous_bundle", "previous_decision", "acceptance_report")
    source = MODULE.read_text(encoding="utf-8"); tree = ast.parse(source)
    imported = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)}
    imported |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert {"app", "os", "pathlib", "socket", "subprocess", "requests", "urllib", "streamlit"}.isdisjoint(imported)
    assert not any(token in source for token in ("session_state", "open(", "os.environ", "subprocess",
        "execute_cost_skill(", "bridge_prepared_cost_response(", "decide_controlled_runtime_integration_admission("))
    assert not any(name.startswith(("set_", "apply_", "approve_", "activate_", "execute_", "dispatch_"))
        for name in vars(binding))
