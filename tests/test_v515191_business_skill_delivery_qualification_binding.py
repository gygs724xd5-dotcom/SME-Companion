"""V5.15.19.1 immutable delivery qualification binding tests."""
import dataclasses
from pathlib import Path

import pytest

from brain.business_skill_cost_response_delivery_qualification import *
from tests.test_v51519_business_skill_cost_response_delivery_qualification import NOW, make


def qualified(skill="cost.change_analysis.v1", suffix="1"):
    return qualify_cost_response_delivery((make(skill, suffix),), qualification_id="qual1",
                                            reference_time=NOW).results[0]


def test_versions_exact_schema_and_both_skills_are_bound():
    assert HISTORICAL_COST_DELIVERY_QUALIFICATION_VERSION == "5.15.19"
    assert COST_DELIVERY_QUALIFICATION_VERSION == QUALIFICATION_VERSION == "5.15.19.1"
    for skill, suffix in (("cost.change_analysis.v1", "1"),
                          ("cost.per_unit_calculation.v1", "2")):
        result = qualified(skill, suffix)
        binding = result.binding
        assert binding.skill_id == binding.payload_skill_id == skill
        assert binding.payload_digest == make(skill, suffix).adapter_result.payload.payload_digest
        assert verify_cost_delivery_qualification_binding(binding)
        assert verify_cost_delivery_qualification_result_integrity(result)


@pytest.mark.parametrize("field,value", (
    ("binding_schema_version", "5.15.19"), ("qualification_version", "5.15.19"),
    ("qualification_id", "other"), ("reference_time", "2026-07-12T13:00:00+07:00"),
    ("case_id", "other"), ("skill_id", "cost.per_unit_calculation.v1"),
    ("adapter_version", "5.15.17"), ("adapter_request_id", "other"),
    ("adapter_outcome", "OTHER"), ("payload_digest", "0" * 64),
    ("payload_authorization_id", "other"), ("payload_presentation_id", "other"),
    ("payload_execution_id", "other"), ("payload_request_id", "other"),
    ("payload_skill_id", "cost.per_unit_calculation.v1"),
    ("presentation_digest", "0" * 64), ("draft_digest", "0" * 64),
    ("scope", "GLOBAL"), ("locale", "en-US"), ("target_channel", "OTHER"),
    ("output_mode", "OTHER"), ("recommendation", "OTHER"),
    ("reason_codes", ("OTHER",)), ("response_generated", True),
    ("qualification_digest", "0" * 64), ("qualification_digest", "a" * 63),
    ("qualification_digest", "G" * 64), ("qualification_digest", "A" * 64),
))
def test_binding_tamper_fails_closed(field, value):
    assert not verify_cost_delivery_qualification_binding(
        dataclasses.replace(qualified().binding, **{field: value}))


def test_gate_snapshot_status_reason_order_and_top_level_result_tamper():
    result = qualified()
    snapshot = result.binding.gate_snapshot
    mutations = (
        snapshot[::-1],
        ((snapshot[0][0], False, snapshot[0][2]),) + snapshot[1:],
        ((snapshot[0][0], True, ("OTHER",)),) + snapshot[1:],
        ((snapshot[1][0], True, snapshot[0][2]),) + snapshot[1:],
    )
    assert all(not verify_cost_delivery_qualification_binding(
        dataclasses.replace(result.binding, gate_snapshot=x)) for x in mutations)
    assert not verify_cost_delivery_qualification_result_integrity(
        dataclasses.replace(result, qualification_id="other"))
    assert not verify_cost_delivery_qualification_result_integrity(
        dataclasses.replace(result, reason_codes=("OTHER",)))
    assert not verify_cost_delivery_qualification_result_integrity(
        dataclasses.replace(result, binding=None))


def test_denied_result_has_no_binding_and_verifies():
    case = dataclasses.replace(make(), response_committed=True)
    result = qualify_cost_response_delivery((case,), qualification_id="qual1", reference_time=NOW).results[0]
    assert result.binding is None and verify_cost_delivery_qualification_result_integrity(result)


def test_cross_request_same_skill_cross_skill_and_payload_substitution_detected():
    one, two = qualified(suffix="1"), qualified(suffix="2")
    assert not verify_cost_delivery_qualification_result_integrity(dataclasses.replace(one, binding=two.binding))
    other = qualified("cost.per_unit_calculation.v1", "3")
    assert not verify_cost_delivery_qualification_result_integrity(dataclasses.replace(one, binding=other.binding))
    forged = dataclasses.replace(one.binding, payload_digest=two.binding.payload_digest)
    assert not verify_cost_delivery_qualification_binding(forged)


def test_source_mutation_does_not_mutate_binding_and_verification_is_deterministic():
    case = make()
    result = qualify_cost_response_delivery((case,), qualification_id="qual1", reference_time=NOW).results[0]
    before = result.binding
    replaced = dataclasses.replace(case.adapter_result.payload, text="changed")
    dataclasses.replace(case, adapter_result=dataclasses.replace(case.adapter_result, payload=replaced))
    assert result.binding == before
    assert verify_cost_delivery_qualification_result_integrity(result)
    assert verify_cost_delivery_qualification_result_integrity(result)


def test_no_upstream_rerun_or_runtime_authority_imports():
    source = (Path(__file__).parents[1] / "brain" /
              "business_skill_cost_response_delivery_qualification.py").read_text(encoding="utf-8")
    forbidden = ("import app", "import router", "import planner", "import workflow",
                 "adapt_authorized_cost_response(", "authorize_cost_response(",
                 "execute_cost_skill(", "present_cost_result(")
    assert all(token not in source for token in forbidden)
    assert "signature/MAC, replay defence, or proof against untrusted artifact fabrication" in source
