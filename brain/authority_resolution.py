from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

from brain.authority_models import (
    AUTHORITY_NAMES,
    GENERAL_BUSINESS_AUTHORITY,
)


AUTHORITY_RESOLUTION_VERSION = "5.4.3"
AUTHORITY_RESOLUTION_SOURCE = "authority_resolution"
LOW_CONFIDENCE_SCORE = 0
HIGH_CONFIDENCE_SCORE = 2
NEAR_EQUAL_SCORE_DELTA = 1


@dataclass(frozen=True)
class AuthorityResolution:
    primary_authority: str = GENERAL_BUSINESS_AUTHORITY
    secondary_authorities: list = field(default_factory=list)
    confidence: str = "low"
    reason: str = ""
    assumptions: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    resolution_path: list = field(default_factory=list)
    version: str = AUTHORITY_RESOLUTION_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


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


def _candidate_items(candidates: Any) -> list[dict]:
    if candidates is None:
        return []
    if isinstance(candidates, dict):
        return [
            {
                "authority": authority,
                **_as_dict(payload),
            }
            for authority, payload in candidates.items()
        ]
    if isinstance(candidates, (list, tuple)):
        return [_as_dict(candidate) for candidate in candidates]
    return []


def _score(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_candidates(candidates: Any) -> list[dict]:
    normalized = []
    for index, candidate in enumerate(_candidate_items(candidates)):
        authority = str(
            candidate.get("authority")
            or candidate.get("authority_id")
            or candidate.get("primary_authority")
            or ""
        )
        score = _score(candidate.get("score"))
        is_known = authority in AUTHORITY_NAMES
        normalized.append(
            {
                "authority": authority,
                "score": score,
                "matched_keywords": list(candidate.get("matched_keywords") or []),
                "source": str(candidate.get("source") or AUTHORITY_RESOLUTION_SOURCE),
                "signal": str(candidate.get("signal") or "authority_candidate"),
                "valid": bool(is_known and score > LOW_CONFIDENCE_SCORE),
                "ignored": not is_known,
                "input_order": index,
            }
        )
    return sorted(
        normalized,
        key=lambda item: (
            -int(item.get("score") or 0),
            str(item.get("authority") or ""),
            int(item.get("input_order") or 0),
        ),
    )


def _resolution_path(candidates: list[dict]) -> list[dict]:
    return [
        {
            "source": candidate["source"],
            "signal": candidate["signal"],
            "authority": candidate["authority"],
            "score": candidate["score"],
            "matched_keywords": list(candidate.get("matched_keywords") or []),
            "valid": candidate["valid"],
            "ignored": candidate["ignored"],
        }
        for candidate in candidates
    ]


def _fallback_resolution(candidates: list[dict], reason: str) -> AuthorityResolution:
    path = _resolution_path(candidates)
    if not path:
        path = [
            {
                "source": AUTHORITY_RESOLUTION_SOURCE,
                "signal": "fallback",
                "authority": GENERAL_BUSINESS_AUTHORITY,
                "score": 0,
                "matched_keywords": [],
                "valid": True,
                "ignored": False,
            }
        ]

    return AuthorityResolution(
        primary_authority=GENERAL_BUSINESS_AUTHORITY,
        secondary_authorities=[],
        confidence="low",
        reason=reason,
        assumptions=[
            "Authority Resolution is diagnostics-only in V5.4.3.",
            "Unknown authority candidates are ignored without changing runtime behavior.",
        ],
        conflicts=[],
        resolution_path=path,
    )


def resolve_authority(candidates, business_situation=None) -> AuthorityResolution:
    """Resolve candidate authorities into one deterministic authority result."""

    del business_situation

    normalized = _normalize_candidates(candidates)
    valid_candidates = [
        candidate
        for candidate in normalized
        if candidate["valid"]
    ]
    if not valid_candidates:
        return _fallback_resolution(
            normalized,
            "No valid authority candidate exceeded the low-confidence threshold.",
        )

    top_score = int(valid_candidates[0].get("score") or 0)
    tied = [
        candidate
        for candidate in valid_candidates
        if int(candidate.get("score") or 0) == top_score
    ]
    near_equal = [
        candidate
        for candidate in valid_candidates
        if 0 <= top_score - int(candidate.get("score") or 0) <= NEAR_EQUAL_SCORE_DELTA
    ]

    conflicts = []
    if len(near_equal) > 1:
        conflicts.append(
            {
                "kind": "authority_conflict",
                "authorities": [candidate["authority"] for candidate in near_equal],
                "reason": "Multiple authorities had nearly equal heuristic scores.",
            }
        )

    if len(tied) > 1:
        return AuthorityResolution(
            primary_authority=GENERAL_BUSINESS_AUTHORITY,
            secondary_authorities=sorted(candidate["authority"] for candidate in tied),
            confidence="conflicted",
            reason="Multiple authorities had the same strongest heuristic score.",
            assumptions=[
                "Authority Resolution is diagnostics-only in V5.4.3.",
                "Tie handling is deterministic and conservative.",
            ],
            conflicts=[
                {
                    "kind": "authority_conflict",
                    "authorities": sorted(candidate["authority"] for candidate in tied),
                    "reason": "Multiple authorities had the same strongest heuristic score.",
                }
            ],
            resolution_path=_resolution_path(normalized),
        )

    primary = valid_candidates[0]["authority"]
    secondary = [
        candidate["authority"]
        for candidate in valid_candidates
        if candidate["authority"] != primary
    ]
    confidence = "high" if top_score >= HIGH_CONFIDENCE_SCORE else "medium"

    return AuthorityResolution(
        primary_authority=primary,
        secondary_authorities=secondary,
        confidence=confidence,
        reason="Highest scoring valid authority candidate selected.",
        assumptions=[
            "Authority Resolution is diagnostics-only in V5.4.3.",
            "Authority Resolution does not route workflow, planner, knowledge, or response behavior.",
        ],
        conflicts=conflicts,
        resolution_path=_resolution_path(normalized),
    )
