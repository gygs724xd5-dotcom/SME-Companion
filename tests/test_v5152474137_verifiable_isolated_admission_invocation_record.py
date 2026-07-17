from __future__ import annotations

import ast
from dataclasses import fields, replace
import inspect
from pathlib import Path

import pytest

import brain.verifiable_isolated_admission_invocation_record as owner
from brain.bridge_record_runtime_manifest_binding import create_bridge_record_runtime_manifest_binding
from brain.business_skill_cost_runtime_integration_admission_gateway import (
    ControlledRuntimeIntegrationAdmissionDecision,
    verify_controlled_runtime_integration_admission_decision,
)
from brain.verifiable_isolated_bridge_invocation_record import create_isolated_bridge_invocation_batch
from brain.versioned_controlled_runtime_admission_request_binding import (
    create_versioned_controlled_runtime_admission_request_bindings,
)
from test_v5152474133_execution_result_runtime_bridge_request_binding import _batch as execution_batch


@pytest.fixture(scope="module")
def source():
    bridge = create_bridge_record_runtime_manifest_binding(
        create_isolated_bridge_invocation_batch(execution_batch()))
    return create_versioned_controlled_runtime_admission_request_bindings(bridge)


@pytest.fixture(scope="module")
def batch(source):
    return owner.create_isolated_admission_invocation_batch(source)


def test_actual_gateway_once_per_exact_bound_request_and_decision_integrity(source, monkeypatch):
    actual = owner._gateway.decide_controlled_runtime_integration_admission
    calls = []
    def counted(request):
        calls.append(request)
        return actual(request)
    monkeypatch.setattr(owner._gateway, "decide_controlled_runtime_integration_admission", counted)
    result = owner.create_isolated_admission_invocation_batch(source)
    assert calls == [x.target_request for x in source.bindings]
    assert all(call is item.target_request for call, item in zip(calls, source.bindings))
    assert len(calls) == 2
    for record, binding in zip(result.records, source.bindings):
        assert type(record.decision) is ControlledRuntimeIntegrationAdmissionDecision
        assert verify_controlled_runtime_integration_admission_decision(
            record.decision, binding.target_request)
        assert record.input_binding.source_binding is binding
        assert record.input_binding.target_request is binding.target_request
        assert record.decision.skill_id == binding.skill_id


def test_fixed_both_skill_order_distinct_decisions_and_canonical_7136_digests(source, batch):
    assert batch.skill_order == ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")
    assert tuple(x.skill_id for x in batch.records) == batch.skill_order
    assert len(set(batch.record_ids)) == len(set(batch.record_digests)) == 2
    assert tuple(x.target_request_material_digest for x in source.bindings) == (
        "332ba0d7ad445082f745f7874c46a240b6182c4ed4116adbe4a83d221bbc721a",
        "9bde313b0f3a199677f99e0b09f8e157be7fad830263d86527d730f1bc793cd8")
    assert tuple(x.binding_digest for x in source.bindings) == (
        "c1882143aa4082a84b9de36be68de904bbc06f1e0a4fb1f8e7656940aab08485",
        "38dc94153c8e2aad56ebea0298a2b1e10737cefb086b49c8e01bce2e31902278")
    assert (source.topology_digest, source.batch_digest) == (
        "1e5c4bd1c189d1dbbb3b33a2d40d74e11e974a80ca44e037c8889fad1f8ec118",
        "10db46e524ffabd9213e43e83a8399567075ca83ee534bd1d7410fc37f3947df")


def test_admitted_decision_continuity_authority_and_counts(batch):
    assert owner.verify_isolated_admission_invocation_batch(batch)
    assert batch.admitted_count == 2 and batch.denied_count == 0
    assert (batch.isolated_execution_invocations, batch.isolated_calculator_invocations,
        batch.isolated_bridge_invocations, batch.isolated_admission_invocations,
        batch.isolated_runtime_invocations) == (2, 2, 2, 2, 0)
    assert (batch.production_admission_invocations, batch.production_runtime_invocations,
        batch.production_delivery_invocations, batch.production_commit_invocations) == (0, 0, 0, 0)
    for record in batch.records:
        assert record.admitted and record.decision_status == "ADMITTED"
        assert record.decision_reasons == record.decision.reasons
        assert record.decision_digest == record.decision.decision_digest
        assert not record.runtime_invoked and record.runtime_result is None
        assert not record.production_admission
        assert not any(getattr(record.authority_boundary, f.name)
            for f in fields(record.authority_boundary))


@pytest.mark.parametrize("change", (
    lambda x: replace(x, records=tuple(reversed(x.records))),
    lambda x: replace(x, records=x.records[:1]),
    lambda x: replace(x, records=(x.records[0],) * 2),
    lambda x: replace(x, skill_order=tuple(reversed(x.skill_order))),
    lambda x: replace(x, admitted_count=1),
    lambda x: replace(x, denied_count=1),
    lambda x: replace(x, isolated_admission_invocations=1),
    lambda x: replace(x, isolated_runtime_invocations=1),
    lambda x: replace(x, production_admission_invocations=1),
    lambda x: replace(x, topology_digest="0" * 64),
    lambda x: replace(x, batch_digest="0" * 64),
))
def test_batch_reorder_drop_duplicate_and_forged_counts_rejected(batch, change):
    assert not owner.verify_isolated_admission_invocation_batch(change(batch))


@pytest.mark.parametrize("field,value", (
    ("skill_id", "cost.per_unit_calculation.v1"), ("decision_status", "DENIED"),
    ("decision_reasons", ("FORGED",)), ("admitted", False),
    ("decision_digest", "0" * 64), ("gateway_identity", "other"),
    ("gateway_version", "other"), ("runtime_invoked", True),
    ("runtime_result", object()), ("production_admission", True),
    ("record_id", "0" * 64), ("record_digest", "0" * 64),
))
def test_record_decision_gateway_runtime_and_digest_tampering_rejected(batch, field, value):
    assert not owner.verify_isolated_admission_invocation_record(
        replace(batch.records[0], **{field: value}))


def test_cross_skill_request_decision_and_source_substitution_rejected(batch):
    first, second = batch.records
    assert not owner.verify_isolated_admission_invocation_record(
        replace(first, decision=second.decision))
    assert not owner.verify_isolated_admission_invocation_record(replace(first,
        input_binding=replace(first.input_binding, source_binding=second.input_binding.source_binding)))


def test_verifier_is_pure_and_never_reinvokes_gateway(batch, monkeypatch):
    monkeypatch.setattr(owner._gateway, "decide_controlled_runtime_integration_admission",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("gateway reinvoked")))
    assert owner.verify_isolated_admission_invocation_batch(batch)
    tree = ast.parse(inspect.getsource(owner.verify_isolated_admission_invocation_record))
    names = {n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
        for n in ast.walk(tree) if isinstance(n, ast.Call)
        and isinstance(n.func, (ast.Attribute, ast.Name))}
    assert "decide_controlled_runtime_integration_admission" not in names


def test_contracts_frozen_public_surface_and_static_isolation():
    for contract in (owner.IsolatedAdmissionInvocationAuthorityBoundary,
        owner.IsolatedAdmissionInvocationInputBinding,
        owner.IsolatedAdmissionInvocationRecord, owner.IsolatedAdmissionInvocationBatch):
        assert contract.__dataclass_params__.frozen
    assert not any(name in owner.__all__ for name in
        ("invoke_runtime", "activate", "production_admit", "deliver", "commit", "approve"))
    text = Path(owner.__file__).read_text(encoding="utf-8")
    for forbidden in ("import app", "os.environ", "session_state", "subprocess", "open(",
                      "requests.", "socket", "bridge_prepared_cost_response", "invoke_runtime"):
        assert forbidden not in text
