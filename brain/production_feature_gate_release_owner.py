"""Release-controlled owner for the current production feature-gate configuration.

Trust is deliberately narrow: this module identifies one exact code-owned
singleton from the loaded release.  It does not prove a git revision, reviewer,
human approval, signature, deployment identity, or runtime configuration source.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    ProductionFeatureGateConfiguration,
    SUPPORTED_PRODUCTION_FEATURE_GATES,
    verify_production_feature_gate_configuration,
)


PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION = "5.15.24.7.4.6"
PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE = (
    "TRUSTED_RELEASE_CONTROLLED_PRODUCTION_FEATURE_GATE_CONFIGURATION"
)
SOURCE_CONTROLLED_RELEASE_CONFIGURATION = "SOURCE_CONTROLLED_RELEASE_CONFIGURATION"
CURRENT_RELEASE_REVISION_ID = "production-feature-gates/default-deny/5.15.24.7.4.6"
PROPOSED_NOT_AUTHORIZED = "PROPOSED_NOT_AUTHORIZED"
NO_TRANSITION_APPLIED = "NO_TRANSITION_APPLIED"
NO_RELEASE_TRANSITION_AUTHORITY = "NO_RELEASE_TRANSITION_AUTHORITY"
CURRENT_EMPTY_DEFAULT_DENY_CONFIGURATION = "CURRENT_EMPTY_DEFAULT_DENY_CONFIGURATION"
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionFeatureGateReleaseAuthorityBoundary:
    routing: bool = False
    planning: bool = False
    response_selection: bool = False
    response_guard: bool = False
    response_commit: bool = False
    persistence: bool = False
    tool_execution: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    delivery: bool = False
    feature_gate_mutation: bool = False
    production_activation: bool = False


@dataclass(frozen=True)
class ProductionFeatureGateReleaseRevision:
    version: str
    scope: str
    source_identity: str
    revision_id: str
    supported_gate_registry: tuple[str, ...]
    applied_entries: tuple[tuple[str, bool], ...]
    configuration: ProductionFeatureGateConfiguration
    configuration_digest: str
    transition_applied: bool = False
    activation_requested: bool = False
    activation_permitted: bool = False
    mutation_permitted: bool = False
    executable_output: None = None
    revision_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateTransitionProposal:
    version: str
    scope: str
    source_identity: str
    source_revision_id: str
    requested_gate_name: str
    requested_gate_state: bool
    status: str
    transition_applied: bool = False
    approval_verified: bool = False
    activation_permitted: bool = False
    mutation_permitted: bool = False
    executable_output: None = None
    proposal_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateTransitionRecord:
    version: str
    scope: str
    source_identity: str
    source_revision_id: str
    target_revision_id: str
    previous_configuration_digest: str
    current_configuration_digest: str
    status: str
    reason: str
    transition_applied: bool = False
    approval_verified: bool = False
    activation_permitted: bool = False
    mutation_permitted: bool = False
    executable_output: None = None
    transition_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateRollbackTarget:
    version: str
    scope: str
    source_identity: str
    target_revision_id: str
    target_configuration: ProductionFeatureGateConfiguration
    target_configuration_digest: str
    target_entries: tuple[tuple[str, bool], ...]
    reason: str
    rollback_available: bool = True
    rollback_applied: bool = False
    activation_permitted: bool = False
    mutation_permitted: bool = False
    executable_output: None = None
    rollback_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateReleaseOwnerSnapshot:
    version: str
    scope: str
    source_identity: str
    supported_gate_registry: tuple[str, ...]
    release_revision: ProductionFeatureGateReleaseRevision
    configuration: ProductionFeatureGateConfiguration
    configuration_digest: str
    transition_record: ProductionFeatureGateTransitionRecord
    rollback_target: ProductionFeatureGateRollbackTarget
    gate_name: str
    configured_state: bool
    effective_state: bool
    default_denied: bool
    transition_applied: bool
    rollback_available: bool
    activation_permitted: bool = False
    mutation_permitted: bool = False
    executable_output: None = None
    authority_boundary: ProductionFeatureGateReleaseAuthorityBoundary = (
        ProductionFeatureGateReleaseAuthorityBoundary()
    )
    owner_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported release-owner material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(
        _canonical((PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION, label, value)),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, digest_field: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value) if field.name != digest_field)


def _all_false(value: Any) -> bool:
    return type(value) is ProductionFeatureGateReleaseAuthorityBoundary and all(
        getattr(value, field.name) is False for field in fields(value)
    )


def _build_release_revision() -> ProductionFeatureGateReleaseRevision:
    configuration = PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    draft = ProductionFeatureGateReleaseRevision(
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION,
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE,
        SOURCE_CONTROLLED_RELEASE_CONFIGURATION,
        CURRENT_RELEASE_REVISION_ID,
        SUPPORTED_PRODUCTION_FEATURE_GATES,
        (),
        configuration,
        configuration.source_digest,
    )
    return replace(draft, revision_digest=_digest("RELEASE_REVISION", _material(draft, "revision_digest")))


def create_production_feature_gate_transition_proposal(
    requested_gate_name: Any, requested_gate_state: Any
) -> ProductionFeatureGateTransitionProposal:
    """Create non-authoritative governance evidence; never an applied configuration."""
    if type(requested_gate_name) is not str or requested_gate_name not in SUPPORTED_PRODUCTION_FEATURE_GATES:
        raise ValueError("requested gate must be an exact supported gate")
    if type(requested_gate_state) is not bool:
        raise ValueError("requested state must be an exact boolean")
    draft = ProductionFeatureGateTransitionProposal(
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION,
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE,
        SOURCE_CONTROLLED_RELEASE_CONFIGURATION,
        CURRENT_RELEASE_REVISION_ID,
        requested_gate_name,
        requested_gate_state,
        PROPOSED_NOT_AUTHORIZED,
    )
    return replace(draft, proposal_digest=_digest("TRANSITION_PROPOSAL", _material(draft, "proposal_digest")))


def _build_transition_record() -> ProductionFeatureGateTransitionRecord:
    configuration_digest = PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION.source_digest
    draft = ProductionFeatureGateTransitionRecord(
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION,
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE,
        SOURCE_CONTROLLED_RELEASE_CONFIGURATION,
        CURRENT_RELEASE_REVISION_ID,
        CURRENT_RELEASE_REVISION_ID,
        configuration_digest,
        configuration_digest,
        NO_TRANSITION_APPLIED,
        NO_RELEASE_TRANSITION_AUTHORITY,
    )
    return replace(draft, transition_digest=_digest("TRANSITION_RECORD", _material(draft, "transition_digest")))


def _build_rollback_target() -> ProductionFeatureGateRollbackTarget:
    configuration = PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    draft = ProductionFeatureGateRollbackTarget(
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION,
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE,
        SOURCE_CONTROLLED_RELEASE_CONFIGURATION,
        CURRENT_RELEASE_REVISION_ID,
        configuration,
        configuration.source_digest,
        (),
        CURRENT_EMPTY_DEFAULT_DENY_CONFIGURATION,
    )
    return replace(draft, rollback_digest=_digest("ROLLBACK_TARGET", _material(draft, "rollback_digest")))


_CANONICAL_RELEASE_REVISION = _build_release_revision()
_CANONICAL_TRANSITION_RECORD = _build_transition_record()
_CANONICAL_ROLLBACK_TARGET = _build_rollback_target()


def _build_owner() -> ProductionFeatureGateReleaseOwnerSnapshot:
    configuration = PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
    draft = ProductionFeatureGateReleaseOwnerSnapshot(
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION,
        PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE,
        SOURCE_CONTROLLED_RELEASE_CONFIGURATION,
        SUPPORTED_PRODUCTION_FEATURE_GATES,
        _CANONICAL_RELEASE_REVISION,
        configuration,
        configuration.source_digest,
        _CANONICAL_TRANSITION_RECORD,
        _CANONICAL_ROLLBACK_TARGET,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
        False,
        False,
        True,
        False,
        True,
    )
    return replace(draft, owner_digest=_digest("RELEASE_OWNER", _material(draft, "owner_digest")))


PRODUCTION_RELEASE_CONTROLLED_DEFAULT_DENY_FEATURE_GATE_OWNER = _build_owner()


def get_production_feature_gate_release_owner() -> ProductionFeatureGateReleaseOwnerSnapshot:
    """Return the one exact owner embedded in this loaded code release."""
    return PRODUCTION_RELEASE_CONTROLLED_DEFAULT_DENY_FEATURE_GATE_OWNER


def verify_production_feature_gate_release_revision(value: Any) -> bool:
    return (
        type(value) is ProductionFeatureGateReleaseRevision
        and value == _CANONICAL_RELEASE_REVISION
        and value.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
        and bool(_HEX.fullmatch(value.revision_digest))
        and verify_production_feature_gate_configuration(value.configuration)
    )


def verify_production_feature_gate_transition_proposal(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateTransitionProposal:
            return False
        expected = create_production_feature_gate_transition_proposal(
            value.requested_gate_name, value.requested_gate_state
        )
        return value == expected and bool(_HEX.fullmatch(value.proposal_digest))
    except (AttributeError, TypeError, ValueError):
        return False


def verify_production_feature_gate_transition_record(value: Any) -> bool:
    return (
        type(value) is ProductionFeatureGateTransitionRecord
        and value == _CANONICAL_TRANSITION_RECORD
        and bool(_HEX.fullmatch(value.transition_digest))
    )


def verify_production_feature_gate_rollback_target(value: Any) -> bool:
    return (
        type(value) is ProductionFeatureGateRollbackTarget
        and value == _CANONICAL_ROLLBACK_TARGET
        and value.target_configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
        and bool(_HEX.fullmatch(value.rollback_digest))
        and verify_production_feature_gate_configuration(value.target_configuration)
    )


def verify_production_feature_gate_release_owner(value: Any) -> bool:
    return (
        type(value) is ProductionFeatureGateReleaseOwnerSnapshot
        and value == PRODUCTION_RELEASE_CONTROLLED_DEFAULT_DENY_FEATURE_GATE_OWNER
        and value.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
        and value.release_revision is _CANONICAL_RELEASE_REVISION
        and value.transition_record is _CANONICAL_TRANSITION_RECORD
        and value.rollback_target is _CANONICAL_ROLLBACK_TARGET
        and value.configuration.gate_entries == ()
        and value.configured_state is False
        and value.effective_state is False
        and value.default_denied is True
        and value.activation_permitted is False
        and value.mutation_permitted is False
        and value.executable_output is None
        and _all_false(value.authority_boundary)
        and bool(_HEX.fullmatch(value.owner_digest))
        and verify_production_feature_gate_release_revision(value.release_revision)
        and verify_production_feature_gate_transition_record(value.transition_record)
        and verify_production_feature_gate_rollback_target(value.rollback_target)
    )


__all__ = (
    "PRODUCTION_FEATURE_GATE_RELEASE_OWNER_VERSION",
    "PRODUCTION_FEATURE_GATE_RELEASE_OWNER_SCOPE",
    "SOURCE_CONTROLLED_RELEASE_CONFIGURATION",
    "CURRENT_RELEASE_REVISION_ID",
    "PROPOSED_NOT_AUTHORIZED",
    "NO_TRANSITION_APPLIED",
    "ProductionFeatureGateReleaseAuthorityBoundary",
    "ProductionFeatureGateReleaseRevision",
    "ProductionFeatureGateTransitionProposal",
    "ProductionFeatureGateTransitionRecord",
    "ProductionFeatureGateRollbackTarget",
    "ProductionFeatureGateReleaseOwnerSnapshot",
    "PRODUCTION_RELEASE_CONTROLLED_DEFAULT_DENY_FEATURE_GATE_OWNER",
    "get_production_feature_gate_release_owner",
    "create_production_feature_gate_transition_proposal",
    "verify_production_feature_gate_release_revision",
    "verify_production_feature_gate_transition_proposal",
    "verify_production_feature_gate_transition_record",
    "verify_production_feature_gate_rollback_target",
    "verify_production_feature_gate_release_owner",
)
