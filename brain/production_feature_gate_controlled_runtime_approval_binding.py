"""V5.15.24.7.4.15 immutable controlled-runtime approval evidence binding.

This passive layer binds the exact recorded V5.15.24.7.4.14 acceptance report
to the existing approval chain.  It grants no production or runtime authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_feature_gate_executable_request_approval_binding import (
    ProductionFeatureGateExecutableRequestEvidenceBundle,
    ProductionFeatureGateExecutableRequestBoundDecision,
    verify_production_feature_gate_executable_request_evidence_bundle,
    verify_production_feature_gate_executable_request_bound_decision,
)
from brain.production_feature_gate_transition_approval import TRANSITION_NOT_APPROVED
from brain.recorded_controlled_runtime_acceptance import (
    RecordedControlledRuntimeAcceptanceReport,
    REQUIREMENT as CONTROLLED_RUNTIME_REQUIREMENT,
    SCOPE as REPORT_SCOPE,
    STATUS as REPORT_STATUS,
    VERSION as REPORT_VERSION,
    verify_recorded_controlled_runtime_acceptance_report,
)

VERSION = "5.15.24.7.4.15"
SCOPE = "CANONICAL_CONTROLLED_RUNTIME_APPROVAL_EVIDENCE_BINDING"
EXPECTED_PREVIOUS_DECISION_DIGEST = "78f4fdf0d1a1d909596f3e6966df95e61c1ce3f0f178fb0022f98d81eaf36fea"
EXPECTED_REPORT_DIGEST = "1cecc90c5a5df536d9e89535bcf6e1eb6c5815f0d0dc88cb9d0251d5f30227df"
EXPECTED_TOPOLOGY_DIGEST = "d836864672edd6ae327b4dd5696915e0825a5daad84c13eea3a1207ed135bbf6"
EXPECTED_ADMISSION_BATCH_DIGEST = "df88fe0cc5d919a172f5d4a0e8d4cd99ceb00664366097c3fd06ce9e8da6b7ca"
REQUIREMENT_IDS = (
    "RELEASE_OWNER_VERIFIED", "CURRENT_DEFAULT_DENY_CONFIGURATION_VERIFIED",
    "TRANSITION_PROPOSAL_VERIFIED", "ROLLBACK_TARGET_VERIFIED",
    "READ_ONLY_RELEASE_WIRING_ACCEPTED", "GATE_ENABLED_PREAUTH_QUALIFIED",
    "EXECUTABLE_REQUEST_QUALIFIED", CONTROLLED_RUNTIME_REQUIREMENT,
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED", "DEPLOYMENT_ROLLBACK_ATTESTED",
)
MISSING_REASONS = {
    "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED": "missing canonical production failure-containment acceptance",
    "DEPLOYMENT_ROLLBACK_ATTESTED": "missing canonical deployment/rollback attestation",
}
EVIDENCE_TOPOLOGY = (
    "V5.15.24.7.4.8_HISTORICAL_APPROVAL_REQUEST_DECISION",
    "V5.15.24.7.4.11_EVIDENCE_BUNDLE_DECISION",
    "V5.15.24.7.4.13_EXECUTABLE_REQUEST_EVIDENCE_BUNDLE_DECISION",
    "V5.15.24.7.4.14_RECORDED_CONTROLLED_RUNTIME_ACCEPTANCE_REPORT",
    "V5.15.24.7.4.14_ORDERED_EXECUTION_BRIDGE_ADMISSION_ANCESTRY",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary:
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
    routing: bool = False
    response_commit: bool = False
    production: bool = False
    deployment: bool = False
    rollback_execution: bool = False
    external_tools: bool = False
    network: bool = False


@dataclass(frozen=True)
class ProductionFeatureGateControlledRuntimeApprovalEvidence:
    evidence_type: str
    evidence_version: str
    evidence_scope: str
    requirement_id: str
    report_digest: str
    topology_digest: str
    admission_batch_digest: str
    observation_digests: tuple[str, ...]
    ancestry_topology_digests: tuple[str, ...]
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    production_configuration_digest: str
    isolated_invocation_counts: tuple[int, ...]
    production_invocation_counts: tuple[int, ...]
    verified: bool
    evidence_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateControlledRuntimeEvidenceBundle:
    version: str
    scope: str
    previous_bundle: ProductionFeatureGateExecutableRequestEvidenceBundle
    previous_decision: ProductionFeatureGateExecutableRequestBoundDecision
    acceptance_report: RecordedControlledRuntimeAcceptanceReport
    historical_request_digest: str
    historical_decision_digest: str
    v7411_bundle_digest: str
    v7411_decision_digest: str
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
    admission_batch_digest: str
    evidence: ProductionFeatureGateControlledRuntimeApprovalEvidence
    requirement_ids: tuple[str, ...]
    evidence_topology: tuple[str, ...]
    ordered_evidence_digests: tuple[str, ...]
    authority_boundary: ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary = ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary()
    bundle_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateControlledRuntimeBoundRequirement:
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
class ProductionFeatureGateControlledRuntimeBoundDecision:
    version: str
    scope: str
    previous_decision: ProductionFeatureGateExecutableRequestBoundDecision
    evidence_bundle: ProductionFeatureGateControlledRuntimeEvidenceBundle
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
    requirements: tuple[ProductionFeatureGateControlledRuntimeBoundRequirement, ...]
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
    authority_boundary: ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary = ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary()
    decision_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal: return {"$decimal": str(value)}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[str(k), _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported controlled-runtime binding material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _material(value: Any, omitted: str):
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != omitted)


def _boundary_false(value: Any) -> bool:
    return type(value) is ProductionFeatureGateControlledRuntimeBindingAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and getattr(value, f.name) is False for f in fields(value))


def _report_exact(report: Any) -> bool:
    if type(report) is not RecordedControlledRuntimeAcceptanceReport: return False
    if not verify_recorded_controlled_runtime_acceptance_report(report): return False
    return all((report.version == REPORT_VERSION, report.scope == REPORT_SCOPE,
        report.requirement == CONTROLLED_RUNTIME_REQUIREMENT, report.status == REPORT_STATUS,
        report.qualified is True, report.accepted is True,
        report.report_digest == EXPECTED_REPORT_DIGEST,
        report.topology_digest == EXPECTED_TOPOLOGY_DIGEST,
        report.source_batch.batch_digest == EXPECTED_ADMISSION_BATCH_DIGEST,
        (report.isolated_execution_invocations, report.isolated_calculator_invocations,
         report.isolated_bridge_invocations, report.isolated_admission_invocations,
         report.separate_controlled_runtime_invocations) == (2, 2, 2, 2, 0),
        (report.production_execution_invocations, report.production_calculator_invocations,
         report.production_bridge_invocations, report.production_admission_invocations,
         report.production_runtime_invocations, report.production_delivery_invocations,
         report.production_response_commits) == (0,) * 7))


def create_production_feature_gate_controlled_runtime_evidence_bundle(
    previous_bundle: Any, previous_decision: Any, acceptance_report: Any,
) -> ProductionFeatureGateControlledRuntimeEvidenceBundle | None:
    try:
        if type(previous_bundle) is not ProductionFeatureGateExecutableRequestEvidenceBundle: return None
        if type(previous_decision) is not ProductionFeatureGateExecutableRequestBoundDecision: return None
        if not verify_production_feature_gate_executable_request_evidence_bundle(previous_bundle): return None
        if not verify_production_feature_gate_executable_request_bound_decision(previous_decision): return None
        if (previous_decision.evidence_bundle != previous_bundle
                or previous_decision.decision_digest != EXPECTED_PREVIOUS_DECISION_DIGEST
                or previous_decision.verified_requirement_count != 7
                or previous_decision.primary_denial != CONTROLLED_RUNTIME_REQUIREMENT): return None
        if not _report_exact(acceptance_report): return None
        report = acceptance_report
        old11 = previous_bundle.previous_bundle
        old11_decision = previous_bundle.previous_decision
        ancestry = tuple(report.observations[0].upstream_topology_digests)
        isolated = (report.isolated_execution_invocations, report.isolated_calculator_invocations,
            report.isolated_bridge_invocations, report.isolated_admission_invocations,
            report.separate_controlled_runtime_invocations)
        production = (report.production_execution_invocations, report.production_calculator_invocations,
            report.production_bridge_invocations, report.production_admission_invocations,
            report.production_runtime_invocations, report.production_delivery_invocations,
            report.production_response_commits)
        evidence_draft = ProductionFeatureGateControlledRuntimeApprovalEvidence(
            type(report).__name__, report.version, report.scope, report.requirement,
            report.report_digest, report.topology_digest, report.source_batch.batch_digest,
            report.observation_digests, ancestry, previous_bundle.release_owner_digest,
            previous_bundle.release_revision_id, previous_bundle.release_revision_digest,
            previous_bundle.production_configuration_digest, isolated, production, True)
        evidence = replace(evidence_draft, evidence_digest=_digest(
            "CONTROLLED_RUNTIME_APPROVAL_EVIDENCE", _material(evidence_draft, "evidence_digest")))
        draft = ProductionFeatureGateControlledRuntimeEvidenceBundle(
            VERSION, SCOPE, previous_bundle, previous_decision, report,
            old11.historical_request_digest, old11.historical_decision_digest,
            old11.bundle_digest, old11_decision.decision_digest, previous_bundle.bundle_digest,
            previous_decision.decision_digest, previous_bundle.approval_owner_digest,
            previous_bundle.release_owner_digest, previous_bundle.release_revision_id,
            previous_bundle.release_revision_digest, previous_bundle.production_configuration_digest,
            previous_bundle.transition_proposal_digest, previous_bundle.rollback_digest,
            report.report_digest, report.topology_digest, report.source_batch.batch_digest,
            evidence, REQUIREMENT_IDS, EVIDENCE_TOPOLOGY,
            previous_bundle.ordered_evidence_digests + (evidence.evidence_digest,))
        return replace(draft, bundle_digest=_digest("EVIDENCE_BUNDLE", _material(draft, "bundle_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError, IndexError): return None


def verify_production_feature_gate_controlled_runtime_evidence(value: Any) -> bool:
    try:
        return (type(value) is ProductionFeatureGateControlledRuntimeApprovalEvidence
            and value.verified is True and value.requirement_id == CONTROLLED_RUNTIME_REQUIREMENT
            and value.report_digest == EXPECTED_REPORT_DIGEST
            and value.topology_digest == EXPECTED_TOPOLOGY_DIGEST
            and value.admission_batch_digest == EXPECTED_ADMISSION_BATCH_DIGEST
            and value.isolated_invocation_counts == (2, 2, 2, 2, 0)
            and value.production_invocation_counts == (0,) * 7
            and bool(_HEX.fullmatch(value.evidence_digest))
            and value.evidence_digest == _digest("CONTROLLED_RUNTIME_APPROVAL_EVIDENCE",
                _material(value, "evidence_digest")))
    except (AttributeError, TypeError, ValueError): return False


def verify_production_feature_gate_controlled_runtime_evidence_bundle(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateControlledRuntimeEvidenceBundle: return False
        if (value.requirement_ids != REQUIREMENT_IDS or value.evidence_topology != EVIDENCE_TOPOLOGY
                or value.previous_decision_digest != EXPECTED_PREVIOUS_DECISION_DIGEST
                or value.report_digest != EXPECTED_REPORT_DIGEST
                or value.topology_digest != EXPECTED_TOPOLOGY_DIGEST
                or value.admission_batch_digest != EXPECTED_ADMISSION_BATCH_DIGEST
                or value.ordered_evidence_digests != value.previous_bundle.ordered_evidence_digests
                    + (value.evidence.evidence_digest,)
                or not verify_production_feature_gate_controlled_runtime_evidence(value.evidence)
                or not _boundary_false(value.authority_boundary)
                or not _HEX.fullmatch(value.bundle_digest)): return False
        expected = create_production_feature_gate_controlled_runtime_evidence_bundle(
            value.previous_bundle, value.previous_decision, value.acceptance_report)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError): return False


def _requirement(identifier: str, source: Any | None, reason: str):
    args = ((identifier, True, None, None, None, None, None, None, False, reason) if source is None else
        (identifier, True, source.evidence_type, source.evidence_version, source.evidence_scope,
         source.evidence_digest, source.report_digest, source.topology_digest, True, reason))
    draft = ProductionFeatureGateControlledRuntimeBoundRequirement(*args)
    return replace(draft, requirement_digest=_digest("BOUND_REQUIREMENT", _material(draft, "requirement_digest")))


def evaluate_production_feature_gate_controlled_runtime_bound_approval(bundle: Any):
    if not verify_production_feature_gate_controlled_runtime_evidence_bundle(bundle): return None
    previous = bundle.previous_decision
    requirements = tuple(_requirement(x.requirement_id, x, x.reason) for x in previous.requirements[:7])
    requirements += (_requirement(CONTROLLED_RUNTIME_REQUIREMENT, bundle.evidence,
        "exact canonical recorded controlled-runtime acceptance report strictly verified and evidence-bound"),)
    requirements += tuple(_requirement(x, None, MISSING_REASONS[x]) for x in REQUIREMENT_IDS[8:])
    missing = tuple(x for x in requirements if not x.verified)
    draft = ProductionFeatureGateControlledRuntimeBoundDecision(
        VERSION, SCOPE, previous, bundle, previous.decision_digest, bundle.bundle_digest,
        bundle.approval_owner_digest, bundle.release_owner_digest, bundle.release_revision_id,
        bundle.production_configuration_digest, bundle.transition_proposal_digest, bundle.rollback_digest,
        bundle.report_digest, bundle.topology_digest, requirements, 8, 2, TRANSITION_NOT_APPROVED,
        missing[0].requirement_id, tuple(x.reason for x in missing))
    return replace(draft, decision_digest=_digest("BOUND_DECISION", _material(draft, "decision_digest")))


def verify_production_feature_gate_controlled_runtime_bound_decision(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateControlledRuntimeBoundDecision: return False
        if tuple(x.requirement_id for x in value.requirements) != REQUIREMENT_IDS: return False
        if len({x.requirement_id for x in value.requirements}) != 10: return False
        if not all(x.verified for x in value.requirements[:8]): return False
        if not all(not x.verified and x.evidence_digest is None and x.report_digest is None
                   and x.topology_digest is None for x in value.requirements[8:]): return False
        if (value.verified_requirement_count != 8 or value.missing_requirement_count != 2
                or value.status != TRANSITION_NOT_APPROVED
                or value.primary_denial != "PRODUCTION_FAILURE_CONTAINMENT_ACCEPTED"
                or value.reasons != tuple(MISSING_REASONS[x] for x in REQUIREMENT_IDS[8:])
                or any((value.transition_approved, value.application_permitted,
                        value.activation_permitted, value.transition_applied))
                or value.executable_output is not None or not _boundary_false(value.authority_boundary)
                or not _HEX.fullmatch(value.decision_digest)): return False
        expected = evaluate_production_feature_gate_controlled_runtime_bound_approval(value.evidence_bundle)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError): return False


__all__ = tuple(name for name in globals() if name.startswith("ProductionFeatureGateControlledRuntime")
    or name.startswith(("create_production_", "verify_production_", "evaluate_production_"))
    or name in ("VERSION", "SCOPE", "REQUIREMENT_IDS", "MISSING_REASONS", "EVIDENCE_TOPOLOGY",
                "EXPECTED_PREVIOUS_DECISION_DIGEST", "EXPECTED_REPORT_DIGEST",
                "EXPECTED_TOPOLOGY_DIGEST", "EXPECTED_ADMISSION_BATCH_DIGEST"))
