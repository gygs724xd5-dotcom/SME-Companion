from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Iterable


PERSPECTIVE_FRAME_REGISTRY_VERSION = "5.8.5"


@dataclass(frozen=True)
class PerspectiveFrameDefinition:
    frame_id: str
    display_name: str
    description: str
    recognition_signals: list[str] = field(default_factory=list)
    required_signal_groups: list[list[str]] = field(default_factory=list)
    contradictory_signals: list[str] = field(default_factory=list)
    minimum_confidence: float = 0.65
    related_business_domains: list[str] = field(default_factory=list)
    allowed_outputs: list[str] = field(default_factory=list)
    forbidden_outputs: list[str] = field(default_factory=list)
    version: str = PERSPECTIVE_FRAME_REGISTRY_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


class PerspectiveFrameRegistry:
    def __init__(self, frames: Iterable[PerspectiveFrameDefinition] | None = None) -> None:
        self._frames = {frame.frame_id: frame for frame in (frames or _initial_frames())}

    @property
    def version(self) -> str:
        return PERSPECTIVE_FRAME_REGISTRY_VERSION

    def get(self, frame_id: str) -> PerspectiveFrameDefinition | None:
        frame = self._frames.get(str(frame_id or ""))
        return deepcopy(frame) if frame else None

    def list(self) -> list[PerspectiveFrameDefinition]:
        return [deepcopy(self._frames[key]) for key in sorted(self._frames)]

    def ids(self) -> list[str]:
        return sorted(self._frames)


def get_perspective_frame(frame_id: str) -> PerspectiveFrameDefinition | None:
    return PerspectiveFrameRegistry().get(frame_id)


def list_perspective_frames() -> list[PerspectiveFrameDefinition]:
    return PerspectiveFrameRegistry().list()


def _frame(
    frame_id: str,
    display_name: str,
    description: str,
    recognition_signals: list[str],
    required_signal_groups: list[list[str]],
    contradictory_signals: list[str] | None = None,
    minimum_confidence: float = 0.65,
    domains: list[str] | None = None,
) -> PerspectiveFrameDefinition:
    return PerspectiveFrameDefinition(
        frame_id=frame_id,
        display_name=display_name,
        description=description,
        recognition_signals=recognition_signals,
        required_signal_groups=required_signal_groups,
        contradictory_signals=contradictory_signals or [],
        minimum_confidence=minimum_confidence,
        related_business_domains=domains or ["sales", "finance", "operations"],
        allowed_outputs=[
            "candidate_frame",
            "selected_frame",
            "supporting_signals",
            "contradictory_signals",
            "diagnostic_confidence",
            "selection_reason",
        ],
        forbidden_outputs=[
            "root_cause",
            "recommendation",
            "decision",
            "workflow_admission",
            "knowledge_lookup",
            "business_judgment",
        ],
    )


def _initial_frames() -> list[PerspectiveFrameDefinition]:
    return [
        _frame(
            "UNKNOWN_SITUATION",
            "Unknown Situation",
            "Evidence is insufficient to identify a supported business situation frame.",
            [],
            [],
            minimum_confidence=0.0,
            domains=["general_business"],
        ),
        _frame(
            "PROFIT_COMPRESSION",
            "Profit Compression",
            "Business activity or demand is stable/increasing, but profit is declining or not improving.",
            ["demand_increase", "sales_increase", "revenue_stable_or_increase", "profit_decrease", "money_not_remaining"],
            [["profit_decrease"], ["customer_increase", "demand_increase", "sales_increase", "revenue_stable_or_increase", "selling_activity_high"]],
            ["profit_increase"],
            0.78,
            ["finance", "sales"],
        ),
        _frame(
            "SALES_DECLINE",
            "Sales Decline",
            "Sales or revenue is decreasing over a relevant period.",
            ["sales_decrease", "revenue_decrease", "continuous_decline", "prior_period_lower"],
            [["sales_decrease", "revenue_decrease"]],
            ["sales_increase", "demand_increase"],
            0.65,
            ["sales"],
        ),
        _frame(
            "INVENTORY_RISK",
            "Inventory Risk",
            "Available stock may be insufficient for current or expected demand.",
            ["stock_low", "stock_near_zero", "inventory_insufficient", "demand_exists"],
            [["stock_low", "stock_near_zero", "inventory_insufficient"]],
            ["stock_abundant"],
            0.65,
            ["inventory", "operations"],
        ),
        _frame(
            "CASH_FLOW_STRESS",
            "Cash Flow Stress",
            "The business appears to have activity or revenue but insufficient available cash.",
            ["sales_exist", "revenue_exists", "cash_insufficient", "money_not_remaining", "cannot_pay"],
            [["cash_insufficient", "money_not_remaining", "cannot_pay"], ["customer_increase", "sales_exist", "revenue_exists", "selling_activity_high"]],
            ["cash_abundant"],
            0.7,
            ["finance"],
        ),
        _frame(
            "DEMAND_SURGE",
            "Demand Surge",
            "Customer demand or order volume is increasing materially.",
            ["demand_increase", "orders_increase", "customer_increase", "sudden_growth"],
            [["demand_increase", "orders_increase", "customer_increase"]],
            ["demand_decrease"],
            0.65,
            ["sales", "operations"],
        ),
        _frame(
            "DEMAND_WEAKNESS",
            "Demand Weakness",
            "Customer demand, traffic, or orders are declining.",
            ["demand_decrease", "orders_decrease", "customer_decrease", "traffic_decrease"],
            [["demand_decrease", "orders_decrease", "customer_decrease", "traffic_decrease"]],
            ["demand_increase"],
            0.65,
            ["sales"],
        ),
        _frame(
            "OPERATIONAL_BOTTLENECK",
            "Operational Bottleneck",
            "Operational flow is constrained and causing delay, backlog, or reduced throughput.",
            ["orders_backlog", "queue_increase", "process_stuck", "delay"],
            [["orders_backlog", "queue_increase", "process_stuck", "delay"]],
            [],
            0.65,
            ["operations"],
        ),
        _frame(
            "CAPACITY_CONSTRAINT",
            "Capacity Constraint",
            "Demand or workload exceeds available production, staffing, or service capacity.",
            ["capacity_exceeded", "cannot_keep_up", "staff_capacity_limited", "equipment_capacity_limited", "max_output_reached"],
            [["capacity_exceeded", "cannot_keep_up", "staff_capacity_limited", "equipment_capacity_limited", "max_output_reached"]],
            [],
            0.65,
            ["operations"],
        ),
        _frame(
            "SUPPLIER_DISRUPTION",
            "Supplier Disruption",
            "Supplier delay, shortage, or dependency is disrupting business operations.",
            ["supplier_late", "material_unavailable", "supplier_interrupted"],
            [["supplier_late", "material_unavailable", "supplier_interrupted"]],
            [],
            0.65,
            ["operations", "procurement"],
        ),
        _frame(
            "PRICING_PRESSURE",
            "Pricing Pressure",
            "Current pricing appears constrained by customers, competitors, or margin conditions.",
            ["price_resistance", "competitor_undercut", "price_margin_constraint"],
            [["price_resistance", "competitor_undercut", "price_margin_constraint"]],
            [],
            0.65,
            ["pricing", "sales"],
        ),
        _frame(
            "CUSTOMER_RETENTION_RISK",
            "Customer Retention Risk",
            "Repeat purchase, loyalty, or returning-customer behavior is weakening.",
            ["repeat_customer_decline", "customers_do_not_return", "churn", "loyalty_weakness"],
            [["repeat_customer_decline", "customers_do_not_return", "churn", "loyalty_weakness"]],
            [],
            0.65,
            ["sales", "customer"],
        ),
        _frame(
            "GROWTH_OPPORTUNITY",
            "Growth Opportunity",
            "Evidence indicates expanding demand, customer growth, or market opportunity without a current material warning signal.",
            ["demand_increase", "orders_increase", "customer_increase", "room_to_serve"],
            [["demand_increase", "orders_increase", "customer_increase"], ["room_to_serve"]],
            ["profit_decrease", "cash_insufficient", "capacity_exceeded", "inventory_insufficient"],
            0.72,
            ["sales", "strategy"],
        ),
    ]
