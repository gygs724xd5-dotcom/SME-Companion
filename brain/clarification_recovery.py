from __future__ import annotations

from dataclasses import asdict, dataclass, field


CLARIFICATION_RECOVERY_VERSION = "5.9.4"


@dataclass
class ClarificationRecoveryResult:
    prior_handoff_id: str = ""
    user_response_type: str = "UNKNOWN"
    resolved_gap_ids: list[str] = field(default_factory=list)
    unresolved_gap_ids: list[str] = field(default_factory=list)
    new_conflicts: list[dict] = field(default_factory=list)
    topic_changed: bool = False
    retry_allowed: bool = True
    retry_count: int = 0
    next_action: str = "ASK_CLARIFICATION"

    def to_dict(self) -> dict:
        return asdict(self)


def recover_from_clarification(prior_handoff: dict | None, follow_up: dict | None, *, retry_count: int = 0, topic_changed: bool = False, max_same_gap_attempts: int = 2) -> dict:
    prior_handoff = prior_handoff or {}
    follow_up = follow_up or {}
    status = follow_up.get("answer_status") or "UNKNOWN"
    gap_id = prior_handoff.get("source_gap_id") or follow_up.get("matched_gap_id") or follow_up.get("matched_metric_id") or ""
    resolved = [gap_id] if status == "ANSWERED" and gap_id else []
    unresolved = [] if resolved else [gap_id] if gap_id else []
    retry_allowed = retry_count < max_same_gap_attempts and status not in {"USER_DECLINED", "ANSWERED"} and not topic_changed
    if topic_changed:
        next_action = "SUPERSEDE_HANDOFF"
    elif status == "USER_DECLINED":
        next_action = "MARK_GAP_DECLINED"
    elif resolved:
        next_action = "ADVANCE_GAP"
    elif retry_allowed:
        next_action = "REPHRASE_WITH_OPTIONS" if retry_count == 1 else "ASK_CLARIFICATION"
    else:
        next_action = "DEFER_GAP_USE_LIMITED_OUTCOME"
    return ClarificationRecoveryResult(
        prior_handoff_id=prior_handoff.get("handoff_id") or "",
        user_response_type="DIRECT_ANSWER" if status == "ANSWERED" else "PARTIAL_ANSWER" if status == "PARTIALLY_ANSWERED" else "AMBIGUOUS_ANSWER" if status == "AMBIGUOUS" else "REFUSAL" if status == "USER_DECLINED" else "TOPIC_SWITCH" if topic_changed else "UNKNOWN",
        resolved_gap_ids=resolved,
        unresolved_gap_ids=unresolved,
        topic_changed=topic_changed,
        retry_allowed=retry_allowed,
        retry_count=retry_count,
        next_action=next_action,
    ).to_dict()
