from __future__ import annotations

import ast
from dataclasses import fields, replace
import inspect
from pathlib import Path

import pytest

import brain.versioned_controlled_runtime_admission_request_binding as owner
from brain.bridge_record_runtime_manifest_binding import create_bridge_record_runtime_manifest_binding
from brain.business_skill_cost_runtime_integration_admission_gateway import (
    ControlledRuntimeIntegrationAdmissionDecision,
    ControlledRuntimeIntegrationAdmissionRequest,
    decide_controlled_runtime_integration_admission,
)
from brain.verifiable_isolated_bridge_invocation_record import create_isolated_bridge_invocation_batch
from test_v5152474133_execution_result_runtime_bridge_request_binding import _batch as execution_batch


@pytest.fixture(scope="module")
def source():
    return create_bridge_record_runtime_manifest_binding(
        create_isolated_bridge_invocation_batch(execution_batch()))


@pytest.fixture(scope="module")
def batch(source):
    return owner.create_versioned_controlled_runtime_admission_request_bindings(source)


def test_exact_manifest_source_inventory_and_canonical_continuity(source, batch):
    assert owner.verify_versioned_controlled_runtime_admission_request_bindings(batch)
    assert batch.source_manifest_binding is source
    assert batch.historical_manifest is source.historical_manifest
    assert batch.skill_order == ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")
    assert tuple(x.skill_id for x in batch.historical_manifest.approvals) == batch.skill_order
    assert (source.qualification_binding_digests, source.manifest_digest,
            source.topology_digest, source.binding_digest) == (
        ("f9aa1ec21e39c44dcce114d585f37d35def02e65f11e5aabdc7a07e43687386d",
         "92e2ff049cef3682f0cb973861c94db2fbf60b5b9929d2584724cd21d5f9be53"),
        "6b4099bd72bdb7fe2aa3da7eccf6d1aa7956d07d122d1a4322cf54a5b554ff6b",
        "e9e944acf79bf47d24d1f42f3194effa3fa297fcf1cdfd6f817adce9d1110f9f",
        "2da1140b075c82d9e13b5516e969eb39d8ed1fc0eabc276ee4458c25e940dd21")


def test_per_skill_requests_are_exact_distinct_and_strict(batch):
    assert tuple(x.skill_id for x in batch.bindings) == batch.skill_order
    assert len({x.binding_digest for x in batch.bindings}) == 2
    for item in batch.bindings:
        assert owner.verify_versioned_controlled_runtime_admission_request_binding(item)
        assert type(item.target_request) is ControlledRuntimeIntegrationAdmissionRequest
        assert item.target_request == ControlledRuntimeIntegrationAdmissionRequest(
            item.skill_id, batch.historical_manifest)
        assert item.target_request.manifest is batch.historical_manifest


def test_full_source_ancestry_and_gate_continuity(batch):
    for item, q in zip(batch.bindings, batch.source_manifest_binding.qualification_bindings):
        assert item.source_qualification_binding is q
        assert item.source_bridge_record is q.bridge_record
        assert (item.source_bridge_record_digest, item.source_bridge_request_digest,
            item.source_bridge_result_digest, item.source_bridge_handoff_digest) == (
            q.bridge_record_digest, q.bridge_request_digest, q.bridge_result_digest,
            q.bridge_handoff_digest)
        assert (item.source_request_id, item.source_request_digest,
            item.source_execution_record_digest, item.source_turn_digest,
            item.source_reference_time_digest) == (q.source_request_id,
            q.source_request_digest, q.source_execution_record_digest,
            q.source_turn_digest, q.source_reference_time_digest)
        assert item.gate_identity == "LIMITED_COST_RESPONSE_RUNTIME_BRIDGE"
        assert q.gate_configured_state is q.gate_effective_state is True
        assert (item.gate_configuration_digest, item.gate_evaluation_digest) == (
            q.gate_configuration_digest, q.gate_evaluation_digest)


def test_batch_determinism_topology_counts_and_no_authority(source, batch):
    again = owner.create_versioned_controlled_runtime_admission_request_bindings(source)
    assert batch == again and len(batch.topology_digest) == len(batch.batch_digest) == 64
    assert (batch.isolated_execution_invocations, batch.isolated_calculator_invocations,
        batch.isolated_bridge_invocations, batch.isolated_admission_invocations,
        batch.isolated_runtime_invocations, batch.production_invocations) == (2, 2, 2, 0, 0, 0)
    assert not batch.admission_invoked and batch.admission_decisions == ()
    assert not batch.controlled_runtime_invoked and batch.runtime_results == ()
    assert not any(getattr(batch.authority_boundary, f.name)
        for f in fields(batch.authority_boundary))


@pytest.mark.parametrize("field,value", (
    ("source_manifest_binding_digest", "0"*64), ("manifest_digest", "0"*64),
    ("source_qualification_binding_digest", "0"*64),
    ("source_bridge_record_digest", "0"*64), ("source_bridge_request_digest", "0"*64),
    ("source_bridge_result_digest", "0"*64), ("source_bridge_handoff_digest", "0"*64),
    ("source_request_digest", "0"*64), ("source_execution_record_digest", "0"*64),
    ("source_turn_digest", "0"*64), ("source_reference_time_digest", "0"*64),
    ("gate_identity", "OTHER"), ("gate_configuration_digest", "0"*64),
    ("gate_evaluation_digest", "0"*64), ("target_request_material_digest", "0"*64),
    ("ancestry_topology", ()), ("binding_digest", "0"*64)))
def test_binding_material_digest_gate_topology_tampering_rejected(batch, field, value):
    assert not owner.verify_versioned_controlled_runtime_admission_request_binding(
        replace(batch.bindings[0], **{field: value}))


def test_target_request_cross_skill_and_source_substitution_rejected(batch):
    first, second = batch.bindings
    assert not owner.verify_versioned_controlled_runtime_admission_request_binding(
        replace(first, target_request=second.target_request))
    assert not owner.verify_versioned_controlled_runtime_admission_request_binding(
        replace(first, source_qualification_binding=second.source_qualification_binding))
    assert owner.create_versioned_controlled_runtime_admission_request_binding(
        batch.source_manifest_binding, replace(first.source_qualification_binding,
        skill_id=second.skill_id)) is None


@pytest.mark.parametrize("change", (
    lambda x: replace(x, bindings=tuple(reversed(x.bindings))),
    lambda x: replace(x, bindings=x.bindings[:1]),
    lambda x: replace(x, bindings=(x.bindings[0],)*2),
    lambda x: replace(x, skill_order=tuple(reversed(x.skill_order))),
    lambda x: replace(x, topology_digest="0"*64),
    lambda x: replace(x, batch_digest="0"*64),
    lambda x: replace(x, admission_invoked=True),
    lambda x: replace(x, admission_decisions=(object(),)),
    lambda x: replace(x, controlled_runtime_invoked=True),
    lambda x: replace(x, runtime_results=(object(),)),
    lambda x: replace(x, production_application_permitted=True),
    lambda x: replace(x, activation_permitted=True),
    lambda x: replace(x, response_committed=True),
    lambda x: replace(x, isolated_admission_invocations=1),
    lambda x: replace(x, production_invocations=1)))
def test_batch_reorder_drop_duplicate_digest_flag_count_injection_rejected(batch, change):
    assert not owner.verify_versioned_controlled_runtime_admission_request_bindings(change(batch))


def test_no_admission_invocation_and_static_isolation(batch, monkeypatch):
    monkeypatch.setattr(
        "brain.business_skill_cost_runtime_integration_admission_gateway.decide_controlled_runtime_integration_admission",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("admission invoked")))
    assert owner.verify_versioned_controlled_runtime_admission_request_bindings(batch)
    tree = ast.parse(inspect.getsource(owner))
    called = {n.func.id for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "decide_controlled_runtime_integration_admission" not in called
    text = Path(owner.__file__).read_text(encoding="utf-8")
    for forbidden in ("import app", "os.environ", "session_state", "subprocess", "open(",
                      "requests.", "socket", "bridge_prepared_cost_response", "invoke_runtime"):
        assert forbidden not in text


def test_downstream_gateway_contract_compatible_without_decision(batch):
    signature = inspect.signature(decide_controlled_runtime_integration_admission)
    assert tuple(signature.parameters) == ("request",)
    assert all(type(x.target_request) is ControlledRuntimeIntegrationAdmissionRequest
        for x in batch.bindings)
    assert "ControlledRuntimeIntegrationAdmissionDecision" == ControlledRuntimeIntegrationAdmissionDecision.__name__
    assert "source_manifest_binding_digest" not in ControlledRuntimeIntegrationAdmissionDecision.__dataclass_fields__
    assert batch.admission_decisions == ()


def test_contracts_frozen_public_surface_and_request_constructor():
    for contract in (owner.ControlledRuntimeAdmissionRequestBindingAuthorityBoundary,
        owner.VersionedControlledRuntimeAdmissionRequestBinding,
        owner.VersionedControlledRuntimeAdmissionRequestBatch):
        assert contract.__dataclass_params__.frozen
    assert tuple(inspect.signature(ControlledRuntimeIntegrationAdmissionRequest).parameters) == (
        "skill_id", "manifest")
    assert not any(any(word in name.lower() for word in
        ("decide", "admit", "invoke", "activate", "approve", "deliver", "commit"))
        for name in owner.__all__)
