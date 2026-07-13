"""V5.15.22 controlled runtime integration governance manifest tests."""
import dataclasses
from pathlib import Path
import pytest

from brain.business_skill_cost_runtime_integration_manifest import *
from brain.business_skill_cost_runtime_integration_qualification import qualify_controlled_runtime_integration
from tests.test_v51521_controlled_runtime_integration_qualification import evidence

def qualifications():
    return (qualify_controlled_runtime_integration(evidence(suffix="522a")),
            qualify_controlled_runtime_integration(evidence("cost.per_unit_calculation.v1", "522b")))

def test_happy_path_lookup_order_determinism_and_immutability():
    qs = qualifications(); manifest = create_controlled_integration_manifest(qs)
    assert manifest == create_controlled_integration_manifest(qs)
    assert manifest.approved_skill_ids == SUPPORTED_SKILL_IDS
    assert all(verify_controlled_integration_approval(x) for x in manifest.approvals)
    assert verify_controlled_integration_manifest(manifest)
    assert get_controlled_integration_skill(SUPPORTED_SKILL_IDS[0]).active_status == LIMITED_ACTIVE
    assert get_controlled_integration_skill("cost.change_analysis.v1.extra") is None
    with pytest.raises(dataclasses.FrozenInstanceError): manifest.approval_status = "X"

@pytest.mark.parametrize("source", ((), (qualifications()[0],), tuple(reversed(qualifications())),
    (qualifications()[0], qualifications()[0])))
def test_partial_reordered_and_duplicate_batches_fail(source):
    with pytest.raises(ValueError): create_controlled_integration_manifest(source)

def test_unknown_historical_unqualified_and_cross_skill_fail():
    a, b = qualifications()
    mutations = (dataclasses.replace(a, skill_id="unknown.v1"),
        dataclasses.replace(a, qualification_version="5.15.20"),
        dataclasses.replace(a, runtime_bridge_version="5.15.20"),
        dataclasses.replace(a, qualified=False),
        dataclasses.replace(a, delivery_qualification=b.delivery_qualification),
        dataclasses.replace(a, runtime_bridge_result=b.runtime_bridge_result))
    for item in mutations:
        with pytest.raises(ValueError): create_controlled_integration_approval(item)

@pytest.mark.parametrize("field,value", (("manifest_version", ""), ("manifest_version", "5.15.21"),
    ("integration_scope", "PRODUCTION_ACTIVE"), ("approval_status", "ACTIVE"),
    ("approval_reason", "X"), ("feature_gate_name", "*"), ("feature_gate_passed", False),
    ("qualification_digest", "0"*64), ("handoff_digest", "0"*64),
    ("result_digest", "0"*64), ("payload_digest", "0"*64),
    ("diagnostics", tuple(reversed(DIAGNOSTICS))), ("approval_digest", "A"*64),
    ("approval_digest", "0"*63)))
def test_approval_semantic_and_digest_tampering(field, value):
    approval = create_controlled_integration_approval(qualifications()[0])
    assert not verify_controlled_integration_approval(dataclasses.replace(approval, **{field: value}))

def test_authority_escalation_and_manifest_tampering_fail():
    manifest = create_controlled_integration_manifest(qualifications()); a = manifest.approvals[0]
    escalated = dataclasses.replace(a, authority_boundary=dataclasses.replace(a.authority_boundary, routing=True))
    assert not verify_controlled_integration_approval(escalated)
    for changed in (dataclasses.replace(manifest, approvals=(manifest.approvals[1], manifest.approvals[0])),
        dataclasses.replace(manifest, approved_skill_ids=(SUPPORTED_SKILL_IDS[0],)),
        dataclasses.replace(manifest, diagnostics=tuple(reversed(DIAGNOSTICS))),
        dataclasses.replace(manifest, manifest_digest="0"*64)):
        assert not verify_controlled_integration_manifest(changed)

def test_no_upstream_pipeline_or_runtime_integration(monkeypatch):
    import brain.business_skill_cost_runtime_integration_qualification as qmod
    import brain.business_skill_cost_response_runtime_bridge as bridge
    monkeypatch.setattr(qmod, "qualify_controlled_runtime_integration", lambda *a, **k: pytest.fail("qualification invoked"))
    monkeypatch.setattr(bridge, "bridge_prepared_cost_response", lambda *a, **k: pytest.fail("bridge invoked"))
    assert verify_controlled_integration_manifest(create_controlled_integration_manifest(qualifications()))
    source = (Path(__file__).parents[1]/"brain"/"business_skill_cost_runtime_integration_manifest.py").read_text()
    forbidden = ("import app", "streamlit", "session_state", "bridge_prepared_cost_response",
        "qualify_controlled_runtime_integration(", "task_router")
    assert not any(token in source for token in forbidden)
