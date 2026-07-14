"""V5.15.24.7.2 current-default-denied single-skill evidence."""
import ast
import copy
import dataclasses
from decimal import Decimal
from pathlib import Path

import pytest

from brain.production_single_skill_admission_evidence import *
from tests.test_v5152471_production_cost_execution_delivery_integrity import chain, CHANGE, UNIT


@pytest.mark.parametrize("message,skill", ((CHANGE, "cost.change_analysis.v1"),
    (UNIT, "cost.per_unit_calculation.v1"),
    ("ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น", "cost.per_unit_calculation.v1")))
def test_complete_current_single_skill_evidence(message, skill):
    _, source = chain(message)
    value = create_production_single_skill_admission_evidence(source)
    assert value is not None and verify_production_single_skill_admission_evidence(value)
    assert value.selected_skill_id == skill and value.status == VERIFIED_DEFAULT_DENIED
    assert tuple(x.gate for x in value.gate_results) == GATE_ORDER
    assert all(x.passed for x in value.gate_results)


def test_default_denial_semantics_and_authority_boundary():
    _, source = chain(); value = create_production_single_skill_admission_evidence(source)
    assert value.eligibility_allowed and value.lineage_verified and value.evidence_complete
    assert value.governance_evidence_verified
    assert not value.gate_satisfied and not value.admission_input_ready and not value.admitted
    assert not value.runtime_invoked and not value.bridge_invoked and value.executable_output is None
    assert all(getattr(value.authority_boundary, x) is False
               for x in value.authority_boundary.__dataclass_fields__)


def test_deterministic_deepcopy_frozen_and_single_cardinality():
    _, source = chain(); one = create_production_single_skill_admission_evidence(source)
    two = create_production_single_skill_admission_evidence(copy.deepcopy(source))
    assert one == two == copy.deepcopy(one)
    assert one.evidence_id.startswith("production-single-skill-admission-evidence-")
    assert type(one.selected_skill_id) is str
    with pytest.raises(dataclasses.FrozenInstanceError): one.status = "X"


def test_exact_text_payload_and_reference_time():
    _, source = chain(); value = create_production_single_skill_admission_evidence(source)
    assert source.context.user_message == CHANGE
    assert value.payload_digest == source.adapter_integrity.adapter_result.payload.payload_digest
    assert value.payload_text_digest == source.rendered_text_digest == source.authorized_text_digest
    assert "\n" in source.adapter_integrity.adapter_result.payload.text
    assert value.accepted_at_iso == value.delivery_reference_time


def test_decimal_operands_not_coerced():
    _, source = chain(); value = create_production_single_skill_admission_evidence(source)
    assert all(type(x.normalized_value) is Decimal for x in
               source.execution_integrity.execution_request.decision.binding.evidence_snapshot)
    assert value.operand_digests == tuple(x.operand_digest for x in source.ordered_decimal_operands)


@pytest.mark.parametrize("field,value", (
    ("feature_gate_configured_state", True), ("feature_gate_effective_state", True),
    ("feature_gate_default_denied", False), ("feature_gate_name", "OTHER"),
    ("selected_skill_id", "cost.per_unit_calculation.v1"),
    ("turn_digest", "0" * 64), ("reference_time_digest", "0" * 64),
    ("payload_digest", "0" * 64), ("delivery_integrity_digest", "0" * 64)))
def test_invalid_substituted_or_nondefault_source_fails_closed(field, value):
    _, source = chain()
    assert create_production_single_skill_admission_evidence(
        dataclasses.replace(source, **{field: value})) is None


@pytest.mark.parametrize("field,value", (
    ("status", "INVALID_FAIL_CLOSED"), ("gate_satisfied", True),
    ("admission_input_ready", True), ("admitted", True), ("runtime_invoked", True),
    ("bridge_invoked", True), ("delivery_committed", True),
    ("response_candidate_created", True), ("executable_output", "x"),
    ("evidence_id", "x"), ("evidence_digest", "A" * 64),
    ("evidence_digest", "0" * 63), ("evidence_digest", "0" * 65)))
def test_outcome_identity_and_digest_tampering_rejected(field, value):
    _, source = chain(); item = create_production_single_skill_admission_evidence(source)
    assert not verify_production_single_skill_admission_evidence(
        dataclasses.replace(item, **{field: value}))


def test_gate_reason_diagnostic_and_authority_tampering_rejected():
    _, source = chain(); item = create_production_single_skill_admission_evidence(source)
    mutations = (dataclasses.replace(item, gate_results=tuple(reversed(item.gate_results))),
        dataclasses.replace(item, reasons=("X",)), dataclasses.replace(item, diagnostics=("X",)),
        dataclasses.replace(item, authority_boundary=dataclasses.replace(
            item.authority_boundary, admission=True)))
    assert all(not verify_production_single_skill_admission_evidence(x) for x in mutations)


def test_wrong_type_and_injection_shapes_rejected():
    _, source = chain()
    assert create_production_single_skill_admission_evidence(None) is None
    assert create_production_single_skill_admission_evidence({"source": source, "manifest": object()}) is None
    assert not verify_production_single_skill_admission_evidence({"admission_request": object()})


def test_verifier_does_not_rerun_transformations(monkeypatch):
    _, source = chain(); item = create_production_single_skill_admission_evidence(source)
    import brain.business_skill_cost_execution as execution
    import brain.business_skill_cost_result_presenter as presentation
    import brain.business_skill_cost_response_authorization as authorization
    import brain.business_skill_cost_response_adapter as adapter
    import brain.business_skill_cost_response_delivery_qualification as delivery
    for module, name in ((execution, "execute_cost_skill"), (presentation, "present_cost_result"),
        (authorization, "authorize_cost_response"), (adapter, "adapt_authorized_cost_response"),
        (delivery, "qualify_cost_response_delivery")):
        monkeypatch.setattr(module, name, lambda *a, **k: pytest.fail("transformation rerun"))
    assert verify_production_single_skill_admission_evidence(item)


def test_static_isolation_and_no_legacy_or_runtime_imports():
    path = Path(__file__).parents[1] / "brain" / "production_single_skill_admission_evidence.py"
    source = path.read_text(encoding="utf-8"); ast.parse(source)
    forbidden = ("import app", "streamlit", "session_state", "integration_manifest",
        "integration_qualification", "admission_gateway", "runtime_bridge", "handoff",
        "execute_cost_skill", "present_cost_result", "authorize_cost_response",
        "adapt_authorized_cost_response", "qualify_cost_response_delivery", "float(")
    assert not any(token in source for token in forbidden)
