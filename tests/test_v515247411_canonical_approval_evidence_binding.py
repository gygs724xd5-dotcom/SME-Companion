from __future__ import annotations

import ast
import dataclasses
from datetime import datetime, timezone
import inspect
from pathlib import Path

import pytest

import brain.production_feature_gate_approval_evidence_binding as binding
from brain.production_feature_gate_approval_evidence_binding import *
from brain.isolated_gate_enabled_pre_authorization_qualification import (
    create_isolated_gate_enabled_pre_authorization_report,
)
from brain.isolated_qualification_configuration_binding import (
    create_isolated_qualification_feature_gate_binding,
    create_isolated_qualification_limited_activation_binding,
    create_isolated_qualification_pre_execution_result,
    create_isolated_qualification_skill_evidence_envelope,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, PURE_TEST_TRUSTED_SOURCE_IDENTITY,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    create_production_feature_gate_configuration, evaluate_production_feature_gate,
)
from brain.production_feature_gate_release_owner import (
    create_production_feature_gate_transition_proposal, get_production_feature_gate_release_owner,
)
from brain.production_feature_gate_release_wiring_acceptance import (
    create_production_feature_gate_release_wiring_report,
)
from brain.production_feature_gate_transition_approval import (
    create_production_feature_gate_transition_approval_request,
    evaluate_production_feature_gate_transition_approval,
)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_feature_gate_approval_evidence_binding.py"


def foundation(conversation="gate-enabled-preauth-qualification"):
    context = create_production_turn_context(conversation, 1, "cost changed from 100 to 120 baht")
    reference = create_production_turn_reference_time(context, datetime(2026, 7, 16, tzinfo=timezone.utc))
    configuration = create_production_feature_gate_configuration(
        PURE_TEST_TRUSTED_SOURCE_IDENTITY, ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),))
    evaluation = evaluate_production_feature_gate(configuration, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    foundation_binding = create_isolated_qualification_feature_gate_binding(context, reference, configuration, evaluation)
    evidence = create_isolated_qualification_skill_evidence_envelope(foundation_binding)
    limited = create_isolated_qualification_limited_activation_binding(evidence)
    foundation = create_isolated_qualification_pre_execution_result(limited)
    return foundation


def artifacts():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    request = create_production_feature_gate_transition_approval_request(owner, proposal)
    decision = evaluate_production_feature_gate_transition_approval(request)
    wiring = create_production_feature_gate_release_wiring_report()
    preauth = create_isolated_gate_enabled_pre_authorization_report(foundation())
    bundle = create_production_feature_gate_approval_evidence_bundle(request, decision, wiring, preauth)
    return request, decision, wiring, preauth, bundle


def test_canonical_bundle_strictly_binds_exact_reports_deterministically():
    one = artifacts()
    two = artifacts()
    assert one[4] == two[4]
    assert verify_production_feature_gate_approval_evidence_bundle(one[4])
    assert one[2].report_digest == binding.EXPECTED_RELEASE_WIRING_REPORT_DIGEST
    assert one[3].report_digest == binding.EXPECTED_PREAUTH_REPORT_DIGEST
    assert tuple(x.requirement_id for x in one[4].evidence) == REQUIREMENT_IDS[4:6]


def test_fixed_requirement_mapping_and_missing_evidence_are_exact():
    decision = evaluate_production_feature_gate_evidence_bound_approval(artifacts()[4])
    assert tuple(x.requirement_id for x in decision.requirements) == REQUIREMENT_IDS
    assert all(x.verified for x in decision.requirements[:6])
    assert all(not x.verified for x in decision.requirements[6:])
    assert all(x.evidence_digest is None and x.report_digest is None and x.topology_digest is None
               for x in decision.requirements[6:])


def test_evidence_bound_decision_remains_denied_at_executable_request():
    decision = evaluate_production_feature_gate_evidence_bound_approval(artifacts()[4])
    assert verify_production_feature_gate_evidence_bound_decision(decision)
    assert decision.status == "TRANSITION_NOT_APPROVED"
    assert decision.primary_denial == "EXECUTABLE_REQUEST_QUALIFIED"
    assert decision.verified_requirement_count == 6 and decision.missing_requirement_count == 4
    assert decision.reasons == tuple(MISSING_REASONS[x] for x in REQUIREMENT_IDS[6:])
    assert not any((decision.transition_approved, decision.application_permitted,
                    decision.activation_permitted, decision.transition_applied))
    assert decision.executable_output is None


def test_historical_policy_is_distinct_and_unchanged():
    _, historical, _, _, bundle = artifacts()
    current = evaluate_production_feature_gate_evidence_bound_approval(bundle)
    assert historical.primary_denial == "READ_ONLY_RELEASE_WIRING_ACCEPTED"
    assert current.primary_denial == "EXECUTABLE_REQUEST_QUALIFIED"
    assert type(historical) is not type(current) and historical.version == "5.15.24.7.4.8"


@pytest.mark.parametrize("index,field,value", (
    (2, "acceptance_status", "FORGED"), (2, "report_digest", "0" * 64),
    (2, "topology_digest", "0" * 64), (3, "requirement_id", "EXECUTABLE_REQUEST_QUALIFIED"),
    (3, "qualified", False), (3, "status", "FORGED"), (3, "report_digest", "0" * 64),
    (3, "topology_digest", "0" * 64), (3, "release_owner_digest", "0" * 64),
    (3, "release_revision_id", "forged"), (3, "production_configuration_digest", "0" * 64),
))
def test_report_identity_status_digest_and_cross_report_tampering_fail_closed(index, field, value):
    values = list(artifacts()[:4])
    values[index] = dataclasses.replace(values[index], **{field: value})
    assert create_production_feature_gate_approval_evidence_bundle(*values) is None


def test_exact_types_and_cross_proposal_substitution_fail_closed():
    request, decision, wiring, preauth, _ = artifacts()
    assert create_production_feature_gate_approval_evidence_bundle({}, decision, wiring, preauth) is None
    assert create_production_feature_gate_approval_evidence_bundle(request, decision, dataclasses.asdict(wiring), preauth) is None
    proposal = create_production_feature_gate_transition_proposal(LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, False)
    other_request = create_production_feature_gate_transition_approval_request(request.release_owner, proposal)
    assert create_production_feature_gate_approval_evidence_bundle(other_request, decision, wiring, preauth) is None


@pytest.mark.parametrize("field,value", (
    ("requirement_ids", REQUIREMENT_IDS[::-1]), ("evidence_topology", EVIDENCE_TOPOLOGY[::-1]),
    ("evidence", ()), ("ordered_evidence_digests", ()), ("bundle_digest", "0" * 64),
    ("authority_boundary", ProductionFeatureGateEvidenceBindingAuthorityBoundary(runtime=True)),
))
def test_bundle_reorder_drop_digest_and_authority_tampering_fail_closed(field, value):
    forged = dataclasses.replace(artifacts()[4], **{field: value})
    assert not verify_production_feature_gate_approval_evidence_bundle(forged)


@pytest.mark.parametrize("field,value", (
    ("status", "APPROVED"), ("primary_denial", "GATE_ENABLED_PREAUTH_QUALIFIED"),
    ("reasons", ("forged",)), ("verified_requirement_count", 10),
    ("missing_requirement_count", 0), ("transition_approved", True),
    ("application_permitted", True), ("activation_permitted", True),
    ("transition_applied", True), ("executable_output", object()),
    ("decision_digest", "0" * 64),
    ("authority_boundary", ProductionFeatureGateEvidenceBindingAuthorityBoundary(execution=True)),
))
def test_decision_claim_count_permission_output_and_digest_tampering_fail_closed(field, value):
    decision = evaluate_production_feature_gate_evidence_bound_approval(artifacts()[4])
    assert not verify_production_feature_gate_evidence_bound_decision(
        dataclasses.replace(decision, **{field: value}))


def test_requirement_reorder_forged_verified_and_fake_missing_digest_fail_closed():
    decision = evaluate_production_feature_gate_evidence_bound_approval(artifacts()[4])
    variants = (
        decision.requirements[::-1], decision.requirements[:-1],
        decision.requirements + (decision.requirements[0],),
        decision.requirements[:6] + (dataclasses.replace(decision.requirements[6], verified=True),) + decision.requirements[7:],
        decision.requirements[:6] + (dataclasses.replace(decision.requirements[6], evidence_digest="0" * 64),) + decision.requirements[7:],
    )
    for requirements in variants:
        assert not verify_production_feature_gate_evidence_bound_decision(
            dataclasses.replace(decision, requirements=requirements))


def test_executable_boundary_and_production_invariants_remain_unchanged():
    owner_before = get_production_feature_gate_release_owner()
    _, _, _, preauth, bundle = artifacts()
    decision = evaluate_production_feature_gate_evidence_bound_approval(bundle)
    preauth_foundation = preauth.foundation_result
    owner_after = get_production_feature_gate_release_owner()
    assert owner_before is owner_after and owner_after.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert owner_after.configuration.gate_entries == ()
    assert not owner_after.configured_state and not owner_after.effective_state and owner_after.default_denied
    assert preauth_foundation.execute_allowed is False and preauth_foundation.executable_request is None
    assert preauth_foundation.executable_request_qualified is False and preauth.controlled_runtime_invocation_count == 0
    assert not decision.requirements[6].verified


def test_authority_is_frozen_false_and_public_builders_accept_no_mapping_or_outcomes():
    decision = evaluate_production_feature_gate_evidence_bound_approval(artifacts()[4])
    assert dataclasses.is_dataclass(decision) and decision.__dataclass_params__.frozen
    assert all(getattr(decision.authority_boundary, f.name) is False
               for f in dataclasses.fields(decision.authority_boundary))
    params = inspect.signature(create_production_feature_gate_approval_evidence_bundle).parameters
    assert set(params) == {"historical_request", "historical_decision", "release_wiring_report", "preauth_report"}
    for name in vars(binding):
        assert not name.startswith(("set_", "apply_", "enable_", "approve_", "activate_", "execute_", "dispatch_"))


def test_static_isolation_from_app_io_environment_and_downstream_invocation():
    source = MODULE.read_text(encoding="utf-8")
    lower = source.lower()
    for forbidden in ("import app", "streamlit", "session_state", "os.environ", "getenv", "subprocess",
                      "requests", "socket", "open(", "write(", "manual smoke", "human approval"):
        assert forbidden not in lower
    calls = {node.func.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name)}
    assert calls.isdisjoint({"calculator", "runtime", "delivery", "bridge", "admission", "execute"})


def test_historical_digest_regression_749_7491_7410():
    _, _, wiring, preauth, _ = artifacts()
    fixed = foundation("foundation")
    assert (wiring.report_digest, wiring.topology_digest) == (
        binding.EXPECTED_RELEASE_WIRING_REPORT_DIGEST, binding.EXPECTED_RELEASE_WIRING_TOPOLOGY_DIGEST)
    assert fixed.configuration_binding.binding_digest == "87814ef7517868c4aa5695d20c678c4e92c5b7e613c71d23f24d1984da6de11a"
    assert fixed.evidence_envelope.envelope_digest == "e71c2f1200a60b0926e95095d1c18c66e32f99372dcf0fabdf7a4e14ebe6d038"
    assert fixed.limited_activation_binding.binding_digest == "931f6b098f83cae7f89b9cd9bd4faf9eb38df070f8be3c68ae9e7c91a5b8f9a7"
    assert fixed.result_digest == "fb7459d151f3be03719a395c20db35ebe4cce70fc2ebddd8c042b42efe3b77d8"
    assert (preauth.report_digest, preauth.topology_digest) == (
        binding.EXPECTED_PREAUTH_REPORT_DIGEST, binding.EXPECTED_PREAUTH_TOPOLOGY_DIGEST)
