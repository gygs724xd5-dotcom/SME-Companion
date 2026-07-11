"""V5.15.16.1 deterministic integrity binding tests.

Identical valid artifact replay is intentionally not detectable by a digest alone.
These SHA-256 bindings are not a signature, MAC, or caller authentication and do
not protect against an untrusted caller rebuilding an object and both digests.
"""

import dataclasses
import re

import pytest

from brain.business_skill_cost_execution import CostExecutionRequest, execute_cost_skill
from brain.business_skill_cost_result_presenter import *
from brain.business_skill_limited_activation_gateway import (
    LIMITED_ACTIVATION_GATEWAY_VERSION, SUPPORTED_ACTIVATION_SCOPE,
    LimitedActivationRequest, decide_limited_activation,
)

NOW = "2026-07-11T12:00:00+07:00"


def _present(pid="p1", eid="e1", rid="r1", skill="cost.change_analysis.v1"):
    values = ({"previous_cost": 20, "current_cost": 24} if "change" in skill
              else {"total_cost": 1000, "unit_quantity": 100})
    evidence = {key: {"value": value, "confidence": 1.0, "source": "current_turn",
        "freshness": "current", "user_confirmed": True} for key, value in values.items()}
    decision = decide_limited_activation(LimitedActivationRequest(
        rid, "cost changed" if "change" in skill else "cost per unit", evidence, NOW,
        skill, SUPPORTED_ACTIVATION_SCOPE, LIMITED_ACTIVATION_GATEWAY_VERSION))
    executed = execute_cost_skill(CostExecutionRequest(eid, rid, skill, decision))
    return present_cost_result(CostPresentationRequest(
        pid, eid, rid, skill, executed, SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION))


@pytest.mark.parametrize("skill", ("cost.change_analysis.v1", "cost.per_unit_calculation.v1"))
def test_positive_integrity_identity_determinism_and_digest_syntax(skill):
    first, second = _present(skill=skill), _present(skill=skill)
    assert first == second
    assert verify_cost_response_draft_integrity(first.draft)
    assert verify_cost_presentation_result_integrity(first)
    assert (first.draft.source_presentation_id, first.draft.source_execution_id,
            first.draft.source_request_id, first.draft.source_skill_id) == ("p1", "e1", "r1", skill)
    assert first.draft.draft_binding_schema_version == DRAFT_BINDING_SCHEMA_VERSION == 1
    assert first.presentation_binding_schema_version == PRESENTATION_BINDING_SCHEMA_VERSION == 1
    assert re.fullmatch(r"[0-9a-f]{64}", first.draft.draft_digest)
    assert re.fullmatch(r"[0-9a-f]{64}", first.presentation_digest)


@pytest.mark.parametrize("field,value", (
    ("source_presentation_id", "p2"), ("source_execution_id", "e2"),
    ("source_request_id", "r2"), ("source_skill_id", "cost.per_unit_calculation.v1"),
    ("template_id", "EVIL"), ("locale", "en-US"), ("draft_text", "evil"),
    ("content_version", "5.15.16"), ("internal_draft_only", False),
    ("presentation_generated", False), ("source_executed", False), ("source_calculated", False),
    ("business_reasoning_generated", True), ("runtime_routed", True), ("tools_invoked", True),
    ("persisted", True), ("follow_up_generated", True), ("response_generated", True),
    ("response_committed", True), ("draft_binding_schema_version", 2),
    ("draft_digest", "0" * 64), ("draft_digest", "a"), ("draft_digest", "G" * 64),
    ("draft_digest", "A" * 64),
))
def test_each_draft_identity_content_authority_and_digest_tamper_fails(field, value):
    draft = _present().draft
    assert not verify_cost_response_draft_integrity(dataclasses.replace(draft, **{field: value}))


def test_each_field_component_and_order_tamper_fails():
    draft = _present().draft
    first = draft.fields[0]
    variants = (
        dataclasses.replace(first, name="evil"), dataclasses.replace(first, label="evil"),
        dataclasses.replace(first, display_value="999"), dataclasses.replace(first, unit="evil"),
    )
    for changed in variants:
        assert not verify_cost_response_draft_integrity(dataclasses.replace(draft, fields=(changed,) + draft.fields[1:]))
    assert not verify_cost_response_draft_integrity(dataclasses.replace(draft, fields=tuple(reversed(draft.fields))))
    assert not verify_cost_response_draft_integrity(dataclasses.replace(draft, fields=draft.fields + (draft.fields[0],)))


@pytest.mark.parametrize("field,value", (
    ("presentation_id", "p2"), ("outcome", PRESENTATION_DENIED),
    ("reason_codes", ("evil",)), ("presentation_generated", False),
    ("internal_draft_only", False), ("source_executed", False), ("source_calculated", False),
    ("business_reasoning_generated", True), ("runtime_routed", True), ("tools_invoked", True),
    ("persisted", True), ("follow_up_generated", True), ("response_generated", True),
    ("response_committed", True), ("presentation_binding_schema_version", 2),
    ("presentation_digest", "0" * 64), ("presentation_digest", "a"),
    ("presentation_digest", "G" * 64), ("presentation_digest", "A" * 64),
))
def test_each_result_identity_outcome_authority_and_digest_tamper_fails(field, value):
    result = _present()
    assert not verify_cost_presentation_result_integrity(dataclasses.replace(result, **{field: value}))


def test_gate_status_order_reason_denial_and_incomplete_binding_fail():
    result = _present()
    gate = result.gate_results[0]
    changes = (
        (dataclasses.replace(gate, passed=False),) + result.gate_results[1:],
        (dataclasses.replace(gate, reason_codes=("EVIL",)),) + result.gate_results[1:],
        tuple(reversed(result.gate_results)),
    )
    for gates in changes:
        assert not verify_cost_presentation_result_integrity(dataclasses.replace(result, gate_results=gates))
    denied = present_cost_result(CostPresentationRequest(
        "p1", "e1", "r1", "cost.change_analysis.v1", None,
        SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION))
    assert denied.outcome == PRESENTATION_DENIED and denied.draft is None
    assert verify_cost_presentation_result_integrity(denied)
    assert not verify_cost_presentation_result_integrity(dataclasses.replace(denied, denial=None))
    assert not verify_cost_presentation_result_integrity(dataclasses.replace(denied, draft=result.draft))


def test_draft_and_result_substitution_fail_but_identical_replay_limitation_is_explicit():
    first, other = _present(pid="p1"), _present(pid="p2")
    assert not verify_cost_presentation_result_integrity(dataclasses.replace(first, draft=other.draft))
    assert not verify_cost_presentation_result_integrity(dataclasses.replace(first, presentation_id="p2"))
    replay = first
    assert verify_cost_presentation_result_integrity(replay)  # digest alone cannot detect valid replay


def test_exact_type_and_no_caller_binding_injection():
    result = _present()
    assert not verify_cost_response_draft_integrity(None)
    assert not verify_cost_presentation_result_integrity(None)
    with pytest.raises(TypeError):
        CostPresentationRequest("p", "e", "r", "cost.change_analysis.v1", None,
            SUPPORTED_LOCALE, INTERNAL_DRAFT_ONLY, PRESENTATION_VERSION, draft_digest="evil")
    assert result.draft.draft_text == _present().draft.draft_text
