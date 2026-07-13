"""Immutable identity and provenance for one accepted production user turn."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any


PRODUCTION_TURN_CONTEXT_VERSION = "5.15.24.1"
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionTurnContext:
    context_version: str
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    user_message: str
    user_message_digest: str
    routing_authority: bool = False
    planning_authority: bool = False
    response_selection_authority: bool = False
    response_guard_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    controlled_runtime_activation_authority: bool = False
    turn_digest: str = ""


_AUTHORITY_FIELDS = (
    "routing_authority",
    "planning_authority",
    "response_selection_authority",
    "response_guard_authority",
    "response_commit_authority",
    "persistence_authority",
    "tool_execution_authority",
    "feature_gate_mutation_authority",
    "controlled_runtime_activation_authority",
)


def _sha256(material: Any) -> str:
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_user_message_digest(message: Any) -> str:
    """Bind the exact accepted string, including whitespace and newlines."""
    if type(message) is not str or not message:
        return ""
    return _sha256(("PRODUCTION_USER_MESSAGE", PRODUCTION_TURN_CONTEXT_VERSION, message))


def compute_turn_digest(
    conversation_id: Any,
    turn_id: Any,
    turn_ordinal: Any,
    user_message_digest: Any,
) -> str:
    if (
        type(conversation_id) is not str
        or not _IDENTITY.fullmatch(conversation_id)
        or type(turn_id) is not str
        or not _IDENTITY.fullmatch(turn_id)
        or type(turn_ordinal) is not int
        or isinstance(turn_ordinal, bool)
        or turn_ordinal < 1
        or type(user_message_digest) is not str
        or not _DIGEST.fullmatch(user_message_digest)
    ):
        return ""
    return _sha256((
        "PRODUCTION_TURN_CONTEXT",
        PRODUCTION_TURN_CONTEXT_VERSION,
        conversation_id,
        turn_id,
        turn_ordinal,
        user_message_digest,
    ))


def create_production_turn_context(
    conversation_id: Any,
    turn_ordinal: Any,
    user_message: Any,
) -> ProductionTurnContext:
    if type(conversation_id) is not str or not _IDENTITY.fullmatch(conversation_id):
        raise ValueError("conversation_id must be a canonical production identity")
    if type(turn_ordinal) is not int or isinstance(turn_ordinal, bool) or turn_ordinal < 1:
        raise ValueError("turn_ordinal must be a positive integer")
    if type(user_message) is not str or not user_message:
        raise ValueError("user_message must be an accepted non-empty production input")
    turn_id = f"turn-{turn_ordinal}"
    message_digest = compute_user_message_digest(user_message)
    draft = ProductionTurnContext(
        context_version=PRODUCTION_TURN_CONTEXT_VERSION,
        conversation_id=conversation_id,
        turn_id=turn_id,
        turn_ordinal=turn_ordinal,
        user_message=user_message,
        user_message_digest=message_digest,
    )
    return replace(
        draft,
        turn_digest=compute_turn_digest(conversation_id, turn_id, turn_ordinal, message_digest),
    )


def verify_production_turn_context(value: Any) -> bool:
    try:
        if type(value) is not ProductionTurnContext:
            return False
        if value.context_version != PRODUCTION_TURN_CONTEXT_VERSION:
            return False
        if any(type(getattr(value, name)) is not bool or getattr(value, name) for name in _AUTHORITY_FIELDS):
            return False
        expected = create_production_turn_context(
            value.conversation_id,
            value.turn_ordinal,
            value.user_message,
        )
        return value == expected
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def resolve_production_turn_context(
    current: Any,
    conversation_id: Any,
    turn_ordinal: Any,
    user_message: Any,
) -> ProductionTurnContext:
    """Reuse only the exact current event; otherwise create its canonical context."""
    expected = create_production_turn_context(conversation_id, turn_ordinal, user_message)
    if verify_production_turn_context(current) and current == expected:
        return current
    return expected
