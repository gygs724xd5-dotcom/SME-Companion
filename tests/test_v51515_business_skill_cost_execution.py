import dataclasses
from decimal import Decimal

import pytest

from brain.business_skill_cost_execution import *
from brain.business_skill_limited_activation_gateway import (
    LIMITED_ACTIVATION_GATEWAY_VERSION, SUPPORTED_ACTIVATION_SCOPE,
    LimitedActivationRequest, decide_limited_activation,
)

NOW = "2026-07-11T12:00:00+07:00"
CHANGE = "my cost increased from 20 to 24"
UNIT = "please calculate cost per unit total 1000 for 100 units"


def rich(value):
    return {"value": value, "confidence": 1.0, "source": "current_turn",
            "freshness": "current", "user_confirmed": True}


def decision(skill="cost.change_analysis.v1", evidence=None, rid="r1"):
    if evidence is None:
        evidence = ({"previous_cost": rich(20), "current_cost": rich(24)} if "change" in skill
                    else {"total_cost": rich(1000), "unit_quantity": rich(100)})
    message = CHANGE if "change" in skill else UNIT
    return decide_limited_activation(LimitedActivationRequest(
        rid, message, evidence, NOW, skill, SUPPORTED_ACTIVATION_SCOPE,
        LIMITED_ACTIVATION_GATEWAY_VERSION))


def execute(skill="cost.change_analysis.v1", evidence=None, eid="e1", rid="r1", d=None, **kw):
    d = decision(skill, evidence, rid) if d is None else d
    return execute_cost_skill(CostExecutionRequest(eid, rid, skill, d, kw.get("authority_inputs", ())))


@pytest.mark.parametrize("previous,current,absolute,percentage,direction", [
    (20, 24, "4.000000", "20.000000", "INCREASED"),
    (24, 20, "-4.000000", "-16.666667", "DECREASED"),
    (20, 20, "0.000000", "0.000000", "UNCHANGED"),
])
def test_change_exact_outputs(previous, current, absolute, percentage, direction):
    result = execute(evidence={"previous_cost": rich(previous), "current_cost": rich(current)})
    assert result.outcome == EXECUTED
    assert tuple((x.name, x.unit, x.value) for x in result.metrics) == (
        ("absolute_change", "currency", absolute),
        ("percentage_change", "percent", percentage),
        ("direction", "category", direction))


def test_zero_previous_has_explicit_undefined_percentage():
    result = execute(evidence={"previous_cost": rich(0), "current_cost": rich(5)})
    assert result.metrics[0].value == "5.000000"
    assert result.metrics[1] == CostMetric("percentage_change", "percent", None, False, "PREVIOUS_COST_ZERO")


@pytest.mark.parametrize("total,quantity,expected", [(1000, 100, "10.000000"), (1, 6, "0.166667"), (1.0000005, 1, "1.000001")])
def test_per_unit_exact_and_round_half_up(total, quantity, expected):
    result = execute("cost.per_unit_calculation.v1", {"total_cost": rich(total), "unit_quantity": rich(quantity)})
    assert result.outcome == EXECUTED
    assert result.metrics == (CostMetric("cost_per_unit", "currency_per_unit", expected),)


def test_optional_waste_is_bound_but_not_formula_operand():
    absent = execute("cost.per_unit_calculation.v1", {"total_cost": rich(100), "unit_quantity": rich(8)})
    present = execute("cost.per_unit_calculation.v1", {"total_cost": rich(100), "unit_quantity": rich(8), "waste_or_loss_quantity": rich(2)})
    assert absent.metrics == present.metrics == (CostMetric("cost_per_unit", "currency_per_unit", "12.500000"),)


def test_contracts_policy_gates_and_authority_flags():
    for cls in (CostExecutionPolicy, CostExecutionRequest, CostExecutionGateResult, CostMetric,
                CostExecutionResult, CostExecutionBatch, CostExecutionDenial, CostExecutionError):
        assert cls.__dataclass_params__.frozen
    result = execute()
    assert tuple(x.gate for x in result.gate_results) == GATE_ORDER
    assert (result.executed, result.calculated) == (True, True)
    for name in ("reasoning_executed", "runtime_routed", "tools_invoked", "persisted",
                 "follow_up_generated", "response_generated", "response_committed"):
        assert getattr(result, name) is False


@pytest.mark.parametrize("execution_request,code,outcome", [
    (CostExecutionRequest("", "r1", "cost.change_analysis.v1", None), "INVALID_EXECUTION_ID", EXECUTION_INVALID),
    (CostExecutionRequest("e1", "r1", "cost.change_analysis.v1", None), "MISSING_OR_FABRICATED_GATEWAY_DECISION", EXECUTION_DENIED),
    (CostExecutionRequest("e1", "wrong", "cost.change_analysis.v1", decision()), "REQUEST_ID_MISMATCH", EXECUTION_DENIED),
    (CostExecutionRequest("e1", "r1", "unsupported", decision()), "UNSUPPORTED_SKILL", EXECUTION_DENIED),
    (CostExecutionRequest("e1", "r1", "cost.change_analysis.v1", decision(), {"callback": "x"}), "AUTHORITY_BEARING_INPUT_REJECTED", EXECUTION_DENIED),
])
def test_request_gateway_identity_and_authority_denials(execution_request, code, outcome):
    result = execute_cost_skill(execution_request)
    assert result.outcome == outcome and code in result.reason_codes
    assert not any(getattr(result, x) for x in ("executed", "calculated", "reasoning_executed", "runtime_routed", "tools_invoked", "persisted", "follow_up_generated", "response_generated", "response_committed"))


def test_old_missing_and_tampered_binding_denied():
    good = decision()
    old = dataclasses.replace(good, binding=None, policy_version="5.15.14")
    assert "ACTIVATION_BINDING_REQUIRED" in execute(d=old).reason_codes
    bad_binding = dataclasses.replace(good.binding, binding_digest="0" * 64)
    bad = dataclasses.replace(good, binding=bad_binding)
    assert "ACTIVATION_BINDING_VERIFICATION_FAILED" in execute(d=bad).reason_codes


@pytest.mark.parametrize("value,code", [(True, "NON_NUMERIC_VALUE"), ("NaN", "NON_FINITE_VALUE"),
    ("Infinity", "NON_FINITE_VALUE"), ("bad", "MALFORMED_DECIMAL"), ("1" * 29, "EXCESSIVE_NUMERIC_VALUE")])
def test_numeric_invalid_even_for_integrity_valid_gateway_snapshot(value, code):
    # Re-bind a trusted-flow test artifact to prove execution's independent numeric gate.
    import brain.business_skill_limited_activation_gateway as gateway
    d = decision()
    changed = dataclasses.replace(d.binding.evidence_snapshot[0], normalized_value=value)
    base = dataclasses.replace(d.binding, evidence_snapshot=(changed,) + d.binding.evidence_snapshot[1:], binding_digest="")
    d = dataclasses.replace(d, binding=dataclasses.replace(base, binding_digest=gateway._digest(base)))
    result = execute(d=d)
    assert result.outcome == EXECUTION_INVALID
    assert any(x.startswith(code) for x in result.reason_codes)


def test_batch_duplicate_isolation_determinism_and_source_mutation():
    source = {"previous_cost": rich(20), "current_cost": rich(24)}
    d = decision(evidence=source)
    first = execute(d=d)
    source["previous_cost"]["value"] = 999
    assert execute(d=d) == first
    batch = execute_cost_skills((CostExecutionRequest("same", "r1", "cost.change_analysis.v1", d),
                                CostExecutionRequest("same", "r2", "cost.change_analysis.v1", decision(rid="r2"))))
    assert all(x.outcome == EXECUTION_INVALID and "DUPLICATE_EXECUTION_ID" in x.reason_codes for x in batch.results)


def test_frozen_binding_mutation_and_formula_injection_are_impossible():
    result = execute()
    with pytest.raises(dataclasses.FrozenInstanceError): result.formula_id = "evil"
    with pytest.raises(TypeError):
        CostExecutionRequest("e1", "r1", "cost.change_analysis.v1", decision(), formula="evil")
