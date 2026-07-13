"""V5.15.24.2 canonical turn-bound production response candidates."""
import ast
import dataclasses
from pathlib import Path

import pytest

from brain.production_response_candidate import (
    CLARIFICATION,
    DIRECT_ANSWER,
    ERROR_FALLBACK_PROPOSAL,
    EXCEPTION_FALLBACK,
    EXCLUDED_RESPONSE_EVENT_CLASSES,
    GENERAL_RESPONSE,
    LEGACY_GUARDED,
    ORIGIN_KIND_REGISTRY,
    PLANNER_FIRST,
    PRODUCT_FEEDBACK,
    PRODUCTION_RESPONSE_CANDIDATE_VERSION,
    PROVISIONAL,
    RESET,
    RESPONSE_PROPOSAL,
    SIMPLE_FOLLOWUP,
    STRUCTURED_RUNTIME,
    TEMPORARY_INTERRUPT,
    TURN_BOUND_RESPONSE_CANDIDATE_SCOPE,
    WORKFLOW,
    ProductionResponseCandidate,
    compute_response_candidate_digest,
    compute_response_text_digest,
    create_production_response_candidate,
    verify_production_response_candidate,
)
from brain.production_turn_context import create_production_turn_context


ROOT = Path(__file__).parents[1]
EXACT_TEXT = "  ต้นทุน 100 บาท\n\nตอบบรรทัดนี้  "


def context(conversation="conversation-1", ordinal=1, message="คำถาม"):
    return create_production_turn_context(conversation, ordinal, message)


def candidate(origin=WORKFLOW, text=EXACT_TEXT, ctx=None):
    ctx = ctx or context()
    return create_production_response_candidate(ctx, origin, ORIGIN_KIND_REGISTRY[origin], text)


def _function(tree, name):
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def test_deterministic_exact_text_and_scope_binding():
    ctx = context()
    one = candidate(ctx=ctx)
    two = candidate(ctx=ctx)
    assert one == two
    assert one.candidate_version == PRODUCTION_RESPONSE_CANDIDATE_VERSION == "5.15.24.2"
    assert one.candidate_scope == TURN_BOUND_RESPONSE_CANDIDATE_SCOPE == "VERIFIED_USER_TURN_RESPONSE"
    assert one.response_text == EXACT_TEXT
    assert one.response_text_digest == compute_response_text_digest(EXACT_TEXT)
    assert one.candidate_digest == compute_response_candidate_digest(one)
    assert one.candidate_id.startswith("response-candidate-")
    assert len(one.response_text_digest) == len(one.candidate_digest) == 64
    assert candidate(text=EXACT_TEXT.strip()).response_text_digest != one.response_text_digest
    assert candidate(text=EXACT_TEXT.replace("\n", " ")).response_text_digest != one.response_text_digest


def test_same_and_different_turn_origin_and_text_behavior():
    base = candidate()
    assert candidate() == base
    assert candidate(ctx=context(ordinal=2)).candidate_digest != base.candidate_digest
    assert candidate(ctx=context(conversation="conversation-2")).candidate_digest != base.candidate_digest
    assert candidate(origin=DIRECT_ANSWER).candidate_digest != base.candidate_digest
    assert candidate(text=EXACT_TEXT + "x").candidate_digest != base.candidate_digest


def test_registry_is_exact_immutable_and_every_origin_creates():
    expected = {
        RESET, TEMPORARY_INTERRUPT, WORKFLOW, DIRECT_ANSWER, STRUCTURED_RUNTIME,
        PLANNER_FIRST, CLARIFICATION, GENERAL_RESPONSE, SIMPLE_FOLLOWUP,
        PRODUCT_FEEDBACK, LEGACY_GUARDED, EXCEPTION_FALLBACK,
    }
    assert set(ORIGIN_KIND_REGISTRY) == expected
    assert "UI_ACTION_RESPONSE" not in ORIGIN_KIND_REGISTRY
    assert ORIGIN_KIND_REGISTRY[EXCEPTION_FALLBACK] == ERROR_FALLBACK_PROPOSAL
    assert all(verify_production_response_candidate(candidate(origin), context()) for origin in expected)
    with pytest.raises(TypeError):
        ORIGIN_KIND_REGISTRY["NEW"] = RESPONSE_PROPOSAL


@pytest.mark.parametrize("field,value", (
    ("candidate_version", ""),
    ("candidate_version", "5.15.24.1"),
    ("candidate_scope", "UI_ACTION_RESPONSE"),
    ("conversation_id", "conversation-2"),
    ("turn_id", "turn-2"),
    ("turn_digest", "0" * 64),
    ("turn_digest", "A" * 64),
    ("candidate_id", ""),
    ("candidate_id", "response-candidate-" + "0" * 64),
    ("candidate_origin", ""),
    ("candidate_origin", "UI_ACTION_RESPONSE"),
    ("candidate_kind", ""),
    ("candidate_kind", ERROR_FALLBACK_PROPOSAL),
    ("candidate_ordinal", 2),
    ("response_text", EXACT_TEXT + "x"),
    ("response_text_digest", "0" * 64),
    ("response_text_digest", "A" * 64),
    ("response_text_digest", "g" * 64),
    ("response_text_digest", "0" * 63),
    ("response_text_digest", "0" * 65),
    ("status", "FINAL"),
    ("candidate_digest", "0" * 64),
    ("candidate_digest", "A" * 64),
    ("candidate_digest", "0" * 63),
))
def test_strict_verifier_rejects_tampering(field, value):
    assert not verify_production_response_candidate(dataclasses.replace(candidate(), **{field: value}), context())


@pytest.mark.parametrize("field", [
    name for name in ProductionResponseCandidate.__dataclass_fields__ if name.endswith("_authority")
])
def test_authority_escalation_rejected(field):
    value = candidate()
    assert getattr(value, field) is False
    assert not verify_production_response_candidate(dataclasses.replace(value, **{field: True}), context())


def test_frozen_exact_type_context_substitution_and_ordinal_collision_rejection():
    value = candidate()
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.response_text = "changed"
    assert not verify_production_response_candidate(dataclasses.asdict(value), context())
    assert not verify_production_response_candidate(value, context(ordinal=2))
    with pytest.raises(ValueError):
        create_production_response_candidate(context(), WORKFLOW, RESPONSE_PROPOSAL, "x", candidate_ordinal=2)
    with pytest.raises(ValueError):
        create_production_response_candidate(context(), WORKFLOW, ERROR_FALLBACK_PROPOSAL, "x")
    with pytest.raises(ValueError):
        create_production_response_candidate(context(), "UNKNOWN", RESPONSE_PROPOSAL, "x")


def test_exclusion_inventory_is_fixed_and_does_not_claim_broad_coverage():
    assert EXCLUDED_RESPONSE_EVENT_CLASSES == (
        "UI_ACTION_RESPONSE",
        "PRE_TURN_EXCEPTION_RESPONSE",
        "NON_CHAT_UI_RENDERING",
        "NON_TURN_AUTH_STORE_DEMO_UI_EVENT",
    )
    module = (ROOT / "brain" / "production_response_candidate.py").read_text(encoding="utf-8")
    assert "universal coverage" not in module.lower()
    assert "UNIVERSAL" not in TURN_BOUND_RESPONSE_CANDIDATE_SCOPE


def test_quick_actions_are_explicitly_excluded_before_context_creation():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    chat = _function(tree, "_show_chat_companion")
    quick_call = next(node for node in ast.walk(chat) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "_handle_quick_action_conversation")
    context_call = next(node for node in ast.walk(chat) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "resolve_production_turn_context")
    assert quick_call.lineno < context_call.lineno
    quick = ast.unparse(_function(tree, "_handle_quick_action_conversation"))
    assert quick.count("candidate_origin=None") == 3
    assert "resolve_production_turn_context" not in quick
    assert "_record_turn_bound_response_candidate" not in quick


def test_exception_classifies_only_verified_matching_current_turn():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    body = ast.unparse(_function(tree, "_handle_chat_pipeline_exception"))
    assert "verify_production_turn_context(context)" in body
    assert "context.conversation_id == st.session_state.get('conversation_id')" in body
    assert "context.user_message == last_chat_input" in body
    assert "RESPONSE_ORIGIN_EXCEPTION_FALLBACK" in body
    assert body.index("RESPONSE_ORIGIN_EXCEPTION_FALLBACK") < body.index("history.append({'role': 'assistant'")
    assert "resolve_production_turn_context" not in body


def test_candidate_before_every_typed_turn_commit_and_legacy_before_guard():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    chat = _function(tree, "_show_chat_companion")
    direct_commit_lines = sorted(node.lineno for node in ast.walk(chat) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "commit_assistant_turn")
    origins = sorted(node.lineno for node in ast.walk(chat) if isinstance(node, ast.Name)
        and node.id.startswith("RESPONSE_ORIGIN_"))
    assert len(direct_commit_lines) == 10
    for commit_line in direct_commit_lines:
        assert any(commit_line - 45 < origin_line < commit_line for origin_line in origins)

    helper = _function(tree, "_append_workflow_reply")
    helper_body = ast.unparse(helper)
    assert helper_body.index("_record_turn_bound_response_candidate") < helper_body.index("commit_assistant_turn")
    assert "if candidate_origin is not None" in helper_body

    legacy_candidate = source.index("legacy_candidate = _record_turn_bound_response_candidate")
    guard = source.index("guarded_response = guard_response", legacy_candidate)
    final_commit = source.index("commit_assistant_turn(", guard)
    assert legacy_candidate < guard < final_commit


def test_reset_store_and_new_chat_clear_only_transient_candidate():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    for name in ("_reset_chat_session", "_legacy_reset_conversation_state_for_demo_switch",
                 "_reset_conversation_state_for_demo_switch"):
        body = ast.unparse(_function(tree, name))
        assert "current_production_response_candidate" in body
        assert "turn_count" not in body


def test_candidate_module_has_no_ui_persistence_or_controlled_runtime_authority():
    source = (ROOT / "brain" / "production_response_candidate.py").read_text(encoding="utf-8").lower()
    assert "streamlit" not in source and "import app" not in source and "session_state" not in source
    assert "business_skill_cost_response_runtime_bridge" not in source
    assert "business_skill_cost_runtime_integration_admission_gateway" not in source
    assert "save_business" not in source and "save_store" not in source and "open(" not in source
    commit = (ROOT / "brain" / "response_commit_boundary.py").read_text(encoding="utf-8")
    assert "ProductionResponseCandidate" not in commit
    assert "current_production_response_candidate" not in commit
