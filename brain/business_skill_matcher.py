from __future__ import annotations

import re
from typing import Any


DEFAULT_LIMIT = 5

WEIGHTS = {
    "keyword": 0.22,
    "intent": 0.18,
    "business_domain": 0.10,
    "conversation_context": 0.10,
    "business_stage": 0.08,
    "memory_tag": 0.07,
    "exact_phrase": 0.17,
    "semantic_alias": 0.08,
}

SEMANTIC_ALIASES = {
    "customer_asks_price": (
        "\u0e23\u0e32\u0e04\u0e32",
        "\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
        "\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
        "\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17",
        "how much",
        "price",
    ),
    "customer_says_expensive": (
        "\u0e41\u0e1e\u0e07",
        "\u0e41\u0e1e\u0e07\u0e44\u0e1b",
        "\u0e25\u0e14\u0e44\u0e14\u0e49\u0e44\u0e2b\u0e21",
        "\u0e23\u0e49\u0e32\u0e19\u0e2d\u0e37\u0e48\u0e19\u0e16\u0e39\u0e01\u0e01\u0e27\u0e48\u0e32",
        "expensive",
        "too expensive",
        "discount",
    ),
    "close_sale": (
        "\u0e2a\u0e31\u0e48\u0e07",
        "\u0e2a\u0e31\u0e48\u0e07\u0e22\u0e31\u0e07\u0e44\u0e07",
        "\u0e40\u0e2d\u0e32",
        "\u0e08\u0e2d\u0e07",
        "\u0e42\u0e2d\u0e19",
        "order",
        "buy",
        "checkout",
    ),
    "create_promotion": (
        "\u0e42\u0e1b\u0e23",
        "\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e0a\u0e31\u0e48\u0e19",
        "\u0e25\u0e14\u0e23\u0e32\u0e04\u0e32",
        "\u0e41\u0e04\u0e21\u0e40\u0e1b\u0e0d",
        "promotion",
        "campaign",
        "discount",
    ),
    "create_facebook_post": (
        "\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
        "\u0e40\u0e1f\u0e0b\u0e1a\u0e38\u0e4a\u0e01",
        "facebook post",
        "caption",
        "content",
    ),
    "customer_disappears": (
        "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e2b\u0e32\u0e22",
        "\u0e40\u0e07\u0e35\u0e22\u0e1a",
        "\u0e44\u0e21\u0e48\u0e15\u0e2d\u0e1a",
        "disappear",
        "ghost",
    ),
    "shipping_question": (
        "\u0e04\u0e48\u0e32\u0e2a\u0e48\u0e07",
        "\u0e2a\u0e48\u0e07\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
        "\u0e08\u0e31\u0e14\u0e2a\u0e48\u0e07",
        "shipping",
        "delivery",
    ),
    "payment_question": (
        "\u0e08\u0e48\u0e32\u0e22",
        "\u0e42\u0e2d\u0e19",
        "\u0e1a\u0e31\u0e0d\u0e0a\u0e35",
        "payment",
        "pay",
        "bank transfer",
    ),
    "refund_request": (
        "\u0e04\u0e37\u0e19\u0e40\u0e07\u0e34\u0e19",
        "\u0e02\u0e2d\u0e40\u0e07\u0e34\u0e19\u0e04\u0e37\u0e19",
        "refund",
        "return",
    ),
    "startup_business": (
        "\u0e40\u0e1b\u0e34\u0e14\u0e23\u0e49\u0e32\u0e19",
        "\u0e40\u0e23\u0e34\u0e48\u0e21\u0e02\u0e32\u0e22",
        "\u0e2d\u0e22\u0e32\u0e01\u0e40\u0e1b\u0e34\u0e14\u0e23\u0e49\u0e32\u0e19",
        "start business",
        "open a shop",
    ),
    "sales_planning": (
        "\u0e27\u0e32\u0e07\u0e41\u0e1c\u0e19\u0e02\u0e32\u0e22",
        "\u0e02\u0e32\u0e22\u0e22\u0e31\u0e07\u0e44\u0e07",
        "sales plan",
        "sales planning",
    ),
    "marketing": (
        "\u0e01\u0e32\u0e23\u0e15\u0e25\u0e32\u0e14",
        "\u0e42\u0e06\u0e29\u0e13\u0e32",
        "marketing",
        "ads",
    ),
}

BUSINESS_STAGE_ALIASES = {
    "awareness": ("\u0e42\u0e1e\u0e2a\u0e15\u0e4c", "facebook", "content", "marketing"),
    "interest": ("\u0e23\u0e32\u0e04\u0e32", "\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23", "price", "how much"),
    "consideration": ("\u0e41\u0e1e\u0e07", "\u0e25\u0e14", "expensive", "promotion", "discount"),
    "purchase": ("\u0e2a\u0e31\u0e48\u0e07", "\u0e40\u0e2d\u0e32", "\u0e08\u0e2d\u0e07", "order", "buy"),
}


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _slug_from_skill_id(skill_id: Any) -> str:
    parts = str(skill_id or "").split(".")
    return parts[-1] if parts else ""


def _tokens(value: Any) -> list[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []
    tokens = re.findall(r"[a-z0-9]+|[\u0e00-\u0e7f]+", normalized)
    return [token for token in tokens if len(token) > 1]


def _split_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "")
    return [
        item.strip(" -\t\r\n")
        for item in re.split(r"[\n,;]+", text)
        if item.strip(" -\t\r\n")
    ]


def _skill_text(skill: dict[str, Any]) -> str:
    fields = (
        "skill_id",
        "skill_name",
        "business_domain",
        "business_principle",
        "conversation_stage",
        "business_goal",
        "situation",
        "intent",
        "example_questions",
        "recommended_response",
        "business_rules",
        "workflow_integration",
        "response_mode",
        "memory_tags",
        "related_skills",
    )
    return _normalize_text(" ".join(str(skill.get(field) or "") for field in fields))


def _context_text(conversation_context: dict | None) -> str:
    context = conversation_context or {}
    business_context = context.get("business_context") or {}
    parts = [
        context.get("current_workflow"),
        context.get("response_mode"),
        context.get("intent"),
        business_context.get("business_domain"),
        business_context.get("business_stage"),
        business_context.get("business_goal"),
        business_context.get("customer_segment"),
        business_context.get("memory_tags"),
        context.get("memory_tags"),
    ]
    return _normalize_text(" ".join(str(part or "") for part in parts))


def _context_memory_tags(conversation_context: dict | None) -> set[str]:
    context = conversation_context or {}
    business_context = context.get("business_context") or {}
    tags = set()
    for value in (context.get("memory_tags"), business_context.get("memory_tags")):
        for tag in _split_list(value):
            tags.add(_normalize_text(tag))
    return {tag for tag in tags if tag}


def _matched_aliases(message: str, slug: str) -> list[str]:
    normalized_message = _normalize_text(message)
    aliases = SEMANTIC_ALIASES.get(slug, ())
    return [
        alias
        for alias in aliases
        if _normalize_text(alias) and _normalize_text(alias) in normalized_message
    ]


def _matched_keywords(message: str, skill: dict[str, Any]) -> list[str]:
    normalized_message = _normalize_text(message)
    message_tokens = set(_tokens(message))
    candidates = set()
    for field in (
        "skill_name",
        "business_domain",
        "conversation_stage",
        "business_goal",
        "situation",
        "intent",
        "example_questions",
        "memory_tags",
    ):
        candidates.update(_tokens(skill.get(field)))
    slug_tokens = _tokens(_slug_from_skill_id(skill.get("skill_id")))
    candidates.update(slug_tokens)
    matches = {
        keyword
        for keyword in candidates
        if keyword and (keyword in message_tokens or keyword in normalized_message)
    }
    return sorted(matches)


def _ratio(matches: int, possible: int) -> float:
    if possible <= 0:
        return 0.0
    return min(1.0, matches / possible)


def _component_scores(
    user_message: str,
    conversation_context: dict | None,
    skill: dict[str, Any],
) -> dict[str, float | list[str]]:
    normalized_message = _normalize_text(user_message)
    searchable_text = _skill_text(skill)
    slug = _slug_from_skill_id(skill.get("skill_id"))
    matched_keywords = _matched_keywords(user_message, skill)
    matched_aliases = _matched_aliases(user_message, slug)

    message_tokens = _tokens(user_message)
    keyword_score = _ratio(len(matched_keywords), max(3, len(message_tokens)))

    intent_text = _normalize_text(skill.get("intent"))
    situation_text = _normalize_text(skill.get("situation"))
    intent_score = 0.0
    if normalized_message and normalized_message in f"{intent_text} {situation_text}":
        intent_score = 1.0
    elif matched_aliases:
        intent_score = 0.85
    elif any(token in f"{intent_text} {situation_text}" for token in message_tokens):
        intent_score = 0.45

    context = conversation_context or {}
    business_context = context.get("business_context") or {}
    requested_domain = _normalize_text(business_context.get("business_domain"))
    skill_domain = _normalize_text(skill.get("business_domain"))
    business_domain_score = 0.0
    if requested_domain and skill_domain and (requested_domain in skill_domain or skill_domain in requested_domain):
        business_domain_score = 1.0
    elif skill_domain and any(token in skill_domain for token in message_tokens):
        business_domain_score = 0.5

    context_text = _context_text(conversation_context)
    context_score = 0.0
    if context_text:
        context_tokens = _tokens(context_text)
        context_score = _ratio(
            sum(1 for token in context_tokens if token in searchable_text),
            max(3, len(context_tokens)),
        )

    stage = _normalize_text(skill.get("conversation_stage"))
    stage_aliases = BUSINESS_STAGE_ALIASES.get(stage, ())
    business_stage_score = 0.0
    if stage and stage in context_text:
        business_stage_score = 1.0
    elif any(_normalize_text(alias) in normalized_message for alias in stage_aliases):
        business_stage_score = 0.8

    skill_memory_tags = {_normalize_text(tag) for tag in _split_list(skill.get("memory_tags"))}
    context_memory_tags = _context_memory_tags(conversation_context)
    memory_tag_score = 0.0
    if context_memory_tags and skill_memory_tags:
        memory_tag_score = _ratio(
            len(context_memory_tags.intersection(skill_memory_tags)),
            len(context_memory_tags),
        )
    elif any(tag.replace(" ", "_") in _normalize_text(skill.get("skill_id")) for tag in context_memory_tags):
        memory_tag_score = 0.5

    exact_phrase_score = 0.0
    exact_phrases = _split_list(skill.get("example_questions")) + list(SEMANTIC_ALIASES.get(slug, ()))
    for phrase in exact_phrases:
        normalized_phrase = _normalize_text(phrase.strip('"'))
        if normalized_phrase and normalized_phrase in normalized_message:
            exact_phrase_score = 1.0
            break

    semantic_alias_score = 1.0 if matched_aliases else 0.0

    return {
        "keyword": keyword_score,
        "intent": intent_score,
        "business_domain": business_domain_score,
        "conversation_context": context_score,
        "business_stage": business_stage_score,
        "memory_tag": memory_tag_score,
        "exact_phrase": exact_phrase_score,
        "semantic_alias": semantic_alias_score,
        "matched_keywords": matched_keywords,
        "matched_aliases": matched_aliases,
    }


def _weighted_score(components: dict[str, float | list[str]]) -> float:
    score = 0.0
    for name, weight in WEIGHTS.items():
        score += float(components.get(name) or 0.0) * weight
    return score


def _confidence(score: float, components: dict[str, float | list[str]]) -> float:
    confidence = score
    if components.get("exact_phrase") and components.get("semantic_alias"):
        confidence = max(confidence, 0.97)
    elif components.get("exact_phrase"):
        confidence = max(confidence, 0.9)
    elif components.get("semantic_alias"):
        confidence = max(confidence, 0.82)
    if components.get("business_domain") and components.get("memory_tag"):
        confidence += 0.04
    return round(min(0.99, confidence), 2)


def _reason(skill: dict[str, Any], components: dict[str, float | list[str]]) -> str:
    reasons = []
    if components.get("exact_phrase"):
        reasons.append("exact phrase")
    if components.get("matched_aliases"):
        reasons.append("semantic alias")
    if components.get("matched_keywords"):
        reasons.append("keyword")
    if components.get("business_domain"):
        reasons.append("business domain")
    if components.get("conversation_context"):
        reasons.append("conversation context")
    if components.get("business_stage"):
        reasons.append("business stage")
    if components.get("memory_tag"):
        reasons.append("memory tag")
    if not reasons:
        return "No strong business skill match."
    return f"Matched {', '.join(reasons)} for {skill.get('skill_id') or 'skill'}."


def rank_business_skills(
    user_message: str,
    conversation_context: dict | None,
    candidate_skills: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
    limit: int | None = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Rank candidate business skills without depending on the caller's retrieval strategy."""
    if not user_message or not candidate_skills:
        return []

    ranked = []
    for index, skill in enumerate(candidate_skills):
        if not isinstance(skill, dict):
            continue
        components = _component_scores(user_message, conversation_context, skill)
        score = _weighted_score(components)
        confidence = _confidence(score, components)
        if confidence <= 0.0:
            continue
        ranked.append(
            {
                "skill_id": skill.get("skill_id") or "",
                "score": confidence,
                "reason": _reason(skill, components),
                "matched_keywords": components["matched_keywords"],
                "matched_aliases": components["matched_aliases"],
                "confidence": confidence,
                "components": {
                    name: round(float(components.get(name) or 0.0), 2)
                    for name in WEIGHTS
                },
                "candidate_index": index,
            }
        )

    ranked.sort(
        key=lambda item: (
            -float(item.get("score") or 0.0),
            str(item.get("skill_id") or ""),
            int(item.get("candidate_index") or 0),
        )
    )
    for item in ranked:
        item.pop("candidate_index", None)
    if limit is None:
        return ranked
    return ranked[: max(0, int(limit))]


def top_business_skill_match(
    user_message: str,
    conversation_context: dict | None,
    candidate_skills: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
) -> dict[str, Any] | None:
    ranked = rank_business_skills(user_message, conversation_context, candidate_skills, limit=1)
    return ranked[0] if ranked else None
