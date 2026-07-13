"""V5.15.24 isolated acceptance for controlled cost runtime integration.

The harness consumes a preconstructed canonical manifest and invokes only the
pure V5.15.23 admission boundary.  It never constructs production responses,
routes, commits, persists, invokes tools, or changes feature-gate state.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any

from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_cost_response_runtime_bridge import FEATURE_GATE_NAME
from brain.business_skill_cost_runtime_integration_admission_gateway import (
    ControlledRuntimeIntegrationAdmissionRequest,
    ControlledRuntimeIntegrationAdmissionDecision,
    decide_controlled_runtime_integration_admission,
    verify_controlled_runtime_integration_admission_decision,
)
from brain.business_skill_cost_runtime_integration_manifest import (
    AuthorityBoundary,
    ControlledRuntimeIntegrationManifest,
    verify_controlled_integration_manifest,
)

ISOLATED_CONTROLLED_RUNTIME_INTEGRATION_ACCEPTANCE_VERSION = "5.15.24"
SCENARIO_TYPE_POSITIVE = "POSITIVE_GATEWAY_ADMISSION"
SCENARIO_TYPE_NEGATIVE = "NEGATIVE_GATEWAY_ADMISSION"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_INVALID_MANIFEST = "INVALID_OR_NONCANONICAL_MANIFEST"

CANONICAL_SCENARIO_SPECS = (
    ("01.change_analysis.valid", "cost.change_analysis.v1", SCENARIO_TYPE_POSITIVE, True, None),
    ("02.per_unit.valid", "cost.per_unit_calculation.v1", SCENARIO_TYPE_POSITIVE, True, None),
    ("03.unknown_skill", "unknown.cost.skill", SCENARIO_TYPE_NEGATIVE, False, "UNSUPPORTED_OR_MALFORMED_SKILL_ID"),
    ("04.feature_gate_false", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("05.feature_gate_wrong_identity", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("06.historical_bridge", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("07.request_digest_mismatch", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("08.same_id_substituted_request", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("09.payload_substitution", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("10.delivery_qualification_substitution", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("11.cross_skill_qualification_approval", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("12.partial_reordered_invalid_manifest", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("13.provenance_tampering", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("14.authority_escalation", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
    ("15.wrong_integration_scope", "cost.change_analysis.v1", SCENARIO_TYPE_NEGATIVE, False, _INVALID_MANIFEST),
)
CANONICAL_SCENARIO_IDS = tuple(x[0] for x in CANONICAL_SCENARIO_SPECS)


def _digest(value: Any) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return ""
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class IntegrationAcceptanceScenario:
    scenario_id: str
    skill_id: str
    scenario_type: str
    expected_admitted: bool
    expected_denial_code: str | None
    admission_request: ControlledRuntimeIntegrationAdmissionRequest
    evidence_skill_id: str
    scenario_digest: str


@dataclass(frozen=True)
class IntegrationAcceptanceObservation:
    acceptance_version: str
    scenario_id: str
    scenario_type: str
    skill_id: str
    evidence_skill_id: str
    request_id: str
    request_digest: str
    payload_digest: str
    delivery_qualification_digest: str
    bridge_result_digest: str
    handoff_digest: str
    qualification_digest: str
    approval_digest: str
    manifest_digest: str
    admission_decision_digest: str
    feature_gate_name: str
    feature_gate_state: bool
    integration_scope: str
    expected_admitted: bool
    observed_admitted: bool
    expected_denial_code: str | None
    observed_denial_code: str | None
    request_integrity_verified: bool
    provenance_verified: bool
    authority_boundary_verified: bool
    side_effect_isolation_verified: bool
    executable_output: None
    observation_passed: bool
    reasons: tuple[str, ...]
    diagnostics: tuple[tuple[str, str], ...]
    observation_digest: str


@dataclass(frozen=True)
class IntegrationAcceptanceReport:
    acceptance_version: str
    registry_version: str
    scenario_ids: tuple[str, ...]
    observation_digests: tuple[str, ...]
    observations: tuple[IntegrationAcceptanceObservation, ...]
    passed_count: int
    failed_count: int
    all_passed: bool
    authority_boundary_verified: bool
    side_effect_isolation_verified: bool
    diagnostics: tuple[tuple[str, str], ...]
    report_digest: str


def _scenario_material(x: IntegrationAcceptanceScenario) -> tuple[Any, ...]:
    manifest = x.admission_request.manifest
    return (ISOLATED_CONTROLLED_RUNTIME_INTEGRATION_ACCEPTANCE_VERSION,
        x.scenario_id, x.skill_id, x.scenario_type, x.expected_admitted,
        x.expected_denial_code, x.evidence_skill_id,
        getattr(manifest, "manifest_digest", ""),
        tuple(getattr(a, "approval_digest", "") for a in getattr(manifest, "approvals", ())))


def _make_scenario(spec: tuple[Any, ...], request: ControlledRuntimeIntegrationAdmissionRequest,
        evidence_skill_id: str) -> IntegrationAcceptanceScenario:
    draft = IntegrationAcceptanceScenario(*spec, request, evidence_skill_id, "")
    return replace(draft, scenario_digest=_digest(_scenario_material(draft)))


def _replace_qualification(manifest: ControlledRuntimeIntegrationManifest, index: int, qualification: Any):
    approvals = list(manifest.approvals)
    approvals[index] = replace(approvals[index], qualification=qualification)
    return replace(manifest, approvals=tuple(approvals))


def _replace_bridge(manifest: ControlledRuntimeIntegrationManifest, **changes: Any):
    qualification = manifest.approvals[0].qualification
    bridge = replace(qualification.runtime_bridge_result, **changes)
    return _replace_qualification(manifest, 0, replace(qualification, runtime_bridge_result=bridge))


def build_canonical_acceptance_scenarios(manifest: Any) -> tuple[IntegrationAcceptanceScenario, ...]:
    """Create isolated gateway inputs from one preconstructed canonical bundle."""
    if not verify_controlled_integration_manifest(manifest):
        raise ValueError("a strictly verified preconstructed canonical manifest is required")
    first, second = manifest.approvals
    q = first.qualification
    bridge = q.runtime_bridge_result
    handoff = bridge.handoff
    other = second.qualification

    manifests = [manifest, manifest, manifest]
    manifests.append(_replace_bridge(manifest, feature_gate_passed=False,
        handoff=replace(handoff, feature_gate_passed=False)))
    manifests.append(_replace_bridge(manifest, feature_gate_name="*",
        handoff=replace(handoff, feature_gate_name="*")))
    manifests.append(_replace_bridge(manifest, bridge_version="5.15.20"))
    manifests.append(_replace_bridge(manifest, request_digest="0" * 64))
    substituted_request = replace(bridge.canonical_request, scope="SUBSTITUTED_SCOPE")
    manifests.append(_replace_bridge(manifest, canonical_request=substituted_request))
    manifests.append(_replace_bridge(manifest,
        handoff=replace(handoff, payload_digest=other.payload_digest)))
    manifests.append(_replace_qualification(manifest, 0,
        replace(q, delivery_qualification=other.delivery_qualification)))
    manifests.append(_replace_qualification(manifest, 0, other))
    manifests.append(replace(manifest, approvals=(first,)))
    manifests.append(_replace_qualification(manifest, 0, replace(q, provenance_verified=False)))
    approvals = (replace(first, authority_boundary=replace(first.authority_boundary, routing=True)), second)
    manifests.append(replace(manifest, approvals=approvals))
    manifests.append(replace(manifest, integration_scope="WRONG_INTEGRATION_SCOPE"))

    scenarios = []
    for index, (spec, source) in enumerate(zip(CANONICAL_SCENARIO_SPECS, manifests)):
        skill_id = spec[1]
        evidence_skill = skill_id if index < 2 else first.skill_id
        scenarios.append(_make_scenario(spec,
            ControlledRuntimeIntegrationAdmissionRequest(skill_id, source), evidence_skill))
    return tuple(scenarios)


def verify_integration_acceptance_scenario(value: Any) -> bool:
    try:
        if type(value) is not IntegrationAcceptanceScenario or not _HEX.fullmatch(value.scenario_digest):
            return False
        index = CANONICAL_SCENARIO_IDS.index(value.scenario_id)
        spec = CANONICAL_SCENARIO_SPECS[index]
        return (type(value.admission_request) is ControlledRuntimeIntegrationAdmissionRequest
            and (value.scenario_id, value.skill_id, value.scenario_type,
                value.expected_admitted, value.expected_denial_code) == spec
            and value.admission_request.skill_id == value.skill_id
            and value.scenario_digest == _digest(_scenario_material(value)))
    except (AttributeError, TypeError, ValueError):
        return False


def _approval_for_scenario(scenario: IntegrationAcceptanceScenario):
    approvals = getattr(scenario.admission_request.manifest, "approvals", ())
    return next((a for a in approvals if getattr(a, "skill_id", None) == scenario.evidence_skill_id),
        approvals[0] if approvals else None)


def _observation_material(x: IntegrationAcceptanceObservation) -> tuple[Any, ...]:
    return tuple((name, getattr(x, name)) for name in x.__dataclass_fields__
        if name != "observation_digest")


def observe_integration_acceptance_scenario(scenario: Any) -> IntegrationAcceptanceObservation:
    if not verify_integration_acceptance_scenario(scenario):
        raise ValueError("canonical acceptance scenario required")
    registry_before = tuple(get_business_skill_registry())
    decision = decide_controlled_runtime_integration_admission(scenario.admission_request)
    registry_after = tuple(get_business_skill_registry())
    manifest = scenario.admission_request.manifest
    approval = _approval_for_scenario(scenario)
    qualification = getattr(approval, "qualification", None)
    bridge = getattr(qualification, "runtime_bridge_result", None)
    handoff = getattr(bridge, "handoff", None)
    delivery = getattr(qualification, "delivery_qualification", None)
    binding = getattr(delivery, "binding", None)
    decision_ok = verify_controlled_runtime_integration_admission_decision(
        decision, scenario.admission_request)
    request_integrity = bool(decision_ok and _HEX.fullmatch(decision.decision_digest)
        and (not decision.admitted or (decision.request_digest == getattr(bridge, "request_digest", "")
            == getattr(handoff, "request_digest", "") == getattr(qualification, "request_digest", ""))))
    provenance = bool(decision_ok and (not decision.admitted or decision.provenance_verified))
    authority = bool(decision_ok and decision.authority_boundary == AuthorityBoundary()
        and decision.executable_output is None)
    isolation = bool(registry_before == registry_after and FEATURE_GATE_NAME ==
        "LIMITED_COST_RESPONSE_RUNTIME_BRIDGE" and authority)
    outcome_ok = (decision.admitted is scenario.expected_admitted and
        decision.primary_denial_code == scenario.expected_denial_code)
    passed = bool(decision_ok and request_integrity and provenance and authority and isolation and outcome_ok)
    reasons = ("ACCEPTANCE_SCENARIO_PASSED",) if passed else tuple(code for code, ok in (
        ("DECISION_INTEGRITY_FAILED", decision_ok),
        ("REQUEST_INTEGRITY_FAILED", request_integrity),
        ("PROVENANCE_FAILED", provenance),
        ("AUTHORITY_BOUNDARY_FAILED", authority),
        ("SIDE_EFFECT_ISOLATION_FAILED", isolation),
        ("ADMISSION_OUTCOME_MISMATCH", outcome_ok)) if not ok)
    diagnostics = (("classification", "GATEWAY_ADMISSION_SCENARIO"),
        ("production_authority", "NONE"), ("feature_gate_mutated", "FALSE"),
        ("side_effects", "NONE"))
    values = dict(acceptance_version=ISOLATED_CONTROLLED_RUNTIME_INTEGRATION_ACCEPTANCE_VERSION,
        scenario_id=scenario.scenario_id, scenario_type=scenario.scenario_type,
        skill_id=scenario.skill_id, evidence_skill_id=scenario.evidence_skill_id,
        request_id=getattr(handoff, "request_id", ""),
        request_digest=getattr(bridge, "request_digest", ""),
        payload_digest=getattr(handoff, "payload_digest", ""),
        delivery_qualification_digest=getattr(binding, "qualification_digest", ""),
        bridge_result_digest=getattr(bridge, "result_digest", ""),
        handoff_digest=getattr(handoff, "handoff_digest", ""),
        qualification_digest=getattr(qualification, "qualification_digest", ""),
        approval_digest=getattr(approval, "approval_digest", ""),
        manifest_digest=getattr(manifest, "manifest_digest", ""),
        admission_decision_digest=decision.decision_digest,
        feature_gate_name=getattr(bridge, "feature_gate_name", "") or "",
        feature_gate_state=getattr(bridge, "feature_gate_passed", False) is True,
        integration_scope=getattr(manifest, "integration_scope", ""),
        expected_admitted=scenario.expected_admitted, observed_admitted=decision.admitted,
        expected_denial_code=scenario.expected_denial_code,
        observed_denial_code=decision.primary_denial_code,
        request_integrity_verified=request_integrity, provenance_verified=provenance,
        authority_boundary_verified=authority, side_effect_isolation_verified=isolation,
        executable_output=None, observation_passed=passed, reasons=reasons,
        diagnostics=diagnostics)
    draft = IntegrationAcceptanceObservation(**values, observation_digest="")
    return replace(draft, observation_digest=_digest(_observation_material(draft)))


def verify_integration_acceptance_observation(value: Any, scenario: Any) -> bool:
    try:
        if type(value) is not IntegrationAcceptanceObservation:
            return False
        if any(not _HEX.fullmatch(x) for x in (value.observation_digest,
                value.admission_decision_digest, value.manifest_digest,
                value.approval_digest, value.qualification_digest,
                value.bridge_result_digest, value.handoff_digest,
                value.request_digest, value.payload_digest,
                value.delivery_qualification_digest)):
            return False
        expected = observe_integration_acceptance_scenario(scenario)
        return value == expected and value.observation_digest == _digest(_observation_material(value))
    except (AttributeError, TypeError, ValueError):
        return False


def _report_material(x: IntegrationAcceptanceReport) -> tuple[Any, ...]:
    return tuple((name, tuple(o.observation_digest for o in x.observations)
        if name == "observations" else getattr(x, name))
        for name in x.__dataclass_fields__ if name != "report_digest")


def create_integration_acceptance_report(scenarios: Any) -> IntegrationAcceptanceReport:
    source = tuple(scenarios)
    if tuple(getattr(x, "scenario_id", None) for x in source) != CANONICAL_SCENARIO_IDS:
        raise ValueError("full canonical ordered scenario matrix required")
    if not all(verify_integration_acceptance_scenario(x) for x in source):
        raise ValueError("invalid acceptance scenario")
    observations = tuple(observe_integration_acceptance_scenario(x) for x in source)
    passed = sum(x.observation_passed for x in observations)
    failed = len(observations) - passed
    authority = all(x.authority_boundary_verified for x in observations)
    isolation = all(x.side_effect_isolation_verified for x in observations)
    diagnostics = (("classification", "ISOLATED_GATEWAY_ACCEPTANCE"),
        ("post_decision_tampering_in_report", "FALSE"),
        ("production_activation", "FALSE"))
    values = dict(acceptance_version=ISOLATED_CONTROLLED_RUNTIME_INTEGRATION_ACCEPTANCE_VERSION,
        registry_version=BUSINESS_SKILL_REGISTRY_VERSION, scenario_ids=CANONICAL_SCENARIO_IDS,
        observation_digests=tuple(x.observation_digest for x in observations),
        observations=observations, passed_count=passed, failed_count=failed,
        all_passed=(passed == len(CANONICAL_SCENARIO_IDS)),
        authority_boundary_verified=authority, side_effect_isolation_verified=isolation,
        diagnostics=diagnostics)
    draft = IntegrationAcceptanceReport(**values, report_digest="")
    return replace(draft, report_digest=_digest(_report_material(draft)))


def verify_integration_acceptance_report(value: Any, scenarios: Any) -> bool:
    try:
        source = tuple(scenarios)
        if type(value) is not IntegrationAcceptanceReport or not _HEX.fullmatch(value.report_digest):
            return False
        if value.scenario_ids != CANONICAL_SCENARIO_IDS or len(set(value.scenario_ids)) != len(value.scenario_ids):
            return False
        expected = create_integration_acceptance_report(source)
        return (value == expected and value.report_digest == _digest(_report_material(value))
            and all(verify_integration_acceptance_observation(o, s)
                for o, s in zip(value.observations, source)))
    except (AttributeError, TypeError, ValueError):
        return False
