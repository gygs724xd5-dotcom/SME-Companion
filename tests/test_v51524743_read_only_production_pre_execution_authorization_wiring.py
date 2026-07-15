import ast
import copy
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

import brain.production_pre_execution_authorization_runtime as owner
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_limited_activation_binding import create_production_limited_activation_binding
from brain.production_pre_execution_authorization import (
    DENIED_DEFAULT_PRODUCTION_GATE,
    EVIDENCE_NOT_READY,
    NOT_APPLICABLE,
)
from brain.production_turn_bound_skill_evidence import create_production_turn_bound_skill_evidence_envelope
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time


ROOT = Path(__file__).resolve().parents[1]
MESSAGES = (
    ("my cost increased from 20.00 to 24.000", DENIED_DEFAULT_PRODUCTION_GATE),
    ("ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น", DENIED_DEFAULT_PRODUCTION_GATE),
    ("hello unrelated question", NOT_APPLICABLE),
    ("cost increased previous cost 30", EVIDENCE_NOT_READY),
    ("unit cost cost increased", EVIDENCE_NOT_READY),
)


def foundations(message=MESSAGES[0][0], ordinal=1, conversation="runtime-test"):
    context = create_production_turn_context(conversation, ordinal, message)
    reference = create_production_turn_reference_time(
        context, datetime(2026, 7, 15, 5, 6, 7, tzinfo=timezone.utc)
    )
    gate = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
        context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    envelope = create_production_turn_bound_skill_evidence_envelope(context, gate)
    binding = create_production_limited_activation_binding(context, reference, gate, envelope)
    return context, reference, gate, envelope, binding


def resolve(values, current=None):
    return owner.resolve_production_pre_execution_authorization_runtime_evidence(
        *values, current_evidence=current
    )


@pytest.mark.parametrize("message,status", MESSAGES)
def test_current_policy_status_contract(message, status):
    evidence = resolve(foundations(message))
    assert owner.verify_production_pre_execution_authorization_runtime_evidence(evidence)
    assert evidence.decision_status == status
    assert evidence.execute_allowed is False
    assert evidence.executable_request is None
    assert evidence.controlled_response_candidate is None


def test_wrapper_is_frozen_deterministic_and_deepcopy_equal():
    values = foundations()
    first = owner.create_production_pre_execution_authorization_runtime_evidence(*values)
    second = owner.create_production_pre_execution_authorization_runtime_evidence(*values)
    assert first == second == copy.deepcopy(first)
    assert first.runtime_evidence_digest == second.runtime_evidence_digest
    with pytest.raises(Exception):
        first.execute_allowed = True


def test_same_exact_foundations_reuse_identity():
    values = foundations()
    first = resolve(values)
    assert resolve(values, first) is first


@pytest.mark.parametrize(
    "next_values",
    (
        foundations(ordinal=2),
        foundations(message=MESSAGES[0][0], ordinal=2),
        foundations(conversation="another-conversation"),
    ),
)
def test_next_turn_or_conversation_replaces(next_values):
    first = resolve(foundations())
    second = resolve(next_values, first)
    assert second is not first
    assert owner.verify_production_pre_execution_authorization_runtime_evidence(second)


@pytest.mark.parametrize("index", range(5))
def test_each_foundation_identity_mismatch_does_not_reuse(index):
    original = foundations()
    current = resolve(original)
    changed = list(original)
    changed[index] = foundations(ordinal=2)[index]
    assert resolve(tuple(changed), current) is not current


@pytest.mark.parametrize("index", range(5))
def test_missing_or_invalid_foundation_returns_none(index):
    values = list(foundations())
    values[index] = None
    assert resolve(tuple(values)) is None


@pytest.mark.parametrize(
    "field,value",
    (
        ("runtime_evidence_digest", ""),
        ("runtime_evidence_digest", "A" * 64),
        ("runtime_evidence_digest", "a" * 63),
        ("runtime_evidence_digest", "a" * 65),
        ("execute_allowed", True),
        ("runtime_permitted", True),
        ("decision_status", "AUTHORIZED"),
        ("request_digest", "0" * 64),
    ),
)
def test_strict_tamper_rejection(field, value):
    evidence = resolve(foundations())
    assert not owner.verify_production_pre_execution_authorization_runtime_evidence(
        replace(evidence, **{field: value})
    )


def test_substituted_cross_turn_request_and_decision_rejected():
    first = resolve(foundations())
    second = resolve(foundations(ordinal=2))
    assert not owner.verify_production_pre_execution_authorization_runtime_evidence(
        replace(first, authorization_request=second.authorization_request)
    )
    assert not owner.verify_production_pre_execution_authorization_runtime_evidence(
        replace(first, observed_decision=second.observed_decision)
    )


def test_all_runtime_authority_flags_are_false():
    evidence = resolve(foundations())
    assert all(
        getattr(evidence.authority_boundary, field.name) is False
        for field in fields(evidence.authority_boundary)
    )
    assert all(
        getattr(evidence, field.name) is False
        for field in fields(evidence)
        if field.name.endswith("_permitted")
    )


def test_internal_exception_is_contained(monkeypatch):
    monkeypatch.setattr(owner, "create_production_pre_execution_authorization_runtime_evidence",
                        lambda *_args: (_ for _ in ()).throw(RuntimeError("contained")))
    assert resolve(foundations()) is None


def test_module_has_no_downstream_imports_or_calls():
    source = (ROOT / "brain" / "production_pre_execution_authorization_runtime.py").read_text("utf-8")
    forbidden = (
        "calculator", "presenter", "adapter", "delivery", "runtime_bridge",
        "admission", "production_response_candidate", "final_response_resolution",
        "turn_commit_receipt", "business_memory", "conversation_memory", "store_profile",
    )
    tree = ast.parse(source)
    imports = tuple(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    )
    assert not any(any(term in name for term in forbidden) for name in imports)


def test_app_call_order_and_passive_unconditional_assignment():
    source = (ROOT / "app.py").read_text("utf-8")
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    named = [node for node in calls if getattr(node.func, "id", "") ==
             "resolve_production_pre_execution_authorization_runtime_evidence"]
    assert len(named) == 1
    runtime_line = named[0].lineno
    activation_line = next(node.lineno for node in calls if getattr(node.func, "id", "") ==
                           "resolve_production_limited_activation_binding")
    response_lines = [node.lineno for node in calls if getattr(node.func, "id", "") in {
        "_record_turn_bound_response_candidate", "resolve_turn_bound_final_response",
    }]
    assert activation_line < runtime_line < min(line for line in response_lines if line > runtime_line)
    assert isinstance(named[0].parent if hasattr(named[0], "parent") else named[0], ast.Call)
    assert source.count('st.session_state["current_production_pre_execution_authorization"] = None') == 4
    assert source.count('st.session_state.setdefault("current_production_pre_execution_authorization", None)') == 1


def test_quick_action_precedes_turn_context_and_runtime_call():
    source = (ROOT / "app.py").read_text("utf-8")
    assert source.index("if pending_quick_action:") < source.index(
        'st.session_state["current_production_turn_context"] = resolve_production_turn_context('
    ) < source.index("resolve_production_pre_execution_authorization_runtime_evidence(",
                     source.index("def _show_chat_companion("))


def test_no_persistence_or_diagnostics_exposure_and_existing_commit_counts_unchanged():
    source = (ROOT / "app.py").read_text("utf-8")
    key = "current_production_pre_execution_authorization"
    assert source.count(key) == 7
    assert source.count("commit_assistant_turn(") == 13
    assert source.count('st.session_state["chat_history"].append(') == 2
