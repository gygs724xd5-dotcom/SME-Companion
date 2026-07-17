from __future__ import annotations

import ast
from dataclasses import fields, replace
from datetime import datetime, timezone
from functools import lru_cache
import inspect
from pathlib import Path

import pytest

import brain.execution_result_runtime_bridge_request_binding as owner
from brain.isolated_executable_request_qualification import create_isolated_executable_request_qualification_report
from brain.isolated_gate_enabled_pre_authorization_qualification import create_isolated_gate_enabled_pre_authorization_report
from brain.isolated_qualification_configuration_binding import (
    create_isolated_qualification_feature_gate_binding, create_isolated_qualification_limited_activation_binding,
    create_isolated_qualification_pre_execution_result, create_isolated_qualification_skill_evidence_envelope)
from brain.production_feature_gate_owner import (LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PURE_TEST_TRUSTED_SOURCE_IDENTITY, create_production_feature_gate_configuration,
    evaluate_production_feature_gate)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time
from brain.versioned_cost_runtime_request_adapter import create_versioned_cost_runtime_request_bindings
from brain.verifiable_isolated_runtime_invocation_record import create_isolated_runtime_invocation_batch


def _foundation(message, ordinal):
    context=create_production_turn_context("runtime-adapter-foundation", ordinal, message)
    reference=create_production_turn_reference_time(context, datetime(2026, 7, 16, tzinfo=timezone.utc))
    config=create_production_feature_gate_configuration(PURE_TEST_TRUSTED_SOURCE_IDENTITY,
        ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),))
    evaluation=evaluate_production_feature_gate(config, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE)
    binding=create_isolated_qualification_feature_gate_binding(context, reference, config, evaluation)
    evidence=create_isolated_qualification_skill_evidence_envelope(binding)
    limited=create_isolated_qualification_limited_activation_binding(evidence)
    foundation=create_isolated_qualification_pre_execution_result(limited)
    return foundation, create_isolated_gate_enabled_pre_authorization_report(foundation)


@lru_cache(maxsize=1)
def _source():
    unit="ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น ของเสีย 2 ชิ้น"
    report=create_isolated_executable_request_qualification_report((
        _foundation("cost changed from 100 to 120 baht", 1),
        _foundation(unit, 2)))
    return create_isolated_runtime_invocation_batch(create_versioned_cost_runtime_request_bindings(report.observations))


@lru_cache(maxsize=1)
def _batch(): return owner.create_execution_result_runtime_bridge_request_bindings(_source())


def test_topology_both_skills_and_exact_bridge_request_without_invocation():
    batch=_batch(); assert owner.verify_execution_result_runtime_bridge_request_bindings(batch)
    assert batch.skill_order == owner.SUPPORTED_ADAPTER_SKILL_IDS
    assert tuple(x.skill_id for x in batch.bindings) == owner.SUPPORTED_ADAPTER_SKILL_IDS
    assert all(type(x.bridge_request) is owner.CostRuntimeBridgeRequest for x in batch.bindings)
    assert all(tuple(s.stage_id for s in x.stage_bindings) == owner.STAGE_IDS for x in batch.bindings)
    assert all(s.pure_transformation and not s.invocation for x in batch.bindings for s in x.stage_bindings)


def test_source_to_target_and_integrity_continuity():
    for source, binding in zip(_source().records, _batch().bindings):
        assert binding.invocation_record == source and binding.execution_result == source.output_artifact
        assert binding.execution_result_integrity_digest == source.output_integrity.integrity_digest
        assert binding.presentation_integrity.execution_integrity == source.output_integrity
        assert binding.authorization_integrity.presentation_integrity == binding.presentation_integrity
        assert binding.adapter_integrity.authorization_integrity == binding.authorization_integrity
        assert binding.delivery_integrity.adapter_integrity == binding.adapter_integrity
        assert binding.bridge_request.adapter_result == binding.adapter_result
        assert binding.bridge_request.qualification_result == binding.delivery_qualification
        assert binding.bridge_request_target_material_digest == owner.compute_cost_runtime_bridge_request_digest(binding.bridge_request)


def test_gate_is_derived_from_exact_isolated_binding():
    for binding in _batch().bindings:
        gate=binding.invocation_record.adapter_binding.source_observation.foundation.configuration_binding
        assert (binding.gate_identity, binding.gate_configured_state, binding.gate_effective_state) == (
            LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True, True)
        assert binding.bridge_request.feature_gates == {LIMITED_COST_RESPONSE_RUNTIME_BRIDGE: gate.effective_state}
        assert binding.gate_configuration_digest == gate.configuration_digest
        assert binding.gate_evaluation_digest == gate.evaluation_digest


def test_counts_authority_and_results_are_isolated():
    batch=_batch()
    assert (batch.isolated_execution_invocations, batch.isolated_calculator_invocations,
        batch.isolated_bridge_invocations, batch.isolated_admission_invocations,
        batch.isolated_runtime_invocations) == (2, 2, 0, 0, 0)
    assert (batch.bridge_status, batch.admission_status, batch.runtime_status) == (owner.NOT_INVOKED,) * 3
    assert not batch.bridge_invoked and batch.bridge_result is batch.bridge_handoff is None
    assert all(getattr(batch, f.name) == 0 for f in fields(batch) if f.name.startswith("production_"))
    for item in batch.bindings:
        assert not any(getattr(item.authority_boundary, f.name) for f in fields(item.authority_boundary))
        assert item.bridge_result is item.bridge_handoff is item.admission_decision is item.runtime_result is None


@pytest.mark.parametrize("field,value", (("skill_id", "cost.per_unit_calculation.v1"),
    ("record_digest", "0"*64), ("source_request_digest", "0"*64),
    ("execution_result_integrity_digest", "0"*64), ("gate_identity", "OTHER"),
    ("bridge_request_target_material_digest", "0"*64), ("binding_digest", "0"*64)))
def test_binding_tampering_fails_closed(field, value):
    assert not owner.verify_execution_result_runtime_bridge_request_binding(replace(_batch().bindings[0], **{field:value}))


def test_stage_reorder_drop_duplicate_and_cross_skill_substitution_fail_closed():
    first, second=_batch().bindings
    for stages in (tuple(reversed(first.stage_bindings)), first.stage_bindings[:-1],
                   (first.stage_bindings[0],)+first.stage_bindings):
        assert not owner.verify_execution_result_runtime_bridge_request_binding(replace(first, stage_bindings=stages))
    assert not owner.verify_execution_result_runtime_bridge_request_binding(replace(first, bridge_request=second.bridge_request))
    assert not owner.verify_execution_result_runtime_bridge_request_binding(replace(first, execution_result=second.execution_result))


@pytest.mark.parametrize("change", (lambda b: replace(b, bindings=tuple(reversed(b.bindings))),
    lambda b: replace(b, bindings=b.bindings[:1]), lambda b: replace(b, topology_digest="0"*64),
    lambda b: replace(b, isolated_bridge_invocations=1), lambda b: replace(b, bridge_invoked=True),
    lambda b: replace(b, production_runtime_invocations=1), lambda b: replace(b, batch_digest="0"*64)))
def test_batch_tampering_fails_closed(change):
    assert not owner.verify_execution_result_runtime_bridge_request_bindings(change(_batch()))


def test_verifier_purity_when_bridge_entry_point_raises(monkeypatch):
    import brain.business_skill_cost_response_runtime_bridge as bridge
    monkeypatch.setattr(bridge, "bridge_prepared_cost_response", lambda *a, **k: (_ for _ in ()).throw(AssertionError("invoked")))
    assert owner.verify_execution_result_runtime_bridge_request_bindings(_batch())
    tree=ast.parse(inspect.getsource(owner))
    called={n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "bridge_prepared_cost_response" not in called


def test_deterministic_rerun_and_distinct_skill_material():
    assert owner.create_execution_result_runtime_bridge_request_bindings(_source()) == _batch()
    first, second=_batch().bindings
    assert first.binding_digest != second.binding_digest
    assert first.bridge_request_target_material_digest != second.bridge_request_target_material_digest
    assert first.presentation_result.draft.draft_text != second.presentation_result.draft.draft_text


def test_canonical_74132_digests_are_unchanged():
    source=_source()
    assert tuple(x.record_digest for x in source.records) == (
        "c623db00e38ee4da708e8787e92cd64d80e6699273e9aaf3be42e89c2827a93b",
        "a97182ae3c775247ee8bdf101114d7ac361158021cf4d60d949e957ded167a70")
    assert source.batch_digest == "1f21f77936763b54de33363c523d53746da9c0687d697f722cad48b430a3cc36"


def test_frozen_public_api_and_static_isolation():
    for contract in (owner.ExecutionResultBridgeBindingAuthorityBoundary, owner.ExecutionResultBridgeStageBinding,
                     owner.ExecutionResultRuntimeBridgeRequestBinding, owner.ExecutionResultRuntimeBridgeRequestBatch):
        assert contract.__dataclass_params__.frozen
    assert tuple(inspect.signature(owner.create_execution_result_runtime_bridge_request_binding).parameters) == ("record",)
    assert tuple(inspect.signature(owner.create_execution_result_runtime_bridge_request_bindings).parameters) == ("source",)
    text=Path(owner.__file__).read_text(encoding="utf-8")
    for forbidden in ("import app", "os.environ", "subprocess", "requests.", "open(", "socket", "session_state"):
        assert forbidden not in text
