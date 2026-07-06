from __future__ import annotations

from brain.workflow_state_machine import cost_calculation_trace
from brain.workflow_readiness import WORKFLOW_COST_CALCULATION, WORKFLOW_PROFIT_CALCULATION


def _format_number(value) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "0"
    if amount.is_integer():
        return f"{amount:,.0f}"
    return f"{amount:,.2f}".rstrip("0").rstrip(".")


def generate_cost_calculation_reply(workflow_state: dict) -> str | None:
    fields = (workflow_state or {}).get("collected_fields") or {}
    trace = cost_calculation_trace(fields)
    if trace.get("selected_formula") != "sum_component_costs":
        return None
    total_cost = trace.get("computed_total_cost")
    if total_cost in (None, "", [], {}):
        return None

    components = fields.get("component_costs") or fields.get("ingredients_costs") or []
    parts = []
    for item in components:
        if not isinstance(item, dict):
            continue
        label = item.get("label") or item.get("name")
        amount = item.get("amount") if item.get("amount") not in (None, "", [], {}) else item.get("cost")
        if label and amount not in (None, "", [], {}):
            parts.append(f"{label} {_format_number(amount)} \u0e1a\u0e32\u0e17")

    total_line = f"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = {_format_number(total_cost)} \u0e1a\u0e32\u0e17"
    if parts:
        return " + ".join(parts) + "\n" + total_line
    return total_line


def generate_completed_cost_calculation_reply(workflow_state: dict) -> str | None:
    fields = (workflow_state or {}).get("collected_fields") or {}
    trace = cost_calculation_trace(fields)
    validation_error = trace.get("validation_error")
    if validation_error == "quantity_must_be_greater_than_zero":
        return "\u0e08\u0e33\u0e19\u0e27\u0e19\u0e0a\u0e34\u0e49\u0e19\u0e15\u0e49\u0e2d\u0e07\u0e21\u0e32\u0e01\u0e01\u0e27\u0e48\u0e32 0 \u0e0a\u0e34\u0e49\u0e19\u0e04\u0e23\u0e31\u0e1a"

    component_reply = generate_cost_calculation_reply(workflow_state)
    if component_reply:
        return component_reply

    selected_formula = trace.get("selected_formula")
    total_cost = trace.get("computed_total_cost")
    cost_per_unit = trace.get("computed_cost_per_unit")

    if selected_formula == "total_cost_div_quantity" and cost_per_unit not in (None, "", [], {}):
        return f"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 = {_format_number(cost_per_unit)} \u0e1a\u0e32\u0e17"
    if selected_formula == "unit_cost_times_quantity" and total_cost not in (None, "", [], {}):
        return f"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = {_format_number(total_cost)} \u0e1a\u0e32\u0e17"
    if total_cost not in (None, "", [], {}) and trace.get("requested_output") == "total_cost":
        return f"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = {_format_number(total_cost)} \u0e1a\u0e32\u0e17"
    return None


def _numeric_workflow_value(value):
    if value in (None, "", [], {}):
        return None
    if isinstance(value, dict):
        for key in ("amount", "cost", "value", "total"):
            nested = _numeric_workflow_value(value.get(key))
            if nested is not None:
                return nested
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            nested = _numeric_workflow_value(item)
            if nested is not None:
                return nested
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def generate_profit_calculation_reply(workflow_state: dict) -> str | None:
    fields = (workflow_state or {}).get("collected_fields") or {}
    price = _numeric_workflow_value(fields.get("price") or fields.get("selling_price") or fields.get("prices"))
    cost = _numeric_workflow_value(fields.get("cost") or fields.get("unit_cost") or fields.get("cost_per_unit") or fields.get("costs"))
    if price is None or cost is None:
        return None
    profit = price - cost
    return f"\u0e01\u0e33\u0e44\u0e23 = {_format_number(profit)} \u0e1a\u0e32\u0e17"


def generate_deterministic_workflow_reply(workflow_state: dict) -> str | None:
    workflow = (workflow_state or {}).get("workflow")
    if workflow == WORKFLOW_COST_CALCULATION:
        return generate_completed_cost_calculation_reply(workflow_state)
    if workflow == WORKFLOW_PROFIT_CALCULATION:
        return generate_profit_calculation_reply(workflow_state)
    return None
