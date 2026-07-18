"""V5.15.24.7.4.15.2 immutable response/state containment foundation.

This module evaluates only a fixed, isolated state fixture.  It never invokes
the production candidate, resolution, commit, delivery, or persistence paths.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
from typing import Any, Mapping

from brain.verifiable_isolated_failure_containment_record import (
    ADMISSION_SCENARIO, BRIDGE_CLASS, BRIDGE_SCENARIOS, SCENARIO_ORDER,
    IsolatedFailureContainmentBatch, IsolatedFailureContainmentRecord,
    verify_isolated_failure_containment_batch,
    verify_isolated_failure_containment_record,
)

VERSION = "5.15.24.7.4.15.2"
SCOPE = "IMMUTABLE_FAILURE_RESPONSE_AND_STATE_CONTAINMENT"
STATUS = "RESPONSE_AND_STATE_CONTAINMENT_BOUND_NOT_ACCEPTED"
SNAPSHOT_VERSION = "5.15.24.7.4.15.2-state.1"
STATE_SCHEMA = "brain.response_commit_boundary.commit_response_boundary:v5.3.8-compatible-fields"
FOUNDATION_BATCH_DIGEST = "3d647e06542b2ec6560b6542071347d0e365c3d26918b22f62f34ebfeeae60a3"
FOUNDATION_TOPOLOGY_DIGEST = "651b59298d25c38e4863ee69a88d8a4b691f98d12b536b1acda9fe2eff038bff"
CANDIDATE_BOUNDARY = "brain.production_response_candidate.ProductionResponseCandidate:5.15.24.2"
RESOLUTION_BOUNDARY = "brain.production_final_response_resolution.ProductionFinalResponseResolution:5.15.24.3"
COMMIT_BOUNDARY = "brain.production_turn_commit_receipt.ProductionTurnCommitReceipt:5.15.24.4"
STATE_MUTATION_OWNER = "brain.response_commit_boundary.commit_response_boundary"


@dataclass(frozen=True)
class FailureResponseStateContainmentAuthorityBoundary:
    production_application_permitted: bool = False
    response_candidate_permitted: bool = False
    final_resolution_permitted: bool = False
    response_commit_permitted: bool = False
    persistence_permitted: bool = False
    runtime_permitted: bool = False
    delivery_permitted: bool = False
    approval_evidence_permitted: bool = False
    deployment_attested: bool = False
    rollback_attested: bool = False


@dataclass(frozen=True)
class FailureResponseSuppressionDecision:
    scenario_id: str
    failure_record_digest: str
    failure_classification: str
    operation_stage: str
    outcome_status: str
    reason_codes: tuple[str, ...]
    success: bool
    suppress_response: bool
    response_candidate_count: int
    final_resolution_count: int
    response_commit_count: int
    downstream_artifact_digests: tuple[str, ...]
    authority_boundary: FailureResponseStateContainmentAuthorityBoundary
    decision_digest: str = ""


@dataclass(frozen=True)
class FailureStateSnapshot:
    snapshot_version: str
    snapshot_scope: str
    state_schema_identity: str
    conversation_id: str
    chat_history: tuple[tuple[tuple[str, Any], ...], ...]
    conversation_memory: tuple[tuple[str, Any], ...]
    application_conversation: tuple[tuple[str, Any], ...]
    turn_metadata: tuple[tuple[str, Any], ...]
    last_assistant_reply: str
    recent_assistant_replies: tuple[str, ...]
    response_commit_marker: str
    response_commit_count: int
    unrelated_sentinel_state: tuple[tuple[str, Any], ...]
    snapshot_digest: str = ""


@dataclass(frozen=True)
class FailureResponseStateContainmentObservation:
    scenario_id: str
    failure_record_digest: str
    failure_output_digest: str
    boundary_identity: str
    operation_stage: str
    suppression_decision: FailureResponseSuppressionDecision
    suppression_decision_digest: str
    response_candidate: None
    final_resolution: None
    response_commit: None
    runtime_result: None
    delivery_artifact: None
    before_snapshot: FailureStateSnapshot
    after_snapshot: FailureStateSnapshot
    before_snapshot_digest: str
    after_snapshot_digest: str
    state_unchanged: bool
    object_alias_isolated: bool
    response_candidate_attempts: int
    final_resolution_attempts: int
    response_commit_attempts: int
    mutation_count: int
    persistence_count: int
    production_invocation_count: int
    observation_topology_digest: str
    observation_digest: str = ""


@dataclass(frozen=True)
class FailureResponseStateContainmentBinding:
    version: str
    scope: str
    status: str
    source_batch: IsolatedFailureContainmentBatch
    source_batch_digest: str
    source_topology_digest: str
    scenario_order: tuple[str, ...]
    candidate_boundary_identity: str
    resolution_boundary_identity: str
    commit_boundary_identity: str
    state_mutation_owner: str
    observations: tuple[FailureResponseStateContainmentObservation, ...]
    isolated_bridge_denial_invocations: int
    isolated_admission_denial_invocations: int
    response_candidate_attempts: int
    final_resolution_attempts: int
    response_commit_attempts: int
    mutation_count: int
    persistence_count: int
    production_invocation_count: int
    state_containment_bound: bool
    state_containment_verified: bool
    response_suppression_bound: bool
    requirement_qualified: bool
    containment_accepted: bool
    production_failure_containment_accepted: bool
    approval_evidence_permitted: bool
    authority_boundary: FailureResponseStateContainmentAuthorityBoundary
    topology_digest: str
    binding_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int): return value
    if isinstance(value, (tuple, list)): return [_canonical(x) for x in value]
    if isinstance(value, Mapping): return [[str(k), _canonical(value[k])] for k in sorted(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return [[f.name, _canonical(getattr(value, f.name))] for f in fields(value)]
    raise ValueError("unsupported containment material")


def _digest(label: str, value: Any) -> str:
    raw = json.dumps(_canonical((VERSION, label, value)), ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _without(value: Any, *names: str) -> tuple[Any, ...]:
    return tuple(getattr(value, f.name) for f in fields(value) if f.name not in names)


def _authority_valid(value: Any) -> bool:
    return type(value) is FailureResponseStateContainmentAuthorityBoundary and all(
        type(getattr(value, f.name)) is bool and not getattr(value, f.name) for f in fields(value))


def _freeze(value: Any) -> Any:
    if type(value) is dict: return tuple((str(k), _freeze(value[k])) for k in sorted(value))
    if type(value) is list: return tuple(_freeze(x) for x in value)
    if type(value) is tuple: return tuple(_freeze(x) for x in value)
    if value is None or type(value) in (str, bool, int): return value
    raise ValueError("noncanonical fixture state")


def _fixture() -> dict[str, Any]:
    memory = {
        "last_assistant_reply": "canonical prior assistant reply",
        "last_user_message": "canonical denied turn",
        "recent_assistant_replies": ["canonical prior assistant reply"],
        "turn_count": 7,
    }
    history = (
        {"content": "canonical denied turn", "role": "user"},
        {"content": "canonical prior assistant reply", "role": "assistant"},
    )
    return {
        "application_state": {
            "conversation": {
                "chat_history": [dict(x) for x in history],
                "conversation_id": "containment-conversation-001",
                "conversation_memory": deepcopy(memory),
            },
            "conversation_memory": deepcopy(memory),
            "unrelated": {"preserve": "sentinel", "revision": 11},
        },
        "canonical_turn_state": {
            "chat_history": [dict(x) for x in history],
            "conversation_id": "containment-conversation-001",
            "conversation_state": {"conversation_memory": deepcopy(memory)},
            "last_user_message": "canonical denied turn",
            "response_commit_count": 4,
            "response_commit_marker": "prior-commit-marker",
        },
        "turn_metadata": {"intent": "cost_analysis", "turn_id": "denied-turn-008"},
    }


def _snapshot(state: dict[str, Any]) -> FailureStateSnapshot:
    session, app = state["canonical_turn_state"], state["application_state"]
    memory = session["conversation_state"]["conversation_memory"]
    draft = FailureStateSnapshot(SNAPSHOT_VERSION, SCOPE, STATE_SCHEMA,
        session["conversation_id"], _freeze(session["chat_history"]), _freeze(memory),
        _freeze(app["conversation"]), _freeze(state["turn_metadata"]),
        memory["last_assistant_reply"], tuple(memory["recent_assistant_replies"]),
        session["response_commit_marker"], session["response_commit_count"],
        _freeze(app["unrelated"]))
    return replace(draft, snapshot_digest=_digest("STATE_SNAPSHOT", _without(draft, "snapshot_digest")))


def _canonical_record(record: Any) -> bool:
    if not verify_isolated_failure_containment_record(record): return False
    if record.outcome.classification != BRIDGE_CLASS or record.outcome.success: return False
    if record.scenario_id in BRIDGE_SCENARIOS:
        return record.boundary_identity == "ISOLATED_RUNTIME_BRIDGE" and record.outcome.status == "RUNTIME_HANDOFF_DENIED"
    return record.scenario_id == ADMISSION_SCENARIO and record.boundary_identity == "ISOLATED_CONTROLLED_RUNTIME_ADMISSION" and record.outcome.status == "ADMISSION_DENIED"


def _decision(record: IsolatedFailureContainmentRecord) -> FailureResponseSuppressionDecision:
    if not _canonical_record(record): raise ValueError("exact canonical failure record required")
    out = record.outcome
    if out.downstream_invocation_count != 0 or out.downstream_artifact_digests != ():
        raise ValueError("canonical downstream suppression required")
    draft = FailureResponseSuppressionDecision(record.scenario_id, record.record_digest,
        out.classification, record.boundary_identity, out.status, out.reason_codes, out.success,
        True, 0, 0, 0, out.downstream_artifact_digests,
        FailureResponseStateContainmentAuthorityBoundary())
    return replace(draft, decision_digest=_digest("SUPPRESSION_DECISION", _without(draft, "decision_digest")))


def verify_failure_response_suppression_decision(value: Any, record: Any) -> bool:
    try:
        return type(value) is FailureResponseSuppressionDecision and value == _decision(record)
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def verify_failure_state_snapshot(value: Any) -> bool:
    try:
        return (type(value) is FailureStateSnapshot and value == _snapshot(_fixture())
            and value.snapshot_digest == _digest("STATE_SNAPSHOT", _without(value, "snapshot_digest")))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def _expected_observation(record: IsolatedFailureContainmentRecord) -> FailureResponseStateContainmentObservation:
    decision = _decision(record)
    before, after = _snapshot(_fixture()), _snapshot(_fixture())
    topology = _digest("OBSERVATION_TOPOLOGY", (record.record_digest,
        decision.decision_digest, before.snapshot_digest, after.snapshot_digest,
        CANDIDATE_BOUNDARY, RESOLUTION_BOUNDARY, COMMIT_BOUNDARY))
    draft = FailureResponseStateContainmentObservation(record.scenario_id,
        record.record_digest, record.outcome.output_digest, record.boundary_identity,
        record.input_binding.operation_identity, decision, decision.decision_digest,
        None, None, None, None, None, before, after, before.snapshot_digest,
        after.snapshot_digest, True, True, 0, 0, 0, 0, 0, 0, topology)
    return replace(draft, observation_digest=_digest("OBSERVATION", _without(draft, "observation_digest")))


def _evaluate(record: IsolatedFailureContainmentRecord) -> FailureResponseStateContainmentObservation:
    working = deepcopy(_fixture())
    before = _snapshot(deepcopy(working))
    decision = _decision(record)
    candidate_attempts = resolution_attempts = commit_attempts = 0
    if not decision.suppress_response:  # unreachable for exact canonical failures
        candidate_attempts += 1
    after = _snapshot(deepcopy(working))
    expected = _expected_observation(record)
    return replace(expected, before_snapshot=before, after_snapshot=after,
        before_snapshot_digest=before.snapshot_digest,
        after_snapshot_digest=after.snapshot_digest,
        state_unchanged=before == after,
        object_alias_isolated=before is not after,
        response_candidate_attempts=candidate_attempts,
        final_resolution_attempts=resolution_attempts,
        response_commit_attempts=commit_attempts,
        observation_digest="")


def verify_failure_response_state_containment_observation(value: Any, record: Any) -> bool:
    try:
        if type(value) is not FailureResponseStateContainmentObservation: return False
        if value.before_snapshot is value.after_snapshot: return False
        if not verify_failure_state_snapshot(value.before_snapshot) or not verify_failure_state_snapshot(value.after_snapshot): return False
        expected = _expected_observation(record)
        return value == expected and value.observation_digest == _digest("OBSERVATION", _without(value, "observation_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


def create_failure_response_state_containment_binding(source_batch: Any):
    if (type(source_batch) is not IsolatedFailureContainmentBatch
            or not verify_isolated_failure_containment_batch(source_batch)
            or source_batch.batch_digest != FOUNDATION_BATCH_DIGEST
            or source_batch.topology_digest != FOUNDATION_TOPOLOGY_DIGEST): return None
    observations = []
    for record in source_batch.records:
        observation = _evaluate(record)
        observation = replace(observation, observation_digest=_digest(
            "OBSERVATION", _without(observation, "observation_digest")))
        observations.append(observation)
    observations = tuple(observations)
    topology = _digest("BINDING_TOPOLOGY", tuple(x.observation_digest for x in observations))
    draft = FailureResponseStateContainmentBinding(VERSION, SCOPE, STATUS, source_batch,
        source_batch.batch_digest, source_batch.topology_digest, SCENARIO_ORDER,
        CANDIDATE_BOUNDARY, RESOLUTION_BOUNDARY, COMMIT_BOUNDARY, STATE_MUTATION_OWNER,
        observations, 2, 1, 0, 0, 0, 0, 0, 0, True, True, True, False, False,
        False, False, FailureResponseStateContainmentAuthorityBoundary(), topology)
    return replace(draft, binding_digest=_digest("BINDING", _without(draft, "binding_digest")))


def verify_failure_response_state_containment_binding(value: Any) -> bool:
    """Pure verification; neither failure operations nor harness evaluation rerun."""
    try:
        if type(value) is not FailureResponseStateContainmentBinding: return False
        batch = value.source_batch
        if (not verify_isolated_failure_containment_batch(batch)
                or batch.batch_digest != FOUNDATION_BATCH_DIGEST
                or batch.topology_digest != FOUNDATION_TOPOLOGY_DIGEST): return False
        if (value.version, value.scope, value.status, value.scenario_order) != (VERSION, SCOPE, STATUS, SCENARIO_ORDER): return False
        if (value.source_batch_digest, value.source_topology_digest) != (FOUNDATION_BATCH_DIGEST, FOUNDATION_TOPOLOGY_DIGEST): return False
        if (value.candidate_boundary_identity, value.resolution_boundary_identity,
                value.commit_boundary_identity, value.state_mutation_owner) != (
                CANDIDATE_BOUNDARY, RESOLUTION_BOUNDARY, COMMIT_BOUNDARY, STATE_MUTATION_OWNER): return False
        if tuple(x.scenario_id for x in value.observations) != SCENARIO_ORDER or len({x.scenario_id for x in value.observations}) != 3: return False
        if not all(verify_failure_response_state_containment_observation(o, r)
                   for o, r in zip(value.observations, batch.records)): return False
        if (value.isolated_bridge_denial_invocations, value.isolated_admission_denial_invocations,
                value.response_candidate_attempts, value.final_resolution_attempts,
                value.response_commit_attempts, value.mutation_count, value.persistence_count,
                value.production_invocation_count) != (2, 1, 0, 0, 0, 0, 0, 0): return False
        if (value.state_containment_bound, value.state_containment_verified,
                value.response_suppression_bound) != (True, True, True): return False
        if any((value.requirement_qualified, value.containment_accepted,
                value.production_failure_containment_accepted, value.approval_evidence_permitted)): return False
        if not _authority_valid(value.authority_boundary): return False
        topology = _digest("BINDING_TOPOLOGY", tuple(x.observation_digest for x in value.observations))
        return value.topology_digest == topology and value.binding_digest == _digest("BINDING", _without(value, "binding_digest"))
    except (AttributeError, TypeError, ValueError, UnicodeEncodeError): return False


__all__ = ("FailureResponseStateContainmentAuthorityBoundary",
    "FailureResponseSuppressionDecision", "FailureStateSnapshot",
    "FailureResponseStateContainmentObservation", "FailureResponseStateContainmentBinding",
    "create_failure_response_state_containment_binding",
    "verify_failure_response_suppression_decision", "verify_failure_state_snapshot",
    "verify_failure_response_state_containment_observation",
    "verify_failure_response_state_containment_binding")
