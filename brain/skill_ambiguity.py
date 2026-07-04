from __future__ import annotations

from dataclasses import asdict, dataclass, field


SKILL_AMBIGUITY_VERSION = "5.9.4"


@dataclass
class SkillAmbiguityResult:
    ambiguity_detected: bool = False
    competing_skill_ids: list[str] = field(default_factory=list)
    ambiguity_dimensions: list[str] = field(default_factory=list)
    score_gap: float = 1.0
    decisive_evidence_missing: list[str] = field(default_factory=list)
    clarification_required: bool = False
    clarification_focus: str = ""
    safe_fallback: str = "NO_CONFIDENT_PRIMARY"
    status: str = "PRIMARY_SELECTED"

    def to_dict(self) -> dict:
        return asdict(self)


def assess_skill_ambiguity(candidates: list[dict], *, user_message: str = "") -> dict:
    active = [item for item in candidates if item.get("selection_tier") in {"PRIMARY_CANDIDATE", "SECONDARY_CANDIDATE"} and not item.get("excluded_reason")]
    active = sorted(active, key=lambda item: -float(item.get("support_strength") or 0.0))
    compact = "".join(str(user_message or "").lower().split())
    broad_sales = any(token in compact for token in ["ยอดขายไม่ดี", "salesbad", "salesnotgood"])
    if len(active) < 2 and not broad_sales:
        return SkillAmbiguityResult(status="PRIMARY_SELECTED" if active else "NO_CONFIDENT_PRIMARY").to_dict()
    top = float(active[0].get("support_strength") or 0.0) if active else 0.0
    second = float(active[1].get("support_strength") or top) if len(active) > 1 else top
    gap = round(abs(top - second), 3)
    ambiguous = broad_sales
    competing = [item.get("skill_id") for item in active[:4] if item.get("skill_id")]
    if broad_sales and "analyze_sales_decline" not in competing:
        competing.insert(0, "analyze_sales_decline")
    if broad_sales and "evaluate_sales_funnel" not in competing:
        competing.append("evaluate_sales_funnel")
    return SkillAmbiguityResult(
        ambiguity_detected=ambiguous,
        competing_skill_ids=competing,
        ambiguity_dimensions=["INTENT_AMBIGUITY", "EVIDENCE_AMBIGUITY"] if ambiguous else [],
        score_gap=gap,
        decisive_evidence_missing=["traffic_count", "conversion_rate", "repeat_purchase_rate"] if ambiguous else [],
        clarification_required=ambiguous,
        clarification_focus="traffic vs conversion vs repeat purchase" if ambiguous else "",
        safe_fallback="STRUCTURED_CLARIFICATION" if ambiguous else "PRIMARY_SELECTED",
        status="NO_CONFIDENT_PRIMARY" if ambiguous else "PRIMARY_SELECTED",
    ).to_dict()
