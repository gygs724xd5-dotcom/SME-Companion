"""V5.15.24.6.3 activation binding Decimal compatibility hotfix."""

import copy
import dataclasses
from decimal import Decimal
from fractions import Fraction

import pytest

from brain.business_skill_limited_activation_gateway import (
    ACTIVATION_BINDING_DECIMAL_SCHEMA_VERSION,
    ACTIVATION_BINDING_SCHEMA_VERSION,
    LIMITED_ACTIVATION_GATEWAY_VERSION,
    LIMITED_EXECUTION_ELIGIBLE,
    SUPPORTED_ACTIVATION_SCOPE,
    ActivationEvidenceItem,
    LimitedActivationRequest,
    _canonical_value,
    canonicalize_activation_binding_decimal,
    decide_limited_activation,
    verify_activation_request_binding,
)

NOW = "2026-07-11T12:00:00+07:00"
CHANGE = "my cost increased from 20 to 24"
UNIT = "please calculate cost per unit total 1000 for 100 units"


def rich(value):
    return {"value": value, "confidence": 1.0, "source": "current_turn",
            "freshness": "current", "user_confirmed": True}


def request(skill="cost.change_analysis.v1", evidence=None, rid="r1", message=None):
    if evidence is None:
        evidence = {"previous_cost": rich(Decimal("20.00")),
                    "current_cost": rich(Decimal("24.000"))}
    return LimitedActivationRequest(
        rid, message or (CHANGE if skill.startswith("cost.change") else UNIT), evidence, NOW,
        skill, SUPPORTED_ACTIVATION_SCOPE, LIMITED_ACTIVATION_GATEWAY_VERSION,
    )


def binding_for(values, skill="cost.change_analysis.v1"):
    evidence = ({"previous_cost": rich(values[0]), "current_cost": rich(values[1])}
                if skill.startswith("cost.change") else
                {"total_cost": rich(values[0]), "unit_quantity": rich(values[1]),
                 "waste_or_loss_quantity": rich(values[2])})
    decision = decide_limited_activation(request(skill, evidence))
    assert decision.decision == LIMITED_EXECUTION_ELIGIBLE
    assert decision.binding is not None
    return decision.binding


@pytest.mark.parametrize("value", (
    Decimal("1"), Decimal("1.0"), Decimal("1.00"), Decimal("-0"), Decimal("-0.00"),
    Decimal("1000"), Decimal("1E+3"), Decimal("12345678901234567890.12345678901234567890"),
    Decimal("1E-9999"), Decimal("9.99E+9999"), Decimal("-123.4500"),
))
def test_lossless_tagged_decimal_material(value):
    material = canonicalize_activation_binding_decimal(value)
    sign, digits, exponent = value.as_tuple()
    assert material == {"$decimal": ["DECIMAL", "5.15.24.6.3", sign, list(digits), exponent]}
    assert ACTIVATION_BINDING_DECIMAL_SCHEMA_VERSION == "5.15.24.6.3"


def test_mapper_to_gateway_change_and_per_unit_decimal_compatibility_is_deterministic():
    change_values = (Decimal("12345678901234567890.12345678901234567890"),
                     Decimal("12345678901234567890.12345678901234567891"))
    unit_values = (Decimal("1200.00000000000000000001"), Decimal("40.00"), Decimal("0.000"))
    for values, skill in ((change_values, "cost.change_analysis.v1"),
                          (unit_values, "cost.per_unit_calculation.v1")):
        first = binding_for(values, skill)
        second = binding_for(values, skill)
        assert first == second and verify_activation_request_binding(first)
        assert tuple(item.normalized_value.as_tuple() for item in first.evidence_snapshot) == tuple(
            value.as_tuple() for value in values)


def test_representation_identity_and_typed_distinction():
    representations = (Decimal("1"), Decimal("1.0"), Decimal("1.00"))
    digests = {binding_for((value, Decimal("2"))).binding_digest for value in representations}
    assert len(digests) == len(representations)
    assert binding_for((Decimal("1000"), Decimal("2"))).binding_digest != binding_for(
        (Decimal("1E+3"), Decimal("2"))).binding_digest
    assert binding_for((Decimal("-0"), Decimal("2"))).binding_digest != binding_for(
        (Decimal("-0.00"), Decimal("2"))).binding_digest
    assert binding_for((Decimal("1"), Decimal("2"))).binding_digest != binding_for((1, 2)).binding_digest
    assert binding_for((Decimal("1.0"), Decimal("2"))).binding_digest != binding_for((1.0, 2)).binding_digest


def test_nested_tuple_decimal_canonicalization_and_substitution_rejection():
    assert _canonical_value((("amount", (Decimal("1.00"),)),)) == {
        "amount": [{"$decimal": ["DECIMAL", "5.15.24.6.3", 0, [1, 0, 0], -2]}]
    }
    binding = binding_for((Decimal("1.00"), Decimal("2")))
    item = binding.evidence_snapshot[0]
    nested = dataclasses.replace(item, normalized_value=(("amount", (Decimal("1.00"),)),))
    # A caller-provided material change without the private canonical recomputation is not authority.
    assert not verify_activation_request_binding(dataclasses.replace(
        binding, evidence_snapshot=(nested,) + binding.evidence_snapshot[1:]))
    for replacement in (1, 1.0, "1.00", Decimal("1.0")):
        changed = dataclasses.replace(item, normalized_value=replacement)
        assert not verify_activation_request_binding(dataclasses.replace(
            binding, evidence_snapshot=(changed,) + binding.evidence_snapshot[1:]))


@pytest.mark.parametrize("value", (
    Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"), Fraction(1, 2),
))
def test_non_finite_and_unsupported_numeric_values_rejected(value):
    with pytest.raises(ValueError):
        canonicalize_activation_binding_decimal(value)
    with pytest.raises(ValueError):
        _canonical_value(value)


def test_decimal_subclass_rejected():
    class CustomDecimal(Decimal):
        pass
    with pytest.raises(ValueError):
        canonicalize_activation_binding_decimal(CustomDecimal("1.0"))


def test_gateway_input_non_mutation_and_binding_immutability():
    source = {"previous_cost": rich(Decimal("-0.00")), "current_cost": rich(Decimal("2.00"))}
    before = copy.deepcopy(source)
    binding = decide_limited_activation(request(evidence=source)).binding
    assert source == before and binding.evidence_snapshot[0].normalized_value.as_tuple() == Decimal("-0.00").as_tuple()
    with pytest.raises(dataclasses.FrozenInstanceError):
        binding.binding_digest = "0" * 64


def test_digest_order_cross_skill_field_and_version_tampering_fail_closed():
    binding = binding_for((Decimal("20"), Decimal("24")))
    other = binding_for((Decimal("1000"), Decimal("100"), Decimal("0")),
                        "cost.per_unit_calculation.v1")
    mutations = (
        dataclasses.replace(binding, evidence_snapshot=tuple(reversed(binding.evidence_snapshot))),
        dataclasses.replace(binding, evidence_snapshot=(other.evidence_snapshot[0],) + binding.evidence_snapshot[1:]),
        dataclasses.replace(binding, request_id="other"),
        dataclasses.replace(binding, matched_skill_id=other.matched_skill_id),
        dataclasses.replace(binding, binding_schema_version="5.15.14.1"),
        dataclasses.replace(binding, gateway_policy_version="5.15.14"),
        dataclasses.replace(binding, binding_digest="A" * 64),
        dataclasses.replace(binding, binding_digest="0" * 63),
        dataclasses.replace(binding, binding_digest="g" * 64),
    )
    assert all(not verify_activation_request_binding(item) for item in mutations)
    assert ACTIVATION_BINDING_SCHEMA_VERSION == "1"


@pytest.mark.parametrize("skill,values,expected", (
    ("cost.change_analysis.v1", (20, 24), "d6451caa315de6457972d3d33603dc9bf494e5cf447de6f09adebcbacce1a5fc"),
    ("cost.per_unit_calculation.v1", (1000, 100, 2), "915621c13b957816205c590b539bac95e24f7ec122f7695183ea90df24af654a"),
))
def test_historical_v515141_exact_int_digest_fixtures_unchanged(skill, values, expected):
    binding = binding_for(values, skill)
    assert binding.binding_digest == expected and verify_activation_request_binding(binding)


def test_existing_float_binding_digest_is_stable():
    binding = binding_for((20.5, 24.25))
    assert binding.binding_digest == "f4b19c0d9ff6cf1ca7f2542b19a16c86e00af5a1dc3697d3aef70536977a65b9"
    assert verify_activation_request_binding(binding)


def test_decision_embeds_verified_binding_without_runtime_authority():
    decision = decide_limited_activation(request())
    assert verify_activation_request_binding(decision.binding)
    assert all(not getattr(decision, name) for name in (
        "executed", "calculated", "reasoning_executed", "runtime_routed", "tools_invoked",
        "persisted", "follow_up_generated", "response_generated", "response_committed"))
