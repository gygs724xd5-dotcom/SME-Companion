from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable


BUSINESS_KNOWLEDGE_REGISTRY_VERSION = "5.9.0"


class KnowledgeType(str, Enum):
    CONCEPTUAL = "CONCEPTUAL"
    METRIC = "METRIC"
    RELATIONSHIP = "RELATIONSHIP"
    OPERATIONAL = "OPERATIONAL"


@dataclass(frozen=True)
class RelationshipRule:
    rule_id: str
    statement: str
    input_metrics: list[str] = field(default_factory=list)
    relationship_type: str = "neutral_business_principle"
    allowed_inference: list[str] = field(default_factory=list)
    forbidden_inference: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BusinessKnowledgeDefinition:
    knowledge_id: str
    display_name: str
    description: str
    knowledge_type: list[str]
    business_domain: str
    applicable_frames: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    relationship_rules: list[RelationshipRule] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    optional_evidence: list[str] = field(default_factory=list)
    applicability_conditions: list[str] = field(default_factory=list)
    misuse_constraints: list[str] = field(default_factory=list)
    skill_references: list[str] = field(default_factory=list)
    source_provenance: list[str] = field(default_factory=list)
    allowed_outputs: list[str] = field(default_factory=list)
    forbidden_outputs: list[str] = field(default_factory=list)
    priority: int = 50
    version: str = BUSINESS_KNOWLEDGE_REGISTRY_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


FRAME_TO_KNOWLEDGE = {
    "PROFIT_COMPRESSION": ["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS", "PRICING_POSITION", "CASH_CONVERSION"],
    "SALES_DECLINE": ["SALES_FUNNEL", "CUSTOMER_RETENTION", "PRICING_POSITION"],
    "INVENTORY_RISK": ["INVENTORY_HEALTH", "SUPPLY_RELIABILITY"],
    "CASH_FLOW_STRESS": ["CASH_CONVERSION", "PROFITABILITY_STRUCTURE", "INVENTORY_HEALTH"],
    "DEMAND_SURGE": ["SALES_FUNNEL", "OPERATING_CAPACITY", "ORDER_FULFILLMENT", "INVENTORY_HEALTH"],
    "DEMAND_WEAKNESS": ["SALES_FUNNEL", "CUSTOMER_RETENTION", "PRICING_POSITION"],
    "OPERATIONAL_BOTTLENECK": ["PROCESS_FLOW", "ORDER_FULFILLMENT", "OPERATING_CAPACITY"],
    "CAPACITY_CONSTRAINT": ["OPERATING_CAPACITY", "ORDER_FULFILLMENT", "PROCESS_FLOW"],
    "SUPPLIER_DISRUPTION": ["SUPPLY_RELIABILITY", "INVENTORY_HEALTH", "ORDER_FULFILLMENT"],
    "PRICING_PRESSURE": ["PRICING_POSITION", "UNIT_ECONOMICS", "PROFITABILITY_STRUCTURE"],
    "CUSTOMER_RETENTION_RISK": ["CUSTOMER_RETENTION", "SALES_FUNNEL"],
    "GROWTH_OPPORTUNITY": ["SALES_FUNNEL", "OPERATING_CAPACITY", "UNIT_ECONOMICS", "CASH_CONVERSION"],
    "UNKNOWN_SITUATION": [],
}


def _rule(
    rule_id: str,
    statement: str,
    metrics: list[str],
    allowed: list[str],
    forbidden: list[str],
    relationship_type: str = "neutral_business_principle",
) -> RelationshipRule:
    return RelationshipRule(
        rule_id=rule_id,
        statement=statement,
        input_metrics=metrics,
        relationship_type=relationship_type,
        allowed_inference=allowed,
        forbidden_inference=forbidden,
    )


def _definition(
    knowledge_id: str,
    display_name: str,
    domain: str,
    concepts: list[str],
    metrics: list[str],
    relationships: list[RelationshipRule],
    *,
    frames: list[str] | None = None,
    required: list[str] | None = None,
    optional: list[str] | None = None,
    applicability: list[str] | None = None,
    misuse: list[str] | None = None,
    priority: int = 50,
    knowledge_type: list[str] | None = None,
) -> BusinessKnowledgeDefinition:
    return BusinessKnowledgeDefinition(
        knowledge_id=knowledge_id,
        display_name=display_name,
        description=f"Canonical business knowledge for {display_name.lower()}.",
        knowledge_type=knowledge_type or [
            KnowledgeType.CONCEPTUAL.value,
            KnowledgeType.METRIC.value,
            KnowledgeType.RELATIONSHIP.value,
        ],
        business_domain=domain,
        applicable_frames=frames or [],
        concepts=concepts,
        metrics=metrics,
        relationship_rules=relationships,
        required_evidence=required or [],
        optional_evidence=optional or [],
        applicability_conditions=applicability or [],
        misuse_constraints=misuse or ["Do not diagnose root causes.", "Do not recommend actions without a later authority."],
        skill_references=[],
        source_provenance=["SME Companion V5.9.0 canonical seed registry"],
        allowed_outputs=[
            "relevant_concepts",
            "relevant_metrics",
            "neutral_relationship_rules",
            "evidence_requirements",
            "knowledge_gap",
            "clarification_handoff",
        ],
        forbidden_outputs=[
            "root_cause",
            "recommendation",
            "business_judgment",
            "decision",
            "workflow_trigger",
            "business_memory_mutation",
        ],
        priority=priority,
    )


def _initial_knowledge() -> list[BusinessKnowledgeDefinition]:
    return [
        _definition(
            "STARTUP_COST_STRUCTURE",
            "Startup Cost Structure",
            "Startup / Cost",
            ["initial investment", "one-time setup cost", "working capital", "fixed cost", "variable cost", "contingency reserve"],
            ["equipment_cost", "renovation_cost", "deposit_cost", "initial_inventory_cost", "license_cost", "marketing_launch_cost", "working_capital_requirement", "contingency_amount"],
            [
                _rule("startup_capital_has_setup_and_cash", "Startup capital includes setup cost and initial operating cash.", ["working_capital_requirement"], ["Setup and operating cash should be separated."], ["The startup budget is known."]),
                _rule("business_model_changes_startup_cost", "Business model changes startup-cost structure.", ["business_model", "location_model"], ["Business model or location model may be needed first."], ["A storefront should be assumed."]),
                _rule("made_to_order_reduces_some_inventory_not_all_costs", "Made-to-order may reduce finished-goods inventory but still requires equipment, ingredients, and operating cash.", ["business_model"], ["Inventory assumptions depend on model."], ["Made-to-order has no startup cost."]),
            ],
            required=["business_model", "location_model", "product_category", "starting_scale", "equipment_requirements", "sales_channel"],
            misuse=["Do not invent a startup budget.", "Do not assume a physical storefront.", "Do not recommend borrowing.", "Do not treat working capital as profit."],
            priority=95,
        ),
        _definition(
            "PROFITABILITY_STRUCTURE",
            "Profitability Structure",
            "Profitability",
            ["revenue", "cost of goods sold", "gross profit", "gross margin", "operating expenses", "net profit", "net margin"],
            ["total_revenue", "total_cost_of_goods", "gross_profit", "gross_margin", "operating_expenses", "net_profit", "net_margin", "analysis_timeframe"],
            [
                _rule("gross_profit_equals_revenue_minus_direct_cost", "Gross profit equals revenue minus direct cost of goods.", ["total_revenue", "total_cost_of_goods"], ["Revenue and direct cost are required for gross profit."], ["Costs are the cause of profit change."]),
                _rule("net_profit_reflects_operating_expenses", "Net profit also reflects operating expenses.", ["gross_profit", "operating_expenses"], ["Operating expenses may be relevant to net profit."], ["Operating expenses caused the decline."]),
                _rule("revenue_growth_not_guaranteed_by_profit_growth", "Revenue growth does not guarantee profit growth.", ["total_revenue", "net_profit"], ["Profitability and unit economics should be examined."], ["Costs, discounts, or waste are the actual cause."]),
                _rule("profit_comparisons_require_compatible_timeframes", "Comparisons require compatible timeframes.", ["analysis_timeframe"], ["The comparison period may be missing."], ["Current profit trend is known."]),
            ],
            frames=["PROFIT_COMPRESSION", "PRICING_PRESSURE", "GROWTH_OPPORTUNITY", "CASH_FLOW_STRESS"],
            required=["analysis_timeframe", "total_revenue", "total_cost_of_goods"],
            optional=["operating_expenses", "net_profit"],
            priority=100,
        ),
        _definition(
            "UNIT_ECONOMICS",
            "Unit Economics",
            "Pricing / Cost / Profitability",
            ["selling price", "unit cost", "contribution margin", "average order value", "discount", "channel fee", "fulfillment cost"],
            ["selling_price", "unit_cost", "contribution_margin", "contribution_margin_rate", "average_order_value", "discount_rate", "channel_fee_rate", "fulfillment_cost"],
            [
                _rule("contribution_margin_needs_realized_price_and_variable_cost", "Contribution margin depends on realized selling price minus variable costs.", ["selling_price", "unit_cost"], ["Price and unit cost are required for contribution margin."], ["Revenue is contribution margin."]),
                _rule("discounts_reduce_realized_revenue", "Discounts reduce realized revenue per order.", ["discount_rate"], ["Discount evidence may be relevant."], ["Discounts caused lower profit."]),
                _rule("channel_fees_reduce_contribution", "Channel fees reduce contribution after a sale.", ["channel_fee_rate"], ["Channel fee evidence may be relevant."], ["Channel fees caused lower profit."]),
                _rule("aov_shapes_customer_growth_profit_translation", "Average order value influences how customer growth translates into profit.", ["average_order_value"], ["Average order value may be needed."], ["More customers should increase profit."]),
            ],
            frames=["PROFIT_COMPRESSION", "PRICING_PRESSURE", "GROWTH_OPPORTUNITY"],
            required=["selling_price", "unit_cost"],
            misuse=["Do not infer discounts caused lower profit without evidence.", "Do not recommend increasing price.", "Do not treat revenue as contribution margin."],
            priority=98,
        ),
        _definition(
            "PRICING_POSITION",
            "Pricing Position",
            "Pricing",
            ["current price", "price floor", "competitor price", "willingness to pay", "perceived value", "discounting"],
            ["selling_price", "minimum_viable_price", "competitor_price", "discount_rate", "conversion_by_price", "gross_margin"],
            [
                _rule("price_affects_conversion_and_margin", "Price affects both conversion and margin.", ["selling_price", "conversion_by_price", "gross_margin"], ["Price can be relevant to both demand and margin."], ["Price is too high or too low."]),
                _rule("price_comparisons_require_comparable_offers", "Price comparisons require comparable offers.", ["competitor_price"], ["Offer comparability may be needed."], ["Competitors explain the situation."]),
            ],
            frames=["PROFIT_COMPRESSION", "SALES_DECLINE", "DEMAND_WEAKNESS", "PRICING_PRESSURE"],
            required=["selling_price"],
            priority=76,
        ),
        _definition(
            "SALES_FUNNEL",
            "Sales Funnel",
            "Sales",
            ["traffic", "inquiry", "lead", "conversion", "order", "average order value"],
            ["traffic_count", "inquiry_count", "lead_count", "conversion_rate", "order_count", "average_order_value", "analysis_timeframe", "customer_count"],
            [
                _rule("sales_decline_can_be_traffic_or_conversion", "Sales can decline because traffic falls or conversion weakens.", ["traffic_count", "conversion_rate"], ["Traffic and conversion are separable evidence needs."], ["Traffic or conversion is the cause."]),
                _rule("orders_and_revenue_can_diverge_by_aov", "Order growth and revenue growth may differ when average order value changes.", ["order_count", "average_order_value"], ["Order count and average order value may both matter."], ["More orders guarantee more revenue."]),
            ],
            frames=["SALES_DECLINE", "DEMAND_SURGE", "DEMAND_WEAKNESS", "GROWTH_OPPORTUNITY", "CUSTOMER_RETENTION_RISK"],
            required=["analysis_timeframe"],
            priority=92,
        ),
        _definition(
            "CUSTOMER_RETENTION",
            "Customer Retention",
            "Customer",
            ["repeat purchase", "returning customer", "churn", "purchase frequency", "customer continuity"],
            ["repeat_purchase_rate", "returning_customer_count", "churn_rate", "purchase_frequency", "customer_lifetime_value"],
            [
                _rule("retention_affects_revenue_stability", "Repeat purchase affects revenue stability.", ["repeat_purchase_rate"], ["Retention can be a relevant separate dimension."], ["Retention caused the situation."]),
                _rule("customer_growth_can_hide_retention_decline", "Customer growth may hide declining retention.", ["customer_count", "repeat_purchase_rate"], ["Acquisition and retention should be separated."], ["Retention is declining."]),
            ],
            frames=["SALES_DECLINE", "DEMAND_WEAKNESS", "CUSTOMER_RETENTION_RISK"],
            required=["repeat_purchase_rate"],
            priority=70,
        ),
        _definition(
            "INVENTORY_HEALTH",
            "Inventory Health",
            "Inventory",
            ["current stock", "sales velocity", "days of stock", "safety stock", "stockout", "excess stock", "obsolete stock", "shelf life"],
            ["current_stock", "average_daily_sales", "days_of_stock", "safety_stock", "stockout_frequency", "inventory_age", "shelf_life"],
            [
                _rule("stock_quantity_needs_velocity", "Stock quantity alone is incomplete without sales velocity.", ["current_stock", "average_daily_sales"], ["Sales velocity or current demand may be needed."], ["Stock is excessive or insufficient."]),
                _rule("stockout_risk_depends_on_demand_and_replenishment", "Stockout risk depends on demand and replenishment time.", ["average_daily_sales", "supplier_lead_time"], ["Demand and replenishment are separate inputs."], ["Reorder is required."]),
                _rule("perishable_inventory_needs_shelf_life", "Perishable inventory also depends on shelf life.", ["current_stock", "shelf_life"], ["Shelf life can matter for perishable products."], ["Old inventory is unusable."]),
            ],
            frames=["INVENTORY_RISK", "CASH_FLOW_STRESS", "DEMAND_SURGE", "SUPPLIER_DISRUPTION"],
            required=["current_stock", "average_daily_sales"],
            optional=["shelf_life", "supplier_lead_time"],
            misuse=["Do not recommend reordering automatically.", "Do not label stock excessive without velocity and timeframe.", "Do not treat old inventory records as current."],
            priority=96,
        ),
        _definition(
            "SUPPLY_RELIABILITY",
            "Supply Reliability",
            "Supplier / Purchasing",
            ["lead time", "delivery reliability", "material availability", "purchase order", "supplier dependency"],
            ["supplier_lead_time", "on_time_delivery_rate", "open_purchase_orders", "shortage_count", "supplier_concentration"],
            [
                _rule("lead_time_increases_planning_requirement", "Longer lead time increases planning requirements.", ["supplier_lead_time"], ["Lead time may be relevant."], ["Supplier is unreliable."]),
                _rule("supplier_delay_may_affect_inventory_and_fulfillment", "Supplier delay may affect inventory and fulfillment.", ["supplier_lead_time", "shortage_count"], ["Supply evidence can connect to inventory or fulfillment."], ["Delay caused lost sales."]),
            ],
            frames=["INVENTORY_RISK", "SUPPLIER_DISRUPTION"],
            required=["supplier_lead_time"],
            priority=68,
        ),
        _definition(
            "OPERATING_CAPACITY",
            "Operating Capacity",
            "Operations",
            ["maximum capacity", "current output", "utilization", "available labor", "equipment capacity", "cycle time", "backlog"],
            ["maximum_capacity", "output_quantity", "current_output", "utilization_rate", "production_hours", "staffing_level", "cycle_time", "backlog_count", "current_order_volume", "output_time_period"],
            [
                _rule("capacity_requires_time_unit", "Capacity is only interpretable when quantity and time period are known.", ["output_quantity", "output_time_period"], ["The metric is incomplete without a period."], ["The business has insufficient capacity."]),
                _rule("utilization_depends_on_demand_relative_to_capacity", "Utilization depends on demand relative to capacity.", ["current_order_volume", "maximum_capacity"], ["Demand and capacity should be separated."], ["Utilization is high."]),
                _rule("backlog_may_grow_when_demand_exceeds_throughput", "Backlog may grow when incoming demand exceeds throughput.", ["backlog_count", "current_order_volume"], ["Backlog can be relevant after capacity definition."], ["Sales channels should be expanded."]),
            ],
            frames=["DEMAND_SURGE", "OPERATIONAL_BOTTLENECK", "CAPACITY_CONSTRAINT", "GROWTH_OPPORTUNITY"],
            required=["output_quantity", "output_time_period", "current_order_volume"],
            optional=["production_hours", "staffing_level", "equipment_count", "rework_rate", "downtime"],
            misuse=["Do not infer insufficient capacity from quantity alone.", "Do not recommend expansion, hiring, or equipment purchases."],
            priority=99,
            knowledge_type=[KnowledgeType.CONCEPTUAL.value, KnowledgeType.METRIC.value, KnowledgeType.RELATIONSHIP.value, KnowledgeType.OPERATIONAL.value],
        ),
        _definition(
            "ORDER_FULFILLMENT",
            "Order Fulfillment",
            "Operations / Sales",
            ["order intake", "production queue", "promise date", "delivery time", "backlog", "cancellation", "handoff"],
            ["daily_order_volume", "backlog_count", "average_fulfillment_time", "on_time_fulfillment_rate", "cancellation_rate", "late_order_count", "current_order_volume"],
            [
                _rule("made_to_order_connects_demand_to_capacity", "Made-to-order connects demand directly to fulfillment capacity.", ["business_model", "current_order_volume"], ["Order context can be relevant for made-to-order work."], ["Backlog means poor operations."]),
                _rule("backlog_is_waiting_not_failed_sales", "Backlog means orders waiting for completion, not necessarily failed sales.", ["backlog_count"], ["Backlog should be interpreted neutrally."], ["Backlog means failed sales."]),
                _rule("order_growth_may_increase_delay_without_throughput_change", "Order growth may increase delay if throughput does not change.", ["daily_order_volume", "throughput"], ["Throughput and order volume may both matter."], ["Demand growth is bad."]),
            ],
            frames=["DEMAND_SURGE", "OPERATIONAL_BOTTLENECK", "CAPACITY_CONSTRAINT", "SUPPLIER_DISRUPTION"],
            required=["business_model"],
            applicability=["Business accepts orders before production or fulfillment.", "Delivery or production occurs after confirmation.", "Timing and queue are relevant."],
            misuse=["Do not recommend opening more sales channels before capacity context is known.", "Do not assume backlog means poor operations."],
            priority=84,
        ),
        _definition(
            "CASH_CONVERSION",
            "Cash Conversion",
            "Cash Flow",
            ["cash balance", "receivable", "payable", "inventory cash lock", "payment timing", "operating cash movement"],
            ["cash_balance", "accounts_receivable", "accounts_payable", "receivable_days", "payable_days", "inventory_value", "operating_cash_flow"],
            [
                _rule("profit_and_cash_are_different", "Profit and available cash are different measures.", ["net_profit", "cash_balance"], ["Cash timing may need separate evidence."], ["Low cash means business loss."]),
                _rule("revenue_may_precede_cash_receipt", "Revenue may be recorded before cash is received.", ["total_revenue", "accounts_receivable"], ["Payment timing may be needed."], ["Money is stuck in receivables."]),
                _rule("payment_timing_affects_liquidity", "Payment timing affects short-term liquidity.", ["receivable_days", "payable_days"], ["Receivable or payment timing may be relevant."], ["Financing is required."]),
            ],
            frames=["CASH_FLOW_STRESS", "PROFIT_COMPRESSION", "GROWTH_OPPORTUNITY"],
            required=["cash_balance"],
            optional=["accounts_receivable", "receivable_days", "payable_days"],
            misuse=["Do not diagnose cash leakage.", "Do not recommend financing or borrowing.", "Do not equate low cash with business loss."],
            priority=94,
        ),
        _definition(
            "PROCESS_FLOW",
            "Process Flow",
            "Operations",
            ["workflow stage", "queue", "waiting time", "handoff", "rework", "throughput", "bottleneck"],
            ["queue_length", "waiting_time", "throughput", "rework_rate", "stage_cycle_time", "handoff_count"],
            [
                _rule("bottleneck_limits_total_throughput", "A bottleneck limits total throughput.", ["stage_cycle_time", "throughput"], ["Stage evidence is needed before naming a bottleneck."], ["A specific bottleneck exists."]),
                _rule("waiting_can_rise_without_processing_time_change", "Waiting may rise even when processing time is unchanged.", ["waiting_time", "stage_cycle_time"], ["Waiting and processing time are distinct."], ["Staffing changes are needed."]),
            ],
            frames=["OPERATIONAL_BOTTLENECK", "CAPACITY_CONSTRAINT"],
            required=["throughput"],
            misuse=["Do not identify a bottleneck without stage evidence.", "Do not recommend staffing changes."],
            priority=66,
        ),
    ]


class BusinessKnowledgeRegistry:
    def __init__(self, definitions: Iterable[BusinessKnowledgeDefinition] | None = None) -> None:
        self._definitions = {item.knowledge_id: item for item in (definitions or _initial_knowledge())}

    @property
    def version(self) -> str:
        return BUSINESS_KNOWLEDGE_REGISTRY_VERSION

    def get(self, knowledge_id: str) -> BusinessKnowledgeDefinition | None:
        item = self._definitions.get(str(knowledge_id or ""))
        return deepcopy(item) if item else None

    def list(self) -> list[BusinessKnowledgeDefinition]:
        return [deepcopy(self._definitions[key]) for key in sorted(self._definitions)]

    def ids(self) -> list[str]:
        return sorted(self._definitions)

    def get_for_frame(self, frame_id: str) -> list[BusinessKnowledgeDefinition]:
        ids = FRAME_TO_KNOWLEDGE.get(str(frame_id or ""), [])
        return [self.get(knowledge_id) for knowledge_id in ids if self.get(knowledge_id)]


def get_business_knowledge(knowledge_id: str) -> BusinessKnowledgeDefinition | None:
    return BusinessKnowledgeRegistry().get(knowledge_id)


def list_business_knowledge() -> list[BusinessKnowledgeDefinition]:
    return BusinessKnowledgeRegistry().list()


def get_knowledge_for_frame(frame_id: str) -> list[BusinessKnowledgeDefinition]:
    return BusinessKnowledgeRegistry().get_for_frame(frame_id)


def validate_knowledge_registry(registry: BusinessKnowledgeRegistry | None = None) -> dict:
    registry = registry or BusinessKnowledgeRegistry()
    definitions = registry.list()
    errors: list[str] = []
    ids = [item.knowledge_id for item in definitions]
    if len(ids) != len(set(ids)):
        errors.append("knowledge_ids_not_unique")
    for frame_id, mapped_ids in FRAME_TO_KNOWLEDGE.items():
        if frame_id == "UNKNOWN_SITUATION" and mapped_ids:
            errors.append("unknown_situation_has_forced_knowledge")
        for knowledge_id in mapped_ids:
            if knowledge_id not in ids:
                errors.append(f"missing_mapped_knowledge:{frame_id}:{knowledge_id}")
    for item in definitions:
        if not item.allowed_outputs:
            errors.append(f"missing_allowed_outputs:{item.knowledge_id}")
        if not item.forbidden_outputs:
            errors.append(f"missing_forbidden_outputs:{item.knowledge_id}")
        if item.knowledge_id in {"STARTUP_COST_STRUCTURE", "UNIT_ECONOMICS", "INVENTORY_HEALTH", "OPERATING_CAPACITY", "ORDER_FULFILLMENT", "CASH_CONVERSION", "PROCESS_FLOW"} and not item.misuse_constraints:
            errors.append(f"missing_misuse_constraints:{item.knowledge_id}")
        rule_ids = [rule.rule_id for rule in item.relationship_rules]
        if len(rule_ids) != len(set(rule_ids)):
            errors.append(f"duplicate_relationship_rule:{item.knowledge_id}")
    return {
        "valid": not errors,
        "errors": errors,
        "registered_knowledge_count": len(definitions),
        "registered_knowledge_ids": ids,
        "business_domains": sorted({item.business_domain for item in definitions}),
        "registry_version": registry.version,
    }
