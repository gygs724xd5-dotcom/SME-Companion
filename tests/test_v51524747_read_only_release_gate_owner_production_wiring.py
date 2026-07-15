from __future__ import annotations

import ast
import copy
import dataclasses
from pathlib import Path

import pytest

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_feature_gate_release_owner import (
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
)
from brain.production_feature_gate_release_runtime import (
    PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_SCOPE,
    PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_VERSION,
    ProductionFeatureGateReleaseRuntimeAuthorityBoundary,
    create_production_feature_gate_release_runtime_binding,
    resolve_production_feature_gate_release_runtime_binding,
    verify_production_feature_gate_release_runtime_binding,
)
from brain.production_turn_context import create_production_turn_context


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "production_feature_gate_release_runtime.py"
APP = ROOT / "app.py"


def artifacts(conversation_id="conversation-1", ordinal=1, message="ต้นทุน 100 บาท"):
    context = create_production_turn_context(conversation_id, ordinal, message)
    owner = get_production_feature_gate_release_owner()
    evaluation = evaluate_production_feature_gate(
        owner.configuration, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
    )
    return context, owner, evaluation


def test_contract_version_scope_exact_embedded_objects_and_default_deny():
    context, owner, evaluation = artifacts()
    binding = create_production_feature_gate_release_runtime_binding(context, owner, evaluation)
    assert binding is not None
    assert binding.version == PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_VERSION == "5.15.24.7.4.7"
    assert binding.scope == PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_SCOPE
    assert binding.turn_context is context
    assert binding.release_owner is owner
    assert binding.feature_gate_evaluation is evaluation
    assert binding.configuration_digest == "aaee359e5bef2b97416b1028be59fcd04b9e81c8838e55c300c79942cf3043ee"
    assert (binding.configured_state, binding.effective_state, binding.default_denied) == (False, False, True)
    assert binding.activation_permitted is binding.mutation_permitted is False
    assert binding.transition_applied is False and binding.executable_output is None
    assert not any(dataclasses.astuple(binding.authority_boundary))


def test_historical_direct_and_release_configuration_evaluations_are_identical():
    context, owner, release_evaluation = artifacts()
    direct = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
        context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    assert owner.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    assert owner.release_revision.configuration is owner.configuration
    assert direct == release_evaluation
    assert direct.evaluation_digest == release_evaluation.evaluation_digest
    assert direct.source_digest == owner.configuration_digest


def test_deterministic_digest_strict_verification_deepcopy_and_rerun_identity():
    context, owner, evaluation = artifacts()
    first = create_production_feature_gate_release_runtime_binding(context, owner, evaluation)
    second = create_production_feature_gate_release_runtime_binding(context, owner, evaluation)
    assert first == second and first.binding_digest == second.binding_digest
    assert copy.deepcopy(first) is first
    assert verify_production_feature_gate_release_runtime_binding(first, context, owner, evaluation)
    assert resolve_production_feature_gate_release_runtime_binding(context, owner, evaluation, first) is first


@pytest.mark.parametrize("field,value", (
    ("binding_digest", ""), ("binding_digest", "A" * 64),
    ("configured_state", True), ("effective_state", True), ("default_denied", False),
    ("transition_applied", True), ("activation_permitted", True),
    ("mutation_permitted", True), ("executable_output", "execute"),
    ("authority_boundary", dataclasses.replace(ProductionFeatureGateReleaseRuntimeAuthorityBoundary(), routing=True)),
))
def test_verifier_rejects_digest_state_permission_and_authority_tampering(field, value):
    context, owner, evaluation = artifacts()
    binding = create_production_feature_gate_release_runtime_binding(context, owner, evaluation)
    assert not verify_production_feature_gate_release_runtime_binding(
        dataclasses.replace(binding, **{field: value}), context, owner, evaluation
    )


def test_next_turn_and_conversation_replace_while_substitutions_fail_closed():
    context, owner, evaluation = artifacts()
    current = resolve_production_feature_gate_release_runtime_binding(context, owner, evaluation)
    next_context, _, next_evaluation = artifacts(ordinal=2, message="ต้นทุน 200 บาท")
    next_binding = resolve_production_feature_gate_release_runtime_binding(
        next_context, owner, next_evaluation, current
    )
    assert next_binding is not current and next_binding.turn_context is next_context
    other_context, _, other_evaluation = artifacts("conversation-2")
    other = resolve_production_feature_gate_release_runtime_binding(
        other_context, owner, other_evaluation, current
    )
    assert other is not current
    assert resolve_production_feature_gate_release_runtime_binding(context, None, evaluation, current) is None
    assert resolve_production_feature_gate_release_runtime_binding(context, owner, None, current) is None
    assert resolve_production_feature_gate_release_runtime_binding(None, owner, evaluation, current) is None
    assert resolve_production_feature_gate_release_runtime_binding(context, owner, other_evaluation, current) is None


def test_owner_revision_configuration_evaluation_and_proposal_substitution_rejected():
    context, owner, evaluation = artifacts()
    bad_revision = dataclasses.replace(owner.release_revision, revision_digest="0" * 64)
    bad_owner = dataclasses.replace(owner, release_revision=bad_revision)
    assert create_production_feature_gate_release_runtime_binding(context, bad_owner, evaluation) is None
    bad_evaluation = dataclasses.replace(evaluation, evaluation_digest="0" * 64)
    assert create_production_feature_gate_release_runtime_binding(context, owner, bad_evaluation) is None
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True
    )
    assert create_production_feature_gate_release_runtime_binding(context, proposal, evaluation) is None


def test_app_exact_call_order_single_sites_owner_configuration_and_no_gate_branch():
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    chat = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                and node.name == "_show_chat_companion")
    calls = [node for node in ast.walk(chat) if isinstance(node, ast.Call)]
    def line(name):
        return next(node.lineno for node in calls if isinstance(node.func, ast.Name) and node.func.id == name)
    order = [
        line("resolve_production_turn_context"),
        line("resolve_production_turn_reference_time"),
        line("get_production_feature_gate_release_owner"),
        line("resolve_production_feature_gate_evaluation"),
        line("resolve_production_feature_gate_release_runtime_binding"),
        line("resolve_production_turn_bound_skill_evidence_envelope"),
        line("resolve_production_limited_activation_binding"),
        line("resolve_production_pre_execution_authorization_runtime_evidence"),
    ]
    assert order == sorted(order)
    assert source.count("get_production_feature_gate_release_owner()") == 1
    assert source.count("resolve_production_feature_gate_release_runtime_binding(") == 1
    assert "PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION" not in source
    gate_call = next(node for node in calls if isinstance(node.func, ast.Name)
                     and node.func.id == "resolve_production_feature_gate_evaluation")
    assert "production_feature_gate_release_owner.configuration" in ast.unparse(gate_call)
    assert not any(isinstance(node, ast.If) and any(term in ast.unparse(node.test)
        for term in ("production_feature_gate_release_owner", "production_feature_gate_release_runtime_binding",
                     "production_feature_gate_evaluation")) for node in ast.walk(chat))


def test_transient_lifecycle_quick_action_and_no_configuration_authority():
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for name in ("_reset_chat_session", "_legacy_reset_conversation_state_for_demo_switch",
                 "_reset_conversation_state_for_demo_switch"):
        function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                        and node.name == name)
        assert "current_production_feature_gate_release_runtime_binding" in ast.unparse(function)
    quick = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                 and node.name == "_handle_quick_action_conversation")
    assert "feature_gate_release" not in ast.unparse(quick)
    evaluation_call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "resolve_production_feature_gate_evaluation")
    assert "session_state" not in ast.unparse(evaluation_call.args[1])


def test_pure_module_static_audit_has_no_external_sources_or_downstream_calls():
    source = MODULE.read_text(encoding="utf-8").lower()
    for forbidden in (
        "import os", "os.getenv", "os.environ", "streamlit", "session_state", "st.secrets",
        "query_params", "requests", "socket", "subprocess", "decimal", "open(", "write(",
        "response_candidate", "final_response", "commit_assistant", "decide_limited_activation",
        "pre_execution_authorization", "proposal.configuration", "rollback_target.configuration",
    ):
        assert forbidden not in source

