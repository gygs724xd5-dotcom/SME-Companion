from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re


BUSINESS_TYPE_ALIASES = {
    "\u0e23\u0e49\u0e32\u0e19\u0e02\u0e32\u0e22\u0e0a\u0e32": "tea_shop",
    "\u0e23\u0e49\u0e32\u0e19\u0e0a\u0e32": "tea_shop",
    "\u0e0a\u0e32\u0e19\u0e21": "tea_shop",
    "\u0e0a\u0e32\u0e44\u0e17\u0e22": "tea_shop",
    "tea shop": "tea_shop",
    "coffee shop": "coffee_shop",
    "\u0e23\u0e49\u0e32\u0e19\u0e01\u0e32\u0e41\u0e1f": "coffee_shop",
    "\u0e23\u0e49\u0e32\u0e19\u0e2d\u0e32\u0e2b\u0e32\u0e23": "restaurant",
    "\u0e23\u0e49\u0e32\u0e19\u0e02\u0e19\u0e21": "bakery",
    "\u0e40\u0e1a\u0e40\u0e01\u0e2d\u0e23\u0e35\u0e48": "bakery",
    "\u0e40\u0e1a\u0e40\u0e01\u0e2d\u0e23\u0e35": "bakery",
    "\u0e40\u0e2a\u0e37\u0e49\u0e2d\u0e1c\u0e49\u0e32": "fashion_shop",
    "\u0e23\u0e49\u0e32\u0e19\u0e40\u0e2a\u0e37\u0e49\u0e2d\u0e1c\u0e49\u0e32": "fashion_shop",
    "\u0e23\u0e49\u0e32\u0e19\u0e02\u0e32\u0e22\u0e04\u0e23\u0e35\u0e21": "cosmetic_store",
    "\u0e23\u0e49\u0e32\u0e19\u0e04\u0e23\u0e35\u0e21": "cosmetic_store",
    "\u0e04\u0e23\u0e35\u0e21": "cosmetic_store",
    "cosmetic store": "cosmetic_store",
    "beauty shop": "cosmetic_store",
}

PRODUCT_ALIASES = {
    "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21": "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21",
    "\u0e0a\u0e32\u0e19\u0e21": "milk_tea",
    "\u0e0a\u0e32\u0e44\u0e17\u0e22": "thai_tea",
    "\u0e0a\u0e32": "tea",
    "\u0e01\u0e32\u0e41\u0e1f": "coffee",
    "\u0e02\u0e19\u0e21": "bakery",
    "\u0e04\u0e23\u0e35\u0e21": "cream",
}

GOAL_KEYWORDS = {
    "today_action": [
        "\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49\u0e04\u0e27\u0e23\u0e17\u0e33\u0e2d\u0e30\u0e44\u0e23",
        "\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49\u0e17\u0e33\u0e2d\u0e30\u0e44\u0e23",
        "\u0e04\u0e27\u0e23\u0e17\u0e33\u0e2d\u0e30\u0e44\u0e23\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49",
        "\u0e17\u0e33\u0e2d\u0e30\u0e44\u0e23\u0e14\u0e35\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49",
    ],
    "create_content": [
        "\u0e17\u0e33\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
        "\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
        "\u0e2a\u0e23\u0e49\u0e32\u0e07\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
        "\u0e41\u0e04\u0e1b\u0e0a\u0e31\u0e48\u0e19",
        "\u0e04\u0e2d\u0e19\u0e40\u0e17\u0e19\u0e15\u0e4c",
    ],
    "increase_sales": [
        "\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e22\u0e2d\u0e14",
        "\u0e22\u0e2d\u0e14\u0e02\u0e32\u0e22",
        "\u0e02\u0e32\u0e22\u0e14\u0e35\u0e02\u0e36\u0e49\u0e19",
        "\u0e44\u0e21\u0e48\u0e21\u0e35\u0e2d\u0e2d\u0e40\u0e14\u0e2d\u0e23\u0e4c",
    ],
    "set_price": [
        "\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
        "\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
        "\u0e15\u0e31\u0e49\u0e07\u0e23\u0e32\u0e04\u0e32",
        "\u0e02\u0e32\u0e22\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
    ],
}

PROBLEM_KEYWORDS = {
    "low_sales": [
        "\u0e22\u0e2d\u0e14\u0e15\u0e01",
        "\u0e02\u0e32\u0e22\u0e44\u0e21\u0e48\u0e14\u0e35",
        "\u0e44\u0e21\u0e48\u0e21\u0e35\u0e2d\u0e2d\u0e40\u0e14\u0e2d\u0e23\u0e4c",
        "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e19\u0e49\u0e2d\u0e22",
    ],
    "pricing_unclear": [
        "\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
        "\u0e15\u0e31\u0e49\u0e07\u0e23\u0e32\u0e04\u0e32",
        "\u0e41\u0e1e\u0e07\u0e44\u0e1b",
        "\u0e16\u0e39\u0e01\u0e44\u0e1b",
    ],
    "content_needed": [
        "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e2d\u0e30\u0e44\u0e23",
        "\u0e04\u0e2d\u0e19\u0e40\u0e17\u0e19\u0e15\u0e4c\u0e2d\u0e30\u0e44\u0e23",
        "\u0e41\u0e04\u0e1b\u0e0a\u0e31\u0e48\u0e19",
    ],
}

INTERNAL_LABELS = {
    "pricing_unclear",
    "cosmetic_store",
    "customer_says_expensive",
    "business_reasoning",
    "response_mode",
    "workflow_response",
}

SOURCE_PRIORITY = [
    "current_message",
    "workflow",
    "store_profile",
    "conversation_memory",
    "business_memory",
]


def _clean_dict(data: dict | None) -> dict:
    return {key: value for key, value in (data or {}).items() if value not in (None, "", [], {})}


def _is_internal_label(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text in INTERNAL_LABELS or bool(re.fullmatch(r"[a-z][a-z0-9]+(?:_[a-z0-9]+)+", text))


def sanitize_user_context_text(value):
    """Remove snake_case/internal labels from user-facing context snippets."""
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            clean = sanitize_user_context_text(item)
            if clean not in (None, "", [], {}):
                sanitized[key] = clean
        return sanitized
    if isinstance(value, list):
        return [
            item
            for item in (sanitize_user_context_text(item) for item in value)
            if item not in (None, "", [], {})
        ]
    if value is None:
        return None
    text = str(value)
    if text.strip().lower() in INTERNAL_LABELS:
        return ""
    text = re.sub(r"\b[a-z][a-z0-9]+(?:_[a-z0-9]+)+\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _store_profile(application_state: dict | None) -> dict:
    store = (application_state or {}).get("store") or {}
    if isinstance(store.get("profile"), dict):
        return store.get("profile") or {}
    return store


def _has_active_workflow(application_state: dict | None) -> bool:
    state = application_state or {}
    workflow = state.get("workflow") or {}
    workflow_state = workflow.get("workflow_state_v2") or {}
    if workflow_state.get("workflow") and workflow_state.get("step") != "completed":
        return True

    conversation = state.get("conversation") or {}
    conversation_workflow_state = conversation.get("workflow_state_v2") or {}
    if conversation_workflow_state.get("workflow") and conversation_workflow_state.get("step") != "completed":
        return True

    os_state = conversation.get("conversation_os") or {}
    active_id = os_state.get("active_workflow_id")
    active = (os_state.get("workflow_states") or {}).get(active_id) if active_id else None
    return bool(active and active.get("workflow_status") not in {"END", "CANCELLED", "TIMEOUT", "PAUSED"})


def _workflow_fields(application_state: dict | None) -> dict:
    state = application_state or {}
    conversation = state.get("conversation") or {}
    candidates = [
        ((state.get("workflow") or {}).get("workflow_state_v2") or {}),
        (conversation.get("workflow_state_v2") or {}),
    ]
    os_state = conversation.get("conversation_os") or {}
    active_id = os_state.get("active_workflow_id")
    if active_id:
        candidates.append((os_state.get("workflow_states") or {}).get(active_id) or {})
    for workflow_state in candidates:
        if not isinstance(workflow_state, dict):
            continue
        collected = workflow_state.get("collected_fields") or workflow_state.get("workflow_data") or {}
        if isinstance(collected, dict) and collected:
            return collected
    return {}


def _business_memory_context(application_state: dict | None) -> dict:
    memory = (application_state or {}).get("business_memory") or {}
    events = memory if isinstance(memory, list) else memory.get("events") or []
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else event
        if payload:
            return payload
    return memory if isinstance(memory, dict) else {}


def _match_alias(message: str, aliases: dict[str, str]) -> str | None:
    lowered = str(message or "").strip().lower()
    for phrase, value in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase.lower() in lowered:
            return value
    return None


def _match_keyword_group(message: str, groups: dict[str, list[str]]) -> str | None:
    lowered = str(message or "").strip().lower()
    for name, keywords in groups.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return name
    return None


def _extract_current_message_context(message: str) -> dict:
    business_type = _match_alias(message, BUSINESS_TYPE_ALIASES)
    product = _match_alias(message, PRODUCT_ALIASES)
    if product == "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21" and business_type == "cosmetic_store":
        business_type = None
    return _clean_dict(
        {
            "business_type": business_type,
            "current_product": product,
            "current_goal": _match_keyword_group(message, GOAL_KEYWORDS),
            "current_problem": _match_keyword_group(message, PROBLEM_KEYWORDS),
        }
    )


def _candidate_value(source: dict, *keys: str):
    for key in keys:
        value = source.get(key) if isinstance(source, dict) else None
        if value not in (None, "", [], {}):
            return value
    return None


def _add_candidate(candidates: dict, field: str, value, source: str) -> None:
    if value not in (None, "", [], {}):
        candidates.setdefault(field, []).append({"value": value, "source": source})


def _select_candidate(field: str, candidates: dict) -> tuple[object | None, str | None, list[dict]]:
    field_candidates = candidates.get(field) or []
    if not field_candidates:
        return None, None, []
    priority = {source: index for index, source in enumerate(SOURCE_PRIORITY)}
    selected = sorted(field_candidates, key=lambda item: priority.get(item["source"], 99))[0]
    selected_value = str(selected["value"]).strip().lower()
    conflicts = [
        {"field": field, "source": item["source"], "value": item["value"]}
        for item in field_candidates
        if item is not selected and str(item["value"]).strip().lower() != selected_value
    ]
    return selected["value"], selected["source"], conflicts


def _collect_internal_labels(*sources: dict) -> list[str]:
    labels = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if _is_internal_label(str(key)):
                labels.add(str(key))
            if isinstance(value, str) and _is_internal_label(value):
                labels.add(value)
            elif isinstance(value, list):
                labels.update(str(item) for item in value if isinstance(item, str) and _is_internal_label(item))
    return sorted(labels)


def _topic_from_context(context: dict, message: str) -> str | None:
    goal = context.get("current_goal")
    problem = context.get("current_problem")
    product = context.get("current_product")
    business_type = context.get("business_type")
    if goal == "today_action":
        return "daily business planning"
    if goal == "create_content":
        return "content planning"
    if goal == "set_price":
        return "pricing"
    if problem:
        return problem
    if product:
        return str(product)
    if business_type:
        return str(business_type)
    if message:
        return str(message).strip()[:80]
    return None


def build_business_context(
    application_state: dict | None,
    user_message: str | None,
    understanding: dict | None = None,
    conversation_memory: dict | None = None,
) -> dict:
    """Normalize business context; current user message has highest priority."""
    state = application_state or {}
    previous = deepcopy(
        state.get("business_context")
        or ((state.get("conversation") or {}).get("business_context"))
        or {}
    )
    profile = _store_profile(state)
    message = str(user_message or "").strip()
    priority = ((state.get("conversation") or {}).get("conversation_priority") or state.get("conversation_priority") or {})

    current = {}
    if not priority.get("allow_field_extraction") and not _has_active_workflow(state):
        current = _extract_current_message_context(message)

    workflow = _workflow_fields(state)
    business_memory = _business_memory_context(state)
    candidates: dict[str, list[dict]] = {}

    _add_candidate(candidates, "business_type", current.get("business_type"), "current_message")
    _add_candidate(candidates, "current_product", current.get("current_product"), "current_message")
    _add_candidate(candidates, "business_type", _candidate_value(workflow, "business_type", "store_type"), "workflow")
    _add_candidate(candidates, "current_product", _candidate_value(workflow, "product", "current_product", "product_or_business_type"), "workflow")
    _add_candidate(candidates, "business_type", _candidate_value(profile, "store_type", "business_type"), "store_profile")
    _add_candidate(candidates, "current_product", _candidate_value(profile, "product", "current_product"), "store_profile")
    _add_candidate(candidates, "business_type", _candidate_value(previous, "business_type", "store_type"), "conversation_memory")
    _add_candidate(candidates, "current_product", _candidate_value(previous, "current_product", "product"), "conversation_memory")
    _add_candidate(candidates, "business_type", _candidate_value(business_memory, "business_type", "store_type"), "business_memory")
    _add_candidate(candidates, "current_product", _candidate_value(business_memory, "current_product", "product"), "business_memory")

    context = {
        "business_type": None,
        "current_product": None,
        "current_discussion_topic": None,
        "source": None,
        "confidence": 0.0,
        "is_stale": False,
        "conflicts": [],
        "internal_labels": [],
    }
    sources = []
    for field in ["business_type", "current_product"]:
        value, source, conflicts = _select_candidate(field, candidates)
        context[field] = value
        if source:
            sources.append(source)
        context["conflicts"].extend(conflicts)

    profile_customer = profile.get("target_customer") or profile.get("customer_type")
    if profile_customer:
        context["customer_type"] = profile_customer
    context["current_goal"] = current.get("current_goal") or (previous.get("current_goal") if not current else None)
    context["current_problem"] = current.get("current_problem") or (previous.get("current_problem") if not current else None)

    if any(term in message.lower() for term in ["\u0e41\u0e04\u0e21\u0e40\u0e1b\u0e0d", "campaign", "\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e0a\u0e31\u0e19", "\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e0a\u0e31\u0e48\u0e19"]):
        context["current_campaign"] = message[:120]

    focused_topic = (
        (conversation_memory or {}).get("focused_business_topic")
        or ((understanding or {}).get("conversation_context") or {}).get("current_topic")
        or previous.get("current_discussion_topic")
    )
    current_has_clear_context = bool(current.get("business_type") or current.get("current_product"))
    context["current_discussion_topic"] = _topic_from_context(context, message)
    if not current_has_clear_context and focused_topic and not context["current_discussion_topic"]:
        context["current_discussion_topic"] = focused_topic

    context["source"] = sources[0] if sources else ("conversation_memory" if previous else "current_message")
    context["confidence"] = {
        "current_message": 0.95,
        "workflow": 0.9,
        "store_profile": 0.8,
        "conversation_memory": 0.55,
        "business_memory": 0.45,
    }.get(context["source"], 0.0)
    context["is_stale"] = context["source"] in {"conversation_memory", "business_memory"} and not current_has_clear_context
    context["internal_labels"] = _collect_internal_labels(previous, business_memory, current)
    context["updated_at"] = datetime.now(timezone.utc).isoformat()
    return context
