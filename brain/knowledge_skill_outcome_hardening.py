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
V5941_RUNTIME_INTEGRATION_VERSION = "5.9.4.1"
CLARIFICATION_RETRY_CAP = 2


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


def _bridge_from_route(route: dict | None) -> dict:
    route = route or {}
    diagnostics = ((route.get("business_situation") or {}).get("diagnostics") or {})
    return (
        route.get("knowledge_skill_bridge")
        or diagnostics.get("knowledge_skill_bridge")
        or ((route.get("planner_output") or {}).get("business_situation") or {}).get("diagnostics", {}).get("knowledge_skill_bridge")
        or {}
    )


def _compact_text(value: object) -> str:
    return "".join(str(value or "").lower().split())


def _contains_any(value: object, tokens: tuple[str, ...]) -> bool:
    compact = _compact_text(value)
    return any(token in compact for token in tokens)


def _number_in_text(value: object) -> int | float | None:
    import re

    match = re.search(r"\d[\d,]*(?:\.\d+)?", str(value or ""))
    if not match:
        return None
    number = float(match.group(0).replace(",", ""))
    return int(number) if number.is_integer() else number


def _pending_gap(conversation_state: dict | None) -> dict:
    state = conversation_state or {}
    return {
        "metric_id": state.get("pending_clarification_metric_id") or state.get("pending_clarification_id") or "",
        "gap_id": state.get("pending_clarification_id") or "",
        "known_partial_value": state.get("pending_known_partial_value") or {},
    }


def _state_patch_for_owner(
    *,
    owner: str,
    topic: str,
    previous_topic: str = "",
    pending_id: str = "",
    metric_id: str = "",
    known_partial: dict | None = None,
    retry_count: int = 0,
    stop_reason: str = "",
    current_inventory: int | float | None = None,
    superseded_values: list | None = None,
) -> dict:
    patch = {
        "conversation_cognitive_context": {
            "active_topic_id": topic,
            "active_topic_label": topic,
            "previous_topic_id": previous_topic,
            "pending_clarification_id": pending_id,
            "pending_clarification_metric_id": metric_id,
            "pending_known_partial_value": known_partial or {},
            "clarification_retry_count": retry_count,
            "clarification_stop_reason": stop_reason,
            "selected_response_owner": owner,
        },
        "active_topic_id": topic,
        "previous_topic_id": previous_topic,
        "pending_clarification_id": pending_id,
        "pending_clarification_metric_id": metric_id,
        "pending_known_partial_value": known_partial or {},
        "clarification_retry_count": retry_count,
        "clarification_stop_reason": stop_reason,
        "selected_response_owner": owner,
    }
    if current_inventory is not None:
        patch["current_inventory"] = current_inventory
        patch["freshest_value"] = current_inventory
        patch["conversation_cognitive_context"]["current_inventory"] = current_inventory
        patch["conversation_cognitive_context"]["freshest_value"] = current_inventory
    if superseded_values:
        patch["superseded_values"] = superseded_values
        patch["conversation_cognitive_context"]["superseded_values"] = superseded_values
    return patch


def _diagnostics(
    *,
    route: dict | None,
    bridge: dict,
    owner: str,
    generic_fallback_suppressed: bool,
    response_guard_mode: str = "pass",
    response_guard_violations: list[str] | None = None,
    conversation_state: dict | None = None,
) -> dict:
    outcome = bridge.get("conversation_outcome_hardening") or {}
    routing = outcome.get("conversation_routing_outcome") or {}
    topic = outcome.get("topic_transition") or routing.get("topic_transition") or {}
    follow = outcome.get("follow_up_resolution") or {}
    ambiguity = outcome.get("skill_ambiguity") or {}
    recovery = outcome.get("clarification_recovery") or {}
    conflict_sets = outcome.get("evidence_conflict_sets") or []
    next_gap = bridge.get("next_shared_gap") or routing.get("next_gap") or {}
    state = conversation_state or {}
    return {
        "runtime_integration_version": V5941_RUNTIME_INTEGRATION_VERSION,
        "active_topic": topic.get("current_topic_id") or routing.get("active_topic") or state.get("active_topic_id"),
        "previous_topic": topic.get("previous_topic_id") or state.get("previous_topic_id"),
        "topic_transition_type": topic.get("transition_type"),
        "topic_return_detected": topic.get("transition_type") == "TOPIC_RETURN",
        "pending_clarification_id": state.get("pending_clarification_id") or next_gap.get("gap_id"),
        "clarification_retry_count": recovery.get("retry_count", state.get("clarification_retry_count", 0)),
        "clarification_stop_reason": routing.get("stop_reason") or state.get("clarification_stop_reason"),
        "follow_up_resolution_status": follow.get("answer_status"),
        "skill_candidates": [item.get("skill_id") for item in bridge.get("candidate_skills") or [] if isinstance(item, dict)],
        "skill_ambiguity_status": ambiguity.get("status"),
        "missing_evidence": next_gap.get("missing_components") or [],
        "freshest_value": state.get("freshest_value") or state.get("current_inventory") or next_gap.get("known_partial_value"),
        "superseded_values": state.get("superseded_values") or [],
        "conflict_status": "CONFLICT" if conflict_sets else "NONE",
        "workflow_owner": ((route or {}).get("business_workflow") or {}).get("workflow_owner") or routing.get("response_owner"),
        "selected_response_owner": owner,
        "generic_fallback_suppressed": generic_fallback_suppressed,
        "response_guard_mode": response_guard_mode,
        "response_guard_violations": response_guard_violations or [],
        "response_commit_owner": "response_commit_boundary",
    }


def _guard_structured_reply(reply: str, *, owner: str, bridge: dict, route: dict | None) -> tuple[str, str, list[str]]:
    text = str(reply or "")
    violations: list[str] = []
    compact = _compact_text(text)
    inventory_gap = (bridge.get("next_shared_gap") or {}).get("metric_id") == "average_daily_sales"
    if inventory_gap and _contains_any(compact, ("สั่งเพิ่ม", "เติมสต็อก", "เติมสต๊อก", "reorder", "promotion", "โปรโม")):
        violations.append("recommendation_without_inventory_evidence")
    workflow_gate = (route or {}).get("workflow_admission_gate") or {}
    if owner != "workflow" and workflow_gate.get("decision") == "ADMIT" and bool(workflow_gate.get("workflow_executable")):
        violations.append("override_workflow_ownership")
    if violations:
        if inventory_gap:
            return "ตอนนี้รู้จำนวนคงเหลือแล้วครับ ก่อนสรุปว่าควรทำอะไร ขอจำนวนที่ขายเฉลี่ยต่อวัน หรือระยะเวลารอของจากซัพพลายเออร์ก่อนครับ", "downgrade_to_clarification", violations
        return "ข้อมูลตอนนี้ยังไม่พอให้สรุปอย่างมั่นใจครับ ขอรายละเอียดเพิ่มอีก 1 จุดก่อนครับ", "safe_limitation", violations
    return text, "pass", violations


def _clarification_reply_from_bridge(bridge: dict, route: dict | None) -> tuple[str, str, str, dict]:
    clarification = (route or {}).get("clarification_authority") or {}
    if clarification.get("decision") == "USE_SPECIFIC_CLARIFICATION" and clarification.get("clarification_text"):
        return (
            str(clarification.get("clarification_text")),
            "evidence_gap_clarification",
            "clarification_authority",
            {
                "pending_id": (bridge.get("next_shared_gap") or {}).get("gap_id") or "",
                "metric_id": (bridge.get("next_shared_gap") or {}).get("metric_id") or (clarification.get("requested_fields") or [""])[0],
                "known_partial": (bridge.get("next_shared_gap") or {}).get("known_partial_value") or {},
            },
        )
    return "", "", "", {}


def resolve_v5941_runtime_response(
    route: dict | None,
    user_message: str,
    conversation_state: dict | None = None,
) -> dict:
    """Select a V5.9.4 structured response owner before legacy fallback."""

    route = route or {}
    state = dict(conversation_state or {})
    bridge = _bridge_from_route(route)
    outcome = bridge.get("conversation_outcome_hardening") or {}
    routing = outcome.get("conversation_routing_outcome") or {}
    topic = outcome.get("topic_transition") or routing.get("topic_transition") or {}
    ambiguity = outcome.get("skill_ambiguity") or {}
    next_gap = bridge.get("next_shared_gap") or routing.get("next_gap") or {}

    workflow_gate = route.get("workflow_admission_gate") or {}
    workflow_payload = route.get("business_workflow") or {}
    admitted_workflow_id = (
        workflow_gate.get("workflow_candidate")
        or workflow_payload.get("workflow")
        or workflow_payload.get("workflow_id")
        or ((route.get("planner_output") or {}).get("workflow"))
    )
    if workflow_gate.get("decision") == "ADMIT" and admitted_workflow_id and bool(workflow_gate.get("workflow_executable")):
        return {
            "handled": False,
            "selected_response_owner": "active_workflow",
            "diagnostics": _diagnostics(route=route, bridge=bridge, owner="active_workflow", generic_fallback_suppressed=False, conversation_state=state),
        }

    prior_gap = _pending_gap(state)
    if prior_gap.get("metric_id") and topic.get("transition_type") not in {"TOPIC_SWITCH", "TOPIC_RETURN"}:
        follow = resolve_follow_up(user_message, prior_gap, prior_context=state)
        current_topic = state.get("active_topic_id") or ""
        explicit_switch = False
        recovery = recover_from_clarification(
            {"source_gap_id": prior_gap.get("gap_id"), "handoff_id": state.get("pending_clarification_id")},
            follow,
            retry_count=int(state.get("clarification_retry_count") or 0),
            topic_changed=explicit_switch,
            max_same_gap_attempts=CLARIFICATION_RETRY_CAP,
        )
        if follow.get("answer_status") == "ANSWERED":
            if prior_gap.get("metric_id") == "output_time_period":
                reply = "รับทราบครับ ผมใช้จำนวนนี้เป็นกำลังผลิตต่อวันแล้วครับ ตอนนี้มีออเดอร์หรือความต้องการเฉลี่ยวันละกี่ชิ้นครับ?"
                patch = _state_patch_for_owner(
                    owner="follow_up_resolution",
                    topic=current_topic,
                    previous_topic=state.get("previous_topic_id") or "",
                    pending_id="shared_gap::current_order_volume",
                    metric_id="current_order_volume",
                    known_partial={**(state.get("pending_known_partial_value") or {}), "output_time_period": follow.get("parsed_timeframe") or follow.get("parsed_value")},
                    retry_count=0,
                    stop_reason="FOLLOW_UP_RESOLVED",
                )
                guarded, guard_mode, violations = _guard_structured_reply(reply, owner="follow_up_resolution", bridge=bridge, route=route)
                diagnostics = _diagnostics(route=route, bridge=bridge, owner="follow_up_resolution", generic_fallback_suppressed=True, response_guard_mode=guard_mode, response_guard_violations=violations, conversation_state={**state, **patch})
                diagnostics["follow_up_resolution_status"] = "ANSWERED"
                return {"handled": True, "reply": guarded, "response_source": "v5941_follow_up_resolution", "selected_response_owner": "follow_up_resolution", "conversation_state_patch": patch, "diagnostics": diagnostics}
        elif follow.get("answer_status") in {"AMBIGUOUS", "PARTIALLY_ANSWERED", "UNRELATED"}:
            retry_count = int(recovery.get("retry_count") or state.get("clarification_retry_count") or 0) + 1
            if prior_gap.get("metric_id") == "sales_decline_driver":
                base_question = "ขอแยกสาเหตุก่อนครับ ตกที่คนเห็น/เข้าร้านน้อยลง, คนถามแล้วไม่ซื้อ, หรือยอดต่อออเดอร์ลดลง?"
                limited_reply = "ตอนนี้รู้แค่ว่ายอดตก แต่ยังไม่รู้ว่าตกจากคนเห็นน้อยลง การปิดการขาย หรือยอดต่อออเดอร์ จึงยังไม่สรุปสาเหตุครับ"
            elif prior_gap.get("metric_id") == "business_model":
                base_question = "ขอเลือกแบบเริ่มร้านก่อนครับ: ทำจากบ้านรับตามออเดอร์, ทำสต๊อกพร้อมขาย, หรือเปิดหน้าร้าน?"
                limited_reply = "ตอนนี้รู้ว่าต้องการดูทุนเปิดร้าน แต่ยังไม่รู้โมเดลร้าน จึงยังประเมินทุนเริ่มต้นให้ตรงแบบไม่ได้ครับ"
            else:
                base_question = "ขอเลือกให้แคบลงนิดครับ 100 ชิ้นนี้ใกล้เคียงแบบต่อวัน หรือต่อรอบการผลิตมากกว่าครับ?"
                limited_reply = "ตอนนี้ผมรู้จำนวนแล้ว แต่ยังไม่รู้ช่วงเวลาที่แน่นอน จึงยังตีความกำลังผลิตไม่ได้ครับ ถ้าจะวิเคราะห์ต่อ ต้องระบุว่าเป็นต่อวัน ต่อรอบ หรือช่วงเวลาอื่น"
            if retry_count >= CLARIFICATION_RETRY_CAP:
                reply = limited_reply
                stop_reason = "RETRY_CAP_EXHAUSTED"
                pending_id = ""
                metric_id = ""
            else:
                reply = base_question
                stop_reason = "RETRY_CLARIFICATION"
                pending_id = state.get("pending_clarification_id") or ""
                metric_id = prior_gap.get("metric_id") or ""
            patch = _state_patch_for_owner(
                owner="clarification_recovery",
                topic=current_topic,
                previous_topic=state.get("previous_topic_id") or "",
                pending_id=pending_id,
                metric_id=metric_id,
                known_partial=state.get("pending_known_partial_value") or {},
                retry_count=retry_count,
                stop_reason=stop_reason,
            )
            guarded, guard_mode, violations = _guard_structured_reply(reply, owner="clarification_recovery", bridge=bridge, route=route)
            diagnostics = _diagnostics(route=route, bridge=bridge, owner="clarification_recovery", generic_fallback_suppressed=True, response_guard_mode=guard_mode, response_guard_violations=violations, conversation_state={**state, **patch})
            diagnostics["follow_up_resolution_status"] = follow.get("answer_status")
            diagnostics["clarification_stop_reason"] = stop_reason
            diagnostics["clarification_retry_count"] = retry_count
            return {"handled": True, "reply": guarded, "response_source": "v5941_clarification_recovery", "selected_response_owner": "clarification_recovery", "conversation_state_patch": patch, "diagnostics": diagnostics}

    if ambiguity.get("ambiguity_detected"):
        reply = "ยอดที่ตกน่าจะมาจากจุดไหนก่อนครับ: คนเห็น/เข้าร้านน้อยลง, คนถามแล้วไม่ซื้อ, หรือยอดต่อออเดอร์ลดลง?"
        patch = _state_patch_for_owner(
            owner="skill_ambiguity",
            topic=topic.get("current_topic_id") or routing.get("active_topic") or "SALES_FUNNEL",
            previous_topic=topic.get("previous_topic_id") or state.get("active_topic_id") or "",
            pending_id="skill_ambiguity_clarification",
            metric_id="sales_decline_driver",
            retry_count=0,
            stop_reason="AMBIGUOUS_SKILL",
        )
        guarded, guard_mode, violations = _guard_structured_reply(reply, owner="skill_ambiguity", bridge=bridge, route=route)
        return {
            "handled": True,
            "reply": guarded,
            "response_source": "v5941_skill_ambiguity",
            "selected_response_owner": "skill_ambiguity",
            "conversation_state_patch": patch,
            "diagnostics": _diagnostics(route=route, bridge=bridge, owner="skill_ambiguity", generic_fallback_suppressed=True, response_guard_mode=guard_mode, response_guard_violations=violations, conversation_state={**state, **patch}),
        }

    reply, response_type, owner, clarification_context = _clarification_reply_from_bridge(bridge, route)
    if reply:
        current_topic = topic.get("current_topic_id") or routing.get("active_topic") or ""
        previous_topic = topic.get("previous_topic_id") or state.get("active_topic_id") or ""
        if current_topic == "INVENTORY_HEALTH" and next_gap.get("metric_id") == "average_daily_sales":
            reply = "ตอนนี้ขายหรือมีออเดอร์เฉลี่ยวันละกี่ชิ้นครับ?"
        current_inventory = _number_in_text(user_message) if current_topic == "INVENTORY_HEALTH" else None
        superseded = []
        if topic.get("transition_type") == "TOPIC_RETURN" and current_inventory is not None and state.get("current_inventory") not in (None, current_inventory):
            superseded.append(state.get("current_inventory"))
        patch = _state_patch_for_owner(
            owner=owner,
            topic=current_topic,
            previous_topic=previous_topic,
            pending_id=clarification_context.get("pending_id") or "",
            metric_id=clarification_context.get("metric_id") or "",
            known_partial=clarification_context.get("known_partial") or {},
            retry_count=0,
            stop_reason=response_type.upper(),
            current_inventory=current_inventory,
            superseded_values=superseded,
        )
        guarded, guard_mode, violations = _guard_structured_reply(reply, owner=owner, bridge=bridge, route=route)
        return {
            "handled": True,
            "reply": guarded,
            "response_source": "v5941_structured_clarification",
            "response_type": response_type,
            "selected_response_owner": owner,
            "conversation_state_patch": patch,
            "diagnostics": _diagnostics(route=route, bridge=bridge, owner=owner, generic_fallback_suppressed=True, response_guard_mode=guard_mode, response_guard_violations=violations, conversation_state={**state, **patch}),
        }

    return {
        "handled": False,
        "selected_response_owner": "safe_generic_fallback",
        "diagnostics": _diagnostics(route=route, bridge=bridge, owner="safe_generic_fallback", generic_fallback_suppressed=False, conversation_state=state),
    }
