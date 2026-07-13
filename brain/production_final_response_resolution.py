"""Immutable evidence binding the exact resolved text for a verified response candidate."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any

from brain.production_response_candidate import (
    EXCEPTION_FALLBACK,
    LEGACY_GUARDED,
    ORIGIN_KIND_REGISTRY,
    ProductionResponseCandidate,
    verify_production_response_candidate,
)
from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context


PRODUCTION_FINAL_RESPONSE_RESOLUTION_VERSION = "5.15.24.3"
TURN_BOUND_FINAL_RESPONSE_RESOLUTION_SCOPE = "VERIFIED_USER_TURN_RESPONSE"
FINAL_TEXT_RESOLVED = "FINAL_TEXT_RESOLVED"


class FinalResolutionPolicy(str, Enum):
    PASS_THROUGH = "PASS_THROUGH"
    LEGACY_RESPONSE_GUARD = "LEGACY_RESPONSE_GUARD"
    TURN_BOUND_EXCEPTION_FALLBACK = "TURN_BOUND_EXCEPTION_FALLBACK"


PASS_THROUGH = FinalResolutionPolicy.PASS_THROUGH
LEGACY_RESPONSE_GUARD = FinalResolutionPolicy.LEGACY_RESPONSE_GUARD
TURN_BOUND_EXCEPTION_FALLBACK = FinalResolutionPolicy.TURN_BOUND_EXCEPTION_FALLBACK

ORIGIN_RESOLUTION_POLICY_REGISTRY = MappingProxyType({
    origin: (
        LEGACY_RESPONSE_GUARD if origin == LEGACY_GUARDED
        else TURN_BOUND_EXCEPTION_FALLBACK if origin == EXCEPTION_FALLBACK
        else PASS_THROUGH
    )
    for origin in ORIGIN_KIND_REGISTRY
})

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionFinalResponseResolution:
    resolution_version: str
    resolution_scope: str
    conversation_id: str
    turn_id: str
    turn_digest: str
    candidate_id: str
    candidate_digest: str
    candidate_origin: str
    resolution_policy: FinalResolutionPolicy
    candidate_text_digest: str
    resolved_text: str
    resolved_text_digest: str
    text_changed: bool
    guard_applied: bool
    fallback_applied: bool
    resolution_reason: str
    diagnostics: tuple[str, ...]
    status: str = FINAL_TEXT_RESOLVED
    final_text_resolved: bool = True
    provisional: bool = False
    committed: bool = False
    delivered: bool = False
    routing_authority: bool = False
    planning_authority: bool = False
    candidate_creation_authority: bool = False
    candidate_selection_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    controlled_runtime_activation_authority: bool = False
    resolution_digest: str = ""


_AUTHORITY_FIELDS = tuple(
    name for name in ProductionFinalResponseResolution.__dataclass_fields__ if name.endswith("_authority")
)


def _sha256(material: Any) -> str:
    encoded = json.dumps(material, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_resolution_policy_for_origin(origin: Any) -> FinalResolutionPolicy | None:
    return ORIGIN_RESOLUTION_POLICY_REGISTRY.get(origin) if type(origin) is str else None


def compute_resolved_text_digest(resolved_text: Any) -> str:
    if type(resolved_text) is not str:
        return ""
    return _sha256(("PRODUCTION_FINAL_RESPONSE_TEXT", PRODUCTION_FINAL_RESPONSE_RESOLUTION_VERSION, resolved_text))


def compute_final_resolution_digest(resolution: Any) -> str:
    if type(resolution) is not ProductionFinalResponseResolution:
        return ""
    material = tuple(
        getattr(resolution, field)
        for field in ProductionFinalResponseResolution.__dataclass_fields__
        if field != "resolution_digest"
    )
    try:
        return _sha256((
            "PRODUCTION_FINAL_RESPONSE_RESOLUTION",
            PRODUCTION_FINAL_RESPONSE_RESOLUTION_VERSION,
            material,
        ))
    except (TypeError, ValueError, UnicodeEncodeError):
        return ""


def create_production_final_response_resolution(
    context: Any,
    candidate: Any,
    *,
    resolved_text: Any = None,
    existing_guard_applied: Any = False,
) -> ProductionFinalResponseResolution:
    """Create evidence only; policy is always derived from the candidate origin."""
    if not verify_production_turn_context(context):
        raise ValueError("context must be a verified ProductionTurnContext")
    if not verify_production_response_candidate(candidate, context):
        raise ValueError("candidate must be verified for the current context")
    policy = get_resolution_policy_for_origin(candidate.candidate_origin)
    if policy is None:
        raise ValueError("candidate origin has no canonical resolution policy")
    if type(existing_guard_applied) is not bool:
        raise ValueError("existing_guard_applied must be boolean")

    if policy is PASS_THROUGH:
        if resolved_text is not None or existing_guard_applied:
            raise ValueError("pass-through resolution accepts no transformed text or guard evidence")
        final_text = candidate.response_text
        guard_applied = False
        fallback_applied = False
        reason = "CANONICAL_CANDIDATE_TEXT_IS_FINAL"
        diagnostics = ("PASS_THROUGH_EXACT_TEXT",)
    elif policy is LEGACY_RESPONSE_GUARD:
        if type(resolved_text) is not str or not existing_guard_applied:
            raise ValueError("legacy resolution requires exact output from the existing guard sequence")
        final_text = resolved_text
        guard_applied = True
        fallback_applied = False
        reason = "EXISTING_LEGACY_RESPONSE_GUARD_RESULT"
        diagnostics = ("LEGACY_GUARD_CALLED_ONCE_BY_APP", "EXACT_POST_GUARD_TEXT")
    else:
        if resolved_text is not None or existing_guard_applied:
            raise ValueError("exception fallback is canonically bound to its candidate text")
        final_text = candidate.response_text
        guard_applied = False
        fallback_applied = True
        reason = "VERIFIED_TURN_BOUND_EXCEPTION_FALLBACK"
        diagnostics = ("DIRECT_APPEND_SEMANTICS_PRESERVED",)

    draft = ProductionFinalResponseResolution(
        resolution_version=PRODUCTION_FINAL_RESPONSE_RESOLUTION_VERSION,
        resolution_scope=TURN_BOUND_FINAL_RESPONSE_RESOLUTION_SCOPE,
        conversation_id=context.conversation_id,
        turn_id=context.turn_id,
        turn_digest=context.turn_digest,
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.candidate_digest,
        candidate_origin=candidate.candidate_origin,
        resolution_policy=policy,
        candidate_text_digest=candidate.response_text_digest,
        resolved_text=final_text,
        resolved_text_digest=compute_resolved_text_digest(final_text),
        text_changed=final_text != candidate.response_text,
        guard_applied=guard_applied,
        fallback_applied=fallback_applied,
        resolution_reason=reason,
        diagnostics=diagnostics,
    )
    return replace(draft, resolution_digest=compute_final_resolution_digest(draft))


def verify_production_final_response_resolution(resolution: Any, candidate: Any, context: Any) -> bool:
    try:
        if type(resolution) is not ProductionFinalResponseResolution:
            return False
        if not verify_production_turn_context(context) or not verify_production_response_candidate(candidate, context):
            return False
        if resolution.resolution_version != PRODUCTION_FINAL_RESPONSE_RESOLUTION_VERSION:
            return False
        if resolution.resolution_scope != TURN_BOUND_FINAL_RESPONSE_RESOLUTION_SCOPE:
            return False
        if resolution.status != FINAL_TEXT_RESOLVED or resolution.final_text_resolved is not True:
            return False
        if resolution.provisional is not False or resolution.committed is not False or resolution.delivered is not False:
            return False
        if any(type(getattr(resolution, name)) is not bool or getattr(resolution, name) for name in _AUTHORITY_FIELDS):
            return False
        if resolution.conversation_id != context.conversation_id:
            return False
        if resolution.turn_id != context.turn_id or resolution.turn_digest != context.turn_digest:
            return False
        if resolution.candidate_id != candidate.candidate_id or resolution.candidate_digest != candidate.candidate_digest:
            return False
        if resolution.candidate_origin != candidate.candidate_origin:
            return False
        if resolution.candidate_text_digest != candidate.response_text_digest:
            return False
        if not _DIGEST.fullmatch(resolution.candidate_text_digest):
            return False
        if type(resolution.resolved_text) is not str:
            return False
        if resolution.resolved_text_digest != compute_resolved_text_digest(resolution.resolved_text):
            return False
        if not _DIGEST.fullmatch(resolution.resolved_text_digest):
            return False
        if resolution.text_changed is not (resolution.resolved_text != candidate.response_text):
            return False
        policy = get_resolution_policy_for_origin(candidate.candidate_origin)
        if resolution.resolution_policy is not policy:
            return False
        expected = create_production_final_response_resolution(
            context,
            candidate,
            resolved_text=resolution.resolved_text if policy is LEGACY_RESPONSE_GUARD else None,
            existing_guard_applied=policy is LEGACY_RESPONSE_GUARD,
        )
        return resolution == expected and bool(_DIGEST.fullmatch(resolution.resolution_digest))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False
