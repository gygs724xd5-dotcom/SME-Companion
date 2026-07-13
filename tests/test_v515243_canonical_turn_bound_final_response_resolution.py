"""V5.15.24.3 canonical turn-bound final response resolution."""
import ast
import dataclasses
from pathlib import Path

import pytest

from brain.production_final_response_resolution import (
    FINAL_TEXT_RESOLVED,
    LEGACY_RESPONSE_GUARD,
    ORIGIN_RESOLUTION_POLICY_REGISTRY,
    PASS_THROUGH,
    PRODUCTION_FINAL_RESPONSE_RESOLUTION_VERSION,
    TURN_BOUND_EXCEPTION_FALLBACK,
    TURN_BOUND_FINAL_RESPONSE_RESOLUTION_SCOPE,
    ProductionFinalResponseResolution,
    compute_final_resolution_digest,
    compute_resolved_text_digest,
    create_production_final_response_resolution,
    get_resolution_policy_for_origin,
    verify_production_final_response_resolution,
)
from brain.production_response_candidate import (
    EXCEPTION_FALLBACK, LEGACY_GUARDED, ORIGIN_KIND_REGISTRY, STRUCTURED_RUNTIME,
    create_production_response_candidate,
)
from brain.production_turn_context import create_production_turn_context


ROOT = Path(__file__).parents[1]
PASS_ORIGINS = set(ORIGIN_KIND_REGISTRY) - {LEGACY_GUARDED, EXCEPTION_FALLBACK}
EXACT = "  ต้นทุน 100 บาท\n\nบรรทัดสุดท้าย  "


def context(conversation="conversation-1", ordinal=1, message="คำถาม"):
    return create_production_turn_context(conversation, ordinal, message)


def candidate(origin, text=EXACT, ctx=None):
    ctx = ctx or context()
    return create_production_response_candidate(ctx, origin, ORIGIN_KIND_REGISTRY[origin], text)


def resolution(origin, text=EXACT, resolved=None, ctx=None):
    ctx = ctx or context()
    value = candidate(origin, text, ctx)
    kwargs = ({"resolved_text": resolved, "existing_guard_applied": True}
              if origin == LEGACY_GUARDED else {})
    return create_production_final_response_resolution(ctx, value, **kwargs), value, ctx


def _function(tree, name):
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def test_registry_is_exact_immutable_and_policy_is_never_caller_selected():
    assert set(ORIGIN_RESOLUTION_POLICY_REGISTRY) == set(ORIGIN_KIND_REGISTRY)
    assert all(get_resolution_policy_for_origin(origin) is PASS_THROUGH for origin in PASS_ORIGINS)
    assert get_resolution_policy_for_origin(LEGACY_GUARDED) is LEGACY_RESPONSE_GUARD
    assert get_resolution_policy_for_origin(EXCEPTION_FALLBACK) is TURN_BOUND_EXCEPTION_FALLBACK
    assert get_resolution_policy_for_origin("UNKNOWN") is None
    with pytest.raises(TypeError):
        ORIGIN_RESOLUTION_POLICY_REGISTRY["NEW"] = PASS_THROUGH
    assert "resolution_policy" not in create_production_final_response_resolution.__annotations__


@pytest.mark.parametrize("origin", sorted(PASS_ORIGINS))
def test_pass_through_every_applicable_origin_exact_text(origin):
    value, proposal, ctx = resolution(origin)
    assert verify_production_final_response_resolution(value, proposal, ctx)
    assert value.resolved_text == proposal.response_text == EXACT
    assert value.text_changed is value.guard_applied is value.fallback_applied is False
    assert value.resolution_policy is PASS_THROUGH
    with pytest.raises(ValueError):
        create_production_final_response_resolution(ctx, proposal, resolved_text=EXACT)


def test_deterministic_exact_thai_whitespace_newline_digest_binding():
    one, proposal, ctx = resolution(next(iter(PASS_ORIGINS)))
    two = create_production_final_response_resolution(ctx, proposal)
    assert one == two
    assert one.resolution_version == PRODUCTION_FINAL_RESPONSE_RESOLUTION_VERSION == "5.15.24.3"
    assert one.resolution_scope == TURN_BOUND_FINAL_RESPONSE_RESOLUTION_SCOPE == "VERIFIED_USER_TURN_RESPONSE"
    assert one.resolved_text_digest == compute_resolved_text_digest(EXACT)
    assert one.resolution_digest == compute_final_resolution_digest(one)
    assert len(one.resolved_text_digest) == len(one.resolution_digest) == 64
    other, _, _ = resolution(next(iter(PASS_ORIGINS)), EXACT.strip())
    assert other.resolution_digest != one.resolution_digest


@pytest.mark.parametrize("guarded,changed", ((EXACT, False), ("ข้อความหลัง guard\n", True)))
def test_legacy_guard_unchanged_and_changed(guarded, changed):
    value, proposal, ctx = resolution(LEGACY_GUARDED, resolved=guarded)
    assert verify_production_final_response_resolution(value, proposal, ctx)
    assert value.resolved_text == guarded
    assert value.text_changed is changed
    assert value.guard_applied is True and value.fallback_applied is False
    with pytest.raises(ValueError):
        create_production_final_response_resolution(ctx, proposal, resolved_text=guarded)


def test_turn_bound_exception_fallback_and_structured_runtime_no_second_guard():
    fallback, proposal, ctx = resolution(EXCEPTION_FALLBACK)
    assert verify_production_final_response_resolution(fallback, proposal, ctx)
    assert fallback.resolved_text == proposal.response_text
    assert fallback.fallback_applied is True and fallback.guard_applied is False
    structured, proposal, ctx = resolution(STRUCTURED_RUNTIME)
    assert structured.resolution_policy is PASS_THROUGH and not structured.guard_applied
    with pytest.raises(ValueError):
        create_production_final_response_resolution(ctx, proposal, existing_guard_applied=True)


@pytest.mark.parametrize("field,value", (
    ("resolution_version", ""), ("resolution_version", "5.15.24.2"),
    ("resolution_scope", ""), ("resolution_scope", "UI_ACTION_RESPONSE"),
    ("conversation_id", "conversation-2"), ("turn_id", "turn-2"),
    ("turn_digest", "A" * 64), ("candidate_id", "x"),
    ("candidate_digest", "0" * 64), ("candidate_origin", LEGACY_GUARDED),
    ("resolution_policy", LEGACY_RESPONSE_GUARD), ("candidate_text_digest", "0" * 63),
    ("resolved_text", EXACT + "x"), ("resolved_text_digest", "A" * 64),
    ("text_changed", True), ("guard_applied", True), ("fallback_applied", True),
    ("resolution_reason", "tampered"), ("diagnostics", ("tampered",)),
    ("status", "COMMITTED"), ("final_text_resolved", False), ("provisional", True),
    ("committed", True), ("delivered", True), ("resolution_digest", "0" * 63),
    ("resolution_digest", "A" * 64), ("resolution_digest", "g" * 64),
))
def test_strict_verifier_rejects_substitution_and_tampering(field, value):
    item, proposal, ctx = resolution(next(iter(PASS_ORIGINS)))
    assert not verify_production_final_response_resolution(dataclasses.replace(item, **{field: value}), proposal, ctx)


@pytest.mark.parametrize("field", [
    name for name in ProductionFinalResponseResolution.__dataclass_fields__ if name.endswith("_authority")
])
def test_immutable_and_all_authority_escalation_rejected(field):
    item, proposal, ctx = resolution(next(iter(PASS_ORIGINS)))
    assert getattr(item, field) is False
    assert not verify_production_final_response_resolution(dataclasses.replace(item, **{field: True}), proposal, ctx)
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.resolved_text = "changed"


def test_cross_turn_cross_candidate_and_caller_constructed_resolution_rejected():
    item, proposal, ctx = resolution(next(iter(PASS_ORIGINS)))
    ctx2 = context(ordinal=2)
    proposal2 = candidate(proposal.candidate_origin, ctx=ctx2)
    assert not verify_production_final_response_resolution(item, proposal2, ctx2)
    assert not verify_production_final_response_resolution(dataclasses.asdict(item), proposal, ctx)


def test_source_coverage_ordering_exclusions_and_single_owner():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert source.count("def resolve_turn_bound_final_response(") == 1
    assert source.count("guarded_response = guard_response(") == 1
    assert source.count("resolve_turn_bound_final_response(") == 13  # owner + twelve candidate sites
    chat = _function(tree, "_show_chat_companion")
    body = ast.unparse(chat)
    assert body.index("_handle_quick_action_conversation") < body.index("resolve_production_turn_context")
    assert body.index("guarded_response = guard_response") < body.index("existing_guard_result=response['reply']")
    assert body.index("existing_guard_result=response['reply']") < body.rindex("commit_assistant_turn")
    assert body.count("guarded_response = guard_response") == 1
    exception = ast.unparse(_function(tree, "_handle_chat_pipeline_exception"))
    assert exception.index("RESPONSE_ORIGIN_EXCEPTION_FALLBACK") < exception.index("resolve_turn_bound_final_response")
    assert exception.index("resolve_turn_bound_final_response") < exception.index("history.append({'role': 'assistant'")
    helper = ast.unparse(_function(tree, "_append_workflow_reply"))
    assert helper.index("_record_turn_bound_response_candidate") < helper.index("resolve_turn_bound_final_response")
    assert helper.index("resolve_turn_bound_final_response") < helper.index("commit_assistant_turn")


def test_transient_clearing_no_persistence_or_controlled_runtime_dependency():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(app_source)
    for name in ("_reset_chat_session", "_legacy_reset_conversation_state_for_demo_switch",
                 "_reset_conversation_state_for_demo_switch"):
        assert "current_production_final_response_resolution" in ast.unparse(_function(tree, name))
    chat = ast.unparse(_function(tree, "_show_chat_companion"))
    accepted = chat.index("current_production_response_candidate")
    assert "current_production_final_response_resolution" in chat[accepted:accepted + 250]
    module = (ROOT / "brain" / "production_final_response_resolution.py").read_text(encoding="utf-8").lower()
    assert "streamlit" not in module and "import app" not in module and "session_state" not in module
    assert "business_skill_cost_response_runtime_bridge" not in module
    assert "business_skill_cost_runtime_integration_admission_gateway" not in module
    assert "save_business" not in module and "save_store" not in module and "open(" not in module
    wrapper = ast.unparse(_function(tree, "resolve_turn_bound_final_response"))
    assert "commit_assistant_turn" not in wrapper and "chat_history" not in wrapper
    assert "resolve_v5941_runtime_response" not in wrapper and "guard_response" not in wrapper
