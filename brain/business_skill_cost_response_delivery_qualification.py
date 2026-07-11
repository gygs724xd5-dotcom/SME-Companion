"""V5.15.19 diagnostic qualification for prepared cost-response delivery.

This module only recommends feature-gated integration.  It performs no runtime
delivery operation.  Canonical SHA-256 digests are integrity bindings, not a
signature/MAC, replay defence, or proof against untrusted artifact fabrication.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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

QUALIFICATION_VERSION = "5.15.19"
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
class CostDeliveryQualificationResult:
    qualification_id: str; reference_time: str; case_id: str; skill_id: str
    gate_results: tuple[CostDeliveryQualificationGateResult, ...]
    reason_codes: tuple[str, ...]
    recommendation: CostDeliveryQualificationRecommendation | None = None
    denial: CostDeliveryQualificationDenial | None = None
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
    return CostDeliveryQualificationResult(qid,ref,cid,skill,gates,(ALL_DELIVERY_READINESS_GATES_PASSED,),recommendation=rec)

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
