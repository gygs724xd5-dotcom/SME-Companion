"""Read-only production feature-gate policy evidence bound to a verified turn."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any, Iterable

from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context


PRODUCTION_FEATURE_GATE_OWNER_VERSION = "5.15.24.5"
PRODUCTION_FEATURE_GATE_CONFIGURATION_VERSION = "5.15.24.5"
LIMITED_COST_RESPONSE_RUNTIME_BRIDGE = "LIMITED_COST_RESPONSE_RUNTIME_BRIDGE"
SUPPORTED_PRODUCTION_FEATURE_GATES = (LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,)
PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY = "production-empty-default-deny-v5.15.24.5"
PURE_TEST_TRUSTED_SOURCE_IDENTITY = "pure-test-trusted-feature-gate-source-v5.15.24.5"
TRUSTED_PRODUCTION_FEATURE_GATE_SOURCE_IDENTITIES = (
    PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY,
    PURE_TEST_TRUSTED_SOURCE_IDENTITY,
)

GATE_CONFIGURED_ENABLED = "GATE_CONFIGURED_ENABLED"
GATE_CONFIGURED_DISABLED = "GATE_CONFIGURED_DISABLED"
GATE_MISSING_DEFAULT_DENY = "GATE_MISSING_DEFAULT_DENY"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionFeatureGateConfiguration:
    configuration_version: str
    trusted_source_identity: str
    gate_entries: tuple[tuple[str, bool], ...]
    mutation_authority: bool = False
    source_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateEvaluation:
    owner_version: str
    configuration_version: str
    conversation_id: str
    turn_id: str
    turn_digest: str
    gate_name: str
    configured_state: bool
    effective_state: bool
    default_denied: bool
    source_identity: str
    source_digest: str
    evaluation_reason: str
    read_only: bool = True
    mutation_permitted: bool = False
    activation_permitted: bool = False
    routing_authority: bool = False
    planning_authority: bool = False
    response_selection_authority: bool = False
    response_guard_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    evaluation_digest: str = ""


# The immutable evaluation is the canonical per-turn snapshot evidence.
ProductionFeatureGateSnapshot = ProductionFeatureGateEvaluation


_EVALUATION_FALSE_FLAGS = (
    "mutation_permitted",
    "activation_permitted",
    "routing_authority",
    "planning_authority",
    "response_selection_authority",
    "response_guard_authority",
    "response_commit_authority",
    "persistence_authority",
    "tool_execution_authority",
)


def _sha256(material: Any) -> str:
    try:
        encoded = json.dumps(
            material, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return ""
    return hashlib.sha256(encoded).hexdigest()


def _canonical_entries(entries: Any) -> tuple[tuple[str, bool], ...]:
    if isinstance(entries, (str, bytes, dict)):
        raise ValueError("gate entries must be an ordered iterable of exact pairs")
    try:
        result = tuple(entries)
    except TypeError as exc:
        raise ValueError("gate entries must be an ordered iterable of exact pairs") from exc
    seen: set[str] = set()
    canonical: list[tuple[str, bool]] = []
    for entry in result:
        if type(entry) not in (tuple, list) or len(entry) != 2:
            raise ValueError("each gate entry must be an exact name/state pair")
        name, state = entry
        if type(name) is not str or name not in SUPPORTED_PRODUCTION_FEATURE_GATES:
            raise ValueError("unknown, blank, alias, global, or wildcard gate")
        if name in seen:
            raise ValueError("duplicate gate")
        if type(state) is not bool:
            raise ValueError("gate state must be an exact boolean")
        seen.add(name)
        canonical.append((name, state))
    return tuple(canonical)


def compute_production_feature_gate_source_digest(
    configuration_version: Any,
    trusted_source_identity: Any,
    gate_entries: Any,
    mutation_authority: Any = False,
) -> str:
    try:
        if configuration_version != PRODUCTION_FEATURE_GATE_CONFIGURATION_VERSION:
            return ""
        if trusted_source_identity not in TRUSTED_PRODUCTION_FEATURE_GATE_SOURCE_IDENTITIES:
            return ""
        if type(mutation_authority) is not bool or mutation_authority:
            return ""
        entries = _canonical_entries(gate_entries)
        return _sha256((
            "PRODUCTION_FEATURE_GATE_CONFIGURATION",
            configuration_version,
            trusted_source_identity,
            entries,
            ("mutation_authority", False),
        ))
    except (TypeError, ValueError):
        return ""


def create_production_feature_gate_configuration(
    trusted_source_identity: Any,
    gate_entries: Iterable[tuple[str, bool]],
) -> ProductionFeatureGateConfiguration:
    if trusted_source_identity not in TRUSTED_PRODUCTION_FEATURE_GATE_SOURCE_IDENTITIES:
        raise ValueError("untrusted or blank feature-gate source identity")
    entries = _canonical_entries(gate_entries)
    digest = compute_production_feature_gate_source_digest(
        PRODUCTION_FEATURE_GATE_CONFIGURATION_VERSION,
        trusted_source_identity,
        entries,
    )
    if not digest:
        raise ValueError("invalid feature-gate configuration")
    return ProductionFeatureGateConfiguration(
        configuration_version=PRODUCTION_FEATURE_GATE_CONFIGURATION_VERSION,
        trusted_source_identity=trusted_source_identity,
        gate_entries=entries,
        source_digest=digest,
    )


def verify_production_feature_gate_configuration(value: Any) -> bool:
    try:
        if type(value) is not ProductionFeatureGateConfiguration:
            return False
        expected = create_production_feature_gate_configuration(
            value.trusted_source_identity, value.gate_entries
        )
        return value == expected and bool(_DIGEST.fullmatch(value.source_digest))
    except (AttributeError, TypeError, ValueError):
        return False


def exact_production_feature_gate_lookup(
    configuration: Any, gate_name: Any
) -> bool | None:
    if not verify_production_feature_gate_configuration(configuration):
        raise ValueError("feature-gate configuration verification failed")
    if type(gate_name) is not str or gate_name not in SUPPORTED_PRODUCTION_FEATURE_GATES:
        raise ValueError("unknown, blank, alias, global, or wildcard gate")
    return dict(configuration.gate_entries).get(gate_name)


def _evaluation_digest(value: ProductionFeatureGateEvaluation) -> str:
    return _sha256((
        "PRODUCTION_FEATURE_GATE_EVALUATION",
        value.owner_version,
        value.configuration_version,
        value.conversation_id,
        value.turn_id,
        value.turn_digest,
        value.gate_name,
        value.configured_state,
        value.effective_state,
        value.default_denied,
        value.source_identity,
        value.source_digest,
        value.evaluation_reason,
        value.read_only,
        tuple((name, getattr(value, name)) for name in _EVALUATION_FALSE_FLAGS),
    ))


def evaluate_production_feature_gate(
    configuration: Any,
    turn_context: Any,
    gate_name: Any,
) -> ProductionFeatureGateEvaluation:
    if not verify_production_feature_gate_configuration(configuration):
        raise ValueError("feature-gate configuration verification failed")
    if not verify_production_turn_context(turn_context):
        raise ValueError("verified ProductionTurnContext required")
    configured = exact_production_feature_gate_lookup(configuration, gate_name)
    if configured is None:
        state, default_denied, reason = False, True, GATE_MISSING_DEFAULT_DENY
    elif configured is True:
        state, default_denied, reason = True, False, GATE_CONFIGURED_ENABLED
    else:
        state, default_denied, reason = False, False, GATE_CONFIGURED_DISABLED
    draft = ProductionFeatureGateEvaluation(
        owner_version=PRODUCTION_FEATURE_GATE_OWNER_VERSION,
        configuration_version=configuration.configuration_version,
        conversation_id=turn_context.conversation_id,
        turn_id=turn_context.turn_id,
        turn_digest=turn_context.turn_digest,
        gate_name=gate_name,
        configured_state=state,
        effective_state=state,
        default_denied=default_denied,
        source_identity=configuration.trusted_source_identity,
        source_digest=configuration.source_digest,
        evaluation_reason=reason,
    )
    return replace(draft, evaluation_digest=_evaluation_digest(draft))


def verify_production_feature_gate_evaluation(
    value: Any,
    configuration: Any,
    turn_context: Any,
) -> bool:
    try:
        if type(value) is not ProductionFeatureGateEvaluation:
            return False
        if not _DIGEST.fullmatch(value.evaluation_digest):
            return False
        expected = evaluate_production_feature_gate(configuration, turn_context, value.gate_name)
        return value == expected
    except (AttributeError, TypeError, ValueError):
        return False


def resolve_production_feature_gate_evaluation(
    current: Any,
    configuration: Any,
    turn_context: ProductionTurnContext,
    gate_name: Any,
) -> ProductionFeatureGateEvaluation:
    """Reuse only canonical evidence for the same source and verified turn."""
    if verify_production_feature_gate_evaluation(current, configuration, turn_context):
        if current.gate_name == gate_name:
            return current
    return evaluate_production_feature_gate(configuration, turn_context, gate_name)


PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION = (
    create_production_feature_gate_configuration(
        PRODUCTION_DEFAULT_DENY_SOURCE_IDENTITY,
        (),
    )
)
