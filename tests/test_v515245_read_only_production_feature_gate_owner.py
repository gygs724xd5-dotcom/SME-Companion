"""V5.15.24.5 read-only production feature-gate owner and wiring."""
import ast
import dataclasses
from pathlib import Path

import pytest

from brain.production_feature_gate_owner import (
    GATE_CONFIGURED_DISABLED,
    GATE_CONFIGURED_ENABLED,
    GATE_MISSING_DEFAULT_DENY,
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY,
    PRODUCTION_FEATURE_GATE_OWNER_VERSION,
    PURE_TEST_TRUSTED_SOURCE_IDENTITY,
    SUPPORTED_PRODUCTION_FEATURE_GATES,
    ProductionFeatureGateConfiguration,
    ProductionFeatureGateEvaluation,
    create_production_feature_gate_configuration,
    evaluate_production_feature_gate,
    exact_production_feature_gate_lookup,
    resolve_production_feature_gate_evaluation,
    verify_production_feature_gate_configuration,
    verify_production_feature_gate_evaluation,
)
from brain.production_turn_context import create_production_turn_context


ROOT = Path(__file__).parents[1]
GATE = LIMITED_COST_RESPONSE_RUNTIME_BRIDGE


def context(conversation="conversation-1", ordinal=1, message="ต้นทุนเท่าไร"):
    return create_production_turn_context(conversation, ordinal, message)


def configuration(entries=()):
    return create_production_feature_gate_configuration(PURE_TEST_TRUSTED_SOURCE_IDENTITY, entries)


def evaluation(entries=(), turn=None):
    return evaluate_production_feature_gate(configuration(entries), turn or context(), GATE)


def test_registry_version_and_production_default_deny_source_are_exact():
    assert PRODUCTION_FEATURE_GATE_OWNER_VERSION == "5.15.24.5"
    assert SUPPORTED_PRODUCTION_FEATURE_GATES == ("LIMITED_COST_RESPONSE_RUNTIME_BRIDGE",)
    config = PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert config.trusted_source_identity == PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY
    assert config.gate_entries == ()
    value = evaluate_production_feature_gate(config, context(), GATE)
    assert not value.configured_state and not value.effective_state
    assert value.default_denied and value.evaluation_reason == GATE_MISSING_DEFAULT_DENY


@pytest.mark.parametrize("state,reason", ((True, GATE_CONFIGURED_ENABLED), (False, GATE_CONFIGURED_DISABLED)))
def test_exact_boolean_true_and_false_in_pure_trusted_configuration(state, reason):
    config = configuration(((GATE, state),))
    assert exact_production_feature_gate_lookup(config, GATE) is state
    value = evaluate_production_feature_gate(config, context(), GATE)
    assert value.configured_state is state and value.effective_state is state
    assert not value.default_denied and value.evaluation_reason == reason
    assert value.activation_permitted is False


@pytest.mark.parametrize("name", ("", "limited_cost_response_runtime_bridge",
    "Limited_COST_RESPONSE_RUNTIME_BRIDGE", "*", "GLOBAL", "ALL", " " ))
def test_blank_alias_case_global_and_wildcard_names_rejected(name):
    with pytest.raises(ValueError):
        configuration(((name, True),))
    with pytest.raises(ValueError):
        exact_production_feature_gate_lookup(configuration(), name)


@pytest.mark.parametrize("entries", (
    ((GATE, True), (GATE, False)),
    ((GATE, True), ("UNKNOWN_GATE", False)),
    (("UNKNOWN_GATE", True),),
))
def test_duplicate_unknown_and_extra_gates_rejected(entries):
    with pytest.raises(ValueError):
        configuration(entries)


@pytest.mark.parametrize("state", ("true", "1", "yes", 1, 0, None, [], {}))
def test_truthy_strings_integers_none_and_other_non_boole_rejected(state):
    with pytest.raises(ValueError):
        configuration(((GATE, state),))


def test_untrusted_blank_source_and_malformed_container_rejected():
    for source in ("", "caller", None):
        with pytest.raises(ValueError):
            create_production_feature_gate_configuration(source, ())
    for entries in ({GATE: True}, GATE, None):
        with pytest.raises(ValueError):
            create_production_feature_gate_configuration(PURE_TEST_TRUSTED_SOURCE_IDENTITY, entries)


def test_configuration_and_evaluation_digests_are_deterministic_and_source_bound():
    one, two = configuration(((GATE, True),)), configuration(((GATE, True),))
    assert one == two and one.source_digest == two.source_digest
    assert len(one.source_digest) == 64 and one.source_digest.islower()
    first, second = evaluate_production_feature_gate(one, context(), GATE), evaluate_production_feature_gate(two, context(), GATE)
    assert first == second and len(first.evaluation_digest) == 64 and first.evaluation_digest.islower()
    assert configuration().source_digest != one.source_digest


def test_exact_turn_binding_rerun_reuse_next_turn_and_cross_conversation_replacement():
    config = configuration(((GATE, True),))
    first_context = context()
    first = resolve_production_feature_gate_evaluation(None, config, first_context, GATE)
    assert resolve_production_feature_gate_evaluation(first, config, first_context, GATE) is first
    next_turn = resolve_production_feature_gate_evaluation(first, config, context(ordinal=2), GATE)
    other_conversation = resolve_production_feature_gate_evaluation(first, config, context("conversation-2"), GATE)
    assert next_turn.turn_digest != first.turn_digest
    assert other_conversation.conversation_id != first.conversation_id


@pytest.mark.parametrize("field,value", (
    ("owner_version", ""), ("owner_version", "5.15.24"),
    ("configuration_version", ""), ("conversation_id", "conversation-2"),
    ("turn_id", "turn-2"), ("turn_digest", "0" * 64),
    ("gate_name", "*"), ("configured_state", False), ("effective_state", False),
    ("default_denied", True), ("source_identity", PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY),
    ("source_digest", "0" * 64), ("evaluation_reason", GATE_CONFIGURED_DISABLED),
    ("read_only", False), ("mutation_permitted", True), ("activation_permitted", True),
    ("routing_authority", True), ("planning_authority", True),
    ("response_selection_authority", True), ("response_guard_authority", True),
    ("response_commit_authority", True), ("persistence_authority", True),
    ("tool_execution_authority", True), ("evaluation_digest", "A" * 64),
    ("evaluation_digest", "g" * 64), ("evaluation_digest", "0" * 63),
    ("evaluation_digest", "0" * 65),
))
def test_strict_evaluation_verifier_rejects_tampering_escalation_and_malformed_digest(field, value):
    config = configuration(((GATE, True),))
    turn = context()
    forged = dataclasses.replace(evaluate_production_feature_gate(config, turn, GATE), **{field: value})
    assert not verify_production_feature_gate_evaluation(forged, config, turn)


def test_configuration_verifier_rejects_version_entries_authority_and_digest_tampering():
    value = configuration(((GATE, True),))
    for field, changed in (("configuration_version", ""), ("trusted_source_identity", "caller"),
        ("gate_entries", ((GATE, "true"),)), ("mutation_authority", True),
        ("source_digest", "A" * 64), ("source_digest", "0" * 63)):
        assert not verify_production_feature_gate_configuration(dataclasses.replace(value, **{field: changed}))
    forged = ProductionFeatureGateConfiguration("5.15.24.5", PURE_TEST_TRUSTED_SOURCE_IDENTITY,
        ((GATE, True), (GATE, True)), False, "0" * 64)
    assert not verify_production_feature_gate_configuration(forged)


def test_cross_turn_source_substitution_and_caller_constructed_evidence_rejected():
    config = configuration(((GATE, True),))
    turn = context()
    value = evaluate_production_feature_gate(config, turn, GATE)
    assert not verify_production_feature_gate_evaluation(value, config, context(ordinal=2))
    assert not verify_production_feature_gate_evaluation(value, configuration(), turn)
    assert not verify_production_feature_gate_evaluation(dataclasses.asdict(value), config, turn)


def test_contracts_are_frozen_and_all_authority_flags_are_false():
    config, value = configuration(), evaluation()
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.gate_entries = ((GATE, True),)
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.effective_state = True
    flags = {name: getattr(value, name) for name in value.__dataclass_fields__
        if name.endswith("authority") or name.endswith("permitted")}
    assert flags and set(flags.values()) == {False}
    assert value.read_only is True


def _function(tree, name):
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def test_no_mutation_activation_bridge_persistence_ui_or_session_authority_in_owner():
    source = (ROOT / "brain" / "production_feature_gate_owner.py").read_text(encoding="utf-8")
    lowered = source.lower()
    for forbidden in ("enable_gate", "disable_gate", "toggle_gate", "set_gate", "update_gate",
        "streamlit", "session_state", "st.secrets", "getenv(", "os.environ", "query_params",
        "business_skill_cost_response_runtime_bridge", "business_skill_cost_runtime_integration_admission_gateway",
        "save_business", "save_store", "open("):
        assert forbidden not in lowered


def test_app_single_call_order_default_deny_no_branch_and_transient_lifecycle():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    chat = _function(tree, "_show_chat_companion")
    calls = [node for node in ast.walk(chat) if isinstance(node, ast.Call)]
    context_call = next(node for node in calls if isinstance(node.func, ast.Name)
        and node.func.id == "resolve_production_turn_context")
    gate_calls = [node for node in calls if isinstance(node.func, ast.Name)
        and node.func.id == "resolve_production_feature_gate_evaluation"]
    assert len(gate_calls) == 1 and context_call.lineno < gate_calls[0].lineno
    assert "production_feature_gate_release_owner.configuration" in ast.unparse(gate_calls[0])
    response_calls = [node for node in calls if isinstance(node.func, ast.Name)
        and node.func.id in {"_record_reasoning", "select_planner_first_response", "guard_response",
                             "_record_turn_bound_response_candidate", "commit_assistant_turn"}]
    assert response_calls and gate_calls[0].lineno < min(node.lineno for node in response_calls)
    assert not any(isinstance(node, ast.If) and "effective_state" in ast.unparse(node.test)
        for node in ast.walk(chat))
    assert source.count("resolve_production_feature_gate_evaluation(") == 1
    assert "business_skill_cost_response_runtime_bridge" not in source
    assert "business_skill_cost_runtime_integration_admission_gateway" not in source
    for name in ("_reset_chat_session", "_legacy_reset_conversation_state_for_demo_switch",
                 "_reset_conversation_state_for_demo_switch"):
        assert "current_production_feature_gate_evaluation" in ast.unparse(_function(tree, name))


def test_quick_action_pre_turn_path_has_no_gate_evaluation_and_no_ui_or_persistence_exposure():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    quick = ast.unparse(_function(tree, "_handle_quick_action_conversation"))
    assert "production_feature_gate" not in quick
    prefix = source[:source.index('st.session_state["current_production_turn_context"] = resolve_production_turn_context')]
    chat_start = prefix.rfind("def _show_chat_companion")
    assert "resolve_production_feature_gate_evaluation" not in prefix[chat_start:]
    persistence = (ROOT / "brain" / "response_commit_boundary.py").read_text(encoding="utf-8")
    assert "production_feature_gate" not in persistence
    assert source.count('"current_production_feature_gate_evaluation"') == 6
    assert source.count('"current_production_feature_gate_release_runtime_binding"') == 6


def test_no_public_mutation_api_names():
    import brain.production_feature_gate_owner as owner
    public = {name for name in dir(owner) if not name.startswith("_")}
    assert not public.intersection({"enable_gate", "disable_gate", "toggle_gate", "set_gate", "update_gate"})
