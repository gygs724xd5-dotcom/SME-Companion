from __future__ import annotations

import ast
import dataclasses
from datetime import datetime, timezone
import inspect
from functools import lru_cache
from pathlib import Path

import pytest

import brain.production_feature_gate_executable_request_approval_binding as binding
from brain.production_feature_gate_executable_request_approval_binding import *
from brain.isolated_executable_request_qualification import create_isolated_executable_request_qualification_report
from brain.isolated_gate_enabled_pre_authorization_qualification import create_isolated_gate_enabled_pre_authorization_report
from brain.isolated_qualification_configuration_binding import (
    create_isolated_qualification_feature_gate_binding, create_isolated_qualification_limited_activation_binding,
    create_isolated_qualification_pre_execution_result, create_isolated_qualification_skill_evidence_envelope,
)
from brain.production_feature_gate_approval_evidence_binding import (
    create_production_feature_gate_approval_evidence_bundle,
    evaluate_production_feature_gate_evidence_bound_approval,
    verify_production_feature_gate_evidence_bound_decision,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, PURE_TEST_TRUSTED_SOURCE_IDENTITY,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, create_production_feature_gate_configuration,
    evaluate_production_feature_gate,
)
from brain.production_feature_gate_release_owner import (
    create_production_feature_gate_transition_proposal, get_production_feature_gate_release_owner,
)
from brain.production_feature_gate_release_wiring_acceptance import create_production_feature_gate_release_wiring_report
from brain.production_feature_gate_transition_approval import (
    create_production_feature_gate_transition_approval_request, evaluate_production_feature_gate_transition_approval,
)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_feature_gate_executable_request_approval_binding.py"


def foundation(message, ordinal=1, conversation="gate-enabled-preauth-qualification"):
    context = create_production_turn_context(conversation, ordinal, message)
    reference = create_production_turn_reference_time(context, datetime(2026, 7, 16, tzinfo=timezone.utc))
    configuration = create_production_feature_gate_configuration(
        PURE_TEST_TRUSTED_SOURCE_IDENTITY, ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),))
    evaluation = evaluate_production_feature_gate(configuration, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    base = create_isolated_qualification_feature_gate_binding(context, reference, configuration, evaluation)
    return create_isolated_qualification_pre_execution_result(
        create_isolated_qualification_limited_activation_binding(
            create_isolated_qualification_skill_evidence_envelope(base)))


@lru_cache(maxsize=1)
def artifacts():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    request = create_production_feature_gate_transition_approval_request(owner, proposal)
    historical = evaluate_production_feature_gate_transition_approval(request)
    preauth_foundation = foundation("cost changed from 100 to 120 baht")
    old_bundle = create_production_feature_gate_approval_evidence_bundle(
        request, historical, create_production_feature_gate_release_wiring_report(),
        create_isolated_gate_enabled_pre_authorization_report(preauth_foundation))
    old_decision = evaluate_production_feature_gate_evidence_bound_approval(old_bundle)
    unit = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น ของเสีย 2 ชิ้น"
    pairs = tuple((base, create_isolated_gate_enabled_pre_authorization_report(base)) for base in (
        foundation("cost changed from 100 to 120 baht", 1, "request-qualification"),
        foundation(unit, 2, "request-qualification")))
    report = create_isolated_executable_request_qualification_report(pairs)
    bundle = create_production_feature_gate_executable_request_evidence_bundle(old_bundle, old_decision, report)
    return old_bundle, old_decision, report, bundle


def test_canonical_bundle_binds_previous_decision_report_and_requests_deterministically():
    one, two = artifacts(), artifacts()
    assert one[3] == two[3] and verify_production_feature_gate_executable_request_evidence_bundle(one[3])
    assert one[1].decision_digest == binding.EXPECTED_PREVIOUS_DECISION_DIGEST
    assert (one[2].report_digest, one[2].topology_digest) == (
        binding.EXPECTED_REPORT_DIGEST, binding.EXPECTED_TOPOLOGY_DIGEST)
    assert one[2].request_digests == binding.EXPECTED_REQUEST_DIGESTS


def test_fixed_requirement_mapping_is_seven_verified_then_three_exactly_missing():
    decision = evaluate_production_feature_gate_executable_request_bound_approval(artifacts()[3])
    assert tuple(x.requirement_id for x in decision.requirements) == REQUIREMENT_IDS
    assert all(x.verified for x in decision.requirements[:7])
    assert all(not x.verified and x.evidence_digest is None and x.report_digest is None
               and x.topology_digest is None for x in decision.requirements[7:])


def test_decision_remains_denied_without_permissions_or_executable_output():
    decision = evaluate_production_feature_gate_executable_request_bound_approval(artifacts()[3])
    assert verify_production_feature_gate_executable_request_bound_decision(decision)
    assert (decision.verified_requirement_count, decision.missing_requirement_count) == (7, 3)
    assert decision.status == "TRANSITION_NOT_APPROVED"
    assert decision.primary_denial == "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED"
    assert decision.reasons == tuple(MISSING_REASONS[x] for x in REQUIREMENT_IDS[7:])
    assert not any((decision.transition_approved, decision.application_permitted,
                    decision.activation_permitted, decision.transition_applied))
    assert decision.executable_output is None


def test_historical_decision_remains_distinct_six_of_ten_and_unchanged():
    _, old, _, bundle = artifacts()
    current = evaluate_production_feature_gate_executable_request_bound_approval(bundle)
    assert verify_production_feature_gate_evidence_bound_decision(old)
    assert (old.verified_requirement_count, old.missing_requirement_count, old.primary_denial) == (
        6, 4, "EXECUTABLE_REQUEST_QUALIFIED")
    assert old.decision_digest == binding.EXPECTED_PREVIOUS_DECISION_DIGEST
    assert type(old) is not type(current) and old.version == "5.15.24.7.4.11"


def test_request_completeness_and_execution_authority_separation():
    report = artifacts()[2]
    assert tuple(x.skill_id for x in report.observations) == report.supported_skill_ids
    assert report.request_digests == binding.EXPECTED_REQUEST_DIGESTS
    for observation in report.observations:
        request = observation.request
        assert not request.requirement_qualified and not request.execute_allowed
        assert not request.dispatch_permitted and not request.runtime_invocation_permitted
        assert request.execution_result is None
    assert (report.calculator_invocation_count, report.bridge_invocation_count,
            report.admission_invocation_count, report.delivery_invocation_count,
            report.controlled_runtime_invocation_count) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize("field,value", (
    ("requirement_id", "FORGED"), ("status", "FORGED"), ("qualified", False),
    ("supported_skill_ids", ("cost_per_unit",)), ("qualified_skill_count", 1),
    ("failed_skill_count", 1), ("request_digests", binding.EXPECTED_REQUEST_DIGESTS[::-1]),
    ("report_digest", "0" * 64), ("topology_digest", "0" * 64),
    ("execute_allowed", True), ("runtime_invocation_permitted", True),
    ("calculator_invocation_count", 1),
))
def test_report_inventory_count_digest_and_authority_tampering_fail_closed(field, value):
    old_bundle, old_decision, report, _ = artifacts()
    assert create_production_feature_gate_executable_request_evidence_bundle(
        old_bundle, old_decision, dataclasses.replace(report, **{field: value})) is None


def test_observation_request_and_cross_release_substitution_fail_closed():
    old_bundle, old_decision, report, _ = artifacts()
    observations = (dataclasses.replace(report.observations[0], request=report.observations[1].request),) + report.observations[1:]
    forged = dataclasses.replace(report, observations=observations)
    assert create_production_feature_gate_executable_request_evidence_bundle(old_bundle, old_decision, forged) is None
    assert create_production_feature_gate_executable_request_evidence_bundle({}, old_decision, report) is None
    assert create_production_feature_gate_executable_request_evidence_bundle(old_bundle, {}, report) is None
    assert create_production_feature_gate_executable_request_evidence_bundle(old_bundle, old_decision, {}) is None


@pytest.mark.parametrize("field,value", (
    ("requirement_ids", REQUIREMENT_IDS[::-1]), ("evidence_topology", EVIDENCE_TOPOLOGY[::-1]),
    ("ordered_evidence_digests", ()), ("request_ids", ()), ("bundle_digest", "0" * 64),
    ("authority_boundary", ProductionFeatureGateExecutableRequestBindingAuthorityBoundary(persistence=True)),
))
def test_bundle_topology_request_digest_and_authority_tampering_fail_closed(field, value):
    forged = dataclasses.replace(artifacts()[3], **{field: value})
    assert not verify_production_feature_gate_executable_request_evidence_bundle(forged)


@pytest.mark.parametrize("field,value", (
    ("status", "APPROVED"), ("primary_denial", "FORGED"), ("reasons", ("forged",)),
    ("verified_requirement_count", 10), ("missing_requirement_count", 0),
    ("transition_approved", True), ("application_permitted", True),
    ("activation_permitted", True), ("transition_applied", True),
    ("executable_output", object()), ("decision_digest", "0" * 64),
    ("authority_boundary", ProductionFeatureGateExecutableRequestBindingAuthorityBoundary(runtime=True)),
))
def test_decision_status_count_permission_output_and_digest_tampering_fail_closed(field, value):
    decision = evaluate_production_feature_gate_executable_request_bound_approval(artifacts()[3])
    assert not verify_production_feature_gate_executable_request_bound_decision(
        dataclasses.replace(decision, **{field: value}))


def test_requirement_reorder_duplicate_forged_verified_and_fake_evidence_fail_closed():
    decision = evaluate_production_feature_gate_executable_request_bound_approval(artifacts()[3])
    variants = (decision.requirements[::-1], decision.requirements[:-1],
                decision.requirements + (decision.requirements[0],),
                decision.requirements[:7] + (dataclasses.replace(decision.requirements[7], verified=True),) + decision.requirements[8:],
                decision.requirements[:7] + (dataclasses.replace(decision.requirements[7], evidence_digest="0" * 64),) + decision.requirements[8:])
    for requirements in variants:
        assert not verify_production_feature_gate_executable_request_bound_decision(
            dataclasses.replace(decision, requirements=requirements))


def test_static_isolation_frozen_contracts_and_narrow_public_api():
    source = MODULE.read_text(encoding="utf-8"); lower = source.lower()
    for forbidden in ("import app", "streamlit", "session_state", "os.environ", "getenv", "subprocess",
                      "requests", "socket", "open(", "write(", "manual smoke", "human approval"):
        assert forbidden not in lower
    calls = {n.func.id for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert calls.isdisjoint({"calculator", "runtime", "delivery", "bridge", "admission", "execute"})
    for contract in (ProductionFeatureGateExecutableRequestApprovalEvidence,
                     ProductionFeatureGateExecutableRequestEvidenceBundle,
                     ProductionFeatureGateExecutableRequestBoundRequirement,
                     ProductionFeatureGateExecutableRequestBoundDecision,
                     ProductionFeatureGateExecutableRequestBindingAuthorityBoundary):
        assert contract.__dataclass_params__.frozen
    assert set(inspect.signature(create_production_feature_gate_executable_request_evidence_bundle).parameters) == {
        "previous_bundle", "previous_decision", "qualification_report"}
    for name in vars(binding):
        assert not name.startswith(("set_", "apply_", "approve_", "activate_", "execute_", "dispatch_"))


def test_production_default_deny_and_release_owner_remain_unchanged():
    owner_before = get_production_feature_gate_release_owner()
    decision = evaluate_production_feature_gate_executable_request_bound_approval(artifacts()[3])
    owner_after = get_production_feature_gate_release_owner()
    assert owner_before is owner_after and owner_after.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert owner_after.configuration.gate_entries == ()
    assert not owner_after.configured_state and not owner_after.effective_state and owner_after.default_denied
    assert decision.executable_output is None
