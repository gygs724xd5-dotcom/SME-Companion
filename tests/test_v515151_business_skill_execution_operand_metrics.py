import dataclasses

import pytest

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_cost_execution import (
    COST_EXECUTION_VERSION, HISTORICAL_COST_EXECUTION_VERSION, CostExecutionRequest,
    CostMetric, execute_cost_skill,
)
from brain.business_skill_limited_activation_gateway import (
    LIMITED_ACTIVATION_GATEWAY_VERSION, SUPPORTED_ACTIVATION_SCOPE,
    LimitedActivationRequest, decide_limited_activation,
)
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry

NOW = "2026-07-11T12:00:00+07:00"


def rich(value):
    canonical = float(value) if isinstance(value, str) and "." in value else int(value) if isinstance(value, str) else value
    return {"value": canonical, "confidence": 1.0, "source": "current_turn",
            "freshness": "current", "user_confirmed": True}


def execute(skill, evidence, eid="e1", rid="r1"):
    message = ("my cost increased from 20 to 24" if "change" in skill
               else "please calculate cost per unit total 1000 for 100 units")
    decision = decide_limited_activation(LimitedActivationRequest(
        rid, message, evidence, NOW, skill, SUPPORTED_ACTIVATION_SCOPE,
        LIMITED_ACTIVATION_GATEWAY_VERSION))
    return execute_cost_skill(CostExecutionRequest(eid, rid, skill, decision)), decision


def test_versions_registry_and_lifecycle_are_compatible():
    assert HISTORICAL_COST_EXECUTION_VERSION == "5.15.15"
    assert COST_EXECUTION_VERSION == "5.15.15.1"
    assert BUSINESS_SKILL_REGISTRY_VERSION == "5.15.13"
    assert LIMITED_ACTIVATION_GATEWAY_VERSION == "5.15.14.1"
    assert sum(s.active_status == LIMITED_ACTIVE for s in get_business_skill_registry()) == 2


@pytest.mark.parametrize("previous,current,values", [
    ("20", "24", ("20.000000", "24.000000", "4.000000", "20.000000", "INCREASED")),
    ("24", "20", ("24.000000", "20.000000", "-4.000000", "-16.666667", "DECREASED")),
    ("20", "20", ("20.000000", "20.000000", "0.000000", "0.000000", "UNCHANGED")),
    ("-20", "-24", ("-20.000000", "-24.000000", "-4.000000", "20.000000", "DECREASED")),
])
def test_change_operand_metric_schema_and_values(previous, current, values):
    result, _ = execute("cost.change_analysis.v1", {"previous_cost": rich(previous), "current_cost": rich(current)})
    assert tuple(m.name for m in result.metrics) == (
        "previous_cost", "current_cost", "absolute_change", "percentage_change", "direction")
    assert tuple(m.unit for m in result.metrics) == ("currency", "currency", "currency", "percent", "category")
    assert tuple(m.value for m in result.metrics) == values


def test_zero_is_the_only_undefined_percentage_case():
    result, _ = execute("cost.change_analysis.v1", {"previous_cost": rich(0), "current_cost": rich(5)})
    assert result.metrics[3] == CostMetric("percentage_change", "percent", None, False, "PREVIOUS_COST_ZERO")


@pytest.mark.parametrize("total,quantity,expected", [
    ("1000", "100", "10.000000"), ("1", "6", "0.166667"),
])
def test_per_unit_operand_metric_schema(total, quantity, expected):
    result, _ = execute("cost.per_unit_calculation.v1", {"total_cost": rich(total), "unit_quantity": rich(quantity)})
    assert result.metrics == (
        CostMetric("total_cost", "currency", f"{int(total):.6f}"),
        CostMetric("unit_quantity", "unit", f"{int(quantity):.6f}"),
        CostMetric("cost_per_unit", "currency_per_unit", expected))


def test_formatting_does_not_round_formula_operands_early():
    result, _ = execute("cost.change_analysis.v1", {
        "previous_cost": rich("1.0000004"), "current_cost": rich("1.0000005")})
    assert tuple(m.value for m in result.metrics[:4]) == (
        "1.000000", "1.000001", "0.000000", "0.000010")


def test_optional_waste_does_not_change_schema_or_formula():
    base = {"total_cost": rich(100), "unit_quantity": rich(8)}
    absent, _ = execute("cost.per_unit_calculation.v1", base)
    present, _ = execute("cost.per_unit_calculation.v1", {**base, "waste_or_loss_quantity": rich(2)})
    assert absent.metrics == present.metrics


def test_verified_binding_snapshot_is_immutable_and_source_mutation_isolated():
    source = {"previous_cost": rich("20"), "current_cost": rich("24")}
    first, decision = execute("cost.change_analysis.v1", source)
    source["previous_cost"]["value"] = "999"
    second = execute_cost_skill(CostExecutionRequest("e1", "r1", "cost.change_analysis.v1", decision))
    assert first == second
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.metrics[0].value = "999.000000"


def test_no_authority_leakage():
    result, _ = execute("cost.change_analysis.v1", {"previous_cost": rich(20), "current_cost": rich(24)})
    assert result.executed and result.calculated
    assert not any(getattr(result, name) for name in (
        "reasoning_executed", "runtime_routed", "tools_invoked", "persisted",
        "follow_up_generated", "response_generated", "response_committed"))


def test_caller_cannot_inject_operand_metrics():
    with pytest.raises(TypeError):
        CostExecutionRequest("e1", "r1", "cost.change_analysis.v1", None,
                             operand_metrics=(CostMetric("previous_cost", "currency", "999.000000"),))
