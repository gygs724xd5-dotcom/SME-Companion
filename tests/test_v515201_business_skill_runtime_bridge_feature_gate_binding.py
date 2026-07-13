"""V5.15.20.1 immutable runtime-bridge feature-gate identity binding tests."""
import dataclasses
import pytest

from brain.business_skill_cost_response_runtime_bridge import *
from tests.test_v51520_business_skill_cost_response_runtime_bridge import request


@pytest.mark.parametrize("skill,suffix", (("cost.change_analysis.v1","31"),
    ("cost.per_unit_calculation.v1","32")))
def test_exact_gate_identity_is_bound_for_both_skills(skill,suffix):
    req=request(skill,suffix); before=dict(req.feature_gates)
    one=bridge_prepared_cost_response(req); two=bridge_prepared_cost_response(req)
    assert one==two and one.result_digest==two.result_digest
    assert one.bridge_version==COST_RUNTIME_BRIDGE_VERSION=="5.15.20.1"
    assert one.feature_gate_name==one.handoff.feature_gate_name==FEATURE_GATE_NAME
    assert one.feature_gate_passed and one.handoff.feature_gate_passed
    assert req.feature_gates==before


def test_caller_gate_mapping_mutation_cannot_change_existing_artifact():
    gates={FEATURE_GATE_NAME:True}; req=request(feature_gates=gates)
    result=bridge_prepared_cost_response(req); gates.clear(); gates["*"]=True
    assert verify_cost_runtime_bridge_result_integrity(result)
    assert result.feature_gate_name==FEATURE_GATE_NAME


@pytest.mark.parametrize("name", (None,""," ","OTHER","*","GLOBAL",HISTORICAL_COST_RUNTIME_BRIDGE_VERSION))
def test_handoff_gate_name_tampering_fails_closed(name):
    result=bridge_prepared_cost_response(request()); handoff=result.handoff
    forged=dataclasses.replace(handoff,feature_gate_name=name)
    assert not verify_cost_runtime_handoff_integrity(forged)
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(result,handoff=forged))


def test_name_state_version_handoff_and_result_substitution_rejected():
    one=bridge_prepared_cost_response(request(suffix="41"))
    two=bridge_prepared_cost_response(request(suffix="42"))
    for forged in (dataclasses.replace(one.handoff,feature_gate_passed=False),
        dataclasses.replace(one.handoff,bridge_version=HISTORICAL_COST_RUNTIME_BRIDGE_VERSION),
        two.handoff):
        assert not verify_cost_runtime_handoff_integrity(forged) or forged is two.handoff
        assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(one,handoff=forged))
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(one,feature_gate_name=None))
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(one,feature_gate_passed=False))
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(one,bridge_version=HISTORICAL_COST_RUNTIME_BRIDGE_VERSION))
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(one,handoff=two.handoff))


@pytest.mark.parametrize("digest", ("","0","0"*63,"G"*64,"A"*64))
def test_malformed_and_noncanonical_digests_rejected(digest):
    result=bridge_prepared_cost_response(request())
    assert not verify_cost_runtime_handoff_integrity(dataclasses.replace(result.handoff,handoff_digest=digest))
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(result,result_digest=digest))


def test_denials_bind_no_gate_identity_or_usable_authority_and_batches_isolate():
    denied=bridge_prepared_cost_response(request(feature_gates={FEATURE_GATE_NAME:False}))
    assert denied.feature_gate_name is None and not denied.feature_gate_passed and denied.handoff is None
    assert verify_cost_runtime_bridge_result_integrity(denied)
    a=request(suffix="51"); b=request(suffix="52")
    batch=bridge_prepared_cost_responses((a,b))
    assert [x.bridge_request_id for x in batch.results]==["bridge51","bridge52"]
    duplicate=bridge_prepared_cost_responses((a,dataclasses.replace(b,bridge_request_id="bridge51")))
    assert all(x.feature_gate_name is None and x.handoff is None for x in duplicate.results)
    assert all(verify_cost_runtime_bridge_result_integrity(x) for x in duplicate.results)
