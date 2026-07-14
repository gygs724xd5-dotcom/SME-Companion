"""Passive production binding for a limited-activation eligibility decision."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.business_skill_lifecycle_manifest import BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION
from brain.business_skill_limited_activation_gateway import (
    LIMITED_ACTIVATION_GATEWAY_VERSION,
    LIMITED_EXECUTION_DENIED,
    LIMITED_EXECUTION_ELIGIBLE,
    SUPPORTED_ACTIVATION_SCOPE,
    ActivationRequestBinding,
    LimitedActivationDecision,
    LimitedActivationRequest,
    decide_limited_activation,
    verify_activation_request_binding,
)
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    ProductionFeatureGateEvaluation,
    verify_production_feature_gate_evaluation,
)
from brain.production_turn_bound_skill_evidence import (
    PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION,
    ProductionTurnBoundSkillEvidenceEnvelope,
    convert_verified_cost_parse_result_to_mapper_evidence,
    verify_production_turn_bound_skill_evidence_envelope,
)
from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context
from brain.production_turn_reference_time import (
    PRODUCTION_TURN_REFERENCE_TIME_VERSION,
    ProductionTurnReferenceTime,
    verify_production_turn_reference_time,
)


PRODUCTION_LIMITED_ACTIVATION_BINDING_VERSION = "5.15.24.7"
PRODUCTION_LIMITED_ACTIVATION_BINDING_SCOPE = "VERIFIED_TURN_LIMITED_ACTIVATION_DECISION"

NOT_APPLICABLE = "NOT_APPLICABLE"
EVIDENCE_NOT_READY = "EVIDENCE_NOT_READY"
ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED = "ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED"
ACTIVATION_DENIED = "ACTIVATION_DENIED"
INVALID = "INVALID"
ERROR_CONTAINED = "ERROR_CONTAINED"
_STATUSES = (NOT_APPLICABLE, EVIDENCE_NOT_READY,
             ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED, ACTIVATION_DENIED,
             INVALID, ERROR_CONTAINED)
_HEX = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_ID = re.compile(r"^production-limited-activation-[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionLimitedActivationBinding:
    version: str
    scope: str
    registry_version: str
    lifecycle_version: str
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    raw_message_digest: str
    normalized_message_digest: str
    reference_time_version: str
    reference_time_digest: str
    reference_time_iso: str
    feature_gate_evaluation_digest: str
    feature_gate_effective_state: bool
    feature_gate_activation_permitted: bool
    envelope_version: str
    envelope_digest: str
    selected_skill_id: str | None
    selected_candidate_digest: str | None
    selected_parser_digest: str | None
    selected_mapper_binding_digest: str | None
    selected_selector_digest: str
    activation_request_id: str | None
    activation_request: LimitedActivationRequest | None
    activation_request_digest: str | None
    activation_request_binding_digest: str | None
    limited_activation_decision: LimitedActivationDecision | None
    limited_activation_decision_digest: str | None
    gateway_version: str
    gateway_scope: str
    gateway_policy_identity: str
    eligibility_allowed: bool
    production_gate_blocked: bool
    binding_status: str
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    passive_observation: bool = True
    execution_permitted: bool = False
    delivery_permitted: bool = False
    bridge_permitted: bool = False
    admission_permitted: bool = False
    routing_authority: bool = False
    planning_authority: bool = False
    response_selection_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    limited_activation_authority: bool = False
    delivery_preparation_authority: bool = False
    bridge_request_authority: bool = False
    admission_authority: bool = False
    controlled_runtime_activation_authority: bool = False
    binding_digest: str = ""


_FALSE_FIELDS = tuple(
    name for name in ProductionLimitedActivationBinding.__dataclass_fields__
    if name.endswith("_authority") or name.endswith("_permitted")
)


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
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("non-string mapping key")
        return [[key, _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported canonical value")


def _sha256(material: Any) -> str:
    encoded = json.dumps(_canonical(material), ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def derive_production_activation_request_id(
    context: ProductionTurnContext,
    reference_time: ProductionTurnReferenceTime,
    envelope: ProductionTurnBoundSkillEvidenceEnvelope,
) -> str:
    material = (
        "PRODUCTION_LIMITED_ACTIVATION_REQUEST_ID",
        PRODUCTION_LIMITED_ACTIVATION_BINDING_VERSION,
        context.conversation_id,
        context.turn_id,
        context.turn_digest,
        reference_time.reference_time_digest,
        envelope.envelope_digest,
        envelope.selected_skill_id,
    )
    return "production-limited-activation-" + _sha256(material)


def _selected_index(envelope: ProductionTurnBoundSkillEvidenceEnvelope) -> int | None:
    if envelope.selected_skill_id is None:
        return None
    matches = tuple(i for i, item in enumerate(envelope.candidate_bindings)
                    if item.skill_id == envelope.selected_skill_id)
    return matches[0] if len(matches) == 1 else None


def _request(context: ProductionTurnContext, reference_time: ProductionTurnReferenceTime,
             envelope: ProductionTurnBoundSkillEvidenceEnvelope, index: int) -> LimitedActivationRequest:
    parse = envelope.canonical_parse_results[index]
    evidence = convert_verified_cost_parse_result_to_mapper_evidence(parse)
    return LimitedActivationRequest(
        derive_production_activation_request_id(context, reference_time, envelope),
        context.user_message,
        evidence,
        reference_time.accepted_at_iso,
        envelope.selected_skill_id,
        SUPPORTED_ACTIVATION_SCOPE,
        LIMITED_ACTIVATION_GATEWAY_VERSION,
        (),
    )


def _decision_is_passive_and_well_formed(decision: Any, request: LimitedActivationRequest,
                                         envelope: ProductionTurnBoundSkillEvidenceEnvelope,
                                         index: int) -> bool:
    if type(decision) is not LimitedActivationDecision:
        return False
    if (decision.request_id != request.request_id
            or decision.requested_skill_id != envelope.selected_skill_id
            or decision.registry_version != BUSINESS_SKILL_REGISTRY_VERSION
            or decision.policy_version != LIMITED_ACTIVATION_GATEWAY_VERSION):
        return False
    authority = ("executed", "calculated", "reasoning_executed", "runtime_routed",
                 "tools_invoked", "persisted", "follow_up_generated",
                 "response_generated", "response_committed")
    if any(type(getattr(decision, name)) is not bool or getattr(decision, name)
           for name in authority):
        return False
    candidate = envelope.candidate_bindings[index]
    if (decision.candidate_score != candidate.candidate_score
            or decision.candidate_confidence != candidate.candidate_confidence):
        return False
    if decision.decision == LIMITED_EXECUTION_ELIGIBLE:
        return (decision.eligible_skill_id == envelope.selected_skill_id
                and decision.binding is not None
                and verify_activation_request_binding(decision.binding))
    if decision.decision == LIMITED_EXECUTION_DENIED:
        return decision.eligible_skill_id is None and decision.binding is None
    return False


def _base(context: ProductionTurnContext, reference_time: ProductionTurnReferenceTime,
          gate: ProductionFeatureGateEvaluation,
          envelope: ProductionTurnBoundSkillEvidenceEnvelope, **changes: Any
          ) -> ProductionLimitedActivationBinding:
    index = _selected_index(envelope)
    mapper_digest = (envelope.parser_mapper_bindings[index].binding_digest
                     if index is not None else None)
    values = dict(
        version=PRODUCTION_LIMITED_ACTIVATION_BINDING_VERSION,
        scope=PRODUCTION_LIMITED_ACTIVATION_BINDING_SCOPE,
        registry_version=BUSINESS_SKILL_REGISTRY_VERSION,
        lifecycle_version=BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION,
        conversation_id=context.conversation_id, turn_id=context.turn_id,
        turn_ordinal=context.turn_ordinal, turn_digest=context.turn_digest,
        raw_message_digest=context.user_message_digest,
        normalized_message_digest=envelope.normalized_provenance.normalized_message_digest,
        reference_time_version=PRODUCTION_TURN_REFERENCE_TIME_VERSION,
        reference_time_digest=reference_time.reference_time_digest,
        reference_time_iso=reference_time.accepted_at_iso,
        feature_gate_evaluation_digest=gate.evaluation_digest,
        feature_gate_effective_state=gate.effective_state,
        feature_gate_activation_permitted=gate.activation_permitted,
        envelope_version=envelope.envelope_version, envelope_digest=envelope.envelope_digest,
        selected_skill_id=envelope.selected_skill_id,
        selected_candidate_digest=envelope.selected_candidate_digest,
        selected_parser_digest=envelope.selected_parser_digest,
        selected_mapper_binding_digest=mapper_digest,
        selected_selector_digest=envelope.selector_result.selector_digest,
        activation_request_id=None, activation_request=None, activation_request_digest=None,
        activation_request_binding_digest=None, limited_activation_decision=None,
        limited_activation_decision_digest=None,
        gateway_version=LIMITED_ACTIVATION_GATEWAY_VERSION,
        gateway_scope=SUPPORTED_ACTIVATION_SCOPE,
        gateway_policy_identity=LIMITED_ACTIVATION_GATEWAY_VERSION,
        eligibility_allowed=False, production_gate_blocked=not gate.effective_state,
        binding_status=INVALID, reasons=("INVALID",), diagnostics=(),
    )
    values.update(changes)
    draft = ProductionLimitedActivationBinding(**values)
    return replace(draft, binding_digest=_sha256((
        "PRODUCTION_LIMITED_ACTIVATION_BINDING",
        tuple(getattr(draft, field.name) for field in fields(draft)
              if field.name != "binding_digest"),
    )))


def create_production_limited_activation_binding(
    context: Any, reference_time: Any, gate: Any, envelope: Any,
) -> ProductionLimitedActivationBinding | None:
    """Create passive evidence only; invalid foundations fail closed with no artifact."""
    if not verify_production_turn_context(context):
        return None
    if not verify_production_turn_reference_time(context, reference_time):
        return None
    if not verify_production_feature_gate_evaluation(
        gate, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context
    ) or gate.gate_name != LIMITED_COST_RESPONSE_RUNTIME_BRIDGE:
        return None
    if not verify_production_turn_bound_skill_evidence_envelope(envelope, context, gate):
        return None
    if envelope.envelope_version != PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION:
        return None
    index = _selected_index(envelope)
    if envelope.selected_skill_id is None:
        status = NOT_APPLICABLE if envelope.selector_result.selection_status == "NO_CANDIDATES" else EVIDENCE_NOT_READY
        return _base(context, reference_time, gate, envelope, binding_status=status,
                     reasons=(envelope.selector_result.selection_status, "GATEWAY_NOT_CALLED"),
                     diagnostics=("PASSIVE_OBSERVATION_ONLY",))
    if index is None:
        return _base(context, reference_time, gate, envelope, binding_status=INVALID,
                     reasons=("SELECTED_SKILL_CHAIN_INVALID",))
    request = _request(context, reference_time, envelope, index)
    request_digest = _sha256(("LIMITED_ACTIVATION_REQUEST", request))
    try:
        decision = decide_limited_activation(request)
    except Exception:
        return _base(
            context, reference_time, gate, envelope,
            activation_request_id=request.request_id, activation_request=request,
            activation_request_digest=request_digest, binding_status=ERROR_CONTAINED,
            reasons=("LIMITED_ACTIVATION_GATEWAY_ERROR_CONTAINED",),
            diagnostics=("PASSIVE_FAILURE_NO_RUNTIME_EFFECT",),
        )
    if not _decision_is_passive_and_well_formed(decision, request, envelope, index):
        return _base(context, reference_time, gate, envelope, binding_status=INVALID,
                     reasons=("UPSTREAM_GATEWAY_DECISION_INVALID",),
                     diagnostics=("PASSIVE_FAILURE_NO_RUNTIME_EFFECT",))
    allowed = decision.decision == LIMITED_EXECUTION_ELIGIBLE
    status = (ACTIVATION_ALLOWED_GATE_DEFAULT_DENIED if allowed and not gate.effective_state
              else ACTIVATION_DENIED)
    binding_digest = decision.binding.binding_digest if decision.binding is not None else None
    return _base(
        context, reference_time, gate, envelope,
        activation_request_id=request.request_id, activation_request=request,
        activation_request_digest=request_digest,
        activation_request_binding_digest=binding_digest,
        limited_activation_decision=decision,
        limited_activation_decision_digest=_sha256(("LIMITED_ACTIVATION_DECISION", decision)),
        eligibility_allowed=allowed,
        binding_status=status,
        reasons=tuple(decision.reason_codes),
        diagnostics=("SKILL_ELIGIBILITY_ONLY", "PRODUCTION_GATE_SEPARATELY_DEFAULT_DENIED"),
    )


def verify_production_limited_activation_binding(
    value: Any, context: Any, reference_time: Any, gate: Any, envelope: Any,
) -> bool:
    try:
        if type(value) is not ProductionLimitedActivationBinding:
            return False
        if value.version != PRODUCTION_LIMITED_ACTIVATION_BINDING_VERSION or value.scope != PRODUCTION_LIMITED_ACTIVATION_BINDING_SCOPE:
            return False
        if value.binding_status not in _STATUSES or value.passive_observation is not True:
            return False
        if any(type(getattr(value, name)) is not bool or getattr(value, name) for name in _FALSE_FIELDS):
            return False
        if not _HEX.fullmatch(value.binding_digest):
            return False
        expected = create_production_limited_activation_binding(context, reference_time, gate, envelope)
        if expected is None:
            return False
        if value.binding_status == ERROR_CONTAINED:
            # An exception is observational, so verify all deterministic material without rerunning it.
            index = _selected_index(envelope)
            if index is None:
                return False
            canonical_request = _request(context, reference_time, envelope, index)
            canonical_request_digest = _sha256(("LIMITED_ACTIVATION_REQUEST", canonical_request))
            if (value.activation_request != canonical_request
                    or value.activation_request_id != canonical_request.request_id
                    or value.activation_request_digest != canonical_request_digest
                    or value.activation_request_binding_digest is not None
                    or value.limited_activation_decision is not None
                    or value.limited_activation_decision_digest is not None):
                return False
            if expected.binding_status != ERROR_CONTAINED:
                expected = _base(
                    context, reference_time, gate, envelope,
                    activation_request_id=canonical_request.request_id,
                    activation_request=canonical_request,
                    activation_request_digest=canonical_request_digest,
                    binding_status=ERROR_CONTAINED,
                    reasons=("LIMITED_ACTIVATION_GATEWAY_ERROR_CONTAINED",),
                    diagnostics=("PASSIVE_FAILURE_NO_RUNTIME_EFFECT",),
                )
            return value == expected
        if value != expected:
            return False
        if value.activation_request is None:
            return value.activation_request_id is None and value.limited_activation_decision is None
        if not _REQUEST_ID.fullmatch(value.activation_request_id or ""):
            return False
        if value.activation_request.request_id != derive_production_activation_request_id(context, reference_time, envelope):
            return False
        if value.activation_request.current_message != context.user_message:
            return False
        decision = value.limited_activation_decision
        if type(decision) is not LimitedActivationDecision or decision.request_id != value.activation_request_id:
            return False
        if decision.decision not in (LIMITED_EXECUTION_ELIGIBLE, LIMITED_EXECUTION_DENIED):
            return False
        if decision.binding is not None:
            if type(decision.binding) is not ActivationRequestBinding or not verify_activation_request_binding(decision.binding):
                return False
            if decision.binding.current_message != context.user_message.strip():
                return False
        return True
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def resolve_production_limited_activation_binding(
    current: Any, context: Any, reference_time: Any, gate: Any, envelope: Any,
) -> ProductionLimitedActivationBinding | None:
    """Reuse only an exact verified binding for the same immutable foundations."""
    expected = create_production_limited_activation_binding(context, reference_time, gate, envelope)
    if expected is None:
        return None
    if verify_production_limited_activation_binding(current, context, reference_time, gate, envelope) and current == expected:
        return current
    return expected
