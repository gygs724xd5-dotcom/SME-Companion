"""Immutable evidence for a response proposal bound to a verified user turn."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any

from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context


PRODUCTION_RESPONSE_CANDIDATE_VERSION = "5.15.24.2"
TURN_BOUND_RESPONSE_CANDIDATE_SCOPE = "VERIFIED_USER_TURN_RESPONSE"
PROVISIONAL = "PROVISIONAL"

RESPONSE_PROPOSAL = "RESPONSE_PROPOSAL"
FALLBACK_PROPOSAL = "FALLBACK_PROPOSAL"
ERROR_FALLBACK_PROPOSAL = "ERROR_FALLBACK_PROPOSAL"

RESET = "RESET"
TEMPORARY_INTERRUPT = "TEMPORARY_INTERRUPT"
WORKFLOW = "WORKFLOW"
DIRECT_ANSWER = "DIRECT_ANSWER"
STRUCTURED_RUNTIME = "STRUCTURED_RUNTIME"
PLANNER_FIRST = "PLANNER_FIRST"
CLARIFICATION = "CLARIFICATION"
GENERAL_RESPONSE = "GENERAL_RESPONSE"
SIMPLE_FOLLOWUP = "SIMPLE_FOLLOWUP"
PRODUCT_FEEDBACK = "PRODUCT_FEEDBACK"
LEGACY_GUARDED = "LEGACY_GUARDED"
EXCEPTION_FALLBACK = "EXCEPTION_FALLBACK"

ORIGIN_KIND_REGISTRY = MappingProxyType({
    RESET: RESPONSE_PROPOSAL,
    TEMPORARY_INTERRUPT: RESPONSE_PROPOSAL,
    WORKFLOW: RESPONSE_PROPOSAL,
    DIRECT_ANSWER: RESPONSE_PROPOSAL,
    STRUCTURED_RUNTIME: RESPONSE_PROPOSAL,
    PLANNER_FIRST: RESPONSE_PROPOSAL,
    CLARIFICATION: RESPONSE_PROPOSAL,
    GENERAL_RESPONSE: FALLBACK_PROPOSAL,
    SIMPLE_FOLLOWUP: RESPONSE_PROPOSAL,
    PRODUCT_FEEDBACK: RESPONSE_PROPOSAL,
    LEGACY_GUARDED: RESPONSE_PROPOSAL,
    EXCEPTION_FALLBACK: ERROR_FALLBACK_PROPOSAL,
})

# These are event classes, not candidate origins. They are deliberately outside
# the turn-bound contract and may not be extended silently by callers.
EXCLUDED_RESPONSE_EVENT_CLASSES = (
    "UI_ACTION_RESPONSE",
    "PRE_TURN_EXCEPTION_RESPONSE",
    "NON_CHAT_UI_RENDERING",
    "NON_TURN_AUTH_STORE_DEMO_UI_EVENT",
)

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True)
class ProductionResponseCandidate:
    candidate_version: str
    candidate_scope: str
    conversation_id: str
    turn_id: str
    turn_digest: str
    candidate_id: str
    candidate_origin: str
    candidate_kind: str
    candidate_ordinal: int
    response_text: str
    response_text_digest: str
    source_artifact_digest: str | None = None
    workflow_identity: str | None = None
    intent_identity: str | None = None
    topic_identity: str | None = None
    status: str = PROVISIONAL
    routing_authority: bool = False
    planning_authority: bool = False
    final_response_selection_authority: bool = False
    response_guarding_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    controlled_runtime_activation_authority: bool = False
    candidate_digest: str = ""


_AUTHORITY_FIELDS = tuple(
    name for name in ProductionResponseCandidate.__dataclass_fields__ if name.endswith("_authority")
)


def _sha256(material: Any) -> str:
    encoded = json.dumps(material, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_response_text_digest(response_text: Any) -> str:
    if type(response_text) is not str:
        return ""
    return _sha256(("PRODUCTION_RESPONSE_TEXT", PRODUCTION_RESPONSE_CANDIDATE_VERSION, response_text))


def _optional_identity(value: Any) -> bool:
    return value is None or (type(value) is str and bool(value) and len(value) <= 256)


def _candidate_id_material(
    context: ProductionTurnContext,
    origin: str,
    kind: str,
    ordinal: int,
    response_text_digest: str,
) -> tuple[Any, ...]:
    return (
        "PRODUCTION_RESPONSE_CANDIDATE_ID",
        PRODUCTION_RESPONSE_CANDIDATE_VERSION,
        TURN_BOUND_RESPONSE_CANDIDATE_SCOPE,
        context.turn_digest,
        origin,
        kind,
        ordinal,
        response_text_digest,
    )


def compute_response_candidate_digest(candidate: Any) -> str:
    if type(candidate) is not ProductionResponseCandidate:
        return ""
    material = tuple(
        getattr(candidate, field)
        for field in ProductionResponseCandidate.__dataclass_fields__
        if field != "candidate_digest"
    )
    try:
        return _sha256(("PRODUCTION_RESPONSE_CANDIDATE", material))
    except (TypeError, ValueError, UnicodeEncodeError):
        return ""


def create_production_response_candidate(
    context: Any,
    candidate_origin: Any,
    candidate_kind: Any,
    response_text: Any,
    *,
    candidate_ordinal: int = 1,
    source_artifact_digest: str | None = None,
    workflow_identity: str | None = None,
    intent_identity: str | None = None,
    topic_identity: str | None = None,
) -> ProductionResponseCandidate:
    if not verify_production_turn_context(context):
        raise ValueError("context must be a verified ProductionTurnContext")
    if type(candidate_origin) is not str or ORIGIN_KIND_REGISTRY.get(candidate_origin) != candidate_kind:
        raise ValueError("candidate origin/kind must match the canonical registry")
    if type(response_text) is not str:
        raise ValueError("response_text must be the exact proposal string")
    if type(candidate_ordinal) is not int or isinstance(candidate_ordinal, bool) or candidate_ordinal != 1:
        raise ValueError("candidate_ordinal must be canonical for this origin boundary")
    if source_artifact_digest is not None and (
        type(source_artifact_digest) is not str or not _DIGEST.fullmatch(source_artifact_digest)
    ):
        raise ValueError("source_artifact_digest must be canonical or None")
    if not all(_optional_identity(value) for value in (workflow_identity, intent_identity, topic_identity)):
        raise ValueError("optional identities must be canonical or None")
    text_digest = compute_response_text_digest(response_text)
    candidate_id = "response-candidate-" + _sha256(
        _candidate_id_material(context, candidate_origin, candidate_kind, candidate_ordinal, text_digest)
    )
    draft = ProductionResponseCandidate(
        candidate_version=PRODUCTION_RESPONSE_CANDIDATE_VERSION,
        candidate_scope=TURN_BOUND_RESPONSE_CANDIDATE_SCOPE,
        conversation_id=context.conversation_id,
        turn_id=context.turn_id,
        turn_digest=context.turn_digest,
        candidate_id=candidate_id,
        candidate_origin=candidate_origin,
        candidate_kind=candidate_kind,
        candidate_ordinal=candidate_ordinal,
        response_text=response_text,
        response_text_digest=text_digest,
        source_artifact_digest=source_artifact_digest,
        workflow_identity=workflow_identity,
        intent_identity=intent_identity,
        topic_identity=topic_identity,
    )
    return replace(draft, candidate_digest=compute_response_candidate_digest(draft))


def verify_production_response_candidate(candidate: Any, context: Any) -> bool:
    try:
        if type(candidate) is not ProductionResponseCandidate or not verify_production_turn_context(context):
            return False
        if candidate.candidate_version != PRODUCTION_RESPONSE_CANDIDATE_VERSION:
            return False
        if candidate.candidate_scope != TURN_BOUND_RESPONSE_CANDIDATE_SCOPE:
            return False
        if candidate.status != PROVISIONAL:
            return False
        if any(type(getattr(candidate, name)) is not bool or getattr(candidate, name) for name in _AUTHORITY_FIELDS):
            return False
        if candidate.candidate_origin not in ORIGIN_KIND_REGISTRY:
            return False
        if ORIGIN_KIND_REGISTRY[candidate.candidate_origin] != candidate.candidate_kind:
            return False
        if type(candidate.response_text) is not str:
            return False
        if candidate.candidate_ordinal != 1 or isinstance(candidate.candidate_ordinal, bool):
            return False
        if candidate.conversation_id != context.conversation_id:
            return False
        if candidate.turn_id != context.turn_id or candidate.turn_digest != context.turn_digest:
            return False
        expected = create_production_response_candidate(
            context,
            candidate.candidate_origin,
            candidate.candidate_kind,
            candidate.response_text,
            candidate_ordinal=candidate.candidate_ordinal,
            source_artifact_digest=candidate.source_artifact_digest,
            workflow_identity=candidate.workflow_identity,
            intent_identity=candidate.intent_identity,
            topic_identity=candidate.topic_identity,
        )
        return candidate == expected
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False
