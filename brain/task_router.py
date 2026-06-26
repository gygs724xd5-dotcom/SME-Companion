from __future__ import annotations

from dataclasses import asdict, is_dataclass

from brain.capability_registry import get_capability, is_capability_available
from brain.planner_engine import build_execution_plan
from brain.reasoning_engine import build_reasoning
from brain.skill_loader import load_skills


PLACEHOLDER_ENGINES = {
    "ocr_engine": None,
    "inventory_engine": None,
    "sales_forecast_engine": None,
    "business_memory": None,
    "marketing_agent": None,
    "financial_agent": None,
    "inventory_agent": None,
}


TASK_CAPABILITY_NAMES = {
    "Sales Plan": "Sales Plan",
    "Content Plan": "Content Plan",
    "Cost Calculation": "Cost Calculation",
    "Dashboard Request": "Dashboard Request",
    "Receipt Upload": "Receipt Upload",
    "Product Feedback": "Product Feedback",
    "Developer Intelligence": "Developer Intelligence",
    "Marketing": "Content Plan",
    "General Business Help": "Conversation Memory",
    "OCR": "OCR",
    "Inventory": "Inventory",
    "POS Sync": "POS Sync",
    "Business Forecast": "Business Forecast",
}


def _serialize_skill(skill) -> dict:
    if is_dataclass(skill):
        return asdict(skill)
    return dict(skill or {})


def _reasoning_mode(plan: dict, reasoning: dict) -> str:
    if reasoning.get("response_mode"):
        return str(reasoning.get("response_mode"))
    if plan.get("estimated_response_mode"):
        return str(plan.get("estimated_response_mode"))
    return "unknown"


def build_task_route(application_state, user_message) -> dict:
    plan = build_execution_plan(application_state, user_message)
    capability_name = TASK_CAPABILITY_NAMES.get(plan.get("task_type"), plan.get("task_type"))
    capability = get_capability(capability_name)
    capability_available = is_capability_available(capability_name)
    loaded_skills = load_skills(plan.get("required_skills") or [])
    reasoning = build_reasoning(application_state, user_message)

    workflow_state = (application_state or {}).get("workflow") or {}
    workflow_ready = bool(
        workflow_state.get("is_ready")
        or (workflow_state.get("workflow_state_v2") or {}).get("is_ready")
        or reasoning.get("workflow_ready")
    )
    llm_needed = bool(reasoning.get("llm_needed") or plan.get("estimated_response_mode") == "llm")

    return {
        "planner_output": plan,
        "task_type": plan.get("task_type"),
        "selected_capability": capability,
        "loaded_skills": [_serialize_skill(skill) for skill in loaded_skills],
        "reasoning": reasoning,
        "reasoning_mode": _reasoning_mode(plan, reasoning),
        "workflow_ready": workflow_ready,
        "llm_needed": llm_needed,
        "capability_available": capability_available,
        "placeholders": dict(PLACEHOLDER_ENGINES),
    }


def developer_diagnostics(task_route: dict | None) -> dict:
    route = task_route or {}
    skills = route.get("loaded_skills") or []
    loaded_skill_names = [skill.get("name") for skill in skills if skill.get("available")]

    return {
        "Planner Output": route.get("planner_output") or {},
        "Task Type": route.get("task_type"),
        "Selected Capability": (route.get("selected_capability") or {}).get("name"),
        "Loaded Skill": loaded_skill_names,
        "Reasoning Mode": route.get("reasoning_mode"),
        "Workflow Ready": bool(route.get("workflow_ready")),
        "LLM Needed": bool(route.get("llm_needed")),
        "Capability Available": bool(route.get("capability_available")),
    }
