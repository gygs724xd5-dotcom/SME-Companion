"""V5.15.24.7 passive production limited-activation decision binding."""
import ast
import dataclasses
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

import brain.production_limited_activation_binding as owner
from brain.business_skill_limited_activation_gateway import (
    LIMITED_EXECUTION_DENIED,
    LimitedActivationDecision,
    verify_activation_request_binding,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_limited_activation_binding import (
    ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED,
    ACTIVATION_DENIED,
    EVIDENCE_NOT_READY,
    ERROR_CONTAINED,
    NOT_APPLICABLE,
    PRODUCTION_LIMITED_ACTIVATION_BINDING_SCOPE,
    PRODUCTION_LIMITED_ACTIVATION_BINDING_VERSION,
    create_production_limited_activation_binding,
    derive_production_activation_request_id,
    resolve_production_limited_activation_binding,
    verify_production_limited_activation_binding,
)
from brain.production_turn_bound_skill_evidence import (
    create_production_turn_bound_skill_evidence_envelope,
)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time


ROOT = Path(__file__).parents[1]
CHANGE = "my cost increased from 20.00 to 24.000"
UNIT = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น"


def foundations(message=CHANGE, conversation="conversation-1", ordinal=1):
    context = create_production_turn_context(conversation, ordinal, message)
    reference = create_production_turn_reference_time(
        context, datetime(2026, 7, 14, 3, 4, 5, tzinfo=timezone.utc))
    gate = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
        context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    envelope = create_production_turn_bound_skill_evidence_envelope(context, gate)
    return context, reference, gate, envelope


def binding(message=CHANGE, conversation="conversation-1", ordinal=1):
    values = foundations(message, conversation, ordinal)
    artifact = create_production_limited_activation_binding(*values)
    assert artifact is not None
    assert verify_production_limited_activation_binding(artifact, *values)
    return (*values, artifact)


@pytest.mark.parametrize(("message", "skill"), (
    (CHANGE, "cost.change_analysis.v1"),
    (UNIT, "cost.per_unit_calculation.v1"),
))
def test_allowed_decisions_are_passive_and_production_gate_remains_default_denied(message, skill):
    context, reference, gate, envelope, value = binding(message)
    assert (value.version, value.scope) == (
        PRODUCTION_LIMITED_ACTIVATION_BINDING_VERSION,
        PRODUCTION_LIMITED_ACTIVATION_BINDING_SCOPE) == (
        "5.15.24.7", "VERIFIED_TURN_LIMITED_ACTIVATION_DECISION")
    assert value.selected_skill_id == skill
    assert value.binding_status == ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED
    assert value.eligibility_allowed and value.production_gate_blocked
    assert not gate.effective_state and not gate.activation_permitted
    assert verify_activation_request_binding(value.limited_activation_decision.binding)
    assert all(getattr(value, name) is False for name in value.__dataclass_fields__
               if name.endswith("_authority") or name.endswith("_permitted"))


def test_request_is_deterministic_raw_message_reference_time_and_exact_chain_owned():
    context, reference, _, envelope, value = binding("  " + CHANGE + "\n")
    request = value.activation_request
    assert request.request_id == derive_production_activation_request_id(context, reference, envelope)
    assert request.request_id.startswith("production-limited-activation-")
    assert len(request.request_id) == len("production-limited-activation-") + 64
    assert request.current_message == context.user_message
    assert request.reference_time == reference.accepted_at_iso == "2026-07-14T03:04:05+00:00"
    assert value.limited_activation_decision.binding.current_message == context.user_message.strip()
    assert value.activation_request_binding_digest == value.limited_activation_decision.binding.binding_digest


def test_decimal_values_are_parser_owned_and_binding_lossless():
    _, _, _, envelope, value = binding(CHANGE)
    parsed = envelope.canonical_parse_results[0].evidence_values
    snapshot = value.limited_activation_decision.binding.evidence_snapshot
    assert [item.evidence_id for item in snapshot] == [item.required_evidence_id for item in parsed]
    assert all(type(item.normalized_value) is Decimal for item in snapshot)
    assert [item.normalized_value.as_tuple() for item in snapshot] == [
        Decimal(item.canonical_decimal).as_tuple() for item in parsed]


@pytest.mark.parametrize(("message", "status"), (
    ("hello unrelated question", NOT_APPLICABLE),
    ("ต้นทุนต่อชิ้น", EVIDENCE_NOT_READY),
    ("ต้นทุนเดิม 30", NOT_APPLICABLE),
    ("ต้นทุนจาก 30 เป็น 40 และต้นทุนจาก 50 เป็น 60", NOT_APPLICABLE),
    ("ต้นทุนต่อชิ้น ต้นทุนรวม -2 บาท ทำได้ 20 ชิ้น", EVIDENCE_NOT_READY),
))
def test_no_selection_representation_never_calls_gateway(monkeypatch, message, status):
    values = foundations(message)
    assert values[-1].selected_skill_id is None
    monkeypatch.setattr(owner, "decide_limited_activation",
                        lambda request: pytest.fail("gateway must not be called"))
    value = create_production_limited_activation_binding(*values)
    assert value.binding_status == status
    assert value.activation_request_id is value.activation_request is None
    assert value.limited_activation_decision is None
    assert "GATEWAY_NOT_CALLED" in value.reasons


def test_gateway_denial_and_exception_are_passively_contained(monkeypatch):
    values = foundations()
    real = owner.decide_limited_activation
    allowed = real(owner._request(values[0], values[1], values[3], 0))
    denied = dataclasses.replace(
        allowed, decision=LIMITED_EXECUTION_DENIED, eligible_skill_id=None,
        reason_codes=("TEST_POLICY_DENIAL",), binding=None)
    monkeypatch.setattr(owner, "decide_limited_activation", lambda request: denied)
    value = create_production_limited_activation_binding(*values)
    assert value.binding_status == ACTIVATION_DENIED and not value.eligibility_allowed
    assert value.limited_activation_decision is denied
    monkeypatch.setattr(owner, "decide_limited_activation",
                        lambda request: (_ for _ in ()).throw(RuntimeError("contained")))
    error = create_production_limited_activation_binding(*values)
    assert error.binding_status == ERROR_CONTAINED
    assert error.limited_activation_decision is None
    assert not error.execution_permitted


def test_exact_rerun_reuse_and_next_turn_replacement():
    values = foundations()
    first = resolve_production_limited_activation_binding(None, *values)
    assert resolve_production_limited_activation_binding(first, *values) is first
    next_values = foundations(CHANGE, ordinal=2)
    second = resolve_production_limited_activation_binding(first, *next_values)
    assert second != first and second.turn_id == "turn-2"


def test_strict_verifier_rejects_cross_turn_and_all_provenance_or_authority_tampering():
    context, reference, gate, envelope, value = binding()
    other = foundations("ต้นทุนเพิ่มจาก 30 เป็น 41 บาท", "conversation-2")
    assert not verify_production_limited_activation_binding(value, *other)
    request = value.activation_request
    decision = value.limited_activation_decision
    bad = (
        dataclasses.replace(value, turn_digest="0" * 64),
        dataclasses.replace(value, raw_message_digest="0" * 64),
        dataclasses.replace(value, selected_skill_id="cost.per_unit_calculation.v1"),
        dataclasses.replace(value, reference_time_iso="2026-07-14T03:04:06+00:00"),
        dataclasses.replace(value, feature_gate_effective_state=True),
        dataclasses.replace(value, envelope_digest="0" * 64),
        dataclasses.replace(value, activation_request_id="production-limited-activation-" + "A" * 64),
        dataclasses.replace(value, activation_request=dataclasses.replace(request, current_message="forged")),
        dataclasses.replace(value, limited_activation_decision=dataclasses.replace(decision, request_id="forged")),
        dataclasses.replace(value, activation_request_binding_digest="0" * 64),
        dataclasses.replace(value, execution_permitted=True),
        dataclasses.replace(value, delivery_permitted=True),
        dataclasses.replace(value, admission_authority=True),
        dataclasses.replace(value, binding_status=ACTIVATION_DENIED),
        dataclasses.replace(value, binding_digest="A" * 64),
        dataclasses.replace(value, binding_digest="0" * 63),
    )
    assert all(not verify_production_limited_activation_binding(item, context, reference, gate, envelope)
               for item in bad)


def test_invalid_foundations_fail_closed_without_artifact():
    context, reference, gate, envelope = foundations()
    assert create_production_limited_activation_binding({}, reference, gate, envelope) is None
    assert create_production_limited_activation_binding(context, {}, gate, envelope) is None
    assert create_production_limited_activation_binding(context, reference, {}, envelope) is None
    assert create_production_limited_activation_binding(context, reference, gate, {}) is None


def test_owner_and_app_ast_audits_no_runtime_response_delivery_persistence_or_clock():
    source = (ROOT / "brain" / "production_limited_activation_binding.py").read_text("utf-8")
    tree = ast.parse(source)
    imports = tuple(node.module or "" for node in tree.body if isinstance(node, ast.ImportFrom))
    forbidden = ("cost_response_delivery", "cost_response_runtime_bridge", "integration_admission",
                 "cost_execution", "cost_result_presenter")
    assert not any(any(term in module for term in forbidden) for module in imports)
    assert "datetime.now" not in source and "session_state" not in source
    assert "business_memory" not in source and "store_profile" not in source
    app_source = (ROOT / "app.py").read_text("utf-8")
    app_tree = ast.parse(app_source)
    function = next(node for node in app_tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "_show_chat_companion")
    calls = [(node.lineno, node.func.id if isinstance(node.func, ast.Name)
              else getattr(node.func, "attr", "")) for node in ast.walk(function)
             if isinstance(node, ast.Call)]
    context_line = next(line for line, name in calls if name == "resolve_production_turn_context")
    reference_line = next(line for line, name in calls if name == "resolve_production_turn_reference_time")
    gate_line = next(line for line, name in calls if name == "resolve_production_feature_gate_evaluation")
    envelope_line = next(line for line, name in calls if name == "resolve_production_turn_bound_skill_evidence_envelope")
    owner_lines = [line for line, name in calls if name == "resolve_production_limited_activation_binding"]
    assert len(owner_lines) == 1
    assert context_line < reference_line < gate_line < envelope_line < owner_lines[0]
    assert not any(isinstance(node, (ast.If, ast.While)) and
                   "current_production_limited_activation_binding" in ast.unparse(node.test)
                   for node in ast.walk(function))
    assert app_source.count('st.session_state["current_production_limited_activation_binding"] = None') == 3
    assert app_source.count('st.session_state.setdefault("current_production_limited_activation_binding", None)') == 1
