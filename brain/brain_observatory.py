from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from types import MappingProxyType
from typing import Any


BRAIN_OBSERVATORY_VERSION = "5.8.1"
BRAIN_OBSERVATORY_SOURCE = "brain_observatory"
BRAIN_OBSERVATORY_RUNTIME_MODE = "developer_diagnostics_only"

COGNITIVE_LAYERS = (
    "Reality",
    "Perception",
    "Business Situation",
    "Evidence",
    "Truth Status",
    "Evidence Gap",
    "Perspective",
    "Knowledge",
    "Knowledge-Skill Bridge",
    "Business Judgment",
    "Decision",
)

CONSTITUTION_FLAGS = (
    "routing_changed",
    "planner_changed",
    "workflow_changed",
    "responses_changed",
    "execution_changed",
    "commit_changed",
)


def _plain(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, MappingProxyType):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, set):
        return [_plain(item) for item in sorted(value, key=str)]
    return deepcopy(value)


def _as_dict(value: Any) -> dict:
    plain = _plain(value)
    return plain if isinstance(plain, dict) else {}


def _as_list(value: Any) -> list:
    plain = _plain(value)
    if isinstance(plain, list):
        return plain
    if plain in (None, "", {}, ()):
        return []
    return [plain]


def _first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


def _bool_from_any(value: Any) -> bool:
    return bool(value is True or str(value).strip().lower() == "true")


def _collect_flag_values(value: Any, flag: str) -> list[bool]:
    plain = _plain(value)
    found: list[bool] = []
    if isinstance(plain, dict):
        if flag in plain:
            found.append(_bool_from_any(plain.get(flag)))
        if flag == "commit_changed" and "commit_boundary_changed" in plain:
            found.append(_bool_from_any(plain.get("commit_boundary_changed")))
        for item in plain.values():
            found.extend(_collect_flag_values(item, flag))
    elif isinstance(plain, list):
        for item in plain:
            found.extend(_collect_flag_values(item, flag))
    return found


def _status(*, exists: bool, placeholder: bool = False, violation: bool = False) -> str:
    if violation:
        return "violation"
    if placeholder:
        return "placeholder"
    return "observed" if exists else "not_available"


def _layer(
    *,
    name: str,
    runtime_state: Any = None,
    diagnostics: Any = None,
    confidence: Any = None,
    source: str = "",
    status: str = "",
) -> dict:
    runtime = _plain(runtime_state)
    diagnostic_payload = _plain(diagnostics) or {}
    exists = runtime not in (None, "", [], {}) or diagnostic_payload not in (None, "", [], {})
    return {
        "layer": name,
        "runtime_state": runtime if runtime is not None else {},
        "diagnostics": diagnostic_payload,
        "confidence": confidence,
        "source": source or "unknown",
        "status": status or _status(exists=exists),
    }


def _reality_layer(route: dict) -> dict:
    understanding = _as_dict(route.get("conversation_understanding"))
    user_message = _first_present(route.get("user_message"), understanding.get("raw_text"), (route.get("planner_output") or {}).get("goal"), default="")
    return _layer(
        name="Reality",
        runtime_state={
            "user_message": user_message,
            "uploaded_documents": _as_list(route.get("uploaded_documents")),
            "uploaded_images": _as_list(route.get("uploaded_images")),
            "active_workspace": route.get("active_workspace") or "",
        },
        diagnostics={
            "reality_observed": bool(user_message),
            "diagnostic_only": True,
            "runtime_only": True,
        },
        confidence=1.0 if user_message else 0.0,
        source="runtime_input",
    )


def _perception_layer(business_situation: dict) -> dict:
    diagnostics = _as_dict(_as_dict(business_situation.get("diagnostics")).get("perception"))
    return _layer(
        name="Perception",
        runtime_state={
            "percept_id": diagnostics.get("percept_id"),
            "signal_set_id": diagnostics.get("signal_set_id"),
            "signal_count": diagnostics.get("canonical_signal_count"),
            "signal_types": diagnostics.get("canonical_signal_types") or [],
            "signal_sources": diagnostics.get("canonical_signal_sources") or [],
        },
        diagnostics=diagnostics,
        confidence=None,
        source=diagnostics.get("perception_situation_diagnostics_source") or "perception",
    )


def _business_situation_layer(business_situation: dict) -> dict:
    diagnostics = _as_dict(business_situation.get("diagnostics"))
    return _layer(
        name="Business Situation",
        runtime_state={
            "current_business": business_situation.get("current_business"),
            "current_goal": business_situation.get("current_goal"),
            "current_problem": business_situation.get("current_problem"),
            "current_operation": business_situation.get("current_operation"),
            "current_focus": business_situation.get("current_focus"),
            "conversation_purpose": business_situation.get("conversation_purpose"),
            "business_topic": business_situation.get("business_topic"),
        },
        diagnostics=diagnostics,
        confidence=business_situation.get("situation_confidence"),
        source=business_situation.get("situation_source") or diagnostics.get("business_situation_source"),
    )


def _evidence_layer(business_situation: dict) -> dict:
    evidence = _as_dict(_as_dict(business_situation.get("diagnostics")).get("evidence"))
    diagnostics = _as_dict(evidence.get("evidence_diagnostics"))
    return _layer(
        name="Evidence",
        runtime_state={
            "evidence_available": evidence.get("evidence_available"),
            "evidence_items": evidence.get("evidence_items") or [],
            "missing_evidence": evidence.get("missing_evidence") or [],
            "conflicting_evidence": evidence.get("conflicting_evidence") or [],
        },
        diagnostics=diagnostics,
        confidence=evidence.get("evidence_confidence"),
        source=evidence.get("evidence_source") or diagnostics.get("evidence_runtime_source"),
    )


def _truth_status_layer(business_situation: dict) -> dict:
    truth = _as_dict(_as_dict(business_situation.get("diagnostics")).get("truth"))
    diagnostics = _as_dict(truth.get("diagnostics"))
    return _layer(
        name="Truth Status",
        runtime_state={
            "truth_items": truth.get("truth_items") or [],
            "truth_summary": truth.get("truth_summary") or {},
            "runtime_truth": truth.get("runtime_truth") or [],
            "historical_truth": truth.get("historical_truth") or [],
            "conflicting_truths": truth.get("conflicting_truths") or [],
            "unknown_truths": truth.get("unknown_truths") or [],
        },
        diagnostics=diagnostics,
        confidence=None,
        source=truth.get("source") or diagnostics.get("truth_runtime_source"),
    )


def _evidence_gap_layer(business_situation: dict) -> dict:
    evidence_gap = _as_dict(_as_dict(business_situation.get("diagnostics")).get("evidence_gap"))
    diagnostics = _as_dict(evidence_gap.get("diagnostics"))
    gap_items = evidence_gap.get("gap_items") or []
    priority_queue = evidence_gap.get("priority_queue") or []
    next_question = evidence_gap.get("next_best_question") or {}
    duplicate_guard = evidence_gap.get("duplicate_question_guard") or {}
    completeness = evidence_gap.get("completeness_status") or {}
    return _layer(
        name="Evidence Gap",
        runtime_state={
            "gap_items": gap_items,
            "gap_type": [item.get("gap_type") for item in _as_list(gap_items) if isinstance(item, dict)],
            "missing_evidence": evidence_gap.get("missing_evidence") or [],
            "priority_queue": priority_queue,
            "question_intent": [item.get("question_intent") for item in _as_list(gap_items) if isinstance(item, dict)],
            "next_best_question": next_question,
            "duplicate_question_guard": duplicate_guard,
            "duplicate_guard_reason": duplicate_guard.get("duplicate_guard_reason") or diagnostics.get("duplicate_guard_reason"),
            "duplicate_guard_hits": duplicate_guard.get("duplicate_guard_hits") or diagnostics.get("duplicate_guard_hits") or {},
            "suppressed_questions": duplicate_guard.get("suppressed_questions") or diagnostics.get("suppressed_questions") or [],
            "completeness_status": completeness,
            "completeness_reason": completeness.get("completeness_reason") or diagnostics.get("completeness_reason"),
        },
        diagnostics=diagnostics,
        confidence=None,
        source=evidence_gap.get("source") or diagnostics.get("evidence_gap_runtime_source"),
    )


def _perspective_layer(business_situation: dict) -> dict:
    perspective = _as_dict(_as_dict(business_situation.get("diagnostics")).get("perspective"))
    diagnostics = _as_dict(perspective.get("diagnostics"))
    invariants = perspective.get("constitutional_invariants") or diagnostics.get("constitutional_invariants") or {}
    return _layer(
        name="Perspective",
        runtime_state={
            "selected_frame": perspective.get("selected_frame"),
            "candidate_frames": perspective.get("candidate_frames") or [],
            "frame_confidence": perspective.get("frame_confidence"),
            "frame_selection_reason": perspective.get("frame_selection_reason"),
            "frame_status": perspective.get("frame_status"),
            "frame_evidence": perspective.get("frame_evidence") or diagnostics.get("frame_evidence") or {},
            "frame_contradictions": perspective.get("frame_contradictions") or diagnostics.get("frame_contradictions") or {},
            "frame_source_signals": perspective.get("frame_source_signals") or diagnostics.get("frame_source_signals") or [],
            "classification_performed": perspective.get("classification_performed") or diagnostics.get("classification_performed"),
            "classification_method": perspective.get("classification_method") or diagnostics.get("classification_method"),
            "frame_registry_version": perspective.get("frame_registry_version") or diagnostics.get("frame_registry_version"),
            "registered_frame_count": diagnostics.get("registered_frame_count"),
            "registered_frame_ids": diagnostics.get("registered_frame_ids") or [],
            "registry_version": diagnostics.get("registry_version"),
            "source_layers": perspective.get("source_layers") or diagnostics.get("source_layers") or {},
            "constitutional_invariants": invariants,
        },
        diagnostics=diagnostics,
        confidence=perspective.get("frame_confidence"),
        source=perspective.get("source") or diagnostics.get("perspective_runtime_source"),
    )


def _knowledge_layer(business_situation: dict) -> dict:
    knowledge = _as_dict(_as_dict(business_situation.get("diagnostics")).get("knowledge"))
    diagnostics = _as_dict(knowledge.get("diagnostics"))
    registry_validation = _as_dict(diagnostics.get("registry_validation"))
    workflow_like_operation = str(business_situation.get("current_operation") or "").upper()
    workflow_owned_context = bool("PROFIT_CALCULATION" in workflow_like_operation or "COST_CALCULATION" in workflow_like_operation)
    primary_available = bool(knowledge.get("primary_knowledge")) and not workflow_owned_context
    return _layer(
        name="Knowledge",
        runtime_state={
            "knowledge_available": knowledge.get("knowledge_available"),
            "primary_knowledge": knowledge.get("primary_knowledge") or [],
            "secondary_knowledge": knowledge.get("secondary_knowledge") or [],
            "deferred_knowledge": knowledge.get("deferred_knowledge") or [],
            "selection_support": knowledge.get("selection_support_strength"),
            "selection_reason": knowledge.get("selection_reason"),
            "relevant_concepts": knowledge.get("relevant_concepts") or [],
            "relevant_metrics": knowledge.get("relevant_metrics") or [],
            "applicable_relationship_rules": knowledge.get("applicable_relationship_rules") or [],
            "available_metrics": knowledge.get("available_metrics") or {},
            "incomplete_metrics": knowledge.get("incomplete_metrics") or {},
            "missing_metrics": knowledge.get("missing_metrics") or [],
            "all_knowledge_gaps": knowledge.get("knowledge_gaps") or [],
            "merged_gaps": knowledge.get("merged_gaps") or [],
            "suppressed_gaps": knowledge.get("suppressed_gaps") or [],
            "next_knowledge_gap": knowledge.get("next_knowledge_gap") or {},
            "blocking_relationship": (_as_dict(knowledge.get("next_knowledge_gap")).get("blocking_relationship_rules") or []),
            "clarification_handoff": knowledge.get("clarification_handoff") or {},
            "expected_answer_schema": _as_dict(knowledge.get("clarification_handoff")).get("expected_answer_schema") or {},
            "safe_wording_constraints": _as_dict(knowledge.get("clarification_handoff")).get("safe_wording_constraints") or [],
            "duplicate_guard": _as_dict(knowledge.get("clarification_handoff")).get("duplicate_guard") or {},
            "workflow_coordination": _as_dict(knowledge.get("clarification_handoff")).get("workflow_coordination") or {},
            "registry_version": knowledge.get("registry_version") or registry_validation.get("registry_version"),
            "constitutional_invariants": knowledge.get("constitutional_invariants") or diagnostics.get("constitutional_invariants") or {},
            "registered_knowledge_count": registry_validation.get("registered_knowledge_count"),
            "registered_knowledge_ids": registry_validation.get("registered_knowledge_ids") or [],
            "business_domains": registry_validation.get("business_domains") or [],
        },
        diagnostics=diagnostics,
        confidence=knowledge.get("selection_support_strength"),
        source=knowledge.get("source") or diagnostics.get("knowledge_runtime_source") or "knowledge_runtime",
        status="observed" if primary_available else "placeholder",
    )


def _knowledge_skill_bridge_layer(business_situation: dict) -> dict:
    bridge = _as_dict(_as_dict(business_situation.get("diagnostics")).get("knowledge_skill_bridge"))
    primary = _as_dict(bridge.get("primary_skill_candidate"))
    readiness = _as_dict(primary.get("evidence_readiness_result"))
    applicability = _as_dict(primary.get("applicability_result"))
    workflow = _as_dict(bridge.get("workflow_coordination"))
    planner = _as_dict(bridge.get("planner_handoff"))
    judgment = _as_dict(bridge.get("judgment_handoff"))
    next_gap = _as_dict(bridge.get("next_shared_gap"))
    drift = _as_dict(bridge.get("contract_drift"))
    provenance = _as_dict(bridge.get("contract_provenance"))
    migration = _as_dict(bridge.get("canonical_skill_migration"))
    outcome = _as_dict(bridge.get("conversation_outcome_hardening"))
    return _layer(
        name="Knowledge-Skill Bridge",
        runtime_state={
            "selected_knowledge": bridge.get("selected_knowledge_ids") or [],
            "candidate_skills": [item.get("skill_id") for item in _as_list(bridge.get("candidate_skills")) if isinstance(item, dict)],
            "primary_skill": primary.get("skill_id"),
            "secondary_skills": [item.get("skill_id") for item in _as_list(bridge.get("secondary_skill_candidates")) if isinstance(item, dict)],
            "deferred_skills": [item.get("skill_id") for item in _as_list(bridge.get("deferred_skill_candidates")) if isinstance(item, dict)],
            "excluded_skill_count": len(_as_list(bridge.get("excluded_skill_candidates"))),
            "reference_validation": primary.get("reference_validation_status"),
            "validation_issues": primary.get("validation_issues") or [],
            "authority_scope": primary.get("authority_scope") or {},
            "applicability": applicability,
            "evidence_readiness": readiness.get("status"),
            "required_evidence": readiness.get("required_evidence") or [],
            "satisfied_evidence": readiness.get("available_required_evidence") or [],
            "incomplete_evidence": readiness.get("incomplete_required_evidence") or [],
            "missing_evidence": readiness.get("missing_required_evidence") or [],
            "conflicting_evidence": readiness.get("conflicting_required_evidence") or [],
            "stale_evidence": readiness.get("stale_required_evidence") or [],
            "workflow_owned_evidence": readiness.get("workflow_owned_evidence") or [],
            "shared_gaps": bridge.get("merged_evidence_gaps") or [],
            "next_shared_gap": next_gap,
            "question_owner": next_gap.get("question_owner"),
            "legacy_classification": "",
            "legacy_fallback": bridge.get("bridge_status") == "LEGACY_FALLBACK_SELECTED",
            "replacement_mapping": {},
            "redundancy_group": primary.get("redundancy_group"),
            "dependency_stage": primary.get("stage"),
            "selection_reason": primary.get("selection_reason"),
            "chosen_over": [item.get("skill_id") for item in _as_list(bridge.get("secondary_skill_candidates")) if isinstance(item, dict)],
            "workflow_coordination": workflow,
            "response_owner": "CLARIFICATION_AUTHORITY" if bridge.get("clarification_handoff") else "SYSTEM",
            "judgment_eligibility": judgment.get("ready_for_judgment"),
            "planner_eligibility": planner,
            "authority_trace": bridge.get("authority_trace") or {},
            "stop_condition": bridge.get("bridge_status"),
            "registry_versions": bridge.get("registry_versions") or {},
            "Contract Provenance": provenance,
            "Reference Snapshot": provenance.get("reference_snapshots") or [],
            "Drift Detected": drift.get("contract_drift_detected"),
            "Drift Types": drift.get("contract_drift_types") or [],
            "Affected Contracts": drift.get("changed_contracts") or [],
            "Declared Review Status": primary.get("declared_review_status"),
            "Effective Review Status": primary.get("effective_review_status"),
            "Reference Freshness": primary.get("reference_freshness"),
            "Migration Required": bool(_as_dict(primary.get("contract_drift_result")).get("migration_required")),
            "Runtime Restriction": _as_dict(primary.get("contract_drift_result")).get("blocking_reason"),
            "Registry Integrity": drift.get("registry_integrity") or {},
            "Change Manifest": _as_dict(_as_dict(primary.get("contract_drift_result")).get("change_manifest")),
            "Migration Batch": migration.get("migration_batch_id"),
            "Legacy Skill": [item.get("legacy_skill_id") for item in _as_list(migration.get("assessments")) if isinstance(item, dict)],
            "Strategy": {item.get("legacy_skill_id"): item.get("migration_strategy") for item in _as_list(migration.get("assessments")) if isinstance(item, dict)},
            "Canonical Targets": {item.get("legacy_skill_id"): item.get("canonical_target_ids") for item in _as_list(migration.get("assessments")) if isinstance(item, dict)},
            "Rollout Mode": migration.get("rollout_modes") or {},
            "Replacement Status": [item.get("replacement_status") for item in _as_list(migration.get("records")) if isinstance(item, dict)],
            "Active Topic": outcome.get("active_topic_id"),
            "Previous Topic": _as_dict(outcome.get("topic_transition")).get("previous_topic_id"),
            "Transition Type": outcome.get("topic_transition_type"),
            "Continuity Strength": outcome.get("continuity_strength"),
            "Freshness Status": _as_dict(outcome.get("freshness")).get("freshness_status"),
            "Follow-Up Resolution": outcome.get("follow_up_resolution") or {},
            "Answered Gaps": _as_dict(outcome.get("clarification_recovery")).get("resolved_gap_ids") or [],
            "Unresolved Gaps": _as_dict(outcome.get("clarification_recovery")).get("unresolved_gap_ids") or [],
            "Clarification Attempts": outcome.get("clarification_retry_count"),
            "Skill Ambiguity": outcome.get("skill_ambiguity") or {},
            "Competing Skills": _as_dict(outcome.get("skill_ambiguity")).get("competing_skill_ids") or [],
            "Conflict Sets": outcome.get("evidence_conflict_sets") or [],
            "Workflow Interruption": outcome.get("workflow_interruption") or {},
            "Conversation Stop Reason": _as_dict(outcome.get("conversation_routing_outcome")).get("stop_reason"),
        },
        diagnostics={
            "bridge_consulted": bridge.get("bridge_consulted"),
            "bridge_status": bridge.get("bridge_status"),
            "contract_provenance_checked": bool(provenance.get("contract_provenance_checked")),
            "contract_drift_checked": bool(drift.get("contract_drift_checked")),
            "contract_drift_detected": bool(drift.get("contract_drift_detected")),
            "contract_drift_types": drift.get("contract_drift_types") or [],
            "contract_drift_severity": drift.get("contract_drift_severity"),
            "skill_reference_snapshot_available": bool(provenance.get("reference_snapshots")),
            "skill_revalidation_required": bool(_as_dict(primary.get("contract_drift_result")).get("revalidation_required")),
            "skill_rereview_required": bool(_as_dict(primary.get("contract_drift_result")).get("rereview_required")),
            "skill_migration_required": bool(_as_dict(primary.get("contract_drift_result")).get("migration_required")),
            "skill_authority_restricted_by_drift": bool(_as_dict(primary.get("contract_drift_result")).get("authority_restricted")),
            "skill_primary_blocked_by_drift": _as_dict(primary.get("contract_drift_result")).get("severity") in {"BREAKING", "CONSTITUTIONAL"},
            "effective_review_status": primary.get("effective_review_status"),
            "registry_integrity_checked": bool(_as_dict(drift.get("registry_integrity")).get("registry_integrity_checked")),
            "registry_integrity_passed": bool(_as_dict(drift.get("registry_integrity")).get("registry_integrity_passed")),
            "silent_rename_prevented": bool(drift.get("silent_rename_prevented")),
            "silent_contract_upgrade_prevented": bool(drift.get("silent_contract_upgrade_prevented")),
            "canonical_skill_migration_consulted": bool(migration.get("canonical_skill_migration_consulted")),
            "migration_batch_id": migration.get("migration_batch_id"),
            "legacy_deprecation_blocked": bool(migration.get("legacy_deprecation_blocked")),
            "conversation_hardening_consulted": bool(outcome.get("conversation_hardening_consulted")),
            "topic_transition_detected": bool(outcome.get("topic_transition_detected")),
            "topic_transition_type": outcome.get("topic_transition_type"),
            "stale_context_detected": bool(outcome.get("stale_context_detected")),
            "follow_up_resolved": bool(outcome.get("follow_up_resolved")),
            "skill_ambiguity_detected": bool(outcome.get("skill_ambiguity_detected")),
            "workflow_interruption_detected": bool(outcome.get("workflow_interruption_detected")),
            "constitutional_invariants": bridge.get("constitutional_invariants") or {},
        },
        confidence=primary.get("support_strength"),
        source="knowledge_skill_bridge",
        status="observed" if bridge else "not_available",
    )


def _placeholder_layer(name: str) -> dict:
    return _layer(
        name=name,
        runtime_state={},
        diagnostics={
            "placeholder": True,
            "diagnostic_only": True,
            "runtime_only": True,
            "not_implemented_in_version": BRAIN_OBSERVATORY_VERSION,
        },
        confidence=None,
        source="placeholder",
        status="placeholder",
    )


def _constitution_monitor(payload: dict) -> dict:
    flags = {}
    violations = []
    for flag in CONSTITUTION_FLAGS:
        values = _collect_flag_values(payload, flag)
        changed = any(values)
        flags[flag] = changed
        if changed:
            violations.append(flag)
    return {
        "flags": flags,
        "violations": violations,
        "violation_count": len(violations),
        "status": "violation" if violations else "clear",
        "highlight_violations": bool(violations),
    }


def _diagnostics_timeline(layers: list[dict]) -> list[dict]:
    timeline = []
    for index, layer in enumerate(layers, start=1):
        diagnostics = _as_dict(layer.get("diagnostics"))
        timeline.append(
            {
                "order": index,
                "layer": layer.get("layer"),
                "status": layer.get("status"),
                "source": layer.get("source"),
                "confidence": layer.get("confidence"),
                "diagnostics": diagnostics,
            }
        )
    return timeline


def _cognitive_authority_group(route: dict, business_situation: dict) -> dict:
    diagnostics = _as_dict(business_situation.get("diagnostics"))
    audit = _as_dict(diagnostics.get("cognitive_authority_audit")) or _as_dict(route.get("cognitive_authority_audit"))
    if not audit:
        return {
            "status": "not_available",
            "diagnostic_only": True,
            "runtime_only": True,
        }
    return {
        "status": "observed",
        "winning_authority": audit.get("winning_authority"),
        "winning_stage": audit.get("winning_stage"),
        "selected_intent": audit.get("selected_intent"),
        "selected_workflow": audit.get("selected_workflow"),
        "selected_response_mode": audit.get("selected_response_mode"),
        "workflow_candidate": audit.get("workflow_candidate"),
        "workflow_admission_gate_consulted": audit.get("workflow_admission_gate_consulted"),
        "workflow_admission_gate_decision": audit.get("workflow_admission_gate_decision"),
        "workflow_admission_gate_reason": audit.get("workflow_admission_gate_reason"),
        "workflow_admission_gate_authoritative": audit.get("workflow_admission_gate_authoritative"),
        "workflow_candidate_rejected": audit.get("workflow_candidate_rejected"),
        "workflow_candidate_deferred": audit.get("workflow_candidate_deferred"),
        "workflow_admitted": audit.get("workflow_admitted"),
        "workflow_admission_reason": audit.get("workflow_admission_reason"),
        "workflow_admission_gate": (_as_dict(audit.get("diagnostic_summary")).get("workflow_admission_gate") or {}),
        "language_normalization_consulted": audit.get("language_normalization_consulted"),
        "language_normalization_applied": audit.get("language_normalization_applied"),
        "normalized_user_message": audit.get("normalized_user_message"),
        "clarification_authority_consulted": audit.get("clarification_authority_consulted"),
        "clarification_authority_used": audit.get("clarification_authority_used"),
        "clarification_decision": audit.get("clarification_decision"),
        "clarification_reason": audit.get("clarification_reason"),
        "clarification_requested_fields": audit.get("clarification_requested_fields") or [],
        "perspective_classification_performed": audit.get("perspective_classification_performed"),
        "perspective_selected_frame": audit.get("perspective_selected_frame"),
        "perspective_candidate_frames": audit.get("perspective_candidate_frames") or [],
        "perspective_frame_confidence": audit.get("perspective_frame_confidence"),
        "perspective_frame_status": audit.get("perspective_frame_status"),
        "perspective_consulted_by_clarification": audit.get("perspective_consulted_by_clarification"),
        "perspective_authoritative_for_framing": audit.get("perspective_authoritative_for_framing"),
        "perspective_authoritative_for_routing": audit.get("perspective_authoritative_for_routing"),
        "perspective_authoritative_for_workflow": audit.get("perspective_authoritative_for_workflow"),
        "perspective_authoritative_for_response": audit.get("perspective_authoritative_for_response"),
        "knowledge_runtime_consulted": audit.get("knowledge_runtime_consulted"),
        "knowledge_available": audit.get("knowledge_available"),
        "knowledge_primary_ids": audit.get("knowledge_primary_ids") or [],
        "knowledge_secondary_ids": audit.get("knowledge_secondary_ids") or [],
        "knowledge_next_gap": audit.get("knowledge_next_gap") or {},
        "knowledge_used_by_clarification": audit.get("knowledge_used_by_clarification"),
        "knowledge_authoritative_for_relevance": audit.get("knowledge_authoritative_for_relevance"),
        "knowledge_authoritative_for_judgment": audit.get("knowledge_authoritative_for_judgment"),
        "knowledge_authoritative_for_decision": audit.get("knowledge_authoritative_for_decision"),
        "clarification_handoff_created": audit.get("clarification_handoff_created"),
        "clarification_handoff_type": audit.get("clarification_handoff_type"),
        "clarification_question_intent": audit.get("clarification_question_intent"),
        "generic_fallback_avoided": audit.get("generic_fallback_avoided"),
        "cognitive_runtime_consulted": audit.get("cognitive_runtime_consulted"),
        "cognitive_runtime_authoritative": audit.get("cognitive_runtime_authoritative"),
        "fallback_selected": audit.get("fallback_selected"),
        "response_source": audit.get("response_source"),
        "commit_source": audit.get("commit_source"),
        "authority_conflicts": audit.get("authority_conflicts") or [],
        "authority_chain": audit.get("authority_chain") or [],
        "diagnostic_only": True,
        "runtime_only": True,
    }


def build_brain_observatory(task_route: dict | None) -> dict:
    """Build a developer-only observability projection of cognitive runtime state.

    The observatory is a passive diagnostics surface. It does not route, plan,
    execute workflows, build responses, determine truth, produce judgment, or
    commit memory.
    """

    route = _as_dict(task_route)
    business_situation = _as_dict(
        route.get("business_situation")
        or _as_dict(route.get("planner_output")).get("business_situation")
    )
    layers = [
        _reality_layer(route),
        _perception_layer(business_situation),
        _business_situation_layer(business_situation),
        _evidence_layer(business_situation),
        _truth_status_layer(business_situation),
        _evidence_gap_layer(business_situation),
        _perspective_layer(business_situation),
        _knowledge_layer(business_situation),
        _knowledge_skill_bridge_layer(business_situation),
        _placeholder_layer("Business Judgment"),
        _placeholder_layer("Decision"),
    ]
    constitution = _constitution_monitor({"route": route, "layers": layers})
    cognitive_authority = _cognitive_authority_group(route, business_situation)
    diagnostics = _as_dict(business_situation.get("diagnostics"))
    language_normalization = _as_dict(route.get("language_normalization")) or _as_dict(diagnostics.get("language_normalization"))
    clarification_authority = _as_dict(route.get("clarification_authority")) or _as_dict(diagnostics.get("clarification_authority"))
    return {
        "observatory_created": True,
        "observatory_version": BRAIN_OBSERVATORY_VERSION,
        "observatory_source": BRAIN_OBSERVATORY_SOURCE,
        "runtime_mode": BRAIN_OBSERVATORY_RUNTIME_MODE,
        "developer_only": True,
        "diagnostic_only": True,
        "runtime_only": True,
        "layers": layers,
        "layer_order": list(COGNITIVE_LAYERS),
        "constitution_monitor": constitution,
        "language_normalization": {
            "original_text": language_normalization.get("original_text"),
            "normalized_text": language_normalization.get("normalized_text"),
            "normalizations_applied": language_normalization.get("normalizations_applied") or [],
            "confidence": language_normalization.get("confidence"),
        },
        "clarification_authority": {
            "decision": clarification_authority.get("decision"),
            "reason": clarification_authority.get("reason"),
            "clarification_text": clarification_authority.get("clarification_text"),
            "requested_fields": clarification_authority.get("requested_fields") or [],
            "source_layers": clarification_authority.get("source_layers") or [],
            "duplicate_guard_applied": clarification_authority.get("duplicate_guard_applied"),
            "response_confidence": clarification_authority.get("response_confidence"),
            "fallback_used": clarification_authority.get("fallback_used"),
        },
        "cognitive_authority": cognitive_authority,
        "diagnostics_timeline": _diagnostics_timeline(layers),
        "invariants": {
            "routing_changed": False,
            "planner_changed": False,
            "workflow_changed": False,
            "responses_changed": False,
            "execution_changed": False,
            "commit_changed": False,
            "used_for_routing": False,
            "used_for_planner": False,
            "used_for_workflow": False,
            "used_for_response": False,
            "used_for_execution": False,
            "used_for_commit": False,
        },
    }
