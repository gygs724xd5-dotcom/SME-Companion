"""Passive turn provenance for the release-controlled production gate owner."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    ProductionFeatureGateEvaluation,
    verify_production_feature_gate_evaluation,
)
from brain.production_feature_gate_release_owner import (
    ProductionFeatureGateReleaseOwnerSnapshot,
    verify_production_feature_gate_release_owner,
)
from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context


PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_VERSION = "5.15.24.7.4.7"
PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_SCOPE = (
    "READ_ONLY_RELEASE_CONTROLLED_PRODUCTION_FEATURE_GATE_EVALUATION_BINDING"
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionFeatureGateReleaseRuntimeAuthorityBoundary:
    routing: bool = False
    planning: bool = False
    response_selection: bool = False
    response_guard: bool = False
    response_commit: bool = False
    persistence: bool = False
    tool_execution: bool = False
    feature_gate_mutation: bool = False
    production_activation: bool = False
    execution: bool = False
    presentation: bool = False
    authorization: bool = False
    adapter: bool = False
    delivery: bool = False


@dataclass(frozen=True)
class ProductionFeatureGateReleaseRuntimeBinding:
    version: str
    scope: str
    turn_context: ProductionTurnContext
    release_owner: ProductionFeatureGateReleaseOwnerSnapshot
    feature_gate_evaluation: ProductionFeatureGateEvaluation
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    user_message_digest: str
    source_identity: str
    release_revision_id: str
    release_revision_digest: str
    release_owner_digest: str
    configuration_digest: str
    evaluation_digest: str
    gate_name: str
    configured_state: bool
    effective_state: bool
    default_denied: bool
    transition_applied: bool
    activation_permitted: bool = False
    mutation_permitted: bool = False
    executable_output: None = None
    authority_boundary: ProductionFeatureGateReleaseRuntimeAuthorityBoundary = (
        ProductionFeatureGateReleaseRuntimeAuthorityBoundary()
    )
    binding_digest: str = ""

    def __deepcopy__(self, memo: dict[int, Any]) -> "ProductionFeatureGateReleaseRuntimeBinding":
        return self


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported release runtime binding material")


def _digest(value: Any) -> str:
    encoded = json.dumps(
        _canonical(("PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_BINDING", value)),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material(value: ProductionFeatureGateReleaseRuntimeBinding) -> tuple[Any, ...]:
    return tuple(
        getattr(value, field.name) for field in fields(value) if field.name != "binding_digest"
    )


def _all_false(value: Any) -> bool:
    return type(value) is ProductionFeatureGateReleaseRuntimeAuthorityBoundary and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False
        for field in fields(value)
    )


def create_production_feature_gate_release_runtime_binding(
    context: Any, release_owner: Any, evaluation: Any
) -> ProductionFeatureGateReleaseRuntimeBinding | None:
    """Bind exact verified artifacts without evaluating, activating, or mutating anything."""
    try:
        if not verify_production_turn_context(context):
            return None
        if not verify_production_feature_gate_release_owner(release_owner):
            return None
        if not verify_production_feature_gate_evaluation(
            evaluation, release_owner.configuration, context
        ):
            return None
        if evaluation.gate_name != LIMITED_COST_RESPONSE_RUNTIME_BRIDGE:
            return None
        if (
            release_owner.configuration is not release_owner.release_revision.configuration
            or release_owner.configuration_digest != release_owner.configuration.source_digest
            or evaluation.source_digest != release_owner.configuration_digest
            or evaluation.source_identity != release_owner.configuration.trusted_source_identity
        ):
            return None
        draft = ProductionFeatureGateReleaseRuntimeBinding(
            PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_VERSION,
            PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_SCOPE,
            context,
            release_owner,
            evaluation,
            context.conversation_id,
            context.turn_id,
            context.turn_ordinal,
            context.turn_digest,
            context.user_message_digest,
            release_owner.source_identity,
            release_owner.release_revision.revision_id,
            release_owner.release_revision.revision_digest,
            release_owner.owner_digest,
            release_owner.configuration_digest,
            evaluation.evaluation_digest,
            evaluation.gate_name,
            False,
            False,
            True,
            False,
        )
        return replace(draft, binding_digest=_digest(_material(draft)))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return None


def verify_production_feature_gate_release_runtime_binding(
    value: Any, context: Any, release_owner: Any, evaluation: Any
) -> bool:
    try:
        if type(value) is not ProductionFeatureGateReleaseRuntimeBinding:
            return False
        if not _HEX.fullmatch(value.binding_digest) or not _all_false(value.authority_boundary):
            return False
        if value.turn_context is not context or value.release_owner is not release_owner:
            return False
        if value.feature_gate_evaluation is not evaluation:
            return False
        if any(
            getattr(value, name) is not False
            for name in ("configured_state", "effective_state", "transition_applied",
                         "activation_permitted", "mutation_permitted")
        ):
            return False
        if value.default_denied is not True or value.executable_output is not None:
            return False
        expected = create_production_feature_gate_release_runtime_binding(
            context, release_owner, evaluation
        )
        return value == expected and value.binding_digest == _digest(_material(value))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def resolve_production_feature_gate_release_runtime_binding(
    context: Any,
    release_owner: Any,
    evaluation: Any,
    current_binding: Any = None,
) -> ProductionFeatureGateReleaseRuntimeBinding | None:
    """Reuse the exact same-turn binding; otherwise create passive evidence or fail closed."""
    expected = create_production_feature_gate_release_runtime_binding(
        context, release_owner, evaluation
    )
    if expected is None:
        return None
    if verify_production_feature_gate_release_runtime_binding(
        current_binding, context, release_owner, evaluation
    ):
        return current_binding
    return expected


__all__ = (
    "PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_VERSION",
    "PRODUCTION_FEATURE_GATE_RELEASE_RUNTIME_SCOPE",
    "ProductionFeatureGateReleaseRuntimeAuthorityBoundary",
    "ProductionFeatureGateReleaseRuntimeBinding",
    "create_production_feature_gate_release_runtime_binding",
    "verify_production_feature_gate_release_runtime_binding",
    "resolve_production_feature_gate_release_runtime_binding",
)
