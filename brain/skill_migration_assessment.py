from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


SKILL_MIGRATION_ASSESSMENT_VERSION = "5.9.3"


class MigrationStrategy(str, Enum):
    MIGRATE = "MIGRATE"
    WRAP = "WRAP"
    SPLIT = "SPLIT"
    REPLACE = "REPLACE"
    DEPRECATE = "DEPRECATE"
    DEFER = "DEFER"


class AuthorityPurity(str, Enum):
    PURE = "PURE"
    MOSTLY_PURE = "MOSTLY_PURE"
    MIXED = "MIXED"
    MULTI_AUTHORITY = "MULTI_AUTHORITY"
    UNSAFE = "UNSAFE"


@dataclass
class SkillMigrationAssessment:
    legacy_skill_id: str
    source_path: str
    current_classification: str = "LEGACY_SKILL"
    current_intents: list[str] = field(default_factory=list)
    current_procedural_roles: list[str] = field(default_factory=list)
    current_authority_claims: list[str] = field(default_factory=list)
    detected_knowledge_domains: list[str] = field(default_factory=list)
    detected_metrics: list[str] = field(default_factory=list)
    detected_workflows: list[str] = field(default_factory=list)
    detected_tools: list[str] = field(default_factory=list)
    definition_conflicts: list[str] = field(default_factory=list)
    authority_conflicts: list[str] = field(default_factory=list)
    duplicate_candidates: list[str] = field(default_factory=list)
    migration_strategy: str = MigrationStrategy.DEFER.value
    canonical_target_ids: list[str] = field(default_factory=list)
    migration_priority: str = "LOW"
    estimated_complexity: str = "LOW"
    blocking_issues: list[str] = field(default_factory=list)
    required_review: bool = True
    recommendation_reason: str = ""
    authority_purity: str = AuthorityPurity.MIXED.value

    def to_dict(self) -> dict:
        return asdict(self)


METRIC_MAPPING = {
    "price": {"canonical_id": "selling_price", "status": "MAPPED"},
    "cost": {"canonical_id": "unit_cost", "status": "MAPPED"},
    "selling_price": {"canonical_id": "selling_price", "status": "MAPPED"},
    "unit_cost": {"canonical_id": "unit_cost", "status": "MAPPED"},
    "profit": {"canonical_id": "", "status": "MAPPING_REQUIRES_REVIEW", "possible_meanings": ["unit_profit", "contribution_margin", "gross_profit", "net_profit"]},
}

INTENT_MAPPING = {
    "calculate_cost": ["structure_unit_cost_inputs", "calculate_product_margin"],
    "calculate_profit": ["calculate_product_margin"],
    "plan_sales": ["analyze_sales_decline", "evaluate_sales_funnel", "future_build_sales_plan"],
    "dashboard": ["identify_dashboard_metrics", "define_dashboard_requirements", "future_build_dashboard"],
}


def map_legacy_metric(metric_id: str) -> dict:
    return dict(METRIC_MAPPING.get(str(metric_id), {"canonical_id": "", "status": "UNKNOWN_METRIC"}))


def map_legacy_intent(intent_id: str) -> list[str]:
    return list(INTENT_MAPPING.get(str(intent_id), []))


def _read(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""


def _contains(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def assess_legacy_skill(path: str | Path) -> dict:
    source = Path(path)
    skill_id = source.stem
    text = _read(str(source))
    intents: list[str] = []
    roles: list[str] = []
    authority_claims: list[str] = []
    metrics: list[str] = []
    workflows: list[str] = []
    tools: list[str] = []
    domains: list[str] = []
    if skill_id == "cost_calculation" or _contains(text, ["cost", "price", "profit", "margin"]):
        intents.extend(["calculate_cost", "calculate_profit"])
        roles.extend(["METRIC_CALCULATION", "EVIDENCE_STRUCTURING"])
        domains.extend(["UNIT_ECONOMICS", "PROFITABILITY_STRUCTURE"])
        metrics.extend(["price", "cost", "profit"])
        workflows.append("PROFIT_CALCULATION")
    if skill_id == "sales_planning" or _contains(text, ["sales", "campaign", "target", "plan"]):
        intents.append("plan_sales")
        roles.extend(["ANALYSIS_PREPARATION", "PLANNING_SUPPORT"])
        domains.extend(["SALES_FUNNEL", "CUSTOMER_RETENTION"])
    if skill_id == "dashboard_builder" or _contains(text, ["dashboard", "metric", "report"]):
        intents.append("dashboard")
        roles.extend(["EVIDENCE_STRUCTURING", "EXECUTION_SUPPORT"])
        domains.extend(["DASHBOARD_METRICS"])
        tools.append("dashboard_builder")
    if skill_id == "receipt_capture":
        roles.append("WORKFLOW_SUPPORT")
        tools.append("ocr")
    if skill_id == "developer_feedback":
        roles.append("DEVELOPER_DIAGNOSTIC")
    if _contains(text, ["recommend", "final decision", "best action", "create plan", "execute", "write to memory"]):
        authority_claims.append("decision_or_execution_language")
    if _contains(text, ["recommend", "campaign", "plan"]):
        authority_claims.append("planning_or_recommendation_language")
    if _contains(text, ["execute", "tool", "dashboard", "ocr"]):
        authority_claims.append("tool_or_workflow_language")
    strategy = MigrationStrategy.DEFER.value
    rollout = "DIAGNOSTIC_ONLY"
    targets: list[str] = []
    priority = "LOW"
    complexity = "LOW"
    purity = AuthorityPurity.MIXED.value
    blocking: list[str] = []
    if skill_id == "cost_calculation":
        strategy = MigrationStrategy.MIGRATE.value
        rollout = "CANONICAL_PREFERRED"
        targets = ["calculate_product_margin", "structure_unit_cost_inputs"]
        priority = "HIGH"
        purity = AuthorityPurity.MOSTLY_PURE.value
        blocking.append("workflow_retains_profit_calculation_ownership")
    elif skill_id == "sales_planning":
        strategy = MigrationStrategy.SPLIT.value
        rollout = "SHADOW_CANONICAL"
        targets = ["analyze_sales_decline", "evaluate_sales_funnel"]
        priority = "HIGH"
        complexity = "HIGH"
        purity = AuthorityPurity.MULTI_AUTHORITY.value
        blocking.append("downstream_planning_deferred")
    elif skill_id == "dashboard_builder":
        strategy = MigrationStrategy.SPLIT.value
        rollout = "SHADOW_CANONICAL"
        targets = ["identify_dashboard_metrics", "define_dashboard_requirements"]
        priority = "MEDIUM"
        complexity = "MEDIUM"
        purity = AuthorityPurity.MULTI_AUTHORITY.value
        blocking.append("dashboard_execution_not_bridge_owned")
    elif skill_id in {"marketing", "content_creation"}:
        strategy = MigrationStrategy.DEFER.value
        rollout = "DIAGNOSTIC_ONLY"
        blocking.append("canonical_knowledge_support_incomplete")
    elif skill_id == "receipt_capture":
        strategy = MigrationStrategy.WRAP.value
        rollout = "DIAGNOSTIC_ONLY"
        blocking.append("execution_boundary_required")
    elif skill_id == "developer_feedback":
        strategy = MigrationStrategy.DEFER.value
        rollout = "LEGACY_UNCHANGED"
        blocking.append("developer_diagnostic_not_business_skill")
    if "decision_or_execution_language" in authority_claims:
        purity = AuthorityPurity.UNSAFE.value if skill_id not in {"cost_calculation"} else purity
    assessment = SkillMigrationAssessment(
        legacy_skill_id=skill_id,
        source_path=str(source),
        current_intents=sorted(set(intents)),
        current_procedural_roles=sorted(set(roles)),
        current_authority_claims=sorted(set(authority_claims)),
        detected_knowledge_domains=sorted(set(domains)),
        detected_metrics=sorted(set(metrics)),
        detected_workflows=sorted(set(workflows)),
        detected_tools=sorted(set(tools)),
        authority_conflicts=sorted(set(authority_claims)),
        duplicate_candidates=targets,
        migration_strategy=strategy,
        canonical_target_ids=targets,
        migration_priority=priority,
        estimated_complexity=complexity,
        blocking_issues=blocking,
        required_review=True,
        recommendation_reason=f"{skill_id} rollout mode: {rollout}",
        authority_purity=purity.value if hasattr(purity, "value") else str(purity),
    ).to_dict()
    assessment["canonical_rollout_mode"] = rollout
    return assessment
