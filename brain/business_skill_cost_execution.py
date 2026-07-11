"""V5.15.15 isolated, deny-by-default execution for two Cost skills.

The SHA-256 binding checked here is deterministic integrity protection inside
the trusted Gateway flow.  It is neither a signature nor caller authentication.
This module has no runtime, response, persistence, network, or tool authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import re
from typing import Any, Iterable

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_candidate_matcher import BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION
from brain.business_skill_evidence_mapper import BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION
from brain.business_skill_limited_activation_gateway import (
    ACTIVATION_BINDING_SCHEMA_VERSION,
    LIMITED_ACTIVATION_GATEWAY_VERSION,
    LIMITED_EXECUTION_ELIGIBLE,
    SUPPORTED_ACTIVATION_SCOPE,
    ActivationRequestBinding,
    LimitedActivationDecision,
    verify_activation_request_binding,
)
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry

COST_EXECUTION_VERSION = "5.15.15"
EXECUTED = "EXECUTED"
EXECUTION_DENIED = "EXECUTION_DENIED"
EXECUTION_INVALID = "EXECUTION_INVALID"
SUPPORTED_SKILL_IDS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")
GATE_ORDER = ("REQUEST_VALIDITY", "GATEWAY_DECISION", "ACTIVATION_BINDING",
              "REQUEST_DECISION_BINDING", "SKILL_IDENTITY", "LIFECYCLE",
              "EVIDENCE_BINDING", "NUMERIC_VALIDITY", "FORMULA_DISPATCH",
              "AUTHORITY_BOUNDARY")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True)
class CostExecutionPolicy:
    policy_version: str = COST_EXECUTION_VERSION
    decimal_precision: int = 38
    decimal_scale: int = 6
    rounding_mode: str = "ROUND_HALF_UP"
    maximum_input_digits: int = 28

    def __post_init__(self) -> None:
        if (self.policy_version != COST_EXECUTION_VERSION or self.decimal_precision != 38 or
                self.decimal_scale != 6 or self.rounding_mode != "ROUND_HALF_UP" or
                self.maximum_input_digits != 28):
            raise ValueError("unsupported numeric or execution policy")


@dataclass(frozen=True)
class CostExecutionRequest:
    execution_id: Any
    request_id: Any
    requested_skill_id: Any
    decision: Any
    authority_inputs: Any = ()


@dataclass(frozen=True)
class CostExecutionGateResult:
    gate: str
    passed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CostMetric:
    name: str
    unit: str
    value: str | None
    defined: bool = True
    undefined_reason_code: str | None = None


@dataclass(frozen=True)
class CostExecutionDenial:
    reason_codes: tuple[str, ...]
    first_failed_gate: str


@dataclass(frozen=True)
class CostExecutionError:
    reason_codes: tuple[str, ...]
    first_failed_gate: str


@dataclass(frozen=True)
class CostExecutionResult:
    execution_id: str
    request_id: str
    requested_skill_id: str
    outcome: str
    formula_id: str | None
    metrics: tuple[CostMetric, ...]
    gate_results: tuple[CostExecutionGateResult, ...]
    reason_codes: tuple[str, ...]
    denial: CostExecutionDenial | None = None
    error: CostExecutionError | None = None
    executed: bool = False
    calculated: bool = False
    reasoning_executed: bool = False
    runtime_routed: bool = False
    tools_invoked: bool = False
    persisted: bool = False
    follow_up_generated: bool = False
    response_generated: bool = False
    response_committed: bool = False


@dataclass(frozen=True)
class CostExecutionBatch:
    execution_version: str
    results: tuple[CostExecutionResult, ...]


def _gate(name: str, reasons: Iterable[str]) -> CostExecutionGateResult:
    codes = tuple(dict.fromkeys(reasons))
    return CostExecutionGateResult(name, not codes, codes or ("PASSED",))


def _decimal(value: Any, policy: CostExecutionPolicy) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError("NON_NUMERIC_VALUE")
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("NON_FINITE_VALUE")
        source = str(value)
    else:
        source = str(value)
    if not source or source.strip() != source:
        raise ValueError("MALFORMED_DECIMAL")
    try:
        result = Decimal(source)
    except (InvalidOperation, ValueError):
        raise ValueError("MALFORMED_DECIMAL") from None
    if not result.is_finite():
        raise ValueError("NON_FINITE_VALUE")
    tup = result.as_tuple()
    significant = len(tup.digits)
    integer_digits = max(significant + tup.exponent, 0)
    fractional_digits = max(-tup.exponent, 0)
    if significant > policy.maximum_input_digits or integer_digits > policy.maximum_input_digits or fractional_digits > policy.maximum_input_digits:
        raise ValueError("EXCESSIVE_NUMERIC_VALUE")
    return result


def _format(value: Decimal, policy: CostExecutionPolicy) -> str:
    quantum = Decimal(1).scaleb(-policy.decimal_scale)
    with localcontext() as ctx:
        ctx.prec = policy.decimal_precision
        rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)
    return format(rounded, f".{policy.decimal_scale}f")


def execute_cost_skill(request: Any, policy: CostExecutionPolicy | None = None) -> CostExecutionResult:
    policy = CostExecutionPolicy() if policy is None else policy
    if not isinstance(policy, CostExecutionPolicy):
        raise ValueError("policy must be CostExecutionPolicy")
    valid = isinstance(request, CostExecutionRequest)
    execution_id = request.execution_id if valid else ""
    request_id = request.request_id if valid else ""
    skill_id = request.requested_skill_id if valid else ""
    decision = request.decision if valid else None
    authority = request.authority_inputs if valid else ()

    validity = []
    if not valid: validity.append("MALFORMED_EXECUTION_REQUEST")
    if not isinstance(execution_id, str) or not _ID.fullmatch(execution_id): validity.append("INVALID_EXECUTION_ID")
    if not isinstance(request_id, str) or not request_id: validity.append("INVALID_REQUEST_ID")
    if not isinstance(skill_id, str) or not skill_id: validity.append("INVALID_REQUESTED_SKILL_ID")
    gateway = []
    if not isinstance(decision, LimitedActivationDecision): gateway.append("MISSING_OR_FABRICATED_GATEWAY_DECISION")
    elif decision.decision != LIMITED_EXECUTION_ELIGIBLE: gateway.append("GATEWAY_DECISION_NOT_ELIGIBLE")
    binding = decision.binding if isinstance(decision, LimitedActivationDecision) else None
    binding_reasons = []
    if not isinstance(binding, ActivationRequestBinding): binding_reasons.append("ACTIVATION_BINDING_REQUIRED")
    elif not verify_activation_request_binding(binding): binding_reasons.append("ACTIVATION_BINDING_VERIFICATION_FAILED")
    relation = []
    if isinstance(decision, LimitedActivationDecision) and isinstance(binding, ActivationRequestBinding):
        if request_id != binding.request_id or request_id != decision.request_id: relation.append("REQUEST_ID_MISMATCH")
        if skill_id != decision.requested_skill_id or skill_id != binding.requested_skill_id: relation.append("REQUESTED_SKILL_ID_MISMATCH")
    identity = []
    if skill_id not in SUPPORTED_SKILL_IDS: identity.append("UNSUPPORTED_SKILL")
    if isinstance(decision, LimitedActivationDecision):
        if decision.eligible_skill_id != skill_id: identity.append("ELIGIBLE_SKILL_ID_MISMATCH")
        if decision.registry_version != BUSINESS_SKILL_REGISTRY_VERSION: identity.append("REGISTRY_VERSION_MISMATCH")
        if decision.policy_version != LIMITED_ACTIVATION_GATEWAY_VERSION: identity.append("GATEWAY_POLICY_VERSION_MISMATCH")
    if isinstance(binding, ActivationRequestBinding):
        checks = ((binding.matched_skill_id, skill_id, "MATCHED_SKILL_ID_MISMATCH"),
                  (binding.registry_version, BUSINESS_SKILL_REGISTRY_VERSION, "REGISTRY_VERSION_MISMATCH"),
                  (binding.matcher_version, BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION, "MATCHER_VERSION_MISMATCH"),
                  (binding.evidence_mapper_version, BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION, "MAPPER_VERSION_MISMATCH"),
                  (binding.gateway_policy_version, LIMITED_ACTIVATION_GATEWAY_VERSION, "GATEWAY_POLICY_VERSION_MISMATCH"),
                  (binding.binding_schema_version, ACTIVATION_BINDING_SCHEMA_VERSION, "BINDING_SCHEMA_VERSION_MISMATCH"),
                  (binding.activation_scope, SUPPORTED_ACTIVATION_SCOPE, "ACTIVATION_SCOPE_MISMATCH"))
        identity.extend(code for actual, expected, code in checks if actual != expected)

    registry = get_business_skill_registry()
    canonical = next((x for x in registry if x.skill_id == skill_id), None)
    lifecycle = [] if canonical is not None and canonical.active_status == LIMITED_ACTIVE else ["LIFECYCLE_NOT_LIMITED_ACTIVE"]
    evidence_reasons, values = [], {}
    if canonical is not None and isinstance(binding, ActivationRequestBinding):
        contract = tuple(canonical.required_evidence) + tuple(canonical.optional_evidence)
        expected = {x.field_name: x for x in contract}
        expected_order = tuple(x.field_name for x in contract)
        items = binding.evidence_snapshot
        ids = tuple(x.evidence_id for x in items)
        present_expected = tuple(x for x in expected_order if x in ids)
        if len(ids) != len(set(ids)): evidence_reasons.append("DUPLICATE_EVIDENCE")
        if any(x not in expected for x in ids): evidence_reasons.append("UNKNOWN_EVIDENCE")
        if ids != present_expected: evidence_reasons.append("EVIDENCE_ORDER_MISMATCH")
        for item in items:
            spec = expected.get(item.evidence_id)
            if spec is None: continue
            if item.canonical_type != spec.field_type: evidence_reasons.append(f"EVIDENCE_TYPE_MISMATCH:{item.evidence_id}")
            if item.validation_rule != spec.validation_rule: evidence_reasons.append(f"EVIDENCE_RULE_MISMATCH:{item.evidence_id}")
            if item.required != spec.required: evidence_reasons.append(f"EVIDENCE_REQUIRED_FLAG_MISMATCH:{item.evidence_id}")
            if item.validation_status != "VALID" or item.mapping_status != "PRESENT": evidence_reasons.append(f"EVIDENCE_STATUS_INVALID:{item.evidence_id}")
            values[item.evidence_id] = item.normalized_value
        for spec in canonical.required_evidence:
            if spec.field_name not in ids: evidence_reasons.append(f"MISSING_REQUIRED_EVIDENCE:{spec.field_name}")

    numeric, operands = [], {}
    if not evidence_reasons:
        for name, value in values.items():
            try: operands[name] = _decimal(value, policy)
            except ValueError as exc: numeric.append(f"{exc.args[0]}:{name}")
        rules = {"total_cost": "positive", "unit_quantity": "positive", "waste_or_loss_quantity": "non_negative"}
        for name, rule in rules.items():
            if name in operands and ((rule == "positive" and operands[name] <= 0) or (rule == "non_negative" and operands[name] < 0)):
                numeric.append(f"NUMERIC_RULE_VIOLATION:{name}")
    formula = [] if skill_id in SUPPORTED_SKILL_IDS else ["FORMULA_NOT_SUPPORTED"]
    authority_reasons = [] if authority in (None, (), [], {}) else ["AUTHORITY_BEARING_INPUT_REJECTED"]
    reasons_by_gate = (validity, gateway, binding_reasons, relation, identity, lifecycle,
                       evidence_reasons, numeric, formula, authority_reasons)
    gates = tuple(_gate(name, reasons) for name, reasons in zip(GATE_ORDER, reasons_by_gate))
    failures = tuple(code for gate in gates for code in gate.reason_codes if code != "PASSED")
    first = next((gate.gate for gate in gates if not gate.passed), None)
    invalid_gates = {"REQUEST_VALIDITY", "NUMERIC_VALIDITY", "FORMULA_DISPATCH"}
    outcome = EXECUTION_INVALID if first in invalid_gates else EXECUTION_DENIED if first else EXECUTED
    metrics: tuple[CostMetric, ...] = ()
    formula_id = None
    if outcome == EXECUTED:
        with localcontext() as ctx:
            ctx.prec = policy.decimal_precision
            if skill_id == SUPPORTED_SKILL_IDS[0]:
                previous, current = operands["previous_cost"], operands["current_cost"]
                change = current - previous
                direction = "INCREASED" if change > 0 else "DECREASED" if change < 0 else "UNCHANGED"
                percentage = (change / previous) * Decimal(100) if previous != 0 else None
                metrics = (CostMetric("absolute_change", "currency", _format(change, policy)),
                           CostMetric("percentage_change", "percent", _format(percentage, policy) if percentage is not None else None,
                                      percentage is not None, None if percentage is not None else "PREVIOUS_COST_ZERO"),
                           CostMetric("direction", "category", direction))
                formula_id = "cost.change_analysis.v1/formula.v1"
            else:
                result = operands["total_cost"] / operands["unit_quantity"]
                metrics = (CostMetric("cost_per_unit", "currency_per_unit", _format(result, policy)),)
                formula_id = "cost.per_unit_calculation.v1/formula.v1"
    denial = CostExecutionDenial(failures, first) if outcome == EXECUTION_DENIED else None
    error = CostExecutionError(failures, first) if outcome == EXECUTION_INVALID else None
    passed = outcome == EXECUTED
    return CostExecutionResult(execution_id if isinstance(execution_id, str) else "",
        request_id if isinstance(request_id, str) else "", skill_id if isinstance(skill_id, str) else "",
        outcome, formula_id, metrics, gates, failures or ("ALL_EXECUTION_GATES_PASSED",), denial, error,
        passed, passed)


def execute_cost_skills(requests: Iterable[Any], policy: CostExecutionPolicy | None = None) -> CostExecutionBatch:
    try: items = tuple(requests)
    except TypeError: items = (requests,)
    raw_ids = [x.execution_id if isinstance(x, CostExecutionRequest) else None for x in items]
    duplicate_ids = {x for x in raw_ids if isinstance(x, str) and raw_ids.count(x) > 1}
    results = []
    for item in items:
        result = execute_cost_skill(item, policy)
        if result.execution_id in duplicate_ids:
            gates = tuple(_gate(g.gate, (("DUPLICATE_EXECUTION_ID",) if g.gate == "REQUEST_VALIDITY" else ()) +
                                tuple(c for c in g.reason_codes if c != "PASSED")) for g in result.gate_results)
            failures = tuple(c for g in gates for c in g.reason_codes if c != "PASSED")
            result = CostExecutionResult(result.execution_id, result.request_id, result.requested_skill_id,
                EXECUTION_INVALID, None, (), gates, failures, None,
                CostExecutionError(failures, "REQUEST_VALIDITY"))
        results.append(result)
    return CostExecutionBatch(COST_EXECUTION_VERSION, tuple(results))
