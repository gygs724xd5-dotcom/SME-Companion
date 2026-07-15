import ast
import dataclasses
from pathlib import Path

import pytest

import brain.production_pre_execution_authorization_runtime as runtime
import brain.production_pre_execution_authorization_runtime_acceptance as owner
from brain.production_pre_execution_authorization import (
    DENIED_DEFAULT_PRODUCTION_GATE, EVIDENCE_NOT_READY, NOT_APPLICABLE,
    PRODUCTION_FEATURE_GATE_DEFAULT_DENIED,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def matrix():
    scenarios = owner.create_production_pre_execution_runtime_acceptance_scenarios()
    report = owner.create_production_pre_execution_runtime_acceptance_report(scenarios)
    assert scenarios is not None and report is not None
    return scenarios, report


def test_frozen_contracts_version_scope_and_inventory(matrix):
    scenarios, report = matrix
    for contract in (owner.ProductionPreExecutionRuntimeAcceptanceScenario,
                     owner.ProductionPreExecutionRuntimeAcceptanceObservation,
                     owner.ProductionPreExecutionRuntimeAcceptanceReport,
                     owner.ProductionPreExecutionRuntimeAcceptanceAuthorityBoundary):
        assert dataclasses.is_dataclass(contract)
        assert contract.__dataclass_params__.frozen
    assert owner.READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE_VERSION == "5.15.24.7.4.4"
    assert report.canonical_scenario_ids == owner.CANONICAL_SCENARIO_IDS
    assert tuple(item.scenario_id for item in scenarios) == owner.CANONICAL_SCENARIO_IDS


def test_all_observations_are_exact_runtime_resolver_wrappers(matrix):
    for scenario, observation in zip(matrix[0], matrix[1].observations):
        foundations = (scenario.turn_context, scenario.reference_time,
                       scenario.feature_gate_evaluation, scenario.skill_evidence_envelope,
                       scenario.limited_activation_binding)
        exact = runtime.resolve_production_pre_execution_authorization_runtime_evidence(*foundations)
        assert observation.runtime_evidence == exact
        assert runtime.verify_production_pre_execution_authorization_runtime_evidence(
            observation.runtime_evidence)
        assert observation.runtime_evidence_digest == exact.runtime_evidence_digest


def test_exact_runtime_status_matrix_and_counts(matrix):
    report = matrix[1]
    assert tuple(item.observed_status for item in report.observations) == (
        DENIED_DEFAULT_PRODUCTION_GATE, DENIED_DEFAULT_PRODUCTION_GATE,
        DENIED_DEFAULT_PRODUCTION_GATE, NOT_APPLICABLE,
        EVIDENCE_NOT_READY, EVIDENCE_NOT_READY, EVIDENCE_NOT_READY,
    )
    assert (report.total_count, report.default_denied_count, report.not_applicable_count,
            report.evidence_not_ready_count, report.eligibility_denied_observed_count,
            report.invalid_observed_count) == (7, 3, 1, 3, 0, 0)
    assert report.runtime_wrapper_created_count == 7


def test_default_deny_not_applicable_and_partial_evidence_boundaries(matrix):
    observations = matrix[1].observations
    for item in observations[:3]:
        assert item.observed_code == PRODUCTION_FEATURE_GATE_DEFAULT_DENIED
        assert item.eligibility_allowed is True
        assert item.first_failed_gate == "DEFAULT_DENY_GATE_STATE"
    assert observations[3].selected_skill_id is None
    assert observations[3].first_failed_gate == "APPLICABILITY"
    for item in observations[4:]:
        assert item.first_failed_gate == "EVIDENCE_READINESS"
        assert item.observed_status == EVIDENCE_NOT_READY


def test_all_current_decisions_are_non_executable_and_authority_free(matrix):
    report = matrix[1]
    assert (report.execute_allowed_count, report.executable_request_count,
            report.controlled_candidate_count,
            report.bridge_admission_runtime_delivery_count) == (0, 0, 0, 0)
    assert report.persistence_isolation and report.authority_isolation
    for item in report.observations:
        assert not item.execute_allowed
        assert item.executable_request is item.controlled_response_candidate is None
        assert all(getattr(item.authority_boundary, field.name) is False
                   for field in dataclasses.fields(item.authority_boundary))


def test_rerun_identity_and_pipeline_disclosure(matrix):
    report = matrix[1]
    assert all(item.rerun_reused_same_wrapper for item in report.observations)
    assert report.pure_eligibility_pipeline_evaluation_count_per_observation == 1
    assert "EXACT_RERUN_REUSES_WRAPPER_WITHOUT_REEVALUATION" in report.diagnostics


def test_strict_report_reconstructs_and_does_not_trust_booleans_or_counts(matrix):
    report = matrix[1]
    assert owner.verify_production_pre_execution_runtime_acceptance_report(report)
    for forged in (dataclasses.replace(report, all_passed=False),
                   dataclasses.replace(report, total_count=6),
                   dataclasses.replace(report, execute_allowed_count=1)):
        assert not owner.verify_production_pre_execution_runtime_acceptance_report(forged)


@pytest.mark.parametrize("kind", ("missing", "duplicate", "reordered", "partial"))
def test_report_rejects_silent_inventory_changes(matrix, kind):
    scenarios = matrix[0]
    variants = {
        "missing": scenarios[1:], "duplicate": scenarios[:-1] + (scenarios[-2],),
        "reordered": (scenarios[1], scenarios[0], *scenarios[2:]),
        "partial": scenarios[:3],
    }
    assert owner.create_production_pre_execution_runtime_acceptance_report(variants[kind]) is None


@pytest.mark.parametrize("index", range(5))
def test_resolver_containment_for_missing_foundation(matrix, index):
    scenario = matrix[0][0]
    values = [scenario.turn_context, scenario.reference_time,
              scenario.feature_gate_evaluation, scenario.skill_evidence_envelope,
              scenario.limited_activation_binding]
    values[index] = None
    assert runtime.resolve_production_pre_execution_authorization_runtime_evidence(*values) is None


def test_resolver_contains_internal_exception(monkeypatch, matrix):
    scenario = matrix[0][0]
    monkeypatch.setattr(runtime, "create_production_pre_execution_authorization_runtime_evidence",
                        lambda *_args: (_ for _ in ()).throw(RuntimeError("contained")))
    assert runtime.resolve_production_pre_execution_authorization_runtime_evidence(
        scenario.turn_context, scenario.reference_time, scenario.feature_gate_evaluation,
        scenario.skill_evidence_envelope, scenario.limited_activation_binding) is None


@pytest.mark.parametrize("digest", ("", "A" * 64, "g" * 64, "0" * 63, "0" * 65))
def test_post_wrapper_digest_tampering_is_verifier_only(matrix, digest):
    wrapper = matrix[1].observations[0].runtime_evidence
    assert not runtime.verify_production_pre_execution_authorization_runtime_evidence(
        dataclasses.replace(wrapper, runtime_evidence_digest=digest))


@pytest.mark.parametrize("changes", (
    {"decision_status": "FORGED"}, {"denial_code": "FORGED"},
    {"execute_allowed": True}, {"executable_request": object()},
    {"controlled_response_candidate": object()}, {"request_digest": "0" * 64},
))
def test_post_wrapper_field_injection_is_verifier_only(matrix, changes):
    wrapper = matrix[1].observations[0].runtime_evidence
    assert not runtime.verify_production_pre_execution_authorization_runtime_evidence(
        dataclasses.replace(wrapper, **changes))


def test_request_decision_cross_turn_and_authority_substitution_rejected(matrix):
    first, second = matrix[1].observations[:2]
    wrapper = first.runtime_evidence
    assert not runtime.verify_production_pre_execution_authorization_runtime_evidence(
        dataclasses.replace(wrapper, authorization_request=second.runtime_evidence.authorization_request))
    assert not runtime.verify_production_pre_execution_authorization_runtime_evidence(
        dataclasses.replace(wrapper, observed_decision=second.runtime_evidence.observed_decision))
    escalated = dataclasses.replace(wrapper.authority_boundary, execution=True)
    assert not runtime.verify_production_pre_execution_authorization_runtime_evidence(
        dataclasses.replace(wrapper, authority_boundary=escalated))


def test_ast_production_order_single_passive_call_and_no_conditional_read():
    source = (ROOT / "app.py").read_text("utf-8")
    tree = ast.parse(source)
    chat = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == "_show_chat_companion")
    calls = [node for node in ast.walk(chat) if isinstance(node, ast.Call)]
    runtime_calls = [node for node in calls if getattr(node.func, "id", "") ==
                     "resolve_production_pre_execution_authorization_runtime_evidence"]
    assert len(runtime_calls) == 1
    activation = next(node.lineno for node in calls if getattr(node.func, "id", "") ==
                      "resolve_production_limited_activation_binding")
    response = min(node.lineno for node in calls
                   if getattr(node.func, "id", "") == "_record_turn_bound_response_candidate"
                   and node.lineno > runtime_calls[0].lineno)
    assert activation < runtime_calls[0].lineno < response
    forbidden = ("current_production_pre_execution_authorization", "execute_allowed",
                 "decision_status", "selected_skill_id")
    assert not any(any(term in ast.unparse(node.test) for term in forbidden)
                   for node in ast.walk(chat) if isinstance(node, (ast.If, ast.While, ast.IfExp)))


def test_quick_action_and_lifecycle_atomic_owner_source_contract():
    source = (ROOT / "app.py").read_text("utf-8")
    chat_start = source.index("def _show_chat_companion(")
    assert source.index("if pending_quick_action:", chat_start) < source.index(
        'st.session_state["current_production_turn_context"] = resolve_production_turn_context(',
        chat_start)
    key = "current_production_pre_execution_authorization"
    assert source.count(key) == 7
    assert source.count(f'st.session_state["{key}"] = None') == 4
    assert source.count(f'st.session_state.setdefault("{key}", None)') == 1


def test_acceptance_has_no_app_downstream_or_persistence_imports():
    source = (ROOT / "brain" / "production_pre_execution_authorization_runtime_acceptance.py").read_text("utf-8")
    imports = tuple(node.module or "" for node in ast.walk(ast.parse(source))
                    if isinstance(node, ast.ImportFrom))
    assert "app" not in imports
    forbidden = ("business_skill_cost_execution", "presenter", "adapter", "delivery",
                 "runtime_bridge", "admission", "production_response_candidate",
                 "final_response_resolution", "business_memory", "conversation_memory",
                 "store_profile", "streamlit", "requests", "openai")
    assert not any(any(term in name for term in forbidden) for name in imports)


def test_causal_isolation_when_downstream_entry_points_throw(monkeypatch):
    import importlib
    targets = (
        ("brain.business_skill_cost_execution", "execute_cost_skill"),
        ("brain.business_skill_cost_result_presenter", "present_cost_result"),
        ("brain.business_skill_cost_response_authorization", "authorize_cost_response"),
        ("brain.business_skill_cost_response_adapter", "adapt_authorized_cost_response"),
        ("brain.business_skill_cost_response_delivery_qualification", "qualify_cost_response_delivery"),
        ("brain.business_skill_cost_response_runtime_bridge", "bridge_prepared_cost_response"),
        ("brain.business_skill_cost_runtime_integration_admission_gateway", "decide_controlled_runtime_integration_admission"),
        ("brain.business_skill_cost_runtime_integration_qualification", "qualify_controlled_runtime_integration"),
    )
    def forbidden(*_args, **_kwargs):
        raise AssertionError("downstream called")
    for module, attribute in targets:
        monkeypatch.setattr(importlib.import_module(module), attribute, forbidden)
    scenarios = owner.create_production_pre_execution_runtime_acceptance_scenarios()
    report = owner.create_production_pre_execution_runtime_acceptance_report(scenarios)
    assert report is not None and owner.verify_production_pre_execution_runtime_acceptance_report(report)


def test_historical_pre_execution_contract_has_no_later_milestone_diff():
    # Later production wiring may extend app.py but must not rewrite this historical contract.
    import subprocess
    changed = subprocess.run([
        "git", "diff", "--name-only", "--",
        "brain/production_pre_execution_authorization.py",
        "brain/production_pre_execution_authorization_acceptance.py",
    ],
                             cwd=ROOT, text=True, capture_output=True, check=True).stdout
    assert changed == ""
