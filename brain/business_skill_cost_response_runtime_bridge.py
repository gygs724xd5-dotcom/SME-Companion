"""V5.15.20 isolated, feature-gated cost-response runtime handoff bridge.

Consumes canonical V5.15.18 and V5.15.19.1 artifacts only.  It never routes or
delivers a response. SHA-256 is deterministic integrity binding, not a
signature, MAC, caller authentication, or identical-replay protection.  The
trusted artifact boundary remains required; no nonce store is maintained.
"""
from __future__ import annotations

from dataclasses import dataclass
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
    COST_RESPONSE_AUTHORIZATION_VERSION, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE,
)
from brain.business_skill_cost_response_delivery_qualification import (
    ALL_DELIVERY_READINESS_GATES_PASSED, BINDING_SCHEMA_VERSION,
    COST_DELIVERY_QUALIFICATION_VERSION,
    READY_FOR_FEATURE_GATED_DELIVERY_INTEGRATION,
    CostDeliveryQualificationRecommendation, CostDeliveryQualificationResult,
    verify_cost_delivery_qualification_result_integrity,
)

COST_RUNTIME_BRIDGE_VERSION = "5.15.20"
SUPPORTED_REGISTRY_VERSION = "5.15.13"
FEATURE_GATE_NAME = "LIMITED_COST_RESPONSE_RUNTIME_BRIDGE"
FEATURE_GATED_HANDOFF_ONLY = "FEATURE_GATED_HANDOFF_ONLY"
RUNTIME_HANDOFF_PREPARED = "RUNTIME_HANDOFF_PREPARED"
RUNTIME_HANDOFF_DENIED = "RUNTIME_HANDOFF_DENIED"
RUNTIME_HANDOFF_INVALID = "RUNTIME_HANDOFF_INVALID"
ALL_RUNTIME_BRIDGE_GATES_PASSED = "ALL_RUNTIME_BRIDGE_GATES_PASSED"
SUPPORTED_LOCALE = "th-TH"
GATE_ORDER = ("REQUEST_VALIDITY", "FEATURE_GATE", "QUALIFICATION_RESULT",
    "QUALIFICATION_PROVENANCE", "ADAPTER_RESULT_INTEGRITY", "PAYLOAD_INTEGRITY",
    "IDENTITY_BINDING", "SCOPE_AND_CHANNEL", "CONTENT_BOUNDARY",
    "AUTHORITY_BOUNDARY", "HANDOFF_CONSTRUCTION", "RUNTIME_ISOLATION")
_SKILLS = frozenset(("cost.change_analysis.v1", "cost.per_unit_calculation.v1"))
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_FALSE_FLAGS = ("runtime_routed", "response_generated", "response_delivered",
    "response_committed", "persisted", "tools_invoked", "follow_up_generated",
    "business_reasoning_executed", "skill_executed", "calculated",
    "presentation_generated", "response_authorized")

@dataclass(frozen=True)
class CostRuntimeBridgePolicy:
    bridge_version: str = COST_RUNTIME_BRIDGE_VERSION
    registry_version: str = SUPPORTED_REGISTRY_VERSION
    required_adapter_version: str = COST_RESPONSE_ADAPTER_VERSION
    required_qualification_version: str = COST_DELIVERY_QUALIFICATION_VERSION
    required_binding_schema_version: str = BINDING_SCHEMA_VERSION
    required_authorization_version: str = COST_RESPONSE_AUTHORIZATION_VERSION
    scope: str = LIMITED_COST_RESPONSE
    channel: str = USER_TEXT_RESPONSE
    input_mode: str = PREPARED_ONLY
    handoff_mode: str = FEATURE_GATED_HANDOFF_ONLY
    feature_gate_name: str = FEATURE_GATE_NAME
    enabled_by_default: bool = False
    deny_by_default: bool = True
    def __post_init__(self):
        expected=(COST_RUNTIME_BRIDGE_VERSION,SUPPORTED_REGISTRY_VERSION,COST_RESPONSE_ADAPTER_VERSION,
            COST_DELIVERY_QUALIFICATION_VERSION,BINDING_SCHEMA_VERSION,COST_RESPONSE_AUTHORIZATION_VERSION,
            LIMITED_COST_RESPONSE,USER_TEXT_RESPONSE,PREPARED_ONLY,FEATURE_GATED_HANDOFF_ONLY,
            FEATURE_GATE_NAME,False,True)
        if tuple(getattr(self,x) for x in self.__dataclass_fields__) != expected:
            raise ValueError("unsupported, malformed, or weakened runtime bridge policy")

@dataclass(frozen=True)
class CostRuntimeBridgeRequest:
    bridge_request_id: Any
    feature_gates: Any
    adapter_result: Any
    qualification_result: Any
    scope: Any = LIMITED_COST_RESPONSE
    channel: Any = USER_TEXT_RESPONSE
    input_mode: Any = PREPARED_ONLY
    handoff_mode: Any = FEATURE_GATED_HANDOFF_ONLY
    runtime_routed: Any = False; response_generated: Any = False
    response_delivered: Any = False; response_committed: Any = False
    persisted: Any = False; tools_invoked: Any = False
    follow_up_generated: Any = False; business_reasoning_executed: Any = False
    skill_executed: Any = False; calculated: Any = False
    presentation_generated: Any = False; response_authorized: Any = False

@dataclass(frozen=True)
class CostRuntimeBridgeGateResult:
    gate: str; passed: bool; reason_codes: tuple[str,...]

@dataclass(frozen=True)
class CostRuntimeHandoff:
    bridge_version: str; bridge_request_id: str; qualification_version: str
    qualification_id: str; qualification_digest: str; adapter_version: str
    adapter_request_id: str; payload_digest: str; authorization_version: str
    authorization_id: str; presentation_id: str; execution_id: str
    request_id: str; skill_id: str; registry_version: str; scope: str
    locale: str; channel: str; input_mode: str; handoff_mode: str; text: str
    presentation_digest: str; draft_digest: str
    runtime_handoff_prepared: bool; feature_gate_passed: bool; source_delivery_ready: bool
    runtime_routed: bool; response_generated: bool; response_delivered: bool
    response_committed: bool; persisted: bool; tools_invoked: bool
    follow_up_generated: bool; business_reasoning_executed: bool
    skill_executed: bool; calculated: bool; presentation_generated: bool
    response_authorized: bool; handoff_digest: str

@dataclass(frozen=True)
class CostRuntimeBridgeDenial:
    reason_codes: tuple[str,...]; first_failed_gate: str

@dataclass(frozen=True)
class CostRuntimeBridgeResult:
    bridge_request_id: str; outcome: str
    gate_results: tuple[CostRuntimeBridgeGateResult,...]; reason_codes: tuple[str,...]
    handoff: CostRuntimeHandoff|None = None; denial: CostRuntimeBridgeDenial|None = None
    runtime_handoff_prepared: bool = False; feature_gate_passed: bool = False
    source_delivery_ready: bool = False
    runtime_routed: bool = False; response_generated: bool = False
    response_delivered: bool = False; response_committed: bool = False
    persisted: bool = False; tools_invoked: bool = False
    follow_up_generated: bool = False; business_reasoning_executed: bool = False
    skill_executed: bool = False; calculated: bool = False
    presentation_generated: bool = False; response_authorized: bool = False
    result_digest: str = ""

@dataclass(frozen=True)
class CostRuntimeBridgeBatch:
    bridge_version: str; results: tuple[CostRuntimeBridgeResult,...]

def _digest(material):
    try:
        raw=json.dumps(material,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    except (TypeError,ValueError,UnicodeEncodeError):
        return ""
    return hashlib.sha256(raw).hexdigest()
def _material(obj, omitted): return {x:getattr(obj,x) for x in obj.__dataclass_fields__ if x not in omitted}
def _gate(name,reasons):
    codes=tuple(dict.fromkeys(reasons)); return CostRuntimeBridgeGateResult(name,not codes,codes or ("PASSED",))
def _unsafe(text): return any(c!="\n" and unicodedata.category(c)=="Cc" for c in text)

def verify_cost_runtime_handoff_integrity(handoff: Any) -> bool:
    try:
        if type(handoff) is not CostRuntimeHandoff: return False
        if (handoff.bridge_version,handoff.qualification_version,handoff.adapter_version,
            handoff.authorization_version,handoff.registry_version,handoff.scope,handoff.locale,
            handoff.channel,handoff.input_mode,handoff.handoff_mode)!=(COST_RUNTIME_BRIDGE_VERSION,
            COST_DELIVERY_QUALIFICATION_VERSION,COST_RESPONSE_ADAPTER_VERSION,
            COST_RESPONSE_AUTHORIZATION_VERSION,SUPPORTED_REGISTRY_VERSION,LIMITED_COST_RESPONSE,
            SUPPORTED_LOCALE,USER_TEXT_RESPONSE,PREPARED_ONLY,FEATURE_GATED_HANDOFF_ONLY): return False
        ids=(handoff.bridge_request_id,handoff.qualification_id,handoff.adapter_request_id,
            handoff.authorization_id,handoff.presentation_id,handoff.execution_id,
            handoff.request_id,handoff.skill_id)
        if any(type(x) is not str or not _ID.fullmatch(x) for x in ids) or handoff.skill_id not in _SKILLS: return False
        if any(type(x) is not str or not _HEX.fullmatch(x) for x in (handoff.qualification_digest,
            handoff.payload_digest,handoff.presentation_digest,handoff.draft_digest,handoff.handoff_digest)): return False
        if type(handoff.text) is not str or not handoff.text.strip() or len(handoff.text)>MAX_RESPONSE_LENGTH or _unsafe(handoff.text): return False
        if not all(type(getattr(handoff,x)) is bool for x in ("runtime_handoff_prepared","feature_gate_passed","source_delivery_ready")+_FALSE_FLAGS): return False
        if not all(getattr(handoff,x) for x in ("runtime_handoff_prepared","feature_gate_passed","source_delivery_ready")): return False
        if any(getattr(handoff,x) for x in _FALSE_FLAGS): return False
        return handoff.handoff_digest==_digest(_material(handoff,{"handoff_digest"}))
    except (AttributeError,TypeError,ValueError): return False

def _result_material(result):
    return {"bridge_request_id":result.bridge_request_id,"outcome":result.outcome,
        "gate_results":tuple((g.gate,g.passed,g.reason_codes) for g in result.gate_results),
        "reason_codes":result.reason_codes,"handoff_digest":result.handoff.handoff_digest if result.handoff else None,
        **{x:getattr(result,x) for x in ("runtime_handoff_prepared","feature_gate_passed","source_delivery_ready")+_FALSE_FLAGS}}

def verify_cost_runtime_bridge_result_integrity(result: Any) -> bool:
    try:
        if type(result) is not CostRuntimeBridgeResult or tuple(g.gate for g in result.gate_results)!=GATE_ORDER: return False
        if any(type(g) is not CostRuntimeBridgeGateResult or g.passed!=(g.reason_codes==("PASSED",)) for g in result.gate_results): return False
        if result.result_digest!=_digest(_result_material(result)): return False
        if result.outcome==RUNTIME_HANDOFF_PREPARED:
            return (result.reason_codes==(ALL_RUNTIME_BRIDGE_GATES_PASSED,) and result.denial is None
                and all(g.passed for g in result.gate_results) and verify_cost_runtime_handoff_integrity(result.handoff)
                and result.runtime_handoff_prepared and result.feature_gate_passed and result.source_delivery_ready
                and not any(getattr(result,x) for x in _FALSE_FLAGS))
        return (result.outcome in (RUNTIME_HANDOFF_DENIED,RUNTIME_HANDOFF_INVALID) and result.handoff is None
            and type(result.denial) is CostRuntimeBridgeDenial and not result.runtime_handoff_prepared
            and not result.feature_gate_passed and not result.source_delivery_ready
            and not any(getattr(result,x) for x in _FALSE_FLAGS)
            and result.denial.reason_codes==result.reason_codes
            and result.denial.first_failed_gate==next(g.gate for g in result.gate_results if not g.passed))
    except (AttributeError,TypeError,ValueError,StopIteration): return False

def bridge_prepared_cost_response(request: Any, policy: CostRuntimeBridgePolicy|None=None) -> CostRuntimeBridgeResult:
    policy=CostRuntimeBridgePolicy() if policy is None else policy
    if type(policy) is not CostRuntimeBridgePolicy: raise ValueError("policy must be CostRuntimeBridgePolicy")
    valid=type(request) is CostRuntimeBridgeRequest
    brid=getattr(request,"bridge_request_id","") if valid else ""
    adapter=getattr(request,"adapter_result",None) if valid else None
    qual=getattr(request,"qualification_result",None) if valid else None
    payload=adapter.payload if type(adapter) is CostResponseAdapterResult else None
    binding=qual.binding if type(qual) is CostDeliveryQualificationResult else None
    validity=[]
    if not valid: validity.append("MALFORMED_BRIDGE_REQUEST")
    if type(brid) is not str or not _ID.fullmatch(brid): validity.append("INVALID_BRIDGE_REQUEST_ID")
    fg=[]
    gates=getattr(request,"feature_gates",None)
    if type(gates) is not dict: fg.append("FEATURE_GATE_MISSING_OR_MALFORMED")
    elif set(gates)!={FEATURE_GATE_NAME}: fg.append("UNKNOWN_GLOBAL_OR_WILDCARD_FEATURE_GATE")
    elif type(gates[FEATURE_GATE_NAME]) is not bool: fg.append("FEATURE_GATE_MALFORMED")
    elif not gates[FEATURE_GATE_NAME]: fg.append("FEATURE_GATE_DISABLED")
    qr=[]
    if not verify_cost_delivery_qualification_result_integrity(qual): qr.append("QUALIFICATION_RESULT_INTEGRITY_FAILED")
    elif (qual.recommendation!=CostDeliveryQualificationRecommendation(READY_FOR_FEATURE_GATED_DELIVERY_INTEGRATION,ALL_DELIVERY_READINESS_GATES_PASSED)
          or qual.reason_codes!=(ALL_DELIVERY_READINESS_GATES_PASSED,)): qr.append("QUALIFICATION_NOT_DELIVERY_READY")
    qp=[]
    if binding is None: qp.append("MISSING_QUALIFICATION_BINDING")
    else:
        if binding.qualification_version!=policy.required_qualification_version: qp.append("QUALIFICATION_VERSION_MISMATCH")
        if binding.binding_schema_version!=policy.required_binding_schema_version: qp.append("BINDING_SCHEMA_VERSION_MISMATCH")
    ari=[] if verify_cost_response_adapter_result_integrity(adapter) else ["ADAPTER_RESULT_INTEGRITY_FAILED"]
    pi=[] if verify_prepared_cost_response_payload_integrity(payload) else ["PAYLOAD_INTEGRITY_FAILED"]
    identity=[]
    if binding is not None and payload is not None and type(adapter) is CostResponseAdapterResult:
        pairs=((binding.adapter_request_id,adapter.adapter_request_id),(binding.adapter_version,payload.adapter_version),
            (binding.adapter_outcome,adapter.outcome),(binding.payload_digest,payload.payload_digest),
            (binding.payload_authorization_id,payload.source_authorization_id),(binding.payload_presentation_id,payload.source_presentation_id),
            (binding.payload_execution_id,payload.source_execution_id),(binding.payload_request_id,payload.source_request_id),
            (binding.payload_skill_id,payload.source_skill_id),(binding.skill_id,payload.source_skill_id),
            (binding.presentation_digest,payload.presentation_digest),(binding.draft_digest,payload.draft_digest))
        if any(a!=b for a,b in pairs): identity.append("QUALIFICATION_ADAPTER_BINDING_MISMATCH")
    else: identity.append("IDENTITY_BINDING_UNAVAILABLE")
    sc=[]
    if valid and (request.scope,request.channel,request.input_mode,request.handoff_mode)!=(policy.scope,policy.channel,policy.input_mode,policy.handoff_mode): sc.append("SCOPE_CHANNEL_OR_MODE_MISMATCH")
    if binding is not None and payload is not None and (binding.scope,binding.locale,binding.target_channel,binding.output_mode)!=(payload.scope,payload.locale,payload.target_channel,payload.output_mode): sc.append("QUALIFICATION_PAYLOAD_SCOPE_MISMATCH")
    if payload is not None and (payload.scope,payload.locale,payload.target_channel,payload.output_mode,payload.authorization_policy_version)!=(policy.scope,SUPPORTED_LOCALE,policy.channel,policy.input_mode,policy.required_authorization_version): sc.append("CANONICAL_VERSION_SCOPE_OR_CHANNEL_MISMATCH")
    content=[]; text=getattr(payload,"text",None)
    if type(text) is not str or not text.strip(): content.append("EMPTY_OR_MALFORMED_TEXT")
    elif len(text)>MAX_RESPONSE_LENGTH: content.append("TEXT_TOO_LONG")
    elif _unsafe(text): content.append("MALFORMED_TEXT")
    authority=[]
    if valid and any(getattr(request,x) is not False for x in _FALSE_FLAGS): authority.append("CALLER_AUTHORITY_INJECTION")
    if binding is not None and any(getattr(binding,x) for x in ("response_generated","response_committed","runtime_routed","persisted","tools_invoked","follow_up_generated","business_reasoning_executed","execution_performed","calculation_performed","presentation_rendered","authorization_performed")): authority.append("QUALIFICATION_AUTHORITY_LEAKAGE")
    if payload is not None and any(getattr(payload,x) for x in ("response_generated","response_committed","runtime_routed","persisted","tools_invoked","follow_up_generated","business_reasoning_executed","execution_performed","calculation_performed","presentation_rendered","authorization_performed")): authority.append("ADAPTER_AUTHORITY_LEAKAGE")
    groups=[validity,fg,qr,qp,ari,pi,identity,sc,content,authority]
    construct=[] if not any(groups) else ["HANDOFF_NOT_CONSTRUCTED"]
    isolation=[] if not any(groups) else ["RUNTIME_ISOLATION_NOT_ESTABLISHED"]
    groups.extend((construct,isolation)); gate_results=tuple(_gate(n,r) for n,r in zip(GATE_ORDER,groups))
    failures=tuple(c for g in gate_results for c in g.reason_codes if c!="PASSED")
    if failures:
        first=next(g.gate for g in gate_results if not g.passed)
        out=RUNTIME_HANDOFF_INVALID if first in ("REQUEST_VALIDITY","QUALIFICATION_RESULT","QUALIFICATION_PROVENANCE","ADAPTER_RESULT_INTEGRITY","PAYLOAD_INTEGRITY","IDENTITY_BINDING") else RUNTIME_HANDOFF_DENIED
        result=CostRuntimeBridgeResult(brid,out,gate_results,failures,denial=CostRuntimeBridgeDenial(failures,first))
        return CostRuntimeBridgeResult(**{**_material(result,{"result_digest"}),"result_digest":_digest(_result_material(result))})
    values=dict(bridge_version=COST_RUNTIME_BRIDGE_VERSION,bridge_request_id=brid,
        qualification_version=binding.qualification_version,qualification_id=binding.qualification_id,
        qualification_digest=binding.qualification_digest,adapter_version=payload.adapter_version,
        adapter_request_id=adapter.adapter_request_id,payload_digest=payload.payload_digest,
        authorization_version=payload.authorization_policy_version,authorization_id=payload.source_authorization_id,
        presentation_id=payload.source_presentation_id,execution_id=payload.source_execution_id,
        request_id=payload.source_request_id,skill_id=payload.source_skill_id,registry_version=SUPPORTED_REGISTRY_VERSION,
        scope=payload.scope,locale=payload.locale,channel=payload.target_channel,input_mode=payload.output_mode,
        handoff_mode=policy.handoff_mode,text=payload.text,presentation_digest=payload.presentation_digest,
        draft_digest=payload.draft_digest,runtime_handoff_prepared=True,feature_gate_passed=True,source_delivery_ready=True,
        **{x:False for x in _FALSE_FLAGS})
    handoff=CostRuntimeHandoff(**values,handoff_digest=_digest(values))
    result=CostRuntimeBridgeResult(brid,RUNTIME_HANDOFF_PREPARED,gate_results,(ALL_RUNTIME_BRIDGE_GATES_PASSED,),
        handoff=handoff,runtime_handoff_prepared=True,feature_gate_passed=True,source_delivery_ready=True)
    return CostRuntimeBridgeResult(**{**_material(result,{"result_digest"}),"result_digest":_digest(_result_material(result))})

def bridge_prepared_cost_responses(requests: Iterable[Any], policy: CostRuntimeBridgePolicy|None=None) -> CostRuntimeBridgeBatch:
    try: items=tuple(requests)
    except TypeError: items=(requests,)
    ids=[x.bridge_request_id for x in items if type(x) is CostRuntimeBridgeRequest]
    dup={x for x in ids if ids.count(x)>1}
    results=[]
    for item in items:
        result=bridge_prepared_cost_response(item,policy)
        if result.bridge_request_id in dup:
            groups=[["DUPLICATE_BRIDGE_REQUEST_ID"]]+[[] for _ in GATE_ORDER[1:-2]]+[["HANDOFF_NOT_CONSTRUCTED"],["RUNTIME_ISOLATION_NOT_ESTABLISHED"]]
            gs=tuple(_gate(n,r) for n,r in zip(GATE_ORDER,groups)); reasons=tuple(c for g in gs for c in g.reason_codes if c!="PASSED")
            result=CostRuntimeBridgeResult(result.bridge_request_id,RUNTIME_HANDOFF_INVALID,gs,reasons,denial=CostRuntimeBridgeDenial(reasons,"REQUEST_VALIDITY"))
            result=CostRuntimeBridgeResult(**{**_material(result,{"result_digest"}),"result_digest":_digest(_result_material(result))})
        results.append(result)
    return CostRuntimeBridgeBatch(COST_RUNTIME_BRIDGE_VERSION,tuple(results))
