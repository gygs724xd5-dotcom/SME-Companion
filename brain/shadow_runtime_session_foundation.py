"""V5.15.24.7.4.26 canonical immutable shadow runtime sessions.

The module constructs and verifies read-only session artifacts.  It contains no
runtime executor, memory, service, deployment, activation, or rollback adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Iterable, Mapping


VERSION = "5.15.24.7.4.26"
SCHEMA = "shadow-runtime-session/v1"
POLICY_IDENTITY = "canonical-shadow-runtime-session-policy"
POLICY_VERSION = "1"

SESSION_CREATED = "SESSION_CREATED"
SESSION_COMPLETED = "SESSION_COMPLETED"
SESSION_REJECTED = "SESSION_REJECTED"
SESSION_STATUSES = (SESSION_CREATED, SESSION_COMPLETED, SESSION_REJECTED)

ORDERED_CHECKS = (
    "SESSION_TYPE_VERIFIED",
    "SESSION_SCHEMA_VERIFIED",
    "POLICY_TYPE_VERIFIED",
    "POLICY_IDENTITY_VERIFIED",
    "POLICY_DIGEST_VERIFIED",
    "IDENTITY_TYPE_VERIFIED",
    "SESSION_ID_VERIFIED",
    "CREATION_SEQUENCE_VERIFIED",
    "PLANNER_IDENTITY_VERIFIED",
    "SKILL_IDENTITY_VERIFIED",
    "RUNTIME_DRY_RUN_DIGEST_VERIFIED",
    "OPERATIONAL_ACCEPTANCE_DIGEST_VERIFIED",
    "EVIDENCE_DIGEST_VERIFIED",
    "IDENTITY_POLICY_DIGEST_VERIFIED",
    "DUPLICATE_IDENTITY_REJECTED",
    "EXECUTION_NOT_SUPPLIED",
    "ACTIVATION_NOT_SUPPLIED",
    "DEPLOYMENT_NOT_SUPPLIED",
    "ORDERED_CHECKS_VERIFIED",
    "BOUNDARY_FLAGS_VERIFIED",
    "STATUS_VERIFIED",
    "SESSION_DIGEST_VERIFIED",
)

BOUNDARY_FLAGS = (
    "runtime_mutated",
    "business_memory_changed",
    "conversation_memory_changed",
    "deployment_performed",
    "activation_performed",
    "rollback_performed",
    "external_services_called",
    "side_effect_detected",
)

_HEX = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


@dataclass(frozen=True)
class ShadowRuntimeSessionPolicy:
    schema: str
    identity: str
    version: str
    ordered_checks: tuple[str, ...]
    required_false_boundaries: tuple[str, ...]
    allowed_statuses: tuple[str, ...]
    policy_digest: str = ""


@dataclass(frozen=True)
class ShadowRuntimeSessionIdentity:
    session_id: str
    planner_identity: str
    selected_skill_identity: str
    runtime_dry_run_digest: str
    operational_failure_acceptance_digest: str
    evidence_digest: str
    policy_digest: str
    creation_sequence: int


@dataclass(frozen=True)
class ShadowRuntimeSession:
    schema: str
    identity: ShadowRuntimeSessionIdentity
    session_digest: str
    status: str
    runtime_mutated: bool = False
    business_memory_changed: bool = False
    conversation_memory_changed: bool = False
    deployment_performed: bool = False
    activation_performed: bool = False
    rollback_performed: bool = False
    external_services_called: bool = False
    side_effect_detected: bool = False


@dataclass(frozen=True)
class ShadowRuntimeSessionVerifier:
    schema: str
    policy: ShadowRuntimeSessionPolicy
    ordered_checks: tuple[str, ...]
    verifier_digest: str = ""

    def verify(
        self,
        session: Any,
        expected_identity: Any = None,
        existing_sessions: Iterable[Any] = (),
    ) -> bool:
        return verify_shadow_runtime_session(
            session, expected_identity, existing_sessions, self
        )


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if type(value) is dict:
        return [[str(key), _canonical(value[key])] for key in sorted(value)]
    if isinstance(value, Mapping):
        raise ValueError("mutable or substituted mapping")
    if is_dataclass(value) and not isinstance(value, type):
        return [
            [field.name, _canonical(getattr(value, field.name))]
            for field in fields(value)
        ]
    raise ValueError("unsupported session material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(
        _canonical((VERSION, label, value)),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(
        getattr(value, field.name)
        for field in fields(value)
        if field.name not in excluded
    )


def _build_policy() -> ShadowRuntimeSessionPolicy:
    draft = ShadowRuntimeSessionPolicy(
        SCHEMA,
        POLICY_IDENTITY,
        POLICY_VERSION,
        ORDERED_CHECKS,
        BOUNDARY_FLAGS,
        SESSION_STATUSES,
    )
    return replace(
        draft,
        policy_digest=_digest("SESSION_POLICY", _material(draft, "policy_digest")),
    )


CANONICAL_SHADOW_RUNTIME_SESSION_POLICY = _build_policy()


def _build_verifier() -> ShadowRuntimeSessionVerifier:
    draft = ShadowRuntimeSessionVerifier(
        SCHEMA, CANONICAL_SHADOW_RUNTIME_SESSION_POLICY, ORDERED_CHECKS
    )
    return replace(
        draft,
        verifier_digest=_digest("SESSION_VERIFIER", _material(draft, "verifier_digest")),
    )


CANONICAL_SHADOW_RUNTIME_SESSION_VERIFIER = _build_verifier()


def _valid_identifier(value: Any) -> bool:
    return type(value) is str and bool(_IDENTIFIER.fullmatch(value))


def _valid_digest(value: Any) -> bool:
    return type(value) is str and bool(_HEX.fullmatch(value))


def verify_shadow_runtime_session_policy(value: Any) -> bool:
    try:
        return (
            type(value) is ShadowRuntimeSessionPolicy
            and value == CANONICAL_SHADOW_RUNTIME_SESSION_POLICY
            and type(value.ordered_checks) is tuple
            and value.ordered_checks == ORDERED_CHECKS
            and value.required_false_boundaries == BOUNDARY_FLAGS
            and value.allowed_statuses == SESSION_STATUSES
            and _valid_digest(value.policy_digest)
            and value.policy_digest
            == _digest("SESSION_POLICY", _material(value, "policy_digest"))
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def verify_shadow_runtime_session_identity(
    value: Any,
    policy: Any = CANONICAL_SHADOW_RUNTIME_SESSION_POLICY,
) -> bool:
    try:
        return (
            type(value) is ShadowRuntimeSessionIdentity
            and verify_shadow_runtime_session_policy(policy)
            and policy is CANONICAL_SHADOW_RUNTIME_SESSION_POLICY
            and _valid_identifier(value.session_id)
            and _valid_identifier(value.planner_identity)
            and _valid_identifier(value.selected_skill_identity)
            and _valid_digest(value.runtime_dry_run_digest)
            and _valid_digest(value.operational_failure_acceptance_digest)
            and _valid_digest(value.evidence_digest)
            and value.policy_digest == policy.policy_digest
            and type(value.creation_sequence) is int
            and value.creation_sequence >= 0
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _session_digest_material(
    identity: ShadowRuntimeSessionIdentity, status: str
) -> tuple[Any, ...]:
    boundary_flags = tuple((name, False) for name in BOUNDARY_FLAGS)
    return (
        identity.session_id,
        identity.planner_identity,
        identity.selected_skill_identity,
        identity.runtime_dry_run_digest,
        identity.operational_failure_acceptance_digest,
        identity.evidence_digest,
        identity.policy_digest,
        identity.creation_sequence,
        ORDERED_CHECKS,
        boundary_flags,
        status,
    )


def create_shadow_runtime_session(
    identity: Any,
    *,
    execution_requested: bool = False,
    activation_requested: bool = False,
    deployment_requested: bool = False,
) -> ShadowRuntimeSession | None:
    """Create a deterministic artifact without invoking the described runtime."""
    try:
        if not verify_shadow_runtime_session_identity(identity):
            return None
        if any(
            type(value) is not bool or value is not False
            for value in (
                execution_requested,
                activation_requested,
                deployment_requested,
            )
        ):
            return None
        status = SESSION_COMPLETED
        return ShadowRuntimeSession(
            schema=SCHEMA,
            identity=identity,
            session_digest=_digest(
                "SHADOW_RUNTIME_SESSION", _session_digest_material(identity, status)
            ),
            status=status,
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_shadow_runtime_session_verifier(value: Any) -> bool:
    try:
        return (
            type(value) is ShadowRuntimeSessionVerifier
            and value == CANONICAL_SHADOW_RUNTIME_SESSION_VERIFIER
            and value.policy is CANONICAL_SHADOW_RUNTIME_SESSION_POLICY
            and value.ordered_checks == ORDERED_CHECKS
            and _valid_digest(value.verifier_digest)
            and value.verifier_digest
            == _digest("SESSION_VERIFIER", _material(value, "verifier_digest"))
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def _duplicates_identity(
    identity: ShadowRuntimeSessionIdentity, existing_sessions: Iterable[Any]
) -> bool:
    if type(existing_sessions) not in (tuple, list):
        return True
    for existing in existing_sessions:
        if type(existing) is ShadowRuntimeSession:
            other = existing.identity
        elif type(existing) is ShadowRuntimeSessionIdentity:
            other = existing
        else:
            return True
        if (
            other == identity
            or other.session_id == identity.session_id
            or (
                other.planner_identity == identity.planner_identity
                and other.selected_skill_identity == identity.selected_skill_identity
                and other.creation_sequence == identity.creation_sequence
            )
        ):
            return True
    return False


def verify_shadow_runtime_session(
    session: Any,
    expected_identity: Any = None,
    existing_sessions: Iterable[Any] = (),
    verifier: Any = CANONICAL_SHADOW_RUNTIME_SESSION_VERIFIER,
) -> bool:
    try:
        if not verify_shadow_runtime_session_verifier(verifier):
            return False
        if type(session) is not ShadowRuntimeSession:
            return False
        if session.schema != SCHEMA or session.status != SESSION_COMPLETED:
            return False
        if not verify_shadow_runtime_session_identity(session.identity, verifier.policy):
            return False
        if expected_identity is not None and (
            type(expected_identity) is not ShadowRuntimeSessionIdentity
            or session.identity != expected_identity
        ):
            return False
        if _duplicates_identity(session.identity, existing_sessions):
            return False
        if any(
            type(getattr(session, field)) is not bool
            or getattr(session, field) is not False
            for field in BOUNDARY_FLAGS
        ):
            return False
        expected_digest = _digest(
            "SHADOW_RUNTIME_SESSION",
            _session_digest_material(session.identity, session.status),
        )
        return _valid_digest(session.session_digest) and session.session_digest == expected_digest
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "VERSION",
    "SCHEMA",
    "POLICY_IDENTITY",
    "POLICY_VERSION",
    "SESSION_CREATED",
    "SESSION_COMPLETED",
    "SESSION_REJECTED",
    "SESSION_STATUSES",
    "ORDERED_CHECKS",
    "BOUNDARY_FLAGS",
    "ShadowRuntimeSessionPolicy",
    "ShadowRuntimeSessionIdentity",
    "ShadowRuntimeSession",
    "ShadowRuntimeSessionVerifier",
    "CANONICAL_SHADOW_RUNTIME_SESSION_POLICY",
    "CANONICAL_SHADOW_RUNTIME_SESSION_VERIFIER",
    "create_shadow_runtime_session",
    "verify_shadow_runtime_session_policy",
    "verify_shadow_runtime_session_identity",
    "verify_shadow_runtime_session_verifier",
    "verify_shadow_runtime_session",
)
