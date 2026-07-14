"""Canonical UTC reference time bound to one verified production turn."""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any

from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context


PRODUCTION_TURN_REFERENCE_TIME_VERSION = "5.15.24.6.2"
PRODUCTION_TURN_REFERENCE_TIME_SCOPE = "VERIFIED_ACCEPTED_USER_TURN_REFERENCE_TIME"
PRODUCTION_TURN_REFERENCE_TIME_SOURCE = "PRODUCTION_ACCEPTED_TURN_CLOCK"
PRODUCTION_TURN_REFERENCE_TIME_TIMEZONE = "UTC"
PRODUCTION_TURN_REFERENCE_TIME_PRECISION = "SECONDS_0_FRACTIONAL_DIGITS"

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionTurnReferenceTime:
    reference_time_version: str
    reference_time_scope: str
    source_identity: str
    conversation_id: str
    turn_id: str
    turn_digest: str
    accepted_at_utc: datetime
    accepted_at_iso: str
    timezone_identity: str
    precision_identity: str
    captured_once: bool = True
    read_only: bool = True
    caller_override_permitted: bool = False
    routing_authority: bool = False
    planning_authority: bool = False
    skill_selection_authority: bool = False
    response_selection_authority: bool = False
    response_guard_authority: bool = False
    response_resolution_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    limited_activation_authority: bool = False
    controlled_runtime_activation_authority: bool = False
    reference_time_digest: str = ""


_AUTHORITY_FIELDS = tuple(
    field.name for field in fields(ProductionTurnReferenceTime)
    if field.name.endswith("_authority")
)


def canonicalize_accepted_turn_time(value: Any) -> tuple[datetime, str]:
    """Return the fixed UTC/seconds representation; reject naive/non-UTC input."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("accepted_at must be a timezone-aware datetime")
    if value.tzinfo is not timezone.utc or value.utcoffset() != timedelta(0):
        raise ValueError("accepted_at must be UTC")
    canonical = value.astimezone(timezone.utc).replace(microsecond=0)
    return canonical, canonical.isoformat(timespec="seconds")


def compute_production_turn_reference_time_digest(
    reference_time_version: Any,
    reference_time_scope: Any,
    source_identity: Any,
    conversation_id: Any,
    turn_id: Any,
    turn_digest: Any,
    accepted_at_iso: Any,
    timezone_identity: Any,
    precision_identity: Any,
    captured_once: Any,
    read_only: Any,
    caller_override_permitted: Any,
    authority_flags: Any,
) -> str:
    try:
        material = (
            "PRODUCTION_TURN_REFERENCE_TIME_DIGEST",
            reference_time_version, reference_time_scope, source_identity,
            conversation_id, turn_id, turn_digest, accepted_at_iso,
            timezone_identity, precision_identity, captured_once, read_only,
            caller_override_permitted, tuple(authority_flags),
        )
        encoded = json.dumps(material, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
    except (TypeError, ValueError, UnicodeEncodeError):
        return ""


def _digest(value: ProductionTurnReferenceTime) -> str:
    return compute_production_turn_reference_time_digest(
        value.reference_time_version, value.reference_time_scope, value.source_identity,
        value.conversation_id, value.turn_id, value.turn_digest, value.accepted_at_iso,
        value.timezone_identity, value.precision_identity, value.captured_once,
        value.read_only, value.caller_override_permitted,
        tuple((name, getattr(value, name)) for name in _AUTHORITY_FIELDS),
    )


def create_production_turn_reference_time(
    context: Any,
    accepted_at: Any,
) -> ProductionTurnReferenceTime:
    if not verify_production_turn_context(context):
        raise ValueError("verified ProductionTurnContext required")
    canonical_time, canonical_iso = canonicalize_accepted_turn_time(accepted_at)
    draft = ProductionTurnReferenceTime(
        PRODUCTION_TURN_REFERENCE_TIME_VERSION,
        PRODUCTION_TURN_REFERENCE_TIME_SCOPE,
        PRODUCTION_TURN_REFERENCE_TIME_SOURCE,
        context.conversation_id,
        context.turn_id,
        context.turn_digest,
        canonical_time,
        canonical_iso,
        PRODUCTION_TURN_REFERENCE_TIME_TIMEZONE,
        PRODUCTION_TURN_REFERENCE_TIME_PRECISION,
    )
    return replace(draft, reference_time_digest=_digest(draft))


def verify_production_turn_reference_time(context: Any, artifact: Any) -> bool:
    try:
        if not verify_production_turn_context(context) or type(artifact) is not ProductionTurnReferenceTime:
            return False
        if (artifact.reference_time_version, artifact.reference_time_scope, artifact.source_identity) != (
            PRODUCTION_TURN_REFERENCE_TIME_VERSION,
            PRODUCTION_TURN_REFERENCE_TIME_SCOPE,
            PRODUCTION_TURN_REFERENCE_TIME_SOURCE,
        ):
            return False
        if (artifact.conversation_id, artifact.turn_id, artifact.turn_digest) != (
            context.conversation_id, context.turn_id, context.turn_digest,
        ):
            return False
        if (artifact.timezone_identity, artifact.precision_identity) != (
            PRODUCTION_TURN_REFERENCE_TIME_TIMEZONE,
            PRODUCTION_TURN_REFERENCE_TIME_PRECISION,
        ):
            return False
        canonical_time, canonical_iso = canonicalize_accepted_turn_time(artifact.accepted_at_utc)
        if artifact.accepted_at_utc != canonical_time or artifact.accepted_at_iso != canonical_iso:
            return False
        if artifact.captured_once is not True or artifact.read_only is not True:
            return False
        if artifact.caller_override_permitted is not False:
            return False
        if any(type(getattr(artifact, name)) is not bool or getattr(artifact, name)
               for name in _AUTHORITY_FIELDS):
            return False
        return (type(artifact.reference_time_digest) is str
                and _DIGEST.fullmatch(artifact.reference_time_digest) is not None
                and artifact.reference_time_digest == _digest(artifact))
    except (AttributeError, TypeError, ValueError):
        return False
