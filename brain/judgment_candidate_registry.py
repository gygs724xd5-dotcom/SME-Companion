from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Iterable

from brain.business_knowledge_registry import BusinessKnowledgeRegistry
from brain.judgment_contracts import (
    BUSINESS_JUDGMENT_VERSION,
    CandidateReviewStatus,
    CandidateRuntimeStatus,
    CandidateSpecificity,
    CausalClaimLevel,
    EvidenceRole,
    JudgmentCandidateConflict,
    JudgmentCandidateDefinition,
    JudgmentEvidenceRule,
    JudgmentType,
)
from brain.perspective_frame_registry import PerspectiveFrameRegistry


JUDGMENT_CANDIDATE_REGISTRY_VERSION = "5.10.1"


@dataclass
class JudgmentCandidateRetrievalResult:
    selected_frame: str
    selected_knowledge_ids: list[str]
    available_candidate_ids: list[str] = field(default_factory=list)
    excluded_candidate_ids: list[str] = field(default_factory=list)
    deferred_candidate_ids: list[str] = field(default_factory=list)
    retrieval_reasons: dict = field(default_factory=dict)
    registry_version: str = JUDGMENT_CANDIDATE_REGISTRY_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _rule(rule_id: str, metrics: list[str], operator: str, direction: str, effect: str = "SUPPORTS") -> JudgmentEvidenceRule:
    return JudgmentEvidenceRule(
        rule_id=rule_id,
        rule_type="METRIC_PATTERN",
        input_metrics=metrics,
        operator=operator,
        expected_direction=direction,
        support_effect=effect,
        claim_limit=CausalClaimLevel.CONTRIBUTING_FACTOR.value,
    )


def _candidate(
    short_id: str,
    name: str,
    domain: str,
    knowledge: list[str],
    metrics: list[str],
    frames: list[str],
    support_rules: list[JudgmentEvidenceRule],
    *,
    relationship_rules: list[str] | None = None,
    optional: list[str] | None = None,
    judgment_type: str = JudgmentType.EXPLANATORY.value,
    review: str = CandidateReviewStatus.APPROVED.value,
    specificity: str = CandidateSpecificity.SPECIFIC.value,
    priority: int = 50,
    forbidden: list[str] | None = None,
    allowed: list[str] | None = None,
) -> JudgmentCandidateDefinition:
    return JudgmentCandidateDefinition(
        candidate_id=f"JUDGMENT::{domain.upper().replace(' ', '_')}::{short_id}",
        display_name=name,
        description=f"Deterministic judgment candidate for {name}.",
        judgment_type=judgment_type,
        business_domain=domain,
        applicable_frames=frames,
        required_knowledge_ids=knowledge,
        supporting_knowledge_ids=knowledge,
        required_relationship_rule_ids=relationship_rules or [],
        required_metric_ids=metrics,
        optional_metric_ids=optional or [],
        supporting_evidence_rules=support_rules,
        contradicting_evidence_rules=[],
        minimum_evidence_coverage=0.6,
        maximum_claim_level=CausalClaimLevel.CONTRIBUTING_FACTOR.value,
        default_status=CandidateRuntimeStatus.AVAILABLE.value,
        misuse_constraints=forbidden or ["Do not produce recommendations.", "Do not claim sole cause."],
        allowed_outputs=allowed or ["observation", "association", "contributing factor", "condition assessment", "risk assessment", "limitation"],
        forbidden_outputs=forbidden or ["sole cause", "recommendation", "Decision", "plan", "execution"],
        provenance=[
            "SME Companion V5.10 canonical Judgment Candidate Registry",
            "Derived from canonical Knowledge, Metric, Relationship Rule, Skill scope, and observed Evidence contracts.",
        ],
        review_status=review,
        specificity=specificity,
        priority=priority,
        version=BUSINESS_JUDGMENT_VERSION,
    )


def _initial_candidates() -> list[JudgmentCandidateDefinition]:
    approved_forbidden = {
        "aov": ["sole cause", "customer quality worsened", "customers became price-sensitive", "price recommendation", "PRIMARY_DRIVER", "CONFIRMED_CAUSE"],
        "unit_cost": ["supplier overcharging", "waste caused the increase", "change supplier", "PRIMARY_DRIVER", "CONFIRMED_CAUSE"],
        "capacity": ["hire staff", "buy equipment", "expand production", "PRIMARY_DRIVER", "CONFIRMED_CAUSE"],
        "stockout": ["reorder quantity", "purchase recommendation", "PRIMARY_DRIVER", "CONFIRMED_CAUSE"],
        "receivable": ["blame customer credit quality", "collection action recommendation", "PRIMARY_DRIVER", "CONFIRMED_CAUSE"],
    }
    candidates = [
        _candidate(
            "AVERAGE_ORDER_VALUE_DECLINE",
            "Average Order Value Decline",
            "PROFITABILITY",
            ["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"],
            ["analysis_timeframe", "order_count", "total_revenue", "average_order_value", "net_profit"],
            ["PROFIT_COMPRESSION", "SALES_DECLINE"],
            [
                _rule("aov_declines_with_profit_decline", ["order_count", "total_revenue", "average_order_value", "net_profit"], "directional_comparison", "aov_down_profit_down"),
            ],
            relationship_rules=["orders_and_revenue_can_diverge_by_aov", "revenue_growth_not_guaranteed_by_profit_growth", "aov_shapes_customer_growth_profit_translation"],
            optional=["discount_rate", "unit_cost", "operating_expenses"],
            priority=100,
            forbidden=approved_forbidden["aov"],
        ),
        _candidate(
            "UNIT_COST_INCREASE",
            "Unit Cost Increase",
            "PROFITABILITY",
            ["UNIT_ECONOMICS", "PROFITABILITY_STRUCTURE"],
            ["unit_cost", "selling_price", "net_profit"],
            ["PROFIT_COMPRESSION", "PRICING_PRESSURE"],
            [_rule("unit_cost_rises_profit_declines", ["unit_cost", "selling_price", "net_profit"], "directional_comparison", "unit_cost_up_profit_down")],
            relationship_rules=["contribution_margin_needs_realized_price_and_variable_cost", "revenue_growth_not_guaranteed_by_profit_growth"],
            priority=95,
            forbidden=approved_forbidden["unit_cost"],
        ),
        _candidate(
            "PROFIT_PER_UNIT_OBSERVATION",
            "Profit Per Unit Observation",
            "PROFITABILITY",
            ["UNIT_ECONOMICS"],
            ["profit_per_unit"],
            ["PROFIT_COMPRESSION", "PRICING_PRESSURE", "GROWTH_OPPORTUNITY"],
            [_rule("workflow_profit_per_unit_calculated", ["profit_per_unit"], "calculated_observation", "calculated")],
            judgment_type=JudgmentType.CONDITION_ASSESSMENT.value,
            priority=70,
            forbidden=["good profit", "bad profit", "price recommendation", "benchmark label without benchmark", "PRIMARY_DRIVER", "CONFIRMED_CAUSE"],
        ),
        _candidate(
            "DEMAND_NEAR_CAPACITY",
            "Demand Near Capacity",
            "CAPACITY",
            ["OPERATING_CAPACITY"],
            ["maximum_capacity", "current_order_volume", "output_time_period"],
            ["DEMAND_SURGE", "CAPACITY_CONSTRAINT", "OPERATIONAL_BOTTLENECK"],
            [_rule("demand_near_capacity_threshold", ["maximum_capacity", "current_order_volume", "output_time_period"], "ratio_threshold", "near_capacity")],
            relationship_rules=["utilization_depends_on_demand_relative_to_capacity", "capacity_requires_time_unit"],
            judgment_type=JudgmentType.CONDITION_ASSESSMENT.value,
            priority=90,
            forbidden=approved_forbidden["capacity"],
        ),
        _candidate(
            "STOCKOUT_EXPOSURE",
            "Stockout Exposure",
            "INVENTORY",
            ["INVENTORY_HEALTH", "SUPPLY_RELIABILITY"],
            ["current_stock", "average_daily_sales", "supplier_lead_time"],
            ["INVENTORY_RISK", "DEMAND_SURGE", "SUPPLIER_DISRUPTION"],
            [_rule("stock_coverage_below_lead_time", ["current_stock", "average_daily_sales", "supplier_lead_time"], "coverage_vs_lead_time", "coverage_short")],
            relationship_rules=["stock_quantity_needs_velocity", "stockout_risk_depends_on_demand_and_replenishment"],
            judgment_type=JudgmentType.RISK_ASSESSMENT.value,
            priority=90,
            forbidden=approved_forbidden["stockout"],
        ),
        _candidate(
            "RECEIVABLE_TIMING_PRESSURE",
            "Receivable Timing Pressure",
            "CASH_FLOW",
            ["CASH_CONVERSION"],
            ["total_revenue", "cash_received", "accounts_receivable", "receivable_days"],
            ["CASH_FLOW_STRESS"],
            [_rule("receivable_timing_cash_conversion", ["total_revenue", "cash_received", "accounts_receivable", "receivable_days"], "timing_association", "delayed_collection")],
            relationship_rules=["revenue_may_precede_cash_receipt", "payment_timing_affects_liquidity"],
            judgment_type=JudgmentType.CONDITION_ASSESSMENT.value,
            priority=88,
            forbidden=approved_forbidden["receivable"],
        ),
        _candidate("DISCOUNT_PRESSURE", "Discount Pressure", "PROFITABILITY", ["UNIT_ECONOMICS", "PRICING_POSITION"], ["discount_rate", "average_order_value"], ["PROFIT_COMPRESSION", "PRICING_PRESSURE"], [_rule("discount_rate_up", ["discount_rate"], "directional_comparison", "discount_up")], review=CandidateReviewStatus.DRAFT.value, priority=60),
        _candidate("CHANNEL_FEE_PRESSURE", "Channel Fee Pressure", "PROFITABILITY", ["UNIT_ECONOMICS"], ["channel_fee_rate"], ["PROFIT_COMPRESSION"], [_rule("channel_fee_up", ["channel_fee_rate"], "directional_comparison", "fee_up")], review=CandidateReviewStatus.DRAFT.value, priority=55),
        _candidate("OPERATING_EXPENSE_INCREASE", "Operating Expense Increase", "PROFITABILITY", ["PROFITABILITY_STRUCTURE"], ["operating_expenses", "net_profit"], ["PROFIT_COMPRESSION"], [_rule("operating_expense_up", ["operating_expenses", "net_profit"], "directional_comparison", "expense_up_profit_down")], priority=78),
        _candidate("SALES_MIX_SHIFT", "Sales Mix Shift", "PROFITABILITY", ["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"], ["product_mix", "gross_margin"], ["PROFIT_COMPRESSION"], [_rule("sales_mix_margin_shift", ["product_mix", "gross_margin"], "directional_comparison", "mix_shift")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("ORDER_GROWTH_WITH_LOW_CONTRIBUTION", "Order Growth With Low Contribution", "PROFITABILITY", ["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"], ["order_count", "contribution_margin"], ["PROFIT_COMPRESSION"], [_rule("orders_up_contribution_low", ["order_count", "contribution_margin"], "directional_comparison", "orders_up_low_contribution")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("DEMAND_EXCEEDS_THROUGHPUT", "Demand Exceeds Throughput", "CAPACITY", ["OPERATING_CAPACITY"], ["current_order_volume", "throughput", "output_time_period"], ["CAPACITY_CONSTRAINT"], [_rule("demand_exceeds_throughput", ["current_order_volume", "throughput"], "ratio_threshold", "demand_exceeds")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("BACKLOG_ACCUMULATION", "Backlog Accumulation", "CAPACITY", ["OPERATING_CAPACITY", "ORDER_FULFILLMENT"], ["backlog_count", "current_order_volume"], ["OPERATIONAL_BOTTLENECK", "CAPACITY_CONSTRAINT"], [_rule("backlog_increases", ["backlog_count"], "directional_comparison", "backlog_up")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("PROCESS_STAGE_CONSTRAINT", "Process Stage Constraint", "CAPACITY", ["PROCESS_FLOW"], ["stage_cycle_time", "throughput"], ["OPERATIONAL_BOTTLENECK"], [_rule("stage_constraint", ["stage_cycle_time", "throughput"], "stage_comparison", "stage_slower")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("TEMPORARY_DEMAND_SPIKE", "Temporary Demand Spike", "CAPACITY", ["SALES_FUNNEL"], ["daily_order_volume", "analysis_timeframe"], ["DEMAND_SURGE"], [_rule("temporary_spike", ["daily_order_volume"], "directional_comparison", "temporary_up")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("CAPACITY_DATA_INSUFFICIENT", "Capacity Data Insufficient", "CAPACITY", ["OPERATING_CAPACITY"], ["maximum_capacity", "current_order_volume"], ["CAPACITY_CONSTRAINT"], [], review=CandidateReviewStatus.DRAFT.value, specificity=CandidateSpecificity.GENERAL.value),
        _candidate("EXCESS_STOCK_EXPOSURE", "Excess Stock Exposure", "INVENTORY", ["INVENTORY_HEALTH"], ["current_stock", "average_daily_sales"], ["INVENTORY_RISK"], [_rule("stock_coverage_high", ["current_stock", "average_daily_sales"], "coverage_threshold", "coverage_high")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("SLOW_MOVING_STOCK", "Slow Moving Stock", "INVENTORY", ["INVENTORY_HEALTH"], ["inventory_age", "average_daily_sales"], ["INVENTORY_RISK"], [_rule("slow_stock", ["inventory_age", "average_daily_sales"], "velocity_threshold", "slow")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("PERISHABILITY_RISK", "Perishability Risk", "INVENTORY", ["INVENTORY_HEALTH"], ["current_stock", "shelf_life"], ["INVENTORY_RISK"], [_rule("perishability_window", ["current_stock", "shelf_life"], "time_horizon", "risk")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("SUPPLIER_LEAD_TIME_EXPOSURE", "Supplier Lead Time Exposure", "INVENTORY", ["SUPPLY_RELIABILITY"], ["supplier_lead_time"], ["SUPPLIER_DISRUPTION", "INVENTORY_RISK"], [_rule("lead_time_exposure", ["supplier_lead_time"], "threshold", "long_lead_time")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("INVENTORY_DATA_INSUFFICIENT", "Inventory Data Insufficient", "INVENTORY", ["INVENTORY_HEALTH"], ["current_stock", "average_daily_sales"], ["INVENTORY_RISK"], [], review=CandidateReviewStatus.DRAFT.value, specificity=CandidateSpecificity.GENERAL.value),
        _candidate("INVENTORY_CASH_LOCK", "Inventory Cash Lock", "CASH_FLOW", ["CASH_CONVERSION", "INVENTORY_HEALTH"], ["inventory_value", "cash_balance"], ["CASH_FLOW_STRESS"], [_rule("inventory_cash_lock", ["inventory_value", "cash_balance"], "association", "cash_locked")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("PAYABLE_TIMING_PRESSURE", "Payable Timing Pressure", "CASH_FLOW", ["CASH_CONVERSION"], ["accounts_payable", "payable_days"], ["CASH_FLOW_STRESS"], [_rule("payable_timing", ["accounts_payable", "payable_days"], "timing_association", "payable_pressure")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("LOW_OPERATING_CASH_CONVERSION", "Low Operating Cash Conversion", "CASH_FLOW", ["CASH_CONVERSION"], ["operating_cash_flow", "total_revenue"], ["CASH_FLOW_STRESS"], [_rule("cash_conversion_low", ["operating_cash_flow", "total_revenue"], "ratio_threshold", "low_conversion")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("CASH_BALANCE_DATA_INSUFFICIENT", "Cash Balance Data Insufficient", "CASH_FLOW", ["CASH_CONVERSION"], ["cash_balance"], ["CASH_FLOW_STRESS"], [], review=CandidateReviewStatus.DRAFT.value, specificity=CandidateSpecificity.GENERAL.value),
        _candidate("TRAFFIC_DECLINE", "Traffic Decline", "SALES", ["SALES_FUNNEL"], ["traffic_count", "order_count"], ["SALES_DECLINE", "DEMAND_WEAKNESS"], [_rule("traffic_declines", ["traffic_count"], "directional_comparison", "traffic_down")], priority=82),
        _candidate("CONVERSION_DECLINE", "Conversion Decline", "SALES", ["SALES_FUNNEL"], ["traffic_count", "conversion_rate", "order_count"], ["SALES_DECLINE", "DEMAND_WEAKNESS"], [_rule("conversion_declines", ["traffic_count", "conversion_rate", "order_count"], "directional_comparison", "conversion_down")], priority=84),
        _candidate("REPEAT_PURCHASE_DECLINE", "Repeat Purchase Decline", "SALES", ["CUSTOMER_RETENTION"], ["repeat_purchase_rate"], ["SALES_DECLINE", "CUSTOMER_RETENTION_RISK"], [_rule("repeat_purchase_declines", ["repeat_purchase_rate"], "directional_comparison", "repeat_down")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("CUSTOMER_MIX_SHIFT", "Customer Mix Shift", "SALES", ["SALES_FUNNEL", "CUSTOMER_RETENTION"], ["customer_count", "customer_segment"], ["SALES_DECLINE"], [_rule("customer_mix_shift", ["customer_count", "customer_segment"], "mix_shift", "shift")], review=CandidateReviewStatus.DRAFT.value),
        _candidate("SALES_DATA_INSUFFICIENT", "Sales Data Insufficient", "SALES", ["SALES_FUNNEL"], ["analysis_timeframe", "order_count"], ["SALES_DECLINE"], [], review=CandidateReviewStatus.DRAFT.value, specificity=CandidateSpecificity.GENERAL.value),
    ]
    return candidates


def _initial_conflicts() -> list[JudgmentCandidateConflict]:
    aov = "JUDGMENT::PROFITABILITY::AVERAGE_ORDER_VALUE_DECLINE"
    unit = "JUDGMENT::PROFITABILITY::UNIT_COST_INCREASE"
    discount = "JUDGMENT::PROFITABILITY::DISCOUNT_PRESSURE"
    traffic = "JUDGMENT::SALES::TRAFFIC_DECLINE"
    conversion = "JUDGMENT::SALES::CONVERSION_DECLINE"
    return [
        JudgmentCandidateConflict(aov, unit, "COEXISTING", True, ["average_order_value", "unit_cost"]),
        JudgmentCandidateConflict(discount, aov, "DEPENDENT", True, ["discount_rate", "average_order_value"]),
        JudgmentCandidateConflict(traffic, conversion, "PARTIALLY_EXCLUSIVE", False, ["traffic_count", "conversion_rate"]),
    ]


class JudgmentCandidateRegistry:
    def __init__(self, definitions: Iterable[JudgmentCandidateDefinition] | None = None) -> None:
        self._definitions = {item.candidate_id: item for item in (definitions or _initial_candidates())}
        self._conflicts = _initial_conflicts()

    @property
    def version(self) -> str:
        return JUDGMENT_CANDIDATE_REGISTRY_VERSION

    def get(self, candidate_id: str) -> JudgmentCandidateDefinition | None:
        item = self._definitions.get(str(candidate_id or ""))
        return deepcopy(item) if item else None

    def list(self) -> list[JudgmentCandidateDefinition]:
        return [deepcopy(self._definitions[key]) for key in sorted(self._definitions)]

    def conflicts(self) -> list[JudgmentCandidateConflict]:
        return deepcopy(self._conflicts)


def _known_metric_ids() -> set[str]:
    registry = BusinessKnowledgeRegistry()
    return {metric for item in registry.list() for metric in item.metrics + item.required_evidence + item.optional_evidence} | {
        "cash_received", "product_mix", "customer_segment", "throughput", "profit_per_unit",
    }


def validate_judgment_candidate_registry(registry: JudgmentCandidateRegistry | None = None) -> dict:
    registry = registry or JudgmentCandidateRegistry()
    definitions = registry.list()
    knowledge = {item.knowledge_id: item for item in BusinessKnowledgeRegistry().list()}
    frames = set(PerspectiveFrameRegistry().ids())
    metrics = _known_metric_ids()
    rules = {rule.rule_id for item in knowledge.values() for rule in item.relationship_rules}
    errors: list[str] = []
    ids = [item.candidate_id for item in definitions]
    if len(ids) != len(set(ids)):
        errors.append("candidate_ids_not_unique")
    for item in definitions:
        if item.maximum_claim_level in {CausalClaimLevel.PRIMARY_DRIVER.value, CausalClaimLevel.CONFIRMED_CAUSE.value}:
            errors.append(f"forbidden_claim_level:{item.candidate_id}")
        if not item.forbidden_outputs:
            errors.append(f"missing_forbidden_outputs:{item.candidate_id}")
        if not item.misuse_constraints:
            errors.append(f"missing_misuse_constraints:{item.candidate_id}")
        if not item.provenance:
            errors.append(f"missing_provenance:{item.candidate_id}")
        for knowledge_id in item.required_knowledge_ids:
            if knowledge_id not in knowledge:
                errors.append(f"unknown_knowledge:{item.candidate_id}:{knowledge_id}")
        for frame_id in item.applicable_frames:
            if frame_id not in frames:
                errors.append(f"unknown_frame:{item.candidate_id}:{frame_id}")
        for metric_id in item.required_metric_ids + item.optional_metric_ids:
            if metric_id not in metrics:
                errors.append(f"unknown_metric:{item.candidate_id}:{metric_id}")
        for rule_id in item.required_relationship_rule_ids:
            if rule_id not in rules:
                errors.append(f"unknown_relationship_rule:{item.candidate_id}:{rule_id}")
    pairs = {(conflict.candidate_a, conflict.candidate_b) for conflict in registry.conflicts()}
    if len(pairs) != len(registry.conflicts()):
        errors.append("duplicate_conflict_definition")
    return {
        "valid": not errors,
        "errors": errors,
        "registered_candidate_count": len(definitions),
        "registered_candidate_ids": ids,
        "approved_candidate_ids": [item.candidate_id for item in definitions if item.review_status == CandidateReviewStatus.APPROVED.value],
        "draft_candidate_ids": [item.candidate_id for item in definitions if item.review_status == CandidateReviewStatus.DRAFT.value],
        "registry_version": registry.version,
    }


def retrieve_judgment_candidates(
    *,
    selected_frame: str,
    selected_knowledge_ids: list[str],
    evidence_package: dict | None = None,
    registry: JudgmentCandidateRegistry | None = None,
) -> dict:
    registry = registry or JudgmentCandidateRegistry()
    selected_knowledge = set(selected_knowledge_ids or [])
    evidence_keys = set((evidence_package or {}).keys())
    available: list[str] = []
    deferred: list[str] = []
    excluded: list[str] = []
    reasons: dict[str, str] = {}
    for item in sorted(registry.list(), key=lambda candidate: (-candidate.priority, candidate.candidate_id)):
        if item.review_status in {CandidateReviewStatus.REJECTED.value, CandidateReviewStatus.DEPRECATED.value}:
            excluded.append(item.candidate_id)
            reasons[item.candidate_id] = item.review_status
            continue
        frame_match = selected_frame in item.applicable_frames or selected_frame == "UNKNOWN_SITUATION"
        knowledge_match = bool(selected_knowledge.intersection(item.required_knowledge_ids))
        evidence_hint = bool(evidence_keys.intersection(item.required_metric_ids))
        if not (frame_match or knowledge_match or evidence_hint):
            deferred.append(item.candidate_id)
            reasons[item.candidate_id] = "no_frame_knowledge_or_evidence_match"
            continue
        if item.review_status != CandidateReviewStatus.APPROVED.value or item.specificity == CandidateSpecificity.TOO_GENERAL.value:
            deferred.append(item.candidate_id)
            reasons[item.candidate_id] = "diagnostic_only_review_or_specificity"
            continue
        available.append(item.candidate_id)
        reasons[item.candidate_id] = "frame_knowledge_evidence_filter"
    result = JudgmentCandidateRetrievalResult(
        selected_frame=selected_frame,
        selected_knowledge_ids=sorted(selected_knowledge),
        available_candidate_ids=available[:5],
        excluded_candidate_ids=excluded,
        deferred_candidate_ids=deferred[:20],
        retrieval_reasons=reasons,
        registry_version=registry.version,
    )
    return result.to_dict()
