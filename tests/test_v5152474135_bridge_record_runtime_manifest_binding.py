from __future__ import annotations

import ast
from dataclasses import fields, replace
import inspect
from pathlib import Path

import pytest

import brain.bridge_record_runtime_manifest_binding as owner
from brain.business_skill_cost_runtime_integration_admission_gateway import ControlledRuntimeIntegrationAdmissionRequest
from brain.business_skill_cost_runtime_integration_manifest import verify_controlled_integration_manifest
from brain.business_skill_cost_runtime_integration_qualification import verify_controlled_runtime_integration_qualification
from brain.production_feature_gate_owner import LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
from brain.verifiable_isolated_bridge_invocation_record import create_isolated_bridge_invocation_batch
from test_v5152474133_execution_result_runtime_bridge_request_binding import _batch as source_batch


@pytest.fixture(scope="module")
def bridge_batch():
    return create_isolated_bridge_invocation_batch(source_batch())


@pytest.fixture(scope="module")
def binding(bridge_batch):
    return owner.create_bridge_record_runtime_manifest_binding(bridge_batch)


def test_exact_records_fixed_order_and_no_reinvocation(binding, bridge_batch, monkeypatch):
    assert owner.verify_bridge_record_runtime_manifest_binding(binding)
    assert binding.source_batch is bridge_batch
    assert binding.skill_order == owner.SUPPORTED_ADAPTER_SKILL_IDS
    monkeypatch.setattr("brain.verifiable_isolated_bridge_invocation_record.bridge_prepared_cost_response",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("bridge reinvoked")))
    assert owner.verify_bridge_record_runtime_manifest_binding(binding)


def test_manifest_builder_reuses_batch_verified_records(bridge_batch, monkeypatch):
    monkeypatch.setattr(
        owner,
        "verify_isolated_bridge_invocation_record",
        lambda *a, **k: pytest.fail("record ancestry verified again after batch verification"),
    )
    value = owner.create_bridge_record_runtime_manifest_binding(bridge_batch)
    assert value is not None
    assert value.skill_order == owner.SUPPORTED_ADAPTER_SKILL_IDS


def test_qualification_exact_continuity_and_handoff_ancestry(binding):
    for record, item in zip(binding.source_batch.records, binding.qualification_bindings):
        assert owner.verify_bridge_record_qualification_binding(item)
        assert item.bridge_record is record
        assert item.bridge_request is record.bridge_request
        assert item.bridge_result is record.bridge_result
        assert item.bridge_handoff is record.bridge_result.handoff
        assert item.delivery_qualification is record.source_binding.delivery_qualification
        assert item.runtime_qualification.runtime_bridge_result is record.bridge_result
        assert verify_controlled_runtime_integration_qualification(item.runtime_qualification)


def test_source_request_execution_bridge_and_record_ancestry(binding):
    for item in binding.qualification_bindings:
        source = item.bridge_record.source_binding
        assert (item.source_request_id, item.source_request_digest, item.source_turn_digest,
            item.source_reference_time_digest, item.source_execution_record_digest,
            item.source_bridge_request_binding_digest, item.bridge_record_digest) == (
            source.source_request_id, source.source_request_digest, source.source_turn_digest,
            source.source_reference_time_digest, source.record_digest, source.binding_digest,
            item.bridge_record.record_digest)


def test_manifest_exact_history_and_deterministic_digests(binding, bridge_batch):
    assert binding.historical_qualifications == tuple(x.runtime_qualification for x in binding.qualification_bindings)
    assert verify_controlled_integration_manifest(binding.historical_manifest)
    assert binding.manifest_digest == binding.historical_manifest.manifest_digest
    assert binding == owner.create_bridge_record_runtime_manifest_binding(bridge_batch)
    assert len(binding.topology_digest) == len(binding.binding_digest) == 64


@pytest.mark.parametrize("field", ("bridge_record", "bridge_request", "bridge_result", "bridge_handoff",
    "delivery_qualification", "runtime_qualification"))
def test_cross_skill_artifact_substitution_rejected(binding, field):
    first, second = binding.qualification_bindings
    forged = replace(first, **{field: getattr(second, field)})
    assert not owner.verify_bridge_record_qualification_binding(forged)


@pytest.mark.parametrize("field,value", (("qualification_digest", "0"*64),
    ("bridge_record_digest", "0"*64), ("bridge_request_digest", "0"*64),
    ("bridge_result_digest", "0"*64), ("bridge_handoff_digest", "0"*64),
    ("delivery_qualification_digest", "0"*64), ("gate_identity", "OTHER"),
    ("gate_configured_state", False), ("gate_effective_state", False),
    ("source_target_topology", ()), ("binding_digest", "0"*64)))
def test_qualification_digest_gate_topology_tampering_rejected(binding, field, value):
    assert not owner.verify_bridge_record_qualification_binding(
        replace(binding.qualification_bindings[0], **{field: value}))


@pytest.mark.parametrize("change", (
    lambda x: replace(x, qualification_bindings=tuple(reversed(x.qualification_bindings))),
    lambda x: replace(x, qualification_bindings=x.qualification_bindings[:1]),
    lambda x: replace(x, qualification_bindings=(x.qualification_bindings[0],)*2),
    lambda x: replace(x, historical_qualifications=tuple(reversed(x.historical_qualifications))),
    lambda x: replace(x, historical_manifest=replace(x.historical_manifest, manifest_digest="0"*64)),
    lambda x: replace(x, manifest_digest="0"*64),
    lambda x: replace(x, topology_digest="0"*64),
    lambda x: replace(x, binding_digest="0"*64)))
def test_manifest_reorder_drop_duplicate_source_and_digest_tampering(binding, change):
    assert not owner.verify_bridge_record_runtime_manifest_binding(change(binding))


@pytest.mark.parametrize("field,value", (("admission_invoked", True),
    ("admission_decision", object()), ("controlled_runtime_invoked", True),
    ("runtime_result", object()), ("production_application_permitted", True),
    ("activation_permitted", True), ("response_committed", True),
    ("isolated_admission_invocations", 1), ("isolated_runtime_invocations", 1),
    ("production_bridge_invocations", 1)))
def test_authority_permission_decision_result_and_count_injection_rejected(binding, field, value):
    assert not owner.verify_bridge_record_runtime_manifest_binding(replace(binding, **{field: value}))


def test_gate_counts_and_authority_are_fixed(binding):
    assert all(x[0] == LIMITED_COST_RESPONSE_RUNTIME_BRIDGE and x[1:3] == (True, True)
        for x in binding.gate_identity_bindings)
    assert (binding.isolated_execution_invocations, binding.isolated_calculator_invocations,
        binding.isolated_bridge_invocations, binding.isolated_admission_invocations,
        binding.isolated_runtime_invocations) == (2, 2, 2, 0, 0)
    assert all(getattr(binding, f.name) == 0 for f in fields(binding) if f.name.startswith("production_"))
    assert not any(getattr(binding.authority_boundary, f.name) for f in fields(binding.authority_boundary))


def test_verifier_purity_and_no_bridge_admission_runtime_calls(binding, monkeypatch):
    monkeypatch.setattr(owner, "qualify_controlled_runtime_integration",
        owner.qualify_controlled_runtime_integration)
    assert owner.verify_bridge_record_runtime_manifest_binding(binding)
    tree = ast.parse(inspect.getsource(owner))
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert not called.intersection({"bridge_prepared_cost_response", "decide_controlled_runtime_integration_admission",
        "invoke_runtime", "deliver", "commit_response"})


def test_downstream_admission_request_compatibility_but_no_new_digest_binding(binding):
    request = ControlledRuntimeIntegrationAdmissionRequest(binding.skill_order[0], binding.historical_manifest)
    assert request.manifest is binding.historical_manifest
    assert not hasattr(request, "manifest_binding_digest")
    assert binding.admission_decision is None and not binding.admission_invoked


def test_historical_record_digests_and_static_isolation(binding):
    assert binding.bridge_record_digests == (
        "c8c95c1f0cde489fb0a57ba05b2b429463587f7391a90d4a4c6a09baf34009ec",
        "3dc9ebfdfab92f4210cc4c9d4cb3a9af76f6ef472902ce33e5463ff870813b72")
    assert binding.source_batch.batch_digest == "44c84775f6f5311181e5674f016ddbcd7ab62c12ced613031c83d3901fe4af79"
    for contract in (owner.BridgeRecordManifestBindingAuthorityBoundary,
        owner.BridgeRecordQualificationBinding, owner.BridgeRecordRuntimeManifestBinding):
        assert contract.__dataclass_params__.frozen
    text = Path(owner.__file__).read_text(encoding="utf-8")
    for forbidden in ("import app", "os.environ", "subprocess", "requests.", "open(", "socket",
        "session_state", "decide_controlled_runtime_integration_admission"):
        assert forbidden not in text


def test_public_surface_has_no_authority_api():
    public = set(owner.__all__)
    assert not any(any(word in name.lower() for word in ("admit", "activate", "approve", "deliver", "commit"))
        for name in public)
