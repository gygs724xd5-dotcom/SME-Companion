from __future__ import annotations

from copy import deepcopy
from typing import Any

from brain.business_reasoning_engine import reason_business_message
from brain.business_skill_loader import get_business_skill, search_business_skills
from brain.response_mode_engine import BUSINESS_CONSULTING


HIGH_CONFIDENCE_THRESHOLD = 0.6
MIN_DIRECT_MATCH_SCORE = 2

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


def _compact(data: dict | None) -> dict:
    return {key: value for key, value in (data or {}).items() if value not in (None, "", [], {})}


def _best_skill(user_message: str, conversation_context: dict | None) -> tuple[dict | None, bool]:
    business_context = (conversation_context or {}).get("business_context") or {}
    domain = business_context.get("business_domain")
    results = search_business_skills(user_message, domain=domain)
    if results and int(results[0].get("match_score") or 0) >= MIN_DIRECT_MATCH_SCORE:
        return results[0], False

    normalized = str(user_message or "").strip().lower()
    if any(term.lower() in normalized for term in _BROAD_BUSINESS_TERMS):
        return get_business_skill("close_sale"), True

    return None, False


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
    try:
        matched_skill, broad_consulting = _best_skill(user_message, conversation_context)
        if not matched_skill:
            return {
                "bridge_used": False,
                "fallback_used": True,
                "planner_output": existing_plan,
                "matched_skill": None,
                "matched_domain": None,
                "business_reasoning": None,
                "confidence": 0.0,
            }

        reasoning = reason_business_message(
            user_message,
            matched_skill,
            conversation_context,
        )
        confidence = float(reasoning.get("confidence") or 0.0)
        response_mode = BUSINESS_CONSULTING if broad_consulting else reasoning.get("response_mode")
        business_payload = {
            "matched_skill": _compact(
                {
                    "skill_id": matched_skill.get("skill_id"),
                    "skill_name": matched_skill.get("skill_name"),
                    "business_domain": matched_skill.get("business_domain"),
                    "match_score": matched_skill.get("match_score"),
                    "source_path": matched_skill.get("source_path"),
                }
            ),
            "matched_domain": matched_skill.get("business_domain"),
            "business_reasoning": reasoning,
            "business_principle": reasoning.get("business_principle"),
            "thinking_pattern": reasoning.get("thinking_pattern"),
            "decision_tree": reasoning.get("decision_tree") or [],
            "questions_to_ask": reasoning.get("questions_to_ask") or [],
            "response_mode": response_mode,
            "workflow": reasoning.get("workflow"),
            "memory_tags": reasoning.get("memory_tags") or [],
            "confidence": confidence,
            "bridge_used": True,
            "fallback_used": False,
            "broad_consulting": bool(broad_consulting),
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
            "business_reasoning": None,
            "confidence": 0.0,
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
