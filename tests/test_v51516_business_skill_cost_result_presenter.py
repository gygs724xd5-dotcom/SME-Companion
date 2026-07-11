import dataclasses

import pytest

from brain.business_skill_cost_execution import CostExecutionRequest, execute_cost_skill
from brain.business_skill_cost_result_presenter import *
from brain.business_skill_limited_activation_gateway import (LIMITED_ACTIVATION_GATEWAY_VERSION,
    SUPPORTED_ACTIVATION_SCOPE, LimitedActivationRequest, decide_limited_activation)

NOW = "2026-07-11T12:00:00+07:00"

def execution(skill="cost.change_analysis.v1", values=None, eid="e1", rid="r1"):
    values = values or ({"previous_cost": 20, "current_cost": 24} if "change" in skill else {"total_cost": 1000, "unit_quantity": 100})
    evidence = {k: {"value": v, "confidence": 1.0, "source": "current_turn", "freshness": "current", "user_confirmed": True} for k, v in values.items()}
    msg = "cost changed" if "change" in skill else "cost per unit"
    decision = decide_limited_activation(LimitedActivationRequest(rid, msg, evidence, NOW, skill, SUPPORTED_ACTIVATION_SCOPE, LIMITED_ACTIVATION_GATEWAY_VERSION))
    return execute_cost_skill(CostExecutionRequest(eid, rid, skill, decision))

def present(source=None, **kw):
    source = source or execution()
    request = CostPresentationRequest(kw.get("pid", "p1"), kw.get("eid", source.execution_id), kw.get("rid", source.request_id),
        kw.get("skill", source.requested_skill_id), source, kw.get("locale", "th-TH"), kw.get("channel", INTERNAL_DRAFT_ONLY), kw.get("version", PRESENTATION_VERSION))
    return present_cost_result(request)

@pytest.mark.parametrize("previous,current,text", [
    (20,24,"ต้นทุนเดิม: 20.00\nต้นทุนปัจจุบัน: 24.00\nผลต่างต้นทุน: 4.00\nเปอร์เซ็นต์การเปลี่ยนแปลง: 20.00%\nทิศทาง: เพิ่มขึ้น"),
    (24,20,"ต้นทุนเดิม: 24.00\nต้นทุนปัจจุบัน: 20.00\nผลต่างต้นทุน: -4.00\nเปอร์เซ็นต์การเปลี่ยนแปลง: -16.67%\nทิศทาง: ลดลง"),
    (20,20,"ต้นทุนเดิม: 20.00\nต้นทุนปัจจุบัน: 20.00\nผลต่างต้นทุน: 0.00\nเปอร์เซ็นต์การเปลี่ยนแปลง: 0.00%\nทิศทาง: ไม่เปลี่ยนแปลง"),
    (0,5,"ต้นทุนเดิม: 0.00\nต้นทุนปัจจุบัน: 5.00\nผลต่างต้นทุน: 5.00\nไม่สามารถคำนวณเปอร์เซ็นต์การเปลี่ยนแปลงจากต้นทุนเดิมที่เป็นศูนย์ได้\nทิศทาง: เพิ่มขึ้น"),
    (-20,-24,"ต้นทุนเดิม: -20.00\nต้นทุนปัจจุบัน: -24.00\nผลต่างต้นทุน: -4.00\nเปอร์เซ็นต์การเปลี่ยนแปลง: 20.00%\nทิศทาง: ลดลง"),
])
def test_exact_change_templates(previous, current, text):
    result = present(execution(values={"previous_cost": previous, "current_cost": current}))
    assert result.outcome == PRESENTATION_DRAFTED and result.draft.template_id == "COST_CHANGE_TH_V1"
    assert result.draft.draft_text.encode() == text.encode()
    assert tuple(x.name for x in result.draft.fields) == ("previous_cost","current_cost","absolute_change","percentage_change","direction")

@pytest.mark.parametrize("total,quantity,cpu", [(1000,100,"10.00"),(1,6,"0.17")])
def test_exact_per_unit(total, quantity, cpu):
    result = present(execution("cost.per_unit_calculation.v1", {"total_cost": total, "unit_quantity": quantity}))
    assert result.draft.draft_text == f"ต้นทุนรวม: {total:,.2f}\nจำนวนหน่วย: {quantity:,.2f}\nต้นทุนต่อหน่วย: {cpu}"
    assert tuple(x.name for x in result.draft.fields) == ("total_cost","unit_quantity","cost_per_unit")
    assert "ของเสีย" not in result.draft.draft_text

def test_determinism_authority_and_immutability():
    source = execution(); first = present(source); second = present(source)
    assert first == second
    assert verify_cost_response_draft_integrity(first.draft)
    assert verify_cost_presentation_result_integrity(first)
    assert first.presentation_generated and first.internal_draft_only and first.source_executed and first.source_calculated
    assert not any(getattr(first, x) for x in ("business_reasoning_generated","runtime_routed","tools_invoked","persisted","follow_up_generated","response_generated","response_committed"))
    with pytest.raises(dataclasses.FrozenInstanceError): first.draft.draft_text = "evil"

@pytest.mark.parametrize("change,reason", [
    ({"outcome":"EXECUTION_DENIED"}, "SOURCE_NOT_EXECUTED"), ({"executed":False}, "SOURCE_EXECUTION_FLAGS_INVALID"),
    ({"execution_id":"other"}, "EXECUTION_BINDING_MISMATCH"), ({"requested_skill_id":"other"}, "SKILL_IDENTITY_MISMATCH"),
    ({"formula_id":"evil"}, "FORMULA_ID_MISMATCH"), ({"response_generated":True}, "SOURCE_AUTHORITY_LEAKAGE"),
])
def test_tampered_sources_denied(change, reason):
    source = dataclasses.replace(execution(), **change)
    result = present(source, eid="e1", rid="r1", skill="cost.change_analysis.v1")
    assert result.outcome == PRESENTATION_DENIED and reason in result.reason_codes and result.draft is None
    assert not result.presentation_generated and not result.internal_draft_only
    assert verify_cost_presentation_result_integrity(result)

@pytest.mark.parametrize("metrics,reason", [
    (lambda m: m[:-1], "MISSING_METRICS"), (lambda m: m+(m[-1],), "DUPLICATE_METRICS"),
    (lambda m: (dataclasses.replace(m[0], value="20"),)+m[1:], "NONCANONICAL_DECIMAL:previous_cost"),
    (lambda m: m[:3]+(dataclasses.replace(m[3], value="NaN"),)+m[4:], "NONCANONICAL_DECIMAL:percentage_change"),
    (lambda m: m[:4]+(dataclasses.replace(m[4], value="UP"),), "INVALID_DIRECTION"),
])
def test_schema_defects_invalid(metrics, reason):
    source=execution(); result=present(dataclasses.replace(source, metrics=metrics(source.metrics)))
    assert result.outcome == PRESENTATION_INVALID and reason in result.reason_codes
    assert verify_cost_presentation_result_integrity(result)

def test_request_policy_batch_and_injection_boundaries():
    source=execution()
    assert present(source, pid="").outcome == PRESENTATION_INVALID
    assert present(source, locale="en-US").outcome == PRESENTATION_DENIED
    assert present(source, channel="USER").outcome == PRESENTATION_DENIED
    assert present(source, version="x").outcome == PRESENTATION_INVALID
    batch=present_cost_results((CostPresentationRequest("same","e1","r1",source.requested_skill_id,source,"th-TH",INTERNAL_DRAFT_ONLY,PRESENTATION_VERSION),)*2)
    assert all(x.outcome == PRESENTATION_INVALID for x in batch.results)
    with pytest.raises(TypeError): CostPresentationRequest("p","e","r",source.requested_skill_id,source,"th-TH",INTERNAL_DRAFT_ONLY,PRESENTATION_VERSION, template="evil")
    with pytest.raises(ValueError): CostPresentationPolicy(currency_scale=3)

def test_contract_versions_registry_and_no_runtime_imports():
    from brain.business_skill import LIMITED_ACTIVE
    from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
    assert BUSINESS_SKILL_REGISTRY_VERSION == "5.15.13"
    assert HISTORICAL_PRESENTATION_VERSION == "5.15.16" and PRESENTATION_VERSION == "5.15.16.1"
    assert sum(x.active_status == LIMITED_ACTIVE for x in get_business_skill_registry()) == 2
    source = open("brain/business_skill_cost_result_presenter.py", encoding="utf-8").read()
    assert "import app" not in source and "execute_cost_skill" not in source
