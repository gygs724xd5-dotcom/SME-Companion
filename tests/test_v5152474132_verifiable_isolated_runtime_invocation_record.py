from __future__ import annotations

import ast
from dataclasses import fields, replace
from datetime import datetime, timezone
import inspect
from functools import lru_cache
from pathlib import Path

import pytest

import brain.verifiable_isolated_runtime_invocation_record as owner
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
from brain.versioned_cost_runtime_request_adapter import create_versioned_cost_runtime_request_bindings

MODULE = Path(owner.__file__)


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
def _bindings(waste=True):
    unit = "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น"
    if waste: unit += " ของเสีย 2 ชิ้น"
    report = create_isolated_executable_request_qualification_report((
        _foundation("cost changed from 100 to 120 baht", 1), _foundation(unit, 2)))
    return create_versioned_cost_runtime_request_bindings(report.observations)


def _batch(waste=True):
    return owner.create_isolated_runtime_invocation_batch(_bindings(waste))


def test_actual_exact_adapter_targets_are_invoked_once_and_verifier_is_pure(monkeypatch):
    calls = []
    original = owner.execute_cost_skill
    monkeypatch.setattr(owner, "execute_cost_skill", lambda request: (calls.append(request), original(request))[1])
    batch = _batch()
    assert calls == [x.target_request for x in _bindings()]
    assert owner.verify_isolated_runtime_invocation_batch(batch)
    assert len(calls) == 2
    monkeypatch.setattr(owner, "execute_cost_skill", lambda request: (_ for _ in ()).throw(AssertionError("reinvoked")))
    assert owner.verify_isolated_runtime_invocation_batch(batch)


def test_both_skills_order_exact_results_and_distinct_records():
    batch = _batch()
    assert tuple(x.skill_id for x in batch.records) == owner.SUPPORTED_ADAPTER_SKILL_IDS
    assert tuple(x.adapter_digest for x in batch.records) == (
        "667b9953c59a14c984601323ec0120959a8769ae229cbe43d517205c6fdf4c34",
        "92f5d2cf8cdc39af5857f001fc8317391ad5219102e378cfcb9ad4c2d61f2078",
    )
    assert (batch.records[0].output_artifact.metrics[3].value,
            batch.records[1].output_artifact.metrics[2].value) == ("20.000000", "15.000000")
    assert len({x.record_id for x in batch.records}) == len({x.record_digest for x in batch.records}) == 2
    assert batch.records[1].previous_record_digest == batch.records[0].record_digest


def test_exact_source_adapter_target_output_and_integrity_binding():
    for record, binding in zip(_batch().records, _bindings()):
        assert record.source_request == binding.source_request
        assert record.adapter_binding == binding
        assert record.target_request == binding.target_request
        assert record.output_integrity.execution_request == binding.target_request
        assert record.output_integrity.execution_result == record.output_artifact
        assert record.output_result_digest == record.output_integrity.result_snapshot_digest
        assert owner.verify_isolated_execution_invocation_record(record)


def test_optional_waste_identity_is_bound_but_formula_result_is_unchanged():
    present, absent = _batch(True).records[1], _batch(False).records[1]
    assert present.output_artifact.metrics == absent.output_artifact.metrics
    assert present.source_request.evidence_envelope_digest != absent.source_request.evidence_envelope_digest
    assert present.adapter_digest != absent.adapter_digest
    assert present.record_digest != absent.record_digest


def test_counts_are_derived_and_unrecorded_stages_and_production_stay_zero():
    batch = _batch()
    assert (batch.isolated_execution_invocations, batch.isolated_calculator_invocations,
            batch.isolated_bridge_invocations, batch.isolated_admission_invocations,
            batch.isolated_runtime_invocations) == (2, 2, 0, 0, 0)
    assert (batch.bridge_status, batch.admission_status, batch.runtime_status) == (owner.NOT_RECORDED,) * 3
    assert all(getattr(batch, f.name) == 0 for f in fields(batch) if f.name.startswith("production_"))


@pytest.mark.parametrize("field,value", (
    ("stage", "CONTROLLED_RUNTIME"), ("skill_id", "cost.per_unit_calculation.v1"),
    ("source_request_digest", "0" * 64), ("adapter_digest", "0" * 64),
    ("target_material_digest", "0" * 64), ("invoked_operation", "caller.operation"),
    ("output_result_digest", "0" * 64), ("invocation_outcome", "FAILED"),
    ("record_id", "0" * 64), ("record_digest", "0" * 64),
))
def test_record_tampering_fails_closed(field, value):
    assert not owner.verify_isolated_execution_invocation_record(replace(_batch().records[0], **{field: value}))


def test_cross_skill_target_output_and_authority_tampering_fail_closed():
    first, second = _batch().records
    assert not owner.verify_isolated_execution_invocation_record(replace(first, target_request=second.target_request))
    assert not owner.verify_isolated_execution_invocation_record(replace(first, output_artifact=second.output_artifact))
    boundary = replace(first.authority_boundary, production_dispatch=True)
    assert not owner.verify_isolated_execution_invocation_record(replace(first, authority_boundary=boundary))


@pytest.mark.parametrize("change", (
    lambda b: replace(b, records=tuple(reversed(b.records))),
    lambda b: replace(b, records=b.records[:1]),
    lambda b: replace(b, records=(b.records[0], b.records[0])),
    lambda b: replace(b, isolated_execution_invocations=99),
    lambda b: replace(b, isolated_bridge_invocations=1),
    lambda b: replace(b, production_runtime_invocations=1),
    lambda b: replace(b, bridge_status="ACCEPTED"),
    lambda b: replace(b, batch_digest="0" * 64),
))
def test_batch_reorder_drop_duplicate_forged_counts_and_stage_claims_fail(change):
    assert not owner.verify_isolated_runtime_invocation_batch(change(_batch()))


def test_underlying_source_and_adapter_permissions_remain_immutable_and_false():
    bindings = _bindings(); before = tuple(bindings)
    batch = owner.create_isolated_runtime_invocation_batch(bindings)
    assert bindings == before and owner.verify_isolated_runtime_invocation_batch(batch)
    for binding in bindings:
        assert not binding.source_request.execute_allowed
        assert not binding.execution_permitted and not binding.runtime_invocation_permitted
        assert binding.execution_result is None and binding.invocation_record is None


def test_public_api_has_no_authority_output_or_count_injection_and_verifier_source_has_no_call():
    assert tuple(inspect.signature(owner.create_isolated_execution_invocation_record).parameters) == ("binding",)
    assert tuple(inspect.signature(owner.create_isolated_runtime_invocation_batch).parameters) == ("bindings",)
    verifier = ast.parse(inspect.getsource(owner.verify_isolated_execution_invocation_record))
    calls = {n.func.id for n in ast.walk(verifier) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "execute_cost_skill" not in calls


def test_static_isolation_has_no_app_environment_file_network_or_subprocess_access():
    text = MODULE.read_text(encoding="utf-8")
    for forbidden in ("import app", "os.environ", "subprocess", "requests.", "open(", "socket", "session_state"):
        assert forbidden not in text
    imported = {n.module for n in ast.walk(ast.parse(text)) if isinstance(n, ast.ImportFrom)}
    assert not any(x and ("presenter" in x or "authorization" in x or "response_adapter" in x
                          or "runtime_bridge" in x or "admission" in x) for x in imported)


def test_noncanonical_adapter_and_wrong_order_fail_without_invocation(monkeypatch):
    calls = []
    monkeypatch.setattr(owner, "execute_cost_skill", lambda request: calls.append(request))
    bindings = _bindings()
    assert owner.create_isolated_execution_invocation_record(replace(bindings[0], adapter_digest="0" * 64)) is None
    assert owner.create_isolated_runtime_invocation_batch(tuple(reversed(bindings))) is None
    assert calls == []


def test_contracts_are_frozen_and_authority_is_fixed_false():
    for contract in (owner.IsolatedRuntimeInvocationAuthorityBoundary, owner.IsolatedRuntimeInvocationInputBinding,
                     owner.IsolatedRuntimeInvocationRecord, owner.IsolatedRuntimeInvocationBatch):
        assert contract.__dataclass_params__.frozen
    boundary = _batch().records[0].authority_boundary
    assert boundary.boundary_id == "CANONICAL_TEST_ACCEPTANCE_HARNESS_ONLY"
    assert not any(getattr(boundary, f.name) for f in fields(boundary) if f.name != "boundary_id")
