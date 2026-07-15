"""Immutable isolated acceptance for the current default-denied boundary.

The caller supplies already-created production evidence.  This module only
copies immutable artifacts, evaluates the pure V5.15.24.7.3 boundary, and
records what that boundary actually returned.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
from datetime import datetime
import hashlib
import json
import re
from typing import Any

from brain.production_default_denied_admission_boundary import (
    DENIED_DEFAULT_PRODUCTION_GATE,
    DENIED_INVALID_PRODUCTION_EVIDENCE,
    DENIED_MALFORMED_REQUEST,
    DENIED_SKILL_IDENTITY_MISMATCH,
    INVALID_PRODUCTION_ADMISSION_EVIDENCE,
    MALFORMED_PRODUCTION_ADMISSION_REQUEST,
    PRODUCTION_FEATURE_GATE_DEFAULT_DENIED,
    PRODUCTION_SKILL_IDENTITY_MISMATCH,
    ProductionAdmissionBoundaryDecision,
    ProductionAdmissionBoundaryRequest,
    evaluate_default_denied_production_admission,
    verify_production_admission_boundary_decision,
    verify_production_admission_boundary_request,
)
from brain.production_single_skill_admission_evidence import (
    ProductionSingleSkillAdmissionEvidence,
    verify_production_single_skill_admission_evidence,
)

ISOLATED_DEFAULT_DENIED_PRODUCTION_ADMISSION_ACCEPTANCE_VERSION = "5.15.24.7.4"
ISOLATED_DEFAULT_DENIED_PRODUCTION_ADMISSION_ACCEPTANCE_SCOPE = (
    "CURRENT_DEFAULT_DENIED_PRODUCTION_ADMISSION_BOUNDARY_ACCEPTANCE")
BOUNDARY_ACCEPTANCE = "BOUNDARY_ACCEPTANCE"
VALID_DEFAULT_DENIED = "VALID_DEFAULT_DENIED"
INVALID_FAIL_CLOSED = "INVALID_FAIL_CLOSED"
_HEX = re.compile(r"^[0-9a-f]{64}$")

CANONICAL_SCENARIO_IDS = (
    "01.change_analysis.valid_default_denied",
    "02.per_unit.valid_default_denied",
    "03.per_unit_with_waste.valid_default_denied",
    "04.skill_selector_mismatch", "05.cross_turn_evidence",
    "06.cross_skill_evidence", "07.reference_time_substitution",
    "08.gate_identity_substitution", "09.configured_denied_out_of_scope",
    "10.trusted_enabled_out_of_scope", "11.activation_binding_substitution",
    "12.execution_integrity_substitution", "13.payload_delivery_substitution",
    "14.authority_escalation", "15.historical_or_wrong_version",
)


@dataclass(frozen=True)
class ProductionAdmissionAcceptanceAuthorityBoundary:
    admission: bool = False
    activation: bool = False
    execution: bool = False
    bridge: bool = False
    runtime: bool = False
    delivery: bool = False
    response: bool = False
    commit: bool = False
    persistence: bool = False
    session: bool = False
    network: bool = False
    tool_execution: bool = False
    llm: bool = False
    feature_gate_mutation: bool = False


@dataclass(frozen=True)
class ProductionAdmissionAcceptanceScenario:
    version: str
    scope: str
    scenario_id: str
    classification: str
    outcome_class: str
    skill_id: str
    expected_decision_status: str
    expected_denial_code: str
    boundary_request: ProductionAdmissionBoundaryRequest
    scenario_digest: str = ""


@dataclass(frozen=True)
class ProductionAdmissionAcceptanceObservation:
    version: str
    scope: str
    scenario_id: str
    classification: str
    skill_id: str
    expected_decision_status: str
    expected_denial_code: str
    boundary_request: ProductionAdmissionBoundaryRequest
    request_id: str
    request_digest: str
    evidence_id: str
    evidence_digest: str
    observed_decision: ProductionAdmissionBoundaryDecision
    decision_digest: str
    observed_decision_status: str
    observed_denial_code: str
    observed_denial_reason: str
    admitted: bool
    admission_input_ready: bool
    executable_output: None
    request_verified: bool
    evidence_verified: bool
    lineage_verified: bool
    feature_gate_name: str
    configured_state: bool
    effective_state: bool
    default_denied: bool
    authority_isolated: bool
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    observation_passed: bool
    authority_boundary: ProductionAdmissionAcceptanceAuthorityBoundary
    observation_digest: str = ""


@dataclass(frozen=True)
class ProductionAdmissionAcceptanceReport:
    version: str
    scope: str
    canonical_scenario_ids: tuple[str, ...]
    observations: tuple[ProductionAdmissionAcceptanceObservation, ...]
    ordered_observation_digests: tuple[str, ...]
    scenario_count: int
    valid_default_denied_count: int
    invalid_fail_closed_count: int
    observed_admitted_count: int
    observed_denied_count: int
    skill_coverage: tuple[str, ...]
    request_integrity: bool
    evidence_integrity: bool
    decision_integrity: bool
    default_deny_verified: bool
    authority_isolated: bool
    all_passed: bool
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    authority_boundary: ProductionAdmissionAcceptanceAuthorityBoundary
    report_digest: str = ""


def _canonical(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return (type(value).__name__, tuple((f.name, _canonical(getattr(value, f.name)))
                                            for f in fields(value)))
    if type(value) is tuple:
        return tuple(_canonical(item) for item in value)
    if type(value) is list:
        return ("LIST", tuple(_canonical(item) for item in value))
    if type(value) is dict:
        return ("MAPPING", tuple((_canonical(key), _canonical(item))
                                  for key, item in value.items()))
    if type(value) is Decimal:
        return ("DECIMAL", str(value))
    if type(value) is datetime:
        return ("DATETIME", value.isoformat())
    if value is None or type(value) in (str, int, bool, float):
        return value
    raise TypeError("non-canonical acceptance material")


def _sha(label: str, value: Any) -> str:
    return hashlib.sha256(json.dumps((label, _canonical(value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _digest(value: Any) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _scenario_material(value: ProductionAdmissionAcceptanceScenario):
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != "scenario_digest")


def _observation_material(value: ProductionAdmissionAcceptanceObservation):
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != "observation_digest")


def _report_material(value: ProductionAdmissionAcceptanceReport):
    return tuple(getattr(value, f.name) for f in fields(value)
                 if f.name not in ("observations", "report_digest"))


def _scenario(sid, outcome, request, status, code):
    draft = ProductionAdmissionAcceptanceScenario(
        ISOLATED_DEFAULT_DENIED_PRODUCTION_ADMISSION_ACCEPTANCE_VERSION,
        ISOLATED_DEFAULT_DENIED_PRODUCTION_ADMISSION_ACCEPTANCE_SCOPE,
        sid, BOUNDARY_ACCEPTANCE, outcome, request.selected_skill_id, status, code, request)
    return replace(draft, scenario_digest=_sha("PRODUCTION_ADMISSION_ACCEPTANCE_SCENARIO",
                                               _scenario_material(draft)))


def create_production_admission_acceptance_scenarios(
    change_request: Any, per_unit_request: Any, per_unit_waste_request: Any,
    other_change_request: Any,
) -> tuple[ProductionAdmissionAcceptanceScenario, ...] | None:
    """Create the matrix from four prebuilt canonical request artifacts."""
    try:
        requests = (change_request, per_unit_request, per_unit_waste_request,
                    other_change_request)
        if not all(verify_production_admission_boundary_request(x) for x in requests):
            return None
        c, u, w, c2 = requests
        e = c.evidence
        invalid = (DENIED_INVALID_PRODUCTION_EVIDENCE,
                   INVALID_PRODUCTION_ADMISSION_EVIDENCE)
        malformed = (DENIED_MALFORMED_REQUEST, MALFORMED_PRODUCTION_ADMISSION_REQUEST)
        mismatch = (DENIED_SKILL_IDENTITY_MISMATCH, PRODUCTION_SKILL_IDENTITY_MISMATCH)
        def embedded(**changes):
            return replace(c, evidence=replace(e, **changes))
        other_authority = replace(e.authority_boundary, admission=True)
        matrix = (
            (CANONICAL_SCENARIO_IDS[0], VALID_DEFAULT_DENIED, c,
             DENIED_DEFAULT_PRODUCTION_GATE, PRODUCTION_FEATURE_GATE_DEFAULT_DENIED),
            (CANONICAL_SCENARIO_IDS[1], VALID_DEFAULT_DENIED, u,
             DENIED_DEFAULT_PRODUCTION_GATE, PRODUCTION_FEATURE_GATE_DEFAULT_DENIED),
            (CANONICAL_SCENARIO_IDS[2], VALID_DEFAULT_DENIED, w,
             DENIED_DEFAULT_PRODUCTION_GATE, PRODUCTION_FEATURE_GATE_DEFAULT_DENIED),
            (CANONICAL_SCENARIO_IDS[3], INVALID_FAIL_CLOSED,
             replace(c, selected_skill_id=u.selected_skill_id), *malformed),
            (CANONICAL_SCENARIO_IDS[4], INVALID_FAIL_CLOSED,
             replace(c, evidence=c2.evidence), DENIED_DEFAULT_PRODUCTION_GATE,
             PRODUCTION_FEATURE_GATE_DEFAULT_DENIED),
            (CANONICAL_SCENARIO_IDS[5], INVALID_FAIL_CLOSED,
             replace(c, evidence=u.evidence), *mismatch),
            (CANONICAL_SCENARIO_IDS[6], INVALID_FAIL_CLOSED,
             embedded(reference_time_digest="0" * 64), *invalid),
            (CANONICAL_SCENARIO_IDS[7], INVALID_FAIL_CLOSED,
             embedded(feature_gate_name="SUBSTITUTED_GATE"), *invalid),
            (CANONICAL_SCENARIO_IDS[8], INVALID_FAIL_CLOSED,
             embedded(default_denied=False), *invalid),
            (CANONICAL_SCENARIO_IDS[9], INVALID_FAIL_CLOSED,
             embedded(configured_state=True, effective_state=True, default_denied=False), *invalid),
            (CANONICAL_SCENARIO_IDS[10], INVALID_FAIL_CLOSED,
             embedded(activation_binding_digest="0" * 64), *invalid),
            (CANONICAL_SCENARIO_IDS[11], INVALID_FAIL_CLOSED,
             embedded(execution_integrity_digest="0" * 64), *invalid),
            (CANONICAL_SCENARIO_IDS[12], INVALID_FAIL_CLOSED,
             embedded(payload_digest="0" * 64), *invalid),
            (CANONICAL_SCENARIO_IDS[13], INVALID_FAIL_CLOSED,
             embedded(authority_boundary=other_authority), *invalid),
            (CANONICAL_SCENARIO_IDS[14], INVALID_FAIL_CLOSED,
             embedded(version="5.15.24.7.1"), *invalid),
        )
        return tuple(_scenario(*row) for row in matrix)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_admission_acceptance_scenario(value: Any) -> bool:
    try:
        return (type(value) is ProductionAdmissionAcceptanceScenario
                and value.version == ISOLATED_DEFAULT_DENIED_PRODUCTION_ADMISSION_ACCEPTANCE_VERSION
                and value.scope == ISOLATED_DEFAULT_DENIED_PRODUCTION_ADMISSION_ACCEPTANCE_SCOPE
                and value.classification == BOUNDARY_ACCEPTANCE
                and value.outcome_class in (VALID_DEFAULT_DENIED, INVALID_FAIL_CLOSED)
                and value.skill_id == value.boundary_request.selected_skill_id
                and _digest(value.scenario_digest)
                and value.scenario_digest == _sha("PRODUCTION_ADMISSION_ACCEPTANCE_SCENARIO",
                                                  _scenario_material(value)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def observe_production_admission_acceptance_scenario(value: Any):
    try:
        if not verify_production_admission_acceptance_scenario(value):
            return None
        request = value.boundary_request
        decision = evaluate_default_denied_production_admission(request)
        if decision is None:
            return None
        decision_ok = verify_production_admission_boundary_decision(request, decision)
        request_ok = verify_production_admission_boundary_request(request)
        evidence_ok = verify_production_single_skill_admission_evidence(request.evidence)
        authority = ProductionAdmissionAcceptanceAuthorityBoundary()
        authority_ok = all(getattr(decision.authority_boundary, n) is False
                           for n in decision.authority_boundary.__dataclass_fields__)
        passed = (decision_ok and decision.decision_status == value.expected_decision_status
                  and decision.denial_code == value.expected_denial_code
                  and decision.admitted is False and decision.admission_input_ready is False
                  and decision.executable_output is None and authority_ok)
        draft = ProductionAdmissionAcceptanceObservation(
            value.version, value.scope, value.scenario_id, value.classification, value.skill_id,
            value.expected_decision_status, value.expected_denial_code, request,
            request.request_id, request.request_digest, request.evidence_id,
            request.evidence_digest, decision, decision.decision_digest,
            decision.decision_status, decision.denial_code, decision.denial_reason,
            decision.admitted, decision.admission_input_ready, decision.executable_output,
            request_ok, evidence_ok, decision.lineage_verified, decision.feature_gate_name,
            decision.configured_state, decision.effective_state, decision.default_denied,
            authority_ok, decision.reasons, decision.diagnostics, passed, authority)
        return replace(draft, observation_digest=_sha(
            "PRODUCTION_ADMISSION_ACCEPTANCE_OBSERVATION", _observation_material(draft)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_admission_acceptance_observation(value: Any) -> bool:
    try:
        if type(value) is not ProductionAdmissionAcceptanceObservation or not _digest(value.observation_digest):
            return False
        scenario = ProductionAdmissionAcceptanceScenario(
            value.version, value.scope, value.scenario_id, value.classification,
            VALID_DEFAULT_DENIED if value.scenario_id in CANONICAL_SCENARIO_IDS[:3]
            else INVALID_FAIL_CLOSED, value.skill_id, value.expected_decision_status,
            value.expected_denial_code, value.boundary_request)
        scenario = replace(scenario, scenario_digest=_sha(
            "PRODUCTION_ADMISSION_ACCEPTANCE_SCENARIO", _scenario_material(scenario)))
        expected = observe_production_admission_acceptance_scenario(scenario)
        return expected is not None and value == expected and value.observation_digest == _sha(
            "PRODUCTION_ADMISSION_ACCEPTANCE_OBSERVATION", _observation_material(value))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def create_production_admission_acceptance_report(scenarios: Any):
    try:
        if (type(scenarios) is not tuple or tuple(x.scenario_id for x in scenarios) != CANONICAL_SCENARIO_IDS
                or len(set(x.scenario_id for x in scenarios)) != len(CANONICAL_SCENARIO_IDS)
                or not all(verify_production_admission_acceptance_scenario(x) for x in scenarios)):
            return None
        observations = tuple(observe_production_admission_acceptance_scenario(x) for x in scenarios)
        if any(x is None for x in observations):
            return None
        coverage = tuple(sorted(set(x.skill_id for x in observations)))
        authority = ProductionAdmissionAcceptanceAuthorityBoundary()
        draft = ProductionAdmissionAcceptanceReport(
            ISOLATED_DEFAULT_DENIED_PRODUCTION_ADMISSION_ACCEPTANCE_VERSION,
            ISOLATED_DEFAULT_DENIED_PRODUCTION_ADMISSION_ACCEPTANCE_SCOPE,
            CANONICAL_SCENARIO_IDS, observations,
            tuple(x.observation_digest for x in observations), len(observations), 3,
            len(observations) - 3, sum(x.admitted for x in observations),
            sum(not x.admitted for x in observations), coverage,
            all(x.request_verified for x in observations[:3]),
            all(x.evidence_verified for x in observations[:3]),
            all(verify_production_admission_boundary_decision(x.boundary_request,
                                                              x.observed_decision)
                for x in observations),
            all(x.observed_decision_status == DENIED_DEFAULT_PRODUCTION_GATE
                for x in observations[:3]),
            all(x.authority_isolated for x in observations),
            all(x.observation_passed for x in observations),
            ("CANONICAL_MATRIX_OBSERVED", "ALL_SCENARIOS_DENIED"),
            ("PURE_BOUNDARY_EVALUATION_ONLY", "NO_SYNTHETIC_DECISIONS",
             "POST_DECISION_TAMPERING_EXCLUDED"), authority)
        return replace(draft, report_digest=_sha("PRODUCTION_ADMISSION_ACCEPTANCE_REPORT",
                                                 _report_material(draft)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_admission_acceptance_report(value: Any) -> bool:
    try:
        if (type(value) is not ProductionAdmissionAcceptanceReport or not _digest(value.report_digest)
                or value.canonical_scenario_ids != CANONICAL_SCENARIO_IDS
                or tuple(x.scenario_id for x in value.observations) != CANONICAL_SCENARIO_IDS
                or not all(verify_production_admission_acceptance_observation(x)
                           for x in value.observations)):
            return False
        scenarios = tuple(ProductionAdmissionAcceptanceScenario(
            x.version, x.scope, x.scenario_id, x.classification,
            VALID_DEFAULT_DENIED if x.scenario_id in CANONICAL_SCENARIO_IDS[:3]
            else INVALID_FAIL_CLOSED, x.skill_id, x.expected_decision_status,
            x.expected_denial_code, x.boundary_request) for x in value.observations)
        scenarios = tuple(replace(x, scenario_digest=_sha(
            "PRODUCTION_ADMISSION_ACCEPTANCE_SCENARIO", _scenario_material(x))) for x in scenarios)
        expected = create_production_admission_acceptance_report(scenarios)
        return expected is not None and value == expected and value.report_digest == _sha(
            "PRODUCTION_ADMISSION_ACCEPTANCE_REPORT", _report_material(value))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = tuple(name for name in globals() if name.startswith("ISOLATED_") or
    name.startswith("CANONICAL_") or name.startswith("ProductionAdmissionAcceptance") or
    name.startswith("create_production_admission_acceptance") or
    name.startswith("observe_production_admission_acceptance") or
    name.startswith("verify_production_admission_acceptance"))
