from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

import brain.shadow_runtime_session_foundation as shadow


MODULE = Path(__file__).resolve().parents[1] / "brain" / "shadow_runtime_session_foundation.py"


@pytest.fixture
def identity():
    return shadow.ShadowRuntimeSessionIdentity(
        session_id="shadow-session/0001",
        planner_identity="canonical-planner/v1",
        selected_skill_identity="business-skill/cost-analysis/v1",
        runtime_dry_run_digest="1" * 64,
        operational_failure_acceptance_digest="2" * 64,
        evidence_digest="3" * 64,
        policy_digest=shadow.CANONICAL_SHADOW_RUNTIME_SESSION_POLICY.policy_digest,
        creation_sequence=1,
    )


@pytest.fixture
def session(identity):
    value = shadow.create_shadow_runtime_session(identity)
    assert value is not None
    return value


def test_positive_session_and_digest_determinism(identity, session):
    duplicate = shadow.create_shadow_runtime_session(identity)
    assert duplicate == session
    assert duplicate.session_digest == session.session_digest
    assert session.status == shadow.SESSION_COMPLETED
    assert shadow.verify_shadow_runtime_session(session, identity)


@pytest.mark.parametrize(
    "field,value",
    (
        ("planner_identity", "other-planner/v1"),
        ("selected_skill_identity", "other-skill/v1"),
        ("runtime_dry_run_digest", "4" * 64),
        ("evidence_digest", "5" * 64),
        ("operational_failure_acceptance_digest", "6" * 64),
        ("policy_digest", "7" * 64),
    ),
)
def test_identity_mismatches_are_rejected(identity, session, field, value):
    mismatched = dataclasses.replace(identity, **{field: value})
    assert not shadow.verify_shadow_runtime_session(session, mismatched)
    if field == "policy_digest":
        assert shadow.create_shadow_runtime_session(mismatched) is None


def test_schema_and_digest_mismatches_are_rejected(session):
    assert not shadow.verify_shadow_runtime_session(
        dataclasses.replace(session, schema="wrong/schema")
    )
    assert not shadow.verify_shadow_runtime_session(
        dataclasses.replace(session, session_digest="8" * 64)
    )


@pytest.mark.parametrize("value", ({}, [], set(), object(), None))
def test_mutable_substitution_is_rejected(value):
    assert shadow.create_shadow_runtime_session(value) is None
    assert not shadow.verify_shadow_runtime_session(value)


def test_subclass_substitution_is_rejected(identity, session):
    class IdentitySpoof(shadow.ShadowRuntimeSessionIdentity):
        pass

    class SessionSpoof(shadow.ShadowRuntimeSession):
        pass

    spoof_identity = IdentitySpoof(
        **{field.name: getattr(identity, field.name) for field in dataclasses.fields(identity)}
    )
    spoof_session = SessionSpoof(
        **{field.name: getattr(session, field.name) for field in dataclasses.fields(session)}
    )
    assert shadow.create_shadow_runtime_session(spoof_identity) is None
    assert not shadow.verify_shadow_runtime_session(spoof_session)


def test_duplicate_session_identity_is_rejected(identity, session):
    assert not shadow.verify_shadow_runtime_session(session, existing_sessions=(session,))
    assert not shadow.verify_shadow_runtime_session(session, existing_sessions=(identity,))
    colliding = dataclasses.replace(identity, evidence_digest="9" * 64)
    assert not shadow.verify_shadow_runtime_session(
        shadow.create_shadow_runtime_session(colliding),
        existing_sessions=(session,),
    )


@pytest.mark.parametrize("field", shadow.BOUNDARY_FLAGS)
def test_boundary_verification(identity, session, field):
    assert getattr(session, field) is False
    assert not shadow.verify_shadow_runtime_session(
        dataclasses.replace(session, **{field: True}), identity
    )


@pytest.mark.parametrize(
    "argument",
    ("execution_requested", "activation_requested", "deployment_requested"),
)
def test_caller_supplied_authority_is_rejected(identity, argument):
    assert shadow.create_shadow_runtime_session(identity, **{argument: True}) is None


def test_policy_verifier_and_frozen_contracts(identity, session):
    policy = shadow.CANONICAL_SHADOW_RUNTIME_SESSION_POLICY
    verifier = shadow.CANONICAL_SHADOW_RUNTIME_SESSION_VERIFIER
    assert shadow.verify_shadow_runtime_session_policy(policy)
    assert shadow.verify_shadow_runtime_session_verifier(verifier)
    assert not shadow.verify_shadow_runtime_session_policy(
        dataclasses.replace(policy, identity="forged-policy")
    )
    assert len(shadow.ORDERED_CHECKS) >= 16
    assert len(set(shadow.ORDERED_CHECKS)) == len(shadow.ORDERED_CHECKS)
    for value in (policy, identity, session, verifier):
        assert value.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        session.runtime_mutated = True


def test_only_canonical_statuses_and_static_non_operational_surface():
    assert shadow.SESSION_STATUSES == (
        "SESSION_CREATED",
        "SESSION_COMPLETED",
        "SESSION_REJECTED",
    )
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {
        "os", "pathlib", "socket", "subprocess", "requests", "urllib",
        "uuid", "random", "datetime",
    }.isdisjoint(imported)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
        for node in ast.walk(tree)
    )
    for forbidden in ("ACTIVE", "EXECUTING", "DEPLOYED"):
        assert forbidden not in source
