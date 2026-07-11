"""V5.15.18 deterministic, prepared-only cost response adapter.

This boundary consumes only the V5.15.17.1 authorization decision/artifact.  It
does not calculate, execute, present, authorize, route, commit, persist, invoke
tools, or generate follow-up content.  SHA-256 digests are deterministic
integrity bindings, not signatures or authentication.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable

from brain.business_skill_cost_response_authorization import (
    COST_RESPONSE_AUTHORIZATION_VERSION,
    LIMITED_COST_RESPONSE,
    RESPONSE_DELIVERY_ELIGIBLE,
    USER_TEXT_RESPONSE,
    AuthorizedCostResponseArtifact,
    CostResponseAuthorizationDecision,
)

COST_RESPONSE_ADAPTER_VERSION = "5.15.18"
SUPPORTED_REGISTRY_VERSION = "5.15.13"
SUPPORTED_LOCALE = "th-TH"
PREPARED_ONLY = "PREPARED_ONLY"
RESPONSE_PAYLOAD_PREPARED = "RESPONSE_PAYLOAD_PREPARED"
RESPONSE_PAYLOAD_DENIED = "RESPONSE_PAYLOAD_DENIED"
RESPONSE_PAYLOAD_INVALID = "RESPONSE_PAYLOAD_INVALID"
PAYLOAD_SCHEMA_VERSION = "5.15.18"
MAX_RESPONSE_LENGTH = 4000
GATE_ORDER = (
    "REQUEST_VALIDITY", "AUTHORIZATION_RESULT", "AUTHORIZED_ARTIFACT",
    "IDENTITY_BINDING", "VERSION_COMPATIBILITY", "SCOPE_AND_CHANNEL",
    "OUTPUT_MODE", "CONTENT_BOUNDARY", "AUTHORITY_SEPARATION",
    "PAYLOAD_PREPARATION",
)
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SKILLS = frozenset(("cost.change_analysis.v1", "cost.per_unit_calculation.v1"))


@dataclass(frozen=True)
class CostResponseAdapterPolicy:
    policy_version: str = COST_RESPONSE_ADAPTER_VERSION
    supported_authorization_version: str = COST_RESPONSE_AUTHORIZATION_VERSION
    supported_registry_version: str = SUPPORTED_REGISTRY_VERSION
    supported_locale: str = SUPPORTED_LOCALE
    supported_scope: str = LIMITED_COST_RESPONSE
    supported_target_channel: str = USER_TEXT_RESPONSE
    output_mode: str = PREPARED_ONLY
    max_response_length: int = MAX_RESPONSE_LENGTH
    deny_by_default: bool = True

    def __post_init__(self) -> None:
        expected = (COST_RESPONSE_ADAPTER_VERSION, COST_RESPONSE_AUTHORIZATION_VERSION,
                    SUPPORTED_REGISTRY_VERSION, SUPPORTED_LOCALE, LIMITED_COST_RESPONSE,
                    USER_TEXT_RESPONSE, PREPARED_ONLY, MAX_RESPONSE_LENGTH, True)
        if tuple(getattr(self, f) for f in self.__dataclass_fields__) != expected:
            raise ValueError("unsupported, malformed, or weakened adapter policy")


@dataclass(frozen=True)
class CostResponseAdapterRequest:
    adapter_request_id: Any
    authorization_decision: Any
    target_channel: Any = USER_TEXT_RESPONSE
    output_mode: Any = PREPARED_ONLY
    response_generated: Any = False
    response_committed: Any = False
    runtime_routed: Any = False
    persisted: Any = False
    tools_invoked: Any = False
    follow_up_generated: Any = False


@dataclass(frozen=True)
class CostResponseAdapterGateResult:
    gate: str
    passed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class PreparedCostResponsePayload:
    payload_schema_version: str
    adapter_version: str
    adapter_request_id: str
    source_authorization_id: str
    source_presentation_id: str
    source_execution_id: str
    source_request_id: str
    source_skill_id: str
    authorization_policy_version: str
    template_id: str
    locale: str
    target_channel: str
    scope: str
    output_mode: str
    text: str
    presentation_digest: str
    draft_digest: str
    payload_prepared: bool
    response_delivery_eligible: bool
    response_generated: bool
    response_committed: bool
    runtime_routed: bool
    persisted: bool
    tools_invoked: bool
    follow_up_generated: bool
    business_reasoning_executed: bool
    execution_performed: bool
    calculation_performed: bool
    presentation_rendered: bool
    authorization_performed: bool
    payload_digest: str


@dataclass(frozen=True)
class CostResponseAdapterDenial:
    reason_codes: tuple[str, ...]
    first_failed_gate: str


@dataclass(frozen=True)
class CostResponseAdapterResult:
    adapter_request_id: str
    outcome: str
    gate_results: tuple[CostResponseAdapterGateResult, ...]
    reason_codes: tuple[str, ...]
    payload: PreparedCostResponsePayload | None = None
    denial: CostResponseAdapterDenial | None = None
    payload_prepared: bool = False
    response_delivery_eligible: bool = False
    response_generated: bool = False
    response_committed: bool = False
    runtime_routed: bool = False
    persisted: bool = False
    tools_invoked: bool = False
    follow_up_generated: bool = False
    business_reasoning_executed: bool = False
    execution_performed: bool = False
    calculation_performed: bool = False
    presentation_rendered: bool = False
    authorization_performed: bool = False


@dataclass(frozen=True)
class CostResponseAdapterBatch:
    adapter_version: str
    results: tuple[CostResponseAdapterResult, ...]


def _gate(name: str, reasons: Iterable[str]) -> CostResponseAdapterGateResult:
    codes = tuple(dict.fromkeys(reasons))
    return CostResponseAdapterGateResult(name, not codes, codes or ("PASSED",))


def _unsafe_control(text: str) -> bool:
    return any(ch != "\n" and unicodedata.category(ch) == "Cc" for ch in text)


def _payload_material(payload: PreparedCostResponsePayload) -> dict[str, Any]:
    return {name: getattr(payload, name) for name in payload.__dataclass_fields__ if name != "payload_digest"}


def _digest(material: dict[str, Any]) -> str:
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_prepared_cost_response_payload_integrity(payload: Any) -> bool:
    try:
        if type(payload) is not PreparedCostResponsePayload:
            return False
        if payload.payload_schema_version != PAYLOAD_SCHEMA_VERSION or payload.adapter_version != COST_RESPONSE_ADAPTER_VERSION:
            return False
        ids = (payload.adapter_request_id, payload.source_authorization_id,
               payload.source_presentation_id, payload.source_execution_id,
               payload.source_request_id, payload.source_skill_id)
        if any(not isinstance(x, str) or not _ID.fullmatch(x) for x in ids):
            return False
        if payload.source_skill_id not in _SKILLS:
            return False
        if payload.authorization_policy_version != COST_RESPONSE_AUTHORIZATION_VERSION:
            return False
        if (payload.locale, payload.target_channel, payload.scope, payload.output_mode) != (
                SUPPORTED_LOCALE, USER_TEXT_RESPONSE, LIMITED_COST_RESPONSE, PREPARED_ONLY):
            return False
        if not isinstance(payload.text, str) or not payload.text.strip() or len(payload.text) > MAX_RESPONSE_LENGTH or _unsafe_control(payload.text):
            return False
        if any(not isinstance(x, str) or not _DIGEST.fullmatch(x)
               for x in (payload.presentation_digest, payload.draft_digest, payload.payload_digest)):
            return False
        flags = (payload.payload_prepared, payload.response_delivery_eligible,
                 not payload.response_generated, not payload.response_committed,
                 not payload.runtime_routed, not payload.persisted, not payload.tools_invoked,
                 not payload.follow_up_generated, not payload.business_reasoning_executed,
                 not payload.execution_performed, not payload.calculation_performed,
                 not payload.presentation_rendered, not payload.authorization_performed)
        return all(type(x) is bool and x for x in flags) and payload.payload_digest == _digest(_payload_material(payload))
    except (AttributeError, TypeError, ValueError):
        return False


def adapt_authorized_cost_response(request: Any, policy: CostResponseAdapterPolicy | None = None) -> CostResponseAdapterResult:
    policy = CostResponseAdapterPolicy() if policy is None else policy
    if type(policy) is not CostResponseAdapterPolicy:
        raise ValueError("policy must be CostResponseAdapterPolicy")
    valid = type(request) is CostResponseAdapterRequest
    arid = request.adapter_request_id if valid and isinstance(request.adapter_request_id, str) else ""
    source = request.authorization_decision if valid else None
    artifact = source.authorized_artifact if type(source) is CostResponseAuthorizationDecision else None

    validity = [] if valid else ["MALFORMED_ADAPTER_REQUEST"]
    if not isinstance(arid, str) or not _ID.fullmatch(arid): validity.append("INVALID_ADAPTER_REQUEST_ID")
    authorization = []
    if type(source) is not CostResponseAuthorizationDecision: authorization.append("MALFORMED_AUTHORIZATION_DECISION")
    elif source.outcome != RESPONSE_DELIVERY_ELIGIBLE or source.denial is not None or not source.response_delivery_eligible:
        authorization.append("AUTHORIZATION_NOT_ELIGIBLE")
    artifact_gate = [] if type(artifact) is AuthorizedCostResponseArtifact else ["MISSING_OR_FABRICATED_AUTHORIZED_ARTIFACT"]
    binding = []
    if type(source) is CostResponseAuthorizationDecision and type(artifact) is AuthorizedCostResponseArtifact:
        if source.authorization_id != artifact.authorization_id: binding.append("AUTHORIZATION_ID_MISMATCH")
        if not artifact.response_delivery_eligible: binding.append("ARTIFACT_NOT_DELIVERY_ELIGIBLE")
        for name in ("authorization_id", "source_presentation_id", "source_execution_id", "source_request_id", "source_skill_id"):
            if not isinstance(getattr(artifact, name), str) or not _ID.fullmatch(getattr(artifact, name)):
                binding.append("INVALID_ARTIFACT_IDENTITY")
        if artifact.source_skill_id not in _SKILLS: binding.append("UNSUPPORTED_SKILL_IDENTITY")
    version = []
    if type(artifact) is AuthorizedCostResponseArtifact and artifact.authorization_policy_version != policy.supported_authorization_version:
        version.append("AUTHORIZATION_VERSION_MISMATCH")
    scope_channel = []
    if valid and request.target_channel != policy.supported_target_channel: scope_channel.append("TARGET_CHANNEL_MISMATCH")
    if type(artifact) is AuthorizedCostResponseArtifact:
        if artifact.authorization_scope != policy.supported_scope: scope_channel.append("UNSUPPORTED_AUTHORIZATION_SCOPE")
        if artifact.target_channel != policy.supported_target_channel: scope_channel.append("ARTIFACT_TARGET_CHANNEL_MISMATCH")
        if valid and request.target_channel != artifact.target_channel: scope_channel.append("REQUEST_ARTIFACT_CHANNEL_MISMATCH")
        if artifact.locale != policy.supported_locale: scope_channel.append("UNSUPPORTED_LOCALE")
    output = [] if valid and request.output_mode == policy.output_mode else ["OUTPUT_MODE_MISMATCH"]
    content = []
    if type(artifact) is AuthorizedCostResponseArtifact:
        text = artifact.authorized_text
        if not isinstance(text, str) or not text.strip(): content.append("EMPTY_AUTHORIZED_TEXT")
        elif len(text) > policy.max_response_length: content.append("AUTHORIZED_TEXT_TOO_LONG")
        elif _unsafe_control(text): content.append("CONTROL_CHARACTER_NOT_ALLOWED")
        if not _DIGEST.fullmatch(artifact.presentation_integrity_digest or ""): content.append("INVALID_PRESENTATION_DIGEST")
        if not _DIGEST.fullmatch(artifact.draft_integrity_digest or ""): content.append("INVALID_DRAFT_DIGEST")
    authority = []
    if valid and any(getattr(request, x) is not False for x in (
            "response_generated", "response_committed", "runtime_routed", "persisted",
            "tools_invoked", "follow_up_generated")):
        authority.append("CALLER_AUTHORITY_INJECTION")
    if type(source) is CostResponseAuthorizationDecision and any(getattr(source, x, False) for x in (
            "response_generated", "response_committed", "runtime_routed", "persisted",
            "tools_invoked", "follow_up_generated", "execution_performed", "calculation_performed")):
        authority.append("AUTHORIZATION_AUTHORITY_LEAKAGE")

    groups = [validity, authorization, artifact_gate, binding, version, scope_channel,
              output, content, authority]
    preparation = [] if not any(groups) else ["PAYLOAD_NOT_PREPARED"]
    groups.append(preparation)
    gates = tuple(_gate(name, reasons) for name, reasons in zip(GATE_ORDER, groups))
    failures = tuple(code for gate in gates for code in gate.reason_codes if code != "PASSED")
    if failures:
        first = next(g.gate for g in gates if not g.passed)
        outcome = RESPONSE_PAYLOAD_INVALID if first in ("REQUEST_VALIDITY", "AUTHORIZED_ARTIFACT", "IDENTITY_BINDING") else RESPONSE_PAYLOAD_DENIED
        return CostResponseAdapterResult(arid, outcome, gates, failures,
            denial=CostResponseAdapterDenial(failures, first))

    values = dict(
        payload_schema_version=PAYLOAD_SCHEMA_VERSION, adapter_version=COST_RESPONSE_ADAPTER_VERSION,
        adapter_request_id=arid, source_authorization_id=artifact.authorization_id,
        source_presentation_id=artifact.source_presentation_id,
        source_execution_id=artifact.source_execution_id, source_request_id=artifact.source_request_id,
        source_skill_id=artifact.source_skill_id,
        authorization_policy_version=artifact.authorization_policy_version,
        template_id=artifact.template_id, locale=artifact.locale,
        target_channel=artifact.target_channel, scope=artifact.authorization_scope,
        output_mode=request.output_mode, text=artifact.authorized_text,
        presentation_digest=artifact.presentation_integrity_digest,
        draft_digest=artifact.draft_integrity_digest, payload_prepared=True,
        response_delivery_eligible=artifact.response_delivery_eligible,
        response_generated=False, response_committed=False, runtime_routed=False,
        persisted=False, tools_invoked=False, follow_up_generated=False,
        business_reasoning_executed=False, execution_performed=False,
        calculation_performed=False, presentation_rendered=False,
        authorization_performed=False,
    )
    payload = PreparedCostResponsePayload(**values, payload_digest=_digest(values))
    return CostResponseAdapterResult(arid, RESPONSE_PAYLOAD_PREPARED, gates,
        ("ALL_ADAPTER_GATES_PASSED",), payload=payload, payload_prepared=True,
        response_delivery_eligible=True)


def verify_cost_response_adapter_result_integrity(result: Any) -> bool:
    try:
        if type(result) is not CostResponseAdapterResult or tuple(g.gate for g in result.gate_results) != GATE_ORDER:
            return False
        if any(type(g) is not CostResponseAdapterGateResult for g in result.gate_results): return False
        if result.outcome == RESPONSE_PAYLOAD_PREPARED:
            return (result.denial is None and result.reason_codes == ("ALL_ADAPTER_GATES_PASSED",)
                    and all(g.passed and g.reason_codes == ("PASSED",) for g in result.gate_results)
                    and result.payload_prepared and result.response_delivery_eligible
                    and verify_prepared_cost_response_payload_integrity(result.payload)
                    and result.adapter_request_id == result.payload.adapter_request_id
                    and not any(getattr(result, x) for x in ("response_generated", "response_committed",
                        "runtime_routed", "persisted", "tools_invoked", "follow_up_generated",
                        "business_reasoning_executed", "execution_performed", "calculation_performed",
                        "presentation_rendered", "authorization_performed")))
        return (result.outcome in (RESPONSE_PAYLOAD_DENIED, RESPONSE_PAYLOAD_INVALID)
                and result.payload is None and result.denial is not None
                and not result.payload_prepared and not result.response_delivery_eligible
                and not any(getattr(result, x) for x in ("response_generated", "response_committed",
                    "runtime_routed", "persisted", "tools_invoked", "follow_up_generated",
                    "business_reasoning_executed", "execution_performed", "calculation_performed",
                    "presentation_rendered", "authorization_performed"))
                and result.denial.reason_codes == result.reason_codes
                and result.denial.first_failed_gate == next(g.gate for g in result.gate_results if not g.passed))
    except (AttributeError, StopIteration, TypeError):
        return False


def adapt_authorized_cost_responses(requests: Iterable[Any], policy: CostResponseAdapterPolicy | None = None) -> CostResponseAdapterBatch:
    policy = CostResponseAdapterPolicy() if policy is None else policy
    if type(policy) is not CostResponseAdapterPolicy: raise ValueError("policy must be CostResponseAdapterPolicy")
    try: items = tuple(requests)
    except TypeError: items = (requests,)
    raw = [x.adapter_request_id if type(x) is CostResponseAdapterRequest else None for x in items]
    duplicates = {x for x in raw if isinstance(x, str) and raw.count(x) > 1}
    results = []
    for item in items:
        result = adapt_authorized_cost_response(item, policy)
        if result.adapter_request_id in duplicates:
            reasons = ("DUPLICATE_ADAPTER_REQUEST_ID", "PAYLOAD_NOT_PREPARED")
            gates = tuple(_gate(name, ("DUPLICATE_ADAPTER_REQUEST_ID",) if name == "REQUEST_VALIDITY"
                                else (("PAYLOAD_NOT_PREPARED",) if name == "PAYLOAD_PREPARATION" else ()))
                          for name in GATE_ORDER)
            result = CostResponseAdapterResult(result.adapter_request_id, RESPONSE_PAYLOAD_INVALID,
                gates, reasons, denial=CostResponseAdapterDenial(reasons, "REQUEST_VALIDITY"))
        results.append(result)
    return CostResponseAdapterBatch(COST_RESPONSE_ADAPTER_VERSION, tuple(results))
