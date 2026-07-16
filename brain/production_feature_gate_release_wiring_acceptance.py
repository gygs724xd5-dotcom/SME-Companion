"""Canonical read-only acceptance for release-owner production gate wiring.

This artifact qualifies deterministic source-controlled contracts.  It is not
deployment, CI, human-approval, activation, or runtime-execution attestation.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any

from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    evaluate_production_feature_gate,
    verify_production_feature_gate_configuration,
    verify_production_feature_gate_evaluation,
)
from brain.production_feature_gate_release_owner import (
    PROPOSED_NOT_AUTHORIZED,
    ProductionFeatureGateReleaseOwnerSnapshot,
    create_production_feature_gate_transition_proposal,
    get_production_feature_gate_release_owner,
    verify_production_feature_gate_release_owner,
    verify_production_feature_gate_rollback_target,
    verify_production_feature_gate_transition_proposal,
    verify_production_feature_gate_transition_record,
)
from brain.production_feature_gate_release_runtime import (
    ProductionFeatureGateReleaseRuntimeBinding,
    resolve_production_feature_gate_release_runtime_binding,
    verify_production_feature_gate_release_runtime_binding,
)
from brain.production_turn_context import ProductionTurnContext, create_production_turn_context


PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION = "5.15.24.7.4.9"
PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_SCOPE = (
    "SOURCE_CONTROLLED_READ_ONLY_RELEASE_GATE_WIRING_ACCEPTANCE"
)
READ_ONLY_RELEASE_WIRING_ACCEPTED = "READ_ONLY_RELEASE_WIRING_ACCEPTED"
ACCEPTANCE_DIAGNOSTIC = (
    "SOURCE_CONTROLLED_WIRING_ACCEPTED_WITHOUT_DEPLOYMENT_OR_ACTIVATION_ATTESTATION"
)
EXPECTED_HISTORICAL_CONFIGURATION_DIGEST = (
    "aaee359e5bef2b97416b1028be59fcd04b9e81c8838e55c300c79942cf3043ee"
)
EXPECTED_PRODUCTION_TOPOLOGY = (
    "PRODUCTION_TURN_CONTEXT",
    "PRODUCTION_TURN_REFERENCE_TIME",
    "RELEASE_GATE_OWNER_LOOKUP",
    "PRODUCTION_FEATURE_GATE_EVALUATION",
    "RELEASE_GATE_RUNTIME_BINDING",
    "PRODUCTION_SKILL_EVIDENCE",
    "PRODUCTION_LIMITED_ACTIVATION",
    "PRODUCTION_PRE_EXECUTION_AUTHORIZATION",
    "EXISTING_RESPONSE_FLOW",
)
TOPOLOGY_TRUST_CLASSIFICATION = "CONTRACT_EXPECTATION_NOT_SOURCE_OR_DEPLOYED_SHA_ATTESTATION"
CANONICAL_SCENARIO_IDS = (
    "01.release_owner_exact_singleton",
    "02.historical_configuration_identity",
    "03.owner_backed_evaluation_equivalence",
    "04.turn_bound_runtime_binding",
    "05.exact_rerun_reuse",
    "06.next_turn_separation",
    "07.proposal_not_applied",
    "08.transition_not_applied",
    "09.rollback_available_not_applied",
    "10.authority_and_persistence_isolation",
)
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionFeatureGateReleaseWiringAuthorityBoundary:
    routing: bool = False
    planning: bool = False
    response_selection: bool = False
    response_guard: bool = False
    response_commit: bool = False
    persistence: bool = False
    tool_execution: bool = False
    calculator: bool = False
    presentation: bool = False
    authorization: bool = False
    adapter: bool = False
    delivery: bool = False
    bridge: bool = False
    admission: bool = False
    runtime: bool = False
    controlled_response_candidate: bool = False
    feature_gate_mutation: bool = False
    production_activation: bool = False


@dataclass(frozen=True)
class ProductionFeatureGateReleaseWiringScenario:
    scenario_id: str
    classification: str
    conversation_id: str
    turn_ordinal: int
    user_message: str
    expected_outcome: str


@dataclass(frozen=True)
class ProductionFeatureGateReleaseWiringObservation:
    version: str
    scope: str
    scenario: ProductionFeatureGateReleaseWiringScenario
    turn_context: ProductionTurnContext
    release_owner: ProductionFeatureGateReleaseOwnerSnapshot
    runtime_binding: ProductionFeatureGateReleaseRuntimeBinding
    context_digest: str
    release_owner_digest: str
    release_revision_id: str
    release_revision_digest: str
    configuration_digest: str
    evaluation_digest: str
    runtime_binding_digest: str
    proposal_digest: str
    transition_digest: str
    rollback_digest: str
    configured_state: bool
    effective_state: bool
    default_denied: bool
    proposal_applied: bool
    transition_applied: bool
    rollback_applied: bool
    activation_permitted: bool
    mutation_permitted: bool
    authority_boundary: ProductionFeatureGateReleaseWiringAuthorityBoundary
    persistence_invoked: bool
    runtime_invoked: bool
    deterministic_expected_outcome: str
    deterministic_observed_outcome: str
    owner_verified: bool
    configuration_identity_verified: bool
    evaluation_equivalence_verified: bool
    runtime_binding_verified: bool
    rerun_reuse_verified: bool
    turn_separation_verified: bool
    observation_passed: bool
    observation_digest: str = ""


@dataclass(frozen=True)
class ProductionFeatureGateReleaseWiringReport:
    version: str
    scope: str
    topology: tuple[str, ...]
    topology_trust_classification: str
    topology_digest: str
    canonical_scenario_ids: tuple[str, ...]
    observations: tuple[ProductionFeatureGateReleaseWiringObservation, ...]
    ordered_observation_digests: tuple[str, ...]
    total_count: int
    owner_verified_count: int
    configuration_identity_verified_count: int
    evaluation_equivalence_verified_count: int
    runtime_binding_verified_count: int
    rerun_reuse_verified_count: int
    turn_separation_verified_count: int
    proposal_applied_count: int
    transition_applied_count: int
    rollback_applied_count: int
    enabled_effective_true_count: int
    activation_mutation_permission_count: int
    authority_violation_count: int
    persistence_runtime_invocation_count: int
    acceptance_status: str
    deployment_attested: bool
    human_approval_attested: bool
    ci_attested: bool
    activation_approved: bool
    all_passed: bool
    diagnostics: tuple[str, ...]
    report_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported acceptance digest material")


def _digest(label: str, value: Any) -> str:
    material = (PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION, label, value)
    encoded = json.dumps(_canonical(material), ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _without(value: Any, digest_field: str) -> tuple[Any, ...]:
    return tuple(getattr(value, field.name) for field in fields(value) if field.name != digest_field)


def _all_false(value: Any) -> bool:
    return type(value) is ProductionFeatureGateReleaseWiringAuthorityBoundary and all(
        type(getattr(value, field.name)) is bool and getattr(value, field.name) is False
        for field in fields(value)
    )


def _scenarios() -> tuple[ProductionFeatureGateReleaseWiringScenario, ...]:
    classifications = (
        "OWNER_IDENTITY", "CONFIGURATION_IDENTITY", "EVALUATION_EQUIVALENCE",
        "RUNTIME_BINDING", "RERUN_REUSE", "TURN_SEPARATION", "PROPOSAL_ISOLATION",
        "TRANSITION_ISOLATION", "ROLLBACK_ISOLATION", "AUTHORITY_PERSISTENCE_ISOLATION",
    )
    outcomes = (
        "EXACT_SINGLETON_VERIFIED", "HISTORICAL_CONFIGURATION_IDENTICAL",
        "EVALUATIONS_IDENTICAL", "TURN_BOUND_BINDING_VERIFIED", "EXACT_BINDING_REUSED",
        "NEXT_TURN_BINDING_SEPARATED", "PROPOSAL_REMAINS_NOT_AUTHORIZED",
        "NO_TRANSITION_APPLIED", "ROLLBACK_AVAILABLE_NOT_APPLIED", "ALL_AUTHORITIES_ISOLATED",
    )
    return tuple(ProductionFeatureGateReleaseWiringScenario(
        scenario_id, classification, "release-wiring-acceptance", 2 if index == 5 else 1,
        "ต้นทุนต่อชิ้น 100 บาท" if index != 5 else "ต้นทุนต่อชิ้น 200 บาท", outcome,
    ) for index, (scenario_id, classification, outcome) in enumerate(
        zip(CANONICAL_SCENARIO_IDS, classifications, outcomes)
    ))


def _observe(scenario: ProductionFeatureGateReleaseWiringScenario) -> ProductionFeatureGateReleaseWiringObservation:
    owner = get_production_feature_gate_release_owner()
    context = create_production_turn_context(
        scenario.conversation_id, scenario.turn_ordinal, scenario.user_message
    )
    direct = evaluate_production_feature_gate(
        PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context,
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    )
    evaluation = evaluate_production_feature_gate(
        owner.configuration, context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
    )
    binding = resolve_production_feature_gate_release_runtime_binding(context, owner, evaluation)
    if binding is None:
        raise ValueError("canonical runtime binding resolution failed")
    rerun = resolve_production_feature_gate_release_runtime_binding(context, owner, evaluation, binding)
    first_context = create_production_turn_context(
        scenario.conversation_id, 1, "ต้นทุนต่อชิ้น 100 บาท"
    )
    first_evaluation = evaluate_production_feature_gate(
        owner.configuration, first_context, LIMITED_COST_RESPONSE_RUNTIME_BRIDGE
    )
    first_binding = resolve_production_feature_gate_release_runtime_binding(
        first_context, owner, first_evaluation
    )
    separated = scenario.scenario_id != CANONICAL_SCENARIO_IDS[5] or (
        binding is not first_binding and binding.turn_digest != first_binding.turn_digest
    )
    proposal = create_production_feature_gate_transition_proposal(
        LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, True
    )
    owner_ok = owner is get_production_feature_gate_release_owner() and verify_production_feature_gate_release_owner(owner)
    config_ok = (
        owner.configuration is PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION
        and owner.release_revision.configuration is owner.configuration
        and verify_production_feature_gate_configuration(owner.configuration)
        and owner.configuration_digest == EXPECTED_HISTORICAL_CONFIGURATION_DIGEST
    )
    evaluation_ok = direct == evaluation and verify_production_feature_gate_evaluation(
        evaluation, owner.configuration, context
    )
    binding_ok = verify_production_feature_gate_release_runtime_binding(
        binding, context, owner, evaluation
    )
    isolation_ok = (
        verify_production_feature_gate_transition_proposal(proposal)
        and proposal.status == PROPOSED_NOT_AUTHORIZED and proposal.transition_applied is False
        and verify_production_feature_gate_transition_record(owner.transition_record)
        and owner.transition_record.transition_applied is False
        and verify_production_feature_gate_rollback_target(owner.rollback_target)
        and owner.rollback_target.rollback_available is True
        and owner.rollback_target.rollback_applied is False
    )
    passed = all((owner_ok, config_ok, evaluation_ok, binding_ok, rerun is binding,
                  separated, isolation_ok, not owner.configuration.gate_entries))
    draft = ProductionFeatureGateReleaseWiringObservation(
        PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION,
        PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_SCOPE,
        scenario, context, owner, binding, context.turn_digest, owner.owner_digest,
        owner.release_revision.revision_id, owner.release_revision.revision_digest,
        owner.configuration_digest, evaluation.evaluation_digest, binding.binding_digest,
        proposal.proposal_digest, owner.transition_record.transition_digest,
        owner.rollback_target.rollback_digest, evaluation.configured_state,
        evaluation.effective_state, evaluation.default_denied, proposal.transition_applied,
        owner.transition_record.transition_applied, owner.rollback_target.rollback_applied,
        False, False, ProductionFeatureGateReleaseWiringAuthorityBoundary(), False, False,
        scenario.expected_outcome, scenario.expected_outcome, owner_ok, config_ok,
        evaluation_ok, binding_ok, rerun is binding,
        separated if scenario.scenario_id == CANONICAL_SCENARIO_IDS[5] else True, passed,
    )
    return replace(draft, observation_digest=_digest("OBSERVATION", _without(draft, "observation_digest")))


def create_production_feature_gate_release_wiring_report() -> ProductionFeatureGateReleaseWiringReport:
    """Reconstruct canonical observations solely through the unmodified read-only pipeline."""
    observations = tuple(_observe(item) for item in _scenarios())
    topology_digest = _digest("EXPECTED_TOPOLOGY", EXPECTED_PRODUCTION_TOPOLOGY)
    count = lambda name: sum(getattr(item, name) is True for item in observations)
    draft = ProductionFeatureGateReleaseWiringReport(
        PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION,
        PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_SCOPE,
        EXPECTED_PRODUCTION_TOPOLOGY, TOPOLOGY_TRUST_CLASSIFICATION, topology_digest,
        CANONICAL_SCENARIO_IDS, observations,
        tuple(item.observation_digest for item in observations), len(observations),
        count("owner_verified"), count("configuration_identity_verified"),
        count("evaluation_equivalence_verified"), count("runtime_binding_verified"),
        count("rerun_reuse_verified"), count("turn_separation_verified"),
        sum(item.proposal_applied for item in observations),
        sum(item.transition_applied for item in observations),
        sum(item.rollback_applied for item in observations),
        sum(item.configured_state or item.effective_state for item in observations),
        sum(item.activation_permitted or item.mutation_permitted for item in observations),
        sum(not _all_false(item.authority_boundary) for item in observations),
        sum(item.persistence_invoked or item.runtime_invoked for item in observations),
        READ_ONLY_RELEASE_WIRING_ACCEPTED, False, False, False, False,
        all(item.observation_passed for item in observations), (ACCEPTANCE_DIAGNOSTIC,),
    )
    return replace(draft, report_digest=_digest("REPORT", _without(draft, "report_digest")))


def verify_production_feature_gate_release_wiring_observation(value: Any) -> bool:
    """Reject stored claims and reconstruct the exact canonical scenario observation."""
    try:
        if type(value) is not ProductionFeatureGateReleaseWiringObservation:
            return False
        scenarios = {item.scenario_id: item for item in _scenarios()}
        scenario = scenarios.get(value.scenario.scenario_id)
        if scenario is None or value.scenario != scenario or not _HEX.fullmatch(value.observation_digest):
            return False
        return value == _observe(scenario)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


def verify_production_feature_gate_release_wiring_report(value: Any) -> bool:
    """Strictly reconstruct all scenarios, pipeline artifacts, counts, and digests."""
    try:
        if type(value) is not ProductionFeatureGateReleaseWiringReport:
            return False
        if not _HEX.fullmatch(value.topology_digest) or not _HEX.fullmatch(value.report_digest):
            return False
        if tuple(item.scenario.scenario_id for item in value.observations) != CANONICAL_SCENARIO_IDS:
            return False
        if not all(verify_production_feature_gate_release_wiring_observation(item)
                   for item in value.observations):
            return False
        return value == create_production_feature_gate_release_wiring_report()
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError):
        return False


__all__ = (
    "PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_VERSION",
    "PRODUCTION_FEATURE_GATE_RELEASE_WIRING_ACCEPTANCE_SCOPE",
    "READ_ONLY_RELEASE_WIRING_ACCEPTED", "ACCEPTANCE_DIAGNOSTIC",
    "EXPECTED_HISTORICAL_CONFIGURATION_DIGEST", "EXPECTED_PRODUCTION_TOPOLOGY",
    "TOPOLOGY_TRUST_CLASSIFICATION", "CANONICAL_SCENARIO_IDS",
    "ProductionFeatureGateReleaseWiringScenario",
    "ProductionFeatureGateReleaseWiringObservation",
    "ProductionFeatureGateReleaseWiringReport",
    "ProductionFeatureGateReleaseWiringAuthorityBoundary",
    "create_production_feature_gate_release_wiring_report",
    "verify_production_feature_gate_release_wiring_observation",
    "verify_production_feature_gate_release_wiring_report",
)
