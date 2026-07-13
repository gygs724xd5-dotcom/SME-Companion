"""Immutable exactly-once evidence for a canonical production turn commit."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any

from brain.production_final_response_resolution import (
    ProductionFinalResponseResolution,
    compute_resolved_text_digest,
    verify_production_final_response_resolution,
)
from brain.production_response_candidate import (
    EXCEPTION_FALLBACK,
    ProductionResponseCandidate,
    verify_production_response_candidate,
)
from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context


PRODUCTION_TURN_COMMIT_RECEIPT_VERSION = "5.15.24.4"
TURN_BOUND_SINGLE_COMMIT_SCOPE = "VERIFIED_USER_TURN_RESPONSE"
NORMAL_TURN_BOUND_COMMIT = "NORMAL_TURN_BOUND_COMMIT"
TURN_BOUND_EXCEPTION_COMMIT = "TURN_BOUND_EXCEPTION_COMMIT"
COMMIT_APPLIED = "COMMIT_APPLIED"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionTurnCommitReceipt:
    receipt_version: str
    receipt_scope: str
    conversation_id: str
    turn_id: str
    turn_digest: str
    candidate_digest: str
    resolution_digest: str
    commit_kind: str
    committed_response_digest: str
    commit_status: str = COMMIT_APPLIED
    commit_applied: bool = True
    exactly_once: bool = True
    routing_authority: bool = False
    response_selection_authority: bool = False
    response_guard_authority: bool = False
    persistence_authority: bool = False
    controlled_runtime_activation_authority: bool = False
    receipt_digest: str = ""


_AUTHORITY_FIELDS = tuple(
    name for name in ProductionTurnCommitReceipt.__dataclass_fields__ if name.endswith("_authority")
)


def _sha256(material: Any) -> str:
    encoded = json.dumps(material, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_turn_commit_receipt_digest(receipt: Any) -> str:
    if type(receipt) is not ProductionTurnCommitReceipt:
        return ""
    material = tuple(
        getattr(receipt, field)
        for field in ProductionTurnCommitReceipt.__dataclass_fields__
        if field != "receipt_digest"
    )
    try:
        return _sha256(("PRODUCTION_TURN_COMMIT_RECEIPT", PRODUCTION_TURN_COMMIT_RECEIPT_VERSION, material))
    except (TypeError, ValueError, UnicodeEncodeError):
        return ""


def create_production_turn_commit_receipt(
    context: Any,
    candidate: Any,
    resolution: Any,
    committed_text: Any,
) -> ProductionTurnCommitReceipt:
    if not verify_production_turn_context(context):
        raise ValueError("context must be verified")
    if not verify_production_response_candidate(candidate, context):
        raise ValueError("candidate must be verified for context")
    if not verify_production_final_response_resolution(resolution, candidate, context):
        raise ValueError("resolution must be verified for candidate and context")
    if type(committed_text) is not str or committed_text != resolution.resolved_text:
        raise ValueError("committed text must equal the canonical resolved text")
    kind = TURN_BOUND_EXCEPTION_COMMIT if candidate.candidate_origin == EXCEPTION_FALLBACK else NORMAL_TURN_BOUND_COMMIT
    draft = ProductionTurnCommitReceipt(
        receipt_version=PRODUCTION_TURN_COMMIT_RECEIPT_VERSION,
        receipt_scope=TURN_BOUND_SINGLE_COMMIT_SCOPE,
        conversation_id=context.conversation_id,
        turn_id=context.turn_id,
        turn_digest=context.turn_digest,
        candidate_digest=candidate.candidate_digest,
        resolution_digest=resolution.resolution_digest,
        commit_kind=kind,
        committed_response_digest=compute_resolved_text_digest(resolution.resolved_text),
    )
    return replace(draft, receipt_digest=compute_turn_commit_receipt_digest(draft))


def verify_production_turn_commit_receipt(
    receipt: Any,
    context: Any,
    candidate: Any,
    resolution: Any,
    committed_text: Any,
) -> bool:
    try:
        if type(receipt) is not ProductionTurnCommitReceipt:
            return False
        if receipt.receipt_version != PRODUCTION_TURN_COMMIT_RECEIPT_VERSION:
            return False
        if receipt.receipt_scope != TURN_BOUND_SINGLE_COMMIT_SCOPE:
            return False
        if receipt.commit_status != COMMIT_APPLIED or receipt.commit_applied is not True or receipt.exactly_once is not True:
            return False
        if any(type(getattr(receipt, name)) is not bool or getattr(receipt, name) for name in _AUTHORITY_FIELDS):
            return False
        expected = create_production_turn_commit_receipt(context, candidate, resolution, committed_text)
        if receipt != expected:
            return False
        return all(_DIGEST.fullmatch(value) for value in (
            receipt.turn_digest,
            receipt.candidate_digest,
            receipt.resolution_digest,
            receipt.committed_response_digest,
            receipt.receipt_digest,
        ))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False
