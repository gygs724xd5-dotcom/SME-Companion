"""Historical identity and production-owner regression for the superseded V5.15.24.6 envelope."""
import ast
import dataclasses
from pathlib import Path

import pytest

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_turn_bound_skill_evidence import (
    PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_HISTORICAL_VERSION,
    PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION,
    create_production_turn_bound_skill_evidence_envelope,
    resolve_production_turn_bound_skill_evidence_envelope,
    verify_production_turn_bound_skill_evidence_envelope,
)
from brain.production_turn_context import create_production_turn_context

ROOT = Path(__file__).parents[1]


def foundations(message="ต้นทุนเพิ่มจาก 30 เป็น 40 บาท", conversation="conversation-1", ordinal=1):
    context = create_production_turn_context(conversation, ordinal, message)
    gate = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
        context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    return context, gate


def envelope(message="ต้นทุนเพิ่มจาก 30 เป็น 40 บาท", conversation="conversation-1", ordinal=1):
    context, gate = foundations(message, conversation, ordinal)
    value = create_production_turn_bound_skill_evidence_envelope(context, gate)
    assert verify_production_turn_bound_skill_evidence_envelope(value, context, gate)
    return context, gate, value


def test_historical_identity_is_preserved_without_becoming_current():
    assert PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_HISTORICAL_VERSION == "5.15.24.6"
    assert PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION == "5.15.24.6.1"


def test_deterministic_normalization_and_exact_raw_thai_whitespace_newline_binding():
    message = "  ต้นทุนต่อชิ้น\nเท่าไร  "
    context, _, first = envelope(message)
    provenance = first.normalized_provenance
    assert provenance.raw_message_digest == context.user_message_digest
    assert provenance.normalized_message == "ต้นทุนต่อชิ้น เท่าไร"
    assert provenance.normalized_message_digest != provenance.raw_message_digest
    assert provenance.normalization_changed and len(provenance.provenance_digest) == 64


@pytest.mark.parametrize(("message", "skill_id"), (
    ("ต้นทุนเพิ่มจาก 30 เป็น 40 บาท", "cost.change_analysis.v1"),
    ("ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น", "cost.per_unit_calculation.v1"),
))
def test_exact_cost_match_and_selection_require_complete_canonical_evidence(message, skill_id):
    _, _, value = envelope(message)
    assert tuple(item.skill_id for item in value.candidate_bindings) == (skill_id,)
    assert value.selector_result.selection_status == "SHADOW_SELECTED"
    assert value.selected_skill_id == skill_id
    assert value.selected_candidate_digest == value.candidate_bindings[0].candidate_digest
    assert value.canonical_parse_results[0].status == "COMPLETE"


def test_match_without_evidence_is_immutable_no_selection_not_fabricated_success():
    _, _, value = envelope("ต้นทุนต่อชิ้น")
    assert value.selected_skill_id is None
    assert value.selector_result.selection_status == "EVIDENCE_NOT_READY"
    assert [item.mapping_status for item in value.evidence_items] == [
        "MISSING", "MISSING", "OPTIONAL_MISSING"]
    assert all(item.value_digest is None for item in value.evidence_items)


def test_no_match_has_empty_ordered_snapshots():
    _, _, value = envelope("hello unrelated question")
    assert value.selector_result.selection_status == "NO_CANDIDATES"
    assert value.selected_skill_id is None
    assert value.candidate_bindings == value.canonical_parse_results == value.evidence_items == ()


def test_ambiguous_candidates_never_claim_selected_skill():
    _, _, value = envelope("unit cost cost increased")
    assert len(value.candidate_bindings) == 2
    assert value.selector_result.selection_status != "SHADOW_SELECTED"
    assert value.selected_skill_id is value.selected_candidate_digest is None
    assert [item.candidate_index for item in value.candidate_bindings] == [1, 2]


def test_parser_claims_and_mapped_evidence_are_frozen_and_explicit():
    _, _, value = envelope()
    parsed = value.canonical_parse_results[0].evidence_values[0]
    mapped = value.evidence_items[0]
    assert parsed.confidence == "1.0" and parsed.source == "CURRENT_USER_MESSAGE"
    assert parsed.freshness == "CURRENT_TURN" and not parsed.assumed and not parsed.user_confirmed
    assert mapped.present and mapped.confidence == 1.0 and mapped.value_type == "Decimal"
    assert mapped.source == "current_turn" and mapped.freshness == "current"
    with pytest.raises(dataclasses.FrozenInstanceError):
        mapped.source = "store"


@pytest.mark.parametrize("message", (
    "ต้นทุนเดิม 30",
    "ต้นทุนจาก 30 เป็น 40 และต้นทุนจาก 50 เป็น 60",
    "ต้นทุนต่อชิ้น ต้นทุนรวม -2 บาท ทำได้ 20 ชิ้น",
))
def test_missing_invalid_or_ambiguous_evidence_fails_closed(message):
    _, _, value = envelope(message)
    assert value.selected_skill_id is None


def test_strict_verifier_rejects_turn_gate_skill_evidence_and_digest_substitution():
    context, gate, value = envelope()
    other_context, other_gate = foundations("ต้นทุนเพิ่มจาก 30 เป็น 41 บาท", "conversation-2")
    assert not verify_production_turn_bound_skill_evidence_envelope(value, other_context, other_gate)
    mutations = (
        dataclasses.replace(value, raw_message_digest="0" * 64),
        dataclasses.replace(value, selected_skill_id="cost.per_unit_calculation.v1"),
        dataclasses.replace(value, evidence_items=value.evidence_items[:-1]),
        dataclasses.replace(value, envelope_digest="A" * 64),
        dataclasses.replace(value, envelope_digest="0" * 63),
        dataclasses.replace(value, passive_observation=False),
        dataclasses.replace(value, routing_authority=True),
    )
    assert all(not verify_production_turn_bound_skill_evidence_envelope(item, context, gate) for item in mutations)


def test_candidate_duplicate_reorder_and_provenance_tampering_rejected():
    context, gate, value = envelope("unit cost cost increased")
    bad = (
        dataclasses.replace(value, candidate_bindings=tuple(reversed(value.candidate_bindings))),
        dataclasses.replace(value, candidate_bindings=(value.candidate_bindings[0],) * 2),
        dataclasses.replace(value, normalized_provenance=dataclasses.replace(
            value.normalized_provenance, normalized_message="forged")),
    )
    assert all(not verify_production_turn_bound_skill_evidence_envelope(item, context, gate) for item in bad)


def test_resolver_reuses_exact_rerun_replaces_next_turn_and_returns_none_on_invalid_input():
    context, gate = foundations()
    first = resolve_production_turn_bound_skill_evidence_envelope(None, context, gate)
    assert resolve_production_turn_bound_skill_evidence_envelope(first, context, gate) is first
    next_context, next_gate = foundations("ต้นทุนต่อชิ้น", "conversation-1", 2)
    second = resolve_production_turn_bound_skill_evidence_envelope(first, next_context, next_gate)
    assert second != first and second.turn_id == "turn-2"
    assert resolve_production_turn_bound_skill_evidence_envelope(first, {}, gate) is None


def test_contracts_are_deeply_immutable_and_authority_flags_false():
    _, _, value = envelope()
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.selected_skill_id = "forged"
    assert value.passive_observation
    assert all(getattr(value, name) is False for name in value.__dataclass_fields__ if name.endswith("_authority"))


def test_app_single_passive_owner_call_order_and_no_selection_branch():
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


def test_passive_owner_forbidden_import_and_call_audit():
    source = (ROOT / "brain" / "production_turn_bound_skill_evidence.py").read_text("utf-8")
    tree = ast.parse(source)
    forbidden = ("business_skill_limited_activation_gateway", "cost_response_delivery",
                 "cost_response_runtime_bridge", "integration_admission")
    imports = tuple(node.module or "" for node in tree.body if isinstance(node, ast.ImportFrom))
    assert not any(any(term in module for term in forbidden) for module in imports)
    assert "session_state" not in source and "business_memory" not in source and "store_profile" not in source
