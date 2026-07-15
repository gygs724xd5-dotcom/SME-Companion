"""V5.15.24.7.4.1 canonical production pre-execution authorization boundary."""
import ast
import copy
import dataclasses
from datetime import datetime, timezone
import importlib
from pathlib import Path

import pytest

import brain.production_limited_activation_binding as binding_owner
import brain.production_pre_execution_authorization as owner
import brain.production_turn_bound_skill_evidence as envelope_owner
from brain.business_skill_limited_activation_gateway import LIMITED_EXECUTION_DENIED
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_limited_activation_binding import (
    ACTIVATION_DENIED,
    ERROR_CONTAINED,
    create_production_limited_activation_binding,
)
from brain.production_pre_execution_authorization import (
    CONTROLLED_COST_ELIGIBILITY_DENIED,
    CONTROLLED_COST_EVIDENCE_NOT_READY,
    CONTROLLED_COST_RUNTIME_NOT_APPLICABLE,
    DENIED_DEFAULT_PRODUCTION_GATE,
    ELIGIBILITY_DENIED,
    EVIDENCE_NOT_READY,
    GATE_ORDER,
    INVALID_FAIL_CLOSED,
    NOT_APPLICABLE,
    PRODUCTION_FEATURE_GATE_DEFAULT_DENIED,
    PRODUCTION_PRE_EXECUTION_AUTHORIZATION_INVALID,
    PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE,
    PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION,
    create_production_pre_execution_authorization_request,
    evaluate_production_pre_execution_authorization,
    verify_production_pre_execution_authorization_decision,
    verify_production_pre_execution_authorization_request,
)
from brain.production_turn_bound_skill_evidence import (
    create_production_turn_bound_skill_evidence_envelope,
)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time


ROOT = Path(__file__).parents[1]
CHANGE = "my cost increased from 20.00 to 24.000"
CHANGE_WASTE = "my cost increased from 20.00 to 24.000 including waste 2.5 percent"
UNIT = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น"
UNIT_WASTE = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น ของเสีย 2 ชิ้น"
UNRELATED = "hello unrelated question"
NOT_READY = "unit cost"


def foundations(message=CHANGE, conversation="conversation-1", ordinal=1):
    context = create_production_turn_context(conversation, ordinal, message)
    reference = create_production_turn_reference_time(
        context, datetime(2026, 7, 15, 4, 5, 6, tzinfo=timezone.utc)
    )
    gate = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
        context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    envelope = create_production_turn_bound_skill_evidence_envelope(context, gate)
    binding = create_production_limited_activation_binding(
        context, reference, gate, envelope
    )
    assert binding is not None
    return context, reference, gate, envelope, binding


def request_and_decision(message=CHANGE, conversation="conversation-1", ordinal=1):
    values = foundations(message, conversation, ordinal)
    request = create_production_pre_execution_authorization_request(*values)
    assert request is not None
    decision = evaluate_production_pre_execution_authorization(request)
    assert decision is not None
    return values, request, decision


@pytest.mark.parametrize(
    ("message", "skill"),
    (
        (CHANGE, "cost.change_analysis.v1"),
        (CHANGE_WASTE, "cost.change_analysis.v1"),
        (UNIT, "cost.per_unit_calculation.v1"),
        (UNIT_WASTE, "cost.per_unit_calculation.v1"),
    ),
)
def test_eligible_cost_skill_is_deterministically_default_denied(message, skill):
    (_, _, gate, _, binding), request, decision = request_and_decision(message)
    assert (request.version, request.scope) == (
        "5.15.24.7.4.1",
        "CURRENT_DEFAULT_DENIED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION",
    )
    assert (request.version, request.scope) == (
        PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION,
        PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE,
    )
    assert binding.selected_skill_id == decision.selected_skill_id == skill
    assert binding.eligibility_allowed and decision.eligibility_allowed
    assert decision.eligibility_verified and decision.foundations_verified
    assert decision.decision_status == DENIED_DEFAULT_PRODUCTION_GATE
    assert decision.denial_code == PRODUCTION_FEATURE_GATE_DEFAULT_DENIED
    assert not gate.effective_state and not decision.execute_allowed


def test_exact_request_decision_determinism_and_deepcopy_immutability():
    values, request, decision = request_and_decision()
    second_request = create_production_pre_execution_authorization_request(*values)
    second_decision = evaluate_production_pre_execution_authorization(second_request)
    assert request == second_request == copy.deepcopy(request)
    assert decision == second_decision == copy.deepcopy(decision)
    assert request.request_id == second_request.request_id
    assert request.request_digest == second_request.request_digest
    assert decision.decision_digest == second_decision.decision_digest
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.request_digest = "0" * 64
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.execute_allowed = True


def test_exact_cross_artifact_parity_is_exposed_in_decision():
    (context, reference, gate, envelope, binding), request, decision = request_and_decision()
    assert (decision.conversation_id, decision.turn_id, decision.turn_ordinal) == (
        context.conversation_id, context.turn_id, context.turn_ordinal)
    assert decision.turn_digest == context.turn_digest == envelope.turn_digest == binding.turn_digest
    assert decision.user_message_digest == context.user_message_digest == envelope.raw_message_digest
    assert decision.reference_time_digest == reference.reference_time_digest == binding.reference_time_digest
    assert decision.feature_gate_evaluation_digest == gate.evaluation_digest
    assert gate.evaluation_digest == envelope.feature_gate_evaluation_digest == binding.feature_gate_evaluation_digest
    assert decision.envelope_digest == envelope.envelope_digest == binding.envelope_digest
    assert verify_production_pre_execution_authorization_request(request)
    assert verify_production_pre_execution_authorization_decision(request, decision)


@pytest.mark.parametrize(
    ("message", "status", "code", "failed_gate"),
    (
        (UNRELATED, NOT_APPLICABLE, CONTROLLED_COST_RUNTIME_NOT_APPLICABLE, "APPLICABILITY"),
        (NOT_READY, EVIDENCE_NOT_READY, CONTROLLED_COST_EVIDENCE_NOT_READY, "EVIDENCE_READINESS"),
        ("unit cost total cost -2 for 20 units", EVIDENCE_NOT_READY, CONTROLLED_COST_EVIDENCE_NOT_READY, "EVIDENCE_READINESS"),
    ),
)
def test_non_executable_selection_states_precede_default_gate(message, status, code, failed_gate):
    (_, _, _, _, binding), _, decision = request_and_decision(message)
    assert decision.decision_status == status
    assert decision.denial_code == code
    assert decision.diagnostics[0] == "FIRST_FAILED_GATE:" + failed_gate
    assert not decision.eligibility_allowed
    assert not decision.execute_allowed and decision.executable_request is None
    if status == NOT_APPLICABLE:
        assert binding.selected_skill_id is None


def test_upstream_activation_denial_preserves_deterministic_reason(monkeypatch):
    values = foundations()[:4]
    allowed = binding_owner.decide_limited_activation(
        binding_owner._request(values[0], values[1], values[3], 0)
    )
    denied = dataclasses.replace(
        allowed,
        decision=LIMITED_EXECUTION_DENIED,
        eligible_skill_id=None,
        reason_codes=("TEST_POLICY_DENIAL",),
        binding=None,
    )
    monkeypatch.setattr(binding_owner, "decide_limited_activation", lambda request: denied)
    binding = create_production_limited_activation_binding(*values)
    assert binding.binding_status == ACTIVATION_DENIED
    request = create_production_pre_execution_authorization_request(*values, binding)
    decision = evaluate_production_pre_execution_authorization(request)
    assert decision.decision_status == ELIGIBILITY_DENIED
    assert decision.denial_code == CONTROLLED_COST_ELIGIBILITY_DENIED
    assert decision.denial_reason == "TEST_POLICY_DENIAL"
    assert decision.diagnostics[0] == "FIRST_FAILED_GATE:ELIGIBILITY"


def test_upstream_error_contained_is_canonical_invalid_fail_closed(monkeypatch):
    values = foundations()[:4]
    monkeypatch.setattr(
        binding_owner,
        "decide_limited_activation",
        lambda request: (_ for _ in ()).throw(RuntimeError("contained")),
    )
    binding = create_production_limited_activation_binding(*values)
    assert binding.binding_status == ERROR_CONTAINED
    request = create_production_pre_execution_authorization_request(*values, binding)
    assert request is not None
    decision = evaluate_production_pre_execution_authorization(request)
    assert decision.decision_status == INVALID_FAIL_CLOSED
    assert decision.denial_code == PRODUCTION_PRE_EXECUTION_AUTHORIZATION_INVALID
    assert not decision.execute_allowed


@pytest.mark.parametrize("index", range(5))
def test_cross_turn_or_foundation_substitution_cannot_create_request(index):
    first = list(foundations())
    second = foundations("my cost increased from 30 to 41", "conversation-2", 2)
    first[index] = second[index]
    assert create_production_pre_execution_authorization_request(*first) is None


@pytest.mark.parametrize(
    "field,value",
    (
        ("request_id", "production-pre-execution-authorization-request-" + "0" * 64),
        ("request_digest", "0" * 64),
        ("request_digest", "A" * 64),
        ("request_digest", "0" * 63),
        ("version", "5.15.24.7.3"),
        ("scope", "HISTORICAL_OR_WRONG_SCOPE"),
    ),
)
def test_request_identity_version_scope_and_digest_tampering_rejected(field, value):
    _, request, _ = request_and_decision()
    tampered = dataclasses.replace(request, **{field: value})
    assert not verify_production_pre_execution_authorization_request(tampered)
    invalid = evaluate_production_pre_execution_authorization(tampered)
    assert invalid.decision_status == INVALID_FAIL_CLOSED
    assert invalid.gate_results[0].gate == "REQUEST_IDENTITY"
    assert not invalid.gate_results[0].satisfied


@pytest.mark.parametrize(
    "changes",
    (
        {"execute_allowed": True},
        {"executable_request": object()},
        {"controlled_response_candidate": object()},
        {"runtime_permitted": True},
        {"bridge_permitted": True},
        {"admission_permitted": True},
        {"delivery_permitted": True},
        {"response_candidate_permitted": True},
        {"persistence_permitted": True},
        {"tool_execution_permitted": True},
        {"feature_gate_mutation_permitted": True},
        {"decision_status": "AUTHORIZED"},
        {"denial_code": "FORGED"},
        {"denial_reason": "FORGED"},
        {"diagnostics": ("FORGED",)},
        {"decision_digest": "A" * 64},
    ),
)
def test_decision_output_policy_status_and_digest_tampering_rejected(changes):
    _, request, decision = request_and_decision()
    assert not verify_production_pre_execution_authorization_decision(
        request, dataclasses.replace(decision, **changes)
    )


def test_gate_order_duplicate_missing_and_result_tampering_rejected():
    _, request, decision = request_and_decision()
    gates = decision.gate_results
    variants = (
        gates[:-1],
        gates + (gates[-1],),
        (gates[1], gates[0], *gates[2:]),
        (dataclasses.replace(gates[0], satisfied=False), *gates[1:]),
        (dataclasses.replace(gates[0], reason_codes=("FORGED",)), *gates[1:]),
    )
    assert all(
        not verify_production_pre_execution_authorization_decision(
            request, dataclasses.replace(decision, gate_results=tuple(value))
        )
        for value in variants
    )


def test_authority_boundary_escalation_and_cross_request_decision_rejected():
    _, request, decision = request_and_decision()
    authority = dataclasses.replace(decision.authority_boundary, execution=True)
    assert not verify_production_pre_execution_authorization_decision(
        request, dataclasses.replace(decision, authority_boundary=authority)
    )
    _, other_request, _ = request_and_decision(
        "my cost increased from 30 to 41", "conversation-2", 2
    )
    assert not verify_production_pre_execution_authorization_decision(other_request, decision)


def test_configured_denied_enabled_or_gate_identity_substitution_is_out_of_scope():
    values, request, _ = request_and_decision()
    gate = values[2]
    variants = (
        dataclasses.replace(gate, configured_state=True),
        dataclasses.replace(gate, effective_state=True),
        dataclasses.replace(gate, default_denied=False),
        dataclasses.replace(gate, activation_permitted=True),
        dataclasses.replace(gate, mutation_permitted=True),
        dataclasses.replace(gate, gate_name="OTHER_GATE"),
        dataclasses.replace(gate, source_digest="0" * 64),
    )
    assert all(
        create_production_pre_execution_authorization_request(
            values[0], values[1], item, values[3], values[4]
        ) is None
        for item in variants
    )
    assert verify_production_pre_execution_authorization_request(request)


def test_strict_verification_reruns_matcher_mapper_selector_and_gateway(monkeypatch):
    values, request, decision = request_and_decision()
    counts = {"matcher": 0, "mapper": 0, "selector": 0, "gateway": 0}
    targets = (
        (envelope_owner, "match_business_skill_candidates", "matcher"),
        (envelope_owner, "map_candidate_skill_evidence", "mapper"),
        (envelope_owner, "select_shadow_business_skill", "selector"),
        (binding_owner, "decide_limited_activation", "gateway"),
    )
    for module, name, key in targets:
        real = getattr(module, name)
        def wrapper(*args, _real=real, _key=key, **kwargs):
            counts[_key] += 1
            return _real(*args, **kwargs)
        monkeypatch.setattr(module, name, wrapper)
    assert verify_production_pre_execution_authorization_request(request)
    assert verify_production_pre_execution_authorization_decision(request, decision)
    assert all(counts[name] > 0 for name in counts)


def test_all_outputs_are_non_executable_and_authority_false():
    for message in (CHANGE, UNIT, UNRELATED, NOT_READY):
        _, _, decision = request_and_decision(message)
        assert decision.execute_allowed is False
        assert decision.executable_request is None
        assert decision.controlled_response_candidate is None
        assert all(
            getattr(decision, name) is False
            for name in decision.__dataclass_fields__
            if name.endswith("_permitted")
        )
        assert all(
            getattr(decision.authority_boundary, name) is False
            for name in decision.authority_boundary.__dataclass_fields__
        )


def test_causal_isolation_ast_has_no_post_execution_or_runtime_dependencies(monkeypatch):
    path = ROOT / "brain" / "production_pre_execution_authorization.py"
    source = path.read_text("utf-8")
    tree = ast.parse(source)
    imports = tuple(
        node.module or "" for node in tree.body if isinstance(node, ast.ImportFrom)
    )
    forbidden_modules = (
        "production_cost_execution_delivery_integrity",
        "production_single_skill_admission_evidence",
        "production_default_denied_admission_boundary",
        "production_default_denied_admission_acceptance",
        "cost_execution",
        "cost_result_presenter",
        "cost_response_delivery",
        "runtime_bridge",
        "integration_admission",
        "production_response_candidate",
        "production_final_response_resolution",
        "production_turn_commit",
    )
    assert not any(any(term in module for term in forbidden_modules) for module in imports)
    calls = {
        node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    forbidden_calls = {
        "calculate", "present", "authorize", "deliver", "bridge", "admit",
        "commit_assistant_turn", "create_production_response_candidate",
    }
    assert calls.isdisjoint(forbidden_calls)
    assert "app" not in imports and "session_state" not in source
    downstream = (
        ("brain.business_skill_cost_execution", "execute_cost_skill"),
        ("brain.business_skill_cost_result_presenter", "present_cost_result"),
        ("brain.business_skill_cost_response_authorization", "authorize_cost_response"),
        ("brain.business_skill_cost_response_adapter", "adapt_authorized_cost_response"),
        ("brain.business_skill_cost_response_delivery_qualification", "qualify_cost_response_delivery"),
        ("brain.business_skill_cost_response_runtime_bridge", "bridge_prepared_cost_response"),
        ("brain.business_skill_cost_runtime_integration_admission_gateway", "decide_controlled_runtime_integration_admission"),
    )
    def forbidden(*args, **kwargs):
        pytest.fail("downstream production function must not be called")
    for module_name, function_name in downstream:
        monkeypatch.setattr(importlib.import_module(module_name), function_name, forbidden)
    _, request, decision = request_and_decision()
    assert verify_production_pre_execution_authorization_request(request)
    assert verify_production_pre_execution_authorization_decision(request, decision)


def test_boundary_does_not_modify_app_or_import_it():
    source = (ROOT / "brain" / "production_pre_execution_authorization.py").read_text("utf-8")
    assert "from app" not in source and "import app" not in source
    app_source = (ROOT / "app.py").read_text("utf-8")
    assert "from brain.production_pre_execution_authorization import" not in app_source
    assert GATE_ORDER == (
        "REQUEST_IDENTITY", "TURN_CONTEXT", "REFERENCE_TIME",
        "FEATURE_GATE_EVALUATION", "SKILL_EVIDENCE", "ACTIVATION_BINDING",
        "CROSS_ARTIFACT_PARITY", "APPLICABILITY", "EVIDENCE_READINESS",
        "ELIGIBILITY", "DEFAULT_DENY_GATE_STATE", "EXECUTION_AUTHORITY",
        "AUTHORITY_BOUNDARY", "PRE_EXECUTION_ISOLATION",
    )
