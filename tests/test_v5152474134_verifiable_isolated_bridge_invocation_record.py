from __future__ import annotations

import ast
from dataclasses import fields, replace
import inspect
from pathlib import Path

import pytest

import brain.verifiable_isolated_bridge_invocation_record as owner
from test_v5152474133_execution_result_runtime_bridge_request_binding import _batch as source_batch


@pytest.fixture(scope="module")
def batch():
    return owner.create_isolated_bridge_invocation_batch(source_batch())


def test_actual_bridge_invocation_both_skills_and_exact_continuity(batch, monkeypatch):
    assert owner.verify_isolated_bridge_invocation_batch(batch)
    assert tuple(x.skill_id for x in batch.records)==owner.SUPPORTED_ADAPTER_SKILL_IDS
    assert batch.records[0].record_digest!=batch.records[1].record_digest
    for record in batch.records:
        assert record.bridge_request is record.source_binding.bridge_request
        assert record.bridge_result.canonical_request.adapter_result==record.bridge_request.adapter_result
        assert record.bridge_result.handoff is record.bridge_handoff
        assert record.bridge_handoff.text==record.source_binding.adapter_result.payload.text
        assert record.bridge_result_digest==record.bridge_result.result_digest
        assert record.bridge_handoff_digest==record.bridge_handoff.handoff_digest
    monkeypatch.setattr(owner,"bridge_prepared_cost_response",lambda *a,**k: (_ for _ in ()).throw(AssertionError("reinvoked")))
    assert owner.verify_isolated_bridge_invocation_batch(batch)


def test_builder_invokes_once_and_verifier_is_pure(monkeypatch):
    source=source_batch().bindings[0]; calls=[]
    real=owner.bridge_prepared_cost_response
    monkeypatch.setattr(owner,"bridge_prepared_cost_response",lambda request: (calls.append(request),real(request))[1])
    record=owner.create_isolated_bridge_invocation_record(source)
    assert calls==[source.bridge_request]
    monkeypatch.setattr(owner,"bridge_prepared_cost_response",lambda *a,**k: (_ for _ in ()).throw(AssertionError("reinvoked")))
    assert owner.verify_isolated_bridge_invocation_record(record)
    tree=ast.parse(inspect.getsource(owner.verify_isolated_bridge_invocation_record))
    assert "bridge_prepared_cost_response" not in {n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}


def test_batch_reuses_verified_source_for_records(monkeypatch):
    source = source_batch()
    monkeypatch.setattr(
        owner,
        "create_isolated_bridge_invocation_record",
        lambda *a, **k: pytest.fail("public record factory repeated source verification"),
    )
    value = owner.create_isolated_bridge_invocation_batch(source)
    assert value is not None
    monkeypatch.setattr(
        owner,
        "verify_isolated_bridge_invocation_record",
        lambda *a, **k: pytest.fail("public record verifier repeated source verification"),
    )
    assert owner.verify_isolated_bridge_invocation_batch(value)


def test_gate_identity_authority_and_counts(batch):
    assert (batch.isolated_execution_invocations,batch.isolated_calculator_invocations,
        batch.isolated_bridge_invocations,batch.isolated_admission_invocations,
        batch.isolated_runtime_invocations)==(2,2,2,0,0)
    assert all(getattr(batch,f.name)==0 for f in fields(batch) if f.name.startswith("production_"))
    for record in batch.records:
        assert record.gate_identity_binding==owner.FEATURE_GATE_NAME
        assert (record.input_binding.gate_configured_state,record.input_binding.gate_effective_state)==(True,True)
        assert record.bridge_result.feature_gate_name==record.bridge_handoff.feature_gate_name==owner.FEATURE_GATE_NAME
        assert not record.admission_invoked and not record.runtime_invoked
        assert not record.delivery_invoked and not record.response_committed
        boundary=record.authority_boundary
        assert boundary.isolated_bridge_invocation and not any(getattr(boundary,f.name) for f in fields(boundary) if f.name!="isolated_bridge_invocation")


@pytest.mark.parametrize("field,value",(("skill_id","cost.per_unit_calculation.v1"),("bridge_result_digest","0"*64),
    ("bridge_handoff_digest","0"*64),("gate_identity_binding","OTHER"),("invocation_outcome","FORGED"),
    ("admission_invoked",True),("runtime_invoked",True),("delivery_invoked",True),("response_committed",True),
    ("record_id","forged"),("record_digest","0"*64)))
def test_record_tampering_fails_closed(batch,field,value):
    assert not owner.verify_isolated_bridge_invocation_record(replace(batch.records[0],**{field:value}))


def test_source_request_result_handoff_and_cross_skill_substitution_rejected(batch):
    first,second=batch.records
    changes=(replace(first,source_binding=second.source_binding),replace(first,bridge_request=second.bridge_request),
        replace(first,bridge_result=second.bridge_result),replace(first,bridge_handoff=second.bridge_handoff),
        replace(first,input_binding=replace(first.input_binding,request_digest="0"*64)),
        replace(first,authority_boundary=replace(first.authority_boundary,network=True)))
    assert all(not owner.verify_isolated_bridge_invocation_record(x) for x in changes)


@pytest.mark.parametrize("change",(lambda b: replace(b,records=tuple(reversed(b.records))),
    lambda b: replace(b,records=b.records[:1]),lambda b: replace(b,records=(b.records[0],b.records[0])),
    lambda b: replace(b,isolated_bridge_invocations=1),lambda b: replace(b,production_bridge_invocations=1),
    lambda b: replace(b,batch_digest="0"*64)))
def test_batch_reorder_drop_duplicate_and_count_injection_rejected(batch,change):
    assert not owner.verify_isolated_bridge_invocation_batch(change(batch))


def test_downstream_feasibility_without_admission_invocation(batch):
    from brain.business_skill_cost_runtime_integration_qualification import (
        ControlledRuntimeQualificationInput, qualify_controlled_runtime_integration,
        verify_controlled_runtime_integration_qualification)
    qualifications=tuple(qualify_controlled_runtime_integration(ControlledRuntimeQualificationInput(
        x.skill_id,x.source_binding.delivery_qualification,x.bridge_result)) for x in batch.records)
    assert all(verify_controlled_runtime_integration_qualification(x) for x in qualifications)
    from brain.business_skill_cost_runtime_integration_manifest import create_controlled_integration_manifest
    assert create_controlled_integration_manifest(qualifications).approved_skill_ids==owner.SUPPORTED_ADAPTER_SKILL_IDS
    assert all(not x.admission_invoked for x in batch.records)


def test_historical_digests_frozen_contracts_and_static_isolation(batch):
    source=source_batch()
    assert source.topology_digest=="388787e6ed552ee80b6ed6dd9ce3f8096f4517679ec2dae1c2d35bad4eb5f840"
    assert source.batch_digest=="cc7505404010e1112dceea42fafb588462bd87004cbfa3711bee11b0ba0d0104"
    assert tuple(x.binding_digest for x in source.bindings)==("67eb73a57c042adeacccaf6f0df5fe4bfa6494c1c3a789240f59449e221873d5","560c78e4f7b392526f49bf9c897abf02cc9a01308aa136eabe4469770a778802")
    for contract in (owner.IsolatedBridgeInvocationAuthorityBoundary,owner.IsolatedBridgeInvocationInputBinding,
        owner.IsolatedBridgeInvocationRecord,owner.IsolatedBridgeInvocationBatch): assert contract.__dataclass_params__.frozen
    text=Path(owner.__file__).read_text(encoding="utf-8")
    for forbidden in ("import app","os.environ","subprocess","requests.","open(","socket","session_state",
        "decide_controlled_runtime_integration_admission"):
        assert forbidden not in text
    public_functions={n.name for n in ast.walk(ast.parse(text)) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    assert not public_functions.intersection({"admit","activate","production_dispatch","deliver","commit","approve"})
