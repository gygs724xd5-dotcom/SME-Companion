"""V5.15.24.1 immutable production turn-context foundation."""
import ast
import dataclasses
from pathlib import Path

import pytest

from brain.production_turn_context import (
    PRODUCTION_TURN_CONTEXT_VERSION,
    ProductionTurnContext,
    compute_turn_digest,
    compute_user_message_digest,
    create_production_turn_context,
    resolve_production_turn_context,
    verify_production_turn_context,
)


ROOT = Path(__file__).parents[1]
RAW_MESSAGE = "  ต้นทุน 100 บาท\nขาย 12 ชิ้น  "


def context(conversation_id="conversation-1", ordinal=1, message=RAW_MESSAGE):
    return create_production_turn_context(conversation_id, ordinal, message)


def test_deterministic_exact_raw_message_binding():
    one = context()
    two = context()
    assert one == two
    assert one.context_version == PRODUCTION_TURN_CONTEXT_VERSION == "5.15.24.1"
    assert one.user_message == RAW_MESSAGE
    assert one.user_message_digest == compute_user_message_digest(RAW_MESSAGE)
    assert one.turn_digest == compute_turn_digest(
        one.conversation_id, one.turn_id, one.turn_ordinal, one.user_message_digest)
    assert len(one.user_message_digest) == len(one.turn_digest) == 64
    assert one.user_message_digest.islower() and one.turn_digest.islower()
    assert context(message=RAW_MESSAGE.strip()).user_message_digest != one.user_message_digest
    assert context(message=RAW_MESSAGE.replace("\n", " ")).user_message_digest != one.user_message_digest


def test_empty_and_non_string_messages_follow_production_acceptance_contract():
    for value in ("", None, 1, b"message"):
        assert compute_user_message_digest(value) == ""
        with pytest.raises(ValueError):
            create_production_turn_context("conversation-1", 1, value)


def test_turn_and_conversation_identity_separation():
    first = context()
    assert context() == first
    assert context(ordinal=2).turn_id != first.turn_id
    assert context(ordinal=2).turn_digest != first.turn_digest
    assert context(conversation_id="conversation-2").turn_digest != first.turn_digest


@pytest.mark.parametrize("field,value", (
    ("context_version", ""),
    ("context_version", "5.15.24"),
    ("conversation_id", ""),
    ("conversation_id", "conversation-2"),
    ("turn_id", ""),
    ("turn_id", "turn-2"),
    ("turn_ordinal", 2),
    ("user_message", RAW_MESSAGE + "x"),
    ("user_message_digest", "0" * 64),
    ("user_message_digest", "A" * 64),
    ("user_message_digest", "0" * 63),
    ("user_message_digest", "0" * 65),
    ("turn_digest", "0" * 64),
    ("turn_digest", "A" * 64),
    ("turn_digest", "g" * 64),
    ("turn_digest", "0" * 63),
    ("turn_digest", "0" * 65),
    ("routing_authority", True),
    ("planning_authority", True),
    ("response_selection_authority", True),
    ("response_guard_authority", True),
    ("response_commit_authority", True),
    ("persistence_authority", True),
    ("tool_execution_authority", True),
    ("feature_gate_mutation_authority", True),
    ("controlled_runtime_activation_authority", True),
))
def test_strict_verifier_rejects_substitution_tampering_and_escalation(field, value):
    assert not verify_production_turn_context(dataclasses.replace(context(), **{field: value}))


def test_frozen_immutable_contract_and_exact_type_verification():
    value = context()
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.user_message = "changed"
    assert verify_production_turn_context(value)
    assert not verify_production_turn_context(dataclasses.asdict(value))
    assert not verify_production_turn_context(None)


def test_all_authority_flags_are_immutable_false():
    value = context()
    authority = {name: getattr(value, name) for name in value.__dataclass_fields__ if name.endswith("_authority")}
    assert authority
    assert set(authority.values()) == {False}


def test_exact_once_rerun_next_turn_reset_and_stale_context_semantics():
    first = resolve_production_turn_context(None, "conversation-1", 1, RAW_MESSAGE)
    rerun = resolve_production_turn_context(first, "conversation-1", 1, RAW_MESSAGE)
    assert rerun is first

    next_turn = resolve_production_turn_context(first, "conversation-1", 2, RAW_MESSAGE)
    assert next_turn != first and next_turn.turn_digest != first.turn_digest

    reset = resolve_production_turn_context(first, "conversation-2", 1, RAW_MESSAGE)
    assert reset.conversation_id == "conversation-2"
    assert reset != first and reset.turn_digest != first.turn_digest

    changed_message = resolve_production_turn_context(first, "conversation-1", 1, RAW_MESSAGE + "x")
    assert changed_message != first


def test_exception_identity_preservation_requires_no_context_mutation():
    failed_turn = resolve_production_turn_context(None, "conversation-1", 1, RAW_MESSAGE)
    session = {"current_production_turn_context": failed_turn, "chat_history": []}
    session["chat_history"].append({"role": "user", "content": RAW_MESSAGE})
    assert session["current_production_turn_context"] is failed_turn
    assert verify_production_turn_context(session["current_production_turn_context"])


def _function(tree, name):
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def test_source_has_one_canonical_creation_call_and_no_branch_duplication():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    chat = _function(tree, "_show_chat_companion")
    calls = [node for node in ast.walk(chat) if isinstance(node, ast.Call)]
    resolve_calls = [node for node in calls if isinstance(node.func, ast.Name)
        and node.func.id == "resolve_production_turn_context"]
    assert len(resolve_calls) == 1
    call = resolve_calls[0]
    history_appends = [node for node in calls if isinstance(node.func, ast.Attribute)
        and node.func.attr == "append" and "chat_history" in ast.unparse(node.func.value)]
    routing_calls = [node for node in calls if isinstance(node.func, ast.Name)
        and node.func.id in {"_record_reasoning", "select_planner_first_response", "guard_response"}]
    assert len(history_appends) == 2  # unchanged normal and reset branches
    assert routing_calls and call.lineno < min(node.lineno for node in routing_calls)
    assert call.lineno < min(node.lineno for node in history_appends)


def test_reset_owners_clear_transient_context_and_do_not_change_turn_count():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for name in ("_reset_chat_session", "_legacy_reset_conversation_state_for_demo_switch",
                 "_reset_conversation_state_for_demo_switch"):
        body = ast.unparse(_function(tree, name))
        assert "current_production_turn_context" in body
        assert "turn_count" not in body


def test_no_response_runtime_persistence_or_side_effect_imports():
    module_source = (ROOT / "brain" / "production_turn_context.py").read_text(encoding="utf-8")
    lowered = module_source.lower()
    assert "streamlit" not in lowered and "import app" not in lowered
    assert "session_state" not in lowered
    assert not any(name in lowered for name in (
        "business_skill_cost_response_runtime_bridge",
        "business_skill_cost_runtime_integration_admission_gateway",
        "business_skill_cost_runtime_integration_acceptance",
        "save_business", "save_store", "open(",
    ))

    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "business_skill_cost_response_runtime_bridge" not in app_source
    assert "business_skill_cost_runtime_integration_admission_gateway" not in app_source
    assert "business_skill_cost_runtime_integration_acceptance" not in app_source
    assert "current_production_turn_context" not in (ROOT / "brain" / "response_commit_boundary.py").read_text(encoding="utf-8")
