"""V5.15.24 isolated controlled-runtime integration acceptance."""
import dataclasses
from pathlib import Path

import pytest

from brain.business_skill_cost_runtime_integration_acceptance import *
from brain.business_skill_cost_runtime_integration_admission_gateway import (
    decide_controlled_runtime_integration_admission,
    verify_controlled_runtime_integration_admission_decision,
)
from brain.business_skill_cost_runtime_integration_manifest import (
    create_controlled_integration_manifest,
)
from tests.test_v51522_controlled_runtime_integration_manifest import qualifications


def canonical_manifest():
    return create_controlled_integration_manifest(qualifications())


def scenarios():
    return build_canonical_acceptance_scenarios(canonical_manifest())


def test_full_gateway_matrix_order_classification_and_results():
    source = scenarios()
    assert tuple(x.scenario_id for x in source) == CANONICAL_SCENARIO_IDS
    assert len(source) == len(set(CANONICAL_SCENARIO_IDS)) == 15
    observations = tuple(observe_integration_acceptance_scenario(x) for x in source)
    assert all(x.observation_passed for x in observations)
    assert tuple(x.observed_admitted for x in observations) == (True, True) + (False,) * 13
    assert observations[2].observed_denial_code == "UNSUPPORTED_OR_MALFORMED_SKILL_ID"
    assert all(x.observed_denial_code == "INVALID_OR_NONCANONICAL_MANIFEST"
        for x in observations[3:])
    assert all(x.executable_output is None and x.authority_boundary_verified
        and x.side_effect_isolation_verified for x in observations)


@pytest.mark.parametrize("index", range(15))
def test_each_gateway_scenario_is_a_real_verified_decision(index):
    scenario = scenarios()[index]
    decision = decide_controlled_runtime_integration_admission(scenario.admission_request)
    assert verify_controlled_runtime_integration_admission_decision(decision, scenario.admission_request)
    assert decision.admitted is scenario.expected_admitted
    assert decision.primary_denial_code == scenario.expected_denial_code


def test_positive_request_integrity_continuity_for_both_cost_skills():
    for scenario in scenarios()[:2]:
        observation = observe_integration_acceptance_scenario(scenario)
        approval = scenario.admission_request.manifest.approvals[
            0 if "change_analysis" in scenario.skill_id else 1]
        q = approval.qualification
        bridge, handoff = q.runtime_bridge_result, q.runtime_bridge_result.handoff
        assert observation.request_integrity_verified and observation.provenance_verified
        assert observation.request_digest == bridge.request_digest == handoff.request_digest == q.request_digest == approval.request_digest
        assert observation.payload_digest == handoff.payload_digest == q.payload_digest == approval.payload_digest


def test_report_determinism_counts_and_strict_verification():
    source = scenarios()
    one = create_integration_acceptance_report(source)
    two = create_integration_acceptance_report(source)
    assert one == two and one.all_passed
    assert (one.passed_count, one.failed_count) == (15, 0)
    assert one.scenario_ids == CANONICAL_SCENARIO_IDS
    assert one.observation_digests == tuple(x.observation_digest for x in one.observations)
    assert verify_integration_acceptance_report(one, source)


def test_contracts_are_frozen_and_runs_do_not_leak_state():
    source = scenarios()
    report = create_integration_acceptance_report(source)
    for value in (source[0], report.observations[0], report):
        with pytest.raises(dataclasses.FrozenInstanceError):
            value.acceptance_version = "changed"
    assert create_integration_acceptance_report(source) == report
    assert source == scenarios()


@pytest.mark.parametrize("mutation", (
    lambda r: dataclasses.replace(r, observations=r.observations[:-1]),
    lambda r: dataclasses.replace(r, observations=(r.observations[0],) + r.observations),
    lambda r: dataclasses.replace(r, observations=tuple(reversed(r.observations))),
    lambda r: dataclasses.replace(r, scenario_ids=r.scenario_ids[:-1]),
    lambda r: dataclasses.replace(r, observation_digests=tuple(reversed(r.observation_digests))),
    lambda r: dataclasses.replace(r, passed_count=14),
    lambda r: dataclasses.replace(r, failed_count=1),
    lambda r: dataclasses.replace(r, all_passed=False),
    lambda r: dataclasses.replace(r, authority_boundary_verified=False),
    lambda r: dataclasses.replace(r, report_digest="A" * 64),
))
def test_report_verifier_rejects_partial_duplicate_reordered_and_tampered(mutation):
    source = scenarios()
    assert not verify_integration_acceptance_report(
        mutation(create_integration_acceptance_report(source)), source)


@pytest.mark.parametrize("field,value", (
    ("acceptance_version", ""), ("scenario_id", "unknown"),
    ("skill_id", "other"), ("expected_admitted", False),
    ("observed_admitted", False), ("observed_denial_code", "FORGED"),
    ("request_integrity_verified", False), ("provenance_verified", False),
    ("authority_boundary_verified", False), ("side_effect_isolation_verified", False),
    ("observation_passed", False), ("reasons", ("FORGED",)),
    ("observation_digest", "A" * 64), ("request_digest", "0" * 63),
))
def test_observation_verifier_recomputes_semantics_and_digests(field, value):
    scenario = scenarios()[0]
    observation = observe_integration_acceptance_scenario(scenario)
    assert not verify_integration_acceptance_observation(
        dataclasses.replace(observation, **{field: value}), scenario)


def test_missing_reordered_duplicate_scenarios_cannot_create_report():
    source = scenarios()
    for bad in (source[:-1], tuple(reversed(source)), (source[0],) + source):
        with pytest.raises(ValueError):
            create_integration_acceptance_report(bad)


@pytest.mark.parametrize("field,value", (
    ("decision_digest", ""), ("decision_digest", "A" * 64),
    ("decision_digest", "g" * 64), ("decision_digest", "0" * 63),
    ("decision_digest", "0" * 65), ("admitted", False),
    ("primary_denial_code", "FORGED"), ("primary_denial_reason", "FORGED"),
    ("gate_results", ()),
    ("authority_boundary", AuthorityBoundary(routing=True)),
))
def test_post_decision_artifact_tampering_is_verifier_only(field, value):
    scenario = scenarios()[0]
    decision = decide_controlled_runtime_integration_admission(scenario.admission_request)
    tampered = dataclasses.replace(decision, **{field: value})
    assert not verify_controlled_runtime_integration_admission_decision(
        tampered, scenario.admission_request)
    assert scenario.scenario_id in CANONICAL_SCENARIO_IDS


def test_post_decision_executable_output_and_denial_gate_order_tampering():
    positive, negative = scenarios()[0], scenarios()[2]
    admitted = decide_controlled_runtime_integration_admission(positive.admission_request)
    denied = decide_controlled_runtime_integration_admission(negative.admission_request)
    object.__setattr__(admitted, "executable_output", "forged")
    assert not verify_controlled_runtime_integration_admission_decision(admitted, positive.admission_request)
    assert not verify_controlled_runtime_integration_admission_decision(
        dataclasses.replace(denied, gate_results=tuple(reversed(denied.gate_results))),
        negative.admission_request)


def test_isolation_forbidden_import_and_constructor_audit():
    path = Path(__file__).parents[1] / "brain" / "business_skill_cost_runtime_integration_acceptance.py"
    source = path.read_text(encoding="utf-8").lower()
    forbidden = ("import app", "streamlit", "session_state", "router", "planner",
        "persistence", "data store", "requests", "urllib", "socket", "openai",
        "bridge_prepared_cost_response", "qualify_controlled_runtime_integration",
        "create_controlled_integration_manifest", "response_committed=true")
    assert not any(value in source for value in forbidden)
    assert "decide_controlled_runtime_integration_admission" in source


def test_no_registry_lifecycle_or_feature_gate_mutation():
    from brain.business_skill_registry import get_business_skill_registry
    before = tuple(get_business_skill_registry())
    report = create_integration_acceptance_report(scenarios())
    after = tuple(get_business_skill_registry())
    assert before == after and report.authority_boundary_verified
    assert report.side_effect_isolation_verified
    assert FEATURE_GATE_NAME == "LIMITED_COST_RESPONSE_RUNTIME_BRIDGE"
