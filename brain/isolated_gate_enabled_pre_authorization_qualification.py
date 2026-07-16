"""Deterministic qualification acceptance for the isolated enabled gate chain.

The report owns only the GATE_ENABLED_PREAUTH_QUALIFIED evidence decision.  It
does not alter its foundation, qualify an executable request, or grant any
production, transition, activation, persistence, dispatch, or runtime authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any

from brain.isolated_qualification_configuration_binding import (
    FOUNDATION_BOUND,
    ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_SCOPE,
    ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_VERSION,
    IsolatedQualificationPreExecutionResult,
    verify_isolated_qualification_pre_execution_result,
)
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
)
from brain.production_feature_gate_release_owner import (
    PROPOSED_NOT_AUTHORIZED,
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
    verify_production_feature_gate_release_owner,
    verify_production_feature_gate_transition_proposal,
)


ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_VERSION = "5.15.24.7.4.10"
ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_SCOPE = (
    "ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_ACCEPTANCE"
)
GATE_ENABLED_PREAUTH_QUALIFIED = "GATE_ENABLED_PREAUTH_QUALIFIED"
QUALIFICATION_DIAGNOSTIC = (
    "ISOLATED_GATE_ENABLED_PREAUTH_QUALIFIED_WITHOUT_APPLICATION_ACTIVATION_OR_EXECUTION"
)
EXECUTABLE_REQUEST_REQUIREMENT_IDENTITY = "EXECUTABLE_REQUEST_QUALIFIED"
CANONICAL_SCENARIO_IDS = (
    "01.exact_foundation_version_scope",
    "02.supported_gate_identity",
    "03.isolated_enabled_configuration_integrity",
    "04.enabled_evaluation_integrity",
    "05.production_turn_continuity",
    "06.reference_time_continuity",
    "07.qualification_feature_gate_binding",
    "08.qualification_skill_evidence_envelope",
    "09.qualification_limited_activation_binding",
    "10.qualification_pre_execution_result",
    "11.production_configuration_separation",
    "12.release_owner_non_mutation",
    "13.executable_request_separation",
    "14.transition_proposal_non_application",
    "15.authority_and_persistence_isolation",
    "16.downstream_runtime_non_invocation",
)
EXPECTED_TOPOLOGY = (
    "PRODUCTION_TURN_CONTEXT",
    "PRODUCTION_TURN_REFERENCE_TIME",
    "ISOLATED_VERIFIED_ENABLED_CONFIGURATION",
    "ISOLATED_QUALIFICATION_FEATURE_GATE_BINDING",
    "ISOLATED_QUALIFICATION_SKILL_EVIDENCE_ENVELOPE",
    "ISOLATED_QUALIFICATION_LIMITED_ACTIVATION_BINDING",
    "ISOLATED_QUALIFICATION_PRE_EXECUTION_RESULT",
    "GATE_ENABLED_PREAUTH_QUALIFICATION_ACCEPTANCE",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class IsolatedGateEnabledPreAuthorizationAuthorityBoundary:
    approval: bool = False
    transition_application: bool = False
    activation: bool = False
    mutation: bool = False
    persistence: bool = False
    production_execution: bool = False
    executable_request_qualification: bool = False
    dispatch: bool = False
    runtime: bool = False
    bridge: bool = False
    admission: bool = False
    calculator: bool = False
    delivery: bool = False
    response_replacement: bool = False
    deployment: bool = False
    rollback_execution: bool = False


@dataclass(frozen=True)
class IsolatedGateEnabledPreAuthorizationScenario:
    scenario_id: str
    classification: str
    deterministic_outcome: str


@dataclass(frozen=True)
class IsolatedGateEnabledPreAuthorizationObservation:
    version: str
    scope: str
    scenario: IsolatedGateEnabledPreAuthorizationScenario
    foundation_result: IsolatedQualificationPreExecutionResult
    turn_digest: str
    reference_time_digest: str
    configuration_digest: str
    evaluation_digest: str
    configuration_binding_digest: str
    qualification_evidence_digest: str
    limited_activation_digest: str
    pre_execution_result_digest: str
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    production_configuration_digest: str
    deterministic_observed_outcome: str
    observation_passed: bool
    authority_boundary: IsolatedGateEnabledPreAuthorizationAuthorityBoundary
    observation_digest: str = ""


@dataclass(frozen=True)
class IsolatedGateEnabledPreAuthorizationReport:
    version: str
    scope: str
    requirement_id: str
    foundation_result: IsolatedQualificationPreExecutionResult
    topology: tuple[str, ...]
    topology_digest: str
    canonical_scenario_ids: tuple[str, ...]
    observations: tuple[IsolatedGateEnabledPreAuthorizationObservation, ...]
    ordered_observation_digests: tuple[str, ...]
    configuration_digest: str
    evaluation_digest: str
    qualification_configuration_binding_digest: str
    qualification_evidence_digest: str
    limited_activation_digest: str
    pre_execution_foundation_result_digest: str
    turn_digest: str
    reference_time_digest: str
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    production_configuration_digest: str
    total_count: int
    passed_count: int
    authority_violation_count: int
    controlled_runtime_invocation_count: int
    transition_approved: bool
    transition_applied: bool
    application_permitted: bool
    activation_permitted: bool
    executable_request_qualified: bool
    qualified: bool
    status: str
    diagnostics: tuple[str, ...]
    authority_boundary: IsolatedGateEnabledPreAuthorizationAuthorityBoundary
    source_sha_attested: bool = False
    deployed_sha_attested: bool = False
    report_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        return {"$float": format(value, ".17g")}
    if type(value) is Decimal:
        return {"$decimal": str(value)}
    if type(value) is datetime:
        return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("non-string mapping key")
        return [[key, _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported qualification acceptance material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(
        _canonical((ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_VERSION, label, value)),
        ensure_ascii=False, allow_nan=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, digest_field: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value) if field.name != digest_field)


def _authority_false(value: Any) -> bool:
    return type(value) is IsolatedGateEnabledPreAuthorizationAuthorityBoundary and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False
        for field in fields(value)
    )


def _scenarios() -> tuple[IsolatedGateEnabledPreAuthorizationScenario, ...]:
    return tuple(
        IsolatedGateEnabledPreAuthorizationScenario(scenario_id, scenario_id.split(".", 1)[1].upper(), "VERIFIED")
        for scenario_id in CANONICAL_SCENARIO_IDS
    )


def _chain_is_qualified(result: IsolatedQualificationPreExecutionResult) -> bool:
    binding = result.configuration_binding
    evidence = result.evidence_envelope
    limited = result.limited_activation_binding
    owner = binding.release_owner
    proposal = create_production_feature_gate_transition_proposal(LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True)
    return all((
        verify_isolated_qualification_pre_execution_result(result),
        result.version == ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_VERSION,
        result.scope.endswith("PRE_EXECUTION_FOUNDATION"),
        binding.scope == ISOLATED_QUALIFICATION_CONFIGURATION_BINDING_SCOPE,
        binding.gate_name == LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
        binding.configuration.gate_entries == ((LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True),),
        binding.configured_state is True, binding.effective_state is True, binding.default_denied is False,
        binding.evaluation.configured_state is True, binding.evaluation.effective_state is True,
        binding.evaluation.default_denied is False,
        evidence.configuration_binding is binding, evidence.turn_context is binding.turn_context,
        evidence.reference_time is binding.reference_time, evidence.gate_evaluation is binding.evaluation,
        limited.configuration_binding is binding, limited.evidence_envelope is evidence,
        result.status == FOUNDATION_BOUND, result.requirement_qualified is False,
        result.executable_request_qualified is False, result.execute_allowed is False,
        result.executable_request is None, result.dispatch_permitted is False,
        result.production_application_permitted is False, result.runtime_invocation_permitted is False,
        verify_production_feature_gate_release_owner(owner), owner is get_production_feature_gate_release_owner(),
        owner.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
        owner.configuration.gate_entries == (), owner.configured_state is False,
        owner.effective_state is False, owner.default_denied is True,
        owner.transition_applied is False, owner.activation_permitted is False,
        owner.mutation_permitted is False, owner.executable_output is None,
        verify_production_feature_gate_transition_proposal(proposal),
        proposal.status == PROPOSED_NOT_AUTHORIZED, proposal.transition_applied is False,
        proposal.approval_verified is False, proposal.activation_permitted is False,
        proposal.mutation_permitted is False, proposal.executable_output is None,
    ))


def _observe(scenario: IsolatedGateEnabledPreAuthorizationScenario,
             result: IsolatedQualificationPreExecutionResult
             ) -> IsolatedGateEnabledPreAuthorizationObservation:
    binding, evidence, limited = result.configuration_binding, result.evidence_envelope, result.limited_activation_binding
    owner = binding.release_owner
    passed = _chain_is_qualified(result)
    observed = scenario.deterministic_outcome if passed else "REJECTED"
    draft = IsolatedGateEnabledPreAuthorizationObservation(
        ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_VERSION,
        ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_SCOPE, scenario, result,
        binding.turn_context.turn_digest, binding.reference_time.reference_time_digest,
        binding.configuration.source_digest, binding.evaluation.evaluation_digest, binding.binding_digest,
        evidence.envelope_digest, limited.binding_digest, result.result_digest, owner.owner_digest,
        owner.release_revision.revision_id, owner.release_revision.revision_digest,
        owner.configuration_digest, observed, passed,
        IsolatedGateEnabledPreAuthorizationAuthorityBoundary(),
    )
    return replace(draft, observation_digest=_digest("OBSERVATION", _material(draft, "observation_digest")))


def create_isolated_gate_enabled_pre_authorization_report(
    foundation_result: Any,
) -> IsolatedGateEnabledPreAuthorizationReport | None:
    """Derive qualification solely from the exact strictly verified foundation result."""
    try:
        if not verify_isolated_qualification_pre_execution_result(foundation_result):
            return None
        binding = foundation_result.configuration_binding
        evidence = foundation_result.evidence_envelope
        limited = foundation_result.limited_activation_binding
        owner = binding.release_owner
        observations = tuple(_observe(scenario, foundation_result) for scenario in _scenarios())
        qualified = len(observations) == len(CANONICAL_SCENARIO_IDS) and all(
            item.observation_passed for item in observations
        )
        boundary = IsolatedGateEnabledPreAuthorizationAuthorityBoundary()
        draft = IsolatedGateEnabledPreAuthorizationReport(
            ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_VERSION,
            ISOLATED_GATE_ENABLED_PRE_AUTHORIZATION_QUALIFICATION_SCOPE,
            GATE_ENABLED_PREAUTH_QUALIFIED, foundation_result, EXPECTED_TOPOLOGY,
            _digest("ORDERED_TOPOLOGY", EXPECTED_TOPOLOGY), CANONICAL_SCENARIO_IDS, observations,
            tuple(item.observation_digest for item in observations), binding.configuration.source_digest,
            binding.evaluation.evaluation_digest, binding.binding_digest, evidence.envelope_digest,
            limited.binding_digest, foundation_result.result_digest, binding.turn_context.turn_digest,
            binding.reference_time.reference_time_digest, owner.owner_digest,
            owner.release_revision.revision_id, owner.release_revision.revision_digest,
            owner.configuration_digest, len(observations), sum(item.observation_passed for item in observations),
            sum(not _authority_false(item.authority_boundary) for item in observations), 0,
            False, False, False, False, False, qualified,
            GATE_ENABLED_PREAUTH_QUALIFIED if qualified else "QUALIFICATION_REJECTED",
            (QUALIFICATION_DIAGNOSTIC,) if qualified else ("CANONICAL_FOUNDATION_CHAIN_REJECTED",), boundary,
        )
        return replace(draft, report_digest=_digest("REPORT", _material(draft, "report_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_isolated_gate_enabled_pre_authorization_observation(
    value: Any, foundation_result: Any,
) -> bool:
    try:
        if type(value) is not IsolatedGateEnabledPreAuthorizationObservation:
            return False
        scenarios = {scenario.scenario_id: scenario for scenario in _scenarios()}
        scenario = scenarios.get(value.scenario.scenario_id)
        return bool(
            scenario is not None and value.scenario == scenario and _HEX.fullmatch(value.observation_digest)
            and value == _observe(scenario, foundation_result)
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def verify_isolated_gate_enabled_pre_authorization_report(value: Any) -> bool:
    """Reject stored claims and reconstruct the entire report from its canonical foundation."""
    try:
        if type(value) is not IsolatedGateEnabledPreAuthorizationReport:
            return False
        if not _HEX.fullmatch(value.topology_digest) or not _HEX.fullmatch(value.report_digest):
            return False
        if tuple(item.scenario.scenario_id for item in value.observations) != CANONICAL_SCENARIO_IDS:
            return False
        if not _authority_false(value.authority_boundary):
            return False
        if not all(verify_isolated_gate_enabled_pre_authorization_observation(item, value.foundation_result)
                   for item in value.observations):
            return False
        expected = create_isolated_gate_enabled_pre_authorization_report(value.foundation_result)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = tuple(name for name in globals() if name.startswith("ISOLATED_") or name.startswith("GATE_")
                or name.startswith("QUALIFICATION_") or name.startswith("EXECUTABLE_")
                or name.startswith("CANONICAL_") or name.startswith("EXPECTED_")
                or name.startswith("IsolatedGateEnabled") or name.startswith("create_isolated_")
                or name.startswith("verify_isolated_"))
