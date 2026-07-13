"""V5.15.23 controlled runtime integration admission gateway."""
import dataclasses
from pathlib import Path
import pytest

from brain.business_skill_cost_runtime_integration_admission_gateway import *
from brain.business_skill_cost_runtime_integration_manifest import create_controlled_integration_manifest
from tests.test_v51522_controlled_runtime_integration_manifest import qualifications

def manifest(): return create_controlled_integration_manifest(qualifications())
def request(skill="cost.change_analysis.v1", source=None):
    return ControlledRuntimeIntegrationAdmissionRequest(skill, source or manifest())

@pytest.mark.parametrize("skill", SUPPORTED_SKILL_IDS)
def test_happy_path_deterministic_immutable_and_exact_lookup(skill):
    r=request(skill); one=decide_controlled_runtime_integration_admission(r); two=decide_controlled_runtime_integration_admission(r)
    assert one == two and one.admitted and one.primary_denial_code is None
    assert one.gate_results == tuple(AdmissionGateResult(x,True,"PASSED") for x in ADMISSION_GATE_ORDER)
    assert verify_controlled_runtime_integration_admission_decision(one,r)
    assert one.request_id != one.request_digest != one.payload_digest
    with pytest.raises(dataclasses.FrozenInstanceError): one.admitted=False

@pytest.mark.parametrize("skill,code", (("unknown", "UNSUPPORTED_OR_MALFORMED_SKILL_ID"),
    ("cost.change_analysis.v1.extra", "UNSUPPORTED_OR_MALFORMED_SKILL_ID")))
def test_unknown_exact_id_denied(skill,code):
    d=decide_controlled_runtime_integration_admission(request(skill)); assert not d.admitted and d.primary_denial_code==code and d.executable_output is None

def test_manifest_tamper_partial_reorder_and_standalone_fail_closed():
    m=manifest(); changes=(dataclasses.replace(m,approvals=(m.approvals[0],)),
        dataclasses.replace(m,approvals=tuple(reversed(m.approvals))),
        dataclasses.replace(m,manifest_version="5.15.22"),
        dataclasses.replace(m,request_digest_bindings=tuple(reversed(m.request_digest_bindings))))
    for changed in changes:
        d=decide_controlled_runtime_integration_admission(request(source=changed)); assert not d.admitted and d.primary_denial_code=="INVALID_OR_NONCANONICAL_MANIFEST"
    assert not decide_controlled_runtime_integration_admission(m.approvals[0]).admitted

@pytest.mark.parametrize("path,value", (("qualification_version","5.15.21"),("request_digest","0"*64),
    ("feature_gate_name","*"),("payload_digest","0"*64),("provenance_verified",False)))
def test_embedded_chain_tampering(path,value):
    m=manifest(); a=m.approvals[0]; q=dataclasses.replace(a.qualification,**{path:value})
    changed=dataclasses.replace(m,approvals=(dataclasses.replace(a,qualification=q),m.approvals[1]))
    assert not decide_controlled_runtime_integration_admission(request(source=changed)).admitted

def test_cross_skill_request_payload_and_authority_substitution():
    m=manifest(); a,b=m.approvals
    variants=(dataclasses.replace(a,qualification=b.qualification),
        dataclasses.replace(a,request_id=b.request_id),dataclasses.replace(a,payload_digest=b.payload_digest),
        dataclasses.replace(a,authority_boundary=dataclasses.replace(a.authority_boundary,routing=True)))
    for bad in variants:
        changed=dataclasses.replace(m,approvals=(bad,b)); assert not decide_controlled_runtime_integration_admission(request(source=changed)).admitted

def test_denial_precedence_decision_tamper_and_isolation(monkeypatch):
    r=request("unknown",dataclasses.replace(manifest(),manifest_version="5.15.22")); d=decide_controlled_runtime_integration_admission(r)
    assert d.primary_denial_code=="UNSUPPORTED_OR_MALFORMED_SKILL_ID"
    for bad in (dataclasses.replace(d,gateway_version=""),dataclasses.replace(d,admitted=True),
        dataclasses.replace(d,decision_digest="A"*64),dataclasses.replace(d,gate_results=tuple(reversed(d.gate_results)))):
        assert not verify_controlled_runtime_integration_admission_decision(bad,r)
    import brain.business_skill_cost_response_runtime_bridge as bridge
    import brain.business_skill_cost_runtime_integration_manifest as mm
    monkeypatch.setattr(bridge,"bridge_prepared_cost_response",lambda *a,**k: pytest.fail("bridge constructor invoked"))
    monkeypatch.setattr(mm,"create_controlled_integration_manifest",lambda *a,**k: pytest.fail("manifest constructor invoked"))
    assert decide_controlled_runtime_integration_admission(request()).admitted
    source=(Path(__file__).parents[1]/"brain"/"business_skill_cost_runtime_integration_admission_gateway.py").read_text()
    forbidden=("import app","streamlit","session_state","bridge_prepared_cost_response","qualify_controlled_runtime_integration","create_controlled_integration_manifest","router","planner","persistence")
    assert not any(x in source for x in forbidden)
