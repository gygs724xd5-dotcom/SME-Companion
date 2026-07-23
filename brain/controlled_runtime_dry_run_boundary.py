"""V5.15.24.7.4.25 canonical, non-operational runtime dry-run boundary.

This module only constructs and verifies an immutable description of a runtime
path.  It has no executor, tool, store, deployment, activation, or rollback
interface and therefore grants no production authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping


VERSION = "5.15.24.7.4.25"
SCHEMA = "controlled-runtime-dry-run-boundary/v1"
POLICY_IDENTITY = "controlled-runtime-dry-run-policy"
POLICY_VERSION = "1"

DRY_RUN_READY = "DRY_RUN_READY"
DRY_RUN_COMPLETED = "DRY_RUN_COMPLETED"
DRY_RUN_REJECTED = "DRY_RUN_REJECTED"
RUNTIME_STATES = (DRY_RUN_READY, DRY_RUN_COMPLETED, DRY_RUN_REJECTED)

CHECK_ORDER = (
    "REQUEST_TYPE_VERIFIED",
    "REQUEST_SCHEMA_VERIFIED",
    "REQUEST_STATUS_READY",
    "POLICY_TYPE_VERIFIED",
    "POLICY_IDENTITY_VERIFIED",
    "POLICY_DIGEST_VERIFIED",
    "PLANNER_IDENTITY_VERIFIED",
    "SKILL_IDENTITY_VERIFIED",
    "SKILL_CONTRACT_VERIFIED",
    "EVIDENCE_DIGEST_VERIFIED",
    "OPERATIONAL_ACCEPTANCE_DIGEST_VERIFIED",
    "EXECUTION_NOT_REQUESTED",
    "DEPLOYMENT_NOT_REQUESTED",
    "ACTIVATION_NOT_REQUESTED",
    "EXTERNAL_CALL_NOT_REQUESTED",
    "RUNTIME_MUTATION_NOT_REQUESTED",
    "ORDERED_CHECKS_VERIFIED",
    "BOUNDARY_INVARIANTS_VERIFIED",
)

BOUNDARY_FIELDS = (
    "execution_performed",
    "deployment_performed",
    "rollback_performed",
    "activation_performed",
    "runtime_mutated",
    "business_data_changed",
    "feature_gate_changed",
    "external_service_called",
    "side_effect_detected",
)

_HEX = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


@dataclass(frozen=True)
class ControlledRuntimeDryRunPolicy:
    schema: str
    identity: str
    version: str
    ready_status: str
    completed_status: str
    rejected_status: str
    required_checks: tuple[str, ...]
    required_false_boundaries: tuple[str, ...]
    policy_digest: str = ""


@dataclass(frozen=True)
class ControlledRuntimeDryRunRequest:
    schema: str
    planner_identity: str
    selected_skill_identity: str
    validated_skill_contract: str
    evidence_digest: str
    operational_failure_acceptance_digest: str
    runtime_policy_digest: str
    dry_run_status: str = DRY_RUN_READY
    execution_requested: bool = False
    deployment_requested: bool = False
    activation_requested: bool = False
    external_call_attempted: bool = False
    runtime_mutation_requested: bool = False


@dataclass(frozen=True)
class ControlledRuntimeDryRunResult:
    planner_identity: str
    selected_skill_identity: str
    validated_skill_contract: str
    evidence_digest: str
    operational_failure_acceptance_digest: str
    runtime_policy_digest: str
    runtime_result_digest: str
    dry_run_status: str
    execution_performed: bool = False
    deployment_performed: bool = False
    rollback_performed: bool = False
    activation_performed: bool = False
    runtime_mutated: bool = False
    business_data_changed: bool = False
    feature_gate_changed: bool = False
    external_service_called: bool = False
    side_effect_detected: bool = False


@dataclass(frozen=True)
class ControlledRuntimeDryRunVerifier:
    schema: str
    policy: ControlledRuntimeDryRunPolicy
    ordered_checks: tuple[str, ...]
    verifier_digest: str = ""

    def verify_request(self, request: Any) -> bool:
        return verify_controlled_runtime_dry_run_request(request, self.policy)

    def verify_result(self, request: Any, result: Any) -> bool:
        return verify_controlled_runtime_dry_run_result(request, result, self)


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if type(value) is dict:
        return [[str(key), _canonical(value[key])] for key in sorted(value)]
    if isinstance(value, Mapping):
        raise ValueError("mutable or substituted mapping")
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))]
                for field in fields(value)]
    raise ValueError("unsupported dry-run material")


def _digest(label: str, value: Any) -> str:
    encoded = json.dumps(
        _canonical((VERSION, label, value)),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: Any, *excluded: str) -> tuple[Any, ...]:
    return tuple(
        getattr(value, field.name)
        for field in fields(value)
        if field.name not in excluded
    )


def _build_policy() -> ControlledRuntimeDryRunPolicy:
    draft = ControlledRuntimeDryRunPolicy(
        SCHEMA,
        POLICY_IDENTITY,
        POLICY_VERSION,
        DRY_RUN_READY,
        DRY_RUN_COMPLETED,
        DRY_RUN_REJECTED,
        CHECK_ORDER,
        BOUNDARY_FIELDS,
    )
    return replace(
        draft,
        policy_digest=_digest("RUNTIME_POLICY", _material(draft, "policy_digest")),
    )


CANONICAL_DRY_RUN_POLICY = _build_policy()


def _build_verifier() -> ControlledRuntimeDryRunVerifier:
    draft = ControlledRuntimeDryRunVerifier(
        SCHEMA, CANONICAL_DRY_RUN_POLICY, CHECK_ORDER
    )
    return replace(
        draft,
        verifier_digest=_digest("RUNTIME_VERIFIER", _material(draft, "verifier_digest")),
    )


CANONICAL_DRY_RUN_VERIFIER = _build_verifier()


def verify_controlled_runtime_dry_run_policy(value: Any) -> bool:
    try:
        return (
            type(value) is ControlledRuntimeDryRunPolicy
            and value == CANONICAL_DRY_RUN_POLICY
            and type(value.required_checks) is tuple
            and value.required_checks == CHECK_ORDER
            and value.required_false_boundaries == BOUNDARY_FIELDS
            and bool(_HEX.fullmatch(value.policy_digest))
        )
    except (AttributeError, TypeError, ValueError):
        return False


def verify_controlled_runtime_dry_run_verifier(value: Any) -> bool:
    try:
        return (
            type(value) is ControlledRuntimeDryRunVerifier
            and value == CANONICAL_DRY_RUN_VERIFIER
            and value.policy is CANONICAL_DRY_RUN_POLICY
            and value.ordered_checks == CHECK_ORDER
            and bool(_HEX.fullmatch(value.verifier_digest))
            and value.verifier_digest
            == _digest("RUNTIME_VERIFIER", _material(value, "verifier_digest"))
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def _valid_identity(value: Any) -> bool:
    return type(value) is str and bool(_IDENTITY.fullmatch(value))


def _valid_contract(value: Any) -> bool:
    return (
        type(value) is str
        and 0 < len(value) <= 4096
        and value == value.strip()
        and "\x00" not in value
    )


def verify_controlled_runtime_dry_run_request(
    request: Any,
    policy: Any = CANONICAL_DRY_RUN_POLICY,
) -> bool:
    try:
        return (
            type(request) is ControlledRuntimeDryRunRequest
            and verify_controlled_runtime_dry_run_policy(policy)
            and policy is CANONICAL_DRY_RUN_POLICY
            and request.schema == SCHEMA
            and request.dry_run_status == DRY_RUN_READY
            and _valid_identity(request.planner_identity)
            and _valid_identity(request.selected_skill_identity)
            and _valid_contract(request.validated_skill_contract)
            and type(request.evidence_digest) is str
            and bool(_HEX.fullmatch(request.evidence_digest))
            and type(request.operational_failure_acceptance_digest) is str
            and bool(_HEX.fullmatch(request.operational_failure_acceptance_digest))
            and request.runtime_policy_digest == policy.policy_digest
            and all(
                type(getattr(request, field)) is bool
                and getattr(request, field) is False
                for field in (
                    "execution_requested",
                    "deployment_requested",
                    "activation_requested",
                    "external_call_attempted",
                    "runtime_mutation_requested",
                )
            )
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _result_material(request: ControlledRuntimeDryRunRequest) -> tuple[Any, ...]:
    boundary_flags = tuple((name, False) for name in BOUNDARY_FIELDS)
    return (
        request.planner_identity,
        request.selected_skill_identity,
        request.validated_skill_contract,
        request.evidence_digest,
        request.operational_failure_acceptance_digest,
        request.runtime_policy_digest,
        CHECK_ORDER,
        boundary_flags,
        DRY_RUN_COMPLETED,
    )


def simulate_controlled_runtime_dry_run(
    request: Any,
) -> ControlledRuntimeDryRunResult | None:
    """Deterministically describe the path; never invoke any path component."""
    try:
        if not verify_controlled_runtime_dry_run_request(request):
            return None
        runtime_result_digest = _digest("RUNTIME_RESULT", _result_material(request))
        return ControlledRuntimeDryRunResult(
            request.planner_identity,
            request.selected_skill_identity,
            request.validated_skill_contract,
            request.evidence_digest,
            request.operational_failure_acceptance_digest,
            request.runtime_policy_digest,
            runtime_result_digest,
            DRY_RUN_COMPLETED,
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def classify_controlled_runtime_dry_run(request: Any) -> str:
    return (
        DRY_RUN_COMPLETED
        if simulate_controlled_runtime_dry_run(request) is not None
        else DRY_RUN_REJECTED
    )


def verify_controlled_runtime_dry_run_result(
    request: Any,
    result: Any,
    verifier: Any = CANONICAL_DRY_RUN_VERIFIER,
) -> bool:
    try:
        if not verify_controlled_runtime_dry_run_verifier(verifier):
            return False
        if not verifier.verify_request(request):
            return False
        if type(result) is not ControlledRuntimeDryRunResult:
            return False
        if result.dry_run_status != DRY_RUN_COMPLETED:
            return False
        if any(
            type(getattr(result, field)) is not bool or getattr(result, field) is not False
            for field in BOUNDARY_FIELDS
        ):
            return False
        expected = simulate_controlled_runtime_dry_run(request)
        return (
            expected is not None
            and result == expected
            and bool(_HEX.fullmatch(result.runtime_result_digest))
            and result.runtime_result_digest
            == _digest("RUNTIME_RESULT", _result_material(request))
        )
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "VERSION",
    "SCHEMA",
    "POLICY_IDENTITY",
    "POLICY_VERSION",
    "DRY_RUN_READY",
    "DRY_RUN_COMPLETED",
    "DRY_RUN_REJECTED",
    "RUNTIME_STATES",
    "CHECK_ORDER",
    "BOUNDARY_FIELDS",
    "ControlledRuntimeDryRunPolicy",
    "ControlledRuntimeDryRunRequest",
    "ControlledRuntimeDryRunResult",
    "ControlledRuntimeDryRunVerifier",
    "CANONICAL_DRY_RUN_POLICY",
    "CANONICAL_DRY_RUN_VERIFIER",
    "simulate_controlled_runtime_dry_run",
    "classify_controlled_runtime_dry_run",
    "verify_controlled_runtime_dry_run_policy",
    "verify_controlled_runtime_dry_run_request",
    "verify_controlled_runtime_dry_run_verifier",
    "verify_controlled_runtime_dry_run_result",
)
