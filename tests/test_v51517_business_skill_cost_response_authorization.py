"""V5.15.17/V5.15.17.1 cost response authorization boundary tests.

Digest verification cannot detect identical valid replay. SHA-256 is not a
signature, MAC, authentication, or protection from wholesale reconstruction
outside the trusted internal artifact boundary.
"""

import dataclasses

import pytest

from brain.business_skill_cost_execution import CostExecutionRequest, execute_cost_skill
from brain.business_skill_cost_result_presenter import (
    INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION, SUPPORTED_LOCALE,
    CostPresentationRequest, present_cost_result,
    verify_cost_presentation_result_integrity, verify_cost_response_draft_integrity,
)
from brain.business_skill_limited_activation_gateway import (
    LIMITED_ACTIVATION_GATEWAY_VERSION, SUPPORTED_ACTIVATION_SCOPE,
    LimitedActivationRequest, decide_limited_activation,
)
from brain.business_skill_cost_response_authorization import *

NOW = "2026-07-12T12:00:00+07:00"


def _presentation(skill="cost.change_analysis.v1", values=None, pid="p1", eid="e1", rid="r1"):
    values = values or ({"previous_cost": 20, "current_cost": 24} if "change" in skill else
                        {"total_cost": 1000, "unit_quantity": 3})
    evidence = {k: {"value": v, "confidence": 1.0, "source": "current_turn",
        "freshness": "current", "user_confirmed": True} for k, v in values.items()}
    text = "cost changed" if "change" in skill else "cost per unit"
    gateway = decide_limited_activation(LimitedActivationRequest(
        rid, text, evidence, NOW, skill, SUPPORTED_ACTIVATION_SCOPE, LIMITED_ACTIVATION_GATEWAY_VERSION))
    execution = execute_cost_skill(CostExecutionRequest(eid, rid, skill, gateway))
    return present_cost_result(CostPresentationRequest(
        pid, eid, rid, skill, execution, SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION))


def _request(source=None, aid="a1", pid="p1", eid="e1", rid="r1", skill="cost.change_analysis.v1",
             scope=LIMITED_COST_RESPONSE, channel=USER_TEXT_RESPONSE, version=AUTHORIZATION_POLICY_VERSION):
    source = _presentation(skill, pid=pid, eid=eid, rid=rid) if source is None else source
    return CostResponseAuthorizationRequest(aid, pid, eid, rid, skill, source, scope, channel, version)


@pytest.mark.parametrize("values", (
    {"previous_cost": 20, "current_cost": 24}, {"previous_cost": 20, "current_cost": 12},
    {"previous_cost": 20, "current_cost": 20}, {"previous_cost": 0, "current_cost": 20},
))
def test_change_artifacts_are_exact_bound_deterministic_and_authority_limited(values):
    source = _presentation(values=values)
    first = authorize_cost_response(_request(source))
    second = authorize_cost_response(_request(source))
    assert first == second and first.outcome == RESPONSE_DELIVERY_ELIGIBLE
    assert verify_cost_response_draft_integrity(source.draft)
    assert verify_cost_presentation_result_integrity(source)
    artifact = first.authorized_artifact
    assert artifact.authorization_scope == LIMITED_COST_RESPONSE
    assert artifact.authorization_policy_version == COST_RESPONSE_AUTHORIZATION_VERSION
    assert artifact.authorized_text.encode() == source.draft.draft_text.encode()
    assert (artifact.presentation_integrity_digest, artifact.draft_integrity_digest) == (
        source.presentation_digest, source.draft.draft_digest)
    assert first.response_delivery_eligible and first.source_presentation_generated
    assert first.source_executed and first.source_calculated
    for name in ("response_generated", "response_committed", "runtime_routed", "tools_invoked", "persisted",
                 "follow_up_generated", "business_reasoning_generated", "execution_performed", "calculation_performed"):
        assert not getattr(first, name)


@pytest.mark.parametrize("values", ({"total_cost": 1000, "unit_quantity": 4},
                                     {"total_cost": 1000, "unit_quantity": 3}))
def test_per_unit_exact_and_rounded_are_eligible(values):
    source = _presentation("cost.per_unit_calculation.v1", values)
    decision = authorize_cost_response(_request(source, skill="cost.per_unit_calculation.v1"))
    assert decision.outcome == RESPONSE_DELIVERY_ELIGIBLE
    assert decision.authorized_artifact.authorized_text == source.draft.draft_text


@pytest.mark.parametrize("field,value", (
    ("authorization_id", ""), ("authorization_id", " bad"), ("presentation_id", "other"),
    ("execution_id", "other"), ("request_id", "other"),
    ("requested_skill_id", "cost.per_unit_calculation.v1"),
    ("authorization_scope", "WIDE"), ("target_channel", "RUNTIME"), ("policy_version", "5.15.16"),
))
def test_request_identity_scope_channel_and_version_fail_closed(field, value):
    decision = authorize_cost_response(dataclasses.replace(_request(), **{field: value}))
    assert decision.outcome != RESPONSE_DELIVERY_ELIGIBLE
    assert decision.authorized_artifact is None and not decision.response_delivery_eligible


@pytest.mark.parametrize("field,value", (
    ("draft_text", ""), ("draft_text", "x" * (MAXIMUM_DRAFT_LENGTH + 1)),
    ("draft_text", "bad\x00text"), ("locale", "en-US"), ("template_id", "EVIL"),
    ("source_request_id", "other"), ("draft_digest", "0" * 64),
    ("runtime_routed", True), ("response_generated", True),
))
def test_draft_tamper_substitution_content_and_authority_leakage_fail(field, value):
    source = _presentation()
    changed = dataclasses.replace(source.draft, **{field: value})
    decision = authorize_cost_response(_request(dataclasses.replace(source, draft=changed)))
    assert decision.outcome != RESPONSE_DELIVERY_ELIGIBLE and decision.authorized_artifact is None
    assert all(not getattr(decision, x) for x in ("response_delivery_eligible", "source_executed", "source_calculated"))


def test_missing_denied_invalid_result_and_result_substitution_or_digest_tamper_fail():
    valid = _presentation()
    denied = _presentation(pid="p2")
    cases = (None, dataclasses.replace(valid, outcome="PRESENTATION_DENIED"),
             dataclasses.replace(valid, presentation_digest="0" * 64),
             dataclasses.replace(valid, draft=denied.draft))
    for source in cases:
        request = _request(valid)
        request = dataclasses.replace(request, presentation_result=source)
        assert authorize_cost_response(request).authorized_artifact is None


def test_policy_is_exact_frozen_and_cannot_be_weakened_or_injected():
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        CostResponseAuthorizationPolicy().maximum_draft_length = 9999
    for kwargs in ({"deny_by_default": False}, {"maximum_draft_length": 9999}, {"locale": "en-US"}):
        with pytest.raises(ValueError): CostResponseAuthorizationPolicy(**kwargs)
    with pytest.raises(TypeError):
        CostResponseAuthorizationRequest("a", "p", "e", "r", "s", None, LIMITED_COST_RESPONSE,
                                         USER_TEXT_RESPONSE, AUTHORIZATION_POLICY_VERSION, response_text="evil")
    with pytest.raises(TypeError):
        CostResponseAuthorizationRequest("a", "p", "e", "r", "s", None, LIMITED_COST_RESPONSE,
                                         USER_TEXT_RESPONSE, AUTHORIZATION_POLICY_VERSION, template="evil")


def test_artifact_and_all_contracts_are_frozen():
    decision = authorize_cost_response(_request())
    for obj in (CostResponseAuthorizationPolicy(), _request(), decision.gate_results[0], decision,
                CostResponseAuthorizationBatch(AUTHORIZATION_POLICY_VERSION, (decision,)),
                decision.authorized_artifact):
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            obj.authorization_id = "mutated"


def test_duplicate_conflicting_ids_cross_request_isolation_and_stable_batch():
    one = _request(_presentation(pid="p1", rid="r1"), aid="dup", pid="p1", rid="r1")
    two = _request(_presentation(pid="p2", rid="r2"), aid="dup", pid="p2", rid="r2")
    first = authorize_cost_responses((one, two))
    second = authorize_cost_responses((one, two))
    assert first == second
    assert all(x.outcome == RESPONSE_DELIVERY_INVALID and x.authorized_artifact is None for x in first.decisions)
    isolated = authorize_cost_responses((dataclasses.replace(one, authorization_id="a1"),
                                         dataclasses.replace(two, authorization_id="a2")))
    assert [x.authorized_artifact.source_request_id for x in isolated.decisions] == ["r1", "r2"]


def test_gate_order_and_replay_trust_limitation_are_explicit():
    request = _request()
    first = authorize_cost_response(request)
    replay = authorize_cost_response(request)
    assert tuple(x.gate for x in first.gate_results) == GATE_ORDER
    assert first == replay and replay.response_delivery_eligible  # no consumed-ID/nonce state
