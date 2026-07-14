"""V5.15.24.7.0.1 canonical rendered-delivery provenance sidecars."""
from __future__ import annotations

import ast
import copy
import dataclasses
from decimal import Decimal
from pathlib import Path

import pytest

from brain.business_skill_cost_execution import CostExecutionRequest, execute_cost_skill
from brain.business_skill_cost_result_presenter import (
    INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION, SUPPORTED_LOCALE,
    CostPresentationRequest, present_cost_result,
)
from brain.business_skill_limited_activation_gateway import (
    LIMITED_ACTIVATION_GATEWAY_VERSION, SUPPORTED_ACTIVATION_SCOPE,
    LimitedActivationRequest, decide_limited_activation,
)
from brain.business_skill_cost_response_authorization import (
    AUTHORIZATION_POLICY_VERSION, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE,
    CostResponseAuthorizationRequest, authorize_cost_response,
)
from brain.business_skill_cost_response_adapter import (
    CostResponseAdapterRequest, adapt_authorized_cost_response,
)
from brain.business_skill_cost_response_delivery_qualification import (
    COST_DELIVERY_QUALIFICATION_VERSION,
    CostDeliveryQualificationCase, qualify_cost_response_delivery,
)
from brain.cost_execution_result_integrity import create_cost_execution_result_integrity
from brain.cost_rendered_delivery_provenance_integrity import *


NOW = "2026-07-14T12:00:00+07:00"


def _evidence(skill, *, high_precision=False):
    if skill == "cost.change_analysis.v1":
        values = {"previous_cost": Decimal("1.000000000000000000000000001"),
                  "current_cost": Decimal("1.000000000000000000000000002")} if high_precision else {
                      "previous_cost": Decimal("20"), "current_cost": Decimal("24")}
    else:
        values = {"total_cost": Decimal("1000"), "unit_quantity": Decimal("3"),
                  "waste_or_loss_quantity": Decimal("2.00")}
    return {key: {"value": value, "confidence": 1.0, "source": "current_turn",
                  "freshness": "current", "user_confirmed": True}
            for key, value in values.items()}


def chain(skill="cost.change_analysis.v1", suffix="1", *, high_precision=False):
    rid, eid, pid, aid, arid = (prefix + suffix for prefix in ("r", "e", "p", "a", "ar"))
    message = ("my cost increased from 20 to 24" if "change" in skill
               else "please calculate cost per unit total 1000 for 3 units")
    decision = decide_limited_activation(LimitedActivationRequest(
        rid, message, _evidence(skill, high_precision=high_precision), NOW, skill,
        SUPPORTED_ACTIVATION_SCOPE, LIMITED_ACTIVATION_GATEWAY_VERSION,
    ))
    execution_request = CostExecutionRequest(eid, rid, skill, decision)
    execution_result = execute_cost_skill(execution_request)
    execution_integrity = create_cost_execution_result_integrity(execution_request, execution_result)
    presentation_request = CostPresentationRequest(
        pid, eid, rid, skill, execution_result, SUPPORTED_LOCALE,
        INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION,
    )
    presentation_result = present_cost_result(presentation_request)
    presentation_integrity = create_cost_presentation_result_integrity(
        execution_integrity, presentation_request, presentation_result)
    authorization_request = CostResponseAuthorizationRequest(
        aid, pid, eid, rid, skill, presentation_result,
        LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE, AUTHORIZATION_POLICY_VERSION,
    )
    authorization_decision = authorize_cost_response(authorization_request)
    authorization_integrity = create_cost_authorization_decision_integrity(
        presentation_integrity, authorization_request, authorization_decision)
    adapter_request = CostResponseAdapterRequest(arid, authorization_decision)
    adapter_result = adapt_authorized_cost_response(adapter_request)
    adapter_integrity = create_cost_adapter_result_integrity(
        authorization_integrity, adapter_request, adapter_result)
    case = CostDeliveryQualificationCase(
        "case" + suffix, rid, skill, eid, pid, aid, arid,
        authorization_decision, adapter_result, adapter_result,
    )
    qualification = qualify_cost_response_delivery(
        (case,), qualification_id="qual" + suffix, reference_time=NOW).results[0]
    delivery_integrity = create_cost_delivery_provenance_integrity(
        adapter_integrity, case, qualification)
    return dict(
        execution=execution_integrity, presentation_request=presentation_request,
        presentation_result=presentation_result, presentation=presentation_integrity,
        authorization_request=authorization_request,
        authorization_decision=authorization_decision, authorization=authorization_integrity,
        adapter_request=adapter_request, adapter_result=adapter_result, adapter=adapter_integrity,
        case=case, qualification=qualification, delivery=delivery_integrity,
    )


@pytest.mark.parametrize("skill", (
    "cost.change_analysis.v1", "cost.per_unit_calculation.v1"))
def test_complete_sidecar_chain_both_cost_skills(skill):
    items = chain(skill, "2" if "per_unit" in skill else "1")
    assert verify_cost_presentation_result_integrity(items["presentation"])
    assert verify_cost_authorization_decision_integrity(items["authorization"])
    assert verify_cost_adapter_result_integrity(items["adapter"])
    assert verify_cost_delivery_provenance_integrity(items["delivery"])
    assert items["delivery"].qualification_version == COST_DELIVERY_QUALIFICATION_VERSION
    assert items["delivery"].reference_time == NOW


def test_exact_thai_text_whitespace_and_newlines_are_bound_byte_for_byte():
    items = chain()
    text = items["presentation_result"].draft.draft_text
    assert "ต้นทุนเดิม" in text and "\n" in text
    assert items["authorization_decision"].authorized_artifact.authorized_text.encode("utf-8") == text.encode("utf-8")
    assert items["adapter_result"].payload.text.encode("utf-8") == text.encode("utf-8")
    changed = dataclasses.replace(items["presentation_result"].draft, draft_text=text + "\n ")
    result = dataclasses.replace(items["presentation_result"], draft=changed)
    assert create_cost_presentation_result_integrity(
        items["execution"], items["presentation_request"], result) is None


def test_high_precision_decimal_and_repeat_run_determinism():
    first = chain(high_precision=True)
    second = chain(high_precision=True)
    assert first["presentation"] == second["presentation"]
    assert first["authorization"] == second["authorization"]
    assert first["adapter"] == second["adapter"]
    assert first["delivery"] == second["delivery"]


def test_presentation_input_output_and_execution_substitution_rejected():
    one, two = chain(suffix="1"), chain(suffix="2")
    assert create_cost_presentation_result_integrity(
        two["execution"], one["presentation_request"], one["presentation_result"]) is None
    assert create_cost_presentation_result_integrity(
        one["execution"], two["presentation_request"], one["presentation_result"]) is None
    bad = dataclasses.replace(one["presentation_result"].draft, source_execution_id="e2")
    assert create_cost_presentation_result_integrity(
        one["execution"], one["presentation_request"],
        dataclasses.replace(one["presentation_result"], draft=bad)) is None


def test_presentation_fields_text_and_digest_tampering_rejected():
    items = chain()
    draft = items["presentation_result"].draft
    mutations = (
        dataclasses.replace(draft, fields=tuple(reversed(draft.fields))),
        dataclasses.replace(draft, draft_text=draft.draft_text + "x"),
        dataclasses.replace(draft, draft_digest="0" * 64),
    )
    for changed in mutations:
        result = dataclasses.replace(items["presentation_result"], draft=changed)
        assert create_cost_presentation_result_integrity(
            items["execution"], items["presentation_request"], result) is None


def test_authorization_exact_request_decision_artifact_and_text_binding():
    items = chain()
    assert items["authorization"].authorization_request.presentation_result == items["presentation_result"]
    artifact = items["authorization_decision"].authorized_artifact
    bad_artifact = dataclasses.replace(artifact, authorized_text=artifact.authorized_text + "x")
    bad_decision = dataclasses.replace(items["authorization_decision"], authorized_artifact=bad_artifact)
    assert create_cost_authorization_decision_integrity(
        items["presentation"], items["authorization_request"], bad_decision) is None
    other = chain(suffix="2")
    assert create_cost_authorization_decision_integrity(
        items["presentation"], other["authorization_request"], other["authorization_decision"]) is None


def test_denied_authorization_and_denied_adapter_are_bound_without_artifacts():
    items = chain()
    denied_request = dataclasses.replace(items["authorization_request"], authorization_scope="OTHER")
    denied_decision = authorize_cost_response(denied_request)
    denied_auth = create_cost_authorization_decision_integrity(
        items["presentation"], denied_request, denied_decision)
    assert denied_auth is not None and denied_decision.authorized_artifact is None
    adapter_request = CostResponseAdapterRequest("denied-adapter", denied_decision)
    adapter_result = adapt_authorized_cost_response(adapter_request)
    denied_adapter = create_cost_adapter_result_integrity(
        denied_auth, adapter_request, adapter_result)
    assert denied_adapter is not None and adapter_result.payload is None
    assert verify_cost_authorization_decision_integrity(denied_auth)
    assert verify_cost_adapter_result_integrity(denied_adapter)


def test_denied_decision_with_artifact_or_authority_escalation_rejected():
    items = chain()
    denied_request = dataclasses.replace(items["authorization_request"], authorization_scope="OTHER")
    denied = authorize_cost_response(denied_request)
    assert create_cost_authorization_decision_integrity(
        items["presentation"], denied_request,
        dataclasses.replace(denied, authorized_artifact=items["authorization_decision"].authorized_artifact)) is None
    assert create_cost_authorization_decision_integrity(
        items["presentation"], items["authorization_request"],
        dataclasses.replace(items["authorization_decision"], response_committed=True)) is None


def test_adapter_payload_content_identity_and_digest_substitution_rejected():
    items, other = chain(), chain(suffix="2")
    assert create_cost_adapter_result_integrity(
        items["authorization"], other["adapter_request"], other["adapter_result"]) is None
    payload = items["adapter_result"].payload
    for changed in (
        dataclasses.replace(payload, text=payload.text + "x"),
        dataclasses.replace(payload, source_request_id="r2"),
        dataclasses.replace(payload, payload_digest="0" * 64),
    ):
        result = dataclasses.replace(items["adapter_result"], payload=changed)
        assert create_cost_adapter_result_integrity(
            items["authorization"], items["adapter_request"], result) is None


def test_delivery_payload_binding_reference_time_and_qualification_substitution():
    items, other = chain(), chain(suffix="2")
    assert items["delivery"].qualification_binding_digest == items["qualification"].binding.qualification_digest
    assert items["delivery"].payload_digest == items["adapter_result"].payload.payload_digest
    assert create_cost_delivery_provenance_integrity(
        items["adapter"], items["case"], other["qualification"]) is None
    bad_binding = dataclasses.replace(items["qualification"].binding,
                                      reference_time="2026-07-14T13:00:00+07:00")
    bad_result = dataclasses.replace(items["qualification"], binding=bad_binding)
    assert create_cost_delivery_provenance_integrity(
        items["adapter"], items["case"], bad_result) is None


@pytest.mark.parametrize("name", ("presentation", "authorization", "adapter", "delivery"))
def test_sidecar_digest_format_tamper_and_all_authority_flags(name):
    artifact = chain()[name]
    for digest in ("0" * 63, "0" * 65, "A" * 64, "g" * 64, "1" * 64):
        changed = dataclasses.replace(artifact, integrity_digest=digest)
        verifier = globals()["verify_cost_" + ({
            "presentation": "presentation_result", "authorization": "authorization_decision",
            "adapter": "adapter_result", "delivery": "delivery_provenance",
        }[name]) + "_integrity"]
        assert not verifier(changed)
    assert artifact.structural_integrity_verified is True
    assert artifact.isolated_observation is True
    assert all(getattr(artifact, field.name) is False
               for field in dataclasses.fields(artifact)
               if field.name.endswith("_authority") or field.name in ("production_permitted", "delivered", "committed"))


def test_frozen_deepcopy_safe_and_inputs_not_mutated():
    items = chain()
    before = (items["presentation_request"], items["presentation_result"],
              items["authorization_request"], items["authorization_decision"],
              items["adapter_request"], items["adapter_result"], items["case"], items["qualification"])
    for cls in (CostPresentationResultIntegrity, CostAuthorizationDecisionIntegrity,
                CostAdapterResultIntegrity, CostDeliveryProvenanceIntegrity):
        assert cls.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        items["delivery"].integrity_digest = "0" * 64
    assert copy.deepcopy(items["delivery"]) == items["delivery"]
    assert before == (items["presentation_request"], items["presentation_result"],
                      items["authorization_request"], items["authorization_decision"],
                      items["adapter_request"], items["adapter_result"], items["case"], items["qualification"])


def test_constructors_and_verifiers_do_not_rerun_transformations(monkeypatch):
    items = chain()
    import brain.business_skill_cost_execution as execution
    import brain.business_skill_cost_result_presenter as presentation
    import brain.business_skill_cost_response_authorization as authorization
    import brain.business_skill_cost_response_adapter as adapter
    import brain.business_skill_cost_response_delivery_qualification as delivery
    fail = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("transformation rerun"))
    monkeypatch.setattr(execution, "execute_cost_skill", fail)
    monkeypatch.setattr(presentation, "present_cost_result", fail)
    monkeypatch.setattr(authorization, "authorize_cost_response", fail)
    monkeypatch.setattr(adapter, "adapt_authorized_cost_response", fail)
    monkeypatch.setattr(delivery, "qualify_cost_response_delivery", fail)
    assert create_cost_presentation_result_integrity(
        items["execution"], items["presentation_request"], items["presentation_result"]) == items["presentation"]
    assert verify_cost_authorization_decision_integrity(items["authorization"])
    assert verify_cost_adapter_result_integrity(items["adapter"])
    assert verify_cost_delivery_provenance_integrity(items["delivery"])


def test_source_audit_no_runtime_wiring_or_forbidden_calls():
    path = Path(__file__).parents[1] / "brain" / "cost_rendered_delivery_provenance_integrity.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    forbidden = {"execute_cost_skill", "present_cost_result", "authorize_cost_response",
                 "adapt_authorized_cost_response", "qualify_cost_response_delivery",
                 "execute_cost_runtime_bridge", "admit_cost_runtime", "float"}
    assert not (calls & forbidden)
    assert all(token not in source for token in (
        "import app", "production_response_candidate", "response_commit_boundary",
        "streamlit", "requests", "socket", "subprocess"))
