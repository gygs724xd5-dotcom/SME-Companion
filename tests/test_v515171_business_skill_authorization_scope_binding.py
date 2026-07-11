"""V5.15.17.1 authorization artifact scope-binding hotfix tests."""

import dataclasses

import pytest

from brain.business_skill_cost_response_authorization import (
    AUTHORIZATION_POLICY_VERSION,
    COST_RESPONSE_AUTHORIZATION_VERSION,
    HISTORICAL_COST_RESPONSE_AUTHORIZATION_VERSION,
    LIMITED_COST_RESPONSE,
    RESPONSE_DELIVERY_ELIGIBLE,
    USER_TEXT_RESPONSE,
    CostResponseAuthorizationBatch,
    CostResponseAuthorizationPolicy,
    authorize_cost_response,
    authorize_cost_responses,
)
from tests.test_v51517_business_skill_cost_response_authorization import _request


def test_versions_and_positive_artifact_scope_are_canonical():
    assert HISTORICAL_COST_RESPONSE_AUTHORIZATION_VERSION == "5.15.17"
    assert COST_RESPONSE_AUTHORIZATION_VERSION == "5.15.17.1"
    assert AUTHORIZATION_POLICY_VERSION == COST_RESPONSE_AUTHORIZATION_VERSION
    decision = authorize_cost_response(_request())
    assert decision.outcome == RESPONSE_DELIVERY_ELIGIBLE
    assert decision.response_delivery_eligible
    assert decision.authorized_artifact.authorization_scope == LIMITED_COST_RESPONSE
    assert decision.authorized_artifact.authorization_policy_version == COST_RESPONSE_AUTHORIZATION_VERSION


@pytest.mark.parametrize("scope", (None, "", "   ", "GLOBAL", "*", "LIMITED_COST_RESPONSE:*"))
def test_missing_empty_whitespace_wrong_wildcard_and_global_scope_fail_closed(scope):
    decision = authorize_cost_response(dataclasses.replace(_request(), authorization_scope=scope))
    assert decision.outcome != RESPONSE_DELIVERY_ELIGIBLE
    assert decision.authorized_artifact is None
    assert not decision.response_delivery_eligible
    assert "UNSUPPORTED_AUTHORIZATION_SCOPE" in decision.reason_codes


def test_request_policy_scope_or_version_cannot_be_substituted():
    with pytest.raises(ValueError):
        CostResponseAuthorizationPolicy(authorization_scope="GLOBAL")
    old_version = dataclasses.replace(
        _request(), policy_version=HISTORICAL_COST_RESPONSE_AUTHORIZATION_VERSION
    )
    decision = authorize_cost_response(old_version)
    assert decision.authorized_artifact is None
    assert "POLICY_VERSION_MISMATCH" in decision.reason_codes


def test_artifact_scope_is_frozen_and_replace_creates_only_an_untrusted_copy():
    decision = authorize_cost_response(_request())
    artifact = decision.authorized_artifact
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        artifact.authorization_scope = "GLOBAL"
    forged = dataclasses.replace(artifact, authorization_scope="GLOBAL")
    assert forged.authorization_scope == "GLOBAL"
    assert decision.authorized_artifact.authorization_scope == LIMITED_COST_RESPONSE
    assert forged != decision.authorized_artifact


def test_denied_and_invalid_decisions_never_expose_a_scoped_artifact():
    denied = authorize_cost_response(dataclasses.replace(_request(), authorization_scope="GLOBAL"))
    invalid = authorize_cost_response(dataclasses.replace(_request(), authorization_id=""))
    for decision in (denied, invalid):
        assert decision.authorized_artifact is None
        assert not decision.response_delivery_eligible


def test_batch_scope_binding_order_duplicates_determinism_and_authority_flags():
    one = dataclasses.replace(_request(), authorization_id="dup")
    two = dataclasses.replace(_request(), authorization_id="dup")
    assert authorize_cost_responses((one, two)) == authorize_cost_responses((one, two))
    batch = authorize_cost_responses((dataclasses.replace(one, authorization_id="a1"),
                                      dataclasses.replace(two, authorization_id="a2")))
    assert isinstance(batch, CostResponseAuthorizationBatch)
    assert [d.authorization_id for d in batch.decisions] == ["a1", "a2"]
    assert all(d.authorized_artifact.authorization_scope == LIMITED_COST_RESPONSE for d in batch.decisions)
    for decision in batch.decisions:
        for flag in ("response_generated", "response_committed", "runtime_routed", "persisted",
                     "tools_invoked", "follow_up_generated", "business_reasoning_generated",
                     "execution_performed", "calculation_performed"):
            assert not getattr(decision, flag)
        assert decision.response_delivery_eligible
        assert decision.authorized_artifact.target_channel == USER_TEXT_RESPONSE
