from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

import brain.production_feature_gate_release_wiring_acceptance as acceptance
from brain.production_feature_gate_release_wiring_acceptance import (
    ACCEPTANCE_DIAGNOSTIC, CANONICAL_SCENARIO_IDS,
    EXPECTED_HISTORICAL_CONFIGURATION_DIGEST, EXPECTED_PRODUCTION_TOPOLOGY,
    PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_SCOPE,
    PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION,
    READ_ONLY_RELEASE_WIRING_ACCEPTED, TOPOLOGY_TRUST_CLASSIFICATION,
    ProductionFeatureGateReleaseWiringAuthorityBoundary,
    create_production_feature_gate_release_wiring_report,
    verify_production_feature_gate_release_wiring_observation,
    verify_production_feature_gate_release_wiring_report,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_feature_gate_release_owner import (
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
)
from brain.production_feature_gate_release_runtime import (
    resolve_production_feature_gate_release_runtime_binding,
)
from brain.production_turn_context import create_production_turn_context


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
MODULE = ROOT / "brain" / "production_feature_gate_release_wiring_acceptance.py"


def report():
    return create_production_feature_gate_release_wiring_report()


def test_contract_inventory_status_and_limited_trust_claim_are_exact():
    value = report()
    assert PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION == "5.15.24.7.4.9"
    assert PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_SCOPE == "SOURCE_CONTROLLED_READ_ONLY_RELEASE_GATE_WIRING_ACCEPTANCE"
    assert value.canonical_scenario_ids == CANONICAL_SCENARIO_IDS
    assert tuple(item.scenario.scenario_id for item in value.observations) == CANONICAL_SCENARIO_IDS
    assert value.total_count == len(CANONICAL_SCENARIO_IDS) == 10
    assert value.acceptance_status == READ_ONLY_RELEASE_WIRING_ACCEPTED
    assert value.diagnostics == (ACCEPTANCE_DIAGNOSTIC,)
    assert value.all_passed and verify_production_feature_gate_release_wiring_report(value)


def test_report_counts_prove_empty_default_deny_and_zero_authority_only():
    value = report()
    assert value.owner_verified_count == value.configuration_identity_verified_count == 10
    assert value.evaluation_equivalence_verified_count == value.runtime_binding_verified_count == 10
    assert value.rerun_reuse_verified_count == value.turn_separation_verified_count == 10
    assert value.proposal_applied_count == value.transition_applied_count == 0
    assert value.rollback_applied_count == value.enabled_effective_true_count == 0
    assert value.activation_mutation_permission_count == value.authority_violation_count == 0
    assert value.persistence_runtime_invocation_count == 0
    assert all((not item.configured_state and not item.effective_state and item.default_denied)
               for item in value.observations)


def test_topology_is_explicit_contract_expectation_not_source_or_deployment_attestation():
    value = report()
    assert value.topology == EXPECTED_PRODUCTION_TOPOLOGY
    assert value.topology_trust_classification == TOPOLOGY_TRUST_CLASSIFICATION
    assert "NOT_SOURCE_OR_DEPLOYED_SHA_ATTESTATION" in value.topology_trust_classification
    assert not any((value.deployment_attested, value.human_approval_attested,
                    value.ci_attested, value.activation_approved))


def test_observations_bind_exact_owner_configuration_evaluation_and_runtime_artifacts():
    owner = get_production_feature_gate_release_owner()
    for item in report().observations:
        assert item.release_owner is owner
        assert item.configuration_digest == EXPECTED_HISTORICAL_CONFIGURATION_DIGEST
        assert item.release_owner_digest == owner.owner_digest
        assert item.release_revision_digest == owner.release_revision.revision_digest
        assert item.evaluation_digest == item.runtime_binding.evaluation_digest
        assert item.runtime_binding_digest == item.runtime_binding.binding_digest
        assert verify_production_feature_gate_release_wiring_observation(item)


def test_direct_historical_and_release_owner_evaluations_remain_exactly_equal():
    context = create_production_turn_context("acceptance-equivalence", 1, "ต้นทุน 100 บาท")
    owner = get_production_feature_gate_release_owner()
    direct = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    backed = evaluate_production_feature_gate(
        owner.configuration, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    assert owner.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert owner.configuration_digest == EXPECTED_HISTORICAL_CONFIGURATION_DIGEST
    assert direct == backed and direct.evaluation_digest == backed.evaluation_digest


def test_unmodified_resolver_reuses_exact_rerun_and_separates_next_turn():
    owner = get_production_feature_gate_release_owner()
    one = create_production_turn_context("acceptance-resolver", 1, "หนึ่ง")
    one_eval = evaluate_production_feature_gate(owner.configuration, one, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    binding = resolve_production_feature_gate_release_runtime_binding(one, owner, one_eval)
    assert resolve_production_feature_gate_release_runtime_binding(one, owner, one_eval, binding) is binding
    two = create_production_turn_context("acceptance-resolver", 2, "สอง")
    two_eval = evaluate_production_feature_gate(owner.configuration, two, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    next_binding = resolve_production_feature_gate_release_runtime_binding(two, owner, two_eval, binding)
    assert next_binding is not binding and next_binding.turn_digest != binding.turn_digest


def test_resolver_rejections_never_become_synthetic_observations():
    owner = get_production_feature_gate_release_owner()
    context = create_production_turn_context("acceptance-reject", 1, "test")
    evaluation = evaluate_production_feature_gate(owner.configuration, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    other = create_production_turn_context("acceptance-reject", 2, "other")
    other_evaluation = evaluate_production_feature_gate(owner.configuration, other, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    proposal = create_production_feature_gate_transition_proposal(LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    bad_owner = dataclasses.replace(owner, owner_digest="0" * 64)
    assert resolve_production_feature_gate_release_runtime_binding(None, owner, evaluation) is None
    assert resolve_production_feature_gate_release_runtime_binding(context, bad_owner, evaluation) is None
    assert resolve_production_feature_gate_release_runtime_binding(context, owner, other_evaluation) is None
    assert resolve_production_feature_gate_release_runtime_binding(context, owner, dataclasses.replace(evaluation, evaluation_digest="0" * 64)) is None
    assert resolve_production_feature_gate_release_runtime_binding(context, proposal, evaluation) is None


@pytest.mark.parametrize("field,value", (
    ("release_owner_digest", "0" * 64), ("release_revision_digest", "0" * 64),
    ("configuration_digest", "0" * 64), ("evaluation_digest", "0" * 64),
    ("runtime_binding_digest", "0" * 64), ("proposal_applied", True),
    ("transition_applied", True), ("rollback_applied", True),
    ("configured_state", True), ("effective_state", True),
    ("activation_permitted", True), ("mutation_permitted", True),
    ("observation_passed", False), ("deterministic_observed_outcome", "tampered"),
    ("observation_digest", "0" * 64),
))
def test_observation_verifier_rejects_artifact_state_permission_and_outcome_tampering(field, value):
    item = report().observations[0]
    assert not verify_production_feature_gate_release_wiring_observation(
        dataclasses.replace(item, **{field: value})
    )


@pytest.mark.parametrize("digest", ("", "A" * 64, "g" * 64, "0" * 63, "0" * 65))
@pytest.mark.parametrize("field", ("topology_digest", "report_digest"))
def test_report_verifier_rejects_every_malformed_digest_form(field, digest):
    assert not verify_production_feature_gate_release_wiring_report(
        dataclasses.replace(report(), **{field: digest})
    )


@pytest.mark.parametrize("field,value", (
    ("total_count", 9), ("owner_verified_count", 9),
    ("configuration_identity_verified_count", 9), ("evaluation_equivalence_verified_count", 9),
    ("runtime_binding_verified_count", 9), ("rerun_reuse_verified_count", 9),
    ("turn_separation_verified_count", 9), ("proposal_applied_count", 1),
    ("transition_applied_count", 1), ("rollback_applied_count", 1),
    ("enabled_effective_true_count", 1), ("activation_mutation_permission_count", 1),
    ("authority_violation_count", 1), ("persistence_runtime_invocation_count", 1),
    ("acceptance_status", "DEPLOYED"), ("diagnostics", ("tampered",)),
    ("deployment_attested", True), ("human_approval_attested", True),
    ("ci_attested", True), ("activation_approved", True), ("all_passed", False),
))
def test_report_verifier_rejects_count_status_diagnostic_and_attestation_tampering(field, value):
    assert not verify_production_feature_gate_release_wiring_report(
        dataclasses.replace(report(), **{field: value})
    )


def test_report_verifier_rejects_topology_and_scenario_drop_duplicate_or_reorder():
    value = report()
    variants = (
        dataclasses.replace(value, topology=value.topology[:-1]),
        dataclasses.replace(value, topology=value.topology[::-1]),
        dataclasses.replace(value, topology=value.topology + (value.topology[0],)),
        dataclasses.replace(value, observations=value.observations[:-1]),
        dataclasses.replace(value, observations=value.observations[::-1]),
        dataclasses.replace(value, observations=value.observations + (value.observations[0],)),
        dataclasses.replace(value, canonical_scenario_ids=value.canonical_scenario_ids[:-1]),
        dataclasses.replace(value, ordered_observation_digests=value.ordered_observation_digests[::-1]),
    )
    assert all(not verify_production_feature_gate_release_wiring_report(item) for item in variants)


def test_authority_escalation_and_cross_turn_binding_are_rejected():
    value = report()
    item = value.observations[0]
    escalated = dataclasses.replace(item, authority_boundary=dataclasses.replace(
        ProductionFeatureGateReleaseWiringAuthorityBoundary(), runtime=True
    ))
    cross_turn = dataclasses.replace(item, runtime_binding=value.observations[5].runtime_binding)
    assert not verify_production_feature_gate_release_wiring_observation(escalated)
    assert not verify_production_feature_gate_release_wiring_observation(cross_turn)


def test_acceptance_isolated_from_every_downstream_execution_surface(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("downstream surface invoked")
    for name in (
        "calculator", "execution", "presentation", "authorization", "adapter", "delivery",
        "bridge", "admission", "runtime", "controlled_response_candidate",
    ):
        monkeypatch.setattr(acceptance, name, forbidden, raising=False)
    value = create_production_feature_gate_release_wiring_report()
    assert verify_production_feature_gate_release_wiring_report(value)


def test_app_ast_exact_single_call_sites_order_and_no_release_artifact_branch():
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    chat = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                and node.name == "_show_chat_companion")
    calls = [node for node in ast.walk(chat) if isinstance(node, ast.Call)]
    def line(name):
        return next(node.lineno for node in calls if isinstance(node.func, ast.Name) and node.func.id == name)
    order = tuple(map(line, (
        "resolve_production_turn_context", "resolve_production_turn_reference_time",
        "get_production_feature_gate_release_owner", "resolve_production_feature_gate_evaluation",
        "resolve_production_feature_gate_release_runtime_binding",
        "resolve_production_turn_bound_skill_evidence_envelope",
        "resolve_production_limited_activation_binding",
        "resolve_production_pre_execution_authorization_runtime_evidence",
    )))
    assert order == tuple(sorted(order))
    assert source.count("get_production_feature_gate_release_owner()") == 1
    assert source.count("resolve_production_feature_gate_release_runtime_binding(") == 1
    assert "PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION" not in source
    release_terms = ("production_feature_gate_release_owner", "production_feature_gate_evaluation",
                     "production_feature_gate_release_runtime_binding")
    assert not any(isinstance(node, (ast.If, ast.IfExp, ast.While))
                   and any(term in ast.unparse(node.test) for term in release_terms)
                   for node in ast.walk(chat))


def test_app_ast_lifecycle_quick_action_session_isolation_and_no_application_calls():
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for name in ("_reset_chat_session", "_legacy_reset_conversation_state_for_demo_switch",
                 "_reset_conversation_state_for_demo_switch"):
        function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
        assert "current_production_feature_gate_release_runtime_binding" in ast.unparse(function)
    quick = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                 and node.name == "_handle_quick_action_conversation")
    assert "feature_gate_release" not in ast.unparse(quick)
    forbidden = ("apply_production_feature_gate", "apply_transition", "apply_rollback",
                 "controlled_response_candidate", "release_wiring_acceptance")
    assert not any(token in source for token in forbidden)


def test_acceptance_module_static_purity_has_no_external_or_downstream_calls():
    source = MODULE.read_text(encoding="utf-8").lower()
    for forbidden in ("streamlit", "session_state", "st.secrets", "os.environ", "getenv",
                      "subprocess", "requests", "socket", "open(", "write("):
        assert forbidden not in source
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name)}
    assert calls.isdisjoint({"calculator", "execution", "presentation", "authorization",
                             "adapter", "delivery", "bridge", "admission", "runtime",
                             "controlled_response_candidate"})
