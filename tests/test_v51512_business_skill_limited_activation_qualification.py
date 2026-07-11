import dataclasses
from dataclasses import FrozenInstanceError, replace

import pytest

from brain.business_skill import CONTRACTED, LIMITED_ACTIVE, STABLE, UNIT_TESTED
from brain.business_skill_limited_activation_qualification import *
from brain.business_skill_registry import get_business_skill_registry
from brain.business_skill_shadow_evaluation import (
    EXPECTED_AMBIGUITY_BLOCK, EXPECTED_EVIDENCE_BLOCK, EXPECTED_LOW_CONFIDENCE_BLOCK,
    TRUE_NEGATIVE, TRUE_POSITIVE, ExpectedShadowOutcome, ShadowEvaluationCase,
)
from brain.business_skill_shadow_observation import ShadowObservationRequest

NOW = "2026-07-11T12:00:00+07:00"
CHANGE = "เดือนก่อนต้นทุน 20,000 บาท เดือนนี้ 24,000 บาท ต้นทุนเปลี่ยนไปเท่าไร"
UNIT = "ต้นทุนรวม 1,000 บาท ผลิตได้ 100 ชิ้น ต้นทุนต่อชิ้น"


def rich(value, **changes):
    result = {"value": value, "confidence": 1.0, "source": "current_turn",
              "freshness": "current", "user_confirmed": True}
    result.update(changes)
    return result


def ev(case_id, message, evidence, label, skill_id=None):
    req = ShadowObservationRequest.from_mapping(message, evidence, reference_time=NOW if evidence else None)
    return ShadowEvaluationCase(case_id, req, ExpectedShadowOutcome(label, skill_id))


def qualification_input(skill, prefix):
    sid = skill.skill_id
    positive_message = CHANGE if "change" in sid else UNIT
    english = "my cost increased this month" if "change" in sid else "cost per unit"
    evidence = ({"previous_cost": rich(20000), "current_cost": rich(24000)} if "change" in sid
                else {"total_cost": rich(1000), "unit_quantity": rich(100)})
    required_field = "previous_cost" if "change" in sid else "total_cost"
    other_field = "current_cost" if "change" in sid else "unit_quantity"
    def blocked(tag, mutation, label=EXPECTED_EVIDENCE_BLOCK):
        data = {required_field: rich(1), other_field: rich(2)}
        mutation(data)
        return ev(prefix + tag, positive_message, data, label)
    labeled = (
        LimitedActivationLabeledCase("THAI_POSITIVE", ev(prefix+"th", positive_message, evidence, TRUE_POSITIVE, sid)),
        LimitedActivationLabeledCase("ENGLISH_POSITIVE", ev(prefix+"en", english, evidence, TRUE_POSITIVE, sid)),
        LimitedActivationLabeledCase("CORRECT_ABSTENTION", ev(prefix+"none", "วันนี้อากาศดี", {}, TRUE_NEGATIVE)),
        LimitedActivationLabeledCase("MISSING_INCOMPLETE_EVIDENCE", ev(prefix+"missing", positive_message, {required_field: rich(1)}, EXPECTED_EVIDENCE_BLOCK)),
        LimitedActivationLabeledCase("INVALID_EVIDENCE", blocked("invalid", lambda d: d[required_field].update(value="x"))),
        LimitedActivationLabeledCase("STALE_EVIDENCE", blocked("stale", lambda d: d[required_field].update(freshness="stale"))),
        LimitedActivationLabeledCase("ASSUMED_EVIDENCE", blocked("assumed", lambda d: d[required_field].update(assumed=True))),
        LimitedActivationLabeledCase("LOW_CONFIDENCE", blocked("low", lambda d: d[required_field].update(confidence=.2), EXPECTED_LOW_CONFIDENCE_BLOCK)),
        LimitedActivationLabeledCase("COMPETING_CANDIDATE_OR_AMBIGUITY", ev(prefix+"amb", CHANGE+" "+UNIT, {"previous_cost":rich(1),"current_cost":rich(2),"total_cost":rich(3),"unit_quantity":rich(4)}, EXPECTED_AMBIGUITY_BLOCK)),
        LimitedActivationLabeledCase("HISTORICAL_CONTEXT_ONLY_PROTECTION", ev(prefix+"history", "เมื่อวานเคยคุยเรื่องนี้", {}, TRUE_NEGATIVE)),
    )
    return LimitedActivationQualificationInput(skill, REQUIRED_HISTORY, labeled)


def test_positive_exact_results_determinism_and_boundaries():
    skills = [x for x in get_business_skill_registry() if x.skill_id in QUALIFICATION_SKILL_IDS]
    inputs = tuple(qualification_input(x, f"s{i}-") for i, x in enumerate(skills))
    before = get_business_skill_registry()
    first = qualify_limited_activation(reversed(inputs), qualification_id="qa-51512", reference_time=NOW)
    second = qualify_limited_activation(inputs, qualification_id="qa-51512", reference_time=NOW)
    assert first == second
    assert tuple(x.skill_id for x in first.results) == QUALIFICATION_SKILL_IDS
    for result in first.results:
        assert (result.observation_count, result.evaluation_count, result.passed_evaluation_count) == (10, 10, 10)
        assert all(g.passed and g.reason_codes == ("PASSED",) for g in result.gate_results)
        assert result.reason_codes == ("ALL_QUALIFICATION_GATES_PASSED",)
        assert result.recommendation.recommendation == QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION
        assert all(count == 1 for _, count in result.coverage_counts)
    assert get_business_skill_registry() == before
    assert all(x.active_status == "SHADOW_AVAILABLE" for x in skills)


def test_negative_identity_lifecycle_history_volume_coverage_and_quality():
    skill = next(x for x in get_business_skill_registry() if x.skill_id == QUALIFICATION_SKILL_IDS[0])
    good = qualification_input(skill, "n-")
    for status in (CONTRACTED, UNIT_TESTED, LIMITED_ACTIVE, STABLE):
        result = qualify_limited_activation((replace(good, skill=replace(skill, active_status=status)),), qualification_id="q", reference_time=NOW).results[0]
        assert "LIFECYCLE_NOT_SHADOW_AVAILABLE" in result.reason_codes
    bad_history = replace(good, lifecycle_history=(REQUIRED_HISTORY[1], REQUIRED_HISTORY[0]))
    assert "MALFORMED_OR_OUT_OF_ORDER_LIFECYCLE_HISTORY" in qualify_limited_activation((bad_history,), qualification_id="q", reference_time=NOW).results[0].reason_codes
    short = replace(good, labeled_cases=good.labeled_cases[:-1])
    reasons = qualify_limited_activation((short,), qualification_id="q", reference_time=NOW).results[0].reason_codes
    assert "INSUFFICIENT_OBSERVATIONS" in reasons
    assert "MISSING_REQUIRED_COVERAGE:HISTORICAL_CONTEXT_ONLY_PROTECTION" in reasons
    wrong = replace(good.labeled_cases[0].evaluation_case, expected=ExpectedShadowOutcome(TRUE_NEGATIVE))
    bad = replace(good, labeled_cases=(replace(good.labeled_cases[0], evaluation_case=wrong),)+good.labeled_cases[1:])
    reasons = qualify_limited_activation((bad,), qualification_id="q", reference_time=NOW).results[0].reason_codes
    assert "FALSE_POSITIVE_PRESENT" in reasons and "UNEXPECTED_DRIFT_PRESENT" in reasons


def test_validation_frozen_mutation_safety_and_authority_surface():
    for contract in (LimitedActivationQualificationPolicy, LimitedActivationLabeledCase,
                     LimitedActivationQualificationInput, LimitedActivationGateResult,
                     LimitedActivationQualificationResult, LimitedActivationQualificationBatch,
                     LimitedActivationRecommendation):
        assert contract.__dataclass_params__.frozen
    with pytest.raises(ValueError): LimitedActivationQualificationPolicy(minimum_observations_per_skill=0)
    with pytest.raises(ValueError): LimitedActivationQualificationPolicy(minimum_pass_rate=1.01)
    with pytest.raises(ValueError): LimitedActivationQualificationPolicy(maximum_false_positives=1)
    with pytest.raises(ValueError): qualify_limited_activation((), qualification_id="q", reference_time="")
    forbidden = {"answer", "calculation", "business_reasoning", "user_response", "follow_up",
                 "authorization", "execution_instruction", "tool_invocation", "routing_instruction"}
    for contract in (LimitedActivationGateResult, LimitedActivationQualificationResult,
                     LimitedActivationQualificationBatch, LimitedActivationRecommendation):
        assert forbidden.isdisjoint(x.name for x in dataclasses.fields(contract))
    skill = next(x for x in get_business_skill_registry() if x.skill_id == QUALIFICATION_SKILL_IDS[0])
    source = qualification_input(skill, "m-")
    result = qualify_limited_activation((source,), qualification_id="q", reference_time=NOW)
    mutable = {"x": [1]}; request = ShadowObservationRequest.from_mapping("x", mutable)
    mutable["x"].append(2)
    assert result == qualify_limited_activation((source,), qualification_id="q", reference_time=NOW)
    assert request.available_evidence[0].value == (1,)


def test_identity_unknown_unsupported_duplicate_and_conflicting_inputs():
    registry = get_business_skill_registry()
    cost = next(x for x in registry if x.skill_id == QUALIFICATION_SKILL_IDS[0])
    unsupported = next(x for x in registry if x.skill_id.startswith("pricing."))
    unknown = replace(cost, skill_id="cost.unknown.v1")
    for candidate in (unknown, unsupported):
        candidate_input = replace(qualification_input(cost, candidate.skill_id + "-"), skill=candidate)
        result = qualify_limited_activation(
            (candidate_input,),
            qualification_id="identity", reference_time=NOW,
        ).results[0]
        assert "UNKNOWN_OR_UNSUPPORTED_SKILL" in result.reason_codes
        assert result.recommendation.recommendation == NOT_QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION

    first = qualification_input(cost, "duplicate-a-")
    duplicate = replace(
        first,
        skill=replace(cost, active_status=CONTRACTED),
        labeled_cases=qualification_input(cost, "duplicate-b-").labeled_cases,
    )
    results = qualify_limited_activation(
        (first, duplicate), qualification_id="duplicate-input", reference_time=NOW,
    ).results
    assert len(results) == 2
    assert all("DUPLICATE_OR_CONFLICTING_SKILL_INPUT" in x.reason_codes for x in results)
    lifecycle_gates = [next(g for g in result.gate_results if g.gate == "LIFECYCLE") for result in results]
    assert [gate.passed for gate in lifecycle_gates] == [True, False]


def test_duplicate_case_ids_and_cross_skill_contamination_are_executed():
    skills = [x for x in get_business_skill_registry() if x.skill_id in QUALIFICATION_SKILL_IDS]
    good = qualification_input(skills[0], "case-")
    duplicate_case = replace(
        good.labeled_cases[1].evaluation_case,
        case_id=good.labeled_cases[0].evaluation_case.case_id,
    )
    duplicate_input = replace(
        good,
        labeled_cases=(good.labeled_cases[0], replace(good.labeled_cases[1], evaluation_case=duplicate_case))
                      + good.labeled_cases[2:],
    )
    duplicate_result = qualify_limited_activation(
        (duplicate_input,), qualification_id="duplicate-case", reference_time=NOW,
    ).results[0]
    assert "DUPLICATE_OBSERVATION_OR_CASE_ID" in duplicate_result.reason_codes
    assert "MALFORMED_EVALUATION_DATASET" in duplicate_result.reason_codes

    contaminated_case = replace(
        good.labeled_cases[0].evaluation_case,
        expected=ExpectedShadowOutcome(TRUE_POSITIVE, skills[1].skill_id),
    )
    contaminated = replace(
        good,
        labeled_cases=(replace(good.labeled_cases[0], evaluation_case=contaminated_case),)
                      + good.labeled_cases[1:],
    )
    reasons = qualify_limited_activation(
        (contaminated,), qualification_id="cross-skill", reference_time=NOW,
    ).results[0].reason_codes
    assert "CROSS_SKILL_CONTAMINATION" in reasons
    assert "MISCLASSIFICATION_PRESENT" in reasons


def test_lifecycle_history_missing_malformed_duplicate_and_out_of_order():
    skill = next(x for x in get_business_skill_registry() if x.skill_id == QUALIFICATION_SKILL_IDS[0])
    good = qualification_input(skill, "history-")
    histories = {
        "missing": REQUIRED_HISTORY[:-1],
        "malformed": REQUIRED_HISTORY[:-1] + ("not-a-canonical-audit-reference",),
        "duplicate": REQUIRED_HISTORY[:-1] + (REQUIRED_HISTORY[-2],),
        "out-of-order": (REQUIRED_HISTORY[1], REQUIRED_HISTORY[0], *REQUIRED_HISTORY[2:]),
    }
    for name, history in histories.items():
        reasons = qualify_limited_activation(
            (replace(good, lifecycle_history=history),),
            qualification_id="history-" + name, reference_time=NOW,
        ).results[0].reason_codes
        assert "MALFORMED_OR_OUT_OF_ORDER_LIFECYCLE_HISTORY" in reasons
        if name == "duplicate":
            assert "DUPLICATE_LIFECYCLE_HISTORY_REFERENCE" in reasons


def test_false_positive_false_negative_misclassification_and_unexpected_drift():
    skills = [x for x in get_business_skill_registry() if x.skill_id in QUALIFICATION_SKILL_IDS]
    base = qualification_input(skills[0], "quality-")
    scenarios = {
        "false-positive": ExpectedShadowOutcome(TRUE_NEGATIVE),
        "false-negative": ExpectedShadowOutcome(TRUE_POSITIVE, skills[0].skill_id),
        "misclassification": ExpectedShadowOutcome(TRUE_POSITIVE, skills[1].skill_id),
    }
    for name, expected in scenarios.items():
        source_index = 0 if name != "false-negative" else 2
        changed_case = replace(base.labeled_cases[source_index].evaluation_case, expected=expected)
        changed = replace(
            base,
            labeled_cases=base.labeled_cases[:source_index]
                          + (replace(base.labeled_cases[source_index], evaluation_case=changed_case),)
                          + base.labeled_cases[source_index + 1:],
        )
        reasons = qualify_limited_activation(
            (changed,), qualification_id=name, reference_time=NOW,
        ).results[0].reason_codes
        expected_code = name.replace("-", "_").upper() + "_PRESENT"
        assert expected_code in reasons
        assert "UNEXPECTED_DRIFT_PRESENT" in reasons


def test_observation_threshold_below_equal_and_above_boundary():
    skill = next(x for x in get_business_skill_registry() if x.skill_id == QUALIFICATION_SKILL_IDS[0])
    good = qualification_input(skill, "threshold-")
    extra_case = replace(good.labeled_cases[-1].evaluation_case, case_id="threshold-extra")
    extra = replace(good.labeled_cases[-1], evaluation_case=extra_case)
    scenarios = ((9, good.labeled_cases[:-1], False),
                 (10, good.labeled_cases, True),
                 (11, good.labeled_cases + (extra,), True))
    for count, cases, volume_passed in scenarios:
        result = qualify_limited_activation(
            (replace(good, labeled_cases=cases),), qualification_id=f"threshold-{count}",
            reference_time=NOW,
        ).results[0]
        volume_gate = next(x for x in result.gate_results if x.gate == "OBSERVATION_VOLUME")
        assert result.observation_count == count
        assert volume_gate.passed is volume_passed
        assert ("INSUFFICIENT_OBSERVATIONS" in result.reason_codes) is (not volume_passed)


def test_policy_and_required_identifier_validation_paths():
    with pytest.raises(ValueError, match="minimum_observations"):
        LimitedActivationQualificationPolicy(minimum_observations_per_skill=-1)
    with pytest.raises(ValueError, match="between zero and one"):
        LimitedActivationQualificationPolicy(minimum_pass_rate=-0.01)
    with pytest.raises(ValueError, match="zero error and drift"):
        LimitedActivationQualificationPolicy(maximum_unexpected_drift_findings=1)
    with pytest.raises(ValueError, match="coverage categories"):
        LimitedActivationQualificationPolicy(required_coverage_categories=("NOT_REAL",))
    with pytest.raises(ValueError, match="qualification_id"):
        qualify_limited_activation((), qualification_id="", reference_time=NOW)
    with pytest.raises(ValueError, match="qualification_id"):
        qualify_limited_activation((), qualification_id=None, reference_time=NOW)
    with pytest.raises(ValueError, match="reference_time"):
        qualify_limited_activation((), qualification_id="q", reference_time="")
    with pytest.raises(ValueError, match="policy"):
        qualify_limited_activation((), qualification_id="q", reference_time=NOW, policy={})


def test_caller_prior_result_and_canonical_objects_are_mutation_safe():
    skill = next(x for x in get_business_skill_registry() if x.skill_id == QUALIFICATION_SKILL_IDS[0])
    canonical_before = get_business_skill_registry()
    audit_before = skill.tests_required
    source = qualification_input(skill, "immutable-")
    first = qualify_limited_activation((source,), qualification_id="immutable", reference_time=NOW)
    with pytest.raises(FrozenInstanceError):
        first.results[0].observation_count = 999
    with pytest.raises(FrozenInstanceError):
        first.results[0].recommendation.recommendation = "ACTIVATE"
    with pytest.raises(FrozenInstanceError):
        source.lifecycle_history = ()
    with pytest.raises(FrozenInstanceError):
        skill.active_status = LIMITED_ACTIVE
    with pytest.raises(TypeError):
        audit_before[0] = "mutated"
    assert first == qualify_limited_activation((source,), qualification_id="immutable", reference_time=NOW)
    assert get_business_skill_registry() == canonical_before
    assert skill.tests_required == audit_before


def test_authority_leakage_is_rejected_by_contract_and_absent_from_results():
    with pytest.raises(TypeError):
        LimitedActivationRecommendation(
            skill_id=QUALIFICATION_SKILL_IDS[0],
            recommendation=QUALIFIED_FOR_LIMITED_ACTIVE_PROMOTION,
            authorization=True,
        )
    forbidden = {"answer", "calculation", "business_reasoning", "user_response", "follow_up",
                 "authorization", "authorized", "execution_instruction", "tool_invocation",
                 "persistence", "routing_instruction", "runtime_activated"}
    skill = next(x for x in get_business_skill_registry() if x.skill_id == QUALIFICATION_SKILL_IDS[0])
    result = qualify_limited_activation(
        (qualification_input(skill, "authority-"),), qualification_id="authority", reference_time=NOW,
    )
    for value in (result, result.results[0], result.results[0].recommendation,
                  *result.results[0].gate_results):
        assert forbidden.isdisjoint(field.name for field in dataclasses.fields(value))
