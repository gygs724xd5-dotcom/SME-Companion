"""V5.15.17 cost-response delivery authorization boundary.

Authorization consumes only a canonical V5.15.16.1 presentation result.  It
does not execute, calculate, present, rewrite, route, commit, invoke tools,
persist, follow up, or perform business reasoning.

The SHA-256 bindings are deterministic integrity checks inside a trusted
internal artifact boundary.  They are not signatures, MACs, authentication,
or replay protection.  An identical valid artifact replay remains detectable
by neither digest, and an untrusted caller able to rebuild the artifact and
both digests is outside this boundary's threat model.  No nonce/consumption
store is maintained here.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Iterable

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_cost_result_presenter import (
    DRAFT_BINDING_SCHEMA_VERSION,
    INTERNAL_DRAFT_ONLY,
    PRESENTATION_BINDING_SCHEMA_VERSION,
    PRESENTATION_DRAFTED,
    PRESENTATION_VERSION,
    SUPPORTED_LOCALE,
    CostPresentationResult,
    verify_cost_presentation_result_integrity,
    verify_cost_response_draft_integrity,
)

AUTHORIZATION_POLICY_VERSION = "5.15.17"
LIMITED_COST_RESPONSE = "LIMITED_COST_RESPONSE"
USER_TEXT_RESPONSE = "USER_TEXT_RESPONSE"
RESPONSE_DELIVERY_ELIGIBLE = "RESPONSE_DELIVERY_ELIGIBLE"
RESPONSE_DELIVERY_DENIED = "RESPONSE_DELIVERY_DENIED"
RESPONSE_DELIVERY_INVALID = "RESPONSE_DELIVERY_INVALID"
MAXIMUM_DRAFT_LENGTH = 4000
GATE_ORDER = (
    "REQUEST_VALIDITY", "PRESENTATION_RESULT", "DRAFT_INTEGRITY", "PRESENTATION_INTEGRITY",
    "IDENTITY_BINDING", "SKILL_IDENTITY", "LIFECYCLE", "AUTHORIZATION_SCOPE",
    "TARGET_CHANNEL", "CONTENT_SAFETY", "AUTHORITY_SEPARATION", "DELIVERY_ELIGIBILITY",
)
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TEMPLATES = {
    "cost.change_analysis.v1": "COST_CHANGE_TH_V1",
    "cost.per_unit_calculation.v1": "COST_PER_UNIT_TH_V1",
}


@dataclass(frozen=True)
class CostResponseAuthorizationPolicy:
    policy_version: str = AUTHORIZATION_POLICY_VERSION
    locale: str = SUPPORTED_LOCALE
    presentation_channel: str = INTERNAL_DRAFT_ONLY
    authorization_scope: str = LIMITED_COST_RESPONSE
    target_channel: str = USER_TEXT_RESPONSE
    maximum_draft_length: int = MAXIMUM_DRAFT_LENGTH
    deny_by_default: bool = True

    def __post_init__(self) -> None:
        if (self.policy_version, self.locale, self.presentation_channel,
                self.authorization_scope, self.target_channel, self.maximum_draft_length,
                self.deny_by_default) != (
                AUTHORIZATION_POLICY_VERSION, SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY,
                LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE, MAXIMUM_DRAFT_LENGTH, True):
            raise ValueError("unsupported, malformed, or weakened authorization policy")


@dataclass(frozen=True)
class CostResponseAuthorizationRequest:
    authorization_id: Any
    presentation_id: Any
    execution_id: Any
    request_id: Any
    requested_skill_id: Any
    presentation_result: Any
    authorization_scope: Any
    target_channel: Any
    policy_version: Any


@dataclass(frozen=True)
class CostResponseAuthorizationGateResult:
    gate: str
    passed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CostResponseAuthorizationDenial:
    reason_codes: tuple[str, ...]
    first_failed_gate: str


@dataclass(frozen=True)
class AuthorizedCostResponseArtifact:
    authorization_id: str
    source_presentation_id: str
    source_execution_id: str
    source_request_id: str
    source_skill_id: str
    authorization_policy_version: str
    presentation_integrity_digest: str
    draft_integrity_digest: str
    template_id: str
    locale: str
    target_channel: str
    authorized_text: str
    response_delivery_eligible: bool = True


@dataclass(frozen=True)
class CostResponseAuthorizationDecision:
    authorization_id: str
    outcome: str
    gate_results: tuple[CostResponseAuthorizationGateResult, ...]
    reason_codes: tuple[str, ...]
    authorized_artifact: AuthorizedCostResponseArtifact | None = None
    denial: CostResponseAuthorizationDenial | None = None
    response_delivery_eligible: bool = False
    source_presentation_generated: bool = False
    source_executed: bool = False
    source_calculated: bool = False
    response_generated: bool = False
    response_committed: bool = False
    runtime_routed: bool = False
    tools_invoked: bool = False
    persisted: bool = False
    follow_up_generated: bool = False
    business_reasoning_generated: bool = False
    execution_performed: bool = False
    calculation_performed: bool = False


@dataclass(frozen=True)
class CostResponseAuthorizationBatch:
    authorization_policy_version: str
    decisions: tuple[CostResponseAuthorizationDecision, ...]


def _gate(name: str, reasons: Iterable[str]) -> CostResponseAuthorizationGateResult:
    codes = tuple(dict.fromkeys(reasons))
    return CostResponseAuthorizationGateResult(name, not codes, codes or ("PASSED",))


def _unsafe_control(text: str) -> bool:
    return any(ch != "\n" and unicodedata.category(ch) == "Cc" for ch in text)


def authorize_cost_response(
    request: Any, policy: CostResponseAuthorizationPolicy | None = None,
) -> CostResponseAuthorizationDecision:
    policy = CostResponseAuthorizationPolicy() if policy is None else policy
    if type(policy) is not CostResponseAuthorizationPolicy:
        raise ValueError("policy must be CostResponseAuthorizationPolicy")

    valid = type(request) is CostResponseAuthorizationRequest
    aid = request.authorization_id if valid else ""
    source = request.presentation_result if valid else None
    draft = source.draft if type(source) is CostPresentationResult else None

    validity: list[str] = []
    if not valid: validity.append("MALFORMED_AUTHORIZATION_REQUEST")
    if not isinstance(aid, str) or not _ID.fullmatch(aid): validity.append("INVALID_AUTHORIZATION_ID")
    for name in ("presentation_id", "execution_id", "request_id", "requested_skill_id"):
        value = getattr(request, name, None)
        if not isinstance(value, str) or not _ID.fullmatch(value): validity.append(f"INVALID_{name.upper()}")
    if valid and request.policy_version != policy.policy_version: validity.append("POLICY_VERSION_MISMATCH")

    presentation = []
    if type(source) is not CostPresentationResult: presentation.append("MISSING_OR_FABRICATED_PRESENTATION_RESULT")
    elif source.outcome != PRESENTATION_DRAFTED or source.denial is not None:
        presentation.append("PRESENTATION_NOT_DRAFTED")

    # Both prerequisite verifiers are always independently invoked for a typed source.
    draft_ok = verify_cost_response_draft_integrity(draft)
    result_ok = verify_cost_presentation_result_integrity(source)
    draft_integrity = [] if draft_ok else ["DRAFT_INTEGRITY_FAILED"]
    result_integrity = [] if result_ok else ["PRESENTATION_INTEGRITY_FAILED"]

    binding: list[str] = []
    if type(source) is CostPresentationResult and source.presentation_id != getattr(request, "presentation_id", None):
        binding.append("PRESENTATION_ID_MISMATCH")
    if draft is not None:
        pairs = (("source_presentation_id", "presentation_id"), ("source_execution_id", "execution_id"),
                 ("source_request_id", "request_id"), ("source_skill_id", "requested_skill_id"))
        for source_name, request_name in pairs:
            if getattr(draft, source_name, None) != getattr(request, request_name, None):
                binding.append(f"{request_name.upper()}_MISMATCH")

    skill = getattr(request, "requested_skill_id", None)
    skill_identity: list[str] = []
    if skill not in _TEMPLATES: skill_identity.append("UNSUPPORTED_SKILL")
    if BUSINESS_SKILL_REGISTRY_VERSION != "5.15.13": skill_identity.append("REGISTRY_VERSION_MISMATCH")
    if PRESENTATION_VERSION != "5.15.16.1": skill_identity.append("PRESENTATION_VERSION_MISMATCH")
    if DRAFT_BINDING_SCHEMA_VERSION != 1: skill_identity.append("DRAFT_BINDING_SCHEMA_MISMATCH")
    if PRESENTATION_BINDING_SCHEMA_VERSION != 1: skill_identity.append("PRESENTATION_BINDING_SCHEMA_MISMATCH")

    canonical = next((x for x in get_business_skill_registry() if x.skill_id == skill), None)
    lifecycle = [] if canonical is not None and canonical.active_status == LIMITED_ACTIVE else ["LIFECYCLE_NOT_LIMITED_ACTIVE"]
    scope = [] if valid and request.authorization_scope == policy.authorization_scope else ["UNSUPPORTED_AUTHORIZATION_SCOPE"]
    channel = [] if valid and request.target_channel == policy.target_channel else ["UNSUPPORTED_TARGET_CHANNEL"]

    content: list[str] = []
    if draft is None: content.append("MISSING_DRAFT")
    else:
        if draft.locale != policy.locale: content.append("UNSUPPORTED_LOCALE")
        if draft.template_id != _TEMPLATES.get(skill): content.append("UNSUPPORTED_TEMPLATE")
        if not isinstance(draft.draft_text, str) or not draft.draft_text: content.append("EMPTY_DRAFT")
        elif len(draft.draft_text) > policy.maximum_draft_length: content.append("DRAFT_TOO_LONG")
        elif _unsafe_control(draft.draft_text): content.append("CONTROL_CHARACTER_NOT_ALLOWED")

    authority: list[str] = []
    required_true = ("presentation_generated", "internal_draft_only", "source_executed", "source_calculated")
    required_false = ("response_generated", "response_committed", "runtime_routed", "tools_invoked", "persisted",
                      "follow_up_generated", "business_reasoning_generated")
    if type(source) is CostPresentationResult:
        if any(not getattr(source, name, False) for name in required_true): authority.append("SOURCE_AUTHORITY_STATE_INVALID")
        if any(getattr(source, name, False) for name in required_false): authority.append("SOURCE_AUTHORITY_LEAKAGE")
    if draft is not None:
        if any(not getattr(draft, name, False) for name in required_true): authority.append("DRAFT_AUTHORITY_STATE_INVALID")
        if any(getattr(draft, name, False) for name in required_false): authority.append("DRAFT_AUTHORITY_LEAKAGE")

    groups = [validity, presentation, draft_integrity, result_integrity, binding, skill_identity,
              lifecycle, scope, channel, content, authority]
    delivery = [] if not any(groups) else ["DELIVERY_NOT_ELIGIBLE"]
    groups.append(delivery)
    gates = tuple(_gate(name, reasons) for name, reasons in zip(GATE_ORDER, groups))
    failures = tuple(code for gate in gates for code in gate.reason_codes if code != "PASSED")
    if failures:
        first = next(g.gate for g in gates if not g.passed)
        outcome = RESPONSE_DELIVERY_INVALID if first in ("REQUEST_VALIDITY", "DRAFT_INTEGRITY", "PRESENTATION_INTEGRITY") else RESPONSE_DELIVERY_DENIED
        return CostResponseAuthorizationDecision(aid if isinstance(aid, str) else "", outcome, gates, failures,
            denial=CostResponseAuthorizationDenial(failures, first))

    artifact = AuthorizedCostResponseArtifact(
        aid, source.presentation_id, draft.source_execution_id, draft.source_request_id, draft.source_skill_id,
        policy.policy_version, source.presentation_digest, draft.draft_digest, draft.template_id, draft.locale,
        policy.target_channel, draft.draft_text,
    )
    return CostResponseAuthorizationDecision(
        aid, RESPONSE_DELIVERY_ELIGIBLE, gates, ("ALL_AUTHORIZATION_GATES_PASSED",),
        authorized_artifact=artifact, response_delivery_eligible=True,
        source_presentation_generated=True, source_executed=True, source_calculated=True,
    )


def authorize_cost_responses(
    requests: Iterable[Any], policy: CostResponseAuthorizationPolicy | None = None,
) -> CostResponseAuthorizationBatch:
    policy = CostResponseAuthorizationPolicy() if policy is None else policy
    if type(policy) is not CostResponseAuthorizationPolicy:
        raise ValueError("policy must be CostResponseAuthorizationPolicy")
    try: items = tuple(requests)
    except TypeError: items = (requests,)
    raw = [x.authorization_id if type(x) is CostResponseAuthorizationRequest else None for x in items]
    duplicates = {x for x in raw if isinstance(x, str) and raw.count(x) > 1}
    decisions = []
    for item in items:
        decision = authorize_cost_response(item, policy)
        if decision.authorization_id in duplicates:
            reasons = ("DUPLICATE_OR_CONFLICTING_AUTHORIZATION_ID",)
            gates = tuple(_gate(name, reasons if name == "REQUEST_VALIDITY" else
                                (("DELIVERY_NOT_ELIGIBLE",) if name == "DELIVERY_ELIGIBILITY" else ()))
                          for name in GATE_ORDER)
            all_reasons = reasons + ("DELIVERY_NOT_ELIGIBLE",)
            decision = CostResponseAuthorizationDecision(decision.authorization_id, RESPONSE_DELIVERY_INVALID,
                gates, all_reasons, denial=CostResponseAuthorizationDenial(all_reasons, "REQUEST_VALIDITY"))
        decisions.append(decision)
    return CostResponseAuthorizationBatch(policy.policy_version, tuple(decisions))
