from __future__ import annotations

import ast
import dataclasses
from datetime import datetime, timezone
import inspect
from pathlib import Path

import pytest

import brain.isolated_gate_enabled_pre_authorization_qualification as qualification
from brain.isolated_gate_enabled_pre_authorization_qualification import *
from brain.isolated_qualification_configuration_binding import (
    FOUNDATION_BOUND,
    create_isolated_qualification_feature_gate_binding,
    create_isolated_qualification_limited_activation_binding,
    create_isolated_qualification_pre_execution_result,
    create_isolated_qualification_skill_evidence_envelope,
    verify_isolated_qualification_pre_execution_result,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    PURE_TEST_TRUSTED_SOURCE_IDENTITY, create_production_feature_gate_configuration,
    evaluate_production_feature_gate,
)
from brain.production_feature_gate_release_owner import (
    create_production_feature_gate_transition_proposal, get_production_feature_gate_release_owner,
)
from brain.production_feature_gate_release_wiring_acceptance import (
    create_production_feature_gate_release_wiring_report,
)
from brain.production_feature_gate_transition_approval import (
    TRANSITION_NOT_APPROVED, create_production_feature_gate_transition_approval_request,
    evaluate_production_feature_gate_transition_approval,
)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "isolated_gate_enabled_pre_authorization_qualification.py"


def chain(turn=1, conversation="gate-enabled-preauth-qualification"):
    context = create_production_turn_context(conversation, turn, "cost changed from 100 to 120 baht")
    reference = create_production_turn_reference_time(context, datetime(2026, 7, 16, tzinfo=timezone.utc))
    configuration = create_production_feature_gate_configuration(
        PURE_TEST_TRUSTED_SOURCE_IDENTITY, ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),)
    )
    evaluation = evaluate_production_feature_gate(configuration, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    binding = create_isolated_qualification_feature_gate_binding(context, reference, configuration, evaluation)
    evidence = create_isolated_qualification_skill_evidence_envelope(binding)
    limited = create_isolated_qualification_limited_activation_binding(evidence)
    result = create_isolated_qualification_pre_execution_result(limited)
    return context, reference, configuration, evaluation, binding, evidence, limited, result


def report():
    return create_isolated_gate_enabled_pre_authorization_report(chain()[7])


def test_canonical_full_chain_qualifies_deterministically():
    one, two = report(), report()
    assert one == two and verify_isolated_gate_enabled_pre_authorization_report(one)
    assert one.requirement_id == GATE_ENABLED_PREAUTH_QUALIFIED
    assert one.qualified and one.status == GATE_ENABLED_PREAUTH_QUALIFIED
    assert one.diagnostics == (QUALIFICATION_DIAGNOSTIC,)
    assert one.total_count == one.passed_count == 16
    assert len(set(one.canonical_scenario_ids)) == 16


def test_foundation_remains_non_self_authorizing_and_forgery_is_rejected():
    foundation = chain()[7]
    accepted = create_isolated_gate_enabled_pre_authorization_report(foundation)
    assert foundation.status == FOUNDATION_BOUND
    assert not foundation.requirement_qualified and not foundation.executable_request_qualified
    assert accepted.qualified and accepted.foundation_result is foundation
    forged = dataclasses.replace(foundation, requirement_qualified=True)
    assert not verify_isolated_qualification_pre_execution_result(forged)
    assert create_isolated_gate_enabled_pre_authorization_report(forged) is None


@pytest.mark.parametrize("target,field,value", (
    ("binding", "gate_name", "*"), ("binding", "configured_state", False),
    ("binding", "effective_state", False), ("binding", "default_denied", True),
    ("binding", "configuration_digest", "0" * 64), ("binding", "evaluation_digest", "0" * 64),
    ("result", "version", "x"), ("result", "scope", "x"),
))
def test_enabled_state_and_foundation_identity_tampering_rejected(target, field, value):
    result = chain()[7]
    if target == "binding":
        result = dataclasses.replace(result, configuration_binding=dataclasses.replace(
            result.configuration_binding, **{field: value}))
    else:
        result = dataclasses.replace(result, **{field: value})
    assert create_isolated_gate_enabled_pre_authorization_report(result) is None


def test_turn_reference_and_cross_chain_substitution_rejected():
    one, two = chain(), chain(2)
    for forged in (
        dataclasses.replace(one[7], configuration_binding=two[4]),
        dataclasses.replace(one[7], evidence_envelope=two[5]),
        dataclasses.replace(one[7], limited_activation_binding=two[6]),
        dataclasses.replace(one[7], ordered_input_digests=two[7].ordered_input_digests),
    ):
        assert create_isolated_gate_enabled_pre_authorization_report(forged) is None


def test_production_release_and_proposal_remain_unchanged():
    before = get_production_feature_gate_release_owner()
    accepted = report()
    after = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    assert before is after is accepted.foundation_result.configuration_binding.release_owner
    assert after.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert after.configuration.gate_entries == ()
    assert not after.configured_state and not after.effective_state and after.default_denied
    assert not after.transition_applied and not after.activation_permitted and not after.mutation_permitted
    assert not proposal.transition_applied and not proposal.approval_verified
    assert not proposal.activation_permitted and not proposal.mutation_permitted


@pytest.mark.parametrize("field,value", (
    ("requirement_qualified", True), ("executable_request_qualified", True),
    ("execute_allowed", True), ("executable_request", object()),
    ("dispatch_permitted", True), ("production_application_permitted", True),
    ("runtime_invocation_permitted", True),
))
def test_executable_request_and_runtime_authority_injection_rejected(field, value):
    forged = dataclasses.replace(chain()[7], **{field: value})
    assert create_isolated_gate_enabled_pre_authorization_report(forged) is None
    accepted = report()
    assert not accepted.executable_request_qualified
    assert accepted.controlled_runtime_invocation_count == 0


@pytest.mark.parametrize("field,value", (
    ("requirement_id", "EXECUTABLE_REQUEST_QUALIFIED"), ("total_count", 15),
    ("passed_count", 15), ("qualified", False), ("status", "APPROVED"),
    ("diagnostics", ("caller",)), ("topology_digest", "0" * 64),
    ("report_digest", "0" * 64), ("controlled_runtime_invocation_count", 1),
    ("transition_approved", True), ("transition_applied", True),
    ("application_permitted", True), ("activation_permitted", True),
    ("executable_request_qualified", True), ("source_sha_attested", True),
    ("deployed_sha_attested", True),
))
def test_report_claim_count_status_digest_and_authority_tampering_rejected(field, value):
    assert not verify_isolated_gate_enabled_pre_authorization_report(
        dataclasses.replace(report(), **{field: value})
    )


def test_scenario_reorder_drop_duplicate_unknown_and_outcome_tampering_rejected():
    accepted = report()
    observations = accepted.observations
    unknown = dataclasses.replace(observations[0].scenario, scenario_id="99.unknown")
    variants = (
        observations[::-1], observations[:-1], observations + (observations[0],),
        (dataclasses.replace(observations[0], scenario=unknown),) + observations[1:],
        (dataclasses.replace(observations[0], observation_passed=False),) + observations[1:],
        (dataclasses.replace(observations[0], deterministic_observed_outcome="FORGED"),) + observations[1:],
    )
    for variant in variants:
        assert not verify_isolated_gate_enabled_pre_authorization_report(
            dataclasses.replace(accepted, observations=variant)
        )


def test_observation_verifier_recomputes_from_canonical_foundation():
    accepted = report()
    assert all(verify_isolated_gate_enabled_pre_authorization_observation(
        observation, accepted.foundation_result) for observation in accepted.observations)
    assert not verify_isolated_gate_enabled_pre_authorization_observation(
        accepted.observations[0], chain(2)[7])
    assert not verify_isolated_gate_enabled_pre_authorization_observation(
        dataclasses.replace(accepted.observations[0], observation_digest="0" * 64),
        accepted.foundation_result)


def test_authority_boundary_is_frozen_false_and_has_no_mutating_api():
    accepted = report()
    assert dataclasses.is_dataclass(accepted) and accepted.__dataclass_params__.frozen
    for boundary in (accepted.authority_boundary,) + tuple(x.authority_boundary for x in accepted.observations):
        assert all(getattr(boundary, field.name) is False for field in dataclasses.fields(boundary))
    for name in vars(qualification):
        assert not name.startswith(("set_", "apply_", "enable_", "activate_", "dispatch_", "execute_"))


def test_public_builders_accept_no_caller_outcomes_or_authority():
    forbidden = {"passed", "qualified", "accepted", "trusted", "approved", "requirement_qualified",
                 "tests_passed", "activation", "application", "mode", "purpose",
                 "executable_request_qualified"}
    for name in ("create_isolated_gate_enabled_pre_authorization_report",
                 "verify_isolated_gate_enabled_pre_authorization_observation",
                 "verify_isolated_gate_enabled_pre_authorization_report"):
        assert forbidden.isdisjoint(inspect.signature(getattr(qualification, name)).parameters)


def test_historical_digests_and_approval_policy_are_unchanged():
    historical = create_production_feature_gate_release_wiring_report()
    assert historical.report_digest == "f1c24c971a46f1e029743aa72fee71937d7d37aab7971c31e4cfc9bed51f5362"
    assert historical.topology_digest == "feb3f68232ea08eb44e72a28bc4700c39402863bb6c6bde9aab4edc3064439c8"
    fixed = chain(conversation="foundation")
    assert fixed[2].source_digest == "a1add688ffa4943d9f848e7322847fed8de59d0f5f29bfe272576b4a8accd1ae"
    assert fixed[3].evaluation_digest == "7e4ca136f03b33b3f786f2295d7faf7123396879efc6fbf78080d098d43b4ffe"
    assert fixed[4].binding_digest == "87814ef7517868c4aa5695d20c678c4e92c5b7e613c71d23f24d1984da6de11a"
    assert fixed[5].envelope_digest == "e71c2f1200a60b0926e95095d1c18c66e32f99372dcf0fabdf7a4e14ebe6d038"
    assert fixed[6].binding_digest == "931f6b098f83cae7f89b9cd9bd4faf9eb38df070f8be3c68ae9e7c91a5b8f9a7"
    assert fixed[7].result_digest == "fb7459d151f3be03719a395c20db35ebe4cce70fc2ebddd8c042b42efe3b77d8"
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    decision = evaluate_production_feature_gate_transition_approval(
        create_production_feature_gate_transition_approval_request(owner, proposal))
    assert decision.status == TRANSITION_NOT_APPROVED
    assert decision.primary_denial == "READ_ONLY_RELEASE_WIRING_ACCEPTED"
    assert not decision.transition_approved and not decision.application_permitted
    assert not decision.activation_permitted and not decision.transition_applied


def test_static_isolation_has_no_app_io_environment_or_downstream_invocation():
    source = MODULE.read_text(encoding="utf-8")
    lower = source.lower()
    for forbidden in ("import app", "streamlit", "session_state", "os.environ", "getenv", "subprocess",
                      "requests", "socket", "open(", "write("):
        assert forbidden not in lower
    tree = ast.parse(source)
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert calls.isdisjoint({"calculator", "delivery", "bridge", "admission", "runtime", "execute"})
