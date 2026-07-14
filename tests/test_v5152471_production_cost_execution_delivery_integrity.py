"""V5.15.24.7.1 production-bound Cost execution/delivery qualification."""
from __future__ import annotations

import ast
import copy
import dataclasses
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_turn_bound_skill_evidence import create_production_turn_bound_skill_evidence_envelope
from brain.production_limited_activation_binding import create_production_limited_activation_binding
from brain.business_skill_cost_execution import CostExecutionRequest, execute_cost_skill
from brain.cost_execution_result_integrity import create_cost_execution_result_integrity
from brain.business_skill_cost_result_presenter import (
    INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION, SUPPORTED_LOCALE,
    CostPresentationRequest, present_cost_result,
)
from brain.business_skill_cost_response_authorization import (
    AUTHORIZATION_POLICY_VERSION, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE,
    CostResponseAuthorizationRequest, authorize_cost_response,
)
from brain.business_skill_cost_response_adapter import CostResponseAdapterRequest, adapt_authorized_cost_response
from brain.business_skill_cost_response_delivery_qualification import (
    CostDeliveryQualificationCase, qualify_cost_response_delivery,
)
from brain.cost_rendered_delivery_provenance_integrity import (
    create_cost_adapter_result_integrity, create_cost_authorization_decision_integrity,
    create_cost_delivery_provenance_integrity, create_cost_presentation_result_integrity,
)
from brain.production_cost_execution_delivery_integrity import *


CHANGE = "  my cost increased from 20.00 to 24.000\n"
UNIT = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น ของเสีย 2 ชิ้น"


def chain(message=CHANGE, suffix="1"):
    context = create_production_turn_context("conversation-" + suffix, 1, message)
    reference = create_production_turn_reference_time(
        context, datetime(2026, 7, 14, 3, 4, 5, tzinfo=timezone.utc))
    gate = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    envelope = create_production_turn_bound_skill_evidence_envelope(context, gate)
    activation = create_production_limited_activation_binding(context, reference, gate, envelope)
    request = CostExecutionRequest("execution-" + suffix, activation.activation_request_id,
                                   envelope.selected_skill_id, activation.limited_activation_decision)
    result = execute_cost_skill(request)
    execution = create_cost_execution_result_integrity(request, result)
    prequest = CostPresentationRequest(
        "presentation-" + suffix, request.execution_id, request.request_id,
        request.requested_skill_id, result, SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY,
        PRESENTATION_VERSION)
    presult = present_cost_result(prequest)
    presentation = create_cost_presentation_result_integrity(execution, prequest, presult)
    arequest = CostResponseAuthorizationRequest(
        "authorization-" + suffix, prequest.presentation_id, request.execution_id,
        request.request_id, request.requested_skill_id, presult, LIMITED_COST_RESPONSE,
        USER_TEXT_RESPONSE, AUTHORIZATION_POLICY_VERSION)
    adecision = authorize_cost_response(arequest)
    authorization = create_cost_authorization_decision_integrity(presentation, arequest, adecision)
    adrequest = CostResponseAdapterRequest("adapter-" + suffix, adecision)
    adresult = adapt_authorized_cost_response(adrequest)
    adapter = create_cost_adapter_result_integrity(authorization, adrequest, adresult)
    case = CostDeliveryQualificationCase(
        "case-" + suffix, request.request_id, request.requested_skill_id,
        request.execution_id, prequest.presentation_id, arequest.authorization_id,
        adrequest.adapter_request_id, adecision, adresult, adresult)
    qualification = qualify_cost_response_delivery(
        (case,), qualification_id="qualification-" + suffix,
        reference_time=reference.accepted_at_iso).results[0]
    delivery = create_cost_delivery_provenance_integrity(adapter, case, qualification)
    args = (context, reference, gate, envelope, activation, execution,
            presentation, authorization, adapter, delivery)
    return args, create_production_cost_execution_delivery_integrity(*args)


@pytest.mark.parametrize("message,skill,operand_ids", (
    (CHANGE, "cost.change_analysis.v1", ("previous_cost", "current_cost")),
        ("ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น", "cost.per_unit_calculation.v1",
     ("total_cost", "unit_quantity")),
    (UNIT, "cost.per_unit_calculation.v1",
     ("total_cost", "unit_quantity", "waste_or_loss_quantity")),
))
def test_full_isolated_chain_both_skills_and_optional_waste(message, skill, operand_ids):
    _, value = chain(message)
    assert value is not None and verify_production_cost_execution_delivery_integrity(value)
    assert value.version == PRODUCTION_COST_EXECUTION_DELIVERY_INTEGRITY_VERSION == "5.15.24.7.1"
    assert value.qualification_status == QUALIFIED
    assert value.selected_skill_id == skill
    assert tuple(item.evidence_id for item in value.ordered_decimal_operands) == operand_ids
    assert all(type(item.normalized_value) is Decimal
               for item in value.execution_integrity.execution_request.decision.binding.evidence_snapshot)
    assert tuple(item.gate for item in value.gate_results) == GATE_ORDER
    assert all(item.passed for item in value.gate_results)


def test_gate_default_deny_eligibility_is_not_production_authority():
    _, value = chain()
    assert value.feature_gate_effective_state is False and value.feature_gate_default_denied is True
    assert value.eligibility_allowed is True and value.production_activation_claimed is False
    assert value.executable_output is None
    assert all(getattr(value, name) is False for name in value.__dataclass_fields__
               if name.endswith("_authority") or name in (
                   "delivery_committed", "response_candidate_created", "runtime_invoked", "admission_invoked"))


def test_exact_thai_whitespace_newline_and_text_digest_continuity():
    _, value = chain()
    assert value.context.user_message == CHANGE
    text = value.adapter_integrity.adapter_result.payload.text
    assert "\n" in text
    assert value.rendered_text_digest == value.authorized_text_digest == value.payload_text_digest
    assert text == value.authorization_integrity.authorization_decision.authorized_artifact.authorized_text


def test_reference_time_exact_utc_seconds_continuity():
    _, value = chain()
    assert value.accepted_at_iso == "2026-07-14T03:04:05+00:00"
    assert value.delivery_integrity.reference_time == value.accepted_at_iso
    assert value.timezone_identity == "UTC"
    assert value.precision_identity == "SECONDS_0_FRACTIONAL_DIGITS"


def test_repeat_deepcopy_equality_and_frozen_nesting():
    _, first = chain()
    _, second = chain()
    assert first == second == copy.deepcopy(first)
    assert ProductionCostExecutionDeliveryIntegrity.__dataclass_params__.frozen
    assert ProductionCostDeliveryGateResult.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.integrity_digest = "0" * 64


@pytest.mark.parametrize("index", range(10))
def test_each_upstream_layer_substitution_fails_closed(index):
    args, value = chain()
    other, _ = chain(UNIT, "2")
    mixed = list(args)
    mixed[index] = other[index]
    denied = create_production_cost_execution_delivery_integrity(*mixed)
    assert denied is None or (
        verify_production_cost_execution_delivery_integrity(denied)
        and denied.qualification_status == DENIED
        and denied.reasons[0] != "ALL_QUALIFICATION_GATES_PASSED")
    version_fields = (
        "context_version", "reference_time_version", "owner_version", "envelope_version",
        "version", "version", "version", "version", "version", "version",
    )
    historical = list(args)
    historical[index] = dataclasses.replace(
        historical[index], **{version_fields[index]: "5.15.24.0"})
    rejected = create_production_cost_execution_delivery_integrity(*historical)
    assert rejected is None or rejected.qualification_status == DENIED
    assert verify_production_cost_execution_delivery_integrity(value)


def test_turn_gate_skill_activation_and_execution_tampering_rejected():
    _, value = chain()
    mutations = (
        dataclasses.replace(value, turn_digest="0" * 64),
        dataclasses.replace(value, selected_skill_id="cost.per_unit_calculation.v1"),
        dataclasses.replace(value, feature_gate_effective_state=True),
        dataclasses.replace(value, activation_request_id="forged"),
        dataclasses.replace(value, execution_request_digest="0" * 64),
        dataclasses.replace(value, formula_id="forged/formula"),
        dataclasses.replace(value, ordered_decimal_operands=tuple(reversed(value.ordered_decimal_operands))),
    )
    assert all(not verify_production_cost_execution_delivery_integrity(item) for item in mutations)


def test_render_authorization_adapter_delivery_and_reference_substitution_rejected():
    _, value = chain()
    mutations = (
        dataclasses.replace(value, rendered_text_digest="0" * 64),
        dataclasses.replace(value, authorization_decision_digest="0" * 64),
        dataclasses.replace(value, payload_digest="0" * 64),
        dataclasses.replace(value, delivery_case_digest="0" * 64),
        dataclasses.replace(value, accepted_at_iso="2026-07-14T03:04:06+00:00"),
    )
    assert all(not verify_production_cost_execution_delivery_integrity(item) for item in mutations)


def test_gate_reason_diagnostic_status_count_and_authority_tampering_rejected():
    _, value = chain()
    gate = dataclasses.replace(value.gate_results[0], passed=False, reason_codes=("TAMPERED",))
    mutations = (
        dataclasses.replace(value, gate_results=(gate,) + value.gate_results[1:]),
        dataclasses.replace(value, gate_results=tuple(reversed(value.gate_results))),
        dataclasses.replace(value, reasons=("TAMPERED",)),
        dataclasses.replace(value, diagnostics=("TAMPERED",)),
        dataclasses.replace(value, qualification_status=DENIED),
        dataclasses.replace(value, passed_gate_count=15),
        dataclasses.replace(value, production_execution_authority=True),
        dataclasses.replace(value, delivery_committed=True),
        dataclasses.replace(value, executable_output="forbidden"),
    )
    assert all(not verify_production_cost_execution_delivery_integrity(item) for item in mutations)


@pytest.mark.parametrize("digest", ("", "0" * 63, "0" * 65, "A" * 64, "g" * 64, "1" * 64))
def test_malformed_and_tampered_top_digest_rejected(digest):
    _, value = chain()
    assert not verify_production_cost_execution_delivery_integrity(
        dataclasses.replace(value, integrity_digest=digest))


def test_constructor_and_verifier_do_not_rerun_any_transformation(monkeypatch):
    args, value = chain()
    modules = (
        ("brain.production_turn_bound_skill_evidence", (
            "normalize_user_language", "normalize_candidate_message", "match_business_skill_candidates",
            "parse_canonical_cost_evidence", "map_candidate_skill_evidence", "select_shadow_business_skill")),
        ("brain.production_limited_activation_binding", ("decide_limited_activation",)),
        ("brain.business_skill_cost_execution", ("execute_cost_skill",)),
        ("brain.business_skill_cost_result_presenter", ("present_cost_result",)),
        ("brain.business_skill_cost_response_authorization", ("authorize_cost_response",)),
        ("brain.business_skill_cost_response_adapter", ("adapt_authorized_cost_response",)),
        ("brain.business_skill_cost_response_delivery_qualification", ("qualify_cost_response_delivery",)),
    )
    fail = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("pipeline rerun"))
    for module_name, names in modules:
        module = __import__(module_name, fromlist=("x",))
        for name in names:
            monkeypatch.setattr(module, name, fail)
    assert create_production_cost_execution_delivery_integrity(*args) == value
    assert verify_production_cost_execution_delivery_integrity(value)


def test_static_audit_isolated_no_runtime_app_network_persistence_or_float_conversion():
    path = Path(__file__).parents[1] / "brain" / "production_cost_execution_delivery_integrity.py"
    source = path.read_text("utf-8")
    tree = ast.parse(source)
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    forbidden_calls = {
        "create_production_turn_bound_skill_evidence_envelope",
        "create_production_limited_activation_binding", "decide_limited_activation",
        "execute_cost_skill", "present_cost_result", "authorize_cost_response",
        "adapt_authorized_cost_response", "qualify_cost_response_delivery",
        "execute_cost_runtime_bridge", "admit_cost_runtime", "float",
    }
    assert not calls & forbidden_calls
    assert all(token not in source for token in (
        "import app", "streamlit", "session_state", "requests", "socket", "subprocess",
        "production_response_candidate", "response_resolution"))
