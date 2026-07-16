"""V5.15.24.7.4.11.1 passive, versioned Cost executable-request foundation.

This is a self-describing integrity artifact, not an authorization or an
execution entry point.  It never calculates, dispatches, or invokes runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.business_skill_cost_execution import COST_EXECUTION_VERSION, CostExecutionRequest
from brain.cost_execution_result_integrity import (
    CHANGE_SKILL_ID, PER_UNIT_SKILL_ID, SUPPORTED_SKILL_IDS,
    COST_EXECUTION_MATH_POLICY_VERSION, CanonicalExecutionOperand,
    compute_execution_math_policy_digest, compute_execution_request_integrity_digest,
    derive_canonical_execution_operands,
)
from brain.isolated_qualification_configuration_binding import (
    FOUNDATION_BOUND, IsolatedQualificationPreExecutionResult,
    verify_isolated_qualification_pre_execution_result,
)
from brain.isolated_gate_enabled_pre_authorization_qualification import (
    GATE_ENABLED_PREAUTH_QUALIFIED, IsolatedGateEnabledPreAuthorizationReport,
    verify_isolated_gate_enabled_pre_authorization_report,
)
from brain.production_feature_gate_owner import LIMITED_COST_RESPONSE_RUNTIME_BRIDGE

VERSION = "5.15.24.7.4.11.1"
SCOPE = "VERSIONED_COST_EXECUTABLE_REQUEST_CONTRACT_FOUNDATION"
STATUS = "FOUNDATION_BOUND_NOT_QUALIFIED"
TOPOLOGY = (
    "PRODUCTION_TURN_CONTEXT", "PRODUCTION_TURN_REFERENCE_TIME",
    "ISOLATED_QUALIFICATION_FEATURE_GATE_BINDING",
    "ISOLATED_QUALIFICATION_SKILL_EVIDENCE_ENVELOPE",
    "ISOLATED_QUALIFICATION_LIMITED_ACTIVATION_BINDING",
    "ISOLATED_QUALIFICATION_PRE_EXECUTION_RESULT",
    "GATE_ENABLED_PREAUTH_QUALIFICATION_REPORT", "CANONICAL_DECIMAL_OPERANDS",
    "COST_EXECUTABLE_FORMULA_BINDING", "COST_EXECUTABLE_POLICY_BINDING",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")
_FORMULAS = {
    CHANGE_SKILL_ID: ("cost.change_analysis.v1/formula.v1", "1", ("previous_cost", "current_cost")),
    PER_UNIT_SKILL_ID: ("cost.per_unit_calculation.v1/formula.v1", "1", ("total_cost", "unit_quantity")),
}


@dataclass(frozen=True)
class CostExecutableRequestAuthorityBoundary:
    approval: bool = False
    application: bool = False
    activation: bool = False
    mutation: bool = False
    persistence: bool = False
    execution: bool = False
    dispatch: bool = False
    calculator: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    delivery: bool = False
    response_replacement: bool = False
    deployment: bool = False
    rollback_execution: bool = False


@dataclass(frozen=True)
class CostExecutableFormulaBinding:
    skill_id: str
    formula_id: str
    formula_version: str
    ordered_operand_roles: tuple[str, ...]
    formula_digest: str = ""


@dataclass(frozen=True)
class CostExecutablePolicyBinding:
    policy_identity: str
    policy_version: str
    execution_version: str
    supported_skill_ids: tuple[str, ...]
    required_gate_id: str
    required_foundation_status: str
    required_preauth_requirement: str
    canonical_math_policy_digest: str
    no_execution_foundation: bool
    policy_digest: str = ""


@dataclass(frozen=True)
class VersionedCostExecutableRequest:
    version: str
    scope: str
    request_id: str
    skill_id: str
    turn_digest: str
    reference_time_digest: str
    gate_id: str
    configuration_digest: str
    evaluation_digest: str
    configuration_binding_digest: str
    evidence_envelope_digest: str
    limited_activation_digest: str
    pre_execution_result_digest: str
    preauth_report_digest: str
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    activation_binding_digest: str
    canonical_execution_request_digest: str
    operands: tuple[CanonicalExecutionOperand, ...]
    formula: CostExecutableFormulaBinding
    policy: CostExecutablePolicyBinding
    topology: tuple[str, ...]
    topology_digest: str
    status: str
    artifact_validity_claim: bool
    requirement_qualified: bool
    execute_allowed: bool
    dispatch_permitted: bool
    application_permitted: bool
    activation_permitted: bool
    runtime_invocation_permitted: bool
    execution_result: None
    authority_boundary: CostExecutableRequestAuthorityBoundary
    request_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[k, _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value): return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported request material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
                     allow_nan=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _material(value: Any, omitted: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != omitted)


def _authority_false(value: Any) -> bool:
    return type(value) is CostExecutableRequestAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and not getattr(value, f.name) for f in fields(value))


def _formula(skill: str) -> CostExecutableFormulaBinding:
    formula_id, version, roles = _FORMULAS[skill]
    draft = CostExecutableFormulaBinding(skill, formula_id, version, roles)
    return replace(draft, formula_digest=_digest("FORMULA", _material(draft, "formula_digest")))


def _policy(skill: str) -> CostExecutablePolicyBinding:
    draft = CostExecutablePolicyBinding(
        "CANONICAL_COST_EXECUTION_MATH_POLICY", COST_EXECUTION_MATH_POLICY_VERSION,
        COST_EXECUTION_VERSION, SUPPORTED_SKILL_IDS, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
        FOUNDATION_BOUND, GATE_ENABLED_PREAUTH_QUALIFIED,
        compute_execution_math_policy_digest(skill), True,
    )
    return replace(draft, policy_digest=_digest("POLICY", _material(draft, "policy_digest")))


def verify_cost_executable_operand(value: Any) -> bool:
    try:
        return (type(value) is CanonicalExecutionOperand and value.skill_id in SUPPORTED_SKILL_IDS
                and type(value.operand_index) is int and value.operand_index > 0
                and type(value.decimal_sign) is int and value.decimal_sign in (0, 1)
                and type(value.decimal_digits) is tuple and bool(value.decimal_digits)
                and all(type(x) is int and 0 <= x <= 9 for x in value.decimal_digits)
                and type(value.decimal_exponent) is int and _HEX.fullmatch(value.operand_digest) is not None)
    except (AttributeError, TypeError): return False


def verify_cost_executable_formula_binding(value: Any) -> bool:
    try: return type(value) is CostExecutableFormulaBinding and value == _formula(value.skill_id)
    except (KeyError, TypeError, AttributeError): return False


def verify_cost_executable_policy_binding(value: Any) -> bool:
    try:
        return type(value) is CostExecutablePolicyBinding and any(
            value == _policy(skill) for skill in SUPPORTED_SKILL_IDS
        )
    except (TypeError, AttributeError):
        return False


def create_versioned_cost_executable_request(
    foundation: Any, preauth_report: Any,
) -> VersionedCostExecutableRequest | None:
    try:
        if (not verify_isolated_qualification_pre_execution_result(foundation)
                or not verify_isolated_gate_enabled_pre_authorization_report(preauth_report)
                or preauth_report.foundation_result is not foundation): return None
        b, e, limited = foundation.configuration_binding, foundation.evidence_envelope, foundation.limited_activation_binding
        material = limited.canonical_limited_activation_material
        decision = material.limited_activation_decision
        if decision is None or decision.binding is None or material.selected_skill_id not in SUPPORTED_SKILL_IDS: return None
        legacy = CostExecutionRequest("foundation-" + foundation.result_digest[:32], decision.request_id,
                                      material.selected_skill_id, decision, ())
        operands = derive_canonical_execution_operands(legacy)
        if not all(verify_cost_executable_operand(x) for x in operands): return None
        formula, policy = _formula(material.selected_skill_id), _policy(material.selected_skill_id)
        topo_digest = _digest("TOPOLOGY", TOPOLOGY)
        common = (foundation.result_digest, preauth_report.report_digest, b.turn_context.turn_digest,
                  tuple(x.operand_digest for x in operands), formula.formula_digest, policy.policy_digest)
        request_id = "versioned-cost-executable-request-" + _digest("REQUEST_ID", common)
        draft = VersionedCostExecutableRequest(
            VERSION, SCOPE, request_id, material.selected_skill_id, b.turn_context.turn_digest,
            b.reference_time.reference_time_digest, b.gate_name, b.configuration_digest,
            b.evaluation_digest, b.binding_digest, e.envelope_digest, limited.binding_digest,
            foundation.result_digest, preauth_report.report_digest, b.release_owner_digest,
            b.release_revision_id, b.release_revision_digest, decision.binding.binding_digest,
            compute_execution_request_integrity_digest(legacy, operands), operands, formula, policy,
            TOPOLOGY, topo_digest, STATUS, False, False, False, False, False, False, False,
            None, CostExecutableRequestAuthorityBoundary(),
        )
        return replace(draft, request_digest=_digest("REQUEST", _material(draft, "request_digest")))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_versioned_cost_executable_request(value: Any, foundation: Any, preauth_report: Any) -> bool:
    try:
        if type(value) is not VersionedCostExecutableRequest or not _HEX.fullmatch(value.request_digest): return False
        if not _authority_false(value.authority_boundary): return False
        if any((value.artifact_validity_claim, value.requirement_qualified, value.execute_allowed,
                value.dispatch_permitted, value.application_permitted, value.activation_permitted,
                value.runtime_invocation_permitted)) or value.execution_result is not None: return False
        expected = create_versioned_cost_executable_request(foundation, preauth_report)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError): return False


__all__ = ("VERSION", "SCOPE", "STATUS", "TOPOLOGY", "CostExecutableRequestAuthorityBoundary",
           "CostExecutableFormulaBinding", "CostExecutablePolicyBinding", "VersionedCostExecutableRequest",
           "create_versioned_cost_executable_request", "verify_cost_executable_operand",
           "verify_cost_executable_formula_binding", "verify_cost_executable_policy_binding",
           "verify_versioned_cost_executable_request")
