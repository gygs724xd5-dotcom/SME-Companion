"""Pure V5.15.3 candidate discovery for canonical business skills.

``brain.business_skill_matcher`` is the legacy runtime-era matcher.  This
module is the canonical, registry-backed, current-message-only shadow matcher.
The two systems are intentionally not connected in V5.15.3.

Candidates are diagnostic relevance signals only.  They are not selected,
authorized, executable, reasoning-ready, or permitted to answer a user.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from brain.business_skill import BusinessSkill
from brain.business_skill_registry import (
    BUSINESS_SKILL_REGISTRY_VERSION,
    get_business_skill_registry,
)


BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION = "5.15.3"
DEFAULT_MINIMUM_CANDIDATE_SCORE = 15

_TERM_RE = re.compile(r"[a-z0-9]+|[\u0e00-\u0e7f]+")
_IGNORED_TERMS = {
    "a", "an", "and", "basic", "calculation", "check", "explanation",
    "for", "in", "of", "summary", "the", "to", "triage", "v1",
}


def normalize_candidate_message(message: object) -> str:
    """Normalize text while retaining Thai character sequences for matching."""
    text = unicodedata.normalize("NFKC", str(message or "")).casefold()
    text = "".join(" " if unicodedata.category(char)[0] in {"P", "S"} else char for char in text)
    return " ".join(text.split())


def _terms(value: object) -> tuple[str, ...]:
    return tuple(
        term for term in _TERM_RE.findall(normalize_candidate_message(value))
        if len(term) > 1 and term not in _IGNORED_TERMS
    )


def _valid_skill(skill: object) -> bool:
    return isinstance(skill, BusinessSkill) and bool(
        skill.skill_id.strip()
        and skill.skill_name.strip()
        and skill.business_domain.strip()
        and skill.skill_category.strip()
    )


def score_business_skill_candidate(
    user_message: object,
    skill: BusinessSkill,
    business_domain: object | None = None,
) -> dict | None:
    """Return immutable-source diagnostic data for one relevant canonical skill."""
    message = normalize_candidate_message(user_message)
    if not message or not _valid_skill(skill):
        return None

    score = 0
    matched_intents: list[str] = []
    matched_examples: list[str] = []
    reasons: list[str] = []

    for pattern in skill.intent_patterns:
        normalized = normalize_candidate_message(pattern)
        if not normalized:
            continue
        if message == normalized:
            score += 100
            matched_intents.append(str(pattern))
            reasons.append("exact_intent_pattern")
        elif normalized in message:
            score += 70
            matched_intents.append(str(pattern))
            reasons.append("contained_intent_pattern")

    for example in skill.example_questions:
        normalized = normalize_candidate_message(example)
        if not normalized:
            continue
        if message == normalized:
            score += 90
            matched_examples.append(str(example))
            reasons.append("exact_example_question")
        elif normalized in message or (len(message) >= 6 and message in normalized):
            score += 55
            matched_examples.append(str(example))
            reasons.append("partial_example_question")

    metadata_terms = tuple(dict.fromkeys(_terms(skill.skill_name) + _terms(skill.skill_id)))
    message_terms = set(_terms(message))
    matched_terms = [term for term in metadata_terms if term in message_terms]
    if matched_terms:
        score += 8 * len(matched_terms)
        reasons.append("metadata_term_overlap")

    domain_hint = normalize_candidate_message(business_domain)
    domain_matched = bool(domain_hint and domain_hint == normalize_candidate_message(skill.business_domain))
    # A hint can strengthen real message evidence, never originate it.
    if score and domain_matched:
        score += 12
        reasons.append("explicit_domain_hint")

    if not score:
        return None

    confidence = round(min(0.99, score / (score + 50.0)), 4)
    return {
        "skill_id": skill.skill_id,
        "skill_name": skill.skill_name,
        "business_domain": skill.business_domain,
        "skill_category": skill.skill_category,
        "active_status": skill.active_status,
        "candidate_score": score,
        "candidate_confidence": confidence,
        "candidate_rank": None,
        "matched_intent_patterns": list(matched_intents),
        "matched_example_questions": list(matched_examples),
        "matched_terms": list(matched_terms),
        "domain_hint_matched": domain_matched,
        "candidate_reasons": list(dict.fromkeys(reasons)),
        "candidate_shadow_mode": True,
        "candidate_selected": False,
        "candidate_authorized": False,
        "candidate_reasoning_ready": None,
    }


def _registry_entries(registry: Iterable[BusinessSkill] | None) -> tuple[object, ...]:
    if registry is None:
        return tuple(get_business_skill_registry())
    try:
        return tuple(registry)
    except TypeError:
        return ()


def match_business_skill_candidates(
    user_message: object,
    registry: Iterable[BusinessSkill] | None = None,
    business_domain: object | None = None,
    limit: int | None = 5,
    minimum_score: int | float | None = None,
) -> list[dict]:
    """Rank qualifying candidates; stable sorting preserves registry tie order."""
    if not normalize_candidate_message(user_message) or limit == 0:
        return []
    threshold = DEFAULT_MINIMUM_CANDIDATE_SCORE if minimum_score is None else minimum_score
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        threshold = float(DEFAULT_MINIMUM_CANDIDATE_SCORE)

    candidates = []
    for skill in _registry_entries(registry):
        candidate = score_business_skill_candidate(user_message, skill, business_domain)  # type: ignore[arg-type]
        if candidate is not None and candidate["candidate_score"] >= threshold:
            candidates.append(candidate)
    candidates.sort(key=lambda item: -item["candidate_score"])
    for rank, candidate in enumerate(candidates, 1):
        candidate["candidate_rank"] = rank
    if limit is None:
        return candidates
    try:
        bounded_limit = max(0, int(limit))
    except (TypeError, ValueError):
        bounded_limit = 5
    return candidates[:bounded_limit]


def top_business_skill_candidate(
    user_message: object,
    registry: Iterable[BusinessSkill] | None = None,
    business_domain: object | None = None,
    minimum_score: int | float | None = None,
) -> dict | None:
    candidates = match_business_skill_candidates(
        user_message, registry, business_domain, limit=1, minimum_score=minimum_score
    )
    return candidates[0] if candidates else None


def build_business_skill_candidate_diagnostics(
    user_message: object,
    registry: Iterable[BusinessSkill] | None = None,
    business_domain: object | None = None,
    limit: int | None = 5,
    minimum_score: int | float | None = None,
) -> dict:
    entries = _registry_entries(registry)
    valid_count = sum(1 for skill in entries if _valid_skill(skill))
    candidates = match_business_skill_candidates(
        user_message, entries, business_domain, limit=limit, minimum_score=minimum_score
    )
    top = candidates[0] if candidates else None
    return {
        "normalized_current_message": normalize_candidate_message(user_message),
        "registry_version": BUSINESS_SKILL_REGISTRY_VERSION,
        "matcher_version": BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
        "total_registry_skills_considered": valid_count,
        "invalid_registry_entries": len(entries) - valid_count,
        "qualifying_candidate_count": len(candidates),
        "ranked_candidate_ids": [item["skill_id"] for item in candidates],
        "top_candidate_id": top["skill_id"] if top else None,
        "top_candidate_score": top["candidate_score"] if top else None,
        "domain_hint": normalize_candidate_message(business_domain) or None,
        "shadow_mode": True,
        "selected_skill_id": None,
        "authorized_skill_id": None,
        "matching_boundary": (
            "Current-message-only candidate discovery; candidates are not selected, "
            "authorized, executable, reasoning-ready, or response authority."
        ),
        "candidates": candidates,
    }
