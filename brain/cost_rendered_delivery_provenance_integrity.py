"""Canonical structural provenance sidecars for rendered Cost delivery.

The constructors in this module bind already-created artifacts.  They never
execute, render, authorize, adapt, qualify, route, deliver, or commit anything.
The SHA-256 bindings are deterministic trusted-process integrity evidence, not
signatures and not claims that the historical transformations were semantically
correct.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
import hashlib
import json
import math
import re
from typing import Any, Mapping

from brain.cost_execution_result_integrity import (
    COST_EXECUTION_RESULT_INTEGRITY_VERSION,
    CostExecutionResultIntegrity,
    verify_cost_execution_result_integrity,
)
from brain.business_skill_cost_result_presenter import (
    GATE_ORDER as PRESENTATION_GATE_ORDER,
    PRESENTATION_DRAFTED,
    PRESENTATION_DENIED,
    PRESENTATION_INVALID,
    CostPresentationRequest,
    CostPresentationResult,
    verify_cost_presentation_result_integrity as verify_historical_presentation_result,
    verify_cost_response_draft_integrity,
)
from brain.business_skill_cost_response_authorization import (
    GATE_ORDER as AUTHORIZATION_GATE_ORDER,
    RESPONSE_DELIVERY_DENIED,
    RESPONSE_DELIVERY_ELIGIBLE,
    RESPONSE_DELIVERY_INVALID,
    AuthorizedCostResponseArtifact,
    CostResponseAuthorizationDecision,
    CostResponseAuthorizationRequest,
)
from brain.business_skill_cost_response_adapter import (
    CostResponseAdapterRequest,
    CostResponseAdapterResult,
    PreparedCostResponsePayload,
    verify_cost_response_adapter_result_integrity,
    verify_prepared_cost_response_payload_integrity,
)
from brain.business_skill_cost_response_delivery_qualification import (
    COST_DELIVERY_QUALIFICATION_VERSION,
    CostDeliveryQualificationBinding,
    CostDeliveryQualificationCase,
    CostDeliveryQualificationResult,
    verify_cost_delivery_qualification_binding,
    verify_cost_delivery_qualification_result_integrity,
)


COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION = "5.15.24.7.0.1"
PRESENTATION_RESULT_INTEGRITY_SCHEMA_VERSION = "5.15.24.7.0.1"
AUTHORIZATION_DECISION_INTEGRITY_SCHEMA_VERSION = "5.15.24.7.0.1"
ADAPTER_RESULT_INTEGRITY_SCHEMA_VERSION = "5.15.24.7.0.1"
DELIVERY_PROVENANCE_INTEGRITY_SCHEMA_VERSION = "5.15.24.7.0.1"

_HEX = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True)
class _IsolatedStructuralBoundary:
    structural_integrity_verified: bool = True
    isolated_observation: bool = True
    production_permitted: bool = False
    delivered: bool = False
    committed: bool = False
    routing_authority: bool = False
    planning_authority: bool = False
    business_execution_authority: bool = False
    response_selection_authority: bool = False
    response_guard_authority: bool = False
    response_resolution_authority: bool = False
    response_commit_authority: bool = False
    response_delivery_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    bridge_execution_authority: bool = False
    admission_authority: bool = False
    production_activation_authority: bool = False


@dataclass(frozen=True)
class CostPresentationResultIntegrity(_IsolatedStructuralBoundary):
    version: str = ""
    schema_version: str = ""
    execution_integrity: CostExecutionResultIntegrity | None = None
    execution_integrity_digest: str = ""
    presentation_request: CostPresentationRequest | None = None
    presentation_request_digest: str = ""
    embedded_execution_result_digest: str = ""
    presentation_result: CostPresentationResult | None = None
    presentation_result_snapshot_digest: str = ""
    rendered_text_digest: str | None = None
    integrity_digest: str = ""


@dataclass(frozen=True)
class CostAuthorizationDecisionIntegrity(_IsolatedStructuralBoundary):
    version: str = ""
    schema_version: str = ""
    presentation_integrity: CostPresentationResultIntegrity | None = None
    presentation_integrity_digest: str = ""
    authorization_request: CostResponseAuthorizationRequest | None = None
    authorization_request_digest: str = ""
    authorization_decision: CostResponseAuthorizationDecision | None = None
    authorization_decision_digest: str = ""
    authorized_text_digest: str | None = None
    integrity_digest: str = ""


@dataclass(frozen=True)
class CostAdapterResultIntegrity(_IsolatedStructuralBoundary):
    version: str = ""
    schema_version: str = ""
    authorization_integrity: CostAuthorizationDecisionIntegrity | None = None
    authorization_integrity_digest: str = ""
    adapter_request: CostResponseAdapterRequest | None = None
    adapter_request_digest: str = ""
    adapter_result: CostResponseAdapterResult | None = None
    adapter_result_digest: str = ""
    payload_digest: str | None = None
    payload_text_digest: str | None = None
    integrity_digest: str = ""


@dataclass(frozen=True)
class CostDeliveryProvenanceIntegrity(_IsolatedStructuralBoundary):
    version: str = ""
    schema_version: str = ""
    adapter_integrity: CostAdapterResultIntegrity | None = None
    adapter_integrity_digest: str = ""
    qualification_case: CostDeliveryQualificationCase | None = None
    qualification_case_digest: str = ""
    qualification_result: CostDeliveryQualificationResult | None = None
    qualification_result_digest: str = ""
    qualification_version: str = ""
    qualification_binding: CostDeliveryQualificationBinding | None = None
    qualification_binding_digest: str | None = None
    reference_time: str = ""
    payload_digest: str | None = None
    integrity_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite float")
        return ["float", format(value, ".17g")]
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        item = value.as_tuple()
        return ["decimal", item.sign, list(item.digits), item.exponent]
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("non-string mapping key")
        return [[key, _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported canonical value")


def _digest(label: str, value: Any) -> str:
    payload = (COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION, label, value)
    encoded = json.dumps(_canonical(payload), ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _material(value: Any) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
                 if field.name != "integrity_digest")


def _boundary_ok(value: Any) -> bool:
    return (value.structural_integrity_verified is True
            and value.isolated_observation is True
            and all(type(getattr(value, field.name)) is bool
                    and getattr(value, field.name) is False
                    for field in fields(_IsolatedStructuralBoundary)
                    if field.name not in ("structural_integrity_verified", "isolated_observation")))


def _valid_gate_result(gates: Any, order: tuple[str, ...]) -> bool:
    if type(gates) is not tuple or tuple(getattr(item, "gate", None) for item in gates) != order:
        return False
    return all(type(item.passed) is bool and type(item.reason_codes) is tuple
               and bool(item.reason_codes)
               and item.passed == (item.reason_codes == ("PASSED",)) for item in gates)


def _failures(gates: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(code for gate in gates for code in gate.reason_codes if code != "PASSED")


def _valid_authorization_decision(
    request: CostResponseAuthorizationRequest, decision: CostResponseAuthorizationDecision,
) -> bool:
    if not _valid_gate_result(decision.gate_results, AUTHORIZATION_GATE_ORDER):
        return False
    failures = _failures(decision.gate_results)
    if decision.authorization_id != request.authorization_id or decision.reason_codes != (failures or ("ALL_AUTHORIZATION_GATES_PASSED",)):
        return False
    forbidden = ("response_generated", "response_committed", "runtime_routed", "tools_invoked",
                 "persisted", "follow_up_generated", "business_reasoning_generated",
                 "execution_performed", "calculation_performed")
    if any(type(getattr(decision, name)) is not bool or getattr(decision, name) for name in forbidden):
        return False
    source = request.presentation_result
    draft = source.draft if type(source) is CostPresentationResult else None
    if decision.outcome == RESPONSE_DELIVERY_ELIGIBLE:
        artifact = decision.authorized_artifact
        if (failures or decision.denial is not None or decision.response_delivery_eligible is not True
                or type(artifact) is not AuthorizedCostResponseArtifact or draft is None):
            return False
        expected = (
            request.authorization_id, source.presentation_id, draft.source_execution_id,
            draft.source_request_id, draft.source_skill_id, request.policy_version,
            request.authorization_scope, source.presentation_digest, draft.draft_digest,
            draft.template_id, draft.locale, request.target_channel, draft.draft_text, True,
        )
        return tuple(getattr(artifact, field.name) for field in fields(artifact)) == expected
    if decision.outcome not in (RESPONSE_DELIVERY_DENIED, RESPONSE_DELIVERY_INVALID):
        return False
    return (bool(failures) and decision.authorized_artifact is None
            and decision.response_delivery_eligible is False and decision.denial is not None
            and decision.denial.reason_codes == failures
            and decision.denial.first_failed_gate == next(g.gate for g in decision.gate_results if not g.passed))


def create_cost_presentation_result_integrity(
    execution_integrity: Any, presentation_request: Any, presentation_result: Any,
) -> CostPresentationResultIntegrity | None:
    """Bind a preconstructed presentation without calling the presenter."""
    try:
        if (not verify_cost_execution_result_integrity(execution_integrity)
                or type(presentation_request) is not CostPresentationRequest
                or type(presentation_result) is not CostPresentationResult
                or not verify_historical_presentation_result(presentation_result)):
            return None
        execution = execution_integrity.execution_result
        if presentation_request.execution_result != execution:
            return None
        if (presentation_request.execution_id, presentation_request.request_id,
                presentation_request.requested_skill_id) != (
                execution.execution_id, execution.request_id, execution.requested_skill_id):
            return None
        if presentation_result.presentation_id != presentation_request.presentation_id:
            return None
        draft = presentation_result.draft
        if draft is not None:
            if not verify_cost_response_draft_integrity(draft):
                return None
            if (draft.source_presentation_id, draft.source_execution_id, draft.source_request_id,
                    draft.source_skill_id) != (
                    presentation_request.presentation_id, presentation_request.execution_id,
                    presentation_request.request_id, presentation_request.requested_skill_id):
                return None
        elif presentation_result.outcome == PRESENTATION_DRAFTED:
            return None
        if presentation_result.outcome not in (PRESENTATION_DRAFTED, PRESENTATION_DENIED, PRESENTATION_INVALID):
            return None
        draft = CostPresentationResultIntegrity(
            version=COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION,
            schema_version=PRESENTATION_RESULT_INTEGRITY_SCHEMA_VERSION,
            execution_integrity=execution_integrity,
            execution_integrity_digest=execution_integrity.integrity_digest,
            presentation_request=presentation_request,
            presentation_request_digest=_digest("PRESENTATION_REQUEST", presentation_request),
            embedded_execution_result_digest=_digest("EXECUTION_RESULT_SNAPSHOT", execution),
            presentation_result=presentation_result,
            presentation_result_snapshot_digest=_digest("PRESENTATION_RESULT_SNAPSHOT", presentation_result),
            rendered_text_digest=None if presentation_result.draft is None else _text_digest(presentation_result.draft.draft_text),
        )
        return replace(draft, integrity_digest=_digest("PRESENTATION_RESULT_INTEGRITY", _material(draft)))
    except (AttributeError, StopIteration, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_cost_presentation_result_integrity(value: Any) -> bool:
    try:
        if (type(value) is not CostPresentationResultIntegrity or not _boundary_ok(value)
                or value.version != COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION
                or value.schema_version != PRESENTATION_RESULT_INTEGRITY_SCHEMA_VERSION
                or _HEX.fullmatch(value.integrity_digest) is None):
            return False
        return value == create_cost_presentation_result_integrity(
            value.execution_integrity, value.presentation_request, value.presentation_result)
    except (AttributeError, TypeError, ValueError):
        return False


def create_cost_authorization_decision_integrity(
    presentation_integrity: Any, authorization_request: Any, authorization_decision: Any,
) -> CostAuthorizationDecisionIntegrity | None:
    """Bind a preconstructed authorization decision without authorizing."""
    try:
        if (not verify_cost_presentation_result_integrity(presentation_integrity)
                or type(authorization_request) is not CostResponseAuthorizationRequest
                or type(authorization_decision) is not CostResponseAuthorizationDecision):
            return None
        presentation = presentation_integrity.presentation_result
        if authorization_request.presentation_result != presentation:
            return None
        request_ids = (authorization_request.presentation_id, authorization_request.execution_id,
                       authorization_request.request_id, authorization_request.requested_skill_id)
        presentation_request = presentation_integrity.presentation_request
        if request_ids != (presentation.presentation_id, presentation_request.execution_id,
                           presentation_request.request_id, presentation_request.requested_skill_id):
            return None
        if not _valid_authorization_decision(authorization_request, authorization_decision):
            return None
        artifact = authorization_decision.authorized_artifact
        draft = CostAuthorizationDecisionIntegrity(
            version=COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION,
            schema_version=AUTHORIZATION_DECISION_INTEGRITY_SCHEMA_VERSION,
            presentation_integrity=presentation_integrity,
            presentation_integrity_digest=presentation_integrity.integrity_digest,
            authorization_request=authorization_request,
            authorization_request_digest=_digest("AUTHORIZATION_REQUEST", authorization_request),
            authorization_decision=authorization_decision,
            authorization_decision_digest=_digest("AUTHORIZATION_DECISION", authorization_decision),
            authorized_text_digest=None if artifact is None else _text_digest(artifact.authorized_text),
        )
        return replace(draft, integrity_digest=_digest("AUTHORIZATION_DECISION_INTEGRITY", _material(draft)))
    except (AttributeError, StopIteration, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_cost_authorization_decision_integrity(value: Any) -> bool:
    try:
        if (type(value) is not CostAuthorizationDecisionIntegrity or not _boundary_ok(value)
                or value.version != COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION
                or value.schema_version != AUTHORIZATION_DECISION_INTEGRITY_SCHEMA_VERSION
                or _HEX.fullmatch(value.integrity_digest) is None):
            return False
        return value == create_cost_authorization_decision_integrity(
            value.presentation_integrity, value.authorization_request, value.authorization_decision)
    except (AttributeError, TypeError, ValueError):
        return False


def create_cost_adapter_result_integrity(
    authorization_integrity: Any, adapter_request: Any, adapter_result: Any,
) -> CostAdapterResultIntegrity | None:
    """Bind a preconstructed adapter result without adapting."""
    try:
        if (not verify_cost_authorization_decision_integrity(authorization_integrity)
                or type(adapter_request) is not CostResponseAdapterRequest
                or type(adapter_result) is not CostResponseAdapterResult
                or not verify_cost_response_adapter_result_integrity(adapter_result)):
            return None
        decision = authorization_integrity.authorization_decision
        if adapter_request.authorization_decision != decision or adapter_result.adapter_request_id != adapter_request.adapter_request_id:
            return None
        payload = adapter_result.payload
        artifact = decision.authorized_artifact
        if payload is not None:
            if not verify_prepared_cost_response_payload_integrity(payload) or artifact is None:
                return None
            pairs = (
                (payload.source_authorization_id, artifact.authorization_id),
                (payload.source_presentation_id, artifact.source_presentation_id),
                (payload.source_execution_id, artifact.source_execution_id),
                (payload.source_request_id, artifact.source_request_id),
                (payload.source_skill_id, artifact.source_skill_id),
                (payload.presentation_digest, artifact.presentation_integrity_digest),
                (payload.draft_digest, artifact.draft_integrity_digest),
                (payload.text, artifact.authorized_text),
            )
            if any(left != right for left, right in pairs) or payload.text.encode("utf-8") != artifact.authorized_text.encode("utf-8"):
                return None
        elif adapter_result.payload_prepared:
            return None
        draft = CostAdapterResultIntegrity(
            version=COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION,
            schema_version=ADAPTER_RESULT_INTEGRITY_SCHEMA_VERSION,
            authorization_integrity=authorization_integrity,
            authorization_integrity_digest=authorization_integrity.integrity_digest,
            adapter_request=adapter_request,
            adapter_request_digest=_digest("ADAPTER_REQUEST", adapter_request),
            adapter_result=adapter_result,
            adapter_result_digest=_digest("ADAPTER_RESULT", adapter_result),
            payload_digest=None if payload is None else payload.payload_digest,
            payload_text_digest=None if payload is None else _text_digest(payload.text),
        )
        return replace(draft, integrity_digest=_digest("ADAPTER_RESULT_INTEGRITY", _material(draft)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_cost_adapter_result_integrity(value: Any) -> bool:
    try:
        if (type(value) is not CostAdapterResultIntegrity or not _boundary_ok(value)
                or value.version != COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION
                or value.schema_version != ADAPTER_RESULT_INTEGRITY_SCHEMA_VERSION
                or _HEX.fullmatch(value.integrity_digest) is None):
            return False
        return value == create_cost_adapter_result_integrity(
            value.authorization_integrity, value.adapter_request, value.adapter_result)
    except (AttributeError, TypeError, ValueError):
        return False


def create_cost_delivery_provenance_integrity(
    adapter_integrity: Any, qualification_case: Any, qualification_result: Any,
) -> CostDeliveryProvenanceIntegrity | None:
    """Bind an existing delivery qualification without running qualification."""
    try:
        if (not verify_cost_adapter_result_integrity(adapter_integrity)
                or type(qualification_case) is not CostDeliveryQualificationCase
                or type(qualification_result) is not CostDeliveryQualificationResult
                or not verify_cost_delivery_qualification_result_integrity(qualification_result)):
            return None
        adapter_result = adapter_integrity.adapter_result
        decision = adapter_integrity.authorization_integrity.authorization_decision
        if (qualification_case.adapter_result != adapter_result
                or qualification_case.deterministic_comparison_result != adapter_result
                or qualification_case.authorization_decision != decision):
            return None
        payload = adapter_result.payload
        expected_ids = (
            qualification_case.request_id, qualification_case.skill_id,
            qualification_case.execution_id, qualification_case.presentation_id,
            qualification_case.authorization_id, qualification_case.adapter_request_id,
        )
        presentation_request = adapter_integrity.authorization_integrity.presentation_integrity.presentation_request
        if expected_ids != (
            presentation_request.request_id, presentation_request.requested_skill_id,
            presentation_request.execution_id, presentation_request.presentation_id,
            decision.authorization_id, adapter_result.adapter_request_id,
        ):
            return None
        if (qualification_result.case_id, qualification_result.skill_id) != (
                qualification_case.case_id, qualification_case.skill_id):
            return None
        binding = qualification_result.binding
        if binding is not None:
            if (not verify_cost_delivery_qualification_binding(binding) or payload is None
                    or binding.qualification_version != COST_DELIVERY_QUALIFICATION_VERSION
                    or binding.payload_digest != payload.payload_digest
                    or binding.reference_time != qualification_result.reference_time):
                return None
            binding_pairs = (
                (binding.payload_request_id, qualification_case.request_id),
                (binding.payload_skill_id, qualification_case.skill_id),
                (binding.payload_execution_id, qualification_case.execution_id),
                (binding.payload_presentation_id, qualification_case.presentation_id),
                (binding.payload_authorization_id, qualification_case.authorization_id),
                (binding.adapter_request_id, qualification_case.adapter_request_id),
                (binding.presentation_digest, payload.presentation_digest),
                (binding.draft_digest, payload.draft_digest),
            )
            if any(left != right for left, right in binding_pairs):
                return None
        draft = CostDeliveryProvenanceIntegrity(
            version=COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION,
            schema_version=DELIVERY_PROVENANCE_INTEGRITY_SCHEMA_VERSION,
            adapter_integrity=adapter_integrity,
            adapter_integrity_digest=adapter_integrity.integrity_digest,
            qualification_case=qualification_case,
            qualification_case_digest=_digest("DELIVERY_QUALIFICATION_CASE", qualification_case),
            qualification_result=qualification_result,
            qualification_result_digest=_digest("DELIVERY_QUALIFICATION_RESULT", qualification_result),
            qualification_version=COST_DELIVERY_QUALIFICATION_VERSION,
            qualification_binding=binding,
            qualification_binding_digest=None if binding is None else binding.qualification_digest,
            reference_time=qualification_result.reference_time,
            payload_digest=None if payload is None else payload.payload_digest,
        )
        return replace(draft, integrity_digest=_digest("DELIVERY_PROVENANCE_INTEGRITY", _material(draft)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_cost_delivery_provenance_integrity(value: Any) -> bool:
    try:
        if (type(value) is not CostDeliveryProvenanceIntegrity or not _boundary_ok(value)
                or value.version != COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION
                or value.schema_version != DELIVERY_PROVENANCE_INTEGRITY_SCHEMA_VERSION
                or _HEX.fullmatch(value.integrity_digest) is None):
            return False
        return value == create_cost_delivery_provenance_integrity(
            value.adapter_integrity, value.qualification_case, value.qualification_result)
    except (AttributeError, TypeError, ValueError):
        return False


__all__ = (
    "COST_RENDERED_DELIVERY_PROVENANCE_INTEGRITY_VERSION",
    "PRESENTATION_RESULT_INTEGRITY_SCHEMA_VERSION",
    "AUTHORIZATION_DECISION_INTEGRITY_SCHEMA_VERSION",
    "ADAPTER_RESULT_INTEGRITY_SCHEMA_VERSION",
    "DELIVERY_PROVENANCE_INTEGRITY_SCHEMA_VERSION",
    "CostPresentationResultIntegrity", "CostAuthorizationDecisionIntegrity",
    "CostAdapterResultIntegrity", "CostDeliveryProvenanceIntegrity",
    "create_cost_presentation_result_integrity", "verify_cost_presentation_result_integrity",
    "create_cost_authorization_decision_integrity", "verify_cost_authorization_decision_integrity",
    "create_cost_adapter_result_integrity", "verify_cost_adapter_result_integrity",
    "create_cost_delivery_provenance_integrity", "verify_cost_delivery_provenance_integrity",
)
