"""V5.15.18 controlled cost response adapter boundary tests."""

import dataclasses
from pathlib import Path

import pytest

from brain.business_skill_cost_execution import CostExecutionRequest, execute_cost_skill
from brain.business_skill_cost_result_presenter import INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION, SUPPORTED_LOCALE, CostPresentationRequest, present_cost_result
from brain.business_skill_limited_activation_gateway import LIMITED_ACTIVATION_GATEWAY_VERSION, SUPPORTED_ACTIVATION_SCOPE, LimitedActivationRequest, decide_limited_activation
from brain.business_skill_cost_response_authorization import AUTHORIZATION_POLICY_VERSION, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE, CostResponseAuthorizationRequest, authorize_cost_response
from brain.business_skill_cost_response_adapter import *

NOW = "2026-07-12T12:00:00+07:00"


def _decision(skill="cost.change_analysis.v1", values=None, aid="a1", pid="p1", eid="e1", rid="r1"):
    values = values or ({"previous_cost": 20, "current_cost": 24} if "change" in skill else {"total_cost": 1000, "unit_quantity": 3})
    evidence = {k: {"value": v, "confidence": 1.0, "source": "current_turn", "freshness": "current", "user_confirmed": True} for k, v in values.items()}
    text = "cost changed" if "change" in skill else "cost per unit"
    gateway = decide_limited_activation(LimitedActivationRequest(rid, text, evidence, NOW, skill, SUPPORTED_ACTIVATION_SCOPE, LIMITED_ACTIVATION_GATEWAY_VERSION))
    execution = execute_cost_skill(CostExecutionRequest(eid, rid, skill, gateway))
    presentation = present_cost_result(CostPresentationRequest(pid, eid, rid, skill, execution, SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION))
    return authorize_cost_response(CostResponseAuthorizationRequest(aid, pid, eid, rid, skill, presentation, LIMITED_COST_RESPONSE, USER_TEXT_RESPONSE, AUTHORIZATION_POLICY_VERSION))


def _request(**kwargs):
    return CostResponseAdapterRequest(kwargs.pop("adapter_request_id", "adapter1"), kwargs.pop("authorization_decision", _decision()), **kwargs)


@pytest.mark.parametrize("values", ({"previous_cost": 20, "current_cost": 24}, {"previous_cost": 20, "current_cost": 12}, {"previous_cost": 20, "current_cost": 20}, {"previous_cost": 0, "current_cost": 20}))
def test_positive_change_outputs_are_exact_deterministic_and_prepared_only(values):
    decision = _decision(values=values)
    first = adapt_authorized_cost_response(_request(authorization_decision=decision))
    second = adapt_authorized_cost_response(_request(authorization_decision=decision))
    assert first == second and first.outcome == RESPONSE_PAYLOAD_PREPARED
    assert first.payload.text.encode("utf-8") == decision.authorized_artifact.authorized_text.encode("utf-8")
    assert first.payload.scope == decision.authorized_artifact.authorization_scope
    assert verify_prepared_cost_response_payload_integrity(first.payload)
    assert verify_cost_response_adapter_result_integrity(first)


@pytest.mark.parametrize("values", ({"total_cost": 1000, "unit_quantity": 4}, {"total_cost": 1000, "unit_quantity": 3}))
def test_positive_per_unit_exact_and_rounded(values):
    decision = _decision("cost.per_unit_calculation.v1", values)
    result = adapt_authorized_cost_response(_request(authorization_decision=decision))
    assert result.payload.text == decision.authorized_artifact.authorized_text
    assert result.payload.source_skill_id == "cost.per_unit_calculation.v1"


@pytest.mark.parametrize("field,value", (
    ("text", "tamper"), ("source_authorization_id", "other"), ("source_presentation_id", "other"),
    ("source_execution_id", "other"), ("source_request_id", "other"), ("source_skill_id", "other"),
    ("presentation_digest", "0" * 64), ("draft_digest", "0" * 64), ("locale", "en-US"),
    ("target_channel", "RUNTIME"), ("scope", "GLOBAL"), ("output_mode", "COMMITTED"),
    ("response_committed", True), ("response_generated", True), ("runtime_routed", True),
    ("payload_prepared", False), ("authorization_performed", True),
))
def test_payload_tamper_fails_closed(field, value):
    payload = adapt_authorized_cost_response(_request()).payload
    assert not verify_prepared_cost_response_payload_integrity(dataclasses.replace(payload, **{field: value}))


def test_digest_changes_with_material_and_is_lowercase_sha256():
    payload = adapt_authorized_cost_response(_request()).payload
    assert len(payload.payload_digest) == 64 and payload.payload_digest == payload.payload_digest.lower()
    changed = dataclasses.replace(payload, text=payload.text + "x")
    assert changed.payload_digest == payload.payload_digest and not verify_prepared_cost_response_payload_integrity(changed)


@pytest.mark.parametrize("text,reason", (("", "EMPTY_AUTHORIZED_TEXT"), ("   ", "EMPTY_AUTHORIZED_TEXT"), ("x" * (MAX_RESPONSE_LENGTH + 1), "AUTHORIZED_TEXT_TOO_LONG"), ("bad\x00text", "CONTROL_CHARACTER_NOT_ALLOWED")))
def test_content_boundary_does_not_rewrite(text, reason):
    decision = _decision()
    artifact = dataclasses.replace(decision.authorized_artifact, authorized_text=text)
    result = adapt_authorized_cost_response(_request(authorization_decision=dataclasses.replace(decision, authorized_artifact=artifact)))
    assert result.payload is None and reason in result.reason_codes


def test_malformed_denied_missing_artifact_and_wrong_authorization_version():
    valid = _decision()
    cases = (None, dataclasses.replace(valid, outcome="RESPONSE_DELIVERY_DENIED", response_delivery_eligible=False), dataclasses.replace(valid, authorized_artifact=None), dataclasses.replace(valid, authorized_artifact=dataclasses.replace(valid.authorized_artifact, authorization_policy_version="5.15.17")))
    for source in cases:
        result = adapt_authorized_cost_response(_request(authorization_decision=source))
        assert result.payload is None and result.outcome != RESPONSE_PAYLOAD_PREPARED and verify_cost_response_adapter_result_integrity(result)


def test_identity_scope_channel_output_and_authority_injection_fail():
    valid = _decision()
    forged_scope = dataclasses.replace(valid, authorized_artifact=dataclasses.replace(valid.authorized_artifact, authorization_scope="GLOBAL"))
    wrong_identity = dataclasses.replace(valid, authorization_id="other")
    for request in (_request(authorization_decision=forged_scope), _request(authorization_decision=wrong_identity), _request(target_channel="RUNTIME"), _request(output_mode="COMMITTED"), _request(response_committed=True), _request(tools_invoked=True)):
        result = adapt_authorized_cost_response(request)
        assert result.payload is None and not result.payload_prepared


def test_batch_preserves_order_rejects_duplicates_and_inputs_are_not_mutated():
    one = _request(adapter_request_id="one")
    two = _request(adapter_request_id="two", authorization_decision=_decision(aid="a2", pid="p2", eid="e2", rid="r2"))
    before = (one, two)
    batch = adapt_authorized_cost_responses(before)
    assert [x.adapter_request_id for x in batch.results] == ["one", "two"] and before == (one, two)
    duplicate = adapt_authorized_cost_responses((one, dataclasses.replace(two, adapter_request_id="one")))
    assert all(x.outcome == RESPONSE_PAYLOAD_INVALID and x.payload is None for x in duplicate.results)


def test_all_contracts_are_frozen_and_gate_order_is_exact():
    result = adapt_authorized_cost_response(_request())
    objects = (CostResponseAdapterPolicy(), _request(), result.gate_results[0], result.payload, result, CostResponseAdapterBatch(COST_RESPONSE_ADAPTER_VERSION, (result,)), CostResponseAdapterDenial(("x",), "REQUEST_VALIDITY"))
    for obj in objects:
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            obj.adapter_request_id = "changed"
    assert tuple(x.gate for x in result.gate_results) == GATE_ORDER


def test_module_has_no_forbidden_runtime_or_upstream_boundary_dependencies():
    source = (Path(__file__).parents[1] / "brain" / "business_skill_cost_response_adapter.py").read_text(encoding="utf-8")
    forbidden = ("import app", "import runtime", "import router", "import planner", "import workflow", "import legacy", "limited_activation_gateway", "cost_execution", "cost_result_presenter", "authorize_cost_response(", "decide_limited_activation(", "execute_cost_skill(", "present_cost_result(")
    assert all(token not in source for token in forbidden)


def test_registry_and_lifecycle_are_intentionally_not_reconstructed_from_other_sources():
    payload = adapt_authorized_cost_response(_request()).payload
    assert not hasattr(payload, "registry_version") and not hasattr(payload, "lifecycle")
