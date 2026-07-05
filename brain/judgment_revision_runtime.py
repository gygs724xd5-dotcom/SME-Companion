from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from brain.business_judgment_runtime import build_business_judgment_runtime
from brain.judgment_contracts import RevisionStatus


JUDGMENT_REVISION_RUNTIME_VERSION = "5.10.3"


@dataclass
class JudgmentRevisionResult:
    previous_judgment_id: str = ""
    current_judgment_id: str = ""
    revision_status: str = RevisionStatus.UNCHANGED.value
    revision_trigger: str = ""
    new_evidence_ids: list[str] = field(default_factory=list)
    removed_evidence_ids: list[str] = field(default_factory=list)
    stale_evidence_ids: list[str] = field(default_factory=list)
    changed_candidate_ids: list[str] = field(default_factory=list)
    previous_selected_candidates: list[str] = field(default_factory=list)
    current_selected_candidates: list[str] = field(default_factory=list)
    previous_confidence: str = ""
    current_confidence: str = ""
    previous_support_strength: str = ""
    current_support_strength: str = ""
    superseded_claims: list = field(default_factory=list)
    preserved_claims: list = field(default_factory=list)
    withdrawn_claims: list = field(default_factory=list)
    contradiction_changes: list = field(default_factory=list)
    revision_reason: str = ""
    user_visible_revision_required: bool = False
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _selected_ids(result: dict) -> list[str]:
    judgment = _as_dict(result.get("selected_judgment"))
    selected = judgment.get("selected_explanation")
    if isinstance(selected, dict) and selected.get("coexisting_candidates"):
        return [item.get("candidate_id") for item in selected.get("coexisting_candidates") if isinstance(item, dict)]
    if isinstance(selected, dict) and selected.get("candidate_id"):
        return [selected.get("candidate_id")]
    return []


def _claim_ids(result: dict) -> list[str]:
    judgment = _as_dict(result.get("selected_judgment"))
    candidates = []
    selected = judgment.get("selected_explanation")
    if isinstance(selected, dict) and selected.get("coexisting_candidates"):
        candidates = selected.get("coexisting_candidates") or []
    elif isinstance(selected, dict):
        candidates = [selected]
    return [f"claim::{item.get('candidate_id')}" for item in candidates if isinstance(item, dict)]


def revise_business_judgment(previous_judgment_result: dict | None, current_judgment_input: dict | None, *, revision_trigger: str = "NEW_SUPPORTING_EVIDENCE") -> dict:
    previous = _as_dict(previous_judgment_result)
    current = build_business_judgment_runtime(current_judgment_input)
    previous_ids = _selected_ids(previous)
    current_ids = _selected_ids(current)
    previous_claims = set(_claim_ids(previous))
    current_claims = set(_claim_ids(current))
    if current.get("judgment_status") == "CONFLICT_BLOCKED":
        status = RevisionStatus.WITHDRAWN.value
    elif not previous_ids and current_ids:
        status = RevisionStatus.REVISED.value
    elif set(previous_ids) == set(current_ids):
        previous_support = previous.get("support_strength")
        current_support = current.get("support_strength")
        status = RevisionStatus.STRENGTHENED.value if current_support == "STRONG" and previous_support != "STRONG" else RevisionStatus.WEAKENED.value if current_support != previous_support else RevisionStatus.UNCHANGED.value
    elif set(previous_ids).issubset(set(current_ids)):
        status = RevisionStatus.EXPANDED.value
    elif set(current_ids).issubset(set(previous_ids)):
        status = RevisionStatus.NARROWED.value
    else:
        status = RevisionStatus.REVISED.value
    result = JudgmentRevisionResult(
        previous_judgment_id=_as_dict(previous.get("selected_judgment")).get("judgment_id") or "",
        current_judgment_id=_as_dict(current.get("selected_judgment")).get("judgment_id") or "",
        revision_status=status,
        revision_trigger=revision_trigger,
        changed_candidate_ids=sorted(set(previous_ids).symmetric_difference(current_ids)),
        previous_selected_candidates=previous_ids,
        current_selected_candidates=current_ids,
        previous_confidence=previous.get("confidence_class") or "",
        current_confidence=current.get("confidence_class") or "",
        previous_support_strength=previous.get("support_strength") or "",
        current_support_strength=current.get("support_strength") or "",
        superseded_claims=sorted(previous_claims - current_claims) if status in {RevisionStatus.SUPERSEDED.value, RevisionStatus.REVISED.value, RevisionStatus.WITHDRAWN.value} else [],
        preserved_claims=sorted(previous_claims.intersection(current_claims)),
        withdrawn_claims=sorted(previous_claims - current_claims) if status in {RevisionStatus.NARROWED.value, RevisionStatus.WITHDRAWN.value} else [],
        contradiction_changes=current.get("contradictions") or [],
        revision_reason=f"{revision_trigger} produced {status}.",
        user_visible_revision_required=status in {RevisionStatus.REVISED.value, RevisionStatus.WITHDRAWN.value, RevisionStatus.EXPANDED.value, RevisionStatus.NARROWED.value, RevisionStatus.WEAKENED.value},
        provenance={"previous": previous, "current": current, "version": JUDGMENT_REVISION_RUNTIME_VERSION},
    )
    return {**result.to_dict(), "current_judgment_result": current, "version": JUDGMENT_REVISION_RUNTIME_VERSION}

