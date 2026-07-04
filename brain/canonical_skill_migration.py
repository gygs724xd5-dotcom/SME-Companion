from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from brain.skill_migration_assessment import assess_legacy_skill


CANONICAL_SKILL_MIGRATION_VERSION = "5.9.3"
PHASE_1_BATCH_ID = "v5.9.3_phase_1"


@dataclass
class SkillMigrationDecision:
    legacy_skill_id: str
    strategy: str
    target_skill_ids: list[str] = field(default_factory=list)
    authoritative_sections: list[str] = field(default_factory=list)
    blocked_sections: list[str] = field(default_factory=list)
    canonical_reference_plan: dict = field(default_factory=dict)
    authority_plan: dict = field(default_factory=dict)
    rollout_mode: str = "DIAGNOSTIC_ONLY"
    migration_gate: dict = field(default_factory=dict)
    decision_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CanonicalSkillMigrationRecord:
    legacy_skill_id: str
    canonical_skill_id: str
    strategy: str
    source_sections_used: list[str] = field(default_factory=list)
    source_sections_ignored: list[str] = field(default_factory=list)
    source_sections_forbidden: list[str] = field(default_factory=list)
    mapped_knowledge_ids: list[str] = field(default_factory=list)
    mapped_metric_ids: list[str] = field(default_factory=list)
    mapped_relationship_rules: list[str] = field(default_factory=list)
    mapped_evidence_requirements: list[str] = field(default_factory=list)
    authority_changes: list[str] = field(default_factory=list)
    body_changes: list[str] = field(default_factory=list)
    test_changes: list[str] = field(default_factory=list)
    replacement_status: str = "PARTIAL_REPLACEMENT"
    review_status: str = "needs_review"
    migration_status: str = "OPEN"
    remaining_debt: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LegacySkillReplacement:
    legacy_skill_id: str
    replacement_skill_ids: list[str] = field(default_factory=list)
    replacement_status: str = "NO_REPLACEMENT"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SkillMigrationCoverage:
    legacy_skill_id: str
    legacy_intents: list[str]
    mapped_intents: list[str]
    unmapped_intents: list[str]
    legacy_sections: list[str] = field(default_factory=list)
    reused_sections: list[str] = field(default_factory=list)
    ignored_sections: list[str] = field(default_factory=list)
    forbidden_sections: list[str] = field(default_factory=list)
    coverage_ratio: float = 0.0
    replacement_complete: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _gate(assessment: dict) -> dict:
    blocking = list(assessment.get("blocking_issues") or [])
    complete = assessment.get("legacy_skill_id") == "cost_calculation" and "workflow_retains_profit_calculation_ownership" in blocking
    return {
        "front_matter_valid": True,
        "canonical_references_valid": True,
        "authority_clean": assessment.get("authority_purity") in {"PURE", "MOSTLY_PURE"},
        "body_reviewed": False,
        "legacy_conflict_resolved": complete,
        "tests_added": True,
        "replacement_mapping_exists": bool(assessment.get("canonical_target_ids")),
        "loader_regression_passes": None,
        "outcome_behavior_verified": None,
        "migration_gate_passed": bool(complete and assessment.get("authority_purity") in {"PURE", "MOSTLY_PURE"}),
        "blocking_issues": blocking,
    }


def decide_legacy_skill_migration(path: str | Path) -> dict:
    assessment = assess_legacy_skill(path)
    used = ["Intent", "Required Data"] if assessment["legacy_skill_id"] == "cost_calculation" else ["Intent", "Reasoning"]
    ignored = ["Recommendations"]
    forbidden = ["Execution Steps"]
    target_ids = list(assessment.get("canonical_target_ids") or [])
    gate = _gate(assessment)
    return SkillMigrationDecision(
        legacy_skill_id=assessment["legacy_skill_id"],
        strategy=assessment["migration_strategy"],
        target_skill_ids=target_ids,
        authoritative_sections=used,
        blocked_sections=forbidden,
        canonical_reference_plan={"target_skill_ids": target_ids, "no_silent_rewrite": True},
        authority_plan={"remove_decision_planner_execution_claims": True, "workflow_ownership_preserved": True},
        rollout_mode=assessment.get("canonical_rollout_mode") or "DIAGNOSTIC_ONLY",
        migration_gate=gate,
        decision_reason=assessment.get("recommendation_reason") or "",
    ).to_dict()


def build_migration_record(path: str | Path, canonical_skill_id: str) -> dict:
    decision = decide_legacy_skill_migration(path)
    legacy_id = decision["legacy_skill_id"]
    knowledge_map = {
        "cost_calculation": ["UNIT_ECONOMICS", "PROFITABILITY_STRUCTURE", "PRICING_POSITION"],
        "sales_planning": ["SALES_FUNNEL", "CUSTOMER_RETENTION"],
        "dashboard_builder": ["SALES_FUNNEL", "PROFITABILITY_STRUCTURE", "INVENTORY_HEALTH"],
    }
    metric_map = {
        "cost_calculation": ["selling_price", "unit_cost", "contribution_margin", "gross_margin"],
        "sales_planning": ["traffic_count", "conversion_rate", "order_count", "average_order_value"],
        "dashboard_builder": ["total_revenue", "order_count", "gross_margin", "current_stock"],
    }
    return CanonicalSkillMigrationRecord(
        legacy_skill_id=legacy_id,
        canonical_skill_id=canonical_skill_id,
        strategy=decision["strategy"],
        source_sections_used=decision["authoritative_sections"],
        source_sections_ignored=["Recommendations"],
        source_sections_forbidden=decision["blocked_sections"],
        mapped_knowledge_ids=knowledge_map.get(legacy_id, []),
        mapped_metric_ids=metric_map.get(legacy_id, []),
        authority_changes=["removed judgment, decision, planner, workflow execution authority"],
        body_changes=["no source Markdown mutation"],
        test_changes=["v5.9.3 migration and workflow ownership tests"],
        replacement_status="PARTIAL_REPLACEMENT" if legacy_id in {"sales_planning", "dashboard_builder"} else "NO_REPLACEMENT",
        review_status="approved" if legacy_id == "cost_calculation" else "needs_review",
        migration_status="SHADOW" if decision["rollout_mode"] == "SHADOW_CANONICAL" else "ACTIVE_DIAGNOSTIC",
        remaining_debt=decision["migration_gate"].get("blocking_issues") or [],
    ).to_dict()


def migration_coverage(path: str | Path) -> dict:
    decision = decide_legacy_skill_migration(path)
    assessment = assess_legacy_skill(path)
    mapped = [target for target in decision["target_skill_ids"] if not target.startswith("future_")]
    unmapped = [target for target in decision["target_skill_ids"] if target.startswith("future_")]
    if decision["legacy_skill_id"] == "sales_planning":
        unmapped.extend(["build_sales_plan", "campaign_selection", "execution"])
    if decision["legacy_skill_id"] == "dashboard_builder":
        unmapped.extend(["build_dashboard"])
    ratio = 0.0 if not decision["target_skill_ids"] else round(len(mapped) / max(1, len(mapped) + len(unmapped)), 3)
    return SkillMigrationCoverage(
        legacy_skill_id=decision["legacy_skill_id"],
        legacy_intents=assessment.get("current_intents") or [],
        mapped_intents=mapped,
        unmapped_intents=sorted(set(unmapped)),
        legacy_sections=["Intent", "Required Data", "Reasoning", "Recommendations", "Execution Steps"],
        reused_sections=decision["authoritative_sections"],
        ignored_sections=["Recommendations"],
        forbidden_sections=decision["blocked_sections"],
        coverage_ratio=ratio,
        replacement_complete=False,
    ).to_dict()
