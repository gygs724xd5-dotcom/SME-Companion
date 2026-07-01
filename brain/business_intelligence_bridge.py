from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from brain.business_reasoning_engine import reason_business_message
from brain.business_skill_loader import get_business_skill, load_all_business_skills, search_business_skills
from brain.business_skill_matcher import rank_business_skills
from brain.planner_intent_priority import has_profit_calculation_intent
from brain.response_mode_engine import BUSINESS_CONSULTING


HIGH_CONFIDENCE_THRESHOLD = 0.6
MIN_MATCHER_CONFIDENCE = 0.6
NON_BUSINESS_EXPLANATORY_INTENTS = {
    "label_explanation",
    "general_question",
    "unknown_with_question",
}

_BROAD_BUSINESS_TERMS = (
    "\u0e2d\u0e22\u0e32\u0e01\u0e02\u0e32\u0e22",
    "\u0e40\u0e23\u0e34\u0e48\u0e21\u0e02\u0e32\u0e22",
    "\u0e02\u0e32\u0e22\u0e2d\u0e30\u0e44\u0e23",
    "\u0e02\u0e32\u0e22\u0e22\u0e31\u0e07\u0e44\u0e07",
    "\u0e02\u0e32\u0e22\u0e14\u0e35\u0e02\u0e36\u0e49\u0e19",
    "start selling",
    "sell more",
    "increase sales",
)

_STRONG_CURRENT_MESSAGE_BUSINESS_TERMS = (
    "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e1a\u0e2d\u0e01",
    "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e16\u0e32\u0e21",
    "\u0e15\u0e2d\u0e1a\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32",
    "\u0e04\u0e27\u0e23\u0e15\u0e2d\u0e1a\u0e22\u0e31\u0e07\u0e44\u0e07",
    "\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
    "\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e2b\u0e23\u0e48",
    "\u0e15\u0e31\u0e49\u0e07\u0e23\u0e32\u0e04\u0e32",
    "\u0e01\u0e33\u0e44\u0e23",
    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
    "\u0e22\u0e2d\u0e14\u0e02\u0e32\u0e22",
    "customer says",
    "customer asked",
    "reply customer",
    "respond to customer",
    "how much",
    "set price",
    "profit",
    "margin",
    "cost",
    "sales",
)


def _preview(value: Any, limit: int = 160) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _compact(data: dict | None) -> dict:
    return {key: value for key, value in (data or {}).items() if value not in (None, "", [], {})}


def _detected_intent(conversation_context: dict | None) -> str | None:
    context = conversation_context or {}
    business_context = context.get("business_context") or {}
    business_intent = context.get("business_intent") or {}
    business_workflow = context.get("business_workflow") or {}
    candidates = (
        business_intent.get("detected_intent"),
        context.get("detected_intent"),
        business_context.get("detected_intent"),
        business_workflow.get("detected_intent"),
    )
    fallback = None
    for candidate in candidates:
        if candidate in (None, "", [], {}):
            continue
        value = str(candidate)
        if value != "unknown":
            return value
        fallback = value
    return fallback


def _has_strong_current_message_business_evidence(user_message: str, conversation_context: dict | None) -> bool:
    detected_intent = _detected_intent(conversation_context)
    if detected_intent in {
        "customer_reply",
        "customer_says_expensive",
        "pricing_question",
        "profit_calculation",
        "sales_summary",
        "cost_calculation",
        "inventory_check",
        "marketing_content",
        "business_advice",
    }:
        return True
    normalized = str(user_message or "").strip().lower()
    return any(term.lower() in normalized for term in _STRONG_CURRENT_MESSAGE_BUSINESS_TERMS)


def _has_strong_cost_calculation_evidence(user_message: str, conversation_context: dict | None) -> bool:
    if has_profit_calculation_intent(user_message):
        return False
    context = conversation_context or {}
    business_context = context.get("business_context") or {}
    entities = context.get("extracted_entities") or business_context.get("extracted_entities") or {}
    detected_intent = _detected_intent(conversation_context)
    message = str(user_message or "")
    matched_keywords = [
        str(keyword)
        for keyword in (
            (context.get("business_intent") or {}).get("matched_intent_keywords")
            or business_context.get("matched_intent_keywords")
            or []
        )
    ]
    has_cost_intent = detected_intent == "cost_calculation" or any(
        keyword in {"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19", "\u0e17\u0e38\u0e19", "cost", "margin"}
        for keyword in matched_keywords
    )
    has_numeric_evidence = bool(entities.get("costs") or entities.get("prices") or entities.get("quantities") or re.search(r"\d", message))
    has_quantity = bool(entities.get("quantities") or any(unit in message for unit in ["\u0e0a\u0e34\u0e49\u0e19", "pcs", "unit"]))
    return bool(has_cost_intent and has_numeric_evidence and has_quantity)


def _should_suppress_price_skill_for_cost_message(
    user_message: str,
    conversation_context: dict | None,
    matched_skill: dict | None,
) -> bool:
    if not matched_skill:
        return False
    skill_id = str(matched_skill.get("skill_id") or "")
    return bool(skill_id.endswith("customer_asks_price") and _has_strong_cost_calculation_evidence(user_message, conversation_context))


def _should_bypass_skill_matching(user_message: str, conversation_context: dict | None) -> tuple[bool, str | None]:
    detected_intent = _detected_intent(conversation_context)
    if detected_intent not in NON_BUSINESS_EXPLANATORY_INTENTS:
        return False, None
    if _has_strong_current_message_business_evidence(user_message, conversation_context):
        return False, None
    return True, f"Bypassed business skill matching for non-business explanatory/general intent: {detected_intent}."


def _skill_matches_domain(skill: dict[str, Any], domain: str | None) -> bool:
    if not domain:
        return True
    normalized_domain = str(domain or "").strip().lower()
    skill_domain = str(skill.get("business_domain") or "").strip().lower()
    source_path = str(skill.get("source_path") or "").strip().lower()
    return normalized_domain in skill_domain or normalized_domain in source_path


def _candidate_skills(user_message: str, conversation_context: dict | None) -> list[dict]:
    business_context = (conversation_context or {}).get("business_context") or {}
    domain = business_context.get("business_domain")
    search_results = search_business_skills(user_message, domain=domain)
    candidates_by_id = {
        str(skill.get("skill_id") or ""): skill
        for skill in search_results
        if skill.get("skill_id")
    }
    if len(candidates_by_id) < 3:
        for skill in load_all_business_skills():
            if not _skill_matches_domain(skill, domain):
                continue
            skill_id = str(skill.get("skill_id") or "")
            if skill_id and skill_id not in candidates_by_id:
                candidates_by_id[skill_id] = skill
    return list(candidates_by_id.values())


def _skill_by_match(candidate_skills: list[dict], match: dict | None) -> dict | None:
    if not match:
        return None
    match_id = str(match.get("skill_id") or "")
    for skill in candidate_skills:
        if str(skill.get("skill_id") or "") == match_id:
            enriched = dict(skill)
            enriched["match_score"] = match.get("score")
            enriched["match_confidence"] = match.get("confidence")
            enriched["matching_reason"] = match.get("reason")
            enriched["matched_keywords"] = match.get("matched_keywords") or []
            enriched["matched_aliases"] = match.get("matched_aliases") or []
            return enriched
    return None


def _suspicious_matches(ranked_matches: list[dict]) -> list[dict]:
    suspicious: list[dict] = []
    suspicious_types = {
        "conversation_context",
        "skill_metadata",
        "bridge_context",
        "derived",
        "memory",
        "domain",
        "intent",
    }
    for match in ranked_matches or []:
        for item in match.get("match_provenance") or []:
            if item.get("matched_from_current_message"):
                continue
            if item.get("token_type") not in suspicious_types:
                continue
            if not (
                item.get("matched_from_conversation_context")
                or item.get("matched_from_memory")
                or item.get("matched_from_skill_metadata")
                or item.get("token_type") in {"derived", "intent", "domain"}
            ):
                continue
            suspicious.append(
                {
                    "skill_id": match.get("skill_id"),
                    "token": item.get("token"),
                    "token_type": item.get("token_type"),
                    "source_field": item.get("source_field"),
                    "source_value_preview": item.get("source_value_preview"),
                    "score_contribution": item.get("score_contribution"),
                    "reason": "Matched token did not appear in the current message and came from context, metadata, memory, intent, domain, or a derived source.",
                }
            )
    return suspicious


def _suspicious_token_summary(ranked_matches: list[dict]) -> list[dict]:
    summary: list[dict] = []
    suspicious_types = {
        "conversation_context",
        "skill_metadata",
        "bridge_context",
        "derived",
        "memory",
        "domain",
        "intent",
    }
    for match in ranked_matches or []:
        for item in match.get("match_provenance") or []:
            if item.get("matched_from_current_message"):
                continue
            if item.get("token_type") not in suspicious_types:
                continue
            if not (
                item.get("matched_from_conversation_context")
                or item.get("matched_from_memory")
                or item.get("matched_from_skill_metadata")
                or item.get("token_type") in {"derived", "intent", "domain"}
            ):
                continue
            summary.append(
                {
                    "token": item.get("token"),
                    "skill_id": match.get("skill_id"),
                    "source_field": item.get("source_field"),
                    "matched_from_current_message": bool(item.get("matched_from_current_message")),
                    "score_contribution": item.get("score_contribution"),
                }
            )
    return summary


def _skill_match_audit_summary(ranked_matches: list[dict]) -> dict:
    suspicious_tokens = _suspicious_token_summary(ranked_matches)
    suspicious_by_skill: dict[str, list[dict]] = {}
    for item in suspicious_tokens:
        skill_id = str(item.get("skill_id") or "")
        suspicious_by_skill.setdefault(skill_id, []).append(item)

    top_ranked_skills: list[dict] = []
    for match in (ranked_matches or [])[:5]:
        skill_id = str(match.get("skill_id") or "")
        current_message_match = match.get("current_message_match") or {}
        context_match = match.get("context_match") or {}
        intent_match = match.get("intent_match") or {}
        skill_suspicious = suspicious_by_skill.get(skill_id, [])
        top_ranked_skills.append(
            {
                "skill_id": match.get("skill_id"),
                "score": match.get("score"),
                "current_message_evidence": {
                    "keywords": current_message_match.get("current_message_matched_keywords") or [],
                    "aliases": current_message_match.get("current_message_matched_aliases") or [],
                    "score": current_message_match.get("current_message_score"),
                },
                "context_evidence": {
                    "tokens": context_match.get("context_tokens_used") or [],
                    "sources": context_match.get("context_sources_used") or [],
                    "suppressed": bool(context_match.get("context_suppressed")),
                    "suppression_reason": context_match.get("context_suppression_reason"),
                },
                "suspicious_tokens": [item.get("token") for item in skill_suspicious],
                "suspicious_token_sources": [
                    {
                        "token": item.get("token"),
                        "source_field": item.get("source_field"),
                    }
                    for item in skill_suspicious
                ],
                "intent_score": intent_match.get("intent_score"),
                "context_score": context_match.get("context_score"),
                "why_ranked": match.get("reason"),
            }
        )

    return {
        "top_ranked_skills": top_ranked_skills,
        "suspicious_tokens": suspicious_tokens,
    }


def _skill_match_audit(
    user_message: str,
    conversation_context: dict | None,
    ranked_matches: list[dict],
    *,
    bypassed: bool = False,
    bypass_reason: str | None = None,
) -> dict:
    context = conversation_context or {}
    business_context = context.get("business_context") or {}
    business_intent = context.get("business_intent") or {}
    top = ranked_matches[0] if ranked_matches else {}
    return {
        "current_message": _preview(user_message),
        "detected_intent": (
            business_intent.get("detected_intent")
            or context.get("detected_intent")
            or business_context.get("detected_intent")
        ),
        "previous_context_intent": context.get("previous_context_intent") or business_context.get("previous_context_intent"),
        "intent_changed": bool(context.get("intent_changed") or business_context.get("intent_changed")),
        "context_isolation_applied": bool(
            context.get("context_isolation_applied")
            or business_context.get("context_isolation_applied")
            or context.get("intent_changed")
            or business_context.get("intent_changed")
        ),
        "top_skill_id": top.get("skill_id"),
        "top_skill_score": top.get("score"),
        "top_skill_reason": top.get("reason"),
        "suspicious_matches": _suspicious_matches(ranked_matches),
        "skill_match_audit_summary": _skill_match_audit_summary(ranked_matches),
        "skill_matching_bypassed": bool(bypassed),
        "skill_matching_bypass_reason": bypass_reason,
    }


def _best_skill(user_message: str, conversation_context: dict | None) -> tuple[dict | None, bool, list[dict]]:
    candidate_skills = _candidate_skills(user_message, conversation_context)
    ranked_matches = rank_business_skills(
        user_message,
        conversation_context,
        candidate_skills,
        limit=5,
    )
    if ranked_matches and float(ranked_matches[0].get("confidence") or 0.0) >= MIN_MATCHER_CONFIDENCE:
        return _skill_by_match(candidate_skills, ranked_matches[0]), False, ranked_matches

    normalized = str(user_message or "").strip().lower()
    if any(term.lower() in normalized for term in _BROAD_BUSINESS_TERMS):
        fallback_skill = get_business_skill("close_sale")
        fallback_matches = rank_business_skills(
            user_message,
            conversation_context,
            [fallback_skill] if fallback_skill else [],
            limit=1,
        )
        return fallback_skill, True, fallback_matches

    return None, False, ranked_matches


def run_business_intelligence_bridge(
    user_message: str,
    conversation_context: dict | None = None,
    planner_output: dict | None = None,
) -> dict:
    """Connect business skill search and business reasoning to the planner path.

    The bridge is intentionally fail-open. If a skill cannot be matched, or any
    bridge dependency raises, callers can keep using the existing planner result.
    """
    existing_plan = deepcopy(planner_output or {})
    context = conversation_context or {}
    business_context = context.get("business_context") or {}
    detected_intent = _detected_intent(conversation_context)
    extracted_entities = context.get("extracted_entities") or business_context.get("extracted_entities") or {}
    try:
        skill_matching_bypassed, skill_matching_bypass_reason = _should_bypass_skill_matching(
            user_message,
            conversation_context,
        )
        if skill_matching_bypassed:
            skill_match_audit = _skill_match_audit(
                user_message,
                conversation_context,
                [],
                bypassed=True,
                bypass_reason=skill_matching_bypass_reason,
            )
            skill_match_audit_summary = skill_match_audit.get("skill_match_audit_summary") or {}
            return {
                "bridge_used": False,
                "fallback_used": False,
                "planner_output": existing_plan,
                "matched_skill": None,
                "matched_domain": None,
                "matched_skills": [],
                "ranking_table": [],
                "top_skill": None,
                "top_confidence": 0.0,
                "matching_reason": None,
                "business_reasoning": None,
                "confidence": 0.0,
                "detected_intent": detected_intent,
                "extracted_entities": extracted_entities,
                "skill_match_audit": skill_match_audit,
                "skill_match_audit_summary": skill_match_audit_summary,
                "skill_matching_bypassed": True,
                "skill_matching_bypass_reason": skill_matching_bypass_reason,
            }

        matched_skill, broad_consulting, ranked_matches = _best_skill(user_message, conversation_context)
        suppressed_skill = None
        if _should_suppress_price_skill_for_cost_message(user_message, conversation_context, matched_skill):
            suppressed_skill = {
                "skill_id": matched_skill.get("skill_id"),
                "reason": "suppressed customer_asks_price because current message has strong cost_calculation evidence",
            }
            matched_skill = None
            broad_consulting = False
        skill_match_audit = _skill_match_audit(user_message, conversation_context, ranked_matches)
        if suppressed_skill:
            skill_match_audit["suppressed_top_skill"] = suppressed_skill
        skill_match_audit_summary = skill_match_audit.get("skill_match_audit_summary") or {}
        if not matched_skill:
            return {
                "bridge_used": False,
                "fallback_used": True,
                "planner_output": existing_plan,
                "matched_skill": None,
                "matched_domain": None,
                "matched_skills": ranked_matches,
                "ranking_table": ranked_matches,
                "top_skill": None,
                "top_confidence": 0.0,
                "matching_reason": None,
                "business_reasoning": None,
                "confidence": 0.0,
                "detected_intent": detected_intent,
                "extracted_entities": extracted_entities,
                "skill_match_audit": skill_match_audit,
                "skill_match_audit_summary": skill_match_audit_summary,
                "skill_matching_bypassed": False,
                "skill_matching_bypass_reason": None,
                "suppressed_top_skill": suppressed_skill,
            }

        reasoning = reason_business_message(
            user_message,
            matched_skill,
            conversation_context,
        )
        confidence = float(reasoning.get("confidence") or 0.0)
        top_match = ranked_matches[0] if ranked_matches else {}
        top_confidence = float(top_match.get("confidence") or matched_skill.get("match_confidence") or confidence)
        response_mode = BUSINESS_CONSULTING if broad_consulting else reasoning.get("response_mode")
        business_payload = {
            "matched_skill": _compact(
                {
                    "skill_id": matched_skill.get("skill_id"),
                    "skill_name": matched_skill.get("skill_name"),
                    "business_domain": matched_skill.get("business_domain"),
                    "match_score": matched_skill.get("match_score"),
                    "matched_keywords": matched_skill.get("matched_keywords"),
                    "matched_aliases": matched_skill.get("matched_aliases"),
                    "matching_reason": matched_skill.get("matching_reason"),
                    "source_path": matched_skill.get("source_path"),
                }
            ),
            "matched_domain": matched_skill.get("business_domain"),
            "matched_skills": ranked_matches,
            "ranking_table": ranked_matches,
            "top_skill": matched_skill.get("skill_id"),
            "top_confidence": top_confidence,
            "matching_reason": matched_skill.get("matching_reason") or top_match.get("reason"),
            "business_reasoning": reasoning,
            "business_principle": reasoning.get("business_principle"),
            "thinking_pattern": reasoning.get("thinking_pattern"),
            "decision_tree": reasoning.get("decision_tree") or [],
            "questions_to_ask": reasoning.get("questions_to_ask") or [],
            "response_mode": response_mode,
            "workflow": reasoning.get("workflow"),
            "memory_tags": reasoning.get("memory_tags") or [],
            "confidence": max(confidence, top_confidence),
            "bridge_used": True,
            "fallback_used": False,
            "broad_consulting": bool(broad_consulting),
            "detected_intent": detected_intent,
            "extracted_entities": extracted_entities,
            "skill_match_audit": skill_match_audit,
            "skill_match_audit_summary": skill_match_audit_summary,
            "skill_matching_bypassed": False,
            "skill_matching_bypass_reason": None,
        }
        return {
            **business_payload,
            "planner_output": existing_plan,
            "business_principle": business_payload["business_principle"],
        }
    except Exception as exc:
        return {
            "bridge_used": False,
            "fallback_used": True,
            "planner_output": existing_plan,
            "matched_skill": None,
            "matched_domain": None,
            "matched_skills": [],
            "ranking_table": [],
            "top_skill": None,
            "top_confidence": 0.0,
            "matching_reason": None,
            "business_reasoning": None,
            "confidence": 0.0,
            "detected_intent": detected_intent,
            "extracted_entities": extracted_entities,
            "skill_match_audit": _skill_match_audit(user_message, conversation_context, []),
            "skill_match_audit_summary": _skill_match_audit_summary([]),
            "skill_matching_bypassed": False,
            "skill_matching_bypass_reason": None,
            "bridge_error": f"{type(exc).__name__}: {exc}",
        }


def inject_business_intelligence(
    planner_output: dict | None,
    bridge_result: dict | None,
) -> dict:
    """Return planner output enriched with business reasoning when confidence is high."""
    plan = deepcopy(planner_output or {})
    bridge = bridge_result or {}
    if not bridge.get("bridge_used"):
        return plan

    plan["business_intelligence"] = _compact(
        {
            "matched_skill": bridge.get("matched_skill"),
            "matched_domain": bridge.get("matched_domain"),
            "matched_skills": bridge.get("matched_skills"),
            "ranking_table": bridge.get("ranking_table"),
            "top_skill": bridge.get("top_skill"),
            "top_confidence": bridge.get("top_confidence"),
            "matching_reason": bridge.get("matching_reason"),
            "business_principle": bridge.get("business_principle"),
            "thinking_pattern": bridge.get("thinking_pattern"),
            "decision_tree": bridge.get("decision_tree"),
            "questions_to_ask": bridge.get("questions_to_ask"),
            "response_mode": bridge.get("response_mode"),
            "workflow": bridge.get("workflow"),
            "memory_tags": bridge.get("memory_tags"),
            "confidence": bridge.get("confidence"),
            "bridge_used": bridge.get("bridge_used"),
            "fallback_used": bridge.get("fallback_used"),
            "detected_intent": bridge.get("detected_intent"),
            "extracted_entities": bridge.get("extracted_entities"),
        }
    )
    plan["business_reasoning"] = bridge.get("business_reasoning")
    plan["business_principle"] = bridge.get("business_principle")
    plan["thinking_pattern"] = bridge.get("thinking_pattern")
    plan["decision_tree"] = bridge.get("decision_tree") or []
    plan["questions_to_ask"] = bridge.get("questions_to_ask") or []
    plan["business_response_mode"] = bridge.get("response_mode")

    if float(bridge.get("confidence") or 0.0) >= HIGH_CONFIDENCE_THRESHOLD:
        if bridge.get("broad_consulting") or plan.get("task_type") == "General Business Help":
            plan["task_type"] = "Business Consulting"
            plan["workflow"] = plan.get("workflow")
            plan["estimated_response_mode"] = BUSINESS_CONSULTING
        elif bridge.get("response_mode"):
            plan["estimated_response_mode"] = bridge.get("response_mode")
    return plan
