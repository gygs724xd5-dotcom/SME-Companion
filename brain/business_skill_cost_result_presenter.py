"""V5.15.16 pure controlled presenter for canonical Cost execution results.

The output is an internal draft only.  This module has no execution, runtime,
response, persistence, model, network, or tool authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import re
from typing import Any, Iterable

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_cost_execution import COST_EXECUTION_VERSION, EXECUTED, CostExecutionResult, CostMetric
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry

PRESENTATION_VERSION = "5.15.16"
PRESENTATION_DRAFTED = "PRESENTATION_DRAFTED"
PRESENTATION_DENIED = "PRESENTATION_DENIED"
PRESENTATION_INVALID = "PRESENTATION_INVALID"
INTERNAL_DRAFT_ONLY = "INTERNAL_DRAFT_ONLY"
SUPPORTED_LOCALE = "th-TH"
GATE_ORDER = ("REQUEST_VALIDITY", "EXECUTION_RESULT", "EXECUTION_BINDING", "SKILL_IDENTITY",
              "LIFECYCLE", "RESULT_SCHEMA", "LOCALE", "OUTPUT_CHANNEL", "TEMPLATE_DISPATCH",
              "CONTENT_BOUNDARY", "RESPONSE_AUTHORITY_BOUNDARY")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CANONICAL_DECIMAL = re.compile(r"^(?:0|[1-9][0-9]*|-[1-9][0-9]*)\.[0-9]{6}$")
_SCHEMAS = {
    "cost.change_analysis.v1": (("previous_cost", "currency"), ("current_cost", "currency"),
        ("absolute_change", "currency"), ("percentage_change", "percent"), ("direction", "category")),
    "cost.per_unit_calculation.v1": (("total_cost", "currency"), ("unit_quantity", "unit"),
        ("cost_per_unit", "currency_per_unit"),),
}
_FORMULAS = {skill: f"{skill}/formula.v1" for skill in _SCHEMAS}
_TEMPLATES = {"cost.change_analysis.v1": "COST_CHANGE_TH_V1",
              "cost.per_unit_calculation.v1": "COST_PER_UNIT_TH_V1"}


@dataclass(frozen=True)
class CostPresentationPolicy:
    policy_version: str = PRESENTATION_VERSION
    locale: str = SUPPORTED_LOCALE
    output_channel: str = INTERNAL_DRAFT_ONLY
    currency_scale: int = 2
    percent_scale: int = 2
    unit_scale: int = 2
    rounding_mode: str = "ROUND_HALF_UP"
    thousands_separator: str = ","

    def __post_init__(self) -> None:
        if (self.policy_version, self.locale, self.output_channel, self.currency_scale,
            self.percent_scale, self.unit_scale, self.rounding_mode, self.thousands_separator) != (
                PRESENTATION_VERSION, SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY, 2, 2, 2,
                "ROUND_HALF_UP", ","):
            raise ValueError("unsupported or unsafe presentation policy")


@dataclass(frozen=True)
class CostPresentationRequest:
    presentation_id: Any
    execution_id: Any
    request_id: Any
    requested_skill_id: Any
    execution_result: Any
    locale: Any
    output_channel: Any
    policy_version: Any


@dataclass(frozen=True)
class CostPresentationGateResult:
    gate: str
    passed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CostPresentationField:
    name: str
    label: str
    display_value: str
    unit: str


@dataclass(frozen=True)
class CostResponseDraft:
    template_id: str
    locale: str
    fields: tuple[CostPresentationField, ...]
    draft_text: str
    source_execution_id: str
    source_request_id: str
    source_skill_id: str
    internal_draft_only: bool = True
    content_version: str = PRESENTATION_VERSION


@dataclass(frozen=True)
class CostPresentationDenial:
    reason_codes: tuple[str, ...]
    first_failed_gate: str


@dataclass(frozen=True)
class CostPresentationResult:
    presentation_id: str
    outcome: str
    gate_results: tuple[CostPresentationGateResult, ...]
    reason_codes: tuple[str, ...]
    draft: CostResponseDraft | None = None
    denial: CostPresentationDenial | None = None
    presentation_generated: bool = False
    internal_draft_only: bool = False
    source_executed: bool = False
    source_calculated: bool = False
    business_reasoning_generated: bool = False
    runtime_routed: bool = False
    tools_invoked: bool = False
    persisted: bool = False
    follow_up_generated: bool = False
    response_generated: bool = False
    response_committed: bool = False


@dataclass(frozen=True)
class CostPresentationBatch:
    presentation_version: str
    results: tuple[CostPresentationResult, ...]


def _gate(name: str, reasons: Iterable[str]) -> CostPresentationGateResult:
    codes = tuple(dict.fromkeys(reasons))
    return CostPresentationGateResult(name, not codes, codes or ("PASSED",))


def _display(source: str, scale: int) -> str:
    value = Decimal(source)
    with localcontext() as context:
        context.prec = 38
        value = value.quantize(Decimal(1).scaleb(-scale), rounding=ROUND_HALF_UP)
    if value == 0:
        value = abs(value)
    return f"{value:,.{scale}f}"


def _validate_metrics(result: CostExecutionResult, skill: str) -> list[str]:
    reasons: list[str] = []
    metrics = result.metrics
    if not isinstance(metrics, tuple) or any(not isinstance(x, CostMetric) for x in metrics):
        return ["MALFORMED_METRICS"]
    actual = tuple((x.name, x.unit) for x in metrics)
    expected = _SCHEMAS[skill]
    names = tuple(x.name for x in metrics)
    if len(names) != len(set(names)): reasons.append("DUPLICATE_METRICS")
    if any(x not in dict(expected) for x in names): reasons.append("UNKNOWN_METRICS")
    if set(names) != set(dict(expected)): reasons.append("MISSING_METRICS")
    if actual != expected: reasons.append("METRIC_SCHEMA_OR_ORDER_MISMATCH")
    for metric in metrics:
        if metric.name == "direction":
            if (not metric.defined or metric.value not in ("INCREASED", "DECREASED", "UNCHANGED") or
                    metric.undefined_reason_code is not None): reasons.append("INVALID_DIRECTION")
            continue
        if metric.name == "percentage_change" and not metric.defined:
            previous = metrics[0] if metrics else None
            if (metric.value is not None or metric.undefined_reason_code != "PREVIOUS_COST_ZERO" or
                    previous is None or previous.value != "0.000000"):
                reasons.append("INVALID_UNDEFINED_PERCENTAGE")
            continue
        if not metric.defined or metric.undefined_reason_code is not None or not isinstance(metric.value, str):
            reasons.append(f"INVALID_METRIC_STATUS:{metric.name}")
        elif not _CANONICAL_DECIMAL.fullmatch(metric.value):
            reasons.append(f"NONCANONICAL_DECIMAL:{metric.name}")
        else:
            try:
                if not Decimal(metric.value).is_finite(): reasons.append(f"NON_FINITE_VALUE:{metric.name}")
            except InvalidOperation:
                reasons.append(f"INVALID_DECIMAL:{metric.name}")
    return reasons


def present_cost_result(request: Any, policy: CostPresentationPolicy | None = None) -> CostPresentationResult:
    policy = CostPresentationPolicy() if policy is None else policy
    if not isinstance(policy, CostPresentationPolicy):
        raise ValueError("policy must be CostPresentationPolicy")
    valid = isinstance(request, CostPresentationRequest)
    pid = request.presentation_id if valid else ""
    execution_id = request.execution_id if valid else ""
    request_id = request.request_id if valid else ""
    skill = request.requested_skill_id if valid else ""
    source = request.execution_result if valid else None
    validity = []
    if not valid: validity.append("MALFORMED_PRESENTATION_REQUEST")
    if not isinstance(pid, str) or not _ID.fullmatch(pid): validity.append("INVALID_PRESENTATION_ID")
    if not isinstance(execution_id, str) or not _ID.fullmatch(execution_id): validity.append("INVALID_EXECUTION_ID")
    if not isinstance(request_id, str) or not request_id: validity.append("INVALID_REQUEST_ID")
    if not isinstance(skill, str) or not skill: validity.append("INVALID_REQUESTED_SKILL_ID")
    if valid and request.policy_version != PRESENTATION_VERSION: validity.append("POLICY_VERSION_MISMATCH")
    execution = []
    if not isinstance(source, CostExecutionResult): execution.append("MISSING_OR_FABRICATED_EXECUTION_RESULT")
    elif source.outcome != EXECUTED or source.denial is not None or source.error is not None:
        execution.append("SOURCE_NOT_EXECUTED")
    elif not source.executed or not source.calculated: execution.append("SOURCE_EXECUTION_FLAGS_INVALID")
    binding = []
    if isinstance(source, CostExecutionResult) and (source.execution_id != execution_id or source.request_id != request_id):
        binding.append("EXECUTION_BINDING_MISMATCH")
    identity = []
    if skill not in _SCHEMAS: identity.append("UNSUPPORTED_SKILL")
    if isinstance(source, CostExecutionResult) and source.requested_skill_id != skill: identity.append("SKILL_IDENTITY_MISMATCH")
    if COST_EXECUTION_VERSION != "5.15.15.1": identity.append("EXECUTION_VERSION_MISMATCH")
    if BUSINESS_SKILL_REGISTRY_VERSION != "5.15.13": identity.append("REGISTRY_VERSION_MISMATCH")
    if isinstance(source, CostExecutionResult) and skill in _FORMULAS and source.formula_id != _FORMULAS[skill]:
        identity.append("FORMULA_ID_MISMATCH")
    canonical = next((x for x in get_business_skill_registry() if x.skill_id == skill), None)
    lifecycle = [] if canonical is not None and canonical.active_status == LIMITED_ACTIVE else ["LIFECYCLE_NOT_LIMITED_ACTIVE"]
    schema = _validate_metrics(source, skill) if isinstance(source, CostExecutionResult) and skill in _SCHEMAS else []
    locale = [] if valid and request.locale == policy.locale else ["UNSUPPORTED_LOCALE"]
    channel = [] if valid and request.output_channel == policy.output_channel else ["UNSUPPORTED_OUTPUT_CHANNEL"]
    template = [] if skill in _TEMPLATES else ["TEMPLATE_NOT_ALLOWED"]
    content: list[str] = []
    authority = []
    if isinstance(source, CostExecutionResult) and any(getattr(source, x) for x in (
            "reasoning_executed", "runtime_routed", "tools_invoked", "persisted", "follow_up_generated",
            "response_generated", "response_committed")):
        authority.append("SOURCE_AUTHORITY_LEAKAGE")
    groups = (validity, execution, binding, identity, lifecycle, schema, locale, channel, template, content, authority)
    gates = tuple(_gate(name, reasons) for name, reasons in zip(GATE_ORDER, groups))
    failures = tuple(code for gate in gates for code in gate.reason_codes if code != "PASSED")
    first = next((gate.gate for gate in gates if not gate.passed), None)
    if first:
        outcome = PRESENTATION_INVALID if first in ("REQUEST_VALIDITY", "RESULT_SCHEMA") else PRESENTATION_DENIED
        return CostPresentationResult(pid if isinstance(pid, str) else "", outcome, gates, failures,
                                      denial=CostPresentationDenial(failures, first))
    metrics = {x.name: x for x in source.metrics}
    if skill == "cost.change_analysis.v1":
        labels = (("previous_cost", "ต้นทุนเดิม"), ("current_cost", "ต้นทุนปัจจุบัน"),
                  ("absolute_change", "ผลต่างต้นทุน"))
        fields = [CostPresentationField(n, label, _display(metrics[n].value, policy.currency_scale), metrics[n].unit)
                  for n, label in labels]
        lines = [f"{x.label}: {x.display_value}" for x in fields]
        pct = metrics["percentage_change"]
        if pct.defined:
            field = CostPresentationField("percentage_change", "เปอร์เซ็นต์การเปลี่ยนแปลง",
                                          _display(pct.value, policy.percent_scale), "percent")
            fields.append(field); lines.append(f"{field.label}: {field.display_value}%")
        else:
            field = CostPresentationField("percentage_change", "เปอร์เซ็นต์การเปลี่ยนแปลง",
                "ไม่สามารถคำนวณเปอร์เซ็นต์การเปลี่ยนแปลงจากต้นทุนเดิมที่เป็นศูนย์ได้", "percent")
            fields.append(field); lines.append(field.display_value)
        direction = {"INCREASED": "เพิ่มขึ้น", "DECREASED": "ลดลง", "UNCHANGED": "ไม่เปลี่ยนแปลง"}[metrics["direction"].value]
        fields.append(CostPresentationField("direction", "ทิศทาง", direction, "category")); lines.append(f"ทิศทาง: {direction}")
    else:
        specs = (("total_cost", "ต้นทุนรวม", policy.currency_scale), ("unit_quantity", "จำนวนหน่วย", policy.unit_scale),
                 ("cost_per_unit", "ต้นทุนต่อหน่วย", policy.currency_scale))
        fields = [CostPresentationField(n, label, _display(metrics[n].value, scale), metrics[n].unit)
                  for n, label, scale in specs]
        lines = [f"{x.label}: {x.display_value}" for x in fields]
    draft = CostResponseDraft(_TEMPLATES[skill], policy.locale, tuple(fields), "\n".join(lines),
                              execution_id, request_id, skill)
    return CostPresentationResult(pid, PRESENTATION_DRAFTED, gates, ("ALL_PRESENTATION_GATES_PASSED",),
        draft=draft, presentation_generated=True, internal_draft_only=True, source_executed=True, source_calculated=True)


def present_cost_results(requests: Iterable[Any], policy: CostPresentationPolicy | None = None) -> CostPresentationBatch:
    try: items = tuple(requests)
    except TypeError: items = (requests,)
    raw = [x.presentation_id if isinstance(x, CostPresentationRequest) else None for x in items]
    duplicates = {x for x in raw if isinstance(x, str) and raw.count(x) > 1}
    results = []
    for item in items:
        result = present_cost_result(item, policy)
        if result.presentation_id in duplicates:
            reasons = ("DUPLICATE_PRESENTATION_ID",)
            gates = tuple(_gate(g.gate, reasons if g.gate == "REQUEST_VALIDITY" else ()) for g in result.gate_results)
            result = CostPresentationResult(result.presentation_id, PRESENTATION_INVALID, gates, reasons,
                denial=CostPresentationDenial(reasons, "REQUEST_VALIDITY"))
        results.append(result)
    return CostPresentationBatch(PRESENTATION_VERSION, tuple(results))
