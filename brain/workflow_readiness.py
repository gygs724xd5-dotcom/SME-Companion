from __future__ import annotations


WORKFLOW_SALES_PLAN_7_DAY = "SALES_PLAN_7_DAY"
WORKFLOW_COST_CALCULATION = "COST_CALCULATION"
WORKFLOW_CONTENT_PLAN = "CONTENT_PLAN"
WORKFLOW_DASHBOARD_REQUEST = "DASHBOARD_REQUEST"
WORKFLOW_RECEIPT_CAPTURE = "RECEIPT_CAPTURE"
WORKFLOW_GENERAL_BUSINESS_HELP = "GENERAL_BUSINESS_HELP"


def is_workflow_ready(workflow_state: dict | None) -> bool:
    state = workflow_state or {}
    workflow = state.get("workflow")
    fields = state.get("collected_fields") or {}

    if workflow == WORKFLOW_SALES_PLAN_7_DAY:
        return bool(
            fields.get("product")
            and (fields.get("daily_capacity") or fields.get("available_quantity"))
            and (fields.get("selling_window") or fields.get("sales_channel"))
        )

    if workflow == WORKFLOW_COST_CALCULATION:
        return bool(fields.get("ingredients_costs") and fields.get("total_units"))

    if workflow == WORKFLOW_CONTENT_PLAN:
        return bool(fields.get("product") or fields.get("business_type"))

    if workflow in {WORKFLOW_DASHBOARD_REQUEST, WORKFLOW_RECEIPT_CAPTURE}:
        return True

    return False
