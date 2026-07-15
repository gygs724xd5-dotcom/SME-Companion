"""V5.15.24.7.4.2 current-policy isolated authorization acceptance."""
import ast
import dataclasses
from datetime import datetime, timezone
from pathlib import Path

import pytest

import brain.production_pre_execution_authorization_acceptance as owner
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_limited_activation_binding import create_production_limited_activation_binding
from brain.production_pre_execution_authorization import (
    CONTROLLED_COST_EVIDENCE_NOT_READY,
    CONTROLLED_COST_RUNTIME_NOT_APPLICABLE,
    DENIED_DEFAULT_PRODUCTION_GATE,
    EVIDENCE_NOT_READY,
    GATE_ORDER,
    NOT_APPLICABLE,
    PRODUCTION_FEATURE_GATE_DEFAULT_DENIED,
    create_production_pre_execution_authorization_request,
    evaluate_production_pre_execution_authorization,
    verify_production_pre_execution_authorization_decision,
    verify_production_pre_execution_authorization_request,
)
from brain.production_turn_bound_skill_evidence import create_production_turn_bound_skill_evidence_envelope
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time


ROOT = Path(__file__).parents[1]


def matrix():
    scenarios = owner.create_production_pre_execution_acceptance_scenarios()
    assert scenarios is not None
    report = owner.create_production_pre_execution_acceptance_report(scenarios)
    assert report is not None
    return scenarios, report


def foundations(message="my cost increased from 20.00 to 24.000", conversation="reject", ordinal=1):
    context = create_production_turn_context(conversation, ordinal, message)
    reference = create_production_turn_reference_time(
        context, datetime(2026, 7, 15, 4, 5, 6, tzinfo=timezone.utc))
    gate = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    envelope = create_production_turn_bound_skill_evidence_envelope(context, gate)
    binding = create_production_limited_activation_binding(context, reference, gate, envelope)
    return context, reference, gate, envelope, binding


def test_frozen_contracts_version_scope_and_exact_inventory():
    assert owner.ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_VERSION == "5.15.24.7.4.2"
    assert owner.ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_SCOPE == "CURRENT_POLICY_DEFAULT_DENIED_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE"
    for contract in (owner.ProductionPreExecutionAcceptanceScenario,
                     owner.ProductionPreExecutionAcceptanceObservation,
                     owner.ProductionPreExecutionAcceptanceReport,
                     owner.ProductionPreExecutionAcceptanceAuthorityBoundary):
        assert contract.__dataclass_params__.frozen
    scenarios, _ = matrix()
    assert tuple(item.scenario_id for item in scenarios) == owner.CANONICAL_SCENARIO_IDS
    assert len(set(owner.CANONICAL_SCENARIO_IDS)) == 7


@pytest.mark.parametrize("index", range(7))
def test_each_observation_is_real_strictly_verified_and_deterministic(index):
    scenarios, first = matrix()
    second = owner.create_production_pre_execution_acceptance_report(
        owner.create_production_pre_execution_acceptance_scenarios())
    scenario, observation = scenarios[index], first.observations[index]
    assert owner.verify_production_pre_execution_acceptance_scenario(scenario)
    assert owner.verify_production_pre_execution_acceptance_observation(observation)
    assert verify_production_pre_execution_authorization_request(observation.authorization_request)
    assert verify_production_pre_execution_authorization_decision(
        observation.authorization_request, observation.observed_decision)
    assert observation.observed_decision == evaluate_production_pre_execution_authorization(
        observation.authorization_request)
    assert observation.observation_passed
    assert first == second


@pytest.mark.parametrize("index,skill", ((0, "cost.change_analysis.v1"),
                                          (1, "cost.per_unit_calculation.v1"),
                                          (2, "cost.per_unit_calculation.v1")))
def test_eligible_scenarios_end_only_at_default_deny(index, skill):
    observation = matrix()[1].observations[index]
    assert observation.skill_id == skill
    assert observation.observed_decision_status == DENIED_DEFAULT_PRODUCTION_GATE
    assert observation.observed_denial_code == PRODUCTION_FEATURE_GATE_DEFAULT_DENIED
    assert observation.first_failed_gate == "DEFAULT_DENY_GATE_STATE"
    assert observation.eligibility_verified and observation.eligibility_allowed
    assert not observation.execute_allowed
    assert observation.executable_request is observation.controlled_response_candidate is None


def test_not_applicable_has_no_fabricated_skill_and_precedes_default_gate():
    observation = matrix()[1].observations[3]
    assert observation.observed_decision_status == NOT_APPLICABLE
    assert observation.observed_denial_code == CONTROLLED_COST_RUNTIME_NOT_APPLICABLE
    assert observation.skill_id is None and observation.first_failed_gate == "APPLICABILITY"


@pytest.mark.parametrize("index", (4, 5, 6))
def test_evidence_not_ready_precedes_default_gate(index):
    observation = matrix()[1].observations[index]
    assert observation.observed_decision_status == EVIDENCE_NOT_READY
    assert observation.observed_denial_code == CONTROLLED_COST_EVIDENCE_NOT_READY
    assert observation.first_failed_gate == "EVIDENCE_READINESS"
    assert observation.skill_id is None and not observation.execute_allowed


def test_report_exact_counts_coverage_and_current_policy_exclusion():
    report = matrix()[1]
    assert (report.total_count, report.eligible_default_denied_count,
            report.not_applicable_count, report.evidence_not_ready_count,
            report.invalid_fail_closed_count) == (7, 3, 1, 3, 0)
    assert report.eligibility_denied_observed_count == 0
    assert report.eligibility_denied_current_policy_representable is False
    assert owner.ELIGIBILITY_DENIED_NOT_REPRODUCIBLE in report.diagnostics
    assert report.skill_coverage == ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")
    assert (report.execute_allowed_count, report.executable_request_count,
            report.controlled_candidate_count,
            report.admitted_runtime_bridge_delivery_count) == (0, 0, 0, 0)
    assert report.request_integrity and report.decision_integrity
    assert report.authority_isolated and report.all_passed
    assert owner.verify_production_pre_execution_acceptance_report(report)


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "reordered", "partial"))
def test_report_rejects_silent_drop_duplicate_reorder_and_partial_inventory(mutation):
    scenarios, _ = matrix()
    variants = {
        "missing": scenarios[1:],
        "duplicate": scenarios[:-1] + (scenarios[-2],),
        "reordered": (scenarios[1], scenarios[0], *scenarios[2:]),
        "partial": scenarios[:3],
    }
    assert owner.create_production_pre_execution_acceptance_report(variants[mutation]) is None


def test_scenario_and_report_tampering_are_recomputed_not_trusted():
    scenarios, report = matrix()
    assert not owner.verify_production_pre_execution_acceptance_scenario(
        dataclasses.replace(scenarios[0], expected_denial_code="FORGED"))
    assert not owner.verify_production_pre_execution_acceptance_report(
        dataclasses.replace(report, all_passed=False))
    assert not owner.verify_production_pre_execution_acceptance_report(
        dataclasses.replace(report, total_count=6))
    assert not owner.verify_production_pre_execution_acceptance_report(
        dataclasses.replace(report, eligibility_denied_observed_count=1))


@pytest.mark.parametrize("digest", ("", "A" * 64, "g" * 64, "0" * 63, "0" * 65))
def test_malformed_acceptance_digests_rejected(digest):
    scenarios, report = matrix()
    observation = report.observations[0]
    assert not owner.verify_production_pre_execution_acceptance_scenario(
        dataclasses.replace(scenarios[0], scenario_digest=digest))
    assert not owner.verify_production_pre_execution_acceptance_observation(
        dataclasses.replace(observation, observation_digest=digest))
    assert not owner.verify_production_pre_execution_acceptance_report(
        dataclasses.replace(report, report_digest=digest))


@pytest.mark.parametrize("index", range(5))
def test_cross_foundation_substitution_is_constructor_rejection_not_observation(index):
    first = list(foundations())
    second = foundations("my cost increased from 30 to 41", "other", 2)
    first[index] = second[index]
    assert create_production_pre_execution_authorization_request(*first) is None


@pytest.mark.parametrize("field,value", (("context_version", "5.15.23"),
                                           ("context_version", "5.15.25")))
def test_historical_foundation_is_constructor_rejection_not_observation(field, value):
    values = list(foundations())
    values[0] = dataclasses.replace(values[0], **{field: value})
    assert create_production_pre_execution_authorization_request(*values) is None


@pytest.mark.parametrize("changes", (
    {"decision_digest": "A" * 64},
    {"execute_allowed": True},
    {"executable_request": object()},
    {"controlled_response_candidate": object()},
    {"decision_status": "FORGED"},
    {"denial_code": "FORGED"},
    {"denial_reason": "FORGED"},
    {"eligibility_verified": False},
    {"eligibility_allowed": False},
))
def test_post_decision_field_tampering_is_verifier_only_not_observation(changes):
    observation = matrix()[1].observations[0]
    forged = dataclasses.replace(observation.observed_decision, **changes)
    assert not verify_production_pre_execution_authorization_decision(
        observation.authorization_request, forged)


@pytest.mark.parametrize("kind", ("missing", "duplicate", "reordered"))
def test_post_decision_gate_tampering_is_verifier_only_not_observation(kind):
    observation = matrix()[1].observations[0]
    gates = observation.observed_decision.gate_results
    variants = {"missing": gates[:-1], "duplicate": gates + (gates[-1],),
                "reordered": (gates[1], gates[0], *gates[2:])}
    forged = dataclasses.replace(observation.observed_decision,
                                 gate_results=variants[kind])
    assert not verify_production_pre_execution_authorization_decision(
        observation.authorization_request, forged)


def test_authority_escalation_and_cross_request_substitution_are_verifier_only():
    observations = matrix()[1].observations
    malformed_request = dataclasses.replace(
        observations[0].authorization_request, request_digest="A" * 64)
    assert not verify_production_pre_execution_authorization_request(malformed_request)
    boundary = dataclasses.replace(observations[0].observed_decision.authority_boundary,
                                   execution=True)
    forged = dataclasses.replace(observations[0].observed_decision,
                                 authority_boundary=boundary)
    assert not verify_production_pre_execution_authorization_decision(
        observations[0].authorization_request, forged)
    assert not verify_production_pre_execution_authorization_decision(
        observations[1].authorization_request, observations[0].observed_decision)


def test_all_gate_ordering_digest_chain_and_authority_are_exact():
    report = matrix()[1]
    assert report.ordered_observation_digests == tuple(
        item.observation_digest for item in report.observations)
    for item in report.observations:
        request, decision = item.authorization_request, item.observed_decision
        assert tuple(gate.gate for gate in decision.gate_results) == GATE_ORDER
        assert item.request_digest == request.request_digest == decision.request_digest
        assert item.turn_digest == request.turn_context.turn_digest == decision.turn_digest
        assert item.reference_time_digest == request.reference_time.reference_time_digest
        assert item.feature_gate_evaluation_digest == request.feature_gate_evaluation.evaluation_digest
        assert item.envelope_digest == request.skill_evidence_envelope.envelope_digest
        assert item.activation_binding_digest == request.limited_activation_binding.binding_digest
        assert item.decision_digest == decision.decision_digest
        assert all(getattr(item.authority_boundary, field.name) is False
                   for field in dataclasses.fields(item.authority_boundary))


def test_causal_isolation_from_downstream_entry_points(monkeypatch):
    targets = (
        ("brain.business_skill_cost_execution", "execute_cost_skill"),
        ("brain.business_skill_cost_result_presenter", "present_cost_result"),
        ("brain.business_skill_cost_response_authorization", "authorize_cost_response"),
        ("brain.business_skill_cost_response_adapter", "adapt_authorized_cost_response"),
        ("brain.business_skill_cost_response_delivery_qualification", "qualify_cost_response_delivery"),
        ("brain.business_skill_cost_response_runtime_bridge", "bridge_prepared_cost_response"),
        ("brain.business_skill_cost_runtime_integration_admission_gateway", "decide_controlled_runtime_integration_admission"),
        ("brain.business_skill_cost_runtime_integration_qualification", "qualify_controlled_runtime_integration"),
    )
    import importlib
    def forbidden(*args, **kwargs):
        raise AssertionError("downstream entry point called")
    for module_name, attribute in targets:
        monkeypatch.setattr(importlib.import_module(module_name), attribute, forbidden)
    scenarios = owner.create_production_pre_execution_acceptance_scenarios()
    report = owner.create_production_pre_execution_acceptance_report(scenarios)
    assert report is not None and owner.verify_production_pre_execution_acceptance_report(report)


def test_static_isolation_no_app_wiring_or_forbidden_imports():
    path = ROOT / "brain" / "production_pre_execution_authorization_acceptance.py"
    source = path.read_text("utf-8")
    imports = {node.module for node in ast.walk(ast.parse(source))
               if isinstance(node, ast.ImportFrom)}
    assert "app" not in imports and "from app" not in source and "import app" not in source
    assert "production_pre_execution_authorization_acceptance" not in (ROOT / "app.py").read_text("utf-8")
    assert not any(name in source for name in (
        "business_skill_cost_execution", "business_skill_cost_result_presenter",
        "business_skill_cost_response_adapter", "business_skill_cost_response_delivery",
        "business_skill_cost_response_runtime_bridge", "runtime_integration_admission",
        "streamlit", "requests", "openai", "Decimal(", "float(Decimal",
    ))
    assert not any("production_cost_execution_delivery_integrity" in (name or "")
                   or "canonical_cost_execution_result_integrity" in (name or "")
                   or "cost_rendered_delivery_provenance_integrity" in (name or "")
                   for name in imports)
