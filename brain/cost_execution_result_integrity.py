"""Canonical structural integrity sidecar for isolated Cost execution results.

This module does not execute or recalculate a Cost skill.  It binds an existing
canonical activation decision, execution request, ordered Decimal operands and
execution result.  The binding proves structural provenance, not mathematical
correctness or production execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
import hashlib
import json
import math
import re
from typing import Any, Mapping

from brain.business_skill_cost_execution import (
    COST_EXECUTION_VERSION,
    EXECUTED,
    EXECUTION_DENIED,
    EXECUTION_INVALID,
    GATE_ORDER,
    CostExecutionDenial,
    CostExecutionError,
    CostExecutionGateResult,
    CostExecutionRequest,
    CostExecutionResult,
    CostMetric,
)
from brain.business_skill_limited_activation_gateway import (
    ACTIVATION_BINDING_DECIMAL_SCHEMA_VERSION,
    LIMITED_ACTIVATION_GATEWAY_VERSION,
    LIMITED_EXECUTION_ELIGIBLE,
    ActivationEvidenceItem,
    ActivationRequestBinding,
    LimitedActivationDecision,
    canonicalize_activation_binding_decimal,
    verify_activation_request_binding,
)


COST_EXECUTION_RESULT_INTEGRITY_VERSION = "5.15.24.7.0"
COST_EXECUTION_MATH_POLICY_VERSION = "5.15.24.7.0"
COST_EXECUTION_RESULT_INTEGRITY_SCOPE = "ISOLATED_CANONICAL_COST_EXECUTION_RESULT_INTEGRITY"

CHANGE_SKILL_ID = "cost.change_analysis.v1"
PER_UNIT_SKILL_ID = "cost.per_unit_calculation.v1"
SUPPORTED_SKILL_IDS = (CHANGE_SKILL_ID, PER_UNIT_SKILL_ID)

_OPERAND_ORDER = {
    CHANGE_SKILL_ID: ("previous_cost", "current_cost"),
    PER_UNIT_SKILL_ID: ("total_cost", "unit_quantity", "waste_or_loss_quantity"),
}
_FORMULA_OPERANDS = {
    CHANGE_SKILL_ID: frozenset(("previous_cost", "current_cost")),
    PER_UNIT_SKILL_ID: frozenset(("total_cost", "unit_quantity")),
}
_FORMULA_IDS = {skill: f"{skill}/formula.v1" for skill in SUPPORTED_SKILL_IDS}
_METRIC_SCHEMA = {
    CHANGE_SKILL_ID: (
        ("previous_cost", "currency"),
        ("current_cost", "currency"),
        ("absolute_change", "currency"),
        ("percentage_change", "percent"),
        ("direction", "category"),
    ),
    PER_UNIT_SKILL_ID: (
        ("total_cost", "currency"),
        ("unit_quantity", "unit"),
        ("cost_per_unit", "currency_per_unit"),
    ),
}
_HEX = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_DECIMAL_METRIC = re.compile(r"^-?(?:0|[1-9][0-9]*)\.[0-9]{6}$")
_DECISION_AUTHORITY_FIELDS = (
    "executed", "calculated", "reasoning_executed", "runtime_routed",
    "tools_invoked", "persisted", "follow_up_generated", "response_generated",
    "response_committed",
)
_RESULT_AUTHORITY_FIELDS = (
    "reasoning_executed", "runtime_routed", "tools_invoked", "persisted",
    "follow_up_generated", "response_generated", "response_committed",
)


@dataclass(frozen=True)
class CanonicalExecutionOperand:
    skill_id: str
    evidence_id: str
    semantic_role: str
    operand_index: int
    decimal_schema_version: str
    decimal_sign: int
    decimal_digits: tuple[int, ...]
    decimal_exponent: int
    evidence_snapshot_digest: str
    activation_binding_digest: str
    operand_used_by_formula: bool
    operand_digest: str = ""


@dataclass(frozen=True)
class CanonicalExecutionMetric:
    skill_id: str
    metric_id: str
    semantic_role: str
    metric_index: int
    unit: str
    stored_value: str | None
    defined: bool
    undefined_reason_code: str | None
    metric_digest: str = ""


@dataclass(frozen=True)
class CostExecutionMathPolicyBinding:
    math_policy_version: str
    execution_version: str
    skill_id: str
    formula_id: str
    arithmetic_type: str
    decimal_precision: int
    output_decimal_scale: int
    rounding_mode: str
    maximum_input_digits: int
    division_by_zero_rule: str
    domain_rules: tuple[tuple[str, str], ...]
    formula_operand_ids: tuple[str, ...]
    math_policy_digest: str = ""


@dataclass(frozen=True)
class CostExecutionResultIntegrity:
    version: str
    scope: str
    execution_request: CostExecutionRequest
    execution_result: CostExecutionResult
    activation_decision_digest: str
    activation_binding_digest: str
    operands: tuple[CanonicalExecutionOperand, ...]
    execution_request_digest: str
    math_policy: CostExecutionMathPolicyBinding
    metrics: tuple[CanonicalExecutionMetric, ...]
    result_snapshot_digest: str
    structural_provenance_verified: bool = True
    mathematical_correctness_claimed: bool = False
    production_execution_authority: bool = False
    routing_authority: bool = False
    response_selection_authority: bool = False
    presentation_authority: bool = False
    authorization_authority: bool = False
    delivery_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    bridge_authority: bool = False
    admission_authority: bool = False
    runtime_activation_authority: bool = False
    integrity_digest: str = ""


_FALSE_AUTHORITY_FIELDS = tuple(
    name for name in CostExecutionResultIntegrity.__dataclass_fields__
    if name.endswith("_authority")
)


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is Decimal:
        return canonicalize_activation_binding_decimal(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite float")
        return {"$float": format(value, ".17g")}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("non-string mapping key")
        return [[key, _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported canonical value")


def _digest(label: str, material: Any) -> str:
    encoded = json.dumps(
        _canonical((label, material)), ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _without_digest(value: Any, name: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value) if field.name != name)


def _valid_decision(decision: Any) -> bool:
    if type(decision) is not LimitedActivationDecision:
        return False
    binding = decision.binding
    if (decision.decision != LIMITED_EXECUTION_ELIGIBLE
            or decision.denial is not None
            or type(binding) is not ActivationRequestBinding
            or not verify_activation_request_binding(binding)):
        return False
    if (decision.request_id != binding.request_id
            or decision.requested_skill_id != binding.requested_skill_id
            or decision.eligible_skill_id != binding.requested_skill_id
            or decision.policy_version != LIMITED_ACTIVATION_GATEWAY_VERSION):
        return False
    if decision.reason_codes != ("ALL_ELIGIBILITY_GATES_PASSED",):
        return False
    if type(decision.gate_results) is not tuple or not decision.gate_results:
        return False
    if any(type(g.passed) is not bool or not g.passed or g.reason_codes != ("PASSED",)
           for g in decision.gate_results):
        return False
    return not any(type(getattr(decision, name)) is not bool or getattr(decision, name)
                   for name in _DECISION_AUTHORITY_FIELDS)


def _valid_request(request: Any) -> bool:
    return (
        type(request) is CostExecutionRequest
        and type(request.execution_id) is str and _ID.fullmatch(request.execution_id) is not None
        and type(request.request_id) is str and bool(request.request_id)
        and request.requested_skill_id in SUPPORTED_SKILL_IDS
        and type(request.authority_inputs) is tuple
        and _valid_decision(request.decision)
        and request.request_id == request.decision.request_id == request.decision.binding.request_id
        and request.requested_skill_id == request.decision.requested_skill_id
        == request.decision.eligible_skill_id == request.decision.binding.requested_skill_id
    )


def _evidence_digest(item: ActivationEvidenceItem) -> str:
    return _digest("CANONICAL_EXECUTION_ACTIVATION_EVIDENCE_SNAPSHOT", item)


def derive_canonical_execution_operands(request: Any) -> tuple[CanonicalExecutionOperand, ...]:
    """Derive exact current-mode Decimal operands from a verified request."""
    if not _valid_request(request):
        raise ValueError("strictly valid canonical execution request required")
    skill = request.requested_skill_id
    snapshot = request.decision.binding.evidence_snapshot
    expected = _OPERAND_ORDER[skill]
    ids = tuple(item.evidence_id for item in snapshot)
    if ids != tuple(name for name in expected if name in ids):
        raise ValueError("non-canonical operand order")
    operands = []
    for index, item in enumerate(snapshot, 1):
        value = item.normalized_value
        if type(value) is not Decimal or not value.is_finite():
            raise ValueError("current integrity mode requires exact finite Decimal operands")
        if item.validation_status != "VALID" or item.mapping_status != "PRESENT":
            raise ValueError("operand evidence is not valid and present")
        sign, digits, exponent = value.as_tuple()
        draft = CanonicalExecutionOperand(
            skill, item.evidence_id, item.evidence_id, index,
            ACTIVATION_BINDING_DECIMAL_SCHEMA_VERSION, sign, tuple(digits), exponent,
            _evidence_digest(item), request.decision.binding.binding_digest,
            item.evidence_id in _FORMULA_OPERANDS[skill],
        )
        operands.append(replace(draft, operand_digest=_digest(
            "CANONICAL_EXECUTION_OPERAND", _without_digest(draft, "operand_digest")
        )))
    required = _OPERAND_ORDER[skill][:2]
    if any(name not in ids for name in required):
        raise ValueError("missing required execution operand")
    return tuple(operands)


def _formula_id(skill_id: str) -> str:
    return _FORMULA_IDS[skill_id]


def _math_policy(skill_id: str) -> CostExecutionMathPolicyBinding:
    domain = (("previous_cost", "zero_allowed_percentage_undefined"),) if skill_id == CHANGE_SKILL_ID else (
        ("total_cost", "greater_than_zero"),
        ("unit_quantity", "greater_than_zero"),
        ("waste_or_loss_quantity", "optional_non_negative_not_used_by_formula"),
    )
    draft = CostExecutionMathPolicyBinding(
        COST_EXECUTION_MATH_POLICY_VERSION, COST_EXECUTION_VERSION, skill_id,
        _formula_id(skill_id), "DECIMAL", 38, 6, "ROUND_HALF_UP", 28,
        "PERCENTAGE_UNDEFINED_WHEN_PREVIOUS_COST_ZERO" if skill_id == CHANGE_SKILL_ID
        else "UNIT_QUANTITY_MUST_BE_GREATER_THAN_ZERO",
        domain, tuple(name for name in _OPERAND_ORDER[skill_id]
                      if name in _FORMULA_OPERANDS[skill_id]),
    )
    return replace(draft, math_policy_digest=_digest(
        "COST_EXECUTION_MATH_POLICY", _without_digest(draft, "math_policy_digest")
    ))


def compute_execution_math_policy_digest(skill_id: Any) -> str:
    if skill_id not in SUPPORTED_SKILL_IDS:
        return ""
    return _math_policy(skill_id).math_policy_digest


def _decision_digest(decision: LimitedActivationDecision) -> str:
    return _digest("LIMITED_ACTIVATION_DECISION_FOR_EXECUTION_INTEGRITY", decision)


def compute_execution_request_integrity_digest(
    request: Any, operands: tuple[CanonicalExecutionOperand, ...] | None = None,
) -> str:
    try:
        canonical_operands = derive_canonical_execution_operands(request) if operands is None else operands
        if canonical_operands != derive_canonical_execution_operands(request):
            return ""
        material = (
            COST_EXECUTION_RESULT_INTEGRITY_VERSION,
            request.execution_id, request.request_id, request.requested_skill_id,
            _decision_digest(request.decision), request.decision.binding.binding_digest,
            request.authority_inputs, tuple(item.operand_digest for item in canonical_operands),
            _formula_id(request.requested_skill_id), COST_EXECUTION_MATH_POLICY_VERSION,
        )
        return _digest("COST_EXECUTION_REQUEST_INTEGRITY", material)
    except (AttributeError, TypeError, ValueError):
        return ""


def _metric_snapshot(skill: str, result: CostExecutionResult) -> tuple[CanonicalExecutionMetric, ...]:
    metrics = []
    for index, metric in enumerate(result.metrics, 1):
        draft = CanonicalExecutionMetric(
            skill, metric.name, metric.name, index, metric.unit, metric.value,
            metric.defined, metric.undefined_reason_code,
        )
        metrics.append(replace(draft, metric_digest=_digest(
            "CANONICAL_EXECUTION_METRIC", _without_digest(draft, "metric_digest")
        )))
    return tuple(metrics)


def _valid_gate_contract(result: CostExecutionResult) -> bool:
    gates = result.gate_results
    if (type(gates) is not tuple or len(gates) != len(GATE_ORDER)
            or tuple(g.gate for g in gates) != GATE_ORDER
            or any(type(g) is not CostExecutionGateResult or type(g.passed) is not bool
                   or type(g.reason_codes) is not tuple or not g.reason_codes
                   or (g.passed != (g.reason_codes == ("PASSED",))) for g in gates)):
        return False
    failures = tuple(code for gate in gates for code in gate.reason_codes if code != "PASSED")
    return result.reason_codes == (failures or ("ALL_EXECUTION_GATES_PASSED",))


def _valid_result(request: CostExecutionRequest, result: Any) -> bool:
    if type(result) is not CostExecutionResult or not _valid_gate_contract(result):
        return False
    if (result.execution_id, result.request_id, result.requested_skill_id) != (
            request.execution_id, request.request_id, request.requested_skill_id):
        return False
    if any(type(getattr(result, name)) is not bool or getattr(result, name)
           for name in _RESULT_AUTHORITY_FIELDS):
        return False
    failures = tuple(code for gate in result.gate_results for code in gate.reason_codes if code != "PASSED")
    first = next((gate.gate for gate in result.gate_results if not gate.passed), None)
    if result.outcome == EXECUTED:
        if (failures or result.denial is not None or result.error is not None
                or result.formula_id != _formula_id(request.requested_skill_id)
                or result.executed is not True or result.calculated is not True):
            return False
        schema = _METRIC_SCHEMA[request.requested_skill_id]
        if tuple((m.name, m.unit) for m in result.metrics) != schema:
            return False
        for metric in result.metrics:
            if type(metric) is not CostMetric or type(metric.defined) is not bool:
                return False
            if metric.name == "direction":
                if metric.value not in ("INCREASED", "DECREASED", "UNCHANGED"):
                    return False
            elif metric.defined:
                if type(metric.value) is not str or not _DECIMAL_METRIC.fullmatch(metric.value):
                    return False
                if metric.undefined_reason_code is not None:
                    return False
            elif (metric.name, metric.value, metric.undefined_reason_code) != (
                    "percentage_change", None, "PREVIOUS_COST_ZERO"):
                return False
        return True
    if result.outcome not in (EXECUTION_DENIED, EXECUTION_INVALID):
        return False
    if (result.formula_id is not None or result.metrics != ()
            or result.executed is not False or result.calculated is not False or not failures):
        return False
    if result.outcome == EXECUTION_DENIED:
        return (type(result.denial) is CostExecutionDenial and result.error is None
                and result.denial.reason_codes == result.reason_codes
                and result.denial.first_failed_gate == first)
    return (type(result.error) is CostExecutionError and result.denial is None
            and result.error.reason_codes == result.reason_codes
            and result.error.first_failed_gate == first)


def _result_snapshot_digest(result: CostExecutionResult) -> str:
    return _digest("COST_EXECUTION_RESULT_SNAPSHOT", result)


def _integrity_material(value: CostExecutionResultIntegrity) -> tuple[Any, ...]:
    return _without_digest(value, "integrity_digest")


def compute_execution_result_integrity_digest(value: Any) -> str:
    try:
        if type(value) is not CostExecutionResultIntegrity:
            return ""
        return _digest("COST_EXECUTION_RESULT_INTEGRITY", _integrity_material(value))
    except (AttributeError, TypeError, ValueError):
        return ""


def create_cost_execution_result_integrity(
    request: Any, result: Any,
) -> CostExecutionResultIntegrity | None:
    """Bind an already-produced result.  This function never executes a calculator."""
    try:
        if not _valid_request(request) or not _valid_result(request, result):
            return None
        operands = derive_canonical_execution_operands(request)
        request_digest = compute_execution_request_integrity_digest(request, operands)
        if not request_digest:
            return None
        policy = _math_policy(request.requested_skill_id)
        metrics = _metric_snapshot(request.requested_skill_id, result)
        draft = CostExecutionResultIntegrity(
            COST_EXECUTION_RESULT_INTEGRITY_VERSION,
            COST_EXECUTION_RESULT_INTEGRITY_SCOPE,
            request, result, _decision_digest(request.decision),
            request.decision.binding.binding_digest, operands, request_digest,
            policy, metrics, _result_snapshot_digest(result),
        )
        return replace(draft, integrity_digest=compute_execution_result_integrity_digest(draft))
    except (AttributeError, TypeError, ValueError):
        return None


def verify_cost_execution_result_integrity(value: Any) -> bool:
    """Strictly verify structural provenance without recalculating business math."""
    try:
        if type(value) is not CostExecutionResultIntegrity:
            return False
        if (value.version != COST_EXECUTION_RESULT_INTEGRITY_VERSION
                or value.scope != COST_EXECUTION_RESULT_INTEGRITY_SCOPE
                or value.structural_provenance_verified is not True
                or value.mathematical_correctness_claimed is not False):
            return False
        if any(type(getattr(value, name)) is not bool or getattr(value, name)
               for name in _FALSE_AUTHORITY_FIELDS):
            return False
        digest_fields = (
            value.activation_decision_digest, value.activation_binding_digest,
            value.execution_request_digest, value.math_policy.math_policy_digest,
            value.result_snapshot_digest, value.integrity_digest,
            *(item.operand_digest for item in value.operands),
            *(item.evidence_snapshot_digest for item in value.operands),
            *(item.metric_digest for item in value.metrics),
        )
        if any(type(item) is not str or _HEX.fullmatch(item) is None for item in digest_fields):
            return False
        expected = create_cost_execution_result_integrity(
            value.execution_request, value.execution_result
        )
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError):
        return False


__all__ = (
    "COST_EXECUTION_RESULT_INTEGRITY_VERSION",
    "COST_EXECUTION_MATH_POLICY_VERSION",
    "COST_EXECUTION_RESULT_INTEGRITY_SCOPE",
    "CanonicalExecutionOperand",
    "CanonicalExecutionMetric",
    "CostExecutionMathPolicyBinding",
    "CostExecutionResultIntegrity",
    "derive_canonical_execution_operands",
    "compute_execution_request_integrity_digest",
    "compute_execution_math_policy_digest",
    "compute_execution_result_integrity_digest",
    "create_cost_execution_result_integrity",
    "verify_cost_execution_result_integrity",
)
