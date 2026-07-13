"""V5.15.24.4 single commit for verified turn-bound exception responses."""
import ast
import dataclasses
from pathlib import Path

import pytest

from brain.production_final_response_resolution import create_production_final_response_resolution
from brain.production_response_candidate import (
    EXCEPTION_FALLBACK,
    ORIGIN_KIND_REGISTRY,
    create_production_response_candidate,
)
from brain.production_turn_commit_receipt import (
    COMMIT_APPLIED,
    PRODUCTION_TURN_COMMIT_RECEIPT_VERSION,
    TURN_BOUND_EXCEPTION_COMMIT,
    TURN_BOUND_SINGLE_COMMIT_SCOPE,
    ProductionTurnCommitReceipt,
    create_production_turn_commit_receipt,
    verify_production_turn_commit_receipt,
)
from brain.production_turn_context import create_production_turn_context
from brain.conversation_memory_engine import remember_turn
from brain.response_commit_boundary import commit_response_boundary


ROOT = Path(__file__).parents[1]
TEXT = "ระบบขัดข้องชั่วคราว กรุณาลองอีกครั้งครับ"


def artifacts(conversation="conversation-1", ordinal=1, text=TEXT):
    context = create_production_turn_context(conversation, ordinal, "ช่วยดูยอดขาย")
    candidate = create_production_response_candidate(
        context, EXCEPTION_FALLBACK, ORIGIN_KIND_REGISTRY[EXCEPTION_FALLBACK], text
    )
    resolution = create_production_final_response_resolution(context, candidate)
    receipt = create_production_turn_commit_receipt(context, candidate, resolution, text)
    return context, candidate, resolution, receipt


def function(tree, name):
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def test_exception_receipt_is_immutable_exact_and_turn_bound():
    context, candidate, resolution, receipt = artifacts()
    assert verify_production_turn_commit_receipt(receipt, context, candidate, resolution, TEXT)
    assert receipt.receipt_version == PRODUCTION_TURN_COMMIT_RECEIPT_VERSION == "5.15.24.4"
    assert receipt.receipt_scope == TURN_BOUND_SINGLE_COMMIT_SCOPE == "VERIFIED_USER_TURN_RESPONSE"
    assert receipt.commit_kind == TURN_BOUND_EXCEPTION_COMMIT
    assert receipt.commit_status == COMMIT_APPLIED
    assert receipt.commit_applied is receipt.exactly_once is True
    assert len(receipt.receipt_digest) == 64
    with pytest.raises(dataclasses.FrozenInstanceError):
        receipt.commit_applied = False


@pytest.mark.parametrize("field,value", (
    ("receipt_version", ""), ("receipt_version", "5.15.24.3"),
    ("receipt_scope", "UI_ACTION_RESPONSE"), ("conversation_id", "conversation-2"),
    ("turn_id", "turn-2"), ("turn_digest", "A" * 64),
    ("candidate_digest", "0" * 63), ("resolution_digest", "g" * 64),
    ("commit_kind", "NORMAL_TURN_BOUND_COMMIT"), ("committed_response_digest", "A" * 64),
    ("commit_status", "NOT_APPLIED"), ("commit_applied", False), ("exactly_once", False),
    ("routing_authority", True), ("response_selection_authority", True),
    ("response_guard_authority", True), ("persistence_authority", True),
    ("controlled_runtime_activation_authority", True), ("receipt_digest", "0" * 64),
))
def test_strict_receipt_rejects_tampering_authority_and_malformed_digests(field, value):
    context, candidate, resolution, receipt = artifacts()
    changed = dataclasses.replace(receipt, **{field: value})
    assert not verify_production_turn_commit_receipt(changed, context, candidate, resolution, TEXT)


def test_receipt_rejects_cross_turn_cross_candidate_and_committed_text_substitution():
    context, candidate, resolution, receipt = artifacts()
    context2, candidate2, resolution2, _ = artifacts(ordinal=2)
    assert not verify_production_turn_commit_receipt(receipt, context2, candidate2, resolution2, TEXT)
    assert not verify_production_turn_commit_receipt(receipt, context, candidate, resolution, TEXT + "!")
    assert not verify_production_turn_commit_receipt(dataclasses.asdict(receipt), context, candidate, resolution, TEXT)


def test_canonical_boundary_preserves_staged_turn_and_synchronizes_exception_reply_once():
    user = "ช่วยดูยอดขาย"
    staged = remember_turn({}, user)
    session = {
        "conversation_id": "conversation-1",
        "last_user_message": user,
        "chat_history": [{"role": "user", "content": user}],
        "conversation_state": {"conversation_memory": staged},
    }
    application = {"conversation": {"conversation_memory": staged}}
    result = commit_response_boundary(
        session_state=session,
        application_state=application,
        final_reply=TEXT,
        response_metadata={
            "user_message": user,
            "response_source": "empty_response_fallback",
            "commit_kind": TURN_BOUND_EXCEPTION_COMMIT,
        },
        assistant_message={"role": "assistant", "show_business_insights": False},
    )
    assert [item["role"] for item in session["chat_history"]] == ["user", "assistant"]
    assert session["chat_history"][0]["content"] == user
    assert session["chat_history"][1]["content"] == TEXT
    memory = result["conversation_memory"]
    assert memory["turn_count"] == staged["turn_count"] == 1
    assert memory["last_assistant_reply"] == TEXT
    assert memory["recent_assistant_replies"] == [TEXT]
    assert "last_intent" not in memory and "last_workflow" not in memory
    assert "focused_business_topic" not in memory
    assert application["conversation"]["conversation_memory"] == memory
    assert application["conversation_memory"] == memory
    assert application["conversation"]["chat_history"] == session["chat_history"]


def test_exception_branch_has_canonical_owner_and_explicit_pre_turn_fallback():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    body = ast.unparse(function(tree, "_handle_chat_pipeline_exception"))
    assert body.count("commit_assistant_turn(") == 1
    assert body.index("verify_production_turn_context") < body.index("RESPONSE_ORIGIN_EXCEPTION_FALLBACK")
    assert body.index("RESPONSE_ORIGIN_EXCEPTION_FALLBACK") < body.index("resolve_turn_bound_final_response")
    assert body.index("resolve_turn_bound_final_response") < body.index("commit_assistant_turn")
    assert "if turn_bound_exception" in body
    assert "elif not history or history[-1].get('role') != 'assistant'" in body
    assert body.count("history.append({'role': 'assistant'") == 1
    assert "resolve_production_turn_context" not in body


def test_neutral_exception_metadata_and_no_business_or_controlled_runtime_side_effects():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    body = ast.unparse(function(tree, "_handle_chat_pipeline_exception"))
    assert "intent=" not in body and "workflow=" not in body and "business_topic=" not in body
    assert "TURN_BOUND_EXCEPTION_COMMIT" in body
    assert "VERIFIED_TURN_BOUND_EXCEPTION_FALLBACK" in body
    assert "_update_conversation_state_after_assistant" not in body
    assert "_remember_generated_response" not in body
    assert "_remember_completed_workflow_if_done" not in body
    assert "save_business" not in body and "save_store" not in body
    assert "resolve_v5941_runtime_response" not in body


def test_receipt_is_cleared_for_new_turn_reset_new_chat_and_demo_isolation():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    for name in ("_reset_chat_session", "_legacy_reset_conversation_state_for_demo_switch",
                 "_reset_conversation_state_for_demo_switch"):
        assert "current_production_turn_commit_receipt" in ast.unparse(function(tree, name))
    chat = ast.unparse(function(tree, "_show_chat_companion"))
    assert "st.session_state['current_production_turn_commit_receipt'] = None" in chat
    quick = ast.unparse(function(tree, "_handle_quick_action_conversation"))
    assert "current_production_turn_commit_receipt" not in quick
    assert "commit_assistant_turn" not in quick


def test_receipt_module_has_no_ui_durable_persistence_or_controlled_runtime_authority():
    module = (ROOT / "brain" / "production_turn_commit_receipt.py").read_text(encoding="utf-8").lower()
    assert "streamlit" not in module and "import app" not in module and "session_state" not in module
    assert "save_business" not in module and "save_store" not in module and "open(" not in module
    assert "business_skill_cost_response_runtime_bridge" not in module
    assert "business_skill_cost_runtime_integration_admission_gateway" not in module
