from __future__ import annotations

from dataclasses import asdict, dataclass, field

from brain.clarification_recovery import recover_from_clarification
from brain.context_freshness import evaluate_context_freshness
from brain.evidence_conflict_runtime import detect_current_correction
from brain.follow_up_resolution import resolve_follow_up
from brain.skill_ambiguity import assess_skill_ambiguity
from brain.topic_transition import detect_topic_transition
from brain.workflow_interruption import detect_workflow_interruption


KNOWLEDGE_SKILL_OUTCOME_HARDENING_VERSION = "5.9.4"


@dataclass
class ConversationRoutingOutcome:
    active_topic: str = ""
    topic_transition: dict = field(default_factory=dict)
    selected_frame: str = ""
    selected_knowledge: list[str] = field(default_factory=list)
    selected_skill: str = ""
    skill_confidence_status: str = "PRIMARY_SELECTED"
    readiness_status: str = ""
    next_gap: dict = field(default_factory=dict)
    response_owner: str = "SYSTEM"
    workflow_status: dict = field(default_factory=dict)
    judgment_allowed: bool = False
    planner_allowed: bool = False
    continuity_status: str = "WEAK"
    stop_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def harden_knowledge_skill_outcome(bridge_input: dict | None, bridge_result: dict | None) -> dict:
    bridge_input = bridge_input or {}
    bridge = bridge_result or {}
    user_message = str(bridge_input.get("current_message") or bridge_input.get("normalized_message") or "")
    previous_context = (bridge_input.get("conversation_context") or {}).get("conversation_cognitive_context") or (bridge_input.get("conversation_context") or {}).get("conversation_memory") or {}
    if not previous_context.get("active_topic_id"):
        primary_for_topic = bridge.get("primary_skill_candidate") or {}
        selected = bridge.get("selected_knowledge_ids") or []
        if selected or primary_for_topic:
            previous_context = {
                **previous_context,
                "active_topic_id": (selected[0] if selected else primary_for_topic.get("skill_id")),
                "active_topic_label": (selected[0] if selected else primary_for_topic.get("skill_id")),
                "unresolved_gap_ids": [((bridge.get("next_shared_gap") or {}).get("metric_id"))] if bridge.get("next_shared_gap") else [],
            }
    topic = detect_topic_transition(user_message, previous_context)
    prior_gap = previous_context.get("next_gap") or previous_context.get("next_shared_gap") or bridge.get("next_shared_gap") or {}
    follow_up = resolve_follow_up(user_message, prior_gap, prior_context=previous_context)
    clarification = recover_from_clarification(bridge.get("clarification_handoff") or {}, follow_up, retry_count=int(previous_context.get("clarification_retry_count") or 0), topic_changed=topic.get("transition_type") == "TOPIC_SWITCH")
    ambiguity = assess_skill_ambiguity(bridge.get("candidate_skills") or [], user_message=user_message)
    workflow = detect_workflow_interruption(user_message, bridge_input.get("workflow_state") or {})
    primary = bridge.get("primary_skill_candidate") or {}
    correction = {}
    if "ไม่ใช่" in user_message or "ตอนนี้" in user_message:
        current_value = follow_up.get("parsed_value")
        correction = detect_current_correction(user_message, prior_gap.get("metric_id") or "current_stock", prior_gap.get("known_partial_value", {}).get("value"), current_value)
    freshness = evaluate_context_freshness(prior_gap.get("metric_id") or "", turn_distance=1, topic_distance=1 if topic.get("transition_type") == "TOPIC_SWITCH" else 0, superseded=bool(correction))
    stop = "READY_FOR_FUTURE_JUDGMENT"
    if workflow.get("response_owner") == "WORKFLOW":
        stop = "WAITING_FOR_WORKFLOW_FIELD"
    if ambiguity.get("ambiguity_detected"):
        stop = "AMBIGUOUS_SKILL"
    elif clarification.get("next_action") in {"ASK_CLARIFICATION", "REPHRASE_WITH_OPTIONS"}:
        stop = "WAITING_FOR_CLARIFICATION"
    elif correction:
        stop = "CONFLICT_UNRESOLVED" if correction.get("resolution_required") else "READY_FOR_FUTURE_JUDGMENT"
    elif not primary:
        stop = "NO_SAFE_SKILL"
    outcome = ConversationRoutingOutcome(
        active_topic=topic.get("current_topic_id") or "",
        topic_transition=topic,
        selected_frame=str(bridge_input.get("selected_frame") or ""),
        selected_knowledge=list(bridge.get("selected_knowledge_ids") or []),
        selected_skill=str(primary.get("skill_id") or ""),
        skill_confidence_status=ambiguity.get("status") or "PRIMARY_SELECTED",
        readiness_status=(primary.get("evidence_readiness_result") or {}).get("status") or "",
        next_gap=bridge.get("next_shared_gap") or {},
        response_owner=workflow.get("response_owner") or ("CLARIFICATION_AUTHORITY" if bridge.get("clarification_handoff") else "SYSTEM"),
        workflow_status=workflow,
        judgment_allowed=bool((bridge.get("judgment_handoff") or {}).get("ready_for_judgment") == "READY_FOR_JUDGMENT" and not ambiguity.get("ambiguity_detected")),
        planner_allowed=False,
        continuity_status="BROKEN" if topic.get("transition_type") == "TOPIC_SWITCH" else "STRONG" if follow_up.get("continuity_used") else "MODERATE",
        stop_reason=stop,
    ).to_dict()
    return {
        "conversation_hardening_consulted": True,
        "active_topic_id": outcome["active_topic"],
        "topic_transition": topic,
        "topic_transition_detected": topic.get("transition_type") != "CONTINUATION",
        "topic_transition_type": topic.get("transition_type"),
        "continuity_strength": outcome["continuity_status"],
        "freshness": freshness,
        "stale_context_detected": freshness.get("freshness_status") in {"STALE", "SUPERSEDED"},
        "stale_context_suppressed": freshness.get("freshness_status") in {"STALE", "SUPERSEDED"},
        "follow_up_resolution": follow_up,
        "follow_up_resolved": follow_up.get("answer_status") == "ANSWERED",
        "partial_answer_detected": follow_up.get("answer_status") == "PARTIALLY_ANSWERED",
        "ambiguous_answer_detected": follow_up.get("answer_status") == "AMBIGUOUS",
        "user_declined_gap": follow_up.get("answer_status") == "USER_DECLINED",
        "clarification_recovery": clarification,
        "clarification_retry_count": clarification.get("retry_count"),
        "clarification_loop_prevented": not clarification.get("retry_allowed") and clarification.get("unresolved_gap_ids"),
        "skill_ambiguity": ambiguity,
        "skill_ambiguity_detected": ambiguity.get("ambiguity_detected"),
        "no_confident_primary_skill": ambiguity.get("status") == "NO_CONFIDENT_PRIMARY",
        "evidence_conflict_sets": [correction] if correction else [],
        "evidence_conflict_set_created": bool(correction),
        "current_correction_detected": bool(correction),
        "workflow_interruption": workflow,
        "workflow_interruption_detected": workflow.get("interruption_detected"),
        "workflow_state_preserved": workflow.get("workflow_preserved"),
        "legacy_fallback_hardening_applied": True,
        "conversation_routing_outcome": outcome,
        "version": KNOWLEDGE_SKILL_OUTCOME_HARDENING_VERSION,
    }
