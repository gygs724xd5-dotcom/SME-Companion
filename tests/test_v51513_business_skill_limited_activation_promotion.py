import dataclasses
import sys

import pytest

from brain.business_skill import CONTRACTED, LIMITED_ACTIVE, SHADOW_AVAILABLE, STABLE
from brain.business_skill_lifecycle_manifest import apply_approved_lifecycle_promotions
from brain.business_skill_limited_activation_manifest import *
from brain.business_skill_registry import (
    BUSINESS_SKILL_REGISTRY_VERSION, build_seed_business_skills, get_business_skill_registry,
)
from brain.business_skill_shadow_availability_manifest import apply_approved_shadow_availability_promotions
from brain.business_skill_shadow_selector import SHADOW_SELECTION_ELIGIBLE_STATUSES


def historical_shadow_registry():
    current = get_business_skill_registry()
    contracted = tuple(dataclasses.replace(
        skill, active_status=CONTRACTED,
        tests_required=tuple(x for x in skill.tests_required if not any(
            marker in x for marker in ("test_v5156_", "test_v5157_", "test_v5158_", "test_v5159_", "test_v51512_", "test_v51513_"))),
    ) for skill in current)
    return apply_approved_shadow_availability_promotions(apply_approved_lifecycle_promotions(contracted))


def test_exact_manifest_registry_counts_audit_and_determinism():
    assert BUSINESS_SKILL_REGISTRY_VERSION == BUSINESS_SKILL_LIMITED_ACTIVATION_MANIFEST_VERSION == "5.15.13"
    assert tuple(x.skill_id for x in APPROVED_LIMITED_ACTIVATION_PROMOTIONS) == APPROVED_LIMITED_ACTIVATION_SKILL_IDS
    assert all((x.from_status, x.to_status) == (SHADOW_AVAILABLE, LIMITED_ACTIVE) for x in APPROVED_LIMITED_ACTIVATION_PROMOTIONS)
    assert validate_limited_activation_manifest()["valid"]
    first = get_business_skill_registry(); second = build_seed_business_skills()
    assert first == second and first is not second
    assert sum(x.active_status == LIMITED_ACTIVE for x in first) == 2
    assert sum(x.active_status == CONTRACTED for x in first) == 8
    assert sum(x.active_status == SHADOW_AVAILABLE for x in first) == 0
    for skill in first[:2]:
        positions = tuple(skill.tests_required.index(ref) for ref in REQUIRED_AUDIT_REFERENCES)
        assert positions == tuple(sorted(positions))
        assert all(skill.tests_required.count(ref) == 1 for ref in REQUIRED_AUDIT_REFERENCES)


def test_positive_pure_application_and_historical_reconstruction():
    source = historical_shadow_registry(); snapshot = repr(source)
    promoted = apply_approved_limited_activation_promotions(source)
    assert promoted == get_business_skill_registry()
    assert repr(source) == snapshot
    with pytest.raises(ValueError):
        apply_approved_limited_activation_promotions(promoted)


def test_frozen_records_and_caller_safety():
    record = APPROVED_LIMITED_ACTIVATION_PROMOTIONS[0]
    with pytest.raises(dataclasses.FrozenInstanceError): record.skill_id = "changed"
    with pytest.raises(dataclasses.FrozenInstanceError): record.qualification.skill_id = "changed"
    caller = list(historical_shadow_registry()); snapshot = tuple(caller)
    apply_approved_limited_activation_promotions(caller)
    assert tuple(caller) == snapshot


@pytest.mark.parametrize("change", [
    {"skill_id": "unknown.v1"}, {"from_status": LIMITED_ACTIVE},
    {"from_status": CONTRACTED}, {"to_status": SHADOW_AVAILABLE},
    {"to_status": STABLE}, {"manifest_version": "5.15.12"},
])
def test_invalid_transition_identity_and_version(change):
    bad = dataclasses.replace(APPROVED_LIMITED_ACTIVATION_PROMOTIONS[0], **change)
    assert not validate_limited_activation_promotion(bad)["valid"]


def test_qualification_and_audit_rejections():
    record = APPROVED_LIMITED_ACTIVATION_PROMOTIONS[0]; q = record.qualification
    variants = (
        dataclasses.replace(record, qualification=None),
        dataclasses.replace(record, qualification=dataclasses.replace(q, skill_id="wrong.v1")),
        dataclasses.replace(record, qualification=dataclasses.replace(q, recommendation="NO")),
        dataclasses.replace(record, qualification=dataclasses.replace(q, gate_results=tuple(dataclasses.replace(g, passed=False) if i == 0 else g for i, g in enumerate(q.gate_results)))),
        dataclasses.replace(record, qualification=dataclasses.replace(q, qualification_id=" bad ")),
        dataclasses.replace(record, qualification=dataclasses.replace(q, reference_time="not-time")),
        dataclasses.replace(record, audit_references=record.audit_references[::-1]),
        dataclasses.replace(record, audit_references=record.audit_references[:-1]),
    )
    assert all(not validate_limited_activation_promotion(x)["valid"] for x in variants)
    duplicate = (record, record)
    assert not validate_limited_activation_manifest(duplicate)["valid"]


def test_diagnostic_only_selector_contract_and_import_boundary():
    assert LIMITED_ACTIVE in SHADOW_SELECTION_ELIGIBLE_STATUSES
    diagnostics = build_limited_activation_promotion_diagnostics(historical_shadow_registry())
    for key in ("authorized", "executed", "reasoning_executed", "calculated", "runtime_routed",
                "tools_invoked", "follow_up_generated", "persisted", "response_committed", "response_generated"):
        assert diagnostics[key] is False
    forbidden = ("app", "brain.business_skill_matcher")
    module = sys.modules[__name__.replace("tests.test_v51513_business_skill_limited_activation_promotion", "brain.business_skill_limited_activation_manifest")]
    source_names = set(module.__dict__)
    assert not any(name in source_names for name in forbidden)
