"""V5.15.24.7.4.13 immutable executable-request approval evidence binding.

This passive layer composes the exact V5.15.24.7.4.11 evidence-bound decision
with the exact V5.15.24.7.4.12 qualification report.  It grants no execution,
dispatch, application, activation, persistence, deployment, or runtime authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any

from brain.isolated_executable_request_qualification import (
    IsolatedExecutableRequestQualificationReport,
    REQUIREMENT_ID as EXECUTABLE_REQUEST_QUALIFIED,
    SCOPE as QUALIFICATION_SCOPE,
    STATUS as QUALIFICATION_STATUS,
    SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS,
    VERSION as QUALIFICATION_VERSION,
    verify_isolated_executable_request_observation,
    verify_isolated_executable_request_qualification_report,
)
from brain.production_feature_gate_approval_evidence_binding import (
    ProductionFeatureGateApprovalEvidenceBundle,
    ProductionFeatureGateEvidenceBoundDecision,
    verify_production_feature_gate_approval_evidence_bundle,
    verify_production_feature_gate_evidence_bound_decision,
)
from brain.production_feature_gate_transition_approval import TRANSITION_NOT_APPROVED
from brain.versioned_cost_executable_request import verify_versioned_cost_executable_request

VERSION = "5.15.24.7.4.13"
SCOPE = "EXECUTABLE_REQUEST_APPROVAL_EVIDENCE_BINDING"
EXPECTED_PREVIOUS_DECISION_DIGEST = "26e6f92a925724c4ba58f25f93b16b2b9e6315ad2d7b02a7fee3d5dde4b20304"
EXPECTED_REPORT_DIGEST = "8a182e3e60684b34f5332ecb5dc8638d8d78d0858a719799f1d602c861a273de"
EXPECTED_TOPOLOGY_DIGEST = "d6485776e7b004bf99f3aa08864d33851239c0674278dafcf0f2eab6908a629f"
EXPECTED_REQUEST_DIGESTS = (
    "6170a184bd52b99d68f631ecad65785a91044fad14a41deeb6fc979157f42268",
    "e28e5805439b3c2570f27da4ed56d5e96413008f40cca15554153022aaf35f35",
)
REQUIREMENT_IDS = (
    "RELEASE_OWNER_VERIFIED", "CURRENT_DEFAULT_DENY_CONFIGURATION_VERIFIED",
    "TRANSITION_PROPOSAL_VERIFIED", "ROLLBACK_TARGET_VERIFIED",
    "READ_ONLY_RELEASE_WIRING_ACCEPTED", "GATE_ENABLED_PREAUTH_QUALIFIED",
    EXECUTABLE_REQUEST_QUALIFIED, "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED",
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED", "DEPLOYMENT_ROLLBACK_ATTESTED",
)
MISSING_REASONS = {
    "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED": "missing canonical isolated controlled-runtime acceptance",
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED": "missing canonical production failure-containment acceptance",
    "DEPLOYMENT_ROLLBACK_ATTESTED": "missing canonical deployment/rollback attestation",
}
EVIDENCE_TOPOLOGY = (
    "V5.15.24.7.4.8_HISTORICAL_APPROVAL_REQUEST_DECISION",
    "V5.15.24.7.4.11_EVIDENCE_BUNDLE",
    "V5.15.24.7.4.11_EVIDENCE_BOUND_DECISION",
    "V5.15.24.7.4.12_EXECUTABLE_REQUEST_QUALIFICATION_REPORT",
    "V5.15.24.7.4.12_ORDERED_PER_SKILL_REQUEST_EVIDENCE",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionFeatureGateExecutableRequestBindingAuthorityBoundary:
    approval: bool = False
    application: bool = False
    activation: bool = False
    mutation: bool = False
    persistence: bool = False
    execution: bool = False
    dispatch: bool = False
    calculator: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    delivery: bool = False
    deployment: bool = False
    rollback_execution: bool = False
    response_replacement: bool = False


@dataclass(frozen=True)
class ProductionFeatureGateExecutableRequestApprovalEvidence:
    evidence_type: str
    evidence_version: str
    evidence_scope: str
    requirement_id: str
    report_digest: str
    topology_digest: str
    supported_skill_ids: tuple[str, ...]
    request_ids: tuple[str, ...]
    request_digests: tuple[str, ...]
    observation_digests: tuple[str, ...]
    qualified_skill_count: int
    failed_skill_count: int
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    production_configuration_digest: str
    verified: bool
    evidence_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateExecutableRequestEvidenceBundle:
    version: str
    scope: str
    previous_bundle: ProductionFeatureGateApprovalEvidenceBundle
    previous_decision: ProductionFeatureGateEvidenceBoundDecision
    qualification_report: IsolatedExecutableRequestQualificationReport
    historical_request_digest: str
    historical_decision_digest: str
    previous_bundle_digest: str
    previous_decision_digest: str
    approval_owner_digest: str
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    production_configuration_digest: str
    transition_proposal_digest: str
    rollback_digest: str
    report_digest: str
    topology_digest: str
    supported_skill_ids: tuple[str, ...]
    request_ids: tuple[str, ...]
    request_digests: tuple[str, ...]
    observation_digests: tuple[str, ...]
    evidence: ProductionFeatureGateExecutableRequestApprovalEvidence
    requirement_ids: tuple[str, ...]
    evidence_topology: tuple[str, ...]
    ordered_evidence_digests: tuple[str, ...]
    authority_boundary: ProductionFeatureGateExecutableRequestBindingAuthorityBoundary = ProductionFeatureGateExecutableRequestBindingAuthorityBoundary()
    bundle_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateExecutableRequestBoundRequirement:
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
class ProductionFeatureGateExecutableRequestBoundDecision:
    version: str
    scope: str
    previous_decision: ProductionFeatureGateEvidenceBoundDecision
    evidence_bundle: ProductionFeatureGateExecutableRequestEvidenceBundle
    previous_decision_digest: str
    evidence_bundle_digest: str
    approval_owner_digest: str
    release_owner_digest: str
    release_revision_id: str
    production_configuration_digest: str
    proposal_digest: str
    rollback_digest: str
    report_digest: str
    topology_digest: str
    request_ids: tuple[str, ...]
    request_digests: tuple[str, ...]
    requirements: tuple[ProductionFeatureGateExecutableRequestBoundRequirement, ...]
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
    authority_boundary: ProductionFeatureGateExecutableRequestBindingAuthorityBoundary = ProductionFeatureGateExecutableRequestBindingAuthorityBoundary()
    decision_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal: return {"$decimal": str(value)}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported executable-request binding material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
                     allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _material(value: Any, omitted: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != omitted)


def _boundary_false(value: Any) -> bool:
    return type(value) is ProductionFeatureGateExecutableRequestBindingAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and getattr(value, f.name) is False for f in fields(value))


def _report_is_exact_and_compatible(report: Any, previous: Any) -> bool:
    if type(report) is not IsolatedExecutableRequestQualificationReport: return False
    if not verify_isolated_executable_request_qualification_report(report): return False
    if (report.version != QUALIFICATION_VERSION or report.scope != QUALIFICATION_SCOPE
            or report.requirement_id != EXECUTABLE_REQUEST_QUALIFIED
            or report.status != QUALIFICATION_STATUS or report.qualified is not True
            or report.supported_skill_ids != SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS
            or report.qualified_skill_count != len(SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS)
            or report.failed_skill_count != 0 or report.report_digest != EXPECTED_REPORT_DIGEST
            or report.topology_digest != EXPECTED_TOPOLOGY_DIGEST
            or report.request_digests != EXPECTED_REQUEST_DIGESTS): return False
    owner = previous.release_owner
    for observation in report.observations:
        request = observation.request
        binding = observation.foundation.configuration_binding
        if (not verify_isolated_executable_request_observation(observation)
                or not verify_versioned_cost_executable_request(request, observation.foundation, observation.preauth_report)
                or binding.release_owner is not owner
                or request.release_owner_digest != previous.release_owner_digest
                or request.release_revision_id != previous.release_revision_id
                or observation.preauth_report.production_configuration_digest
                    != previous.production_configuration_digest
                or any((request.requirement_qualified, request.execute_allowed, request.dispatch_permitted,
                        request.runtime_invocation_permitted, report.execute_allowed,
                        report.dispatch_permitted, report.application_permitted,
                        report.activation_permitted, report.runtime_invocation_permitted))
                or request.execution_result is not None): return False
    return (tuple(x.skill_id for x in report.observations) == report.supported_skill_ids
            and tuple(x.request.request_digest for x in report.observations) == report.request_digests
            and len({x.request.request_id for x in report.observations}) == len(report.observations)
            and (report.calculator_invocation_count, report.bridge_invocation_count,
                 report.admission_invocation_count, report.delivery_invocation_count,
                 report.controlled_runtime_invocation_count) == (0, 0, 0, 0, 0))


def create_production_feature_gate_executable_request_evidence_bundle(
    previous_bundle: Any, previous_decision: Any, qualification_report: Any,
) -> ProductionFeatureGateExecutableRequestEvidenceBundle | None:
    try:
        if type(previous_bundle) is not ProductionFeatureGateApprovalEvidenceBundle: return None
        if type(previous_decision) is not ProductionFeatureGateEvidenceBoundDecision: return None
        if not verify_production_feature_gate_approval_evidence_bundle(previous_bundle): return None
        if not verify_production_feature_gate_evidence_bound_decision(previous_decision): return None
        if (previous_decision.evidence_bundle != previous_bundle
                or previous_decision.decision_digest != EXPECTED_PREVIOUS_DECISION_DIGEST
                or previous_decision.verified_requirement_count != 6
                or previous_decision.primary_denial != EXECUTABLE_REQUEST_QUALIFIED): return None
        if not _report_is_exact_and_compatible(qualification_report, previous_decision): return None
        report = qualification_report
        request_ids = tuple(x.request.request_id for x in report.observations)
        observation_digests = tuple(x.observation_digest for x in report.observations)
        evidence_draft = ProductionFeatureGateExecutableRequestApprovalEvidence(
            type(report).__name__, report.version, report.scope, EXECUTABLE_REQUEST_QUALIFIED,
            report.report_digest, report.topology_digest, report.supported_skill_ids, request_ids,
            report.request_digests, observation_digests, report.qualified_skill_count,
            report.failed_skill_count, previous_bundle.release_owner_digest,
            previous_bundle.release_revision_id, previous_bundle.release_revision_digest,
            previous_bundle.production_configuration_digest, True)
        evidence = replace(evidence_draft, evidence_digest=_digest(
            "EXECUTABLE_REQUEST_APPROVAL_EVIDENCE", _material(evidence_draft, "evidence_digest")))
        draft = ProductionFeatureGateExecutableRequestEvidenceBundle(
            VERSION, SCOPE, previous_bundle, previous_decision, report,
            previous_bundle.historical_request_digest, previous_bundle.historical_decision_digest,
            previous_bundle.bundle_digest, previous_decision.decision_digest,
            previous_decision.approval_owner_digest, previous_bundle.release_owner_digest,
            previous_bundle.release_revision_id, previous_bundle.release_revision_digest,
            previous_bundle.production_configuration_digest, previous_bundle.transition_proposal_digest,
            previous_bundle.rollback_digest, report.report_digest, report.topology_digest,
            report.supported_skill_ids, request_ids, report.request_digests, observation_digests,
            evidence, REQUIREMENT_IDS, EVIDENCE_TOPOLOGY,
            tuple(x.evidence_digest for x in previous_bundle.evidence) + (evidence.evidence_digest,))
        return replace(draft, bundle_digest=_digest("EVIDENCE_BUNDLE", _material(draft, "bundle_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_production_feature_gate_executable_request_evidence(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateExecutableRequestApprovalEvidence: return False
        return (value.verified is True and value.requirement_id == EXECUTABLE_REQUEST_QUALIFIED
                and value.report_digest == EXPECTED_REPORT_DIGEST
                and value.topology_digest == EXPECTED_TOPOLOGY_DIGEST
                and value.request_digests == EXPECTED_REQUEST_DIGESTS
                and bool(_HEX.fullmatch(value.evidence_digest))
                and value.evidence_digest == _digest("EXECUTABLE_REQUEST_APPROVAL_EVIDENCE",
                                                     _material(value, "evidence_digest")))
    except (AttributeError, TypeError, ValueError): return False


def verify_production_feature_gate_executable_request_evidence_bundle(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateExecutableRequestEvidenceBundle: return False
        if (value.requirement_ids != REQUIREMENT_IDS or value.evidence_topology != EVIDENCE_TOPOLOGY
                or value.previous_decision_digest != EXPECTED_PREVIOUS_DECISION_DIGEST
                or value.report_digest != EXPECTED_REPORT_DIGEST
                or value.topology_digest != EXPECTED_TOPOLOGY_DIGEST
                or value.request_digests != EXPECTED_REQUEST_DIGESTS
                or value.request_ids != tuple(x.request.request_id for x in value.qualification_report.observations)
                or value.ordered_evidence_digests != tuple(x.evidence_digest for x in value.previous_bundle.evidence)
                    + (value.evidence.evidence_digest,)
                or not _boundary_false(value.authority_boundary)
                or not _HEX.fullmatch(value.bundle_digest)): return False
        expected = create_production_feature_gate_executable_request_evidence_bundle(
            value.previous_bundle, value.previous_decision, value.qualification_report)
        return (expected is not None and value == expected
                and verify_production_feature_gate_executable_request_evidence(value.evidence)
                and bool(_HEX.fullmatch(value.bundle_digest)))
    except (AttributeError, TypeError, ValueError): return False


def _requirement(identifier: str, source: Any | None, verified: bool, reason: str):
    if source is None:
        args = (identifier, True, None, None, None, None, None, None, False, reason)
    else:
        args = (identifier, True, source.evidence_type, source.evidence_version, source.evidence_scope,
                source.evidence_digest, source.report_digest, source.topology_digest, verified, reason)
    draft = ProductionFeatureGateExecutableRequestBoundRequirement(*args)
    return replace(draft, requirement_digest=_digest("BOUND_REQUIREMENT", _material(draft, "requirement_digest")))


def evaluate_production_feature_gate_executable_request_bound_approval(bundle: Any):
    if not verify_production_feature_gate_executable_request_evidence_bundle(bundle): return None
    previous = bundle.previous_decision
    requirements = tuple(_requirement(
        old.requirement_id, old, True, old.reason) for old in previous.requirements[:6])
    requirements += (_requirement(EXECUTABLE_REQUEST_QUALIFIED, bundle.evidence, True,
                                  "exact canonical executable-request qualification report strictly verified and evidence-bound"),)
    requirements += tuple(_requirement(x, None, False, MISSING_REASONS[x]) for x in REQUIREMENT_IDS[7:])
    missing = tuple(x for x in requirements if not x.verified)
    draft = ProductionFeatureGateExecutableRequestBoundDecision(
        VERSION, SCOPE, previous, bundle, previous.decision_digest, bundle.bundle_digest,
        bundle.approval_owner_digest, bundle.release_owner_digest, bundle.release_revision_id,
        bundle.production_configuration_digest, bundle.transition_proposal_digest, bundle.rollback_digest,
        bundle.report_digest, bundle.topology_digest, bundle.request_ids, bundle.request_digests,
        requirements, 7, 3, TRANSITION_NOT_APPROVED, missing[0].requirement_id,
        tuple(x.reason for x in missing))
    return replace(draft, decision_digest=_digest("BOUND_DECISION", _material(draft, "decision_digest")))


def verify_production_feature_gate_executable_request_bound_decision(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateExecutableRequestBoundDecision: return False
        if (tuple(x.requirement_id for x in value.requirements) != REQUIREMENT_IDS
                or len({x.requirement_id for x in value.requirements}) != 10): return False
        if (not all(x.verified for x in value.requirements[:7])
                or not all(not x.verified and x.evidence_digest is None and x.report_digest is None
                           and x.topology_digest is None for x in value.requirements[7:])): return False
        if (value.verified_requirement_count != 7 or value.missing_requirement_count != 3
                or value.status != TRANSITION_NOT_APPROVED
                or value.primary_denial != "ISOLATED_CONTROLLED_RUNTIME_ACCEPTED"
                or value.reasons != tuple(MISSING_REASONS[x] for x in REQUIREMENT_IDS[7:])
                or value.transition_approved is not False or value.application_permitted is not False
                or value.activation_permitted is not False or value.transition_applied is not False
                or value.executable_output is not None or not _boundary_false(value.authority_boundary)
                or not _HEX.fullmatch(value.decision_digest)): return False
        expected = evaluate_production_feature_gate_executable_request_bound_approval(value.evidence_bundle)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError): return False


__all__ = tuple(name for name in globals() if name.startswith("ProductionFeatureGateExecutableRequest")
                or name.startswith(("create_production_", "verify_production_", "evaluate_production_"))
                or name in ("VERSION", "SCOPE", "REQUIREMENT_IDS", "MISSING_REASONS", "EVIDENCE_TOPOLOGY",
                            "EXPECTED_PREVIOUS_DECISION_DIGEST", "EXPECTED_REPORT_DIGEST",
                            "EXPECTED_TOPOLOGY_DIGEST", "EXPECTED_REQUEST_DIGESTS"))
