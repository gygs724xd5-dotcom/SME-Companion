"""Passive production owner for canonical pre-execution authorization evidence.

This module observes the canonical default-denied decision only.  It has no
execution, routing, response, persistence, or feature-gate authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_pre_execution_authorization import (
    PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE,
    PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION,
    ProductionPreExecutionAuthorizationDecision,
    ProductionPreExecutionAuthorizationRequest,
    create_production_pre_execution_authorization_request,
    evaluate_production_pre_execution_authorization,
    verify_production_pre_execution_authorization_decision,
    verify_production_pre_execution_authorization_request,
)


READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_VERSION = "5.15.24.7.4.3"
READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_SCOPE = (
    "READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_EVIDENCE"
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionPreExecutionAuthorizationRuntimeAuthorityBoundary:
    execution: bool = False
    calculator: bool = False
    presenter: bool = False
    authorization: bool = False
    adapter: bool = False
    delivery: bool = False
    bridge: bool = False
    admission: bool = False
    runtime: bool = False
    routing: bool = False
    planning: bool = False
    response_selection: bool = False
    response_candidate: bool = False
    response_resolution: bool = False
    response_commit: bool = False
    persistence: bool = False
    memory: bool = False
    network: bool = False
    tool_execution: bool = False
    llm: bool = False
    feature_gate_mutation: bool = False


@dataclass(frozen=True)
class ProductionPreExecutionAuthorizationRuntimeEvidence:
    version: str
    scope: str
    authorization_request: ProductionPreExecutionAuthorizationRequest
    observed_decision: ProductionPreExecutionAuthorizationDecision
    request_id: str
    request_digest: str
    decision_digest: str
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    user_message_digest: str
    reference_time_digest: str
    feature_gate_evaluation_digest: str
    envelope_digest: str
    activation_binding_digest: str
    selected_skill_id: str | None
    decision_status: str
    denial_code: str
    execute_allowed: bool
    executable_request: None
    controlled_response_candidate: None
    execution_permitted: bool
    runtime_permitted: bool
    bridge_permitted: bool
    admission_permitted: bool
    delivery_permitted: bool
    response_candidate_permitted: bool
    persistence_permitted: bool
    tool_execution_permitted: bool
    feature_gate_mutation_permitted: bool
    authority_boundary: ProductionPreExecutionAuthorizationRuntimeAuthorityBoundary
    runtime_evidence_digest: str = ""


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
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported runtime evidence material")


def _material(value: ProductionPreExecutionAuthorizationRuntimeEvidence) -> tuple[Any, ...]:
    return tuple(
        getattr(value, field.name)
        for field in fields(value)
        if field.name != "runtime_evidence_digest"
    )


def _sha(material: Any) -> str:
    encoded = json.dumps(
        _canonical((
            READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_VERSION,
            "RUNTIME_EVIDENCE",
            material,
        )),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _authority_false(value: Any) -> bool:
    return is_dataclass(value) and not isinstance(value, type) and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False
        for field in fields(value)
    )


def create_production_pre_execution_authorization_runtime_evidence(
    context: Any,
    reference_time: Any,
    gate_evaluation: Any,
    evidence_envelope: Any,
    activation_binding: Any,
) -> ProductionPreExecutionAuthorizationRuntimeEvidence | None:
    """Create one immutable observation from the five canonical foundations."""
    try:
        request = create_production_pre_execution_authorization_request(
            context, reference_time, gate_evaluation, evidence_envelope, activation_binding
        )
        if request is None:
            return None
        decision = evaluate_production_pre_execution_authorization(request)
        if decision is None:
            return None
        authority = ProductionPreExecutionAuthorizationRuntimeAuthorityBoundary()
        draft = ProductionPreExecutionAuthorizationRuntimeEvidence(
            READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_VERSION,
            READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_SCOPE,
            request,
            decision,
            request.request_id,
            request.request_digest,
            decision.decision_digest,
            context.conversation_id,
            context.turn_id,
            context.turn_ordinal,
            context.turn_digest,
            context.user_message_digest,
            reference_time.reference_time_digest,
            gate_evaluation.evaluation_digest,
            evidence_envelope.envelope_digest,
            activation_binding.binding_digest,
            decision.selected_skill_id,
            decision.decision_status,
            decision.denial_code,
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
            False,
            authority,
        )
        return replace(draft, runtime_evidence_digest=_sha(_material(draft)))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_pre_execution_authorization_runtime_evidence(value: Any) -> bool:
    """Strictly recompute the passive wrapper and reject substitutions or authority."""
    try:
        if (
            type(value) is not ProductionPreExecutionAuthorizationRuntimeEvidence
            or value.version != READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_VERSION
            or value.scope != READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_SCOPE
            or value.authorization_request.version != PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION
            or value.authorization_request.scope != PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE
            or value.observed_decision.version != PRODUCTION_PRE_EXECUTION_AUTHORIZATION_VERSION
            or value.observed_decision.scope != PRODUCTION_PRE_EXECUTION_AUTHORIZATION_SCOPE
            or _HEX.fullmatch(value.runtime_evidence_digest or "") is None
            or value.execute_allowed is not False
            or value.executable_request is not None
            or value.controlled_response_candidate is not None
            or not _authority_false(value.authority_boundary)
            or any(getattr(value, field.name) is not False for field in fields(value)
                   if field.name.endswith("_permitted"))
            or not verify_production_pre_execution_authorization_request(value.authorization_request)
            or not verify_production_pre_execution_authorization_decision(
                value.authorization_request, value.observed_decision
            )
        ):
            return False
        request = value.authorization_request
        decision = value.observed_decision
        parity = (
            value.request_id == request.request_id
            and value.request_digest == request.request_digest
            and value.decision_digest == decision.decision_digest
            and (value.conversation_id, value.turn_id, value.turn_ordinal,
                 value.turn_digest, value.user_message_digest)
            == (request.turn_context.conversation_id, request.turn_context.turn_id,
                request.turn_context.turn_ordinal, request.turn_context.turn_digest,
                request.turn_context.user_message_digest)
            and value.reference_time_digest == request.reference_time.reference_time_digest
            and value.feature_gate_evaluation_digest == request.feature_gate_evaluation.evaluation_digest
            and value.envelope_digest == request.skill_evidence_envelope.envelope_digest
            and value.activation_binding_digest == request.limited_activation_binding.binding_digest
            and value.selected_skill_id == decision.selected_skill_id
            and value.decision_status == decision.decision_status
            and value.denial_code == decision.denial_code
            and value.execute_allowed == decision.execute_allowed is False
            and decision.executable_request is None
            and decision.controlled_response_candidate is None
        )
        if not parity or value.runtime_evidence_digest != _sha(_material(value)):
            return False
        expected = create_production_pre_execution_authorization_runtime_evidence(
            request.turn_context,
            request.reference_time,
            request.feature_gate_evaluation,
            request.skill_evidence_envelope,
            request.limited_activation_binding,
        )
        return expected is not None and value == expected
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def resolve_production_pre_execution_authorization_runtime_evidence(
    context: Any,
    reference_time: Any,
    gate_evaluation: Any,
    evidence_envelope: Any,
    activation_binding: Any,
    current_evidence: Any = None,
) -> ProductionPreExecutionAuthorizationRuntimeEvidence | None:
    """Reuse exact verified evidence, replace mismatches, and contain failures."""
    try:
        if verify_production_pre_execution_authorization_runtime_evidence(current_evidence):
            request = current_evidence.authorization_request
            if (
                request.turn_context is context
                and request.reference_time is reference_time
                and request.feature_gate_evaluation is gate_evaluation
                and request.skill_evidence_envelope is evidence_envelope
                and request.limited_activation_binding is activation_binding
            ):
                return current_evidence
        return create_production_pre_execution_authorization_runtime_evidence(
            context, reference_time, gate_evaluation, evidence_envelope, activation_binding
        )
    except Exception:
        return None


__all__ = (
    "READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_VERSION",
    "READ_ONLY_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_RUNTIME_SCOPE",
    "ProductionPreExecutionAuthorizationRuntimeAuthorityBoundary",
    "ProductionPreExecutionAuthorizationRuntimeEvidence",
    "create_production_pre_execution_authorization_runtime_evidence",
    "verify_production_pre_execution_authorization_runtime_evidence",
    "resolve_production_pre_execution_authorization_runtime_evidence",
)
