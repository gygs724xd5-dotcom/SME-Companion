"""Immutable evidence binding for the 5.15.24.7.4.11 approval evaluation.

This module verifies and binds canonical historical artifacts.  It grants no
approval, application, activation, execution, deployment, or runtime authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any

from brain.isolated_gate_enabled_pre_authorization_qualification import (
    GATE_ENABLED_PREAUTH_QUALIFIED,
    ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_SCOPE,
    ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_VERSION,
    IsolatedGateEnabledPreAuthorizationReport,
    verify_isolated_gate_enabled_pre_authorization_report,
)
from brain.production_feature_gate_owner import LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
from brain.production_feature_gate_release_wiring_acceptance import (
    PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_SCOPE,
    PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION,
    READ_ONLY_RELEASE_WIRING_ACCEPTED,
    ProductionFeatureGateReleaseWiringReport,
    verify_production_feature_gate_release_wiring_report,
)
from brain.production_feature_gate_transition_approval import (
    TRANSITION_NOT_APPROVED,
    ProductionFeatureGateApprovalRequirement,
    ProductionFeatureGateTransitionApprovalDecision,
    ProductionFeatureGateTransitionApprovalRequest,
    verify_production_feature_gate_transition_approval_decision,
    verify_production_feature_gate_transition_approval_request,
)


PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_VERSION = "5.15.24.7.4.11"
PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_SCOPE = (
    "CANONICAL_IMMUTABLE_APPROVAL_EVIDENCE_BINDING"
)
EXPECTED_RELEASE_WIRING_REPORT_DIGEST = "f1c24c971a46f1e029743aa72fee71937d7d37aab7971c31e4cfc9bed51f5362"
EXPECTED_RELEASE_WIRING_TOPOLOGY_DIGEST = "feb3f68232ea08eb44e72a28bc4700c39402863bb6c6bde9aab4edc3064439c8"
EXPECTED_PREAUTH_REPORT_DIGEST = "0c4a8c33d9ca33562537eaf806d5ed6eb60e3873e2847524860b1ecc53a3216e"
EXPECTED_PREAUTH_TOPOLOGY_DIGEST = "3a7de18b3902805bf616fd971e8254c027ebf21866b7b44d67488d47e9494bab"

REQUIREMENT_IDS = (
    "RELEASE_OWNER_VERIFIED", "CURRENT_DEFAULT_DENY_CONFIGURATION_VERIFIED",
    "TRANSITION_PROPOSAL_VERIFIED", "ROLLBACK_TARGET_VERIFIED",
    READ_ONLY_RELEASE_WIRING_ACCEPTED, GATE_ENABLED_PREAUTH_QUALIFIED,
    "EXECUTABLE_REQUEST_QUALIFIED", "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED",
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED", "DEPLOYMENT_ROLLBACK_ATTESTED",
)
MISSING_REASONS = {
    "EXECUTABLE_REQUEST_QUALIFIED": "missing canonical executable-request qualification",
    "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED": "missing canonical isolated controlled-runtime acceptance",
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED": "missing canonical production failure-containment acceptance",
    "DEPLOYMENT_ROLLBACK_ATTESTED": "missing canonical deployment/rollback attestation",
}
EVIDENCE_TOPOLOGY = (
    "HISTORICAL_APPROVAL_REQUEST", "HISTORICAL_APPROVAL_DECISION",
    "V5.15.24.7.4.9_RELEASE_WIRING_REPORT",
    "V5.15.24.7.4.10_GATE_ENABLED_PREAUTH_REPORT",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionFeatureGateEvidenceBindingAuthorityBoundary:
    approval: bool = False
    application: bool = False
    activation: bool = False
    mutation: bool = False
    execution: bool = False
    dispatch: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    calculator: bool = False
    delivery: bool = False
    persistence: bool = False
    deployment: bool = False
    rollback_execution: bool = False
    response_replacement: bool = False


@dataclass(frozen=True)
class ProductionFeatureGateApprovalEvidence:
    evidence_type: str
    evidence_version: str
    evidence_scope: str
    requirement_id: str
    report_digest: str
    topology_digest: str
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    production_configuration_digest: str
    verified: bool
    evidence_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateApprovalEvidenceBundle:
    version: str
    scope: str
    historical_request: ProductionFeatureGateTransitionApprovalRequest
    historical_decision: ProductionFeatureGateTransitionApprovalDecision
    release_wiring_report: ProductionFeatureGateReleaseWiringReport
    preauth_report: IsolatedGateEnabledPreAuthorizationReport
    historical_request_digest: str
    historical_decision_digest: str
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    production_configuration_digest: str
    transition_proposal_digest: str
    rollback_digest: str
    evidence: tuple[ProductionFeatureGateApprovalEvidence, ...]
    requirement_ids: tuple[str, ...]
    evidence_topology: tuple[str, ...]
    ordered_evidence_digests: tuple[str, ...]
    authority_boundary: ProductionFeatureGateEvidenceBindingAuthorityBoundary = ProductionFeatureGateEvidenceBindingAuthorityBoundary()
    bundle_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateEvidenceBoundRequirement:
    requirement_id: str
    required: bool
    evidence_type: str | None
    evidence_version: str | None
    evidence_scope: str | None
    evidence_digest: str | None
    report_digest: str | None
    topology_digest: str | None
    verified: bool
    reason: str
    requirement_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateEvidenceBoundDecision:
    version: str
    scope: str
    historical_request: ProductionFeatureGateTransitionApprovalRequest
    historical_decision: ProductionFeatureGateTransitionApprovalDecision
    approval_owner: Any
    release_owner: Any
    proposal: Any
    evidence_bundle: ProductionFeatureGateApprovalEvidenceBundle
    historical_request_digest: str
    historical_decision_digest: str
    approval_owner_digest: str
    release_owner_digest: str
    release_revision_id: str
    production_configuration_digest: str
    proposal_digest: str
    rollback_digest: str
    evidence_bundle_digest: str
    requirements: tuple[ProductionFeatureGateEvidenceBoundRequirement, ...]
    verified_requirement_count: int
    missing_requirement_count: int
    status: str
    primary_denial: str
    reasons: tuple[str, ...]
    transition_approved: bool = False
    application_permitted: bool = False
    activation_permitted: bool = False
    transition_applied: bool = False
    executable_output: None = None
    authority_boundary: ProductionFeatureGateEvidenceBindingAuthorityBoundary = ProductionFeatureGateEvidenceBindingAuthorityBoundary()
    decision_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal: return {"$decimal": str(value)}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported evidence-binding material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(_canonical((PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_VERSION, label, value)),
                         ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, digest_field: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value) if field.name != digest_field)


def _all_false(value: Any) -> bool:
    return type(value) is ProductionFeatureGateEvidenceBindingAuthorityBoundary and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False for field in fields(value)
    )


def _reports_compatible(wiring: ProductionFeatureGateReleaseWiringReport,
                        preauth: IsolatedGateEnabledPreAuthorizationReport) -> bool:
    observation = wiring.observations[0]
    foundation = preauth.foundation_result
    binding = foundation.configuration_binding
    return all((
        observation.release_owner is binding.release_owner,
        observation.release_owner_digest == preauth.release_owner_digest,
        observation.release_revision_id == preauth.release_revision_id,
        observation.release_revision_digest == preauth.release_revision_digest,
        observation.configuration_digest == preauth.production_configuration_digest,
        binding.gate_name == LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
        foundation.execute_allowed is False, foundation.executable_request is None,
        foundation.executable_request_qualified is False,
        preauth.executable_request_qualified is False,
        preauth.controlled_runtime_invocation_count == 0,
        preauth.source_sha_attested is False, preauth.deployed_sha_attested is False,
    ))


def _make_evidence(evidence_type: str, version: str, scope: str, requirement_id: str,
                   report_digest: str, topology_digest: str, owner_digest: str,
                   revision_id: str, revision_digest: str, configuration_digest: str
                   ) -> ProductionFeatureGateApprovalEvidence:
    draft = ProductionFeatureGateApprovalEvidence(
        evidence_type, version, scope, requirement_id, report_digest, topology_digest,
        owner_digest, revision_id, revision_digest, configuration_digest, True,
    )
    return replace(draft, evidence_digest=_digest("APPROVAL_EVIDENCE", _material(draft, "evidence_digest")))


def create_production_feature_gate_approval_evidence_bundle(
    historical_request: Any, historical_decision: Any, release_wiring_report: Any, preauth_report: Any,
) -> ProductionFeatureGateApprovalEvidenceBundle | None:
    try:
        if type(historical_request) is not ProductionFeatureGateTransitionApprovalRequest: return None
        if type(historical_decision) is not ProductionFeatureGateTransitionApprovalDecision: return None
        if type(release_wiring_report) is not ProductionFeatureGateReleaseWiringReport: return None
        if type(preauth_report) is not IsolatedGateEnabledPreAuthorizationReport: return None
        if not verify_production_feature_gate_transition_approval_request(historical_request): return None
        if not verify_production_feature_gate_transition_approval_decision(historical_decision): return None
        if historical_decision.release_owner is not historical_request.release_owner or historical_decision.proposal != historical_request.proposal: return None
        if historical_decision.decision_digest == "" or historical_decision.primary_denial != READ_ONLY_RELEASE_WIRING_ACCEPTED: return None
        if not verify_production_feature_gate_release_wiring_report(release_wiring_report): return None
        if not verify_isolated_gate_enabled_pre_authorization_report(preauth_report): return None
        if (release_wiring_report.acceptance_status != READ_ONLY_RELEASE_WIRING_ACCEPTED
                or not release_wiring_report.all_passed
                or preauth_report.requirement_id != GATE_ENABLED_PREAUTH_QUALIFIED
                or preauth_report.status != GATE_ENABLED_PREAUTH_QUALIFIED
                or preauth_report.qualified is not True): return None
        if (release_wiring_report.report_digest != EXPECTED_RELEASE_WIRING_REPORT_DIGEST
                or release_wiring_report.topology_digest != EXPECTED_RELEASE_WIRING_TOPOLOGY_DIGEST
                or preauth_report.report_digest != EXPECTED_PREAUTH_REPORT_DIGEST
                or preauth_report.topology_digest != EXPECTED_PREAUTH_TOPOLOGY_DIGEST): return None
        if not _reports_compatible(release_wiring_report, preauth_report): return None
        owner = historical_request.release_owner
        if (owner is not release_wiring_report.observations[0].release_owner
                or owner.owner_digest != preauth_report.release_owner_digest
                or historical_request.release_revision_id != preauth_report.release_revision_id
                or historical_request.configuration_digest != preauth_report.production_configuration_digest): return None
        evidence = (
            _make_evidence("ProductionFeatureGateReleaseWiringReport",
                PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION,
                PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_SCOPE, READ_ONLY_RELEASE_WIRING_ACCEPTED,
                release_wiring_report.report_digest, release_wiring_report.topology_digest,
                owner.owner_digest, owner.release_revision.revision_id, owner.release_revision.revision_digest,
                owner.configuration_digest),
            _make_evidence("IsolatedGateEnabledPreAuthorizationReport",
                ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_VERSION,
                ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_SCOPE, GATE_ENABLED_PREAUTH_QUALIFIED,
                preauth_report.report_digest, preauth_report.topology_digest, owner.owner_digest,
                owner.release_revision.revision_id, owner.release_revision.revision_digest,
                owner.configuration_digest),
        )
        draft = ProductionFeatureGateApprovalEvidenceBundle(
            PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_VERSION,
            PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_SCOPE, historical_request,
            historical_decision, release_wiring_report, preauth_report, historical_request.request_digest,
            historical_decision.decision_digest, owner.owner_digest, owner.release_revision.revision_id,
            owner.release_revision.revision_digest, owner.configuration_digest,
            historical_request.proposal_digest, historical_request.rollback_digest, evidence,
            REQUIREMENT_IDS, EVIDENCE_TOPOLOGY, tuple(item.evidence_digest for item in evidence),
        )
        return replace(draft, bundle_digest=_digest("EVIDENCE_BUNDLE", _material(draft, "bundle_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_feature_gate_approval_evidence(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateApprovalEvidence: return False
        if value.requirement_id not in (READ_ONLY_RELEASE_WIRING_ACCEPTED, GATE_ENABLED_PREAUTH_QUALIFIED): return False
        return (value.verified is True and bool(_HEX.fullmatch(value.report_digest))
                and bool(_HEX.fullmatch(value.topology_digest)) and bool(_HEX.fullmatch(value.evidence_digest))
                and value.evidence_digest == _digest("APPROVAL_EVIDENCE", _material(value, "evidence_digest")))
    except (AttributeError, TypeError, ValueError): return False


def verify_production_feature_gate_approval_evidence_bundle(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateApprovalEvidenceBundle: return False
        expected = create_production_feature_gate_approval_evidence_bundle(
            value.historical_request, value.historical_decision, value.release_wiring_report, value.preauth_report)
        return (expected is not None and value == expected and value.requirement_ids == REQUIREMENT_IDS
                and value.evidence_topology == EVIDENCE_TOPOLOGY
                and tuple(item.requirement_id for item in value.evidence) == REQUIREMENT_IDS[4:6]
                and all(verify_production_feature_gate_approval_evidence(item) for item in value.evidence)
                and _all_false(value.authority_boundary) and bool(_HEX.fullmatch(value.bundle_digest)))
    except (AttributeError, TypeError, ValueError): return False


def _requirement(requirement_id: str, evidence_type: str | None, evidence_version: str | None,
                 evidence_scope: str | None, evidence_digest: str | None, report_digest: str | None,
                 topology_digest: str | None, verified: bool, reason: str
                 ) -> ProductionFeatureGateEvidenceBoundRequirement:
    draft = ProductionFeatureGateEvidenceBoundRequirement(
        requirement_id, True, evidence_type, evidence_version, evidence_scope,
        evidence_digest, report_digest, topology_digest, verified, reason,
    )
    return replace(draft, requirement_digest=_digest("EVIDENCE_BOUND_REQUIREMENT", _material(draft, "requirement_digest")))


def evaluate_production_feature_gate_evidence_bound_approval(bundle: Any) -> ProductionFeatureGateEvidenceBoundDecision | None:
    if not verify_production_feature_gate_approval_evidence_bundle(bundle): return None
    historical = bundle.historical_decision
    requirements = tuple(_requirement(
        old.requirement_id, "HistoricalApprovalRequirement", historical.version, historical.scope,
        old.evidence_digest, None, None, True, old.reason,
    ) for old in historical.requirements[:4])
    requirements += tuple(_requirement(
        item.requirement_id, item.evidence_type, item.evidence_version, item.evidence_scope,
        item.evidence_digest, item.report_digest, item.topology_digest, True,
        "exact canonical report strictly verified and evidence-bound",
    ) for item in bundle.evidence)
    requirements += tuple(_requirement(identifier, None, None, None, None, None, None, False,
                                       MISSING_REASONS[identifier]) for identifier in REQUIREMENT_IDS[6:])
    missing = tuple(item for item in requirements if not item.verified)
    draft = ProductionFeatureGateEvidenceBoundDecision(
        PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_VERSION,
        PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_SCOPE, bundle.historical_request,
        historical, historical.approval_owner, historical.release_owner, historical.proposal,
        bundle, bundle.historical_request_digest, bundle.historical_decision_digest,
        historical.approval_owner_digest, bundle.release_owner_digest, bundle.release_revision_id,
        bundle.production_configuration_digest, bundle.transition_proposal_digest, bundle.rollback_digest,
        bundle.bundle_digest, requirements, len(requirements) - len(missing), len(missing),
        TRANSITION_NOT_APPROVED, missing[0].requirement_id, tuple(item.reason for item in missing),
    )
    return replace(draft, decision_digest=_digest("EVIDENCE_BOUND_DECISION", _material(draft, "decision_digest")))


def verify_production_feature_gate_evidence_bound_decision(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateEvidenceBoundDecision: return False
        expected = evaluate_production_feature_gate_evidence_bound_approval(value.evidence_bundle)
        return (expected is not None and value == expected
                and tuple(item.requirement_id for item in value.requirements) == REQUIREMENT_IDS
                and len(set(item.requirement_id for item in value.requirements)) == len(REQUIREMENT_IDS)
                and value.verified_requirement_count == 6 and value.missing_requirement_count == 4
                and value.status == TRANSITION_NOT_APPROVED
                and value.primary_denial == "EXECUTABLE_REQUEST_QUALIFIED"
                and value.transition_approved is False and value.application_permitted is False
                and value.activation_permitted is False and value.transition_applied is False
                and value.executable_output is None and _all_false(value.authority_boundary)
                and bool(_HEX.fullmatch(value.decision_digest)))
    except (AttributeError, TypeError, ValueError): return False


__all__ = (
    "PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_VERSION",
    "PRODUCTION_FEATURE_GATE_APPROVAL_EVIDENCE_BINDING_SCOPE", "REQUIREMENT_IDS",
    "MISSING_REASONS", "EVIDENCE_TOPOLOGY",
    "ProductionFeatureGateEvidenceBindingAuthorityBoundary",
    "ProductionFeatureGateApprovalEvidence", "ProductionFeatureGateApprovalEvidenceBundle",
    "ProductionFeatureGateEvidenceBoundRequirement", "ProductionFeatureGateEvidenceBoundDecision",
    "create_production_feature_gate_approval_evidence_bundle",
    "verify_production_feature_gate_approval_evidence",
    "verify_production_feature_gate_approval_evidence_bundle",
    "evaluate_production_feature_gate_evidence_bound_approval",
    "verify_production_feature_gate_evidence_bound_decision",
)
