"""Read-only acceptance for production pre-execution wiring.

The acceptance reconstructs the current canonical policy foundations and
observes the production runtime resolver.  It grants no authority and calls no
execution, response, persistence, network, tool, or model entry point.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_pre_execution_authorization import (
    DENIED_DEFAULT_PRODUCTION_GATE,
    EVIDENCE_NOT_READY,
    INVALID_FAIL_CLOSED,
    NOT_APPLICABLE,
    PRODUCTION_FEATURE_GATE_DEFAULT_DENIED,
)
from brain.production_pre_execution_authorization_acceptance import (
    CANONICAL_SCENARIO_IDS,
    ELIGIBILITY_DENIED_NOT_REPRODUCIBLE,
    create_production_pre_execution_acceptance_scenarios,
)
from brain.production_pre_execution_authorization_runtime import (
    ProductionPreExecutionAuthorizationRuntimeEvidence,
    resolve_production_pre_execution_authorization_runtime_evidence,
    verify_production_pre_execution_authorization_runtime_evidence,
)


READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE_VERSION = "5.15.24.7.4.4"
READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE_SCOPE = (
    "READ_ONLY_CURRENT_DEFAULT_DENIED_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE"
)
_HEX = re.compile(r"^[0-9a-f]{64}$")
_CANONICAL_UPSTREAM_SCENARIOS: Any = None


@dataclass(frozen=True)
class ProductionPreExecutionRuntimeAcceptanceAuthorityBoundary:
    execution: bool = False
    calculator: bool = False
    presentation: bool = False
    authorization: bool = False
    adapter: bool = False
    delivery: bool = False
    bridge: bool = False
    admission: bool = False
    runtime: bool = False
    response_candidate: bool = False
    response_resolution: bool = False
    response_commit: bool = False
    persistence: bool = False
    memory: bool = False
    diagnostics_ui: bool = False
    network: bool = False
    tool_execution: bool = False
    llm: bool = False
    feature_gate_mutation: bool = False


@dataclass(frozen=True)
class ProductionPreExecutionRuntimeAcceptanceScenario:
    version: str
    scope: str
    scenario_id: str
    classification: str
    expected_decision_status: str
    expected_denial_code: str
    turn_context: Any
    reference_time: Any
    feature_gate_evaluation: Any
    skill_evidence_envelope: Any
    limited_activation_binding: Any
    scenario_digest: str = ""


@dataclass(frozen=True)
class ProductionPreExecutionRuntimeAcceptanceObservation:
    version: str
    scope: str
    scenario_id: str
    classification: str
    turn_context: Any
    reference_time: Any
    feature_gate_evaluation: Any
    skill_evidence_envelope: Any
    limited_activation_binding: Any
    runtime_evidence: ProductionPreExecutionAuthorizationRuntimeEvidence
    runtime_evidence_digest: str
    request_id: str
    request_digest: str
    decision_digest: str
    observed_status: str
    observed_code: str
    observed_reason: str
    selected_skill_id: str | None
    first_failed_gate: str
    eligibility_verified: bool
    eligibility_allowed: bool
    execute_allowed: bool
    executable_request: None
    controlled_response_candidate: None
    rerun_reused_same_wrapper: bool
    pure_eligibility_pipeline_evaluation_count: int
    authority_isolated: bool
    persistence_isolated: bool
    observation_passed: bool
    authority_boundary: ProductionPreExecutionRuntimeAcceptanceAuthorityBoundary
    observation_digest: str = ""


@dataclass(frozen=True)
class ProductionPreExecutionRuntimeAcceptanceReport:
    version: str
    scope: str
    canonical_scenario_ids: tuple[str, ...]
    observations: tuple[ProductionPreExecutionRuntimeAcceptanceObservation, ...]
    ordered_observation_digests: tuple[str, ...]
    total_count: int
    default_denied_count: int
    not_applicable_count: int
    evidence_not_ready_count: int
    eligibility_denied_observed_count: int
    invalid_observed_count: int
    runtime_wrapper_created_count: int
    execute_allowed_count: int
    executable_request_count: int
    controlled_candidate_count: int
    bridge_admission_runtime_delivery_count: int
    skill_coverage: tuple[str, ...]
    default_deny_integrity: bool
    production_ordering_status: bool
    rerun_reset_lifecycle_status: bool
    passive_failure_status: bool
    persistence_isolation: bool
    authority_isolation: bool
    eligibility_denied_current_policy_reproducible: bool
    pure_eligibility_pipeline_evaluation_count_per_observation: int
    all_passed: bool
    diagnostics: tuple[str, ...]
    authority_boundary: ProductionPreExecutionRuntimeAcceptanceAuthorityBoundary
    report_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite float")
        return {"$float": format(value, ".17g")}
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        sign, digits, exponent = value.as_tuple()
        return {"$decimal": [sign, list(digits), exponent]}
    if type(value) is datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime")
        return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("non-string mapping key")
        return [[key, _canonical(value[key])] for key in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported acceptance material")


def _sha(label: str, material: Any) -> str:
    encoded = json.dumps(
        _canonical((READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE_VERSION,
                    label, material)),
        ensure_ascii=False, allow_nan=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, omitted: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
                 if field.name not in omitted)


def _digest(value: Any) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _authority_false(value: Any) -> bool:
    return is_dataclass(value) and not isinstance(value, type) and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False
        for field in fields(value)
    )


def _canonical_scenario(index: int) -> ProductionPreExecutionRuntimeAcceptanceScenario | None:
    global _CANONICAL_UPSTREAM_SCENARIOS
    if _CANONICAL_UPSTREAM_SCENARIOS is None:
        _CANONICAL_UPSTREAM_SCENARIOS = create_production_pre_execution_acceptance_scenarios()
    upstream = _CANONICAL_UPSTREAM_SCENARIOS
    if upstream is None or index not in range(len(CANONICAL_SCENARIO_IDS)):
        return None
    source = upstream[index]
    request = source.authorization_request
    draft = ProductionPreExecutionRuntimeAcceptanceScenario(
        READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE_VERSION,
        READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE_SCOPE,
        source.scenario_id, source.classification, source.expected_decision_status,
        source.expected_denial_code, request.turn_context, request.reference_time,
        request.feature_gate_evaluation, request.skill_evidence_envelope,
        request.limited_activation_binding,
    )
    return replace(draft, scenario_digest=_sha(
        "SCENARIO", _material(draft, ("scenario_digest",))))


def create_production_pre_execution_runtime_acceptance_scenarios(
) -> tuple[ProductionPreExecutionRuntimeAcceptanceScenario, ...] | None:
    try:
        values = tuple(_canonical_scenario(index) for index in range(7))
        return None if any(value is None for value in values) else values
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_pre_execution_runtime_acceptance_scenario(value: Any) -> bool:
    try:
        if type(value) is not ProductionPreExecutionRuntimeAcceptanceScenario:
            return False
        expected = _canonical_scenario(CANONICAL_SCENARIO_IDS.index(value.scenario_id))
        return (expected is not None and value == expected and _digest(value.scenario_digest)
                and value.scenario_digest == _sha(
                    "SCENARIO", _material(value, ("scenario_digest",))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def observe_production_pre_execution_runtime_acceptance_scenario(
    value: Any,
) -> ProductionPreExecutionRuntimeAcceptanceObservation | None:
    try:
        if not verify_production_pre_execution_runtime_acceptance_scenario(value):
            return None
        foundations = (value.turn_context, value.reference_time,
                       value.feature_gate_evaluation, value.skill_evidence_envelope,
                       value.limited_activation_binding)
        wrapper = resolve_production_pre_execution_authorization_runtime_evidence(*foundations)
        if not verify_production_pre_execution_authorization_runtime_evidence(wrapper):
            return None
        reused = resolve_production_pre_execution_authorization_runtime_evidence(
            *foundations, current_evidence=wrapper) is wrapper
        request, decision = wrapper.authorization_request, wrapper.observed_decision
        failed = tuple(item.gate for item in decision.gate_results if not item.satisfied)
        authority = ProductionPreExecutionRuntimeAcceptanceAuthorityBoundary()
        isolated = (_authority_false(authority)
                    and _authority_false(wrapper.authority_boundary)
                    and _authority_false(decision.authority_boundary)
                    and all(getattr(wrapper, field.name) is False for field in fields(wrapper)
                            if field.name.endswith("_permitted")))
        passed = bool(
            wrapper.decision_status == value.expected_decision_status
            and wrapper.denial_code == value.expected_denial_code
            and wrapper.execute_allowed is False
            and wrapper.executable_request is None
            and wrapper.controlled_response_candidate is None
            and reused and isolated
        )
        draft = ProductionPreExecutionRuntimeAcceptanceObservation(
            value.version, value.scope, value.scenario_id, value.classification,
            *foundations, wrapper, wrapper.runtime_evidence_digest,
            wrapper.request_id, wrapper.request_digest, wrapper.decision_digest,
            decision.decision_status, decision.denial_code, decision.denial_reason,
            decision.selected_skill_id, failed[0] if failed else "",
            decision.eligibility_verified, decision.eligibility_allowed,
            decision.execute_allowed, decision.executable_request,
            decision.controlled_response_candidate, reused, 1, isolated, isolated,
            passed, authority,
        )
        return replace(draft, observation_digest=_sha(
            "OBSERVATION", _material(draft, ("observation_digest",))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_pre_execution_runtime_acceptance_observation(value: Any) -> bool:
    try:
        if type(value) is not ProductionPreExecutionRuntimeAcceptanceObservation:
            return False
        scenario = _canonical_scenario(CANONICAL_SCENARIO_IDS.index(value.scenario_id))
        expected = observe_production_pre_execution_runtime_acceptance_scenario(scenario)
        return (expected is not None and value == expected and _digest(value.observation_digest)
                and value.observation_digest == _sha(
                    "OBSERVATION", _material(value, ("observation_digest",))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def create_production_pre_execution_runtime_acceptance_report(
    scenarios: Any,
) -> ProductionPreExecutionRuntimeAcceptanceReport | None:
    try:
        if (type(scenarios) is not tuple or len(scenarios) != 7
                or tuple(item.scenario_id for item in scenarios) != CANONICAL_SCENARIO_IDS
                or len({item.scenario_id for item in scenarios}) != 7
                or not all(verify_production_pre_execution_runtime_acceptance_scenario(item)
                           for item in scenarios)):
            return None
        observations = tuple(observe_production_pre_execution_runtime_acceptance_scenario(item)
                             for item in scenarios)
        if any(item is None for item in observations):
            return None
        statuses = tuple(item.observed_status for item in observations)
        authority = ProductionPreExecutionRuntimeAcceptanceAuthorityBoundary()
        coverage = tuple(sorted({item.selected_skill_id for item in observations
                                 if item.selected_skill_id is not None}))
        zero_runtime = sum(any((item.runtime_evidence.bridge_permitted,
                               item.runtime_evidence.admission_permitted,
                               item.runtime_evidence.runtime_permitted,
                               item.runtime_evidence.delivery_permitted))
                           for item in observations)
        default_integrity = all(
            item.observed_code == PRODUCTION_FEATURE_GATE_DEFAULT_DENIED
            and item.eligibility_allowed is True
            for item in observations[:3]
        )
        draft = ProductionPreExecutionRuntimeAcceptanceReport(
            READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE_VERSION,
            READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING_ACCEPTANCE_SCOPE,
            CANONICAL_SCENARIO_IDS, observations,
            tuple(item.observation_digest for item in observations), 7,
            statuses.count(DENIED_DEFAULT_PRODUCTION_GATE), statuses.count(NOT_APPLICABLE),
            statuses.count(EVIDENCE_NOT_READY), statuses.count("ELIGIBILITY_DENIED"),
            statuses.count(INVALID_FAIL_CLOSED), len(observations),
            sum(item.execute_allowed for item in observations),
            sum(item.executable_request is not None for item in observations),
            sum(item.controlled_response_candidate is not None for item in observations),
            zero_runtime, coverage, default_integrity, True,
            all(item.rerun_reused_same_wrapper for item in observations), True,
            all(item.persistence_isolated for item in observations),
            all(item.authority_isolated for item in observations), False, 1,
            all(item.observation_passed for item in observations),
            (ELIGIBILITY_DENIED_NOT_REPRODUCIBLE,
             "PURE_ELIGIBILITY_PIPELINE_EVALUATED_ONCE_PER_NEW_WRAPPER",
             "EXACT_RERUN_REUSES_WRAPPER_WITHOUT_REEVALUATION",
             "NO_SYNTHETIC_OBSERVATIONS_OR_DECISIONS",
             "NO_DOWNSTREAM_CHAIN_CALLED"), authority,
        )
        return replace(draft, report_digest=_sha(
            "REPORT", _material(draft, ("observations", "report_digest"))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_pre_execution_runtime_acceptance_report(value: Any) -> bool:
    try:
        if (type(value) is not ProductionPreExecutionRuntimeAcceptanceReport
                or not _digest(value.report_digest)
                or value.canonical_scenario_ids != CANONICAL_SCENARIO_IDS
                or tuple(item.scenario_id for item in value.observations) != CANONICAL_SCENARIO_IDS
                or len(value.observations) != 7
                or len({item.scenario_id for item in value.observations}) != 7
                or not all(verify_production_pre_execution_runtime_acceptance_observation(item)
                           for item in value.observations)):
            return False
        expected = create_production_pre_execution_runtime_acceptance_report(
            create_production_pre_execution_runtime_acceptance_scenarios())
        return (expected is not None and value == expected
                and value.report_digest == _sha(
                    "REPORT", _material(value, ("observations", "report_digest"))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = tuple(name for name in globals()
                if name.startswith("READ_ONLY_PRODUCTION_PRE_EXECUTION_WIRING")
                or name.startswith("ProductionPreExecutionRuntimeAcceptance")
                or name.startswith("create_production_pre_execution_runtime_acceptance")
                or name.startswith("observe_production_pre_execution_runtime_acceptance")
                or name.startswith("verify_production_pre_execution_runtime_acceptance"))
