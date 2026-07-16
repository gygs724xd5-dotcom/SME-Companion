from __future__ import annotations

import ast
from dataclasses import fields, replace
from datetime import datetime, timezone
import inspect
from functools import lru_cache
from pathlib import Path

import pytest

import brain.versioned_cost_runtime_request_adapter as owner
from brain.business_skill_cost_execution import CostExecutionRequest
from brain.isolated_executable_request_qualification import create_isolated_executable_request_qualification_report
from brain.isolated_gate_enabled_pre_authorization_qualification import create_isolated_gate_enabled_pre_authorization_report
from brain.isolated_qualification_configuration_binding import (
    create_isolated_qualification_feature_gate_binding,
    create_isolated_qualification_limited_activation_binding,
    create_isolated_qualification_pre_execution_result,
    create_isolated_qualification_skill_evidence_envelope,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, PURE_TEST_TRUSTED_SOURCE_IDENTITY,
    create_production_feature_gate_configuration, evaluate_production_feature_gate,
)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "brain" / "versioned_cost_runtime_request_adapter.py"


def _foundation(message, ordinal):
    context = create_production_turn_context("runtime-adapter-foundation", ordinal, message)
    reference = create_production_turn_reference_time(context, datetime(2026, 7, 16, tzinfo=timezone.utc))
    config = create_production_feature_gate_configuration(
        PURE_TEST_TRUSTED_SOURCE_IDENTITY, ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),))
    evaluation = evaluate_production_feature_gate(config, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    binding = create_isolated_qualification_feature_gate_binding(context, reference, config, evaluation)
    evidence = create_isolated_qualification_skill_evidence_envelope(binding)
    limited = create_isolated_qualification_limited_activation_binding(evidence)
    foundation = create_isolated_qualification_pre_execution_result(limited)
    return foundation, create_isolated_gate_enabled_pre_authorization_report(foundation)


@lru_cache(maxsize=2)
def _report(waste=True):
    unit = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น"
    if waste: unit += " ของเสีย 2 ชิ้น"
    return create_isolated_executable_request_qualification_report((
        _foundation("cost changed from 100 to 120 baht", 1), _foundation(unit, 2)))


@lru_cache(maxsize=2)
def _bindings(waste=True):
    return owner.create_versioned_cost_runtime_request_bindings(_report(waste).observations)


def test_both_skill_bindings_are_exact_frozen_and_deterministic():
    one, two = _bindings(), _bindings()
    assert one == two and owner.verify_versioned_cost_runtime_request_bindings(one)
    assert tuple(x.source_skill_id for x in one) == owner.SUPPORTED_ADAPTER_SKILL_IDS
    for item in one:
        assert owner.verify_versioned_cost_runtime_request_binding(item)
        assert type(item.target_request) is CostExecutionRequest
        assert item.target_request.requested_skill_id == item.source_request.skill_id
    for contract in (owner.VersionedCostRuntimeAdapterAuthorityBoundary,
                     owner.VersionedCostRuntimeFieldProvenance,
                     owner.VersionedCostRuntimeRequestBinding):
        assert contract.__dataclass_params__.frozen


def test_exact_field_provenance_and_target_identity():
    for item in _bindings():
        source, target = item.source_request, item.target_request
        decision = item.source_observation.foundation.limited_activation_binding.canonical_limited_activation_material.limited_activation_decision
        assert target == CostExecutionRequest("foundation-" + source.pre_execution_result_digest[:32],
                                              decision.request_id, source.skill_id, decision, ())
        assert tuple(x.target_field for x in item.field_provenance) == tuple(
            x.split("<-", 1)[0] for x in owner.FIELD_PROVENANCE_TOPOLOGY)
        assert item.field_provenance_topology == owner.FIELD_PROVENANCE_TOPOLOGY


def test_source_turn_reference_gate_evidence_formula_policy_and_operands_are_bound():
    for item in _bindings():
        source = item.source_request
        assert (item.source_turn_digest, item.source_reference_time_digest) == (source.turn_digest, source.reference_time_digest)
        assert (item.source_gate_id, item.source_configuration_digest, item.source_evaluation_digest) == (
            source.gate_id, source.configuration_digest, source.evaluation_digest)
        assert item.source_evidence_envelope_digest == source.evidence_envelope_digest
        assert item.source_operand_digests == tuple(x.operand_digest for x in source.operands)
        assert (item.source_formula_digest, item.source_policy_digest) == (source.formula.formula_digest, source.policy.policy_digest)


def test_authority_and_invocation_boundary_is_all_false_and_zero():
    for item in _bindings():
        assert item.status == owner.STATUS and item.adapter_verified
        assert not any((item.execution_permitted, item.dispatch_permitted, item.application_permitted,
                        item.activation_permitted, item.runtime_invocation_permitted))
        assert item.invocation_record is None and item.execution_result is None
        assert not any(getattr(item.authority_boundary, f.name) for f in fields(item.authority_boundary))
        assert item.target_request.authority_inputs == ()
        assert (item.isolated_calculator_invocations, item.isolated_bridge_invocations,
                item.isolated_admission_invocations, item.isolated_runtime_invocations,
                item.production_calculator_invocations, item.production_bridge_invocations,
                item.production_admission_invocations, item.production_runtime_invocations,
                item.production_delivery_invocations, item.production_response_commits
                ) == (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def test_underlying_request_remains_passive_and_unmodified():
    report = _report(); before = report.observations
    bindings = owner.create_versioned_cost_runtime_request_bindings(before)
    assert report.observations == before
    for item in bindings:
        source = item.source_request
        assert source.status == "FOUNDATION_BOUND_NOT_QUALIFIED"
        assert not source.requirement_qualified and not source.execute_allowed and not source.dispatch_permitted
        assert source.execution_result is None


def test_optional_waste_is_preserved_but_not_promoted_to_formula_operand():
    present, absent = _bindings(True)[1], _bindings(False)[1]
    present_ids = tuple(x.evidence_id for x in present.target_request.decision.binding.evidence_snapshot)
    absent_ids = tuple(x.evidence_id for x in absent.target_request.decision.binding.evidence_snapshot)
    assert "waste_or_loss_quantity" in present_ids and "waste_or_loss_quantity" not in absent_ids
    assert tuple(x.semantic_role for x in present.source_request.operands if x.operand_used_by_formula) == (
        "total_cost", "unit_quantity")


def test_order_duplicate_cross_skill_and_wrong_input_fail_closed():
    observations = _report().observations
    assert owner.create_versioned_cost_runtime_request_bindings(tuple(reversed(observations))) is None
    assert owner.create_versioned_cost_runtime_request_bindings((observations[0], observations[0])) is None
    assert owner.create_versioned_cost_runtime_request_binding(object()) is None
    item = _bindings()[0]
    assert not owner.verify_versioned_cost_runtime_request_binding(
        replace(item, target_request=_bindings()[1].target_request))


@pytest.mark.parametrize("field,value", (
    ("source_request_id", "forged"), ("source_request_digest", "0" * 64),
    ("source_turn_digest", "0" * 64), ("source_reference_time_digest", "0" * 64),
    ("source_configuration_digest", "0" * 64), ("source_evaluation_digest", "0" * 64),
    ("source_evidence_envelope_digest", "0" * 64), ("source_operand_digests", ()),
    ("source_formula_digest", "0" * 64), ("source_policy_digest", "0" * 64),
    ("field_provenance", ()), ("field_provenance_topology", ()), ("topology", ()),
    ("target_material_digest", "0" * 64), ("adapter_digest", "0" * 64),
    ("execution_permitted", True), ("runtime_invocation_permitted", True),
    ("invocation_record", object()), ("execution_result", object()),
    ("isolated_calculator_invocations", 1), ("production_runtime_invocations", 1),
))
def test_binding_field_tampering_fails_closed(field, value):
    assert not owner.verify_versioned_cost_runtime_request_binding(replace(_bindings()[0], **{field: value}))


def test_target_field_and_authority_substitution_fail_closed():
    item = _bindings()[0]
    for target in (replace(item.target_request, execution_id="caller-id"),
                   replace(item.target_request, request_id="caller-id"),
                   replace(item.target_request, requested_skill_id=_bindings()[1].source_skill_id),
                   replace(item.target_request, authority_inputs=("trusted",))):
        assert not owner.verify_versioned_cost_runtime_request_binding(replace(item, target_request=target))
    assert not owner.verify_versioned_cost_runtime_request_binding(replace(
        item, authority_boundary=replace(item.authority_boundary, execution=True)))


def test_builder_and_verifier_have_no_execution_or_runtime_calls(monkeypatch):
    import brain.business_skill_cost_execution as execution
    monkeypatch.setattr(execution, "execute_cost_skill", lambda *a, **k: (_ for _ in ()).throw(AssertionError("invoked")))
    bindings = _bindings()
    assert owner.verify_versioned_cost_runtime_request_bindings(bindings)
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert not calls.intersection({"execute_cost_skill", "bridge_prepared_cost_response",
                                   "decide_controlled_runtime_integration_admission"})


def test_public_builder_has_no_caller_authority_or_mapping_parameters():
    assert tuple(inspect.signature(owner.create_versioned_cost_runtime_request_binding).parameters) == ("source_observation",)
    assert tuple(inspect.signature(owner.create_versioned_cost_runtime_request_bindings).parameters) == ("observations",)
    text = MODULE.read_text(encoding="utf-8")
    for forbidden in ("import app", "os.environ", "subprocess", "requests.", "open(", "execute_cost_skill("):
        assert forbidden not in text


def test_historical_request_shape_is_unchanged():
    assert tuple(CostExecutionRequest.__dataclass_fields__) == (
        "execution_id", "request_id", "requested_skill_id", "decision", "authority_inputs")
