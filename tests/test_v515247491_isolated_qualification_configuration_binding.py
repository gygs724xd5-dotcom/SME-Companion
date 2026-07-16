from __future__ import annotations

import ast
import dataclasses
from datetime import datetime, timezone
import inspect
from pathlib import Path

import pytest

import brain.isolated_qualification_configuration_binding as foundation
from brain.isolated_qualification_configuration_binding import *
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
    verify_production_feature_gate_release_wiring_report,
)
from brain.production_feature_gate_transition_approval import (
    TRANSITION_NOT_APPROVED, create_production_feature_gate_transition_approval_request,
    evaluate_production_feature_gate_transition_approval,
)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time
from brain.production_turn_bound_skill_evidence import (
    create_production_turn_bound_skill_evidence_envelope,
    verify_production_turn_bound_skill_evidence_envelope,
)
from brain.production_limited_activation_binding import create_production_limited_activation_binding
from brain.production_pre_execution_authorization import create_production_pre_execution_authorization_request


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "isolated_qualification_configuration_binding.py"


def chain(turn=1, conversation="foundation"):
    context = create_production_turn_context(conversation, turn, "cost changed from 100 to 120 baht")
    reference = create_production_turn_reference_time(context, datetime(2026, 7, 16, tzinfo=timezone.utc))
    config = create_production_feature_gate_configuration(
        PURE_TEST_TRUSTED_SOURCE_IDENTITY, ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),)
    )
    evaluation = evaluate_production_feature_gate(config, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    binding = create_isolated_qualification_feature_gate_binding(context, reference, config, evaluation)
    evidence = create_isolated_qualification_skill_evidence_envelope(binding)
    limited = create_isolated_qualification_limited_activation_binding(evidence)
    result = create_isolated_qualification_pre_execution_result(limited)
    return context, reference, config, evaluation, binding, evidence, limited, result


def test_exact_enabled_foundation_chain_is_deterministic_and_not_acceptance():
    one = chain(); two = chain()
    assert one[4:] == two[4:]
    binding, evidence, limited, result = one[4:]
    assert verify_isolated_qualification_feature_gate_binding(binding)
    assert verify_isolated_qualification_skill_evidence_envelope(evidence)
    assert verify_isolated_qualification_limited_activation_binding(limited)
    assert verify_isolated_qualification_pre_execution_result(result)
    assert binding.configured_state and binding.effective_state and not binding.default_denied
    assert result.status == FOUNDATION_BOUND
    assert not result.requirement_qualified and not result.executable_request_qualified


def test_production_historical_state_and_v749_digests_are_exact():
    owner = get_production_feature_gate_release_owner()
    report = create_production_feature_gate_release_wiring_report()
    assert owner.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert owner.configuration.gate_entries == ()
    assert not owner.configured_state and not owner.effective_state and owner.default_denied
    assert report.report_digest == "f1c24c971a46f1e029743aa72fee71937d7d37aab7971c31e4cfc9bed51f5362"
    assert report.topology_digest == "feb3f68232ea08eb44e72a28bc4700c39402863bb6c6bde9aab4edc3064439c8"
    assert verify_production_feature_gate_release_wiring_report(report)


def test_production_signatures_remain_closed_and_enabled_artifacts_rejected():
    context, reference, _, evaluation, binding, evidence, limited, _ = chain()
    assert tuple(inspect.signature(create_production_turn_bound_skill_evidence_envelope).parameters) == (
        "context", "gate_evaluation", "available_evidence")
    assert tuple(inspect.signature(create_production_limited_activation_binding).parameters) == (
        "context", "reference_time", "gate", "envelope")
    with pytest.raises(ValueError): create_production_turn_bound_skill_evidence_envelope(context, evaluation)
    assert create_production_limited_activation_binding(context, reference, evaluation,
                                                        evidence.canonical_evidence_material) is None
    assert create_production_pre_execution_authorization_request(
        context, reference, evaluation, evidence.canonical_evidence_material,
        limited.canonical_limited_activation_material) is None
    assert not verify_production_turn_bound_skill_evidence_envelope(
        evidence.canonical_evidence_material, context, evaluation)
    assert create_isolated_qualification_skill_evidence_envelope(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION) is None
    assert binding.configuration is not PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION


@pytest.mark.parametrize("field,value", (
    ("version", "x"), ("scope", "x"), ("requirement_identity", "GATE_ENABLED_PREAUTH_QUALIFIED"),
    ("gate_name", "*"), ("configuration_source_identity", "caller"),
    ("configuration_digest", "0" * 64), ("ordered_gate_entries", ()),
    ("evaluation_digest", "0" * 64), ("configured_state", False),
    ("effective_state", False), ("default_denied", True),
    ("production_configuration_digest", "0" * 64), ("release_owner_digest", "0" * 64),
    ("release_revision_id", "x"), ("release_revision_digest", "0" * 64),
    ("binding_digest", "0" * 64),
))
def test_configuration_binding_tampering_fails_closed(field, value):
    binding = chain()[4]
    assert not verify_isolated_qualification_feature_gate_binding(dataclasses.replace(binding, **{field: value}))


def test_configuration_binding_rejects_default_deny_disabled_extra_and_cross_turn():
    context, reference, _, _, binding, *_ = chain()
    default_eval = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    assert create_isolated_qualification_feature_gate_binding(
        context, reference, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, default_eval) is None
    disabled = create_production_feature_gate_configuration(
        PURE_TEST_TRUSTED_SOURCE_IDENTITY, ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, False),))
    assert create_isolated_qualification_feature_gate_binding(
        context, reference, disabled,
        evaluate_production_feature_gate(disabled, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)) is None
    other = chain(2)[0]
    assert create_isolated_qualification_feature_gate_binding(other, reference, binding.configuration, binding.evaluation) is None


@pytest.mark.parametrize("index,field,value", (
    (5, "configuration_binding_digest", "0" * 64), (5, "turn_digest", "0" * 64),
    (5, "reference_time_digest", "0" * 64), (5, "evaluation_digest", "0" * 64),
    (5, "evidence_material_digest", "0" * 64), (5, "envelope_digest", "0" * 64),
    (6, "ordered_upstream_digests", ()), (6, "lifecycle_is_not_production_activation", False),
    (6, "activation_permitted", True), (6, "application_permitted", True),
    (6, "binding_digest", "0" * 64), (7, "ordered_input_digests", ()),
    (7, "gate_enabled_verified", False), (7, "evidence_verified", False),
    (7, "limited_activation_verified", False), (7, "status", "QUALIFIED"),
    (7, "requirement_qualified", True), (7, "executable_request_qualified", True),
    (7, "execute_allowed", True), (7, "dispatch_permitted", True),
    (7, "production_application_permitted", True), (7, "runtime_invocation_permitted", True),
    (7, "result_digest", "0" * 64),
))
def test_downstream_tampering_and_authority_attacks_fail_closed(index, field, value):
    item = chain()[index]
    verifier = (verify_isolated_qualification_skill_evidence_envelope if index == 5 else
                verify_isolated_qualification_limited_activation_binding if index == 6 else
                verify_isolated_qualification_pre_execution_result)
    assert not verifier(dataclasses.replace(item, **{field: value}))


def test_cross_substitution_is_rejected_at_every_downstream_boundary():
    one, two = chain(), chain(2)
    assert not verify_isolated_qualification_skill_evidence_envelope(
        dataclasses.replace(one[5], configuration_binding=two[4]))
    assert not verify_isolated_qualification_limited_activation_binding(
        dataclasses.replace(one[6], evidence_envelope=two[5]))
    assert not verify_isolated_qualification_pre_execution_result(
        dataclasses.replace(one[7], limited_activation_binding=two[6]))


def test_all_authority_fields_are_false_and_no_executable_artifact_exists():
    for item in chain()[4:]:
        assert all(getattr(item.authority_boundary, f.name) is False
                   for f in dataclasses.fields(item.authority_boundary))
    result = chain()[7]
    assert result.executable_request is None and not result.execute_allowed
    assert not result.dispatch_permitted and not result.runtime_invocation_permitted


def test_approval_policy_continuity_keeps_gate_enabled_requirement_missing():
    owner = get_production_feature_gate_release_owner()
    proposal = create_production_feature_gate_transition_proposal(LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    request = create_production_feature_gate_transition_approval_request(owner, proposal)
    decision = evaluate_production_feature_gate_transition_approval(request)
    requirement = next(x for x in decision.requirements if x.requirement_id == "GATE_ENABLED_PREAUTH_QUALIFIED")
    assert decision.status == TRANSITION_NOT_APPROVED
    assert not requirement.verified and requirement.evidence_digest is None
    assert not decision.transition_approved and not decision.application_permitted
    assert not decision.activation_permitted and not decision.transition_applied


def test_module_static_isolation_and_no_caller_authority_parameters():
    source = MODULE.read_text(encoding="utf-8")
    lower = source.lower()
    for forbidden in ("streamlit", "session_state", "os.environ", "getenv", "subprocess",
                      "requests", "socket", "open(", "write("):
        assert forbidden not in lower
    tree = ast.parse(source)
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert calls.isdisjoint({"calculator", "delivery", "bridge", "admission", "runtime", "execute"})
    for name in (
        "create_isolated_qualification_feature_gate_binding",
        "create_isolated_qualification_skill_evidence_envelope",
        "create_isolated_qualification_limited_activation_binding",
        "create_isolated_qualification_pre_execution_result",
    ):
        params = inspect.signature(getattr(foundation, name)).parameters
        assert not set(params).intersection({"qualification", "trusted", "approved", "passed", "allow_enabled"})

