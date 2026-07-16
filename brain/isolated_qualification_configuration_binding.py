"""Isolated gate-enabled qualification foundations with zero production authority.

This module deliberately does not widen any production builder or verifier.  It
reuses their deterministic material builders behind distinct, strictly verified
types whose only purpose is the fixed 7.4.9.1 qualification foundation.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from collections.abc import Mapping
from typing import Any

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    PURE_TEST_TRUSTED_SOURCE_IDENTITY,
    ProductionFeatureGateConfiguration,
    ProductionFeatureGateEvaluation,
    verify_production_feature_gate_configuration,
    verify_production_feature_gate_evaluation,
)
from brain.production_feature_gate_release_owner import (
    ProductionFeatureGateReleaseOwnerSnapshot,
    get_production_feature_gate_release_owner,
    verify_production_feature_gate_release_owner,
)
from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context
from brain.production_turn_reference_time import (
    ProductionTurnReferenceTime, verify_production_turn_reference_time,
)
from brain.production_turn_bound_skill_evidence import (
    ProductionTurnBoundSkillEvidenceEnvelope, _build as _build_evidence,
)
from brain.production_limited_activation_binding import (
    ACTIVATION_DENIED, ERROR_CONTAINED, EVIDENCE_NOT_READY, INVALID, NOT_APPLICABLE,
    ProductionLimitedActivationBinding, _base as _binding_base,
    _decision_is_passive_and_well_formed, _request as _activation_request,
    _selected_index,
)
from brain.business_skill_limited_activation_gateway import (
    LIMITED_EXECUTION_ELIGIBLE, decide_limited_activation,
)


ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_VERSION = "5.15.24.7.4.9.1"
ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_SCOPE = "ISOLATED_GATE_ENABLED_QUALIFICATION_CONFIGURATION_FOUNDATION"
ISOLATED_QUALIFICATION_REQUIREMENT_IDENTITY = "GATE_ENABLED_PREAUTH_QUALIFICATION_FOUNDATION"
QUALIFICATION_EVIDENCE_SCOPE = "ISOLATED_GATE_ENABLED_SKILL_EVIDENCE_FOUNDATION"
QUALIFICATION_LIMITED_ACTIVATION_SCOPE = "ISOLATED_GATE_ENABLED_LIMITED_ACTIVATION_FOUNDATION"
QUALIFICATION_PRE_EXECUTION_SCOPE = "ISOLATED_GATE_ENABLED_PRE_EXECUTION_FOUNDATION"
FOUNDATION_BOUND = "FOUNDATION_BOUND_NOT_QUALIFIED"
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class IsolatedQualificationAuthorityBoundary:
    approval: bool = False
    transition_application: bool = False
    activation: bool = False
    mutation: bool = False
    persistence: bool = False
    production_execution: bool = False
    dispatch: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    calculator: bool = False
    delivery: bool = False
    response_replacement: bool = False
    deployment: bool = False
    rollback_execution: bool = False


@dataclass(frozen=True)
class IsolatedQualificationFeatureGateBinding:
    version: str
    scope: str
    requirement_identity: str
    gate_name: str
    turn_context: ProductionTurnContext
    reference_time: ProductionTurnReferenceTime
    configuration: ProductionFeatureGateConfiguration
    configuration_source_identity: str
    configuration_digest: str
    ordered_gate_entries: tuple[tuple[str, bool], ...]
    evaluation: ProductionFeatureGateEvaluation
    evaluation_digest: str
    configured_state: bool
    effective_state: bool
    default_denied: bool
    production_configuration_digest: str
    release_owner: ProductionFeatureGateReleaseOwnerSnapshot
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    authority_boundary: IsolatedQualificationAuthorityBoundary = IsolatedQualificationAuthorityBoundary()
    binding_digest: str = ""


@dataclass(frozen=True)
class IsolatedQualificationSkillEvidenceEnvelope:
    version: str
    scope: str
    configuration_binding: IsolatedQualificationFeatureGateBinding
    turn_context: ProductionTurnContext
    reference_time: ProductionTurnReferenceTime
    gate_evaluation: ProductionFeatureGateEvaluation
    canonical_evidence_material: ProductionTurnBoundSkillEvidenceEnvelope
    configuration_binding_digest: str
    turn_digest: str
    reference_time_digest: str
    evaluation_digest: str
    evidence_material_digest: str
    authority_boundary: IsolatedQualificationAuthorityBoundary = IsolatedQualificationAuthorityBoundary()
    envelope_digest: str = ""


@dataclass(frozen=True)
class IsolatedQualificationLimitedActivationBinding:
    version: str
    scope: str
    configuration_binding: IsolatedQualificationFeatureGateBinding
    evidence_envelope: IsolatedQualificationSkillEvidenceEnvelope
    canonical_limited_activation_material: ProductionLimitedActivationBinding
    ordered_upstream_digests: tuple[str, ...]
    lifecycle_is_not_production_activation: bool
    activation_permitted: bool = False
    application_permitted: bool = False
    authority_boundary: IsolatedQualificationAuthorityBoundary = IsolatedQualificationAuthorityBoundary()
    binding_digest: str = ""


@dataclass(frozen=True)
class IsolatedQualificationPreExecutionResult:
    version: str
    scope: str
    configuration_binding: IsolatedQualificationFeatureGateBinding
    evidence_envelope: IsolatedQualificationSkillEvidenceEnvelope
    limited_activation_binding: IsolatedQualificationLimitedActivationBinding
    ordered_input_digests: tuple[str, ...]
    gate_enabled_verified: bool
    evidence_verified: bool
    limited_activation_verified: bool
    eligibility_observed: bool
    status: str
    requirement_qualified: bool = False
    executable_request_qualified: bool = False
    execute_allowed: bool = False
    executable_request: None = None
    dispatch_permitted: bool = False
    production_application_permitted: bool = False
    runtime_invocation_permitted: bool = False
    authority_boundary: IsolatedQualificationAuthorityBoundary = IsolatedQualificationAuthorityBoundary()
    result_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal: return {"$decimal": str(value)}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping):
        if any(type(k) is not str for k in value): raise ValueError("non-string mapping key")
        return [[k, _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported qualification material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_VERSION, label, value)),
                         ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, digest_field: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != digest_field)


def _authority_false(value: Any) -> bool:
    return type(value) is IsolatedQualificationAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and getattr(value, f.name) is False for f in fields(value)
    )


def create_isolated_qualification_feature_gate_binding(context: Any, reference_time: Any,
                                                        configuration: Any, evaluation: Any
                                                        ) -> IsolatedQualificationFeatureGateBinding | None:
    try:
        owner = get_production_feature_gate_release_owner()
        if not verify_production_turn_context(context) or not verify_production_turn_reference_time(context, reference_time): return None
        if type(configuration) is not ProductionFeatureGateConfiguration or not verify_production_feature_gate_configuration(configuration): return None
        if configuration.trusted_source_identity != PURE_TEST_TRUSTED_SOURCE_IDENTITY: return None
        if configuration.gate_entries != ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),): return None
        if configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION: return None
        if not verify_production_feature_gate_evaluation(evaluation, configuration, context): return None
        if (evaluation.gate_name != LIMITED_COST_RESPONSE_RUNTIME_BRIDGE or evaluation.configured_state is not True
                or evaluation.effective_state is not True or evaluation.default_denied is not False): return None
        if not verify_production_feature_gate_release_owner(owner) or owner is not get_production_feature_gate_release_owner(): return None
        if owner.configuration is not PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION or owner.configuration.gate_entries != (): return None
        if configuration.source_digest == owner.configuration_digest: return None
        draft = IsolatedQualificationFeatureGateBinding(
            ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_VERSION, ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_SCOPE,
            ISOLATED_QUALIFICATION_REQUIREMENT_IDENTITY, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
            context, reference_time, configuration, configuration.trusted_source_identity,
            configuration.source_digest, configuration.gate_entries, evaluation, evaluation.evaluation_digest,
            True, True, False, owner.configuration_digest, owner, owner.owner_digest,
            owner.release_revision.revision_id, owner.release_revision.revision_digest,
        )
        return replace(draft, binding_digest=_digest("CONFIGURATION_BINDING", _material(draft, "binding_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_isolated_qualification_feature_gate_binding(value: Any) -> bool:
    try:
        if type(value) is not IsolatedQualificationFeatureGateBinding or not _HEX.fullmatch(value.binding_digest): return False
        if not _authority_false(value.authority_boundary): return False
        expected = create_isolated_qualification_feature_gate_binding(value.turn_context, value.reference_time,
                                                                       value.configuration, value.evaluation)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError): return False


def create_isolated_qualification_skill_evidence_envelope(binding: Any) -> IsolatedQualificationSkillEvidenceEnvelope | None:
    try:
        if not verify_isolated_qualification_feature_gate_binding(binding): return None
        evidence = _build_evidence(binding.turn_context, binding.evaluation)
        draft = IsolatedQualificationSkillEvidenceEnvelope(
            ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_VERSION, QUALIFICATION_EVIDENCE_SCOPE,
            binding, binding.turn_context, binding.reference_time, binding.evaluation, evidence,
            binding.binding_digest, binding.turn_context.turn_digest, binding.reference_time.reference_time_digest,
            binding.evaluation.evaluation_digest, evidence.envelope_digest,
        )
        return replace(draft, envelope_digest=_digest("EVIDENCE_ENVELOPE", _material(draft, "envelope_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_isolated_qualification_skill_evidence_envelope(value: Any) -> bool:
    try:
        if type(value) is not IsolatedQualificationSkillEvidenceEnvelope or not _HEX.fullmatch(value.envelope_digest): return False
        if not _authority_false(value.authority_boundary): return False
        expected = create_isolated_qualification_skill_evidence_envelope(value.configuration_binding)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError): return False


def _build_limited(value: IsolatedQualificationSkillEvidenceEnvelope) -> ProductionLimitedActivationBinding:
    c, r, g, e = value.turn_context, value.reference_time, value.gate_evaluation, value.canonical_evidence_material
    index = _selected_index(e)
    if e.selected_skill_id is None:
        status = NOT_APPLICABLE if e.selector_result.selection_status == "NO_CANDIDATES" else EVIDENCE_NOT_READY
        return _binding_base(c, r, g, e, binding_status=status,
                             reasons=(e.selector_result.selection_status, "GATEWAY_NOT_CALLED"),
                             diagnostics=("ISOLATED_QUALIFICATION_OBSERVATION_ONLY",))
    if index is None: return _binding_base(c, r, g, e, binding_status=INVALID, reasons=("SELECTED_SKILL_CHAIN_INVALID",))
    request = _activation_request(c, r, e, index)
    request_digest = hashlib.sha256(json.dumps(_canonical(("LIMITED_ACTIVATION_REQUEST", request)), ensure_ascii=False,
                                                separators=(",", ":")).encode()).hexdigest()
    try: decision = decide_limited_activation(request)
    except Exception:
        return _binding_base(c, r, g, e, activation_request_id=request.request_id, activation_request=request,
                             activation_request_digest=request_digest, binding_status=ERROR_CONTAINED,
                             reasons=("LIMITED_ACTIVATION_GATEWAY_ERROR_CONTAINED",),
                             diagnostics=("PASSIVE_FAILURE_NO_RUNTIME_EFFECT",))
    if not _decision_is_passive_and_well_formed(decision, request, e, index):
        return _binding_base(c, r, g, e, binding_status=INVALID, reasons=("UPSTREAM_GATEWAY_DECISION_INVALID",))
    allowed = decision.decision == LIMITED_EXECUTION_ELIGIBLE
    decision_digest = hashlib.sha256(json.dumps(_canonical(("LIMITED_ACTIVATION_DECISION", decision)), ensure_ascii=False,
                                                 separators=(",", ":")).encode()).hexdigest()
    return _binding_base(c, r, g, e, activation_request_id=request.request_id, activation_request=request,
                         activation_request_digest=request_digest,
                         activation_request_binding_digest=decision.binding.binding_digest if decision.binding else None,
                         limited_activation_decision=decision, limited_activation_decision_digest=decision_digest,
                         eligibility_allowed=allowed, production_gate_blocked=False, binding_status=ACTIVATION_DENIED,
                         reasons=tuple(decision.reason_codes),
                         diagnostics=("SKILL_ELIGIBILITY_ONLY", "ISOLATED_GATE_NOT_PRODUCTION_ACTIVATION"))


def create_isolated_qualification_limited_activation_binding(evidence: Any) -> IsolatedQualificationLimitedActivationBinding | None:
    try:
        if not verify_isolated_qualification_skill_evidence_envelope(evidence): return None
        material = _build_limited(evidence)
        upstream = (evidence.configuration_binding.binding_digest, evidence.envelope_digest,
                    evidence.gate_evaluation.evaluation_digest, evidence.reference_time.reference_time_digest,
                    material.binding_digest)
        draft = IsolatedQualificationLimitedActivationBinding(
            ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_VERSION, QUALIFICATION_LIMITED_ACTIVATION_SCOPE,
            evidence.configuration_binding, evidence, material, upstream, True,
        )
        return replace(draft, binding_digest=_digest("LIMITED_ACTIVATION_BINDING", _material(draft, "binding_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_isolated_qualification_limited_activation_binding(value: Any) -> bool:
    try:
        if type(value) is not IsolatedQualificationLimitedActivationBinding or not _HEX.fullmatch(value.binding_digest): return False
        if value.activation_permitted is not False or value.application_permitted is not False or not _authority_false(value.authority_boundary): return False
        expected = create_isolated_qualification_limited_activation_binding(value.evidence_envelope)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError): return False


def create_isolated_qualification_pre_execution_result(limited: Any) -> IsolatedQualificationPreExecutionResult | None:
    try:
        if not verify_isolated_qualification_limited_activation_binding(limited): return None
        e, b = limited.evidence_envelope, limited.configuration_binding
        inputs = (b.binding_digest, e.envelope_digest, limited.binding_digest,
                  b.turn_context.turn_digest, b.reference_time.reference_time_digest, b.evaluation.evaluation_digest)
        draft = IsolatedQualificationPreExecutionResult(
            ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_VERSION, QUALIFICATION_PRE_EXECUTION_SCOPE,
            b, e, limited, inputs, True, True, True,
            limited.canonical_limited_activation_material.eligibility_allowed is True, FOUNDATION_BOUND,
        )
        return replace(draft, result_digest=_digest("PRE_EXECUTION_RESULT", _material(draft, "result_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_isolated_qualification_pre_execution_result(value: Any) -> bool:
    try:
        if type(value) is not IsolatedQualificationPreExecutionResult or not _HEX.fullmatch(value.result_digest): return False
        if any((value.requirement_qualified, value.executable_request_qualified, value.execute_allowed,
                value.dispatch_permitted, value.production_application_permitted, value.runtime_invocation_permitted)):
            return False
        if value.executable_request is not None or not _authority_false(value.authority_boundary): return False
        expected = create_isolated_qualification_pre_execution_result(value.limited_activation_binding)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError): return False


__all__ = tuple(name for name in globals() if name.startswith("ISOLATED_") or name.startswith("QUALIFICATION_")
                or name.startswith("FOUNDATION_") or name.startswith("IsolatedQualification")
                or name.startswith("create_isolated_") or name.startswith("verify_isolated_"))
