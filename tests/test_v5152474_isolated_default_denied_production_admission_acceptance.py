"""V5.15.24.7.4 isolated default-denied boundary acceptance."""
import ast
import copy
import dataclasses
import re
from pathlib import Path

import pytest

from brain.production_default_denied_admission_acceptance import *
from brain.production_default_denied_admission_boundary import (
    DENIED_DEFAULT_PRODUCTION_GATE, DENIED_INVALID_PRODUCTION_EVIDENCE,
    DENIED_MALFORMED_REQUEST, DENIED_SKILL_IDENTITY_MISMATCH,
    INVALID_PRODUCTION_ADMISSION_EVIDENCE, MALFORMED_PRODUCTION_ADMISSION_REQUEST,
    PRODUCTION_FEATURE_GATE_DEFAULT_DENIED, PRODUCTION_SKILL_IDENTITY_MISMATCH,
    create_production_admission_boundary_request,
    verify_production_admission_boundary_decision,
)
from brain.production_single_skill_admission_evidence import (
    create_production_single_skill_admission_evidence,
)
from tests.test_v5152471_production_cost_execution_delivery_integrity import (
    CHANGE, UNIT, chain,
)

UNIT_NO_WASTE = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น"


def request(message, suffix):
    _, source = chain(message, suffix)
    evidence = create_production_single_skill_admission_evidence(source)
    return create_production_admission_boundary_request(evidence, evidence.selected_skill_id)


@pytest.fixture(scope="module")
def scenarios():
    value = create_production_admission_acceptance_scenarios(
        request(CHANGE, "a"), request(UNIT_NO_WASTE, "b"),
        request(UNIT, "c"), request(CHANGE, "d"))
    assert value is not None
    return value


@pytest.fixture(scope="module")
def report(scenarios):
    value = create_production_admission_acceptance_report(scenarios)
    assert value is not None
    return value


def test_exact_inventory_order_uniqueness_and_classification(scenarios):
    assert tuple(x.scenario_id for x in scenarios) == CANONICAL_SCENARIO_IDS
    assert len(CANONICAL_SCENARIO_IDS) == len(set(CANONICAL_SCENARIO_IDS)) == 15
    assert all(x.classification == "BOUNDARY_ACCEPTANCE" for x in scenarios)
    assert tuple(x.outcome_class for x in scenarios[:3]) == ("VALID_DEFAULT_DENIED",) * 3
    assert all(x.outcome_class == "INVALID_FAIL_CLOSED" for x in scenarios[3:])


def test_valid_both_skills_optional_waste_and_complete_lineage(report):
    valid = report.observations[:3]
    assert tuple(x.skill_id for x in valid) == (
        "cost.change_analysis.v1", "cost.per_unit_calculation.v1",
        "cost.per_unit_calculation.v1")
    assert len(valid[1].boundary_request.evidence.operand_ids) == 2
    assert len(valid[2].boundary_request.evidence.operand_ids) == 3
    assert all(x.request_verified and x.evidence_verified and x.lineage_verified for x in valid)


def test_valid_observed_canonical_default_denial(report):
    for item in report.observations[:3]:
        assert item.observed_decision_status == DENIED_DEFAULT_PRODUCTION_GATE
        assert item.observed_denial_code == PRODUCTION_FEATURE_GATE_DEFAULT_DENIED
        assert item.observed_denial_reason == "CURRENT_PRODUCTION_FEATURE_GATE_IS_DEFAULT_DENIED"
        assert tuple(x.gate for x in item.observed_decision.gate_results
                     if not x.satisfied) == ("DEFAULT_DENY_GATE_STATE",)
        assert not item.admitted and not item.admission_input_ready
        assert item.executable_output is None


def test_negative_exact_observed_precedence(report):
    expected = (
        (DENIED_MALFORMED_REQUEST, MALFORMED_PRODUCTION_ADMISSION_REQUEST),
        (DENIED_DEFAULT_PRODUCTION_GATE, PRODUCTION_FEATURE_GATE_DEFAULT_DENIED),
        (DENIED_SKILL_IDENTITY_MISMATCH, PRODUCTION_SKILL_IDENTITY_MISMATCH),
    ) + ((DENIED_INVALID_PRODUCTION_EVIDENCE,
          INVALID_PRODUCTION_ADMISSION_EVIDENCE),) * 9
    assert tuple((x.observed_decision_status, x.observed_denial_code)
                 for x in report.observations[3:]) == expected
    assert all(x.diagnostics[0].startswith("FIRST_FAILED_GATE:")
               for x in report.observations[3:])


def test_report_counts_coverage_integrity_and_isolation(report):
    assert (report.scenario_count, report.valid_default_denied_count,
            report.invalid_fail_closed_count) == (15, 3, 12)
    assert report.observed_admitted_count == 0 and report.observed_denied_count == 15
    assert report.skill_coverage == ("cost.change_analysis.v1",
                                     "cost.per_unit_calculation.v1")
    assert report.request_integrity and report.evidence_integrity and report.decision_integrity
    assert report.default_deny_verified and report.authority_isolated and report.all_passed
    assert all(getattr(report.authority_boundary, name) is False
               for name in report.authority_boundary.__dataclass_fields__)


def test_deterministic_deepcopy_immutability(scenarios, report):
    again = create_production_admission_acceptance_report(copy.deepcopy(scenarios))
    assert report == again == copy.deepcopy(report)
    assert report.report_digest == again.report_digest
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.all_passed = False


@pytest.mark.parametrize("field,value", (
    ("expected_decision_status", "EXPECTED_OTHER"),
    ("expected_denial_code", "EXPECTED_OTHER"),
))
def test_wrong_expected_outcome_fails_without_becoming_observed(scenarios, field, value):
    changed = dataclasses.replace(scenarios[0], **{field: value}, scenario_digest="")
    from brain import production_default_denied_admission_acceptance as module
    changed = dataclasses.replace(changed, scenario_digest=module._sha(
        "PRODUCTION_ADMISSION_ACCEPTANCE_SCENARIO", module._scenario_material(changed)))
    observed = observe_production_admission_acceptance_scenario(changed)
    assert observed.observation_passed is False
    assert observed.observed_decision_status == DENIED_DEFAULT_PRODUCTION_GATE
    assert observed.observed_denial_code == PRODUCTION_FEATURE_GATE_DEFAULT_DENIED


@pytest.mark.parametrize("field,value", (
    ("request_id", "substituted"), ("request_digest", "0" * 64),
    ("evidence_id", "substituted"), ("evidence_digest", "0" * 64),
))
def test_request_evidence_substitution_is_observed_not_synthetic(scenarios, field, value):
    scenario = scenarios[0]
    altered_request = dataclasses.replace(scenario.boundary_request, **{field: value})
    altered = dataclasses.replace(scenario, boundary_request=altered_request, scenario_digest="")
    from brain import production_default_denied_admission_acceptance as module
    altered = dataclasses.replace(altered, scenario_digest=module._sha(
        "PRODUCTION_ADMISSION_ACCEPTANCE_SCENARIO", module._scenario_material(altered)))
    observed = observe_production_admission_acceptance_scenario(altered)
    assert observed.observed_decision_status == DENIED_MALFORMED_REQUEST
    assert observed.observation_passed is False


@pytest.mark.parametrize("mutation", ("partial", "duplicate", "missing", "reordered"))
def test_partial_duplicate_missing_reordered_scenarios_rejected(scenarios, mutation):
    values = {"partial": scenarios[:3], "duplicate": scenarios[:-1] + (scenarios[0],),
              "missing": scenarios[:-1], "reordered": tuple(reversed(scenarios))}[mutation]
    assert create_production_admission_acceptance_report(values) is None


@pytest.mark.parametrize("field,value", (
    ("scenario_count", 14), ("valid_default_denied_count", 2),
    ("invalid_fail_closed_count", 11), ("observed_denied_count", 14),
    ("all_passed", False), ("reasons", ("TAMPERED",)),
))
def test_report_count_status_reason_tampering_rejected(report, field, value):
    assert not verify_production_admission_acceptance_report(
        dataclasses.replace(report, **{field: value}))


@pytest.mark.parametrize("digest", ("", "A" * 64, "g" * 64, "0" * 63, "0" * 65))
def test_observation_and_report_malformed_digest_rejected(report, digest):
    assert not verify_production_admission_acceptance_observation(
        dataclasses.replace(report.observations[0], observation_digest=digest))
    assert not verify_production_admission_acceptance_report(
        dataclasses.replace(report, report_digest=digest))


@pytest.mark.parametrize("field,value", (
    ("observation_passed", False), ("observed_denial_code", "TAMPERED"),
    ("decision_digest", "0" * 64), ("authority_isolated", False),
))
def test_observation_status_diagnostic_chain_tampering_rejected(report, field, value):
    assert not verify_production_admission_acceptance_observation(
        dataclasses.replace(report.observations[0], **{field: value}))


@pytest.mark.parametrize("field,value", (
    ("decision_digest", ""), ("decision_digest", "A" * 64),
    ("decision_digest", "g" * 64), ("decision_digest", "0" * 63),
    ("decision_digest", "0" * 65), ("admitted", True),
    ("admission_input_ready", True), ("executable_output", "injected"),
    ("denial_code", "TAMPERED"), ("denial_reason", "TAMPERED"),
    ("decision_status", "TAMPERED"),
))
def test_post_decision_integrity_tampering_is_verifier_only(report, field, value):
    observation = report.observations[0]
    altered = dataclasses.replace(observation.observed_decision, **{field: value})
    assert not verify_production_admission_boundary_decision(
        observation.boundary_request, altered)
    assert report.scenario_count == 15


@pytest.mark.parametrize("mutation", ("reverse", "duplicate", "missing", "authority"))
def test_post_decision_gate_and_authority_tampering_verifier_only(report, mutation):
    observation = report.observations[0]
    decision = observation.observed_decision
    gates = {"reverse": tuple(reversed(decision.gate_results)),
             "duplicate": decision.gate_results + (decision.gate_results[0],),
             "missing": decision.gate_results[:-1]}
    if mutation == "authority":
        altered = dataclasses.replace(decision, authority_boundary=dataclasses.replace(
            decision.authority_boundary, admission=True))
    else:
        altered = dataclasses.replace(decision, gate_results=gates[mutation])
    assert not verify_production_admission_boundary_decision(observation.boundary_request, altered)


def test_post_decision_cross_request_and_digest_substitution_verifier_only(report):
    first, second = report.observations[:2]
    assert not verify_production_admission_boundary_decision(
        first.boundary_request, second.observed_decision)
    altered = dataclasses.replace(first.observed_decision,
                                  request_digest=second.request_digest,
                                  evidence_digest=second.evidence_digest)
    assert not verify_production_admission_boundary_decision(first.boundary_request, altered)


def test_report_reverification_reruns_only_pure_boundary(monkeypatch, report):
    import brain.business_skill_cost_execution as execution
    import brain.business_skill_cost_result_presenter as presentation
    import brain.business_skill_cost_response_authorization as authorization
    import brain.business_skill_cost_response_adapter as adapter
    import brain.business_skill_cost_response_delivery_qualification as delivery
    for module, name in ((execution, "execute_cost_skill"),
                         (presentation, "present_cost_result"),
                         (authorization, "authorize_cost_response"),
                         (adapter, "adapt_authorized_cost_response"),
                         (delivery, "qualify_cost_response_delivery")):
        monkeypatch.setattr(module, name, lambda *a, **k: pytest.fail("upstream rerun"))
    assert verify_production_admission_acceptance_report(report)


def test_static_forbidden_import_call_and_app_audit():
    root = Path(__file__).parents[1]
    path = root / "brain" / "production_default_denied_admission_acceptance.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports = tuple(node.module or "" for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom))
    forbidden = ("app", "streamlit", "manifest", "admission_gateway", "runtime_bridge",
                 "handoff", "response_candidate", "resolution", "persistence", "network", "llm")
    assert not any(any(token in name for token in forbidden) for name in imports)
    assert not any(token in text for token in ("session_state", "requests.", "urllib",
        "socket", "open(", "float(", "Decimal(", "feature_gate_config"))
    assert "app.py" not in text


def test_frozen_contracts_and_digest_format(report):
    assert all(cls.__dataclass_params__.frozen for cls in (
        ProductionAdmissionAcceptanceScenario, ProductionAdmissionAcceptanceObservation,
        ProductionAdmissionAcceptanceReport, ProductionAdmissionAcceptanceAuthorityBoundary))
    assert re.fullmatch(r"[0-9a-f]{64}", report.report_digest)
    assert all(re.fullmatch(r"[0-9a-f]{64}", x.observation_digest)
               for x in report.observations)
