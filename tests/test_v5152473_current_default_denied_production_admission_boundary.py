"""V5.15.24.7.3 current default-denied production boundary."""
import ast
import copy
import dataclasses
import re
from pathlib import Path

import pytest

from brain.production_default_denied_admission_boundary import *
from brain.production_single_skill_admission_evidence import (
    create_production_single_skill_admission_evidence,
)
from tests.test_v5152471_production_cost_execution_delivery_integrity import (
    CHANGE, UNIT, chain,
)


def boundary(message=CHANGE):
    _, source = chain(message)
    evidence = create_production_single_skill_admission_evidence(source)
    request = create_production_admission_boundary_request(
        evidence, evidence.selected_skill_id)
    return evidence, request, evaluate_default_denied_production_admission(request)


@pytest.mark.parametrize("message,skill", (
    (CHANGE, "cost.change_analysis.v1"),
    (UNIT, "cost.per_unit_calculation.v1"),
))
def test_current_evidence_has_canonical_default_denial(message, skill):
    evidence, request, decision = boundary(message)
    assert request.selected_skill_id == decision.selected_skill_id == skill
    assert decision.decision_status == DENIED_DEFAULT_PRODUCTION_GATE
    assert decision.denial_code == PRODUCTION_FEATURE_GATE_DEFAULT_DENIED
    assert decision.denial_reason == "CURRENT_PRODUCTION_FEATURE_GATE_IS_DEFAULT_DENIED"
    assert not decision.admitted and not decision.admission_input_ready
    assert decision.executable_output is None and evidence.eligibility_allowed


def test_exact_request_evidence_and_production_identity_binding():
    evidence, request, decision = boundary()
    assert decision.request_id == request.request_id
    assert decision.request_digest == request.request_digest
    assert decision.evidence_id == request.evidence_id == evidence.evidence_id
    assert decision.evidence_digest == request.evidence_digest == evidence.evidence_digest
    assert (decision.conversation_id, decision.turn_id, decision.turn_digest) == (
        evidence.conversation_id, evidence.turn_id, evidence.turn_digest)
    assert decision.reference_time_digest == evidence.reference_time_digest
    assert decision.feature_gate_evaluation_digest == evidence.feature_gate_evaluation_digest


def test_verified_lineage_not_caller_boolean_drives_outcome():
    evidence, request, decision = boundary()
    assert decision.request_verified and decision.evidence_verified and decision.lineage_verified
    assert decision.configured_state is False and decision.effective_state is False
    assert decision.default_denied is True
    assert tuple(x.gate for x in decision.gate_results) == GATE_ORDER
    failed = tuple(x.gate for x in decision.gate_results if not x.satisfied)
    assert failed == ("DEFAULT_DENY_GATE_STATE",)
    assert decision.diagnostics[0] == "FIRST_FAILED_GATE:DEFAULT_DENY_GATE_STATE"


def test_all_authority_is_false_and_contracts_are_frozen():
    _, request, decision = boundary()
    assert all(getattr(decision.authority_boundary, name) is False
               for name in decision.authority_boundary.__dataclass_fields__)
    assert all(cls.__dataclass_params__.frozen for cls in (
        ProductionAdmissionBoundaryRequest, ProductionAdmissionBoundaryDecision,
        ProductionAdmissionBoundaryGateResult,
        ProductionAdmissionBoundaryAuthorityBoundary))
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.scope = "x"


def test_deterministic_deepcopy_and_repeat_verification():
    evidence, request, decision = boundary()
    request2 = create_production_admission_boundary_request(
        copy.deepcopy(evidence), evidence.selected_skill_id)
    decision2 = evaluate_default_denied_production_admission(request2)
    assert request == request2 == copy.deepcopy(request)
    assert decision == decision2 == copy.deepcopy(decision)
    assert verify_production_admission_boundary_request(request)
    assert verify_production_admission_boundary_decision(request, decision)
    assert verify_production_admission_boundary_decision(request, decision)


@pytest.mark.parametrize("selector", (None, "", " ", "unknown", 1,
    "cost.per_unit_calculation.v1"))
def test_malformed_blank_wrong_skill_selector_rejected(selector):
    evidence, _, _ = boundary()
    assert create_production_admission_boundary_request(evidence, selector) is None


@pytest.mark.parametrize("field,value", (
    ("request_id", "x"), ("request_digest", "0" * 64),
    ("version", "5.15.24.7.2"), ("scope", "HISTORICAL"),
))
def test_request_identity_or_scope_tampering_denied(field, value):
    _, request, _ = boundary()
    altered = dataclasses.replace(request, **{field: value})
    decision = evaluate_default_denied_production_admission(altered)
    assert decision.decision_status == DENIED_MALFORMED_REQUEST
    assert not verify_production_admission_boundary_request(altered)


@pytest.mark.parametrize("field,value", (
    ("evidence_id", "other"), ("evidence_digest", "0" * 64),
))
def test_request_evidence_binding_substitution_denied(field, value):
    _, request, _ = boundary()
    altered = dataclasses.replace(request, **{field: value})
    decision = evaluate_default_denied_production_admission(altered)
    assert not decision.admitted
    assert decision.decision_status == DENIED_MALFORMED_REQUEST


def test_cross_skill_and_cross_evidence_substitution_denied():
    change_e, change_r, _ = boundary(CHANGE)
    unit_e, _, _ = boundary(UNIT)
    cross_skill = dataclasses.replace(change_r, selected_skill_id=unit_e.selected_skill_id)
    cross_evidence = dataclasses.replace(change_r, evidence=unit_e)
    assert all(evaluate_default_denied_production_admission(item).decision_status
               in (DENIED_MALFORMED_REQUEST, DENIED_INVALID_PRODUCTION_EVIDENCE,
                   DENIED_SKILL_IDENTITY_MISMATCH)
               for item in (cross_skill, cross_evidence))
    assert change_e.turn_digest != unit_e.turn_digest


@pytest.mark.parametrize("field,value", (
    ("version", "5.15.24.7.1"), ("scope", "HISTORICAL"),
    ("turn_digest", "0" * 64), ("reference_time_digest", "0" * 64),
    ("payload_digest", "0" * 64), ("delivery_integrity_digest", "0" * 64),
))
def test_noncanonical_historical_lineage_or_payload_evidence_denied(field, value):
    evidence, request, _ = boundary()
    bad = dataclasses.replace(evidence, **{field: value})
    altered = dataclasses.replace(request, evidence=bad)
    decision = evaluate_default_denied_production_admission(altered)
    assert decision.decision_status == DENIED_INVALID_PRODUCTION_EVIDENCE
    assert not decision.evidence_verified and not decision.admitted


@pytest.mark.parametrize("configured,effective,default", (
    (False, False, False), (True, True, False), (True, False, True),
))
def test_configured_disabled_enabled_or_nondefault_gate_is_out_of_scope(
    configured, effective, default,
):
    evidence, request, _ = boundary()
    feature = dataclasses.replace(evidence.source.feature_gate_evaluation,
        configured_state=configured, effective_state=effective,
        default_denied=default)
    source = dataclasses.replace(evidence.source, feature_gate_evaluation=feature)
    bad = dataclasses.replace(evidence, source=source, configured_state=configured,
                              effective_state=effective, default_denied=default)
    decision = evaluate_default_denied_production_admission(
        dataclasses.replace(request, evidence=bad))
    assert not decision.admitted
    assert decision.decision_status == DENIED_INVALID_PRODUCTION_EVIDENCE


def test_gate_identity_and_evaluation_substitution_denied():
    evidence, request, _ = boundary()
    for bad in (dataclasses.replace(evidence, feature_gate_name="OTHER"),
                dataclasses.replace(evidence, feature_gate_evaluation_digest="0" * 64)):
        decision = evaluate_default_denied_production_admission(
            dataclasses.replace(request, evidence=bad))
        assert decision.decision_status == DENIED_INVALID_PRODUCTION_EVIDENCE


def test_gate_order_duplicate_missing_are_rejected_by_decision_verifier():
    _, request, decision = boundary()
    mutations = (tuple(reversed(decision.gate_results)),
                 decision.gate_results[:-1],
                 decision.gate_results + (decision.gate_results[0],))
    assert all(not verify_production_admission_boundary_decision(
        request, dataclasses.replace(decision, gate_results=value)) for value in mutations)


@pytest.mark.parametrize("field,value", (
    ("decision_status", "DENIED_OTHER"), ("admitted", True),
    ("denial_code", "OTHER"), ("denial_reason", "OTHER"),
    ("reasons", ("OTHER",)), ("diagnostics", ("OTHER",)),
    ("executable_output", "injected"),
))
def test_decision_outcome_diagnostic_and_output_tampering_rejected(field, value):
    _, request, decision = boundary()
    assert not verify_production_admission_boundary_decision(
        request, dataclasses.replace(decision, **{field: value}))


@pytest.mark.parametrize("digest", ("", "A" * 64, "g" * 64,
    "0" * 63, "0" * 65, None))
def test_malformed_decision_digest_rejected(digest):
    _, request, decision = boundary()
    assert not verify_production_admission_boundary_decision(
        request, dataclasses.replace(decision, decision_digest=digest))


def test_authority_escalation_and_decision_substitution_rejected():
    _, request, decision = boundary(CHANGE)
    _, other_request, other_decision = boundary(UNIT)
    escalated = dataclasses.replace(decision, authority_boundary=dataclasses.replace(
        decision.authority_boundary, admission=True))
    assert not verify_production_admission_boundary_decision(request, escalated)
    assert not verify_production_admission_boundary_decision(request, other_decision)
    assert not verify_production_admission_boundary_decision(other_request, decision)


def test_verifier_does_not_rerun_transformation_pipelines(monkeypatch):
    _, request, decision = boundary()
    import brain.business_skill_cost_execution as execution
    import brain.business_skill_cost_result_presenter as presentation
    import brain.business_skill_cost_response_authorization as authorization
    import brain.business_skill_cost_response_adapter as adapter
    import brain.business_skill_cost_response_delivery_qualification as delivery
    names = ((execution, "execute_cost_skill"), (presentation, "present_cost_result"),
             (authorization, "authorize_cost_response"),
             (adapter, "adapt_authorized_cost_response"),
             (delivery, "qualify_cost_response_delivery"))
    for module, name in names:
        monkeypatch.setattr(module, name, lambda *a, **k: pytest.fail("pipeline rerun"))
    assert verify_production_admission_boundary_request(request)
    assert verify_production_admission_boundary_decision(request, decision)


def test_static_isolation_and_import_prohibitions():
    root = Path(__file__).parents[1]
    path = root / "brain" / "production_default_denied_admission_boundary.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported = tuple(alias.name for node in ast.walk(tree)
                     if isinstance(node, ast.Import) for alias in node.names) + tuple(
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
    forbidden_imports = ("app", "streamlit", "integration_manifest",
        "integration_qualification", "business_skill_admission_gateway",
        "runtime_bridge", "handoff")
    assert not any(any(token in name for token in forbidden_imports) for name in imported)
    forbidden_text = ("session_state", "requests.", "urllib", "socket", "open(",
                      "float(", "Decimal(")
    assert not any(token in text for token in forbidden_text)
    assert "app.py" not in text
    assert re.fullmatch(r"[0-9a-f]{64}", boundary()[2].decision_digest)
