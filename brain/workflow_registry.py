from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_GENERAL_BUSINESS_HELP,
    WORKFLOW_PROFIT_CALCULATION,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    workflow_name: str
    mode: str
    capability_key: str
    skill_name: str | None
    required_fields: tuple[str, ...] = ()
    priority: int = 50
    resume_allowed: bool = True
    cancel_allowed: bool = True
    aliases: tuple[str, ...] = ()
    quick_action: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["required_fields"] = list(self.required_fields)
        data["aliases"] = list(self.aliases)
        return data


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._aliases: dict[str, str] = {}
        self._quick_actions: dict[str, str] = {}

    def register(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        self._workflows[definition.workflow_id] = definition
        for alias in definition.aliases:
            self._aliases[_normalize(alias)] = definition.workflow_id
        if definition.quick_action:
            self._quick_actions[_normalize(definition.quick_action)] = definition.workflow_id
        return definition

    def get(self, workflow_id: str | None) -> WorkflowDefinition | None:
        if not workflow_id:
            return None
        return self._workflows.get(workflow_id) or self._workflows.get(self._aliases.get(_normalize(workflow_id), ""))

    def by_quick_action(self, quick_action: str | None) -> WorkflowDefinition | None:
        if not quick_action:
            return None
        return self.get(self._quick_actions.get(_normalize(quick_action)))

    def detect(self, message: str | None) -> WorkflowDefinition | None:
        normalized = _normalize(message)
        if not normalized:
            return None
        for definition in self._workflows.values():
            if any(_normalize(alias) in normalized for alias in definition.aliases):
                return definition
        return None

    def all(self) -> list[WorkflowDefinition]:
        return list(self._workflows.values())

    def ids(self) -> list[str]:
        return list(self._workflows.keys())


def _normalize(value: str | None) -> str:
    return str(value or "").strip().lower()


def _register_many(registry: WorkflowRegistry, definitions: Iterable[WorkflowDefinition]) -> WorkflowRegistry:
    for definition in definitions:
        registry.register(definition)
    return registry


WORKFLOW_REGISTRY = _register_many(
    WorkflowRegistry(),
    [
        WorkflowDefinition(
            workflow_id=WORKFLOW_CONTENT_PLAN,
            workflow_name="content_creation",
            mode="marketing",
            capability_key="content_plan",
            skill_name="content_creation",
            required_fields=("product_or_business_type",),
            priority=50,
            aliases=("create post", "content", "caption", "post", "สร้างโพสต์", "แคปชั่น", "คอนเทนต์"),
            quick_action="create_post",
        ),
        WorkflowDefinition(
            workflow_id=WORKFLOW_COST_CALCULATION,
            workflow_name="cost_calculation",
            mode="workflow",
            capability_key="cost_calculation",
            skill_name="cost_calculation",
            required_fields=("ingredients_costs", "total_units"),
            priority=70,
            aliases=("cost calculator", "cost calculation", "calculate cost", "คำนวณต้นทุน", "ต้นทุน"),
            quick_action="cost_calculator",
        ),
        WorkflowDefinition(
            workflow_id=WORKFLOW_PROFIT_CALCULATION,
            workflow_name="profit_calculation",
            mode="workflow",
            capability_key="cost_calculation",
            skill_name="cost_calculation",
            required_fields=("price", "cost"),
            priority=75,
            aliases=("profit calculation", "profit", "margin", "\u0e01\u0e33\u0e44\u0e23"),
        ),
        WorkflowDefinition(
            workflow_id=WORKFLOW_RECEIPT_CAPTURE,
            workflow_name="receipt_capture",
            mode="ocr",
            capability_key="receipt_upload",
            skill_name="receipt_capture",
            priority=100,
            aliases=("receipt ocr", "receipt", "read receipt", "อ่านบิล", "บิล", "สลิป"),
            quick_action="receipt_ocr",
        ),
        WorkflowDefinition(
            workflow_id=WORKFLOW_DASHBOARD_REQUEST,
            workflow_name="business_analysis",
            mode="analysis",
            capability_key="dashboard_request",
            skill_name="dashboard_builder",
            priority=80,
            aliases=("business analysis", "analyze business", "dashboard", "วิเคราะห์ร้าน", "แดชบอร์ด"),
            quick_action="business_analysis",
        ),
        WorkflowDefinition(
            workflow_id=WORKFLOW_SALES_PLAN_7_DAY,
            workflow_name="sales_planning",
            mode="planning",
            capability_key="sales_plan",
            skill_name="sales_planning",
            required_fields=("product", "daily_capacity_or_available_quantity", "selling_window_or_sales_channel"),
            priority=60,
            aliases=("sales plan", "7 day sales", "วางแผนขาย", "แผนขาย"),
            quick_action="sales_plan",
        ),
        WorkflowDefinition(
            workflow_id=WORKFLOW_GENERAL_BUSINESS_HELP,
            workflow_name="general_business_help",
            mode="general_chat",
            capability_key="conversation_memory",
            skill_name=None,
            priority=0,
            aliases=("general", "chat"),
            resume_allowed=False,
            cancel_allowed=False,
        ),
    ],
)


def get_workflow_registry() -> WorkflowRegistry:
    return WORKFLOW_REGISTRY


def get_workflow_definition(workflow_id: str | None) -> WorkflowDefinition | None:
    return WORKFLOW_REGISTRY.get(workflow_id)


def get_registered_workflows() -> list[dict]:
    return [definition.to_dict() for definition in WORKFLOW_REGISTRY.all()]
