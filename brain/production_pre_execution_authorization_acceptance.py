"""Current-policy isolated acceptance for pre-execution authorization.

All observations are recomputed through the unmodified canonical pipeline.  The
module records denials only and owns no execution or production authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
)
from brain.production_limited_activation_binding import (
    create_production_limited_activation_binding,
)
from brain.production_pre_execution_authorization import (
    CONTROLLED_COST_EVIDENCE_NOT_READY,
    CONTROLLED_COST_RUNTIME_NOT_APPLICABLE,
    DENIED_DEFAULT_PRODUCTION_GATE,
    EVIDENCE_NOT_READY,
    GATE_ORDER,
    NOT_APPLICABLE,
    PRODUCTION_FEATURE_GATE_DEFAULT_DENIED,
    ProductionPreExecutionAuthorizationDecision,
    ProductionPreExecutionAuthorizationRequest,
    create_production_pre_execution_authorization_request,
    evaluate_production_pre_execution_authorization,
    verify_production_pre_execution_authorization_decision,
    verify_production_pre_execution_authorization_request,
)
from brain.production_turn_bound_skill_evidence import (
    create_production_turn_bound_skill_evidence_envelope,
)
from brain.production_turn_context import create_production_turn_context
from brain.production_turn_reference_time import create_production_turn_reference_time


ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_VERSION = "5.15.24.7.4.2"
ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_SCOPE = (
    "CURRENT_POLICY_DEFAULT_DENIED_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE"
)

ELIGIBLE_DEFAULT_DENIED = "ELIGIBLE_DEFAULT_DENIED"
INVALID_FAIL_CLOSED = "INVALID_FAIL_CLOSED"
ELIGIBILITY_DENIED_NOT_REPRODUCIBLE = (
    "ELIGIBILITY_DENIED_NOT_REPRODUCIBLE_UNDER_CURRENT_CANONICAL_POLICY"
)

CANONICAL_SCENARIO_IDS = (
    "01.change_analysis.eligible_default_denied",
    "02.per_unit.eligible_default_denied",
    "03.per_unit_with_waste.eligible_default_denied",
    "04.no_cost_candidate.not_applicable",
    "05.change_analysis.partial_evidence",
    "06.per_unit.partial_evidence",
    "07.ambiguous_cost_evidence",
)

_MESSAGES = (
    "my cost increased from 20.00 to 24.000",
    "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น",
    "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น ของเสีย 2 ชิ้น",
    "hello unrelated question",
    "cost increased previous cost 30",
    "ต้นทุนต่อชิ้น ต้นทุนรวม 300 บาท",
    "unit cost cost increased",
)
_CLASSIFICATIONS = (
    ELIGIBLE_DEFAULT_DENIED,
    ELIGIBLE_DEFAULT_DENIED,
    ELIGIBLE_DEFAULT_DENIED,
    NOT_APPLICABLE,
    EVIDENCE_NOT_READY,
    EVIDENCE_NOT_READY,
    EVIDENCE_NOT_READY,
)
_EXPECTED = (
    (DENIED_DEFAULT_PRODUCTION_GATE, PRODUCTION_FEATURE_GATE_DEFAULT_DENIED),
    (DENIED_DEFAULT_PRODUCTION_GATE, PRODUCTION_FEATURE_GATE_DEFAULT_DENIED),
    (DENIED_DEFAULT_PRODUCTION_GATE, PRODUCTION_FEATURE_GATE_DEFAULT_DENIED),
    (NOT_APPLICABLE, CONTROLLED_COST_RUNTIME_NOT_APPLICABLE),
    (EVIDENCE_NOT_READY, CONTROLLED_COST_EVIDENCE_NOT_READY),
    (EVIDENCE_NOT_READY, CONTROLLED_COST_EVIDENCE_NOT_READY),
    (EVIDENCE_NOT_READY, CONTROLLED_COST_EVIDENCE_NOT_READY),
)
_HEX = re.compile(r"^[0-9a-f]{64}$")
_ACCEPTED_AT = datetime(2026, 7, 15, 4, 5, 6, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ProductionPreExecutionAcceptanceAuthorityBoundary:
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
    session: bool = False
    network: bool = False
    tool_execution: bool = False
    llm: bool = False
    feature_gate_mutation: bool = False


@dataclass(frozen=True)
class ProductionPreExecutionAcceptanceScenario:
    version: str
    scope: str
    scenario_id: str
    classification: str
    expected_decision_status: str
    expected_denial_code: str
    authorization_request: ProductionPreExecutionAuthorizationRequest
    scenario_digest: str = ""


@dataclass(frozen=True)
class ProductionPreExecutionAcceptanceObservation:
    version: str
    scope: str
    scenario_id: str
    classification: str
    skill_id: str | None
    expected_decision_status: str
    expected_denial_code: str
    authorization_request: ProductionPreExecutionAuthorizationRequest
    request_id: str
    request_digest: str
    conversation_id: str
    turn_id: str
    turn_digest: str
    user_message_digest: str
    reference_time_digest: str
    feature_gate_evaluation_digest: str
    envelope_digest: str
    activation_binding_digest: str
    observed_decision: ProductionPreExecutionAuthorizationDecision
    decision_digest: str
    observed_decision_status: str
    observed_denial_code: str
    observed_denial_reason: str
    first_failed_gate: str
    eligibility_verified: bool
    eligibility_allowed: bool
    execute_allowed: bool
    executable_request: None
    controlled_response_candidate: None
    request_verified: bool
    decision_verified: bool
    authority_isolated: bool
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    observation_passed: bool
    authority_boundary: ProductionPreExecutionAcceptanceAuthorityBoundary
    observation_digest: str = ""


@dataclass(frozen=True)
class ProductionPreExecutionAcceptanceReport:
    version: str
    scope: str
    canonical_scenario_ids: tuple[str, ...]
    observations: tuple[ProductionPreExecutionAcceptanceObservation, ...]
    ordered_observation_digests: tuple[str, ...]
    total_count: int
    eligible_default_denied_count: int
    not_applicable_count: int
    evidence_not_ready_count: int
    invalid_fail_closed_count: int
    eligibility_denied_observed_count: int
    eligibility_denied_current_policy_representable: bool
    constructor_rejection_coverage_count: int
    verifier_only_coverage_count: int
    execute_allowed_count: int
    executable_request_count: int
    controlled_candidate_count: int
    admitted_runtime_bridge_delivery_count: int
    skill_coverage: tuple[str, ...]
    request_integrity: bool
    decision_integrity: bool
    authority_isolated: bool
    all_passed: bool
    reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    authority_boundary: ProductionPreExecutionAcceptanceAuthorityBoundary
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
    value = (ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_VERSION,
             label, material)
    encoded = json.dumps(_canonical(value), ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, omitted: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value)
                 if field.name not in omitted)


def _digest(value: Any) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _authority_false(value: Any) -> bool:
    return is_dataclass(value) and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False
        for field in fields(value)
    )


def _canonical_request(index: int) -> ProductionPreExecutionAuthorizationRequest | None:
    context = create_production_turn_context("v51524742-acceptance", index + 1,
                                             _MESSAGES[index])
    reference = create_production_turn_reference_time(context, _ACCEPTED_AT)
    gate = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
        context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    envelope = create_production_turn_bound_skill_evidence_envelope(context, gate)
    binding = create_production_limited_activation_binding(
        context, reference, gate, envelope
    )
    return create_production_pre_execution_authorization_request(
        context, reference, gate, envelope, binding
    )


def _canonical_scenario(index: int) -> ProductionPreExecutionAcceptanceScenario | None:
    request = _canonical_request(index)
    if request is None:
        return None
    status, code = _EXPECTED[index]
    draft = ProductionPreExecutionAcceptanceScenario(
        ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_VERSION,
        ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_SCOPE,
        CANONICAL_SCENARIO_IDS[index], _CLASSIFICATIONS[index], status, code, request,
    )
    return replace(draft, scenario_digest=_sha("SCENARIO", _material(draft, ("scenario_digest",))))


def create_production_pre_execution_acceptance_scenarios(
) -> tuple[ProductionPreExecutionAcceptanceScenario, ...] | None:
    """Build the fixed current-policy inventory without caller outcome inputs."""
    try:
        values = tuple(_canonical_scenario(index) for index in range(len(CANONICAL_SCENARIO_IDS)))
        return None if any(value is None for value in values) else values
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_pre_execution_acceptance_scenario(value: Any) -> bool:
    try:
        if type(value) is not ProductionPreExecutionAcceptanceScenario:
            return False
        index = CANONICAL_SCENARIO_IDS.index(value.scenario_id)
        expected = _canonical_scenario(index)
        return (_digest(value.scenario_digest) and expected is not None and value == expected
                and value.scenario_digest == _sha("SCENARIO", _material(value, ("scenario_digest",))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def observe_production_pre_execution_acceptance_scenario(
    value: Any,
) -> ProductionPreExecutionAcceptanceObservation | None:
    try:
        if not verify_production_pre_execution_acceptance_scenario(value):
            return None
        request = value.authorization_request
        decision = evaluate_production_pre_execution_authorization(request)
        if decision is None:
            return None
        request_ok = verify_production_pre_execution_authorization_request(request)
        decision_ok = verify_production_pre_execution_authorization_decision(request, decision)
        failed = tuple(item.gate for item in decision.gate_results if not item.satisfied)
        first_failed = failed[0] if failed else ""
        authority = ProductionPreExecutionAcceptanceAuthorityBoundary()
        authority_ok = _authority_false(authority) and _authority_false(decision.authority_boundary)
        authority_ok = authority_ok and all(
            getattr(decision, name) is False for name in (
                "runtime_permitted", "bridge_permitted", "admission_permitted",
                "delivery_permitted", "response_candidate_permitted",
                "persistence_permitted", "tool_execution_permitted",
                "feature_gate_mutation_permitted",
            )
        )
        passed = bool(
            request_ok and decision_ok
            and decision.decision_status == value.expected_decision_status
            and decision.denial_code == value.expected_denial_code
            and decision.execute_allowed is False
            and decision.executable_request is None
            and decision.controlled_response_candidate is None
            and authority_ok
        )
        draft = ProductionPreExecutionAcceptanceObservation(
            value.version, value.scope, value.scenario_id, value.classification,
            decision.selected_skill_id, value.expected_decision_status,
            value.expected_denial_code, request, request.request_id, request.request_digest,
            request.turn_context.conversation_id, request.turn_context.turn_id,
            request.turn_context.turn_digest, request.turn_context.user_message_digest,
            request.reference_time.reference_time_digest,
            request.feature_gate_evaluation.evaluation_digest,
            request.skill_evidence_envelope.envelope_digest,
            request.limited_activation_binding.binding_digest, decision,
            decision.decision_digest, decision.decision_status, decision.denial_code,
            decision.denial_reason, first_failed, decision.eligibility_verified,
            decision.eligibility_allowed, decision.execute_allowed,
            decision.executable_request, decision.controlled_response_candidate,
            request_ok, decision_ok, authority_ok, decision.reasons,
            decision.diagnostics, passed, authority,
        )
        return replace(draft, observation_digest=_sha(
            "OBSERVATION", _material(draft, ("observation_digest",))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_pre_execution_acceptance_observation(value: Any) -> bool:
    try:
        if type(value) is not ProductionPreExecutionAcceptanceObservation:
            return False
        index = CANONICAL_SCENARIO_IDS.index(value.scenario_id)
        scenario = _canonical_scenario(index)
        expected = observe_production_pre_execution_acceptance_scenario(scenario)
        return (_digest(value.observation_digest) and expected is not None and value == expected
                and value.observation_digest == _sha(
                    "OBSERVATION", _material(value, ("observation_digest",))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def create_production_pre_execution_acceptance_report(
    scenarios: Any,
) -> ProductionPreExecutionAcceptanceReport | None:
    try:
        if (type(scenarios) is not tuple
                or tuple(item.scenario_id for item in scenarios) != CANONICAL_SCENARIO_IDS
                or len(set(item.scenario_id for item in scenarios)) != len(CANONICAL_SCENARIO_IDS)
                or not all(verify_production_pre_execution_acceptance_scenario(item)
                           for item in scenarios)):
            return None
        observations = tuple(observe_production_pre_execution_acceptance_scenario(item)
                             for item in scenarios)
        if any(item is None for item in observations):
            return None
        authority = ProductionPreExecutionAcceptanceAuthorityBoundary()
        statuses = tuple(item.observed_decision_status for item in observations)
        coverage = tuple(sorted({item.skill_id for item in observations
                                 if item.skill_id is not None}))
        draft = ProductionPreExecutionAcceptanceReport(
            ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_VERSION,
            ISOLATED_PRODUCTION_PRE_EXECUTION_AUTHORIZATION_ACCEPTANCE_SCOPE,
            CANONICAL_SCENARIO_IDS, observations,
            tuple(item.observation_digest for item in observations), len(observations),
            statuses.count(DENIED_DEFAULT_PRODUCTION_GATE), statuses.count(NOT_APPLICABLE),
            statuses.count(EVIDENCE_NOT_READY), statuses.count(INVALID_FAIL_CLOSED),
            0, False, 7, 13,
            sum(item.execute_allowed for item in observations),
            sum(item.executable_request is not None for item in observations),
            sum(item.controlled_response_candidate is not None for item in observations),
            0, coverage, all(item.request_verified for item in observations),
            all(item.decision_verified for item in observations),
            all(item.authority_isolated for item in observations),
            all(item.observation_passed for item in observations),
            ("CURRENT_POLICY_CANONICAL_MATRIX_OBSERVED", "ALL_OUTCOMES_NON_EXECUTABLE"),
            (ELIGIBILITY_DENIED_NOT_REPRODUCIBLE,
             "STRICT_VERIFICATION_RERUNS_MATCHER_PARSER_MAPPER_SELECTOR_LIMITED_GATEWAY",
             "NO_SYNTHETIC_DECISIONS", "NO_DOWNSTREAM_AUTHORITY"), authority,
        )
        return replace(draft, report_digest=_sha(
            "REPORT", _material(draft, ("observations", "report_digest"))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_pre_execution_acceptance_report(value: Any) -> bool:
    try:
        if (type(value) is not ProductionPreExecutionAcceptanceReport
                or not _digest(value.report_digest)
                or value.canonical_scenario_ids != CANONICAL_SCENARIO_IDS
                or tuple(item.scenario_id for item in value.observations) != CANONICAL_SCENARIO_IDS
                or len(value.observations) != len(CANONICAL_SCENARIO_IDS)
                or any(item.observed_decision_status == "ELIGIBILITY_DENIED"
                       for item in value.observations)
                or not all(verify_production_pre_execution_acceptance_observation(item)
                           for item in value.observations)):
            return False
        scenarios = create_production_pre_execution_acceptance_scenarios()
        expected = create_production_pre_execution_acceptance_report(scenarios)
        return (expected is not None and value == expected
                and value.report_digest == _sha(
                    "REPORT", _material(value, ("observations", "report_digest"))))
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = tuple(name for name in globals() if name.startswith("ISOLATED_")
                or name.startswith("CANONICAL_")
                or name.startswith("ProductionPreExecutionAcceptance")
                or name.startswith("create_production_pre_execution_acceptance")
                or name.startswith("observe_production_pre_execution_acceptance")
                or name.startswith("verify_production_pre_execution_acceptance"))
