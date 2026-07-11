import ast
import copy
import dataclasses
from pathlib import Path

import pytest

from brain.business_skill import CONTRACTED, LIMITED_ACTIVE, SHADOW_AVAILABLE, STABLE, UNIT_TESTED
from brain.business_skill_limited_activation_gateway import *
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_shadow_observation import ShadowObservationRequest, observe_business_skill_shadow, SHADOW_SELECTED

NOW = "2026-07-11T12:00:00+07:00"
CHANGE = "เดือนก่อนต้นทุน 20,000 บาท เดือนนี้ 24,000 บาท ต้นทุนเปลี่ยนไปเท่าไร"
UNIT = "ต้นทุนรวม 1,000 บาท ผลิตได้ 100 ชิ้น ต้นทุนต่อชิ้นเท่าไร"
def rich(value, **kw):
    x = {"value": value, "confidence": 1.0, "source": "current_turn", "freshness": "current", "user_confirmed": True}; x.update(kw); return x
CHANGE_E = {"previous_cost": rich(20000), "current_cost": rich(24000)}
UNIT_E = {"total_cost": rich(1000), "unit_quantity": rich(100)}
def req(rid="r1", message=CHANGE, evidence=CHANGE_E, skill="cost.change_analysis.v1", scope=SUPPORTED_ACTIVATION_SCOPE, version="5.15.14.1", **kw):
    return LimitedActivationRequest(rid, message, evidence, kw.get("reference_time", NOW), skill, scope, version, kw.get("authority_inputs", ()))

@pytest.mark.parametrize("activation_request", [req(), req("r2", UNIT, UNIT_E, "cost.per_unit_calculation.v1")])
def test_exact_positive_canonical_decisions_and_no_authority(activation_request):
    result = decide_limited_activation(activation_request)
    assert result.decision == LIMITED_EXECUTION_ELIGIBLE
    assert (result.candidate_score, result.candidate_confidence, result.evidence_confidence) == (70, .5833, 1.0)
    assert result.reason_codes == ("ALL_ELIGIBILITY_GATES_PASSED",)
    assert tuple(x.gate for x in result.gate_results) == GATE_ORDER and all(x.passed for x in result.gate_results)
    for name in ("executed", "calculated", "reasoning_executed", "runtime_routed", "tools_invoked", "persisted", "follow_up_generated", "response_generated", "response_committed"):
        assert getattr(result, name) is False

def test_frozen_contracts_policy_and_registry_are_unchanged():
    for cls in (LimitedActivationPolicy, LimitedActivationRequest, LimitedActivationGateResult, LimitedActivationDecision, LimitedActivationDecisionBatch, LimitedActivationDenial, ActivationEvidenceItem, ActivationRequestBinding):
        assert cls.__dataclass_params__.frozen
    assert BUSINESS_SKILL_REGISTRY_VERSION == "5.15.13"
    registry = get_business_skill_registry()
    assert tuple(sum(x.active_status == s for x in registry) for s in (LIMITED_ACTIVE, CONTRACTED, SHADOW_AVAILABLE, UNIT_TESTED, STABLE)) == (2, 8, 0, 0, 0)

@pytest.mark.parametrize("bad,code", [
    (req(message=" "), "EMPTY_CURRENT_MESSAGE"), (req(message="ทำต่อได้เลย"), "NO_CANDIDATE"),
    (req(skill="unknown.v1"), "UNKNOWN_OR_UNSUPPORTED_REQUESTED_SKILL"),
    (req(skill="cost.per_unit_calculation.v1"), "CANDIDATE_SKILL_MISMATCH"),
    (req(scope=None), "ACTIVATION_SCOPE_NOT_ALLOWED"), (req(scope="*"), "ACTIVATION_SCOPE_NOT_ALLOWED"),
    (req(scope="GLOBAL"), "ACTIVATION_SCOPE_NOT_ALLOWED"), (req(reference_time=None), "REFERENCE_TIME_REQUIRED"),
    (req(version="5.15.13"), "UNSUPPORTED_POLICY_VERSION"),
    (req(authority_inputs={"response": "yes"}), "AUTHORITY_BEARING_INPUT_REJECTED"),
])
def test_request_identity_scope_current_only_and_authority_denials(bad, code):
    result = decide_limited_activation(bad)
    assert result.decision == LIMITED_EXECUTION_DENIED and code in result.reason_codes

@pytest.mark.parametrize("message,evidence,code", [
    ("Cost Change Analysis", CHANGE_E, "CANDIDATE_CONFIDENCE_BELOW_THRESHOLD"),
    (CHANGE, {"previous_cost": rich(1)}, "EVIDENCE_MISSING:current_cost"),
    (CHANGE, {"previous_cost": rich("bad"), "current_cost": rich(2)}, "EVIDENCE_INVALID:previous_cost"),
    (UNIT, {"total_cost": rich(-1), "unit_quantity": rich(2)}, "EVIDENCE_INVALID:total_cost"),
    (CHANGE, {"previous_cost": rich(1, confidence=.2), "current_cost": rich(2)}, "EVIDENCE_LOW_CONFIDENCE:previous_cost"),
    (CHANGE, {"previous_cost": rich(1, freshness="stale"), "current_cost": rich(2)}, "EVIDENCE_STALE:previous_cost"),
    (CHANGE, {"previous_cost": rich(1, assumed=True), "current_cost": rich(2)}, "EVIDENCE_INVALID:previous_cost"),
    (CHANGE, {"previous_cost": rich(1, validation_errors=["conflict"]), "current_cost": rich(2)}, "EVIDENCE_INVALID:previous_cost"),
    (CHANGE + " " + UNIT, {**CHANGE_E, **UNIT_E}, "COMPETING_CANDIDATES"),
])
def test_confidence_evidence_and_ambiguity_denials(message, evidence, code):
    skill = "cost.per_unit_calculation.v1" if message == UNIT else "cost.change_analysis.v1"
    result = decide_limited_activation(req(message=message, evidence=evidence, skill=skill))
    assert result.decision == LIMITED_EXECUTION_DENIED and code in result.reason_codes

def test_policy_rejects_malformed_impossible_and_relaxed_thresholds():
    for kwargs in ({"policy_version":"x"}, {"minimum_candidate_score":69}, {"minimum_candidate_confidence":.1}, {"minimum_evidence_confidence":.1}, {"minimum_candidate_confidence":1.1}):
        with pytest.raises(ValueError): LimitedActivationPolicy(**kwargs)

def test_duplicates_ordering_determinism_mutation_and_cross_request_isolation():
    source = copy.deepcopy(CHANGE_E); request = req(evidence=source); first = decide_limited_activation(request)
    source["previous_cost"]["value"] = "bad"
    assert decide_limited_activation(request) == first
    batch = decide_limited_activations((request, req("r2", UNIT, UNIT_E, "cost.per_unit_calculation.v1"), req("r3", evidence={})))
    assert tuple(x.request_id for x in batch.decisions) == ("r1", "r2", "r3")
    assert tuple(x.decision for x in batch.decisions) == (LIMITED_EXECUTION_ELIGIBLE, LIMITED_EXECUTION_ELIGIBLE, LIMITED_EXECUTION_DENIED)
    duplicate = decide_limited_activations((req("same"), req("same", UNIT, UNIT_E, "cost.per_unit_calculation.v1")))
    assert all("DUPLICATE_REQUEST_ID" in x.reason_codes for x in duplicate.decisions)

def test_shadow_is_diagnostic_and_separate_and_import_boundary_is_clean():
    shadow = observe_business_skill_shadow(ShadowObservationRequest.from_mapping(CHANGE, CHANGE_E, reference_time=NOW))
    gateway = decide_limited_activation(req())
    assert shadow.outcome == SHADOW_SELECTED and gateway.decision == LIMITED_EXECUTION_ELIGIBLE
    assert shadow.selected_shadow_skill_id == gateway.eligible_skill_id
    source = Path(__file__).parents[1].joinpath("brain/business_skill_limited_activation_gateway.py").read_text("utf-8")
    imports = {n.module for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom)}
    assert "brain.business_skill_matcher" not in imports and "app" not in imports
    assert not any(any(word in (module or "") for word in ("runtime", "router", "planner", "workflow", "response")) for module in imports)
    assert not ({"answer", "business_reasoning", "follow_up_question", "execution_callback", "response_content"} & {f.name for f in dataclasses.fields(LimitedActivationDecision)})

def test_wrong_canonical_lifecycle_denied(monkeypatch):
    import brain.business_skill_limited_activation_gateway as gateway
    canonical = get_business_skill_registry()
    for status in (CONTRACTED, UNIT_TESTED, SHADOW_AVAILABLE, STABLE):
        changed = tuple(dataclasses.replace(x, active_status=status) if x.skill_id == "cost.change_analysis.v1" else x for x in canonical)
        monkeypatch.setattr(gateway, "get_business_skill_registry", lambda changed=changed: changed)
        assert "LIFECYCLE_NOT_LIMITED_ACTIVE" in gateway.decide_limited_activation(req()).reason_codes
