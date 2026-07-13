"""V5.15.22.1 end-to-end runtime request integrity binding tests."""
import dataclasses
import pytest

from brain.business_skill_cost_response_runtime_bridge import *
from brain.business_skill_cost_runtime_integration_qualification import (
    qualify_controlled_runtime_integration, verify_controlled_runtime_integration_qualification,
)
from brain.business_skill_cost_runtime_integration_manifest import (
    create_controlled_integration_manifest, verify_controlled_integration_approval,
    verify_controlled_integration_manifest,
)
from tests.test_v51520_business_skill_cost_response_runtime_bridge import request
from tests.test_v51521_controlled_runtime_integration_qualification import evidence


def qualification(skill="cost.change_analysis.v1", suffix="221a"):
    return qualify_controlled_runtime_integration(evidence(skill, suffix))


@pytest.mark.parametrize("skill,suffix", (("cost.change_analysis.v1","221a"),
    ("cost.per_unit_calculation.v1","221b")))
def test_end_to_end_request_digest_chain(skill, suffix):
    req=request(skill,suffix); digest=compute_cost_runtime_bridge_request_digest(req)
    bridge=bridge_prepared_cost_response(req)
    q=qualify_controlled_runtime_integration(evidence(skill,suffix))
    manifest=create_controlled_integration_manifest((
        q if skill=="cost.change_analysis.v1" else qualification(suffix="221c"),
        q if skill=="cost.per_unit_calculation.v1" else qualification("cost.per_unit_calculation.v1","221d")))
    approval=next(x for x in manifest.approvals if x.skill_id==skill)
    assert len(digest)==64 and digest==bridge.request_digest==bridge.handoff.request_digest
    assert q.request_digest==approval.request_digest
    assert (skill,q.request_digest) in manifest.request_digest_bindings
    assert verify_cost_runtime_bridge_result_integrity(bridge)
    assert verify_controlled_runtime_integration_qualification(q)
    assert verify_controlled_integration_approval(approval) and verify_controlled_integration_manifest(manifest)


def test_digest_is_deterministic_and_sensitive_to_canonical_request_fields():
    req=request(); base=compute_cost_runtime_bridge_request_digest(req)
    mutations=(dataclasses.replace(req,bridge_request_id="other"),
        dataclasses.replace(req,feature_gates={FEATURE_GATE_NAME:False}),
        dataclasses.replace(req,scope="OTHER"), dataclasses.replace(req,runtime_routed=True))
    assert base==compute_cost_runtime_bridge_request_digest(req)
    assert all(compute_cost_runtime_bridge_request_digest(x) not in ("",base) for x in mutations)
    other=request("cost.per_unit_calculation.v1","other")
    assert compute_cost_runtime_bridge_request_digest(other)!=base


def test_invalid_request_has_no_digest_but_valid_denial_is_bound():
    invalid=bridge_prepared_cost_response(None)
    denied=bridge_prepared_cost_response(request(feature_gates={FEATURE_GATE_NAME:False}))
    assert invalid.request_digest=="" and invalid.canonical_request is None
    assert denied.request_digest and denied.canonical_request is not None and denied.handoff is None
    assert verify_cost_runtime_bridge_result_integrity(invalid)
    assert verify_cost_runtime_bridge_result_integrity(denied)


@pytest.mark.parametrize("digest", ("","A"*64,"g"*64,"0"*63,"0"*65))
def test_malformed_and_cross_layer_digest_tampering_fails(digest):
    bridge=bridge_prepared_cost_response(request())
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(bridge,request_digest=digest))
    assert not verify_cost_runtime_handoff_integrity(dataclasses.replace(bridge.handoff,request_digest=digest))
    q=qualification()
    assert not verify_controlled_runtime_integration_qualification(dataclasses.replace(q,request_digest=digest))


def test_same_id_content_change_and_handoff_result_substitution_fail():
    one=request(suffix="x"); two=dataclasses.replace(one,feature_gates={FEATURE_GATE_NAME:False})
    assert compute_cost_runtime_bridge_request_digest(one)!=compute_cost_runtime_bridge_request_digest(two)
    a=bridge_prepared_cost_response(one); b=bridge_prepared_cost_response(request(suffix="y"))
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(a,handoff=b.handoff))
    forged=dataclasses.replace(a.handoff,request_digest=b.request_digest)
    assert not verify_cost_runtime_handoff_integrity(forged)


def test_historical_versions_are_rejected_and_contracts_are_frozen():
    bridge=bridge_prepared_cost_response(request())
    assert not verify_cost_runtime_bridge_result_integrity(dataclasses.replace(
        bridge,bridge_version=HISTORICAL_FEATURE_GATE_BOUND_BRIDGE_VERSION))
    with pytest.raises(dataclasses.FrozenInstanceError):
        bridge.canonical_request.scope="OTHER"
