"""V5.15.19 diagnostic qualification for prepared cost-response delivery.

This module only recommends feature-gated integration.  It performs no runtime
delivery operation.  Canonical SHA-256 digests are integrity bindings, not a
signature/MAC, replay defence, or proof against untrusted artifact fabrication.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable

from brain.business_skill_cost_response_adapter import (
    COST_RESPONSE_ADAPTER_VERSION, MAX_RESPONSE_LENGTH, PREPARED_ONLY,
    RESPONSE_PAYLOAD_PREPARED, CostResponseAdapterResult,
    verify_cost_response_adapter_result_integrity,
    verify_prepared_cost_response_payload_integrity,
)
from brain.business_skill_cost_response_authorization import (
    COST_RESPONSE_AUTHORIZATION_VERSION, LIMITED_COST_RESPONSE,
    RESPONSE_DELIVERY_ELIGIBLE, USER_TEXT_RESPONSE,
    AuthorizedCostResponseArtifact, CostResponseAuthorizationDecision,
)

HISTORICAL_COST_DELIVERY_QUALIFICATION_VERSION = "5.15.19"
COST_DELIVERY_QUALIFICATION_VERSION = "5.15.19.1"
QUALIFICATION_VERSION = COST_DELIVERY_QUALIFICATION_VERSION
BINDING_SCHEMA_VERSION = "5.15.19.1"
READY_FOR_FEATURE_GATED_DELIVERY_INTEGRATION = "READY_FOR_FEATURE_GATED_DELIVERY_INTEGRATION"
DELIVERY_INTEGRATION_NOT_READY = "DELIVERY_INTEGRATION_NOT_READY"
ALL_DELIVERY_READINESS_GATES_PASSED = "ALL_DELIVERY_READINESS_GATES_PASSED"
SUPPORTED_LOCALE = "th-TH"
GATE_ORDER = ("REQUEST_VALIDITY", "ADAPTER_RESULT_INTEGRITY", "PAYLOAD_INTEGRITY",
              "SOURCE_AUTHORIZATION_BINDING", "IDENTITY_BINDING", "SCOPE_AND_CHANNEL",
              "OUTPUT_MODE", "CONTENT_BOUNDARY", "DETERMINISM", "MUTATION_SAFETY",
              "AUTHORITY_BOUNDARY", "DELIVERY_COMPATIBILITY")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SKILLS = frozenset(("cost.change_analysis.v1", "cost.per_unit_calculation.v1"))

@dataclass(frozen=True)
class CostDeliveryQualificationPolicy:
    version: str = QUALIFICATION_VERSION
    required_authorization_version: str = COST_RESPONSE_AUTHORIZATION_VERSION
    required_adapter_version: str = COST_RESPONSE_ADAPTER_VERSION
    required_authorization_scope: str = LIMITED_COST_RESPONSE
    required_target_channel: str = USER_TEXT_RESPONSE
    required_output_mode: str = PREPARED_ONLY
    required_locale: str = SUPPORTED_LOCALE
    maximum_text_length: int = MAX_RESPONSE_LENGTH
    deny_by_default: bool = True
    def __post_init__(self):
        if tuple(getattr(self, x) for x in self.__dataclass_fields__) != (QUALIFICATION_VERSION, COST_RESPONSE_AUTHORIZATION_VERSION, COST_RESPONSE_ADAPTER_VERSION, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE, PREPARED_ONLY, SUPPORTED_LOCALE, MAX_RESPONSE_LENGTH, True):
            raise ValueError("unsupported, malformed, or weakened qualification policy")

@dataclass(frozen=True)
class CostDeliveryQualificationCase:
    case_id: Any
    request_id: Any
    skill_id: Any
    execution_id: Any
    presentation_id: Any
    authorization_id: Any
    adapter_request_id: Any
    authorization_decision: Any
    adapter_result: Any
    deterministic_comparison_result: Any
    caller_input_unchanged: Any = True
    response_generated: Any = False
    response_committed: Any = False
    runtime_routed: Any = False
    persisted: Any = False
    tools_invoked: Any = False
    follow_up_generated: Any = False
    business_reasoning_executed: Any = False
    execution_performed: Any = False
    calculation_performed: Any = False
    presentation_rendered: Any = False
    authorization_performed: Any = False

@dataclass(frozen=True)
class CostDeliveryQualificationGateResult:
    gate: str; passed: bool; reason_codes: tuple[str, ...]
@dataclass(frozen=True)
class CostDeliveryQualificationRecommendation:
    recommendation: str; reason: str
@dataclass(frozen=True)
class CostDeliveryQualificationDenial:
    reason_codes: tuple[str, ...]; first_failed_gate: str
@dataclass(frozen=True)
class CostDeliveryQualificationBinding:
    binding_schema_version: str
    qualification_version: str
    qualification_id: str
    reference_time: str
    case_id: str
    skill_id: str
    adapter_version: str
    adapter_request_id: str
    adapter_outcome: str
    payload_digest: str
    payload_authorization_id: str
    payload_presentation_id: str
    payload_execution_id: str
    payload_request_id: str
    payload_skill_id: str
    presentation_digest: str
    draft_digest: str
    scope: str
    locale: str
    target_channel: str
    output_mode: str
    recommendation: str
    gate_snapshot: tuple[tuple[str, bool, tuple[str, ...]], ...]
    reason_codes: tuple[str, ...]
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
    qualification_digest: str
@dataclass(frozen=True)
class CostDeliveryQualificationResult:
    qualification_id: str; reference_time: str; case_id: str; skill_id: str
    gate_results: tuple[CostDeliveryQualificationGateResult, ...]
    reason_codes: tuple[str, ...]
    recommendation: CostDeliveryQualificationRecommendation | None = None
    denial: CostDeliveryQualificationDenial | None = None
    binding: CostDeliveryQualificationBinding | None = None
    runtime_routed: bool = False; response_delivered: bool = False
    response_generated: bool = False; response_committed: bool = False
    persisted: bool = False; tools_invoked: bool = False
@dataclass(frozen=True)
class CostDeliveryQualificationBatch:
    version: str; qualification_id: str; reference_time: str
    results: tuple[CostDeliveryQualificationResult, ...]

def _gate(name, reasons):
    codes = tuple(dict.fromkeys(reasons))
    return CostDeliveryQualificationGateResult(name, not codes, codes or ("PASSED",))
def _unsafe(text): return any(c != "\n" and unicodedata.category(c) == "Cc" for c in text)
def _valid_ref(value):
    if not isinstance(value, str) or not value or value != value.strip(): return False
    try: parsed = datetime.fromisoformat(value)
    except ValueError: return False
    return parsed.tzinfo is not None

_HEX = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_FIELDS = ("response_generated", "response_committed", "runtime_routed",
    "persisted", "tools_invoked", "follow_up_generated", "business_reasoning_executed",
    "execution_performed", "calculation_performed", "presentation_rendered",
    "authorization_performed")

def _canonical_reference_time(value):
    parsed = datetime.fromisoformat(value)
    return parsed.isoformat(timespec="seconds")

def _binding_material(binding):
    return {name: getattr(binding, name) for name in binding.__dataclass_fields__
            if name != "qualification_digest"}

def _binding_digest(material):
    encoded = json.dumps(material, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def verify_cost_delivery_qualification_binding(binding: Any) -> bool:
    try:
        if type(binding) is not CostDeliveryQualificationBinding: return False
        if (binding.binding_schema_version != BINDING_SCHEMA_VERSION or
                binding.qualification_version != COST_DELIVERY_QUALIFICATION_VERSION): return False
        if not _valid_ref(binding.reference_time) or binding.reference_time != _canonical_reference_time(binding.reference_time): return False
        ids = (binding.qualification_id, binding.case_id, binding.skill_id,
               binding.adapter_request_id, binding.payload_authorization_id,
               binding.payload_presentation_id, binding.payload_execution_id,
               binding.payload_request_id, binding.payload_skill_id)
        if any(type(x) is not str or not _ID.fullmatch(x) for x in ids): return False
        if binding.skill_id not in _SKILLS or binding.payload_skill_id != binding.skill_id: return False
        if binding.adapter_version != COST_RESPONSE_ADAPTER_VERSION or binding.adapter_outcome != RESPONSE_PAYLOAD_PREPARED: return False
        if any(type(x) is not str or not _HEX.fullmatch(x) for x in
               (binding.payload_digest, binding.presentation_digest, binding.draft_digest,
                binding.qualification_digest)): return False
        if (binding.scope, binding.locale, binding.target_channel, binding.output_mode) != (
                LIMITED_COST_RESPONSE, SUPPORTED_LOCALE, USER_TEXT_RESPONSE, PREPARED_ONLY): return False
        if binding.recommendation != READY_FOR_FEATURE_GATED_DELIVERY_INTEGRATION: return False
        if type(binding.gate_snapshot) is not tuple or len(binding.gate_snapshot) != len(GATE_ORDER): return False
        if tuple(x[0] for x in binding.gate_snapshot) != GATE_ORDER or len(set(x[0] for x in binding.gate_snapshot)) != len(GATE_ORDER): return False
        for item in binding.gate_snapshot:
            if type(item) is not tuple or len(item) != 3 or type(item[1]) is not bool or type(item[2]) is not tuple: return False
            if not item[1] or item[2] != ("PASSED",): return False
        if binding.reason_codes != (ALL_DELIVERY_READINESS_GATES_PASSED,) or len(set(binding.reason_codes)) != len(binding.reason_codes): return False
        if any(type(getattr(binding, x)) is not bool or getattr(binding, x) for x in _AUTHORITY_FIELDS): return False
        return binding.qualification_digest == _binding_digest(_binding_material(binding))
    except (AttributeError, TypeError, ValueError, IndexError):
        return False

def verify_cost_delivery_qualification_result_integrity(result: Any) -> bool:
    try:
        if type(result) is not CostDeliveryQualificationResult: return False
        if any(type(x) is not str or not _ID.fullmatch(x) for x in
               (result.qualification_id, result.case_id, result.skill_id)): return False
        if not _valid_ref(result.reference_time): return False
        if tuple(g.gate for g in result.gate_results) != GATE_ORDER or len(set(g.gate for g in result.gate_results)) != len(GATE_ORDER): return False
        if any(type(g) is not CostDeliveryQualificationGateResult or type(g.passed) is not bool or
               type(g.reason_codes) is not tuple or not g.reason_codes or
               len(set(g.reason_codes)) != len(g.reason_codes) or
               any(type(code) is not str or not code for code in g.reason_codes) or
               (g.passed != (g.reason_codes == ("PASSED",)))
               for g in result.gate_results): return False
        if type(result.reason_codes) is not tuple or not result.reason_codes or len(set(result.reason_codes)) != len(result.reason_codes): return False
        qualified = result.recommendation == CostDeliveryQualificationRecommendation(
            READY_FOR_FEATURE_GATED_DELIVERY_INTEGRATION, ALL_DELIVERY_READINESS_GATES_PASSED)
        if qualified:
            b = result.binding
            return (result.denial is None and result.reason_codes == (ALL_DELIVERY_READINESS_GATES_PASSED,)
                    and all(g.passed and g.reason_codes == ("PASSED",) for g in result.gate_results)
                    and verify_cost_delivery_qualification_binding(b)
                    and (b.qualification_id, b.reference_time, b.case_id, b.skill_id) ==
                        (result.qualification_id, result.reference_time, result.case_id, result.skill_id)
                    and b.gate_snapshot == tuple((g.gate, g.passed, g.reason_codes) for g in result.gate_results)
                    and b.reason_codes == result.reason_codes
                    and not any(getattr(result, x) for x in ("runtime_routed", "response_delivered",
                        "response_generated", "response_committed", "persisted", "tools_invoked")))
        failures = tuple(code for gate in result.gate_results for code in gate.reason_codes if code != "PASSED")
        return (result.binding is None and result.recommendation is None and
                type(result.denial) is CostDeliveryQualificationDenial and failures == result.reason_codes
                and result.denial.reason_codes == result.reason_codes
                and result.denial.first_failed_gate == next(g.gate for g in result.gate_results if not g.passed)
                and not any(getattr(result, x) for x in ("runtime_routed", "response_delivered",
                    "response_generated", "response_committed", "persisted", "tools_invoked")))
    except (AttributeError, TypeError, ValueError, StopIteration):
        return False

def _qualify(case, qid, ref, policy, duplicate):
    typed = type(case) is CostDeliveryQualificationCase
    result = case.adapter_result if typed else None
    payload = result.payload if type(result) is CostResponseAdapterResult else None
    decision = case.authorization_decision if typed else None
    artifact = decision.authorized_artifact if type(decision) is CostResponseAuthorizationDecision else None
    validity=[]
    if not typed: validity.append("MALFORMED_QUALIFICATION_CASE")
    for name in ("case_id","request_id","skill_id","execution_id","presentation_id","authorization_id","adapter_request_id"):
        if not isinstance(getattr(case,name,None),str) or not _ID.fullmatch(getattr(case,name,"")): validity.append("INVALID_"+name.upper())
    if getattr(case,"case_id",None) in duplicate: validity.append("DUPLICATE_CASE_ID")
    ri=[] if verify_cost_response_adapter_result_integrity(result) else ["ADAPTER_RESULT_INTEGRITY_FAILED"]
    pi=[] if verify_prepared_cost_response_payload_integrity(payload) else ["PAYLOAD_INTEGRITY_FAILED"]
    source=[]
    if type(decision) is not CostResponseAuthorizationDecision or type(artifact) is not AuthorizedCostResponseArtifact: source.append("MISSING_SOURCE_AUTHORIZATION")
    else:
        if decision.outcome != RESPONSE_DELIVERY_ELIGIBLE or not decision.response_delivery_eligible or decision.denial is not None: source.append("SOURCE_AUTHORIZATION_NOT_ELIGIBLE")
        if payload is not None:
            pairs=(("source_authorization_id","authorization_id"),("source_presentation_id","source_presentation_id"),("source_execution_id","source_execution_id"),("source_request_id","source_request_id"),("source_skill_id","source_skill_id"),("presentation_digest","presentation_integrity_digest"),("draft_digest","draft_integrity_digest"),("text","authorized_text"))
            if any(getattr(payload,a,None)!=getattr(artifact,b,None) for a,b in pairs): source.append("SOURCE_AUTHORIZATION_BINDING_MISMATCH")
            if isinstance(payload.text,str) and isinstance(artifact.authorized_text,str) and payload.text.encode("utf-8") != artifact.authorized_text.encode("utf-8"): source.append("AUTHORIZED_TEXT_BYTE_MISMATCH")
    identity=[]
    if payload is not None:
        pairs=(("source_request_id","request_id"),("source_skill_id","skill_id"),("source_execution_id","execution_id"),("source_presentation_id","presentation_id"),("source_authorization_id","authorization_id"),("adapter_request_id","adapter_request_id"))
        if any(getattr(payload,a,None)!=getattr(case,b,None) for a,b in pairs): identity.append("IDENTITY_BINDING_MISMATCH")
    scope=[]
    if payload is not None and (payload.scope!=policy.required_authorization_scope or payload.target_channel!=policy.required_target_channel or payload.locale!=policy.required_locale): scope.append("SCOPE_CHANNEL_OR_LOCALE_MISMATCH")
    output=[] if payload is not None and payload.output_mode==policy.required_output_mode else ["OUTPUT_MODE_MISMATCH"]
    content=[]
    text=getattr(payload,"text",None)
    if not isinstance(text,str) or not text.strip(): content.append("EMPTY_OR_MALFORMED_TEXT")
    elif len(text)>policy.maximum_text_length: content.append("TEXT_TOO_LONG")
    elif _unsafe(text): content.append("MALFORMED_TEXT")
    deterministic=[] if typed and case.deterministic_comparison_result == result else ["NONDETERMINISTIC_RESULT"]
    mutation=[] if typed and case.caller_input_unchanged is True else ["CALLER_INPUT_MUTATED"]
    authority=[]
    forbidden=("response_generated","response_committed","runtime_routed","persisted","tools_invoked","follow_up_generated","business_reasoning_executed","execution_performed","calculation_performed","presentation_rendered","authorization_performed")
    if typed and any(getattr(case,x) is not False for x in forbidden): authority.append("FORGED_OR_LEAKED_AUTHORITY_STATE")
    if result is not None and any(getattr(result,x,False) for x in forbidden): authority.append("ADAPTER_AUTHORITY_LEAKAGE")
    compatibility=[]
    if payload is None or getattr(payload,"adapter_version",None)!=policy.required_adapter_version: compatibility.append("ADAPTER_VERSION_MISMATCH")
    if payload is None or getattr(payload,"authorization_policy_version",None)!=policy.required_authorization_version: compatibility.append("AUTHORIZATION_VERSION_MISMATCH")
    if getattr(case,"skill_id",None) not in _SKILLS: compatibility.append("UNSUPPORTED_COST_SKILL")
    if result is None or result.outcome!=RESPONSE_PAYLOAD_PREPARED: compatibility.append("PAYLOAD_NOT_PREPARED")
    groups=(validity,ri,pi,source,identity,scope,output,content,deterministic,mutation,authority,compatibility)
    gates=tuple(_gate(n,x) for n,x in zip(GATE_ORDER,groups)); failures=tuple(c for g in gates for c in g.reason_codes if c!="PASSED")
    cid=getattr(case,"case_id","") if isinstance(getattr(case,"case_id",None),str) else ""
    skill=getattr(case,"skill_id","") if isinstance(getattr(case,"skill_id",None),str) else ""
    if failures: return CostDeliveryQualificationResult(qid,ref,cid,skill,gates,failures,denial=CostDeliveryQualificationDenial(failures,next(g.gate for g in gates if not g.passed)))
    rec=CostDeliveryQualificationRecommendation(READY_FOR_FEATURE_GATED_DELIVERY_INTEGRATION,ALL_DELIVERY_READINESS_GATES_PASSED)
    reason_codes=(ALL_DELIVERY_READINESS_GATES_PASSED,)
    canonical_ref=_canonical_reference_time(ref)
    values=dict(binding_schema_version=BINDING_SCHEMA_VERSION,
        qualification_version=COST_DELIVERY_QUALIFICATION_VERSION,
        qualification_id=qid, reference_time=canonical_ref, case_id=cid, skill_id=skill,
        adapter_version=payload.adapter_version, adapter_request_id=result.adapter_request_id,
        adapter_outcome=result.outcome, payload_digest=payload.payload_digest,
        payload_authorization_id=payload.source_authorization_id,
        payload_presentation_id=payload.source_presentation_id,
        payload_execution_id=payload.source_execution_id, payload_request_id=payload.source_request_id,
        payload_skill_id=payload.source_skill_id, presentation_digest=payload.presentation_digest,
        draft_digest=payload.draft_digest, scope=payload.scope, locale=payload.locale,
        target_channel=payload.target_channel, output_mode=payload.output_mode,
        recommendation=rec.recommendation,
        gate_snapshot=tuple((g.gate,g.passed,g.reason_codes) for g in gates),
        reason_codes=reason_codes, **{name:getattr(result,name) for name in _AUTHORITY_FIELDS})
    binding=CostDeliveryQualificationBinding(**values,qualification_digest=_binding_digest(values))
    return CostDeliveryQualificationResult(qid,canonical_ref,cid,skill,gates,reason_codes,recommendation=rec,binding=binding)

def qualify_cost_response_delivery(cases: Iterable[Any], *, qualification_id: str, reference_time: str, policy: CostDeliveryQualificationPolicy|None=None):
    if not isinstance(qualification_id,str) or not _ID.fullmatch(qualification_id): raise ValueError("explicit valid qualification_id is required")
    if not _valid_ref(reference_time): raise ValueError("explicit timezone-aware reference_time is required")
    policy=CostDeliveryQualificationPolicy() if policy is None else policy
    if type(policy) is not CostDeliveryQualificationPolicy: raise ValueError("policy must be CostDeliveryQualificationPolicy")
    try: items=tuple(cases)
    except TypeError: items=(cases,)
    ids=[x.case_id for x in items if type(x) is CostDeliveryQualificationCase]
    duplicates={x for x in ids if ids.count(x)>1}
    ordered=tuple(sorted(items,key=lambda x:(str(getattr(x,"skill_id","")),str(getattr(x,"case_id","")))))
    return CostDeliveryQualificationBatch(QUALIFICATION_VERSION,qualification_id,reference_time,tuple(_qualify(x,qualification_id,reference_time,policy,duplicates) for x in ordered))
