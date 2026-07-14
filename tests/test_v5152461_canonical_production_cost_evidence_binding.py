"""V5.15.24.6.1 canonical production cost extraction binding."""
import ast
import dataclasses
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from brain.canonical_cost_evidence_parser import parse_canonical_cost_evidence
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_turn_bound_skill_evidence import *
from brain.production_turn_context import create_production_turn_context

ROOT = Path(__file__).parents[1]


def foundations(message="ต้นทุนเพิ่มจาก 30 เป็น 40 บาท", conversation="conversation-1", ordinal=1):
    context = create_production_turn_context(conversation, ordinal, message)
    gate = evaluate_production_feature_gate(PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context,
                                               LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    return context, gate


def envelope(message="ต้นทุนเพิ่มจาก 30 เป็น 40 บาท", conversation="conversation-1", ordinal=1):
    context, gate = foundations(message, conversation, ordinal)
    value = create_production_turn_bound_skill_evidence_envelope(context, gate)
    assert verify_production_turn_bound_skill_evidence_envelope(value, context, gate)
    return context, gate, value


def test_versions_provenance_and_complete_change_selection():
    context, gate, value = envelope()
    assert value.envelope_version == "5.15.24.6.1"
    assert value.parser_version == "5.15.24.6.0"
    assert value.mapper_version == "5.15.24.6.0.1"
    assert value.registry_version == "5.15.13" and value.lifecycle_version == "5.15.7"
    assert value.raw_message_digest == context.user_message_digest
    assert value.feature_gate_evaluation_digest == gate.evaluation_digest
    assert value.canonical_parse_results[0].raw_message == context.user_message
    assert value.canonical_parse_results[0].skill_id == value.candidate_bindings[0].skill_id
    assert value.canonical_parse_results[0].status == "COMPLETE"
    assert value.selector_result.selection_status == "SHADOW_SELECTED"
    assert value.selected_skill_id == "cost.change_analysis.v1"
    assert value.selected_parser_digest == value.canonical_parse_results[0].parse_digest


def test_per_unit_complete_optional_waste_and_decimal_snapshots():
    _, _, value = envelope("ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น ของเสีย 2 ชิ้น")
    assert value.selected_skill_id == "cost.per_unit_calculation.v1"
    assert [item.evidence_id for item in value.evidence_items] == [
        "total_cost", "unit_quantity", "waste_or_loss_quantity"]
    assert all(item.value_type == "Decimal" for item in value.evidence_items)
    assert all(item.confidence == 1.0 for item in value.evidence_items)
    assert all(item.source == "current_turn" and item.freshness == "current" for item in value.evidence_items)
    assert all(not item.assumed and not item.user_confirmed for item in value.evidence_items)


def test_adapter_preserves_decimal_and_explicit_claims_without_mutation():
    parsed = parse_canonical_cost_evidence("cost.change_analysis.v1", "ต้นทุนเพิ่มจาก 30.00 เป็น 40.10 บาท")
    before = deepcopy(parsed)
    evidence = convert_verified_cost_parse_result_to_mapper_evidence(parsed)
    assert parsed == before
    assert evidence["previous_cost"]["value"].as_tuple() == Decimal("30").as_tuple()
    assert evidence["current_cost"]["value"] == Decimal("40.1")
    assert all(type(item["value"]) is Decimal for item in evidence.values())
    assert all(item["confidence"] == "1.0" for item in evidence.values())
    assert all(set(item) == {"value", "confidence", "source", "freshness", "assumed", "user_confirmed"}
               for item in evidence.values())


@pytest.mark.parametrize(("message", "skill_id", "status"), (
    ("ต้นทุนเดิม 30", "cost.change_analysis.v1", "PARTIAL"),
    ("ต้นทุนจาก 30 เป็น 40 และต้นทุนจาก 50 เป็น 60", "cost.change_analysis.v1", "AMBIGUOUS"),
    ("ต้นทุนรวม -2 บาท ทำได้ 20 ชิ้น", "cost.per_unit_calculation.v1", "INVALID"),
    ("ต้นทุนเปลี่ยนไปเท่าไร", "cost.change_analysis.v1", "NO_EVIDENCE"),
    ("ต้นทุนต่อชิ้น", "cost.per_unit_calculation.v1", "NO_EVIDENCE"),
))
def test_non_complete_extraction_never_selects(message, skill_id, status):
    assert parse_canonical_cost_evidence(skill_id, message).status == status
    _, _, value = envelope(message)
    if value.canonical_parse_results:
        assert all(item.status != "COMPLETE" for item in value.canonical_parse_results)
    assert value.selected_skill_id is None


def test_correction_single_value_and_prior_turn_input_are_not_evidence():
    _, _, correction = envelope("ต้นทุนเดิมแก้เป็น 40 บาท")
    assert correction.selected_skill_id is None
    first_context, first_gate, first = envelope("ต้นทุนเพิ่มจาก 30 เป็น 40 บาท")
    next_context, next_gate = foundations("ต้นทุนเปลี่ยนไปเท่าไร", ordinal=2)
    next_value = resolve_production_turn_bound_skill_evidence_envelope(first, next_context, next_gate)
    assert next_value is not first and next_value.selected_skill_id is None
    assert next_value.raw_message_digest == next_context.user_message_digest


def test_external_store_or_session_evidence_is_rejected_and_inputs_unchanged():
    context, gate = foundations("ต้นทุนเปลี่ยนไปเท่าไร")
    external = {"previous_cost": Decimal("30"), "current_cost": Decimal("40")}
    before = deepcopy(external)
    with pytest.raises(ValueError):
        create_production_turn_bound_skill_evidence_envelope(context, gate, external)
    assert external == before
    assert resolve_production_turn_bound_skill_evidence_envelope(None, context, gate, external) is None


def test_strict_verifier_rejects_cross_turn_versions_tampering_reorder_and_authority():
    context, gate, value = envelope()
    other_context, other_gate = foundations("ต้นทุนเพิ่มจาก 30 เป็น 41 บาท", "conversation-2")
    assert not verify_production_turn_bound_skill_evidence_envelope(value, other_context, other_gate)
    parse = value.canonical_parse_results[0]
    evidence = value.evidence_items[0]
    mutations = (
        dataclasses.replace(value, envelope_version="5.15.24.6"),
        dataclasses.replace(value, parser_version="wrong"),
        dataclasses.replace(value, mapper_version="5.15.4"),
        dataclasses.replace(value, lifecycle_version="5.15.6"),
        dataclasses.replace(value, canonical_parse_results=(dataclasses.replace(parse, status="PARTIAL"),)),
        dataclasses.replace(value, parser_mapper_bindings=value.parser_mapper_bindings * 2),
        dataclasses.replace(value, evidence_items=tuple(reversed(value.evidence_items))),
        dataclasses.replace(value, evidence_items=(dataclasses.replace(evidence, value_type="float"),) + value.evidence_items[1:]),
        dataclasses.replace(value, selected_skill_id="cost.per_unit_calculation.v1"),
        dataclasses.replace(value, routing_authority=True),
        dataclasses.replace(value, envelope_digest="A" * 64),
        dataclasses.replace(value, envelope_digest="0" * 63),
    )
    assert all(not verify_production_turn_bound_skill_evidence_envelope(item, context, gate) for item in mutations)


def test_exact_rerun_reuse_next_turn_reset_style_isolation_and_immutability():
    context, gate, first = envelope()
    assert resolve_production_turn_bound_skill_evidence_envelope(first, context, gate) is first
    next_context, next_gate = foundations("ต้นทุนต่อชิ้น", ordinal=2)
    second = resolve_production_turn_bound_skill_evidence_envelope(first, next_context, next_gate)
    assert second.turn_id == "turn-2" and second is not first and second.selected_skill_id is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.selected_skill_id = None
    assert first.passive_observation
    assert all(getattr(first, name) is False for name in first.__dataclass_fields__ if name.endswith("_authority"))


def test_source_audit_parser_only_here_no_float_business_conversion_or_runtime_side_effects():
    path = ROOT / "brain" / "production_turn_bound_skill_evidence.py"
    source = path.read_text("utf-8")
    tree = ast.parse(source)
    parser_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
                    isinstance(node.func, ast.Name) and node.func.id == "parse_canonical_cost_evidence"]
    assert len(parser_calls) == 1
    adapter = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and
                   node.name == "convert_verified_cost_parse_result_to_mapper_evidence")
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float"
                   for node in ast.walk(adapter))
    forbidden = ("decide_limited_activation", "prepare_delivery", "create_bridge_request",
                 "decide_controlled_runtime_integration_admission", "activate_controlled_runtime",
                 "session_state", "business_memory", "store_profile", "safe_set_session_state")
    assert not any(term in source for term in forbidden)
