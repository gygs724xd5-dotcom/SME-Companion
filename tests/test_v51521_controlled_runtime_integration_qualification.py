"""V5.15.21 controlled runtime integration qualification tests."""
import dataclasses
import pytest

from brain.business_skill_cost_runtime_integration_qualification import *
from brain.business_skill_cost_response_runtime_bridge import (
    COST_RUNTIME_BRIDGE_VERSION, FEATURE_GATE_NAME, bridge_prepared_cost_response,
)
from tests.test_v51520_business_skill_cost_response_runtime_bridge import request

def evidence(skill="cost.change_analysis.v1", suffix="71"):
    upstream = request(skill, suffix)
    bridge = bridge_prepared_cost_response(upstream)
    return ControlledRuntimeQualificationInput(skill, upstream.qualification_result, bridge)

@pytest.mark.parametrize("skill,suffix", (("cost.change_analysis.v1", "71"),
    ("cost.per_unit_calculation.v1", "72")))
def test_happy_path_is_immutable_canonical_evidence(skill, suffix):
    result = qualify_controlled_runtime_integration(evidence(skill, suffix))
    assert result.qualified and result.reasons == (QUALIFIED_FOR_CONTROLLED_INTEGRATION,)
    assert HISTORICAL_QUALIFICATION_VERSION == "5.15.21"
    assert result.qualification_version == "5.15.22.1" and result.registry_version == "5.15.13"
    assert result.runtime_bridge_version == COST_RUNTIME_BRIDGE_VERSION == "5.15.22.1"
    assert result.feature_gate_name == FEATURE_GATE_NAME and result.feature_gate_passed
    assert result.provenance_verified and result.authority_boundary_verified
    assert verify_controlled_runtime_integration_qualification(result)
    with pytest.raises(dataclasses.FrozenInstanceError): result.qualified = False

def test_single_and_batch_are_deterministic_and_sorted():
    a, b = evidence(suffix="73"), evidence("cost.per_unit_calculation.v1", "74")
    assert qualify_controlled_runtime_integration(a) == qualify_controlled_runtime_integration(a)
    one = qualify_controlled_runtime_integrations((b, a))
    two = qualify_controlled_runtime_integrations((a, b))
    assert one == two
    assert tuple(x.skill_id for x in one.results) == SUPPORTED_SKILL_IDS
    with pytest.raises(ValueError): qualify_controlled_runtime_integrations((a, a))

def test_exact_id_unknown_and_historical_bridge_rejected():
    good = evidence(suffix="75")
    unknown = qualify_controlled_runtime_integration(dataclasses.replace(good, skill_id="cost.change_analysis.v1.extra"))
    assert not unknown.qualified and "UNSUPPORTED_OR_MALFORMED_SKILL_ID" in unknown.reasons
    old = dataclasses.replace(good.runtime_bridge_result, bridge_version="5.15.20")
    result = qualify_controlled_runtime_integration(dataclasses.replace(good, runtime_bridge_result=old))
    assert not result.qualified and "HISTORICAL_OR_INVALID_BRIDGE_VERSION" in result.reasons

@pytest.mark.parametrize("mutation,reason", (
    (lambda b: dataclasses.replace(b, feature_gate_name="*"), "FEATURE_GATE_IDENTITY_OR_STATE_MISMATCH"),
    (lambda b: dataclasses.replace(b, feature_gate_passed=False), "FEATURE_GATE_IDENTITY_OR_STATE_MISMATCH"),
    (lambda b: dataclasses.replace(b, result_digest="0"*64), "INVALID_RUNTIME_BRIDGE_RESULT"),
    (lambda b: dataclasses.replace(b, runtime_routed=True), "AUTHORITY_ESCALATION"),
))
def test_bridge_gate_digest_and_authority_tampering_fail_closed(mutation, reason):
    item = evidence(suffix="76")
    result = qualify_controlled_runtime_integration(dataclasses.replace(item,
        runtime_bridge_result=mutation(item.runtime_bridge_result)))
    assert not result.qualified and reason in result.reasons

def test_delivery_handoff_cross_skill_and_payload_substitution():
    a = evidence(suffix="77")
    b = evidence("cost.per_unit_calculation.v1", "78")
    swapped_delivery = qualify_controlled_runtime_integration(dataclasses.replace(a,
        delivery_qualification=b.delivery_qualification))
    assert not swapped_delivery.qualified
    assert "DELIVERY_PAYLOAD_BINDING_MISMATCH" in swapped_delivery.reasons
    swapped_bridge = qualify_controlled_runtime_integration(dataclasses.replace(a,
        runtime_bridge_result=b.runtime_bridge_result))
    assert not swapped_bridge.qualified and "PROVENANCE_MISMATCH" in swapped_bridge.reasons
    handoff = dataclasses.replace(a.runtime_bridge_result.handoff, payload_digest="0"*64)
    bridge = dataclasses.replace(a.runtime_bridge_result, handoff=handoff)
    result = qualify_controlled_runtime_integration(dataclasses.replace(a, runtime_bridge_result=bridge))
    assert not result.qualified and "INVALID_OR_MISSING_RUNTIME_HANDOFF" in result.reasons

def test_verifier_rejects_gate_reason_digest_and_malformed_digest_tampering():
    result = qualify_controlled_runtime_integration(evidence(suffix="79"))
    reordered = dataclasses.replace(result, gate_results=tuple(reversed(result.gate_results)))
    assert not verify_controlled_runtime_integration_qualification(reordered)
    assert not verify_controlled_runtime_integration_qualification(dataclasses.replace(result, qualified=False))
    assert not verify_controlled_runtime_integration_qualification(dataclasses.replace(result, reasons=("X",)))
    for digest in ("A"*64, "0"*63, "xyz"):
        assert not verify_controlled_runtime_integration_qualification(dataclasses.replace(result, qualification_digest=digest))

def test_invalid_upstream_is_denied_and_qualification_does_not_invoke_bridge(monkeypatch):
    item = evidence(suffix="80")
    invalid = dataclasses.replace(item.delivery_qualification, binding=None)
    result = qualify_controlled_runtime_integration(dataclasses.replace(item, delivery_qualification=invalid))
    assert not result.qualified and "INVALID_DELIVERY_QUALIFICATION" in result.reasons
    assert not verify_controlled_runtime_integration_qualification(result)
    import brain.business_skill_cost_response_runtime_bridge as upstream
    monkeypatch.setattr(upstream, "bridge_prepared_cost_response", lambda *a, **k: pytest.fail("invoked"))
    assert qualify_controlled_runtime_integration(item).qualified

def test_contract_has_deterministic_gate_order_and_no_authority():
    result = qualify_controlled_runtime_integration(evidence(suffix="81"))
    assert tuple(g.gate for g in result.gate_results) == GATE_ORDER
    assert result.diagnostics == (("semantics", "QUALIFICATION_EVIDENCE_ONLY"),
        ("integration_authority", "NONE"), ("feature_gate_mutated", "FALSE"))
    assert not any(getattr(result.runtime_bridge_result, name) for name in
        ("runtime_routed", "response_delivered", "response_committed", "persisted", "tools_invoked"))
