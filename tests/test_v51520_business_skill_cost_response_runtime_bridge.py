"""V5.15.20 isolated runtime bridge contract tests."""
import dataclasses
from pathlib import Path
import pytest

from brain.business_skill_cost_response_runtime_bridge import *
from brain.business_skill_cost_response_delivery_qualification import qualify_cost_response_delivery
from tests.test_v51519_business_skill_cost_response_delivery_qualification import NOW, make

def artifacts(skill="cost.change_analysis.v1", suffix="1"):
    case=make(skill,suffix)
    q=qualify_cost_response_delivery((case,),qualification_id="qual"+suffix,reference_time=NOW).results[0]
    return case.adapter_result,q

def request(skill="cost.change_analysis.v1",suffix="1",**kw):
    a,q=artifacts(skill,suffix)
    return CostRuntimeBridgeRequest(kw.pop("bridge_request_id","bridge"+suffix),
        kw.pop("feature_gates",{FEATURE_GATE_NAME:True}),kw.pop("adapter_result",a),
        kw.pop("qualification_result",q),**kw)

@pytest.mark.parametrize("skill,suffix",(("cost.change_analysis.v1","1"),("cost.per_unit_calculation.v1","2")))
def test_positive_exact_deterministic_handoff_for_both_skills(skill,suffix):
    req=request(skill,suffix); first=bridge_prepared_cost_response(req); second=bridge_prepared_cost_response(req)
    assert first==second and first.outcome==RUNTIME_HANDOFF_PREPARED
    assert first.handoff.text.encode("utf-8")==req.adapter_result.payload.text.encode("utf-8")
    assert first.handoff.skill_id==skill and tuple(x.gate for x in first.gate_results)==GATE_ORDER
    assert verify_cost_runtime_handoff_integrity(first.handoff)
    assert verify_cost_runtime_bridge_result_integrity(first)
    assert first.runtime_handoff_prepared and first.feature_gate_passed and first.source_delivery_ready
    assert first.feature_gate_name==first.handoff.feature_gate_name==FEATURE_GATE_NAME
    assert not any(getattr(first,x) for x in ("runtime_routed","response_generated","response_delivered",
        "response_committed","persisted","tools_invoked","follow_up_generated",
        "business_reasoning_executed","skill_executed","calculated","presentation_generated",
        "response_authorized"))

@pytest.mark.parametrize("gates,reason",((None,"FEATURE_GATE_MISSING_OR_MALFORMED"),({},"UNKNOWN_GLOBAL_OR_WILDCARD_FEATURE_GATE"),
    ({FEATURE_GATE_NAME:False},"FEATURE_GATE_DISABLED"),({FEATURE_GATE_NAME:1},"FEATURE_GATE_MALFORMED"),
    ({"UNKNOWN":True},"UNKNOWN_GLOBAL_OR_WILDCARD_FEATURE_GATE"),({"*":True},"UNKNOWN_GLOBAL_OR_WILDCARD_FEATURE_GATE"),
    ({"GLOBAL":True},"UNKNOWN_GLOBAL_OR_WILDCARD_FEATURE_GATE"),({FEATURE_GATE_NAME:True,"OTHER":False},"UNKNOWN_GLOBAL_OR_WILDCARD_FEATURE_GATE")))
def test_feature_gate_fail_closed(gates,reason):
    result=bridge_prepared_cost_response(request(feature_gates=gates))
    assert result.handoff is None and reason in result.reason_codes and verify_cost_runtime_bridge_result_integrity(result)

def test_default_policy_disabled_deny_by_default_and_exact_versions():
    p=CostRuntimeBridgePolicy()
    assert not p.enabled_by_default and p.deny_by_default
    assert HISTORICAL_COST_RUNTIME_BRIDGE_VERSION=="5.15.20"
    assert (p.bridge_version,p.required_adapter_version,p.required_qualification_version,p.required_binding_schema_version,p.required_authorization_version,p.registry_version)==("5.15.20.1","5.15.18","5.15.19.1","5.15.19.1","5.15.17.1","5.15.13")

@pytest.mark.parametrize("mutator,reason",(
    (lambda r:dataclasses.replace(r,qualification_result=None),"QUALIFICATION_RESULT_INTEGRITY_FAILED"),
    (lambda r:dataclasses.replace(r,qualification_result=dataclasses.replace(r.qualification_result,binding=None)),"QUALIFICATION_RESULT_INTEGRITY_FAILED"),
    (lambda r:dataclasses.replace(r,qualification_result=dataclasses.replace(r.qualification_result,qualification_id="other")),"QUALIFICATION_RESULT_INTEGRITY_FAILED"),
    (lambda r:dataclasses.replace(r,adapter_result=None),"ADAPTER_RESULT_INTEGRITY_FAILED"),
    (lambda r:dataclasses.replace(r,adapter_result=dataclasses.replace(r.adapter_result,payload=None)),"ADAPTER_RESULT_INTEGRITY_FAILED"),
    (lambda r:dataclasses.replace(r,adapter_result=dataclasses.replace(r.adapter_result,payload=dataclasses.replace(r.adapter_result.payload,payload_digest="0"*64))),"ADAPTER_RESULT_INTEGRITY_FAILED"),
    (lambda r:dataclasses.replace(r,scope="GLOBAL"),"SCOPE_CHANNEL_OR_MODE_MISMATCH"),
    (lambda r:dataclasses.replace(r,channel="OTHER"),"SCOPE_CHANNEL_OR_MODE_MISMATCH"),
    (lambda r:dataclasses.replace(r,input_mode="OTHER"),"SCOPE_CHANNEL_OR_MODE_MISMATCH"),
    (lambda r:dataclasses.replace(r,handoff_mode="ROUTE"),"SCOPE_CHANNEL_OR_MODE_MISMATCH"),
    (lambda r:dataclasses.replace(r,runtime_routed=True),"CALLER_AUTHORITY_INJECTION"),
    (lambda r:dataclasses.replace(r,response_authorized=True),"CALLER_AUTHORITY_INJECTION"),
))
def test_negative_integrity_scope_mode_and_authority(mutator,reason):
    result=bridge_prepared_cost_response(mutator(request()))
    assert result.handoff is None and reason in result.reason_codes
    assert verify_cost_runtime_bridge_result_integrity(result)

def test_historical_version_schema_forgery_and_recommendation_fail():
    r=request(); b=r.qualification_result.binding
    for changed in (dataclasses.replace(b,qualification_version="5.15.19"),
                    dataclasses.replace(b,binding_schema_version="5.15.19"),
                    dataclasses.replace(b,recommendation="OTHER")):
        q=dataclasses.replace(r.qualification_result,binding=changed)
        result=bridge_prepared_cost_response(dataclasses.replace(r,qualification_result=q))
        assert result.handoff is None and "QUALIFICATION_RESULT_INTEGRITY_FAILED" in result.reason_codes

def test_cross_request_same_skill_cross_skill_and_payload_substitution():
    one=request(suffix="1"); same=request(suffix="2"); other=request("cost.per_unit_calculation.v1","3")
    for q in (same.qualification_result,other.qualification_result):
        result=bridge_prepared_cost_response(dataclasses.replace(one,qualification_result=q))
        assert result.handoff is None and "QUALIFICATION_ADAPTER_BINDING_MISMATCH" in result.reason_codes
    result=bridge_prepared_cost_response(dataclasses.replace(one,adapter_result=same.adapter_result))
    assert result.handoff is None and "QUALIFICATION_ADAPTER_BINDING_MISMATCH" in result.reason_codes

def test_unsupported_skill_and_content_boundaries_fail_closed():
    r=request(); p=r.adapter_result.payload
    for text in ("","   ","x"*(MAX_RESPONSE_LENGTH+1),"bad\x00text"):
        badp=dataclasses.replace(p,text=text)
        result=bridge_prepared_cost_response(dataclasses.replace(r,adapter_result=dataclasses.replace(r.adapter_result,payload=badp)))
        assert result.handoff is None
    badp=dataclasses.replace(p,source_skill_id="other")
    assert bridge_prepared_cost_response(dataclasses.replace(r,adapter_result=dataclasses.replace(r.adapter_result,payload=badp))).handoff is None

def test_duplicate_order_no_cross_case_leakage_and_mutation_safety():
    a=request(suffix="2"); b=request(suffix="1"); before=(a,b)
    batch=bridge_prepared_cost_responses(before)
    assert [x.bridge_request_id for x in batch.results]==["bridge2","bridge1"] and before==(a,b)
    dup=bridge_prepared_cost_responses((a,dataclasses.replace(b,bridge_request_id="bridge2")))
    assert all(x.handoff is None and "DUPLICATE_BRIDGE_REQUEST_ID" in x.reason_codes for x in dup.results)

def test_frozen_contracts_and_post_construction_tampering():
    result=bridge_prepared_cost_response(request()); h=result.handoff
    for obj in (CostRuntimeBridgePolicy(),request(),result.gate_results[0],h,result,
                CostRuntimeBridgeBatch(COST_RUNTIME_BRIDGE_VERSION,(result,)),CostRuntimeBridgeDenial(("x",),"REQUEST_VALIDITY")):
        with pytest.raises((dataclasses.FrozenInstanceError,AttributeError)): obj.bridge_request_id="changed"
    assert not verify_cost_runtime_handoff_integrity(dataclasses.replace(h,text=h.text+"x"))
    assert not verify_cost_runtime_handoff_integrity(dataclasses.replace(h,handoff_digest="0"*64))
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(result,result_digest="0"*64))
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(result,handoff=dataclasses.replace(h,text="tamper")))

def test_denied_invalid_results_never_have_usable_handoff():
    for req in (None,request(feature_gates={FEATURE_GATE_NAME:False}),request(adapter_result=None)):
        result=bridge_prepared_cost_response(req)
        assert result.handoff is None and not result.runtime_handoff_prepared
        assert result.feature_gate_name is None and not result.feature_gate_passed

def test_no_forbidden_imports_calls_state_or_environment_fallback():
    source=(Path(__file__).parents[1]/"brain"/"business_skill_cost_response_runtime_bridge.py").read_text(encoding="utf-8")
    forbidden=("import app","import router","import planner","import workflow","import os","getenv(","environ",
        "limited_activation_gateway","cost_execution","cost_result_presenter","authorize_cost_response(",
        "adapt_authorized_cost_response(","qualify_cost_response_delivery(","execute_cost_skill(","present_cost_result(")
    assert all(x not in source for x in forbidden)
    assert "verify_cost_delivery_qualification_result_integrity(qual)" in source
    assert "signature, MAC, caller authentication, or identical-replay protection" in source
