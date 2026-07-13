"""V5.15.24.6 passive production turn-bound skill-evidence envelope."""
import ast
import dataclasses
from pathlib import Path

import pytest

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_turn_bound_skill_evidence import *
from brain.production_turn_context import create_production_turn_context


ROOT = Path(__file__).parents[1]


def foundations(message="cost increased", conversation="conversation-1", ordinal=1):
    context = create_production_turn_context(conversation, ordinal, message)
    gate = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
        context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    return context, gate


def envelope(message="cost increased", evidence=None, conversation="conversation-1", ordinal=1):
    context, gate = foundations(message, conversation, ordinal)
    value = create_production_turn_bound_skill_evidence_envelope(context, gate, evidence)
    assert verify_production_turn_bound_skill_evidence_envelope(value, context, gate, evidence)
    return context, gate, value


def test_version_scope_foundations_and_default_deny_gate_reference():
    context, gate, value = envelope()
    assert value.envelope_version == "5.15.24.6"
    assert value.envelope_scope == "VERIFIED_USER_TURN_SKILL_EVIDENCE"
    assert value.registry_version == "5.15.13"
    assert value.turn_digest == context.turn_digest
    assert value.feature_gate_evaluation_digest == gate.evaluation_digest
    assert not gate.effective_state and not gate.activation_permitted


def test_deterministic_normalization_and_exact_raw_thai_whitespace_newline_binding():
    message = "  ต้นทุนต่อชิ้น\nเท่าไร  "
    context, gate, first = envelope(message)
    second = create_production_turn_bound_skill_evidence_envelope(context, gate)
    assert first == second
    provenance = first.normalized_provenance
    assert provenance.raw_message_digest == context.user_message_digest
    assert provenance.normalized_message == "ต้นทุนต่อชิ้น เท่าไร"
    assert provenance.normalized_message_digest != provenance.raw_message_digest
    assert provenance.normalization_changed
    assert len(provenance.provenance_digest) == 64


@pytest.mark.parametrize(("message", "evidence", "skill_id"), (
    ("cost increased", {"previous_cost": 30, "current_cost": 40}, "cost.change_analysis.v1"),
    ("cost per unit", {"total_cost": 1200, "unit_quantity": 40}, "cost.per_unit_calculation.v1"),
))
def test_exact_cost_match_and_selection_require_complete_canonical_evidence(message, evidence, skill_id):
    _, _, value = envelope(message, evidence)
    assert tuple(item.skill_id for item in value.candidate_bindings) == (skill_id,)
    assert value.selection_status == "SHADOW_SELECTED"
    assert value.selected_skill_id == skill_id
    assert value.selected_candidate_digest == value.candidate_bindings[0].candidate_digest
    assert all(item.skill_id == skill_id for item in value.evidence_items)


def test_match_without_evidence_is_immutable_no_selection_not_fabricated_success():
    _, _, value = envelope("cost per unit")
    assert value.selected_skill_id is None
    assert value.selection_status == "EVIDENCE_NOT_READY"
    assert [item.mapping_status for item in value.evidence_items] == [
        "MISSING", "MISSING", "OPTIONAL_MISSING"
    ]
    assert all(item.value_digest is None for item in value.evidence_items)


def test_no_match_has_empty_ordered_snapshots():
    _, _, value = envelope("hello unrelated question")
    assert value.selection_status == "NO_CANDIDATES"
    assert value.selected_skill_id is None
    assert value.candidate_bindings == value.evidence_items == ()


def test_ambiguous_candidates_never_claim_selected_skill():
    evidence = {"previous_cost": 30, "current_cost": 40, "total_cost": 1200, "unit_quantity": 40}
    _, _, value = envelope("unit cost cost increased", evidence)
    assert len(value.candidate_bindings) == 2
    assert value.selection_status == "AMBIGUOUS_CANDIDATES"
    assert value.ambiguity_status == "AMBIGUOUS"
    assert value.selected_skill_id is value.selected_candidate_digest is None
    assert [item.candidate_index for item in value.candidate_bindings] == [1, 2]


def test_evidence_presence_confidence_freshness_assumption_confirmation_are_frozen():
    evidence = {
        "previous_cost": {"value": 30, "confidence": .9, "source": "current_turn", "freshness": "current", "user_confirmed": True},
        "current_cost": {"value": 40, "confidence": .95, "source": "current_turn", "freshness": "current", "assumed": False},
    }
    before = {key: dict(value) for key, value in evidence.items()}
    _, _, value = envelope("cost increased", evidence)
    assert evidence == before
    previous = value.evidence_items[0]
    assert previous.present and previous.confidence == .9 and previous.freshness == "current"
    assert previous.source == "current_turn" and previous.user_confirmed and not previous.assumed
    assert previous.value_digest and not hasattr(previous, "observed_value")
    with pytest.raises(dataclasses.FrozenInstanceError):
        previous.source = "store"


@pytest.mark.parametrize("evidence", (
    {"previous_cost": 30},
    {"previous_cost": "invalid", "current_cost": 40},
    {"previous_cost": {"value": 30, "confidence": .2}, "current_cost": 40},
))
def test_missing_invalid_or_low_confidence_evidence_fails_closed(evidence):
    _, _, value = envelope("cost increased", evidence)
    assert value.selected_skill_id is None
    assert value.selection_status != "SHADOW_SELECTED"


def test_strict_verifier_rejects_turn_gate_skill_evidence_and_digest_substitution():
    context, gate, value = envelope("cost increased", {"previous_cost": 30, "current_cost": 40})
    other_context, other_gate = foundations("cost increased", "conversation-2", 1)
    assert not verify_production_turn_bound_skill_evidence_envelope(value, other_context, other_gate,
        {"previous_cost": 30, "current_cost": 40})
    mutations = (
        dataclasses.replace(value, raw_message_digest="0" * 64),
        dataclasses.replace(value, selected_skill_id="cost.per_unit_calculation.v1"),
        dataclasses.replace(value, evidence_items=value.evidence_items[:-1]),
        dataclasses.replace(value, envelope_digest="A" * 64),
        dataclasses.replace(value, envelope_digest="0" * 63),
        dataclasses.replace(value, passive_observation=False),
        dataclasses.replace(value, routing_authority=True),
    )
    assert all(not verify_production_turn_bound_skill_evidence_envelope(
        item, context, gate, {"previous_cost": 30, "current_cost": 40}
    ) for item in mutations)


def test_candidate_duplicate_reorder_and_provenance_tampering_rejected():
    evidence = {"previous_cost": 30, "current_cost": 40, "total_cost": 1200, "unit_quantity": 40}
    context, gate, value = envelope("unit cost cost increased", evidence)
    bad = (
        dataclasses.replace(value, candidate_bindings=tuple(reversed(value.candidate_bindings))),
        dataclasses.replace(value, candidate_bindings=(value.candidate_bindings[0],) * 2),
        dataclasses.replace(value, normalized_provenance=dataclasses.replace(
            value.normalized_provenance, normalized_message="forged")),
    )
    assert all(not verify_production_turn_bound_skill_evidence_envelope(item, context, gate, evidence) for item in bad)


def test_resolver_reuses_exact_rerun_replaces_next_turn_and_returns_none_on_invalid_input():
    context, gate = foundations()
    first = resolve_production_turn_bound_skill_evidence_envelope(None, context, gate)
    assert resolve_production_turn_bound_skill_evidence_envelope(first, context, gate) is first
    next_context, next_gate = foundations("cost per unit", "conversation-1", 2)
    second = resolve_production_turn_bound_skill_evidence_envelope(first, next_context, next_gate)
    assert second != first and second.turn_id == "turn-2"
    assert resolve_production_turn_bound_skill_evidence_envelope(first, {}, gate) is None


def test_contracts_are_deeply_immutable_and_authority_flags_false():
    _, _, value = envelope("cost increased", {"previous_cost": 30, "current_cost": 40})
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.selected_skill_id = "forged"
    assert value.passive_observation
    assert all(getattr(value, name) is False for name in value.__dataclass_fields__ if name.endswith("_authority"))


def test_app_ast_single_owner_call_order_no_branch_and_transient_reset_coverage():
    source = (ROOT / "app.py").read_text("utf-8")
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_show_chat_companion")
    calls = [(node.lineno, node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", ""))
             for node in ast.walk(function) if isinstance(node, ast.Call)]
    owner = [line for line, name in calls if name == "resolve_production_turn_bound_skill_evidence_envelope"]
    context = [line for line, name in calls if name == "resolve_production_turn_context"]
    gate = [line for line, name in calls if name == "resolve_production_feature_gate_evaluation"]
    assert len(owner) == 1 and context[0] < gate[0] < owner[0]
    assert source.count('st.session_state["current_production_turn_bound_skill_evidence"] = None') == 3
    assert source.count('st.session_state.setdefault("current_production_turn_bound_skill_evidence", None)') == 1
    assert not any(isinstance(node, (ast.If, ast.While)) and
                   "current_production_turn_bound_skill_evidence" in ast.unparse(node.test)
                   for node in ast.walk(function))


def test_passive_owner_has_no_gateway_delivery_bridge_admission_persistence_or_app_imports():
    path = ROOT / "brain" / "production_turn_bound_skill_evidence.py"
    tree = ast.parse(path.read_text("utf-8"))
    imports = tuple(
        alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names
    ) + tuple(
        node.module or "" for node in tree.body if isinstance(node, ast.ImportFrom)
    )
    forbidden = ("business_skill_limited_activation_gateway", "cost_response_delivery",
                 "cost_response_runtime_bridge", "integration_admission")
    assert "app" not in imports
    assert not any(any(term in module for term in forbidden) for module in imports)
    calls = {node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
             for node in ast.walk(tree) if isinstance(node, ast.Call)}
    assert not calls.intersection({"decide_limited_activation", "bridge_prepared_cost_response",
                                   "decide_controlled_runtime_integration_admission", "safe_set_session_state"})
