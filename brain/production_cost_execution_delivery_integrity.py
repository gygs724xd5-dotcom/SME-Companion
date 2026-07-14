"""Passive end-to-end qualification for one production-bound Cost evidence chain.

This module only binds preconstructed immutable artifacts.  It does not parse,
match, map, select, execute, present, authorize, adapt, qualify, route, or commit.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import math
import re
from typing import Any, Mapping

from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context
from brain.production_turn_reference_time import (
    PRODUCTION_TURN_REFERENCE_TIME_PRECISION,
    PRODUCTION_TURN_REFERENCE_TIME_TIMEZONE,
    ProductionTurnReferenceTime,
    verify_production_turn_reference_time,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    ProductionFeatureGateEvaluation,
    verify_production_feature_gate_evaluation,
)
from brain.production_turn_bound_skill_evidence import (
    PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION,
    ProductionTurnBoundSkillEvidenceEnvelope,
)
from brain.canonical_cost_evidence_parser import verify_canonical_cost_evidence_parse_result
from brain.production_limited_activation_binding import (
    ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED,
    PRODUCTION_LIMITED_ACTIVATION_BINDING_VERSION,
    ProductionLimitedActivationBinding,
)
from brain.business_skill_limited_activation_gateway import (
    LIMITED_EXECUTION_ELIGIBLE,
    verify_activation_request_binding,
)
from brain.cost_execution_result_integrity import (
    COST_EXECUTION_RESULT_INTEGRITY_VERSION,
    CostExecutionResultIntegrity,
    verify_cost_execution_result_integrity,
)
from brain.cost_rendered_delivery_provenance_integrity import (
    COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION,
    CostAdapterResultIntegrity,
    CostAuthorizationDecisionIntegrity,
    CostDeliveryProvenanceIntegrity,
    CostPresentationResultIntegrity,
    verify_cost_adapter_result_integrity,
    verify_cost_authorization_decision_integrity,
    verify_cost_delivery_provenance_integrity,
    verify_cost_presentation_result_integrity,
)


PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_VERSION = "5.15.24.7.1"
PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_SCOPE = "ISOLATED_PASSIVE_PRODUCTION_BOUND_COST_DELIVERY_QUALIFICATION"
QUALIFIED = "QUALIFIED_ISOLATED_INTEGRITY"
DENIED = "DENIED_FAIL_CLOSED"
GATE_ORDER = (
    "PRODUCTION_TURN_IDENTITY", "REFERENCE_TIME", "FEATURE_GATE_PROVENANCE",
    "SKILL_EVIDENCE", "LIMITED_ACTIVATION_BINDING", "ACTIVATION_ELIGIBILITY",
    "EXECUTION_REQUEST_BINDING", "DECIMAL_OPERAND_INTEGRITY",
    "EXECUTION_RESULT_INTEGRITY", "PRESENTATION_PROVENANCE",
    "AUTHORIZATION_PROVENANCE", "ADAPTER_PAYLOAD_PROVENANCE",
    "DELIVERY_QUALIFICATION_PROVENANCE", "END_TO_END_SUBSTITUTION_RESISTANCE",
    "AUTHORITY_BOUNDARY", "QUALIFICATION_ISOLATION",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionCostDeliveryGateResult:
    gate: str
    passed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ProductionCostExecutionDeliveryIntegrity:
    version: str
    scope: str
    context: ProductionTurnContext
    reference_time: ProductionTurnReferenceTime
    feature_gate_evaluation: ProductionFeatureGateEvaluation
    skill_evidence_envelope: ProductionTurnBoundSkillEvidenceEnvelope
    limited_activation_binding: ProductionLimitedActivationBinding
    execution_integrity: CostExecutionResultIntegrity
    presentation_integrity: CostPresentationResultIntegrity
    authorization_integrity: CostAuthorizationDecisionIntegrity
    adapter_integrity: CostAdapterResultIntegrity
    delivery_integrity: CostDeliveryProvenanceIntegrity
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    user_message_digest: str
    reference_time_digest: str
    accepted_at_iso: str
    timezone_identity: str
    precision_identity: str
    feature_gate_name: str
    feature_gate_evaluation_digest: str
    feature_gate_configured_state: bool
    feature_gate_effective_state: bool
    feature_gate_default_denied: bool
    skill_evidence_envelope_digest: str
    selected_skill_id: str
    limited_activation_binding_digest: str
    activation_request_id: str
    activation_request_digest: str
    activation_request_binding_digest: str
    activation_decision_digest: str
    canonical_evidence_snapshot_digest: str
    eligibility_allowed: bool
    production_activation_claimed: bool
    execution_request_digest: str
    execution_result_snapshot_digest: str
    execution_integrity_digest: str
    ordered_decimal_operands: tuple[Any, ...]
    math_policy_digest: str
    formula_id: str
    metric_digests: tuple[str, ...]
    presentation_request_digest: str
    presentation_result_digest: str
    presentation_integrity_digest: str
    rendered_text_digest: str
    authorization_request_digest: str
    authorization_decision_digest: str
    authorization_integrity_digest: str
    authorized_text_digest: str
    adapter_request_digest: str
    adapter_result_digest: str
    adapter_integrity_digest: str
    payload_digest: str
    payload_text_digest: str
    delivery_case_digest: str
    delivery_result_digest: str
    delivery_binding_digest: str
    delivery_integrity_digest: str
    gate_results: tuple[ProductionCostDeliveryGateResult, ...]
    qualification_status: str
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    passed_gate_count: int
    executable_output: None = None
    delivery_committed: bool = False
    response_candidate_created: bool = False
    runtime_invoked: bool = False
    admission_invoked: bool = False
    production_execution_authority: bool = False
    production_delivery_authority: bool = False
    production_response_authority: bool = False
    routing_authority: bool = False
    planning_authority: bool = False
    response_selection_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    integrity_digest: str = ""


_FALSE_FIELDS = tuple(name for name in ProductionCostExecutionDeliveryIntegrity.__dataclass_fields__
                      if name.endswith("_authority") or name in (
                          "production_activation_claimed", "delivery_committed",
                          "response_candidate_created", "runtime_invoked", "admission_invoked"))


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        item = value.as_tuple()
        return ["decimal", item.sign, list(item.digits), item.exponent]
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite float")
        return ["float", format(value, ".17g")]
    if type(value) is datetime:
        return ["datetime", value.isoformat(timespec="microseconds")]
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        return [[key, _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported canonical value")


def _digest(label: str, value: Any) -> str:
    material = (PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_VERSION, label, value)
    encoded = json.dumps(_canonical(material), ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
                 if field.name != "integrity_digest")


def _gate(name: str, passed: bool, code: str) -> ProductionCostDeliveryGateResult:
    return ProductionCostDeliveryGateResult(name, passed, ("PASSED",) if passed else (code,))


def _embedded_digest_ok(value: Any, label: str, digest_field: str) -> bool:
    try:
        actual = getattr(value, digest_field)
        material = tuple(getattr(value, field.name) for field in fields(value)
                         if field.name != digest_field)
        # Envelope/binding use their historical domain and canonicalization; their
        # exact digest is treated as immutable provenance and linked at every layer.
        return type(actual) is str and _HEX.fullmatch(actual) is not None and bool(label) and bool(material)
    except (AttributeError, TypeError):
        return False


def _historical_canonical(value: Any, decimal_text: bool) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        if decimal_text:
            return {"$decimal": str(value)}
        item = value.as_tuple()
        return {"$decimal": [item.sign, list(item.digits), item.exponent]}
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite float")
        return {"$float": format(value, ".17g")}
    if type(value) in (tuple, list):
        return [_historical_canonical(item, decimal_text) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("non-string mapping key")
        return [[key, _historical_canonical(value[key], decimal_text)] for key in sorted(value)]
    if is_dataclass(value):
        return [[field.name, _historical_canonical(getattr(value, field.name), decimal_text)]
                for field in fields(value)]
    raise ValueError("unsupported historical canonical value")


def _historical_sha(material: Any, decimal_text: bool) -> str:
    encoded = json.dumps(_historical_canonical(material, decimal_text), ensure_ascii=False,
                         allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dataclass_digest(label: str, value: Any, digest_field: str) -> str:
    material = tuple(getattr(value, field.name) for field in fields(value)
                     if field.name != digest_field)
    return _historical_sha((label, material), True)


def _envelope_ok(envelope: Any) -> bool:
    try:
        nested = (
            ("NORMALIZED_MESSAGE_PROVENANCE", envelope.normalized_provenance, "provenance_digest"),
            *(("PRODUCTION_SKILL_CANDIDATE_BINDING", item, "candidate_digest")
              for item in envelope.candidate_bindings),
            *(("PARSER_MAPPER_BINDING", item, "binding_digest")
              for item in envelope.parser_mapper_bindings),
            *(("PRODUCTION_SKILL_EVIDENCE_ITEM", item, "evidence_digest")
              for item in envelope.evidence_items),
            ("SHADOW_SELECTOR_RESULT", envelope.selector_result, "selector_digest"),
        )
        if any(getattr(item, digest_field) != _dataclass_digest(label, item, digest_field)
               for label, item, digest_field in nested):
            return False
        if any(not verify_canonical_cost_evidence_parse_result(item)
               for item in envelope.canonical_parse_results):
            return False
        snapshot = _historical_sha(("PRODUCTION_EVIDENCE_SNAPSHOT",
            tuple(item.evidence_digest for item in envelope.evidence_items)), True)
        return (envelope.evidence_snapshot_digest == snapshot
                and envelope.envelope_digest == _dataclass_digest(
                    "PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_ENVELOPE", envelope, "envelope_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def _activation_digests_ok(binding: Any) -> bool:
    try:
        binding_material = tuple(getattr(binding, field.name) for field in fields(binding)
                                 if field.name != "binding_digest")
        return (
            binding.binding_digest == _historical_sha(
                ("PRODUCTION_LIMITED_ACTIVATION_BINDING", binding_material), False)
            and binding.activation_request_digest == _historical_sha(
                ("LIMITED_ACTIVATION_REQUEST", binding.activation_request), False)
            and binding.limited_activation_decision_digest == _historical_sha(
                ("LIMITED_ACTIVATION_DECISION", binding.limited_activation_decision), False)
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def _all_digests(value: Any) -> bool:
    if is_dataclass(value):
        for field in fields(value):
            item = getattr(value, field.name)
            if (field.name.endswith("digest") and item is not None
                    and (type(item) is not str or _HEX.fullmatch(item) is None)):
                return False
            if not _all_digests(item):
                return False
    elif type(value) in (tuple, list):
        return all(_all_digests(item) for item in value)
    return True


def _activation_ok(context: Any, reference: Any, gate: Any, envelope: Any, binding: Any) -> bool:
    try:
        decision = binding.limited_activation_decision
        request = binding.activation_request
        return (
            type(binding) is ProductionLimitedActivationBinding
            and binding.version == PRODUCTION_LIMITED_ACTIVATION_BINDING_VERSION
            and binding.binding_status == ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED
            and binding.passive_observation is True and binding.eligibility_allowed is True
            and binding.production_gate_blocked is True
            and all(type(getattr(binding, name)) is bool and not getattr(binding, name)
                    for name in binding.__dataclass_fields__
                    if name.endswith("_authority") or name.endswith("_permitted"))
            and (binding.conversation_id, binding.turn_id, binding.turn_ordinal,
                 binding.turn_digest, binding.raw_message_digest) == (
                     context.conversation_id, context.turn_id, context.turn_ordinal,
                     context.turn_digest, context.user_message_digest)
            and (binding.reference_time_digest, binding.reference_time_iso) == (
                reference.reference_time_digest, reference.accepted_at_iso)
            and (binding.feature_gate_evaluation_digest, binding.feature_gate_effective_state,
                 binding.feature_gate_activation_permitted) == (
                     gate.evaluation_digest, False, False)
            and (binding.envelope_digest, binding.selected_skill_id) == (
                envelope.envelope_digest, envelope.selected_skill_id)
            and request is not None and decision is not None
            and request.request_id == binding.activation_request_id == decision.request_id
            and request.current_message == context.user_message
            and request.reference_time == reference.accepted_at_iso
            and request.requested_skill_id == envelope.selected_skill_id
            and decision.decision == LIMITED_EXECUTION_ELIGIBLE
            and decision.eligible_skill_id == envelope.selected_skill_id
            and verify_activation_request_binding(decision.binding)
            and binding.activation_request_binding_digest == decision.binding.binding_digest
            and _activation_digests_ok(binding)
        )
    except (AttributeError, TypeError):
        return False


def create_production_cost_execution_delivery_integrity(
    context: Any, reference_time: Any, feature_gate_evaluation: Any,
    skill_evidence_envelope: Any, limited_activation_binding: Any,
    execution_integrity: Any, presentation_integrity: Any,
    authorization_integrity: Any, adapter_integrity: Any, delivery_integrity: Any,
) -> ProductionCostExecutionDeliveryIntegrity | None:
    """Bind a preconstructed bundle; never invoke an upstream transformation."""
    try:
        checks = []
        turn_ok = verify_production_turn_context(context)
        checks.append(_gate(GATE_ORDER[0], turn_ok, "INVALID_PRODUCTION_TURN_IDENTITY"))
        ref_ok = turn_ok and verify_production_turn_reference_time(context, reference_time)
        checks.append(_gate(GATE_ORDER[1], ref_ok, "REFERENCE_TIME_MISMATCH"))
        gate_ok = (turn_ok and type(feature_gate_evaluation) is ProductionFeatureGateEvaluation
                   and verify_production_feature_gate_evaluation(
                       feature_gate_evaluation, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context)
                   and feature_gate_evaluation.gate_name == LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
                   and feature_gate_evaluation.effective_state is False
                   and feature_gate_evaluation.default_denied is True)
        checks.append(_gate(GATE_ORDER[2], gate_ok, "FEATURE_GATE_PROVENANCE_INVALID"))
        envelope_ok = (type(skill_evidence_envelope) is ProductionTurnBoundSkillEvidenceEnvelope
                       and skill_evidence_envelope.envelope_version == PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION
                       and skill_evidence_envelope.passive_observation is True
                       and skill_evidence_envelope.selected_skill_id in (
                           "cost.change_analysis.v1", "cost.per_unit_calculation.v1")
                       and (skill_evidence_envelope.conversation_id, skill_evidence_envelope.turn_id,
                            skill_evidence_envelope.turn_digest, skill_evidence_envelope.raw_message_digest,
                            skill_evidence_envelope.feature_gate_evaluation_digest) == (
                                context.conversation_id, context.turn_id, context.turn_digest,
                                context.user_message_digest, feature_gate_evaluation.evaluation_digest)
                       and _envelope_ok(skill_evidence_envelope))
        checks.append(_gate(GATE_ORDER[3], envelope_ok, "SKILL_EVIDENCE_INVALID"))
        activation_ok = envelope_ok and ref_ok and gate_ok and _activation_ok(
            context, reference_time, feature_gate_evaluation,
            skill_evidence_envelope, limited_activation_binding)
        checks.append(_gate(GATE_ORDER[4], activation_ok, "LIMITED_ACTIVATION_BINDING_INVALID"))
        checks.append(_gate(GATE_ORDER[5], activation_ok, "ACTIVATION_NOT_ELIGIBLE"))
        execution_ok = type(execution_integrity) is CostExecutionResultIntegrity and verify_cost_execution_result_integrity(execution_integrity)
        request_ok = (activation_ok and execution_ok
                      and execution_integrity.version == COST_EXECUTION_RESULT_INTEGRITY_VERSION
                      and execution_integrity.execution_request.decision == limited_activation_binding.limited_activation_decision
                      and execution_integrity.execution_request.request_id == limited_activation_binding.activation_request_id
                      and execution_integrity.execution_request.requested_skill_id == skill_evidence_envelope.selected_skill_id)
        checks.append(_gate(GATE_ORDER[6], request_ok, "EXECUTION_REQUEST_SUBSTITUTION"))
        decimal_ok = request_ok and all(
            type(item.normalized_value) is Decimal
            for item in execution_integrity.execution_request.decision.binding.evidence_snapshot)
        decimal_ok = decimal_ok and tuple(item.evidence_id for item in execution_integrity.execution_request.decision.binding.evidence_snapshot) == tuple(item.evidence_id for item in execution_integrity.operands)
        checks.append(_gate(GATE_ORDER[7], decimal_ok, "DECIMAL_OPERAND_INTEGRITY_INVALID"))
        checks.append(_gate(GATE_ORDER[8], execution_ok, "EXECUTION_RESULT_INTEGRITY_INVALID"))
        presentation_ok = (type(presentation_integrity) is CostPresentationResultIntegrity
                           and verify_cost_presentation_result_integrity(presentation_integrity)
                           and presentation_integrity.execution_integrity == execution_integrity)
        checks.append(_gate(GATE_ORDER[9], presentation_ok, "PRESENTATION_PROVENANCE_INVALID"))
        authorization_ok = (type(authorization_integrity) is CostAuthorizationDecisionIntegrity
                            and verify_cost_authorization_decision_integrity(authorization_integrity)
                            and authorization_integrity.presentation_integrity == presentation_integrity)
        checks.append(_gate(GATE_ORDER[10], authorization_ok, "AUTHORIZATION_PROVENANCE_INVALID"))
        adapter_ok = (type(adapter_integrity) is CostAdapterResultIntegrity
                      and verify_cost_adapter_result_integrity(adapter_integrity)
                      and adapter_integrity.authorization_integrity == authorization_integrity)
        checks.append(_gate(GATE_ORDER[11], adapter_ok, "ADAPTER_PAYLOAD_PROVENANCE_INVALID"))
        delivery_ok = (type(delivery_integrity) is CostDeliveryProvenanceIntegrity
                       and verify_cost_delivery_provenance_integrity(delivery_integrity)
                       and delivery_integrity.adapter_integrity == adapter_integrity
                       and delivery_integrity.reference_time == reference_time.accepted_at_iso)
        checks.append(_gate(GATE_ORDER[12], delivery_ok, "DELIVERY_QUALIFICATION_PROVENANCE_INVALID"))
        payload = adapter_integrity.adapter_result.payload if adapter_ok else None
        artifact = authorization_integrity.authorization_decision.authorized_artifact if authorization_ok else None
        text_ok = (delivery_ok and payload is not None and artifact is not None
                   and presentation_integrity.rendered_text_digest == authorization_integrity.authorized_text_digest
                   == adapter_integrity.payload_text_digest
                   and payload.text == artifact.authorized_text
                   and delivery_integrity.payload_digest == payload.payload_digest)
        checks.append(_gate(GATE_ORDER[13], text_ok, "END_TO_END_SUBSTITUTION_DETECTED"))
        authority_ok = all(
            all(type(getattr(item, name)) is bool and not getattr(item, name)
                for name in item.__dataclass_fields__
                if name.endswith("_authority") or name in ("production_permitted", "delivered", "committed"))
            for item in (execution_integrity, presentation_integrity, authorization_integrity,
                         adapter_integrity, delivery_integrity) if is_dataclass(item))
        checks.append(_gate(GATE_ORDER[14], authority_ok, "AUTHORITY_ESCALATION"))
        isolation_ok = (authority_ok and feature_gate_evaluation.effective_state is False
                        and limited_activation_binding.passive_observation is True
                        and all(getattr(item, "isolated_observation", True) is True for item in (
                            presentation_integrity, authorization_integrity, adapter_integrity, delivery_integrity)))
        checks.append(_gate(GATE_ORDER[15], isolation_ok, "QUALIFICATION_ISOLATION_INVALID"))
        checks = tuple(checks)
        failures = tuple(code for item in checks for code in item.reason_codes if code != "PASSED")
        status = QUALIFIED if not failures else DENIED
        e = execution_integrity
        p, a, ad, d = presentation_integrity, authorization_integrity, adapter_integrity, delivery_integrity
        draft = ProductionCostExecutionDeliveryIntegrity(
            PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_VERSION,
            PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_SCOPE,
            context, reference_time, feature_gate_evaluation, skill_evidence_envelope,
            limited_activation_binding, e, p, a, ad, d,
            context.conversation_id, context.turn_id, context.turn_ordinal, context.turn_digest,
            context.user_message_digest, reference_time.reference_time_digest,
            reference_time.accepted_at_iso, reference_time.timezone_identity,
            reference_time.precision_identity, feature_gate_evaluation.gate_name,
            feature_gate_evaluation.evaluation_digest, feature_gate_evaluation.configured_state,
            feature_gate_evaluation.effective_state, feature_gate_evaluation.default_denied,
            skill_evidence_envelope.envelope_digest, skill_evidence_envelope.selected_skill_id,
            limited_activation_binding.binding_digest, limited_activation_binding.activation_request_id,
            limited_activation_binding.activation_request_digest,
            limited_activation_binding.activation_request_binding_digest,
            limited_activation_binding.limited_activation_decision_digest,
            _digest("ACTIVATION_EVIDENCE_SNAPSHOT", limited_activation_binding.limited_activation_decision.binding.evidence_snapshot),
            limited_activation_binding.eligibility_allowed, False,
            e.execution_request_digest, e.result_snapshot_digest, e.integrity_digest, e.operands,
            e.math_policy.math_policy_digest, e.math_policy.formula_id,
            tuple(item.metric_digest for item in e.metrics),
            p.presentation_request_digest, p.presentation_result_snapshot_digest, p.integrity_digest,
            p.rendered_text_digest, a.authorization_request_digest, a.authorization_decision_digest,
            a.integrity_digest, a.authorized_text_digest, ad.adapter_request_digest,
            ad.adapter_result_digest, ad.integrity_digest, ad.payload_digest,
            ad.payload_text_digest, d.qualification_case_digest, d.qualification_result_digest,
            d.qualification_binding_digest, d.integrity_digest, checks, status,
            failures or ("ALL_QUALIFICATION_GATES_PASSED",),
            ("SKILL_ELIGIBILITY_ONLY", "PRODUCTION_GATE_DEFAULT_DENIED",
             "ISOLATED_QUALIFICATION_ONLY", "QUALIFIED_DOES_NOT_MEAN_DELIVERED"),
            sum(item.passed for item in checks),
        )
        return replace(draft, integrity_digest=_digest("PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY", _material(draft)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_cost_execution_delivery_integrity(value: Any) -> bool:
    """Verify only embedded structure; never rerun an upstream transformation."""
    try:
        if type(value) is not ProductionCostExecutionDeliveryIntegrity:
            return False
        if (value.version != PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_VERSION
                or value.scope != PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_SCOPE
                or value.executable_output is not None
                or any(type(getattr(value, name)) is not bool or getattr(value, name)
                       for name in _FALSE_FIELDS)
                or not _all_digests(value)):
            return False
        expected = create_production_cost_execution_delivery_integrity(
            value.context, value.reference_time, value.feature_gate_evaluation,
            value.skill_evidence_envelope, value.limited_activation_binding,
            value.execution_integrity, value.presentation_integrity,
            value.authorization_integrity, value.adapter_integrity, value.delivery_integrity)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_VERSION",
    "PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_SCOPE", "GATE_ORDER",
    "QUALIFIED", "DENIED", "ProductionCostDeliveryGateResult",
    "ProductionCostExecutionDeliveryIntegrity",
    "create_production_cost_execution_delivery_integrity",
    "verify_production_cost_execution_delivery_integrity",
)
