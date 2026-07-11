"""V5.15.19 cost response delivery-readiness qualification tests."""
import dataclasses
from pathlib import Path
import pytest
from brain.business_skill_cost_execution import CostExecutionRequest, execute_cost_skill
from brain.business_skill_cost_result_presenter import INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION, SUPPORTED_LOCALE, CostPresentationRequest, present_cost_result
from brain.business_skill_limited_activation_gateway import LIMITED_ACTIVATION_GATEWAY_VERSION, SUPPORTED_ACTIVATION_SCOPE, LimitedActivationRequest, decide_limited_activation
from brain.business_skill_cost_response_authorization import AUTHORIZATION_POLICY_VERSION, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE, CostResponseAuthorizationRequest, authorize_cost_response
from brain.business_skill_cost_response_adapter import CostResponseAdapterRequest, adapt_authorized_cost_response
from brain.business_skill_cost_response_delivery_qualification import *

NOW="2026-07-12T12:00:00+07:00"
def make(skill="cost.change_analysis.v1", suffix="1"):
    vals={"previous_cost":20,"current_cost":24} if "change" in skill else {"total_cost":1000,"unit_quantity":4}
    evidence={k:{"value":v,"confidence":1.0,"source":"current_turn","freshness":"current","user_confirmed":True} for k,v in vals.items()}
    rid,eid,pid,aid,arid=(x+suffix for x in ("r","e","p","a","ar"))
    text="cost changed" if "change" in skill else "cost per unit"
    g=decide_limited_activation(LimitedActivationRequest(rid,text,evidence,NOW,skill,SUPPORTED_ACTIVATION_SCOPE,LIMITED_ACTIVATION_GATEWAY_VERSION))
    e=execute_cost_skill(CostExecutionRequest(eid,rid,skill,g))
    p=present_cost_result(CostPresentationRequest(pid,eid,rid,skill,e,SUPPORTED_LOCALE,INTERNAL_DRAFT_ONLY,PRESENTATION_VERSION))
    a=authorize_cost_response(CostResponseAuthorizationRequest(aid,pid,eid,rid,skill,p,LIMITED_COST_RESPONSE,USER_TEXT_RESPONSE,AUTHORIZATION_POLICY_VERSION))
    result=adapt_authorized_cost_response(CostResponseAdapterRequest(arid,a))
    return CostDeliveryQualificationCase("case"+suffix,rid,skill,eid,pid,aid,arid,a,result,result)

def test_both_skills_are_ready_using_real_canonical_adapter_results():
    batch=qualify_cost_response_delivery((make("cost.per_unit_calculation.v1","2"),make()),qualification_id="q1",reference_time=NOW)
    assert [x.skill_id for x in batch.results]==["cost.change_analysis.v1","cost.per_unit_calculation.v1"]
    assert all(x.recommendation==CostDeliveryQualificationRecommendation(READY_FOR_FEATURE_GATED_DELIVERY_INTEGRATION,ALL_DELIVERY_READINESS_GATES_PASSED) for x in batch.results)
    assert all(tuple(g.gate for g in x.gate_results)==GATE_ORDER for x in batch.results)
    assert all(not any((x.runtime_routed,x.response_delivered,x.response_generated,x.response_committed,x.persisted,x.tools_invoked)) for x in batch.results)

@pytest.mark.parametrize("qid,ref",(("",NOW),(" bad",NOW),(None,NOW),("q",""),("q","not-time"),("q","2026-01-01T00:00:00")))
def test_explicit_ids_and_time_are_required(qid,ref):
    with pytest.raises(ValueError): qualify_cost_response_delivery((make(),),qualification_id=qid,reference_time=ref)

@pytest.mark.parametrize("mutation,reason",(
    (lambda c:dataclasses.replace(c,adapter_result=dataclasses.replace(c.adapter_result,payload=None)),"ADAPTER_RESULT_INTEGRITY_FAILED"),
    (lambda c:dataclasses.replace(c,adapter_result=dataclasses.replace(c.adapter_result,payload=dataclasses.replace(c.adapter_result.payload,payload_digest="0"*64))),"PAYLOAD_INTEGRITY_FAILED"),
    (lambda c:dataclasses.replace(c,request_id="other"),"IDENTITY_BINDING_MISMATCH"),
    (lambda c:dataclasses.replace(c,skill_id="cost.per_unit_calculation.v1"),"IDENTITY_BINDING_MISMATCH"),
    (lambda c:dataclasses.replace(c,caller_input_unchanged=False),"CALLER_INPUT_MUTATED"),
    (lambda c:dataclasses.replace(c,response_committed=True),"FORGED_OR_LEAKED_AUTHORITY_STATE"),
    (lambda c:dataclasses.replace(c,runtime_routed=True),"FORGED_OR_LEAKED_AUTHORITY_STATE"),
    (lambda c:dataclasses.replace(c,deterministic_comparison_result=None),"NONDETERMINISTIC_RESULT"),
))
def test_negative_paths_fail_closed(mutation,reason):
    r=qualify_cost_response_delivery((mutation(make()),),qualification_id="q",reference_time=NOW).results[0]
    assert r.recommendation is None and reason in r.reason_codes

def test_replaced_payload_cross_request_and_source_digest_fail():
    one,two=make(suffix="1"),make(suffix="2")
    replaced=dataclasses.replace(one,adapter_result=dataclasses.replace(one.adapter_result,payload=two.adapter_result.payload))
    r=qualify_cost_response_delivery((replaced,),qualification_id="q",reference_time=NOW).results[0]
    assert "SOURCE_AUTHORIZATION_BINDING_MISMATCH" in r.reason_codes and "IDENTITY_BINDING_MISMATCH" in r.reason_codes
    p=one.adapter_result.payload
    tampered=dataclasses.replace(one,adapter_result=dataclasses.replace(one.adapter_result,payload=dataclasses.replace(p,presentation_digest="0"*64)))
    assert "PAYLOAD_INTEGRITY_FAILED" in qualify_cost_response_delivery((tampered,),qualification_id="q",reference_time=NOW).results[0].reason_codes

def test_duplicate_order_determinism_frozen_and_no_mutation():
    a,b=make(suffix="2"),make(suffix="1"); before=(a,b)
    first=qualify_cost_response_delivery(before,qualification_id="q",reference_time=NOW)
    second=qualify_cost_response_delivery(reversed(before),qualification_id="q",reference_time=NOW)
    assert first==second and before==(a,b)
    dup=qualify_cost_response_delivery((a,dataclasses.replace(b,case_id=a.case_id)),qualification_id="q",reference_time=NOW)
    assert all("DUPLICATE_CASE_ID" in x.reason_codes for x in dup.results)
    for obj in (CostDeliveryQualificationPolicy(),a,first.results[0].gate_results[0],first.results[0].recommendation,first.results[0],first):
        with pytest.raises((dataclasses.FrozenInstanceError,AttributeError)): obj.version="x"

def test_authority_and_import_audit():
    source=(Path(__file__).parents[1]/"brain"/"business_skill_cost_response_delivery_qualification.py").read_text(encoding="utf-8")
    forbidden=("import app","import router","import planner","import workflow","limited_activation_gateway","cost_execution","cost_result_presenter","authorize_cost_response(","adapt_authorized_cost_response(","execute_cost_skill(","present_cost_result(")
    assert all(x not in source for x in forbidden)
    assert "signature/MAC, replay defence, or proof against untrusted artifact fabrication" in source
