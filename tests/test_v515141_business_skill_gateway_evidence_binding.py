import copy
import dataclasses

import pytest

from brain.business_skill_limited_activation_gateway import *
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION

NOW = "2026-07-11T12:00:00+07:00"
CHANGE = "my cost increased from 20 to 24"
UNIT = "please calculate cost per unit total 1000 for 100 units"


def rich(value, confidence=1.0):
    return {"value": value, "confidence": confidence, "source": "current_turn", "freshness": "current", "user_confirmed": True}


def request(skill="cost.change_analysis.v1", evidence=None, rid="r1", message=None, scope=SUPPORTED_ACTIVATION_SCOPE, ref=NOW):
    if evidence is None:
        evidence = {"previous_cost": rich(20), "current_cost": rich(24)}
    return LimitedActivationRequest(rid, message or (CHANGE if skill.startswith("cost.change") else UNIT), evidence, ref, skill, scope, LIMITED_ACTIVATION_GATEWAY_VERSION)


@pytest.mark.parametrize("skill,evidence,ids,rules", [
    ("cost.change_analysis.v1", {"current_cost": rich(24), "previous_cost": rich(20)},
     ("previous_cost", "current_cost"), ("number", "number")),
    ("cost.per_unit_calculation.v1", {"waste_or_loss_quantity": rich(2), "unit_quantity": rich(100), "total_cost": rich(1000)},
     ("total_cost", "unit_quantity", "waste_or_loss_quantity"), ("positive_number", "positive_number", "non_negative_number")),
])
def test_complete_canonical_binding_and_determinism(skill, evidence, ids, rules):
    first = decide_limited_activation(request(skill, evidence))
    second = decide_limited_activation(request(skill, dict(reversed(tuple(evidence.items())))))
    assert first.decision == LIMITED_EXECUTION_ELIGIBLE
    binding = first.binding
    assert binding is not None and verify_activation_request_binding(binding)
    assert (binding.request_id, binding.requested_skill_id, binding.matched_skill_id) == ("r1", skill, skill)
    assert (binding.activation_scope, binding.reference_time, binding.registry_version) == (SUPPORTED_ACTIVATION_SCOPE, NOW, "5.15.13")
    assert (binding.matcher_version, binding.evidence_mapper_version, binding.gateway_policy_version) == ("5.15.3", "5.15.4", "5.15.14.1")
    assert tuple(x.evidence_id for x in binding.evidence_snapshot) == ids
    assert tuple(x.validation_rule for x in binding.evidence_snapshot) == rules
    assert binding == second.binding and binding.binding_digest == second.binding.binding_digest


def test_source_mutation_unknown_evidence_and_denied_binding():
    source = {"previous_cost": rich(20), "current_cost": rich(24)}
    decision = decide_limited_activation(request(evidence=source))
    source["previous_cost"]["value"] = 999
    assert decision.binding.evidence_snapshot[0].normalized_value == 20
    denied = decide_limited_activation(request(evidence={**source, "intruder": rich(1)}))
    assert denied.binding is None and "EVIDENCE_UNKNOWN:intruder" in denied.reason_codes


@pytest.mark.parametrize("field,value", [
    ("request_id", "other"), ("requested_skill_id", "other"), ("matched_skill_id", "other"),
    ("current_message", "other"), ("activation_scope", "other"), ("reference_time", "other"),
    ("gateway_policy_version", "5.15.14"), ("candidate_confidence", .9), ("binding_digest", "0" * 64),
])
def test_tampering_fails(field, value):
    binding = decide_limited_activation(request()).binding
    assert not verify_activation_request_binding(dataclasses.replace(binding, **{field: value}))


def test_evidence_tampering_order_duplicate_malformed_and_old_contract():
    binding = decide_limited_activation(request()).binding
    changed = dataclasses.replace(binding.evidence_snapshot[0], confidence=.9)
    assert not verify_activation_request_binding(dataclasses.replace(binding, evidence_snapshot=(changed,) + binding.evidence_snapshot[1:]))
    assert not verify_activation_request_binding(dataclasses.replace(binding, evidence_snapshot=tuple(reversed(binding.evidence_snapshot))))
    assert not verify_activation_request_binding(dataclasses.replace(binding, evidence_snapshot=binding.evidence_snapshot + (binding.evidence_snapshot[0],)))
    assert not verify_activation_request_binding(None)
    assert not verify_activation_request_binding(dataclasses.replace(binding, binding_digest="bad"))
    assert HISTORICAL_LIMITED_ACTIVATION_GATEWAY_VERSION == "5.15.14"
    old_decision = dataclasses.replace(decide_limited_activation(request()), binding=None, policy_version="5.15.14")
    assert old_decision.binding is None


def test_authority_remains_entirely_false_and_registry_unchanged():
    decision = decide_limited_activation(request())
    for name in ("executed", "calculated", "reasoning_executed", "runtime_routed", "tools_invoked", "persisted", "follow_up_generated", "response_generated", "response_committed"):
        assert getattr(decision, name) is False
    assert BUSINESS_SKILL_REGISTRY_VERSION == "5.15.13"
