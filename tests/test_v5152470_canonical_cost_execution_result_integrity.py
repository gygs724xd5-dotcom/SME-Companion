"""V5.15.24.7.0 canonical Cost execution-result integrity sidecar tests."""
from __future__ import annotations

import ast
import dataclasses
from decimal import Decimal
from pathlib import Path

import pytest

from brain.business_skill_cost_execution import (
    EXECUTED,
    EXECUTION_DENIED,
    EXECUTION_INVALID,
    CostExecutionRequest,
    CostMetric,
    execute_cost_skill,
)
from brain.business_skill_limited_activation_gateway import (
    ACTIVATION_BINDING_DECIMAL_SCHEMA_VERSION,
    LIMITED_ACTIVATION_GATEWAY_VERSION,
    SUPPORTED_ACTIVATION_SCOPE,
    LimitedActivationRequest,
    decide_limited_activation,
)
from brain.cost_execution_result_integrity import (
    COST_EXECUTION_MATH_POLICY_VERSION,
    COST_EXECUTION_RESULT_INTEGRITY_SCOPE,
    COST_EXECUTION_RESULT_INTEGRITY_VERSION,
    CanonicalExecutionMetric,
    CanonicalExecutionOperand,
    CostExecutionMathPolicyBinding,
    CostExecutionResultIntegrity,
    compute_execution_math_policy_digest,
    compute_execution_request_integrity_digest,
    compute_execution_result_integrity_digest,
    create_cost_execution_result_integrity,
    derive_canonical_execution_operands,
    verify_cost_execution_result_integrity,
)


NOW = "2026-07-14T12:00:00+07:00"
CHANGE = "my cost increased from 30 to 40"
UNIT = "please calculate cost per unit total 1000 for 100 units"


def rich(value):
    return {
        "value": value,
        "confidence": 1.0,
        "source": "current_turn",
        "freshness": "current",
        "user_confirmed": True,
    }


def make_request(skill="cost.change_analysis.v1", evidence=None, *, eid="e1", rid="r1", authority=()):
    if evidence is None:
        evidence = ({"previous_cost": rich(Decimal("30")), "current_cost": rich(Decimal("40"))}
                    if skill == "cost.change_analysis.v1" else
                    {"total_cost": rich(Decimal("1000")), "unit_quantity": rich(Decimal("100"))})
    decision = decide_limited_activation(LimitedActivationRequest(
        rid, CHANGE if skill == "cost.change_analysis.v1" else UNIT, evidence, NOW,
        skill, SUPPORTED_ACTIVATION_SCOPE, LIMITED_ACTIVATION_GATEWAY_VERSION,
    ))
    return CostExecutionRequest(eid, rid, skill, decision, authority)


def bind(request=None):
    request = make_request() if request is None else request
    result = execute_cost_skill(request)
    artifact = create_cost_execution_result_integrity(request, result)
    return request, result, artifact


@pytest.mark.parametrize("skill,evidence,operand_ids,used", [
    ("cost.change_analysis.v1",
     {"previous_cost": rich(Decimal("30")), "current_cost": rich(Decimal("40"))},
     ("previous_cost", "current_cost"), (True, True)),
    ("cost.per_unit_calculation.v1",
     {"total_cost": rich(Decimal("1000")), "unit_quantity": rich(Decimal("100"))},
     ("total_cost", "unit_quantity"), (True, True)),
    ("cost.per_unit_calculation.v1",
     {"total_cost": rich(Decimal("1000")), "unit_quantity": rich(Decimal("100")),
      "waste_or_loss_quantity": rich(Decimal("2.00"))},
     ("total_cost", "unit_quantity", "waste_or_loss_quantity"), (True, True, False)),
])
def test_full_integrity_and_optional_waste_semantics(skill, evidence, operand_ids, used):
    request, result, artifact = bind(make_request(skill, evidence))
    assert result.outcome == EXECUTED
    assert artifact is not None and verify_cost_execution_result_integrity(artifact)
    assert tuple(x.evidence_id for x in artifact.operands) == operand_ids
    assert tuple(x.operand_used_by_formula for x in artifact.operands) == used
    assert artifact.execution_request == request and artifact.execution_result == result
    assert artifact.version == COST_EXECUTION_RESULT_INTEGRITY_VERSION == "5.15.24.7.0"
    assert artifact.scope == COST_EXECUTION_RESULT_INTEGRITY_SCOPE


def test_high_precision_decimal_and_lossless_current_business_identity():
    previous = Decimal("1.000000000000000000000000001")
    current = Decimal("1.000000000000000000000000002")
    request = make_request(evidence={"previous_cost": rich(previous), "current_cost": rich(current)})
    operands = derive_canonical_execution_operands(request)
    assert tuple((x.decimal_sign, x.decimal_digits, x.decimal_exponent) for x in operands) == (
        (previous.as_tuple().sign, previous.as_tuple().digits, previous.as_tuple().exponent),
        (current.as_tuple().sign, current.as_tuple().digits, current.as_tuple().exponent),
    )
    assert all(x.decimal_schema_version == ACTIVATION_BINDING_DECIMAL_SCHEMA_VERSION for x in operands)


def test_canonical_numeric_identity_does_not_invent_lexical_trailing_zeros():
    # The activation value is already the parser-normalized business value.
    request = make_request(evidence={
        "previous_cost": rich(Decimal("100.23")), "current_cost": rich(Decimal("101.24"))})
    operand = derive_canonical_execution_operands(request)[0]
    assert (operand.decimal_digits, operand.decimal_exponent) == (Decimal("100.23").as_tuple().digits, -2)
    assert operand.decimal_exponent != Decimal("100.2300").as_tuple().exponent


def test_request_and_policy_digests_are_deterministic_and_identity_sensitive():
    request = make_request()
    first = compute_execution_request_integrity_digest(request)
    assert first == compute_execution_request_integrity_digest(request)
    assert first != compute_execution_request_integrity_digest(make_request(eid="e2"))
    assert compute_execution_math_policy_digest(request.requested_skill_id) == (
        create_cost_execution_result_integrity(request, execute_cost_skill(request)).math_policy.math_policy_digest)
    assert compute_execution_math_policy_digest("unsupported") == ""


def test_math_policy_exact_formula_precision_rounding_and_domains():
    change = bind()[2].math_policy
    unit = bind(make_request("cost.per_unit_calculation.v1"))[2].math_policy
    assert change.formula_id == "cost.change_analysis.v1/formula.v1"
    assert unit.formula_id == "cost.per_unit_calculation.v1/formula.v1"
    for policy in (change, unit):
        assert (policy.math_policy_version, policy.arithmetic_type, policy.decimal_precision,
                policy.output_decimal_scale, policy.rounding_mode, policy.maximum_input_digits) == (
                    COST_EXECUTION_MATH_POLICY_VERSION, "DECIMAL", 38, 6, "ROUND_HALF_UP", 28)
    assert unit.formula_operand_ids == ("total_cost", "unit_quantity")
    assert dict(unit.domain_rules)["waste_or_loss_quantity"] == "optional_non_negative_not_used_by_formula"


def test_exact_metric_order_and_snapshot_fields():
    artifact = bind()[2]
    assert tuple(x.metric_id for x in artifact.metrics) == (
        "previous_cost", "current_cost", "absolute_change", "percentage_change", "direction")
    assert tuple((x.stored_value, x.unit, x.defined, x.undefined_reason_code)
                 for x in artifact.metrics) == tuple(
        (x.value, x.unit, x.defined, x.undefined_reason_code) for x in artifact.execution_result.metrics)


def test_zero_percentage_undefined_metric_is_bound_without_reparsing():
    request = make_request(evidence={
        "previous_cost": rich(Decimal("0")), "current_cost": rich(Decimal("5"))})
    _, result, artifact = bind(request)
    assert result.metrics[3] == CostMetric("percentage_change", "percent", None, False, "PREVIOUS_COST_ZERO")
    assert artifact.metrics[3].stored_value is None
    assert verify_cost_execution_result_integrity(artifact)


def test_denied_and_invalid_existing_outcomes_are_structurally_bound():
    denied_request = make_request(authority=("forbidden-authority",))
    _, denied, denied_artifact = bind(denied_request)
    assert denied.outcome == EXECUTION_DENIED
    assert denied_artifact is not None and verify_cost_execution_result_integrity(denied_artifact)
    invalid_request = make_request(evidence={
        "previous_cost": rich(Decimal("1" * 29)), "current_cost": rich(Decimal("2"))})
    _, invalid, invalid_artifact = bind(invalid_request)
    assert invalid.outcome == EXECUTION_INVALID
    assert invalid_artifact is not None and verify_cost_execution_result_integrity(invalid_artifact)


@pytest.mark.parametrize("replacement", [Decimal("30.0"), 30, 30.0, "30"])
def test_operand_value_or_decimal_type_substitution_is_rejected(replacement):
    request = make_request()
    binding = request.decision.binding
    changed_item = dataclasses.replace(binding.evidence_snapshot[0], normalized_value=replacement)
    # An unchanged digest makes the upstream binding invalid; non-Decimal variants also fail current mode.
    changed_binding = dataclasses.replace(binding, evidence_snapshot=(changed_item,) + binding.evidence_snapshot[1:])
    changed_decision = dataclasses.replace(request.decision, binding=changed_binding)
    changed_request = dataclasses.replace(request, decision=changed_decision)
    assert create_cost_execution_result_integrity(changed_request, execute_cost_skill(changed_request)) is None


def test_request_result_id_skill_and_cross_execution_substitution_rejected():
    request, result, _ = bind()
    assert create_cost_execution_result_integrity(request, dataclasses.replace(result, execution_id="other")) is None
    assert create_cost_execution_result_integrity(request, dataclasses.replace(result, request_id="other")) is None
    assert create_cost_execution_result_integrity(request, dataclasses.replace(result, requested_skill_id="cost.per_unit_calculation.v1")) is None
    other = make_request(eid="e2", rid="r2")
    assert create_cost_execution_result_integrity(other, result) is None


def test_activation_binding_and_operand_order_substitution_rejected():
    request = make_request()
    binding = request.decision.binding
    swapped = dataclasses.replace(binding, evidence_snapshot=tuple(reversed(binding.evidence_snapshot)))
    changed = dataclasses.replace(request, decision=dataclasses.replace(request.decision, binding=swapped))
    assert create_cost_execution_result_integrity(changed, execute_cost_skill(changed)) is None
    other = make_request(eid="e2", rid="r2")
    changed_artifact = dataclasses.replace(bind()[2], activation_binding_digest=other.decision.binding.binding_digest)
    assert not verify_cost_execution_result_integrity(changed_artifact)


def test_optional_waste_cannot_be_dropped_or_marked_used():
    request = make_request("cost.per_unit_calculation.v1", {
        "total_cost": rich(Decimal("100")), "unit_quantity": rich(Decimal("8")),
        "waste_or_loss_quantity": rich(Decimal("2"))})
    artifact = bind(request)[2]
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, operands=artifact.operands[:2]))
    bad_waste = dataclasses.replace(artifact.operands[2], operand_used_by_formula=True)
    assert not verify_cost_execution_result_integrity(dataclasses.replace(
        artifact, operands=artifact.operands[:2] + (bad_waste,)))


def test_formula_policy_metric_order_value_and_unit_tampering_rejected():
    artifact = bind()[2]
    bad_result = dataclasses.replace(artifact.execution_result, formula_id="evil/formula")
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, execution_result=bad_result))
    bad_policy = dataclasses.replace(artifact.math_policy, decimal_precision=39)
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, math_policy=bad_policy))
    assert not verify_cost_execution_result_integrity(dataclasses.replace(
        artifact, metrics=tuple(reversed(artifact.metrics))))
    bad_metric = dataclasses.replace(artifact.metrics[0], stored_value="999.000000")
    assert not verify_cost_execution_result_integrity(dataclasses.replace(
        artifact, metrics=(bad_metric,) + artifact.metrics[1:]))
    bad_source_metric = dataclasses.replace(artifact.execution_result.metrics[0], unit="unit")
    bad_source = dataclasses.replace(artifact.execution_result,
                                     metrics=(bad_source_metric,) + artifact.execution_result.metrics[1:])
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, execution_result=bad_source))


def test_outcome_gates_reasons_and_authority_tampering_rejected():
    artifact = bind()[2]
    assert not verify_cost_execution_result_integrity(dataclasses.replace(
        artifact, execution_result=dataclasses.replace(artifact.execution_result, outcome=EXECUTION_DENIED)))
    gate = dataclasses.replace(artifact.execution_result.gate_results[0], passed=False)
    result = dataclasses.replace(artifact.execution_result,
                                 gate_results=(gate,) + artifact.execution_result.gate_results[1:])
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, execution_result=result))
    result = dataclasses.replace(artifact.execution_result, reason_codes=("TAMPERED",))
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, execution_result=result))
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, delivery_authority=True))
    result = dataclasses.replace(artifact.execution_result, response_committed=True)
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, execution_result=result))


@pytest.mark.parametrize("digest", ["0" * 63, "0" * 65, "A" * 64, "g" * 64, "1" * 64])
def test_result_digest_malformed_or_tampered_rejected(digest):
    artifact = bind()[2]
    assert not verify_cost_execution_result_integrity(dataclasses.replace(artifact, integrity_digest=digest))


def test_immutable_non_mutating_and_repeat_run_deterministic():
    request = make_request()
    before = request
    first = create_cost_execution_result_integrity(request, execute_cost_skill(request))
    second = create_cost_execution_result_integrity(request, execute_cost_skill(request))
    assert first == second and request == before
    for cls in (CanonicalExecutionOperand, CanonicalExecutionMetric,
                CostExecutionMathPolicyBinding, CostExecutionResultIntegrity):
        assert cls.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.integrity_digest = "0" * 64


def test_constructor_and_verifier_do_not_call_calculator(monkeypatch):
    request, result, artifact = bind()
    import brain.business_skill_cost_execution as execution
    monkeypatch.setattr(execution, "execute_cost_skill", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("called")))
    assert create_cost_execution_result_integrity(request, result) == artifact
    assert verify_cost_execution_result_integrity(artifact)


def test_digest_helpers_and_all_authority_flags_are_false():
    artifact = bind()[2]
    assert compute_execution_result_integrity_digest(artifact) == artifact.integrity_digest
    assert all(getattr(artifact, name) is False for name in artifact.__dataclass_fields__
               if name.endswith("_authority"))
    assert artifact.mathematical_correctness_claimed is False


def test_source_audit_has_no_execution_or_production_side_effect_dependencies():
    path = Path(__file__).parents[1] / "brain" / "cost_execution_result_integrity.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
               for alias in node.names}
    from_imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert "app" not in imports | from_imports
    assert "execute_cost_skill" not in source
    forbidden_imports = {"streamlit", "requests", "socket", "subprocess"}
    assert not (forbidden_imports & (imports | from_imports))
    forbidden_calls = {"present_cost_result", "authorize_cost_response", "adapt_authorized_cost_response",
                       "qualify_cost_response_delivery", "execute_cost_runtime_bridge", "admit_cost_runtime"}
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not (forbidden_calls & calls)
    assert not ({"float", "int", "str"} & calls)
