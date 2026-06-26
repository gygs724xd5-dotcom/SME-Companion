def _compact_dict(data: dict | None, allowed_keys: list[str]) -> dict:
    source = data or {}
    return {
        key: source.get(key)
        for key in allowed_keys
        if source.get(key) not in (None, "", [], {})
    }


def _compact_events(business_memory: dict | list | None, limit: int = 5) -> list[dict]:
    if isinstance(business_memory, dict):
        events = business_memory.get("events", [])
    elif isinstance(business_memory, list):
        events = business_memory
    else:
        events = []

    compact_events = []
    for event in list(events)[-limit:]:
        if not isinstance(event, dict):
            continue
        compact_events.append(
            _compact_dict(
                event,
                ["created_at", "event_type", "summary", "metadata"],
            )
        )
    return compact_events


def build_llm_context(
    store_profile,
    business_diagnosis,
    goal_status,
    business_memory,
    business_os,
    recent_topics,
    intent_analysis=None,
    conversation_intent=None,
    conversation_mode=None,
    include_business_context=True,
    show_business_insights=False,
) -> dict:
    """Build compact context for the LLM communication layer.

    Business reasoning must already be done by deterministic engines. The LLM
    receives only summarized facts and recommendations to explain in Thai.
    """
    base_context = {
        "conversation": {
            "intent": conversation_intent,
            "mode": conversation_mode,
            "include_business_context": bool(include_business_context),
            "show_business_insights": bool(show_business_insights),
            "response_instruction": "ตอบให้กระชับ เหมาะกับหน้าจอมือถือ ถ้าผู้ใช้ไม่ได้ขอรายละเอียด ให้ตอบไม่เกิน 5-8 บรรทัด",
        }
    }

    if not include_business_context:
        return base_context

    context = {
        **base_context,
        "store_profile": _compact_dict(
            store_profile,
            ["store_name", "store_type", "product", "target_customer", "tone"],
        ),
        "intent": _compact_dict(
            intent_analysis,
            ["intent", "confidence", "reasoning", "suggested_action", "related_module"],
        ),
        "business_diagnosis": _compact_dict(
            business_diagnosis,
            [
                "diagnosis_summary",
                "likely_problem",
                "evidence",
                "root_cause",
                "recommended_fix",
                "urgency_level",
                "next_3_actions",
            ],
        ),
        "goal_status": _compact_dict(
            goal_status,
            [
                "goal_type",
                "goal_label",
                "goal_status",
                "progress_pct",
                "gap_to_goal",
                "goal_risk",
                "recommended_actions",
                "next_best_action",
                "target_value",
                "current_value",
                "deadline",
            ],
        ),
        "business_memory": {
            "recent_events": _compact_events(business_memory),
        },
        "business_os": _compact_dict(
            business_os,
            [
                "business_health_score",
                "operating_status",
                "top_priority",
                "current_risk",
                "growth_opportunity",
                "today_action",
                "weekly_focus",
                "owner_message",
            ],
        ),
        "recent_topics": [str(topic).strip() for topic in (recent_topics or []) if str(topic).strip()][:8],
    }

    if not show_business_insights:
        context.pop("business_diagnosis", None)
        context.pop("goal_status", None)
        context.pop("business_os", None)
        context.pop("business_memory", None)

    return context
