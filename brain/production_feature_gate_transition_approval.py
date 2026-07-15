"""Fail-closed approval policy for release-controlled feature-gate proposals.

This module records which source-controlled artifacts are available.  It does
not approve, apply, activate, execute, or verify external human/CI/deployment
claims.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any

from brain.production_feature_gate_release_owner import (
    CURRENT_RELEASE_REVISION_ID,
    ProductionFeatureGateReleaseOwnerSnapshot,
    ProductionFeatureGateTransitionProposal,
    get_production_feature_gate_release_owner,
    verify_production_feature_gate_release_owner,
    verify_production_feature_gate_rollback_target,
    verify_production_feature_gate_transition_proposal,
)


PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_VERSION = "5.15.24.7.4.8"
PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_SCOPE = (
    "TRUSTED_RELEASE_CONTROLLED_FEATURE_GATE_TRANSITION_APPROVAL"
)
TRANSITION_NOT_APPROVED = "TRANSITION_NOT_APPROVED"
NO_TRANSITION_REQUIRED = "NO_TRANSITION_REQUIRED"
_HEX = re.compile(r"^[0-9a-f]{64}$")

_REQUIREMENT_IDS = (
    "RELEASE_OWNER_VERIFIED",
    "CURRENT_DEFAULT_DENY_CONFIGURATION_VERIFIED",
    "TRANSITION_PROPOSAL_VERIFIED",
    "ROLLBACK_TARGET_VERIFIED",
    "READ_ONLY_RELEASE_WIRING_ACCEPTED",
    "GATE_ENABLED_PREAUTH_QUALIFIED",
    "EXECUTABLE_REQUEST_QUALIFIED",
    "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED",
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED",
    "DEPLOYMENT_ROLLBACK_ATTESTED",
)
_MISSING_REASONS = {
    "READ_ONLY_RELEASE_WIRING_ACCEPTED": "missing canonical read-only release wiring acceptance",
    "GATE_ENABLED_PREAUTH_QUALIFIED": "missing canonical gate-enabled pre-authorization qualification",
    "EXECUTABLE_REQUEST_QUALIFIED": "missing canonical executable-request qualification",
    "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED": "missing canonical isolated controlled-runtime acceptance",
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED": "missing canonical production failure-containment acceptance",
    "DEPLOYMENT_ROLLBACK_ATTESTED": "missing canonical deployment/rollback attestation",
}


@dataclass(frozen=True)
class ProductionFeatureGateApprovalAuthorityBoundary:
    approval: bool = False
    application: bool = False
    activation: bool = False
    mutation: bool = False
    execution: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    delivery: bool = False
    persistence: bool = False
    deployment: bool = False
    rollback_execution: bool = False


@dataclass(frozen=True)
class ProductionFeatureGateApprovalRequirement:
    requirement_id: str
    required: bool
    evidence_digest: str | None
    verified: bool
    reason: str
    requirement_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateApprovalOwnerSnapshot:
    version: str
    scope: str
    release_owner: ProductionFeatureGateReleaseOwnerSnapshot
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    configuration_digest: str
    transition_digest: str
    rollback_digest: str
    transition_applied: bool = False
    approved_enable_proposal: None = None
    transition_approved: bool = False
    application_permitted: bool = False
    activation_permitted: bool = False
    mutation_permitted: bool = False
    executable_output: None = None
    authority_boundary: ProductionFeatureGateApprovalAuthorityBoundary = (
        ProductionFeatureGateApprovalAuthorityBoundary()
    )
    owner_digest: str = ""

    def __deepcopy__(self, memo: dict[int, Any]) -> "ProductionFeatureGateApprovalOwnerSnapshot":
        return self


@dataclass(frozen=True)
class ProductionFeatureGateTransitionApprovalRequest:
    version: str
    scope: str
    approval_owner: ProductionFeatureGateApprovalOwnerSnapshot
    release_owner: ProductionFeatureGateReleaseOwnerSnapshot
    proposal: ProductionFeatureGateTransitionProposal
    approval_owner_digest: str
    release_owner_digest: str
    release_revision_id: str
    configuration_digest: str
    proposal_digest: str
    rollback_digest: str
    request_digest: str = ""

    def __deepcopy__(self, memo: dict[int, Any]) -> "ProductionFeatureGateTransitionApprovalRequest":
        return self


@dataclass(frozen=True)
class ProductionFeatureGateTransitionApprovalDecision:
    version: str
    scope: str
    approval_owner: ProductionFeatureGateApprovalOwnerSnapshot
    release_owner: ProductionFeatureGateReleaseOwnerSnapshot
    proposal: ProductionFeatureGateTransitionProposal
    approval_owner_digest: str
    release_owner_digest: str
    release_revision_id: str
    configuration_digest: str
    proposal_digest: str
    rollback_digest: str
    requirements: tuple[ProductionFeatureGateApprovalRequirement, ...]
    proposal_verified: bool
    status: str
    primary_denial: str | None
    reasons: tuple[str, ...]
    transition_approved: bool = False
    application_permitted: bool = False
    activation_permitted: bool = False
    transition_applied: bool = False
    executable_output: None = None
    authority_boundary: ProductionFeatureGateApprovalAuthorityBoundary = (
        ProductionFeatureGateApprovalAuthorityBoundary()
    )
    decision_digest: str = ""

    def __deepcopy__(self, memo: dict[int, Any]) -> "ProductionFeatureGateTransitionApprovalDecision":
        return self


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported transition-approval material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(
        _canonical((PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_VERSION, label, value)),
        ensure_ascii=False, allow_nan=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, digest_field: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value) if field.name != digest_field)


def _all_false(value: Any) -> bool:
    return type(value) is ProductionFeatureGateApprovalAuthorityBoundary and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False
        for field in fields(value)
    )


def _build_owner() -> ProductionFeatureGateApprovalOwnerSnapshot:
    release_owner = get_production_feature_gate_release_owner()
    draft = ProductionFeatureGateApprovalOwnerSnapshot(
        PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_VERSION,
        PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_SCOPE,
        release_owner,
        release_owner.owner_digest,
        release_owner.release_revision.revision_id,
        release_owner.release_revision.revision_digest,
        release_owner.configuration_digest,
        release_owner.transition_record.transition_digest,
        release_owner.rollback_target.rollback_digest,
    )
    return replace(draft, owner_digest=_digest("APPROVAL_OWNER", _material(draft, "owner_digest")))


PRODUCTION_FEATURE_GATE_APPROVAL_OWNER = _build_owner()


def get_production_feature_gate_approval_owner() -> ProductionFeatureGateApprovalOwnerSnapshot:
    return PRODUCTION_FEATURE_GATE_APPROVAL_OWNER


def verify_production_feature_gate_approval_owner(value: Any) -> bool:
    owner = PRODUCTION_FEATURE_GATE_APPROVAL_OWNER
    return (
        type(value) is ProductionFeatureGateApprovalOwnerSnapshot
        and value is owner
        and value == owner
        and value.release_owner is get_production_feature_gate_release_owner()
        and verify_production_feature_gate_release_owner(value.release_owner)
        and value.release_revision_id == CURRENT_RELEASE_REVISION_ID
        and value.transition_applied is False
        and value.approved_enable_proposal is None
        and value.transition_approved is False
        and value.application_permitted is False
        and value.activation_permitted is False
        and value.mutation_permitted is False
        and value.executable_output is None
        and _all_false(value.authority_boundary)
        and bool(_HEX.fullmatch(value.owner_digest))
        and value.owner_digest == _digest("APPROVAL_OWNER", _material(value, "owner_digest"))
    )


def create_production_feature_gate_transition_approval_request(
    release_owner: Any, proposal: Any
) -> ProductionFeatureGateTransitionApprovalRequest | None:
    if release_owner is not get_production_feature_gate_release_owner():
        return None
    if not verify_production_feature_gate_release_owner(release_owner):
        return None
    if not verify_production_feature_gate_transition_proposal(proposal):
        return None
    approval_owner = get_production_feature_gate_approval_owner()
    draft = ProductionFeatureGateTransitionApprovalRequest(
        PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_VERSION,
        PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_SCOPE,
        approval_owner,
        release_owner,
        proposal,
        approval_owner.owner_digest,
        release_owner.owner_digest,
        release_owner.release_revision.revision_id,
        release_owner.configuration_digest,
        proposal.proposal_digest,
        release_owner.rollback_target.rollback_digest,
    )
    return replace(draft, request_digest=_digest("APPROVAL_REQUEST", _material(draft, "request_digest")))


def verify_production_feature_gate_transition_approval_request(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateTransitionApprovalRequest:
            return False
        expected = create_production_feature_gate_transition_approval_request(
            value.release_owner, value.proposal
        )
        return (
            expected is not None and value == expected
            and value.approval_owner is get_production_feature_gate_approval_owner()
            and bool(_HEX.fullmatch(value.request_digest))
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _requirement(requirement_id: str, evidence_digest: str | None, reason: str) -> ProductionFeatureGateApprovalRequirement:
    verified = evidence_digest is not None
    draft = ProductionFeatureGateApprovalRequirement(requirement_id, True, evidence_digest, verified, reason)
    return replace(draft, requirement_digest=_digest("APPROVAL_REQUIREMENT", _material(draft, "requirement_digest")))


def _requirements(request: ProductionFeatureGateTransitionApprovalRequest) -> tuple[ProductionFeatureGateApprovalRequirement, ...]:
    owner = request.release_owner
    available = (
        (owner.owner_digest, "exact canonical release owner verified"),
        (owner.configuration_digest, "exact empty default-deny configuration verified"),
        (request.proposal.proposal_digest, "exact non-authoritative transition proposal verified"),
        (owner.rollback_target.rollback_digest, "exact rollback target verified"),
    )
    result = [_requirement(identifier, digest, reason) for identifier, (digest, reason) in zip(_REQUIREMENT_IDS, available)]
    result.extend(_requirement(identifier, None, _MISSING_REASONS[identifier]) for identifier in _REQUIREMENT_IDS[4:])
    return tuple(result)


def evaluate_production_feature_gate_transition_approval(
    request: Any,
) -> ProductionFeatureGateTransitionApprovalDecision | None:
    if not verify_production_feature_gate_transition_approval_request(request):
        return None
    requirements = _requirements(request)
    no_transition = request.proposal.requested_gate_state is request.release_owner.configured_state
    if no_transition:
        status = NO_TRANSITION_REQUIRED
        primary_denial = None
        reasons = ("requested state already equals the exact current default-deny state; no transition required",)
    else:
        status = TRANSITION_NOT_APPROVED
        missing = tuple(item for item in requirements if item.required and not item.verified)
        primary_denial = missing[0].requirement_id
        reasons = tuple(item.reason for item in missing)
    draft = ProductionFeatureGateTransitionApprovalDecision(
        PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_VERSION,
        PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_SCOPE,
        request.approval_owner,
        request.release_owner,
        request.proposal,
        request.approval_owner_digest,
        request.release_owner_digest,
        request.release_revision_id,
        request.configuration_digest,
        request.proposal_digest,
        request.rollback_digest,
        requirements,
        True,
        status,
        primary_denial,
        reasons,
    )
    return replace(draft, decision_digest=_digest("APPROVAL_DECISION", _material(draft, "decision_digest")))


def verify_production_feature_gate_approval_requirement(value: Any) -> bool:
    return (
        type(value) is ProductionFeatureGateApprovalRequirement
        and value.requirement_id in _REQUIREMENT_IDS
        and value.required is True
        and type(value.verified) is bool
        and ((value.verified and bool(_HEX.fullmatch(value.evidence_digest or ""))) or
             (not value.verified and value.evidence_digest is None))
        and bool(_HEX.fullmatch(value.requirement_digest))
        and value.requirement_digest == _digest("APPROVAL_REQUIREMENT", _material(value, "requirement_digest"))
    )


def verify_production_feature_gate_transition_approval_decision(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateTransitionApprovalDecision:
            return False
        request = create_production_feature_gate_transition_approval_request(value.release_owner, value.proposal)
        if request is None:
            return False
        expected = evaluate_production_feature_gate_transition_approval(request)
        return (
            expected is not None and value == expected
            and value.approval_owner is get_production_feature_gate_approval_owner()
            and tuple(item.requirement_id for item in value.requirements) == _REQUIREMENT_IDS
            and len(set(item.requirement_id for item in value.requirements)) == len(_REQUIREMENT_IDS)
            and all(verify_production_feature_gate_approval_requirement(item) for item in value.requirements)
            and value.transition_approved is False
            and value.application_permitted is False
            and value.activation_permitted is False
            and value.transition_applied is False
            and value.executable_output is None
            and _all_false(value.authority_boundary)
            and bool(_HEX.fullmatch(value.decision_digest))
        )
    except (AttributeError, TypeError, ValueError):
        return False


__all__ = (
    "PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_VERSION",
    "PRODUCTION_FEATURE_GATE_TRANSITION_APPROVAL_SCOPE",
    "TRANSITION_NOT_APPROVED", "NO_TRANSITION_REQUIRED",
    "ProductionFeatureGateApprovalAuthorityBoundary",
    "ProductionFeatureGateApprovalRequirement",
    "ProductionFeatureGateTransitionApprovalRequest",
    "ProductionFeatureGateTransitionApprovalDecision",
    "ProductionFeatureGateApprovalOwnerSnapshot",
    "PRODUCTION_FEATURE_GATE_APPROVAL_OWNER",
    "get_production_feature_gate_approval_owner",
    "create_production_feature_gate_transition_approval_request",
    "evaluate_production_feature_gate_transition_approval",
    "verify_production_feature_gate_approval_owner",
    "verify_production_feature_gate_approval_requirement",
    "verify_production_feature_gate_transition_approval_request",
    "verify_production_feature_gate_transition_approval_decision",
)
