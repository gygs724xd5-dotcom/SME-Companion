"""V5.15.24.7.4.12 passive executable-request integrity qualification.

This module qualifies immutable request material.  It is deliberately not an
execution, dispatch, admission, delivery, bridge, or production-gate API.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from brain.cost_execution_result_integrity import SUPPORTED_SKILL_IDS
from brain.versioned_cost_executable_request import (
    STATUS as FOUNDATION_REQUEST_STATUS,
    VersionedCostExecutableRequest,
    create_versioned_cost_executable_request,
    verify_versioned_cost_executable_request,
)

VERSION = "5.15.24.7.4.12"
SCOPE = "ISOLATED_EXECUTABLE_REQUEST_QUALIFICATION"
REQUIREMENT_ID = "EXECUTABLE_REQUEST_QUALIFIED"
STATUS = "EXECUTABLE_REQUEST_QUALIFIED"
DIAGNOSTIC = "ISOLATED_EXECUTABLE_REQUESTS_QUALIFIED_WITHOUT_DISPATCH_EXECUTION_OR_RUNTIME_INVOCATION"
SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS = SUPPORTED_SKILL_IDS
CANONICAL_SCENARIO_IDS = (
    "01.exact_qualification_version_scope", "02.supported_skill_inventory_order",
    "03.request_integrity", "04.decimal_operands", "05.formula_policy_integrity",
    "06.optional_evidence_semantics", "07.turn_reference_time_continuity",
    "08.gate_configuration_evaluation_continuity", "09.evidence_limited_preauth_continuity",
    "10.request_identity_digest", "11.per_skill_isolation", "12.production_default_deny_separation",
    "13.foundation_non_self_authorization", "14.execution_dispatch_separation",
    "15.authority_persistence_isolation", "16.downstream_runtime_non_invocation",
)
TOPOLOGY = (
    "PRODUCTION_TURN_CONTEXT", "PRODUCTION_TURN_REFERENCE_TIME",
    "ISOLATED_GATE_ENABLED_FOUNDATION", "GATE_ENABLED_PREAUTH_QUALIFICATION_REPORT",
    "CANONICAL_COST_EVIDENCE", "VERSIONED_COST_EXECUTABLE_REQUEST",
    "STRICT_STANDALONE_REQUEST_VERIFICATION", "PER_SKILL_QUALIFICATION_OBSERVATION",
    "BATCH_QUALIFICATION_REPORT",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class IsolatedExecutableRequestQualificationAuthorityBoundary:
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


@dataclass(frozen=True)
class IsolatedExecutableRequestScenario:
    scenario_id: str
    deterministic_outcome: str


@dataclass(frozen=True)
class IsolatedExecutableRequestObservation:
    version: str
    scope: str
    skill_id: str
    foundation: Any
    preauth_report: Any
    request: VersionedCostExecutableRequest
    scenarios: tuple[IsolatedExecutableRequestScenario, ...]
    request_verified: bool
    qualified: bool
    authority_boundary: IsolatedExecutableRequestQualificationAuthorityBoundary
    observation_digest: str = ""


@dataclass(frozen=True)
class IsolatedExecutableRequestQualificationReport:
    version: str
    scope: str
    requirement_id: str
    supported_skill_ids: tuple[str, ...]
    observations: tuple[IsolatedExecutableRequestObservation, ...]
    request_digests: tuple[str, ...]
    topology: tuple[str, ...]
    topology_digest: str
    qualified_skill_count: int
    failed_skill_count: int
    qualified: bool
    status: str
    diagnostic: str
    execute_allowed: bool
    dispatch_permitted: bool
    application_permitted: bool
    activation_permitted: bool
    runtime_invocation_permitted: bool
    calculator_invocation_count: int
    bridge_invocation_count: int
    admission_invocation_count: int
    delivery_invocation_count: int
    controlled_runtime_invocation_count: int
    authority_boundary: IsolatedExecutableRequestQualificationAuthorityBoundary
    source_sha_attested: bool = False
    deployed_sha_attested: bool = False
    report_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float: return {"$float": format(value, ".17g")}
    if type(value) is Decimal: return {"$decimal": str(value)}
    if type(value) is datetime: return {"$datetime": value.isoformat()}
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[k, _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported qualification material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
                     allow_nan=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _material(value: Any, omitted: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name != omitted)


def _boundary_false(value: Any) -> bool:
    return type(value) is IsolatedExecutableRequestQualificationAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and not getattr(value, f.name) for f in fields(value))


def _scenarios() -> tuple[IsolatedExecutableRequestScenario, ...]:
    return tuple(IsolatedExecutableRequestScenario(x, "VERIFIED") for x in CANONICAL_SCENARIO_IDS)


def _observe(foundation: Any, preauth: Any) -> IsolatedExecutableRequestObservation | None:
    request = create_versioned_cost_executable_request(foundation, preauth)
    if request is None or not verify_versioned_cost_executable_request(request, foundation, preauth): return None
    if request.status != FOUNDATION_REQUEST_STATUS or request.skill_id not in SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS: return None
    if any((request.artifact_validity_claim, request.requirement_qualified, request.execute_allowed,
            request.dispatch_permitted, request.application_permitted, request.activation_permitted,
            request.runtime_invocation_permitted)) or request.execution_result is not None: return None
    draft = IsolatedExecutableRequestObservation(
        VERSION, SCOPE, request.skill_id, foundation, preauth, request, _scenarios(), True, True,
        IsolatedExecutableRequestQualificationAuthorityBoundary())
    return replace(draft, observation_digest=_digest("OBSERVATION", _material(draft, "observation_digest")))


def create_isolated_executable_request_qualification_report(
    request_foundations: Any,
) -> IsolatedExecutableRequestQualificationReport | None:
    """Qualify an exact ordered tuple of ``(foundation, preauth_report)`` pairs."""
    try:
        if type(request_foundations) is not tuple or len(request_foundations) != len(SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS): return None
        if any(type(pair) is not tuple or len(pair) != 2 for pair in request_foundations): return None
        observations = tuple(_observe(*pair) for pair in request_foundations)
        if any(x is None for x in observations): return None
        if tuple(x.skill_id for x in observations) != SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS: return None
        if len({x.request.request_id for x in observations}) != len(observations): return None
        qualified = all(x.qualified and x.request_verified for x in observations)
        topo_digest = _digest("TOPOLOGY", TOPOLOGY)
        draft = IsolatedExecutableRequestQualificationReport(
            VERSION, SCOPE, REQUIREMENT_ID, SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS, observations,
            tuple(x.request.request_digest for x in observations), TOPOLOGY, topo_digest,
            sum(x.qualified for x in observations), sum(not x.qualified for x in observations), qualified,
            STATUS if qualified else "EXECUTABLE_REQUEST_QUALIFICATION_REJECTED",
            DIAGNOSTIC if qualified else "CANONICAL_EXECUTABLE_REQUEST_REJECTED",
            False, False, False, False, False, 0, 0, 0, 0, 0,
            IsolatedExecutableRequestQualificationAuthorityBoundary())
        return replace(draft, report_digest=_digest("REPORT", _material(draft, "report_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return None


def verify_isolated_executable_request_observation(value: Any) -> bool:
    try:
        if type(value) is not IsolatedExecutableRequestObservation or not _HEX.fullmatch(value.observation_digest): return False
        if not _boundary_false(value.authority_boundary): return False
        expected = _observe(value.foundation, value.preauth_report)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def verify_isolated_executable_request_qualification_report(value: Any) -> bool:
    try:
        if type(value) is not IsolatedExecutableRequestQualificationReport: return False
        if not _HEX.fullmatch(value.topology_digest) or not _HEX.fullmatch(value.report_digest): return False
        if not _boundary_false(value.authority_boundary): return False
        if not all(verify_isolated_executable_request_observation(x) for x in value.observations): return False
        pairs = tuple((x.foundation, x.preauth_report) for x in value.observations)
        expected = create_isolated_executable_request_qualification_report(pairs)
        return expected is not None and value == expected
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


__all__ = tuple(name for name in globals() if name.startswith(("Isolated", "create_isolated_", "verify_isolated_"))
                or name in ("VERSION", "SCOPE", "REQUIREMENT_ID", "STATUS", "DIAGNOSTIC",
                            "SUPPORTED_EXECUTABLE_REQUEST_SKILL_IDS", "CANONICAL_SCENARIO_IDS", "TOPOLOGY"))
