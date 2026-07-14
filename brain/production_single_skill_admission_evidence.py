"""Current-default-denied, single-skill production admission evidence.

This passive sidecar binds one already-verified V5.15.24.7.1 artifact.  It does
not create an admission input, invoke a bridge, or grant any authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from decimal import Decimal
import hashlib
import json
import re
from typing import Any

from brain.production_cost_execution_delivery_integrity import (
    PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_VERSION,
    ProductionCostExecutionDeliveryIntegrity,
    verify_production_cost_execution_delivery_integrity,
)
from brain.production_feature_gate_owner import LIMITED_COST_RESPONSE_RUNTIME_BRIDGE

PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE_VERSION = "5.15.24.7.2"
PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE_SCOPE = (
    "CURRENT_DEFAULT_DENIED_PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE")
VERIFIED_DEFAULT_DENIED = "VERIFIED_DEFAULT_DENIED"
GATE_ORDER = (
    "PRODUCTION_TURN_IDENTITY", "REFERENCE_TIME", "SELECTED_SKILL_IDENTITY",
    "SKILL_EVIDENCE_PROVENANCE", "ACTIVATION_ELIGIBILITY_PROVENANCE",
    "EXECUTION_REQUEST_PROVENANCE", "DECIMAL_OPERAND_INTEGRITY",
    "EXECUTION_RESULT_INTEGRITY", "PRESENTATION_PROVENANCE",
    "AUTHORIZATION_PROVENANCE", "ADAPTER_PAYLOAD_PROVENANCE",
    "DELIVERY_QUALIFICATION_PROVENANCE", "DEFAULT_DENY_GATE_PROVENANCE",
    "SINGLE_SKILL_CARDINALITY", "SUBSTITUTION_RESISTANCE",
    "AUTHORITY_BOUNDARY", "ADMISSION_ISOLATION",
)
REASONS = ("COMPLETE_PRODUCTION_LINEAGE_VERIFIED_UNDER_DEFAULT_DENIAL",)
DIAGNOSTICS = (
    "GOVERNANCE_EVIDENCE_ONLY", "DEFAULT_DENIAL_REMAINS_EFFECTIVE",
    "ELIGIBILITY_IS_NOT_ADMISSION", "NO_RUNTIME_OR_DELIVERY_AUTHORITY",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")
_SKILLS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")


@dataclass(frozen=True)
class ProductionAdmissionEvidenceAuthorityBoundary:
    activation: bool = False
    admission: bool = False
    bridge: bool = False
    runtime: bool = False
    routing: bool = False
    response_selection: bool = False
    delivery: bool = False
    commit: bool = False
    persistence: bool = False
    tool_execution: bool = False
    feature_gate_mutation: bool = False


@dataclass(frozen=True)
class ProductionAdmissionEvidenceGateResult:
    gate: str
    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ProductionSingleSkillAdmissionEvidence:
    version: str
    scope: str
    evidence_id: str
    source: ProductionCostExecutionDeliveryIntegrity
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    user_message_digest: str
    reference_time_digest: str
    accepted_at_iso: str
    selected_skill_id: str
    production_integrity_digest: str
    skill_evidence_envelope_digest: str
    activation_binding_digest: str
    activation_request_id: str
    activation_request_digest: str
    activation_decision_digest: str
    activation_request_binding_digest: str
    execution_id: str
    execution_request_id: str
    execution_request_digest: str
    execution_result_digest: str
    execution_integrity_digest: str
    operand_digests: tuple[str, ...]
    operand_ids: tuple[str, ...]
    formula_id: str
    math_policy_digest: str
    presentation_request_id: str
    presentation_integrity_digest: str
    authorization_request_id: str
    authorization_integrity_digest: str
    adapter_request_id: str
    adapter_request_digest: str
    adapter_integrity_digest: str
    payload_digest: str
    payload_text_digest: str
    delivery_case_id: str
    delivery_case_digest: str
    delivery_result_digest: str
    delivery_binding_digest: str
    delivery_integrity_digest: str
    delivery_reference_time: str
    feature_gate_name: str
    feature_gate_evaluation_digest: str
    configured_state: bool
    effective_state: bool
    default_denied: bool
    activation_permitted: bool
    eligibility_allowed: bool
    evidence_complete: bool
    lineage_verified: bool
    governance_evidence_verified: bool
    gate_satisfied: bool
    admission_input_ready: bool
    admitted: bool
    runtime_invoked: bool
    bridge_invoked: bool
    delivery_committed: bool
    response_candidate_created: bool
    status: str
    gate_results: tuple[ProductionAdmissionEvidenceGateResult, ...]
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    authority_boundary: ProductionAdmissionEvidenceAuthorityBoundary
    executable_output: None
    evidence_digest: str = ""


def _sha(label: str, material: Any) -> str:
    return hashlib.sha256(json.dumps((label, material), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _material(value: ProductionSingleSkillAdmissionEvidence) -> tuple[Any, ...]:
    result = []
    for field in fields(value):
        if field.name in ("source", "evidence_digest"):
            continue
        item = getattr(value, field.name)
        if type(item) is ProductionAdmissionEvidenceAuthorityBoundary:
            item = tuple(getattr(item, name) for name in item.__dataclass_fields__)
        elif field.name == "gate_results":
            item = tuple((gate.gate, gate.passed, gate.reasons) for gate in item)
        result.append(item)
    return tuple(result)


def _all_digests(value: Any) -> bool:
    try:
        for field in fields(value):
            item = getattr(value, field.name)
            if field.name.endswith("digest") and item is not None:
                if type(item) is not str or _HEX.fullmatch(item) is None:
                    return False
            if hasattr(item, "__dataclass_fields__") and not _all_digests(item):
                return False
            if type(item) is tuple:
                for nested in item:
                    if hasattr(nested, "__dataclass_fields__") and not _all_digests(nested):
                        return False
        return True
    except (AttributeError, TypeError):
        return False


def create_production_single_skill_admission_evidence(source: Any):
    """Bind one complete preconstructed default-denied production chain."""
    try:
        if (type(source) is not ProductionCostExecutionDeliveryIntegrity
                or not verify_production_cost_execution_delivery_integrity(source)
                or source.version != PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_VERSION
                or source.feature_gate_name != LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
                or source.feature_gate_configured_state is not False
                or source.feature_gate_effective_state is not False
                or source.feature_gate_default_denied is not True
                or source.limited_activation_binding.feature_gate_activation_permitted is not False
                or source.selected_skill_id not in _SKILLS):
            return None
        e, p, a, ad, d = (source.execution_integrity, source.presentation_integrity,
                           source.authorization_integrity, source.adapter_integrity,
                           source.delivery_integrity)
        skill = source.selected_skill_id
        if not (e.execution_request.requested_skill_id == e.execution_result.requested_skill_id
                == d.qualification_case.skill_id == d.qualification_result.skill_id
                == d.qualification_binding.skill_id == d.qualification_binding.payload_skill_id
                == ad.adapter_result.payload.source_skill_id == skill):
            return None
        gates = tuple(ProductionAdmissionEvidenceGateResult(name, True, ("PASSED",))
                      for name in GATE_ORDER)
        lineage = (source.turn_digest, source.reference_time_digest, skill,
                   source.integrity_digest, source.activation_request_digest,
                   source.execution_request_digest, source.payload_digest,
                   source.delivery_integrity_digest)
        evidence_id = "production-single-skill-admission-evidence-" + _sha("EVIDENCE_ID", lineage)
        values = dict(version=PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE_VERSION,
            scope=PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE_SCOPE, evidence_id=evidence_id,
            source=source, conversation_id=source.conversation_id, turn_id=source.turn_id,
            turn_ordinal=source.turn_ordinal, turn_digest=source.turn_digest,
            user_message_digest=source.user_message_digest,
            reference_time_digest=source.reference_time_digest, accepted_at_iso=source.accepted_at_iso,
            selected_skill_id=skill, production_integrity_digest=source.integrity_digest,
            skill_evidence_envelope_digest=source.skill_evidence_envelope_digest,
            activation_binding_digest=source.limited_activation_binding_digest,
            activation_request_id=source.activation_request_id,
            activation_request_digest=source.activation_request_digest,
            activation_decision_digest=source.activation_decision_digest,
            activation_request_binding_digest=source.activation_request_binding_digest,
            execution_id=e.execution_request.execution_id,
            execution_request_id=e.execution_request.request_id,
            execution_request_digest=source.execution_request_digest,
            execution_result_digest=source.execution_result_snapshot_digest,
            execution_integrity_digest=source.execution_integrity_digest,
            operand_digests=tuple(x.operand_digest for x in source.ordered_decimal_operands),
            operand_ids=tuple(x.evidence_id for x in source.ordered_decimal_operands),
            formula_id=source.formula_id, math_policy_digest=source.math_policy_digest,
            presentation_request_id=p.presentation_request.presentation_id,
            presentation_integrity_digest=source.presentation_integrity_digest,
            authorization_request_id=a.authorization_request.authorization_id,
            authorization_integrity_digest=source.authorization_integrity_digest,
            adapter_request_id=ad.adapter_request.adapter_request_id,
            adapter_request_digest=source.adapter_request_digest,
            adapter_integrity_digest=source.adapter_integrity_digest,
            payload_digest=source.payload_digest, payload_text_digest=source.payload_text_digest,
            delivery_case_id=d.qualification_case.case_id,
            delivery_case_digest=source.delivery_case_digest,
            delivery_result_digest=source.delivery_result_digest,
            delivery_binding_digest=source.delivery_binding_digest,
            delivery_integrity_digest=source.delivery_integrity_digest,
            delivery_reference_time=d.reference_time, feature_gate_name=source.feature_gate_name,
            feature_gate_evaluation_digest=source.feature_gate_evaluation_digest,
            configured_state=False, effective_state=False, default_denied=True,
            activation_permitted=False, eligibility_allowed=source.eligibility_allowed,
            evidence_complete=True, lineage_verified=True, governance_evidence_verified=True,
            gate_satisfied=False, admission_input_ready=False, admitted=False,
            runtime_invoked=False, bridge_invoked=False, delivery_committed=False,
            response_candidate_created=False, status=VERIFIED_DEFAULT_DENIED,
            gate_results=gates, reasons=REASONS, diagnostics=DIAGNOSTICS,
            authority_boundary=ProductionAdmissionEvidenceAuthorityBoundary(), executable_output=None)
        draft = ProductionSingleSkillAdmissionEvidence(**values)
        return replace(draft, evidence_digest=_sha("PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE", _material(draft)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_single_skill_admission_evidence(value: Any) -> bool:
    """Strictly verify embedded evidence; no transformation is invoked."""
    try:
        if type(value) is not ProductionSingleSkillAdmissionEvidence or not _all_digests(value):
            return False
        expected = create_production_single_skill_admission_evidence(value.source)
        return (expected is not None and value == expected
                and value.evidence_digest == _sha(
                    "PRODUCTION_SINGLE_SKILL_ADMISSION_EVIDENCE", _material(value)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = tuple(name for name in globals() if name.startswith("PRODUCTION_") or name in (
    "VERIFIED_DEFAULT_DENIED", "GATE_ORDER", "REASONS", "DIAGNOSTICS",
    "ProductionAdmissionEvidenceAuthorityBoundary", "ProductionAdmissionEvidenceGateResult",
    "ProductionSingleSkillAdmissionEvidence", "create_production_single_skill_admission_evidence",
    "verify_production_single_skill_admission_evidence"))
