import ast
import dataclasses
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import *


FIXED = datetime(2026, 7, 14, 3, 4, 5, 987654, tzinfo=timezone.utc)


def context(conversation="conversation-1", ordinal=1, message="ต้นทุนเดิม 20 ตอนนี้ 24"):
    return create_production_turn_context(conversation, ordinal, message)


def artifact(ctx=None):
    ctx = ctx or context()
    return create_production_turn_reference_time(ctx, FIXED)


def test_fixed_utc_creation_canonical_seconds_and_deterministic_digest():
    ctx = context()
    first = artifact(ctx)
    second = artifact(ctx)
    assert first == second
    assert first.accepted_at_utc == datetime(2026, 7, 14, 3, 4, 5, tzinfo=timezone.utc)
    assert first.accepted_at_iso == "2026-07-14T03:04:05+00:00"
    assert first.timezone_identity == "UTC"
    assert first.precision_identity == "SECONDS_0_FRACTIONAL_DIGITS"
    assert verify_production_turn_reference_time(ctx, first)
    assert len(first.reference_time_digest) == 64 and first.reference_time_digest.islower()


def test_naive_and_non_utc_datetime_are_rejected():
    with pytest.raises(ValueError):
        create_production_turn_reference_time(context(), datetime(2026, 7, 14, 3, 4, 5))
    with pytest.raises(ValueError):
        create_production_turn_reference_time(
            context(), datetime(2026, 7, 14, 10, 4, 5, tzinfo=timezone(timedelta(hours=7)))
        )
    with pytest.raises(ValueError):
        create_production_turn_reference_time(
            context(), datetime(2026, 7, 14, 3, 4, 5, tzinfo=timezone(timedelta(0), "GMT"))
        )


@pytest.mark.parametrize("change", (
    {"reference_time_version": ""},
    {"reference_time_scope": "OTHER"},
    {"source_identity": "OTHER"},
    {"accepted_at_iso": "2026-07-14T03:04:05Z"},
    {"timezone_identity": "GMT"},
    {"precision_identity": "MICROSECONDS"},
    {"captured_once": False},
    {"read_only": False},
    {"caller_override_permitted": True},
    {"routing_authority": True},
    {"reference_time_digest": "A" * 64},
    {"reference_time_digest": "a" * 63},
    {"reference_time_digest": "0" * 64},
))
def test_strict_verifier_rejects_contract_authority_and_digest_tampering(change):
    ctx = context()
    assert not verify_production_turn_reference_time(ctx, dataclasses.replace(artifact(ctx), **change))


def test_datetime_iso_mismatch_and_noncanonical_microseconds_rejected():
    ctx = context()
    value = artifact(ctx)
    assert not verify_production_turn_reference_time(
        ctx, dataclasses.replace(value, accepted_at_utc=FIXED)
    )
    assert not verify_production_turn_reference_time(
        ctx, dataclasses.replace(value, accepted_at_iso="2026-07-14T03:04:06+00:00")
    )


def test_cross_turn_conversation_and_same_message_next_turn_substitution_rejected():
    value = artifact()
    assert not verify_production_turn_reference_time(context(ordinal=2), value)
    assert not verify_production_turn_reference_time(context(conversation="conversation-2"), value)


def test_frozen_and_all_authority_flags_false():
    value = artifact()
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.accepted_at_iso = "changed"
    assert value.captured_once and value.read_only and not value.caller_override_permitted
    assert not any(getattr(value, field.name) for field in dataclasses.fields(value)
                   if field.name.endswith("_authority"))


def test_app_owner_captures_once_rerun_reuses_and_next_turn_recaptures(monkeypatch):
    calls = []

    class Clock:
        @classmethod
        def now(cls, tz):
            calls.append(tz)
            return FIXED + timedelta(seconds=len(calls) - 1)

    monkeypatch.setattr(app, "datetime", Clock)
    monkeypatch.setattr(app.st, "session_state", {})
    one = app.resolve_production_turn_reference_time(context())
    rerun = app.resolve_production_turn_reference_time(context())
    two = app.resolve_production_turn_reference_time(context(ordinal=2))
    assert one is rerun and len(calls) == 2
    assert two.turn_digest != one.turn_digest and two.accepted_at_iso != one.accepted_at_iso


def test_reset_clears_transient_artifact(monkeypatch):
    monkeypatch.setattr(app.st, "session_state", {
        "current_production_turn_reference_time": artifact(),
        "conversation_state": {},
    })
    monkeypatch.setattr(app, "_sync_session_to_application_state", lambda: None)
    app._reset_chat_session()
    assert app.st.session_state["current_production_turn_reference_time"] is None


def test_source_audit_single_clock_owner_ordering_and_no_forbidden_runtime():
    module_source = Path("brain/production_turn_reference_time.py").read_text(encoding="utf-8")
    app_source = Path("app.py").read_text(encoding="utf-8")
    assert "datetime.now(" not in module_source
    tree = ast.parse(app_source)
    owner = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "resolve_production_turn_reference_time")
    assert sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
               and node.func.attr == "now" for node in ast.walk(owner)) == 1
    chat = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == "_show_chat_companion")
    assert "accepted_at" not in {arg.arg for arg in chat.args.args}
    chat_source = ast.get_source_segment(app_source, chat)
    assert chat_source.index("resolve_production_turn_context(") < chat_source.index(
        "resolve_production_turn_reference_time("
    ) < chat_source.index("resolve_production_feature_gate_evaluation(")
    forbidden = ("limited_activation_gateway", "bridge_prepared_cost_response(",
                 "qualify_cost_response_delivery(", "admission_gateway")
    assert all(token not in module_source for token in forbidden)
    assert "current_production_turn_reference_time" not in Path(
        "brain/business_memory_engine.py").read_text(encoding="utf-8")


def test_demo_reset_owners_clear_and_quick_action_precedes_accepted_turn():
    source = Path("app.py").read_text(encoding="utf-8")
    assert source.count('st.session_state["current_production_turn_reference_time"] = None') == 3
    quick = source.index('pending_quick_action = st.session_state.pop("pending_quick_action", None)')
    capture = source.index('resolve_production_turn_reference_time(', quick)
    assert quick < capture
