"""V5.15.24.6.0.1 Evidence Mapper Decimal compatibility hotfix."""
from copy import deepcopy
from decimal import Decimal
import ast
from pathlib import Path

import pytest

from brain.business_skill import RequiredEvidence, create_cost_change_analysis_skill
from brain.business_skill_candidate_matcher import score_business_skill_candidate
from brain.business_skill_evidence_mapper import (
    BUSINESS_SKILL_EVIDENCE_MAPPER_HISTORICAL_VERSION,
    BUSINESS_SKILL_EVIDENCE_MAPPER_CURRENT_VERSION,
    BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION,
    INVALID,
    LOW_CONFIDENCE,
    PRESENT,
    canonicalize_business_number,
    is_canonical_business_number,
    map_business_skill_evidence,
    map_candidate_skill_evidence,
    validate_explicit_confidence,
)
from brain.business_skill_registry import get_business_skill_registry
from brain.business_skill_shadow_selector import SHADOW_SELECTED, select_shadow_business_skill


ROOT = Path(__file__).parents[1]


def _skill(skill_id):
    return next(item for item in get_business_skill_registry() if item.skill_id == skill_id)


def _rich(value, confidence="1.0", **overrides):
    observation = {
        "value": value,
        "confidence": confidence,
        "source": "current_turn",
        "freshness": "current",
        "assumed": False,
        "user_confirmed": False,
    }
    observation.update(overrides)
    return observation


def test_version_strategy_preserves_historical_identity():
    assert BUSINESS_SKILL_EVIDENCE_MAPPER_HISTORICAL_VERSION == "5.15.4"
    assert BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION == "5.15.4"
    assert BUSINESS_SKILL_EVIDENCE_MAPPER_CURRENT_VERSION == "5.15.24.6.0.1"


def test_decimal_cost_change_preserves_exact_values_and_explicit_confidence():
    evidence = {
        "previous_cost": _rich(Decimal("12345678901234567890.12345678901234567890")),
        "current_cost": _rich(Decimal("12345678901234567890.12345678901234567891")),
    }
    before = deepcopy(evidence)
    result = map_business_skill_evidence(create_cost_change_analysis_skill(), evidence)
    values = [item["observed_value"] for item in result["evidence_mappings"]]
    assert result["evidence_ready"]
    assert values == [evidence["previous_cost"]["value"], evidence["current_cost"]["value"]]
    assert all(type(value) is Decimal for value in values)
    assert all(item["observed_confidence"] == 1.0 for item in result["evidence_mappings"])
    assert evidence == before


def test_decimal_per_unit_required_and_optional_values_survive_mapping():
    skill = _skill("cost.per_unit_calculation.v1")
    evidence = {
        "total_cost": _rich(Decimal("1200.00000000000000000001"), Decimal("1.0")),
        "unit_quantity": _rich(Decimal("40.00")),
        "waste_or_loss_quantity": _rich(Decimal("0.000")),
    }
    first = map_business_skill_evidence(skill, evidence)
    second = map_business_skill_evidence(skill, evidence)
    assert first == second and first["evidence_ready"]
    assert first["optional_evidence_present"] == ["waste_or_loss_quantity"]
    assert [item["observed_value"].as_tuple() for item in first["evidence_mappings"]] == [
        Decimal("1200.00000000000000000001").as_tuple(),
        Decimal("40.00").as_tuple(),
        Decimal("0.000").as_tuple(),
    ]


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"), float("nan"), float("inf"), float("-inf"), True, False])
def test_non_finite_and_bool_are_invalid_business_numbers(value):
    result = map_business_skill_evidence(
        create_cost_change_analysis_skill(), {"previous_cost": value, "current_cost": 1}
    )
    assert not is_canonical_business_number(value)
    assert result["evidence_mappings"][0]["mapping_status"] == INVALID
    assert not result["evidence_ready"]


@pytest.mark.parametrize(("value", "expected"), [
    (Decimal("0"), INVALID), (Decimal("-0.01"), INVALID),
    (Decimal("0.01"), PRESENT), (1, PRESENT), (1.5, PRESENT),
])
def test_positive_rule_decimal_int_float_compatibility(value, expected):
    skill = _skill("cost.per_unit_calculation.v1")
    result = map_business_skill_evidence(skill, {"total_cost": value, "unit_quantity": 1})
    assert result["evidence_mappings"][0]["mapping_status"] == expected


@pytest.mark.parametrize(("value", "expected"), [
    (Decimal("-0.01"), INVALID), (Decimal("0.00"), PRESENT),
    (0, PRESENT), (0.5, PRESENT),
])
def test_non_negative_optional_rule(value, expected):
    skill = _skill("cost.per_unit_calculation.v1")
    result = map_business_skill_evidence(
        skill, {"total_cost": 1, "unit_quantity": 1, "waste_or_loss_quantity": value}
    )
    assert result["evidence_mappings"][2]["mapping_status"] == expected


def test_business_number_canonicalizer_preserves_type_precision_and_exponent():
    value = Decimal("1.00")
    assert canonicalize_business_number(value) is value
    assert canonicalize_business_number(value).as_tuple() == value.as_tuple()
    with pytest.raises(ValueError):
        canonicalize_business_number(Decimal("NaN"))


@pytest.mark.parametrize(("confidence", "accepted"), [
    ("1.0", True), (Decimal("1.0"), True), (1, True), (0.8, True),
    ("0.8", False), (Decimal("0.8"), False), ("bad", False),
    (float("nan"), False), (float("inf"), False), (True, False),
])
def test_explicit_confidence_validation_is_narrow_and_finite(confidence, accepted):
    _, errors = validate_explicit_confidence(confidence)
    assert (not errors) is accepted


def test_parser_confidence_is_explicit_not_default_and_threshold_semantics_hold():
    skill = create_cost_change_analysis_skill()
    explicit = {
        "previous_cost": _rich(Decimal("30"), "1.0"),
        "current_cost": _rich(Decimal("40"), "1.0"),
    }
    assert map_business_skill_evidence(skill, explicit)["evidence_confidence_floor"] == 1.0
    low = deepcopy(explicit)
    low["previous_cost"]["confidence"] = 0.7
    mapped = map_business_skill_evidence(skill, low)
    assert mapped["evidence_mappings"][0]["mapping_status"] == LOW_CONFIDENCE
    invalid = deepcopy(explicit)
    invalid["previous_cost"]["confidence"] = "0.9"
    assert map_business_skill_evidence(skill, invalid)["evidence_mappings"][0]["mapping_status"] == INVALID


def test_source_freshness_assumption_confirmation_and_unknown_field_behavior_unchanged():
    evidence = {
        "previous_cost": _rich(Decimal("30"), source="current_turn", freshness="current"),
        "current_cost": _rich(Decimal("40"), user_confirmed=True),
        "unknown": Decimal("99"),
    }
    mapped = map_business_skill_evidence(create_cost_change_analysis_skill(), evidence)
    previous, current = mapped["evidence_mappings"]
    assert previous["observed_source"] == "current_turn"
    assert previous["observed_freshness"] == "current"
    assert not previous["assumed"] and current["user_confirmed"]
    assert all(item["field_name"] != "unknown" for item in mapped["evidence_mappings"])


def test_decimal_mapper_output_remains_selector_compatible_without_changing_thresholds():
    skill = _skill("cost.change_analysis.v1")
    candidate = score_business_skill_candidate("cost changed", skill)
    mapped = map_candidate_skill_evidence(candidate, {
        "previous_cost": _rich(Decimal("30")), "current_cost": _rich(Decimal("40")),
    })
    decision = select_shadow_business_skill([candidate], [mapped])
    assert mapped["evidence_ready"]
    assert decision["selection_status"] == SHADOW_SELECTED


def test_source_audit_no_production_wiring_or_business_value_coercion():
    path = ROOT / "brain" / "business_skill_evidence_mapper.py"
    source = path.read_text("utf-8")
    tree = ast.parse(source)
    imports = {node.module or "" for node in tree.body if isinstance(node, ast.ImportFrom)}
    assert "app" not in imports
    assert "canonical_cost_evidence_parser" not in source
    assert not any(term in source for term in (
        "decide_limited_activation", "cost_response_delivery", "cost_response_runtime_bridge",
        "integration_admission", "session_state",
    ))
    business_helpers = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
        and node.name in {"is_canonical_business_number", "canonicalize_business_number", "validate_business_number"}
    }
    coercions = {
        call.func.id for node in business_helpers.values() for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        and call.func.id in {"float", "int"}
    }
    assert not coercions
    canonicalizer = business_helpers["canonicalize_business_number"]
    assert not any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                   and call.func.id == "str" for call in ast.walk(canonicalizer))
