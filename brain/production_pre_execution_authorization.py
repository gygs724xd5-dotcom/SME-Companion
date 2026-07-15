"""Canonical current-default-denied production pre-execution authorization.

This pure boundary consumes only the five canonical pre-execution foundations.
It never creates an executable request or grants production authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY,
    ProductionFeatureGateEvaluation,
    verify_production_feature_gate_evaluation,
)
from brain.production_limited_activation_binding import (
    ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED,
    ACTIVATION_DENIED,
    ERROR_CONTAINED,
    EVIDENCE_NOT_READY as BINDING_EVIDENCE_NOT_READY,
    INVALID,
    NOT_APPLICABLE as BINDING_NOT_APPLICABLE,
    ProductionLimitedActivationBinding,
    verify_production_limited_activation_binding,
)
from brain.production_turn_bound_skill_evidence import (
    ProductionTurnBoundSkillEvidenceEnvelope,
    verify_production_turn_bound_skill_evidence_envelope,
)
from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context
from brain.production_turn_reference_time import (
    ProductionTurnReferenceTime,
    verify_production_turn_reference_time,
)


PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION = "5.15.24.7.4.1"
PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE = (
    "CURRENT_DEFAULT_DENIED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION"
)

DENIED_DEFAULT_PRODUCTION_GATE = "DENIED_DEFAULT_PRODUCTION_GATE"
NOT_APPLICABLE = "NOT_APPLICABLE"
EVIDENCE_NOT_READY = "EVIDENCE_NOT_READY"
ELIGIBILITY_DENIED = "ELIGIBILITY_DENIED"
INVALID_FAIL_CLOSED = "INVALID_FAIL_CLOSED"

PRODUCTION_FEATURE_GATE_DEFAULT_DENIED = "PRODUCTION_FEATURE_GATE_DEFAULT_DENIED"
CONTROLLED_COST_RUNTIME_NOT_APPLICABLE = "CONTROLLED_COST_RUNTIME_NOT_APPLICABLE"
CONTROLLED_COST_EVIDENCE_NOT_READY = "CONTROLLED_COST_EVIDENCE_NOT_READY"
CONTROLLED_COST_ELIGIBILITY_DENIED = "CONTROLLED_COST_ELIGIBILITY_DENIED"
PRODUCTION_PRE_EXECUTION_AUTHORIZATION_INVALID = (
    "PRODUCTION_PRE_EXECUTION_AUTHORIZATION_INVALID"
)

GATE_ORDER = (
    "REQUEST_IDENTITY",
    "TURN_CONTEXT",
    "REFERENCE_TIME",
    "FEATURE_GATE_EVALUATION",
    "SKILL_EVIDENCE",
    "ACTIVATION_BINDING",
    "CROSS_ARTIFACT_PARITY",
    "APPLICABILITY",
    "EVIDENCE_READINESS",
    "ELIGIBILITY",
    "DEFAULT_DENY_GATE_STATE",
    "EXECUTION_AUTHORITY",
    "AUTHORITY_BOUNDARY",
    "PRE_EXECUTION_ISOLATION",
)

_HEX = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_ID = re.compile(r"^production-pre-execution-authorization-request-[0-9a-f]{64}$")
_SUPPORTED_SKILLS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")


@dataclass(frozen=True)
class ProductionPreExecutionAuthorizationAuthorityBoundary:
    execution: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    delivery: bool = False
    response_candidate: bool = False
    routing: bool = False
    planning: bool = False
    response_selection: bool = False
    response_guard: bool = False
    response_resolution: bool = False
    response_commit: bool = False
    persistence: bool = False
    tool_execution: bool = False
    feature_gate_mutation: bool = False


@dataclass(frozen=True)
class ProductionPreExecutionAuthorizationGateResult:
    gate: str
    satisfied: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ProductionPreExecutionAuthorizationRequest:
    version: str
    scope: str
    turn_context: ProductionTurnContext
    reference_time: ProductionTurnReferenceTime
    feature_gate_evaluation: ProductionFeatureGateEvaluation
    skill_evidence_envelope: ProductionTurnBoundSkillEvidenceEnvelope
    limited_activation_binding: ProductionLimitedActivationBinding
    request_id: str = ""
    request_digest: str = ""


@dataclass(frozen=True)
class ProductionPreExecutionAuthorizationDecision:
    version: str
    scope: str
    request_id: str
    request_digest: str
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    user_message_digest: str
    reference_time_digest: str
    accepted_at_iso: str
    feature_gate_name: str
    feature_gate_evaluation_digest: str
    feature_gate_configuration_digest: str
    envelope_version: str
    envelope_digest: str
    activation_request_id: str | None
    activation_binding_digest: str
    selected_skill_id: str | None
    activation_status: str
    request_verified: bool
    foundations_verified: bool
    eligibility_verified: bool
    eligibility_allowed: bool
    gate_identity_verified: bool
    gate_state_verified: bool
    execute_allowed: bool
    executable_request: None
    controlled_response_candidate: None
    runtime_permitted: bool
    bridge_permitted: bool
    admission_permitted: bool
    delivery_permitted: bool
    response_candidate_permitted: bool
    persistence_permitted: bool
    tool_execution_permitted: bool
    feature_gate_mutation_permitted: bool
    decision_status: str
    denial_code: str
    denial_reason: str
    gate_results: tuple[ProductionPreExecutionAuthorizationGateResult, ...]
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    authority_boundary: ProductionPreExecutionAuthorizationAuthorityBoundary
    decision_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite float")
        return {"$float": format(value, ".17g")}
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        sign, digits, exponent = value.as_tuple()
        return {"$decimal": [sign, list(digits), exponent]}
    if type(value) is datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime")
        return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("non-string mapping key")
        return [[key, _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported canonical value")


def _sha(label: str, material: Any) -> str:
    encoded = json.dumps(
        _canonical((PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION, label, material)),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _request_material(value: ProductionPreExecutionAuthorizationRequest) -> tuple[Any, ...]:
    return (
        value.version,
        value.scope,
        value.turn_context,
        value.reference_time,
        value.feature_gate_evaluation,
        value.skill_evidence_envelope,
        value.limited_activation_binding,
    )


def _decision_material(value: ProductionPreExecutionAuthorizationDecision) -> tuple[Any, ...]:
    return tuple(
        getattr(value, field.name)
        for field in fields(value)
        if field.name != "decision_digest"
    )


def _digest(value: Any) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _gate(name: str, satisfied: bool) -> ProductionPreExecutionAuthorizationGateResult:
    return ProductionPreExecutionAuthorizationGateResult(
        name,
        bool(satisfied),
        ("SATISFIED",) if satisfied else (name + "_DENIED",),
    )


def _authority_is_false(value: Any) -> bool:
    return is_dataclass(value) and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False
        for field in fields(value)
        if field.name.endswith("_authority") or field.name.endswith("_permitted")
    )


def _strict_foundations(request: Any) -> dict[str, bool]:
    if type(request) is not ProductionPreExecutionAuthorizationRequest:
        return {name: False for name in GATE_ORDER}
    c, r, g, e, b = (
        request.turn_context,
        request.reference_time,
        request.feature_gate_evaluation,
        request.skill_evidence_envelope,
        request.limited_activation_binding,
    )
    turn_ok = verify_production_turn_context(c)
    reference_ok = turn_ok and verify_production_turn_reference_time(c, r)
    gate_ok = (
        turn_ok
        and type(g) is ProductionFeatureGateEvaluation
        and verify_production_feature_gate_evaluation(
            g, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, c
        )
    )
    evidence_ok = (
        gate_ok
        and type(e) is ProductionTurnBoundSkillEvidenceEnvelope
        and verify_production_turn_bound_skill_evidence_envelope(e, c, g)
    )
    binding_verified = (
        reference_ok
        and evidence_ok
        and type(b) is ProductionLimitedActivationBinding
        and verify_production_limited_activation_binding(b, c, r, g, e)
    )
    binding_ok = binding_verified and b.binding_status not in (INVALID, ERROR_CONTAINED)
    parity = bool(
        binding_verified
        and (
            c.conversation_id,
            c.turn_id,
            c.turn_ordinal,
            c.turn_digest,
            c.user_message_digest,
        )
        == (
            e.conversation_id,
            e.turn_id,
            e.turn_ordinal,
            e.turn_digest,
            e.raw_message_digest,
        )
        and (c.conversation_id, c.turn_id, c.turn_ordinal, c.turn_digest)
        == (b.conversation_id, b.turn_id, b.turn_ordinal, b.turn_digest)
        and r.reference_time_digest == b.reference_time_digest
        and r.accepted_at_iso == b.reference_time_iso
        and g.evaluation_digest == e.feature_gate_evaluation_digest
        == b.feature_gate_evaluation_digest
        and g.effective_state == b.feature_gate_effective_state
        and g.activation_permitted == b.feature_gate_activation_permitted
        and e.envelope_digest == b.envelope_digest
        and e.selected_skill_id == b.selected_skill_id
    )
    exact_gate_identity = bool(
        gate_ok
        and g.gate_name == LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
        and g.source_identity == PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY
        and g.source_digest == PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION.source_digest
    )
    exact_default_deny = bool(
        exact_gate_identity
        and g.configured_state is False
        and g.effective_state is False
        and g.default_denied is True
        and g.activation_permitted is False
        and g.mutation_permitted is False
    )
    request_identity = bool(
        request.version == PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION
        and request.scope == PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE
        and _REQUEST_ID.fullmatch(request.request_id or "")
        and _digest(request.request_digest)
        and request.request_digest == _sha("REQUEST", _request_material(request))
        and request.request_id
        == "production-pre-execution-authorization-request-"
        + _sha("REQUEST_ID", _request_material(request))
    )
    selected = getattr(b, "selected_skill_id", None)
    applicability = (
        selected in _SUPPORTED_SKILLS or b.binding_status == BINDING_EVIDENCE_NOT_READY
    )
    readiness = binding_ok and b.binding_status != BINDING_EVIDENCE_NOT_READY
    eligibility = bool(
        binding_ok
        and b.binding_status == ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED
        and b.eligibility_allowed is True
        and b.limited_activation_decision is not None
    )
    upstream_authority_ok = all(
        _authority_is_false(item) for item in (c, r, g, e, b)
    )
    return {
        "REQUEST_IDENTITY": request_identity,
        "TURN_CONTEXT": turn_ok,
        "REFERENCE_TIME": reference_ok,
        "FEATURE_GATE_EVALUATION": gate_ok and exact_gate_identity and exact_default_deny,
        "SKILL_EVIDENCE": evidence_ok,
        "ACTIVATION_BINDING": binding_verified,
        "CROSS_ARTIFACT_PARITY": parity,
        "APPLICABILITY": applicability,
        "EVIDENCE_READINESS": readiness,
        "ELIGIBILITY": eligibility,
        "DEFAULT_DENY_GATE_STATE": False,
        "EXECUTION_AUTHORITY": getattr(b, "execution_permitted", None) is False,
        "AUTHORITY_BOUNDARY": upstream_authority_ok,
        "PRE_EXECUTION_ISOLATION": True,
    }


def create_production_pre_execution_authorization_request(
    turn_context: Any,
    reference_time: Any,
    feature_gate_evaluation: Any,
    skill_evidence_envelope: Any,
    limited_activation_binding: Any,
) -> ProductionPreExecutionAuthorizationRequest | None:
    """Bind exact canonical foundations; callers cannot supply derived policy fields."""
    try:
        draft = ProductionPreExecutionAuthorizationRequest(
            PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION,
            PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE,
            turn_context,
            reference_time,
            feature_gate_evaluation,
            skill_evidence_envelope,
            limited_activation_binding,
        )
        material = _request_material(draft)
        request = replace(
            draft,
            request_id="production-pre-execution-authorization-request-"
            + _sha("REQUEST_ID", material),
            request_digest=_sha("REQUEST", material),
        )
        checks = _strict_foundations(request)
        if not all(checks[name] for name in GATE_ORDER[:7]):
            return None
        return request
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_pre_execution_authorization_request(value: Any) -> bool:
    """Strict verification reruns canonical upstream pure verifiers."""
    try:
        if type(value) is not ProductionPreExecutionAuthorizationRequest:
            return False
        expected = create_production_pre_execution_authorization_request(
            value.turn_context,
            value.reference_time,
            value.feature_gate_evaluation,
            value.skill_evidence_envelope,
            value.limited_activation_binding,
        )
        return expected is not None and value == expected
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def _outcome(
    request: ProductionPreExecutionAuthorizationRequest,
    checks: tuple[ProductionPreExecutionAuthorizationGateResult, ...],
) -> tuple[str, str, str, bool, bool]:
    b = request.limited_activation_binding
    first = next((item.gate for item in checks if not item.satisfied), None)
    if first in GATE_ORDER[:7] or b.binding_status in (INVALID, ERROR_CONTAINED):
        return (
            INVALID_FAIL_CLOSED,
            PRODUCTION_PRE_EXECUTION_AUTHORIZATION_INVALID,
            "CANONICAL_PRE_EXECUTION_FOUNDATIONS_INVALID",
            False,
            False,
        )
    if first == "APPLICABILITY" and b.binding_status == BINDING_NOT_APPLICABLE:
        return (
            NOT_APPLICABLE,
            CONTROLLED_COST_RUNTIME_NOT_APPLICABLE,
            "NO_CANONICAL_CONTROLLED_COST_SKILL_SELECTED",
            False,
            False,
        )
    if first == "EVIDENCE_READINESS" and b.binding_status == BINDING_EVIDENCE_NOT_READY:
        return (
            EVIDENCE_NOT_READY,
            CONTROLLED_COST_EVIDENCE_NOT_READY,
            "CONTROLLED_COST_EVIDENCE_OR_SELECTION_NOT_READY",
            False,
            False,
        )
    if first == "ELIGIBILITY" and b.binding_status == ACTIVATION_DENIED:
        reason = b.reasons[0] if b.reasons else CONTROLLED_COST_ELIGIBILITY_DENIED
        return ELIGIBILITY_DENIED, CONTROLLED_COST_ELIGIBILITY_DENIED, reason, True, False
    if first == "DEFAULT_DENY_GATE_STATE":
        return (
            DENIED_DEFAULT_PRODUCTION_GATE,
            PRODUCTION_FEATURE_GATE_DEFAULT_DENIED,
            "CURRENT_PRODUCTION_FEATURE_GATE_IS_DEFAULT_DENIED",
            True,
            True,
        )
    return (
        INVALID_FAIL_CLOSED,
        PRODUCTION_PRE_EXECUTION_AUTHORIZATION_INVALID,
        "PRE_EXECUTION_AUTHORIZATION_FAILED_CLOSED",
        False,
        False,
    )


def evaluate_production_pre_execution_authorization(
    request: Any,
) -> ProductionPreExecutionAuthorizationDecision | None:
    """Return only a frozen denial; never create executable or response artifacts."""
    try:
        if type(request) is not ProductionPreExecutionAuthorizationRequest:
            return None
        c, r, g, e, b = (
            request.turn_context,
            request.reference_time,
            request.feature_gate_evaluation,
            request.skill_evidence_envelope,
            request.limited_activation_binding,
        )
        raw = _strict_foundations(request)
        gates = tuple(_gate(name, raw[name]) for name in GATE_ORDER)
        status, code, reason, eligibility_verified, eligibility_allowed = _outcome(request, gates)
        request_verified = all(raw[name] for name in GATE_ORDER[:7])
        foundations_verified = all(raw[name] for name in GATE_ORDER[1:7])
        gate_identity_verified = raw["FEATURE_GATE_EVALUATION"]
        gate_state_verified = gate_identity_verified
        first_failed = next(item.gate for item in gates if not item.satisfied)
        draft = ProductionPreExecutionAuthorizationDecision(
            PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION,
            PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE,
            request.request_id,
            request.request_digest,
            getattr(c, "conversation_id", ""),
            getattr(c, "turn_id", ""),
            getattr(c, "turn_ordinal", 0),
            getattr(c, "turn_digest", ""),
            getattr(c, "user_message_digest", ""),
            getattr(r, "reference_time_digest", ""),
            getattr(r, "accepted_at_iso", ""),
            getattr(g, "gate_name", ""),
            getattr(g, "evaluation_digest", ""),
            getattr(g, "source_digest", ""),
            getattr(e, "envelope_version", ""),
            getattr(e, "envelope_digest", ""),
            getattr(b, "activation_request_id", None),
            getattr(b, "binding_digest", ""),
            getattr(b, "selected_skill_id", None),
            getattr(b, "binding_status", INVALID),
            request_verified,
            foundations_verified,
            eligibility_verified,
            eligibility_allowed,
            gate_identity_verified,
            gate_state_verified,
            False,
            None,
            None,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            status,
            code,
            reason,
            gates,
            (code,),
            (
                "FIRST_FAILED_GATE:" + first_failed,
                "PURE_PRE_EXECUTION_DEFAULT_DENIAL",
                "NO_EXECUTABLE_OR_RESPONSE_ARTIFACT",
            ),
            ProductionPreExecutionAuthorizationAuthorityBoundary(),
        )
        return replace(
            draft,
            decision_digest=_sha("DECISION", _decision_material(draft)),
        )
    except (AttributeError, KeyError, TypeError, ValueError, StopIteration, UnicodeEncodeError):
        return None


def verify_production_pre_execution_authorization_decision(
    request: Any, decision: Any
) -> bool:
    """Recompute the complete pure decision and reject any authority escalation."""
    try:
        if (
            type(request) is not ProductionPreExecutionAuthorizationRequest
            or type(decision) is not ProductionPreExecutionAuthorizationDecision
            or not _digest(decision.decision_digest)
            or decision.execute_allowed is not False
            or decision.executable_request is not None
            or decision.controlled_response_candidate is not None
            or tuple(item.gate for item in decision.gate_results) != GATE_ORDER
            or len(set(item.gate for item in decision.gate_results)) != len(GATE_ORDER)
            or not _authority_is_false(decision)
            or not _authority_is_false(decision.authority_boundary)
        ):
            return False
        expected = evaluate_production_pre_execution_authorization(request)
        return (
            expected is not None
            and decision == expected
            and decision.decision_digest == _sha("DECISION", _decision_material(decision))
        )
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = tuple(
    name
    for name in globals()
    if name.startswith("PRODUCTION_")
    or name.startswith("CONTROLLED_")
    or name.startswith("DENIED_")
    or name
    in (
        "NOT_APPLICABLE",
        "EVIDENCE_NOT_READY",
        "ELIGIBILITY_DENIED",
        "INVALID_FAIL_CLOSED",
        "GATE_ORDER",
        "ProductionPreExecutionAuthorizationAuthorityBoundary",
        "ProductionPreExecutionAuthorizationGateResult",
        "ProductionPreExecutionAuthorizationRequest",
        "ProductionPreExecutionAuthorizationDecision",
        "create_production_pre_execution_authorization_request",
        "evaluate_production_pre_execution_authorization",
        "verify_production_pre_execution_authorization_request",
        "verify_production_pre_execution_authorization_decision",
    )
)
