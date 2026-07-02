from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
import hashlib
import json
import re
from typing import Any

from brain.authority_models import (
    AUTHORITY_CONTEXT_VERSION,
    CUSTOMER_SERVICE_AUTHORITY,
    FINANCE_AUTHORITY,
    GENERAL_BUSINESS_AUTHORITY,
    INVENTORY_AUTHORITY,
    MARKETING_AUTHORITY,
    PRICING_AUTHORITY,
    SALES_AUTHORITY,
    AuthorityContext,
)


AUTHORITY_ENGINE_SOURCE = "authority_engine"

AUTHORITY_DIAGNOSTICS = {
    "authority_context_created": True,
    "authority_version": AUTHORITY_CONTEXT_VERSION,
    "runtime_mode": "diagnostics_only",
    "routes_changed": False,
    "planner_output_changed": False,
    "workflow_changed": False,
    "responses_changed": False,
    "commit_boundary_changed": False,
    "authority_selected_by": AUTHORITY_ENGINE_SOURCE,
    "workflow_decided_authority": False,
}

AUTHORITY_KEYWORDS = {
    PRICING_AUTHORITY: (
        "price",
        "pricing",
        "expensive",
        "discount",
        "margin",
        "too expensive",
        "set price",
        "how much",
        "ลดราคา",
        "แพง",
        "ราคา",
    ),
    SALES_AUTHORITY: (
        "sales",
        "sell",
        "revenue",
        "order",
        "closing",
        "close sale",
        "increase sales",
        "ขาย",
        "ยอดขาย",
        "ออเดอร์",
    ),
    CUSTOMER_SERVICE_AUTHORITY: (
        "customer",
        "complaint",
        "reply",
        "service",
        "respond",
        "refund",
        "ลูกค้า",
        "ร้องเรียน",
        "ตอบ",
        "บริการ",
    ),
    INVENTORY_AUTHORITY: (
        "stock",
        "inventory",
        "warehouse",
        "shortage",
        "out of stock",
        "สินค้าคงคลัง",
        "สต็อก",
        "ของขาด",
    ),
    FINANCE_AUTHORITY: (
        "cost",
        "profit",
        "cash",
        "accounting",
        "finance",
        "cash flow",
        "expense",
        "ต้นทุน",
        "กำไร",
        "เงินสด",
        "บัญชี",
    ),
    MARKETING_AUTHORITY: (
        "content",
        "campaign",
        "ad",
        "ads",
        "marketing",
        "promotion",
        "facebook post",
        "caption",
        "คอนเทนต์",
        "แคมเปญ",
        "โฆษณา",
        "การตลาด",
        "โปรโมชัน",
        "โพสต์",
    ),
}


def _as_dict(value: Any) -> dict:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return deepcopy(value)
    return {}


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _stable_id(prefix: str, payload: dict) -> str:
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _flatten_text(value: Any) -> list[str]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, dict):
        texts: list[str] = []
        for key in sorted(value.keys(), key=str):
            if key == "authority_diagnostics":
                continue
            texts.extend(_flatten_text(value.get(key)))
        return texts
    if isinstance(value, (list, tuple, set)):
        texts = []
        for item in value:
            texts.extend(_flatten_text(item))
        return texts
    return [str(value)]


def _keyword_count(text: str, keywords: tuple[str, ...]) -> tuple[int, list[str]]:
    matched = []
    for keyword in keywords:
        normalized = str(keyword or "").strip().lower()
        if not normalized:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text) or normalized in text:
            matched.append(keyword)
    return len(matched), matched


def _score_authorities(search_text: str) -> dict[str, dict[str, Any]]:
    scores = {}
    for authority, keywords in AUTHORITY_KEYWORDS.items():
        count, matched = _keyword_count(search_text, keywords)
        if count:
            scores[authority] = {
                "score": count,
                "matched_keywords": matched,
            }
    return scores


def _select_primary(scores: dict[str, dict[str, Any]]) -> tuple[str, str, list[str]]:
    if not scores:
        return GENERAL_BUSINESS_AUTHORITY, "low", []

    ranked = sorted(
        scores.items(),
        key=lambda item: (-int(item[1].get("score") or 0), item[0]),
    )
    top_score = int(ranked[0][1].get("score") or 0)
    tied = [authority for authority, payload in ranked if int(payload.get("score") or 0) == top_score]
    if len(tied) > 1:
        return GENERAL_BUSINESS_AUTHORITY, "conflicted", tied
    if top_score >= 2:
        return ranked[0][0], "high", []
    return ranked[0][0], "medium", []


def _secondary_authorities(
    primary_authority: str,
    scores: dict[str, dict[str, Any]],
    conflicts: list[str],
) -> list[str]:
    if conflicts:
        return sorted(conflicts)
    return [
        authority
        for authority, _payload in sorted(
            scores.items(),
            key=lambda item: (-int(item[1].get("score") or 0), item[0]),
        )
        if authority != primary_authority
    ]


def build_authority_context(
    business_situation,
    route_context=None,
    planner_context=None,
    knowledge_context=None,
    reasoning_context=None,
    memory_context=None,
) -> AuthorityContext:
    """Build a diagnostics-only AuthorityContext.

    This function is deterministic, does not mutate inputs, does not call an
    LLM, and does not affect routing, planning, workflow, response, or commit
    behavior.
    """

    situation = _as_dict(business_situation)
    route = _as_dict(route_context)
    planner = _as_dict(planner_context)
    knowledge = _as_dict(knowledge_context)
    reasoning = _as_dict(reasoning_context)
    memory = _as_dict(memory_context)

    business_situation_id = str(situation.get("situation_id") or "")
    text_payload = {
        "business_situation": situation,
        "route_context": route,
        "planner_context": planner,
        "knowledge_context": knowledge,
        "reasoning_context": reasoning,
        "memory_context": memory,
    }
    search_text = " ".join(_flatten_text(text_payload)).lower()
    scores = _score_authorities(search_text)
    primary, confidence, conflict_authorities = _select_primary(scores)
    secondaries = _secondary_authorities(primary, scores, conflict_authorities)
    conflicts = [
        {
            "kind": "authority_conflict",
            "authorities": conflict_authorities,
            "reason": "Multiple authorities had the same strongest heuristic score.",
        }
    ] if conflict_authorities else []

    authority_path = []
    for authority, payload in sorted(
        scores.items(),
        key=lambda item: (-int(item[1].get("score") or 0), item[0]),
    ):
        authority_path.append(
            {
                "source": AUTHORITY_ENGINE_SOURCE,
                "signal": "keyword_match",
                "authority": authority,
                "score": payload.get("score"),
                "matched_keywords": list(payload.get("matched_keywords") or []),
            }
        )
    if not authority_path:
        authority_path.append(
            {
                "source": AUTHORITY_ENGINE_SOURCE,
                "signal": "fallback",
                "authority": GENERAL_BUSINESS_AUTHORITY,
                "score": 0,
                "matched_keywords": [],
            }
        )

    id_payload = {
        "business_situation_id": business_situation_id,
        "primary_authority": primary,
        "secondary_authorities": secondaries,
        "authority_confidence": confidence,
        "authority_path": authority_path,
        "conflicts": conflicts,
    }
    authority_context_id = _stable_id("authority_context", id_payload)

    return AuthorityContext(
        authority_context_id=authority_context_id,
        business_situation_id=business_situation_id,
        primary_authority=primary,
        secondary_authorities=secondaries,
        authority_resolution={
            "selected_authority": primary,
            "selection_method": "conservative_keyword_heuristic",
            "fallback_used": primary == GENERAL_BUSINESS_AUTHORITY and not conflict_authorities,
            "scored_authorities": deepcopy(scores),
        },
        authority_confidence=confidence,
        authority_path=authority_path,
        authority_diagnostics=deepcopy(AUTHORITY_DIAGNOSTICS),
        assumptions=[
            "AuthorityContext is diagnostics-only in V5.4.1 Commit 1.",
            "Authority does not change routing, planner, workflow, response, or commit behavior.",
            "Workflow is not allowed to decide authority.",
        ],
        conflicts=conflicts,
        version=AUTHORITY_CONTEXT_VERSION,
    )
