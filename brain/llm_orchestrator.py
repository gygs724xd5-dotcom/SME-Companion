from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter


DETERMINISTIC_TASKS = {
    "Cost Calculation",
    "Dashboard Request",
    "Receipt Upload",
    "OCR",
    "Inventory",
    "POS Sync",
    "Business Forecast",
}

DETERMINISTIC_WORKFLOWS = {
    "COST_CALCULATION",
    "DASHBOARD_REQUEST",
    "RECEIPT_CAPTURE",
}

LANGUAGE_TASKS = {
    "Marketing",
    "General Business Help",
}

LANGUAGE_CAPABILITIES = {
    "Content Plan",
    "Conversation Memory",
}

LANGUAGE_INTENTS = {
    "MARKETING",
    "CONTENT",
    "GENERAL_CHAT",
    "ASK_ADVICE",
    "CUSTOMER_REPLY",
    "TRANSLATION",
    "SUMMARY",
    "RECOMMENDATION",
}

LANGUAGE_KEYWORDS = [
    "caption",
    "post",
    "content",
    "marketing",
    "reply",
    "respond",
    "translate",
    "summary",
    "summarize",
    "explain",
    "recommend",
    "idea",
    "write",
    "rewrite",
    "copy",
    "\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
    "\u0e41\u0e04\u0e1b\u0e0a\u0e31\u0e48\u0e19",
    "\u0e04\u0e2d\u0e19\u0e40\u0e17\u0e19\u0e15\u0e4c",
    "\u0e01\u0e32\u0e23\u0e15\u0e25\u0e32\u0e14",
    "\u0e15\u0e2d\u0e1a\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32",
    "\u0e41\u0e1b\u0e25",
    "\u0e2a\u0e23\u0e38\u0e1b",
    "\u0e2d\u0e18\u0e34\u0e1a\u0e32\u0e22",
    "\u0e41\u0e19\u0e30\u0e19\u0e33",
    "\u0e40\u0e02\u0e35\u0e22\u0e19",
]


@dataclass
class LLMDecision:
    should_use_llm: bool
    response_mode: str
    reason: str
    source_of_truth: str = "workflow"
    latency_ms: int = 0
    token_usage: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["token_usage"] = data["token_usage"] or {}
        return data


def _compact_dict(data: dict | None) -> dict:
    return {key: value for key, value in (data or {}).items() if value not in (None, "", [], {})}


def _capability_name(capability: dict | str | None) -> str | None:
    if isinstance(capability, dict):
        return capability.get("name")
    if capability:
        return str(capability)
    return None


def _loaded_skill_names(loaded_skill: list | dict | None) -> list[str]:
    if isinstance(loaded_skill, dict):
        loaded_skill = [loaded_skill]
    names = []
    for skill in loaded_skill or []:
        if isinstance(skill, dict) and skill.get("name"):
            names.append(str(skill["name"]))
    return names


def _contains_language_request(message: str) -> bool:
    lowered = str(message or "").strip().lower()
    return any(keyword.lower() in lowered for keyword in LANGUAGE_KEYWORDS)


def build_reasoning_context(
    *,
    user_message: str,
    application_state: dict | None = None,
    planner: dict | None = None,
    workflow: dict | None = None,
    reasoning: dict | None = None,
    capability: dict | str | None = None,
    loaded_skill: list | dict | None = None,
    conversation_intent: str | None = None,
    conversation_summary: dict | None = None,
    business_context: dict | None = None,
    store_profile: dict | None = None,
    business_memory: dict | list | None = None,
    current_goal: dict | None = None,
    current_task: str | None = None,
) -> dict:
    state = application_state or {}
    planner = planner or {}
    workflow = workflow if workflow is not None else state.get("workflow") or {}
    conversation = state.get("conversation") or {}
    return {
        "user_message": str(user_message or "").strip(),
        "planner_output": planner,
        "workflow": workflow,
        "business_context": business_context or state.get("business_context") or conversation.get("business_context") or {},
        "conversation_summary": conversation_summary or conversation.get("conversation_memory") or {},
        "store_profile": store_profile or state.get("store") or {},
        "business_memory": business_memory or {},
        "current_goal": current_goal or {},
        "missing_information": planner.get("missing_information") or workflow.get("missing_fields") or [],
        "current_task": current_task or planner.get("task_type"),
        "capability": capability,
        "loaded_skill": loaded_skill,
        "conversation_intent": conversation_intent,
        "reasoning": reasoning or {},
    }


def decide_llm_usage(reasoning_context: dict | None) -> dict:
    started = perf_counter()
    context = reasoning_context or {}
    planner = context.get("planner_output") or {}
    workflow = context.get("workflow") or {}
    reasoning = context.get("reasoning") or {}
    message = context.get("user_message") or planner.get("goal") or ""
    task_type = context.get("current_task") or planner.get("task_type")
    capability_name = _capability_name(context.get("capability")) or planner.get("capability")
    workflow_name = (
        planner.get("workflow")
        or workflow.get("workflow")
        or workflow.get("current_workflow")
        or (workflow.get("workflow_state_v2") or {}).get("workflow")
        or reasoning.get("workflow")
    )
    missing_information = context.get("missing_information") or planner.get("missing_information") or []
    intent = context.get("conversation_intent") or ((planner.get("conversation_understanding") or {}).get("legacy_intent"))
    loaded_skills = set(_loaded_skill_names(context.get("loaded_skill")))
    estimated_mode = planner.get("estimated_response_mode")
    workflow_ready = bool(workflow.get("is_ready") or (workflow.get("workflow_state_v2") or {}).get("is_ready") or reasoning.get("workflow_ready"))

    decision = LLMDecision(
        should_use_llm=False,
        response_mode="workflow",
        reason="Workflow can answer directly.",
    )

    if missing_information:
        decision.reason = "Workflow still needs structured information before any language generation."
    elif task_type in DETERMINISTIC_TASKS or workflow_name in DETERMINISTIC_WORKFLOWS:
        decision.reason = "Deterministic workflow is the source of truth for this task."
    elif reasoning.get("action") in {"receipt_uploaded_ack", "receipt_ocr_pending", "continue_workflow"} and not (
        workflow_ready and (task_type == "Content Plan" or workflow_name == "CONTENT_PLAN")
    ):
        decision.reason = "Reasoning selected a workflow response."
    elif task_type in LANGUAGE_TASKS or capability_name in LANGUAGE_CAPABILITIES or intent in LANGUAGE_INTENTS:
        decision = LLMDecision(
            should_use_llm=True,
            response_mode="llm",
            reason="Language generation adds value for this request.",
            source_of_truth="planner",
        )
    elif task_type == "Content Plan" or workflow_name == "CONTENT_PLAN" or "content_creation" in loaded_skills:
        decision = LLMDecision(
            should_use_llm=True,
            response_mode="llm",
            reason="Content creation needs natural language generation.",
            source_of_truth="workflow",
        )
    elif estimated_mode == "llm" or _contains_language_request(message):
        decision = LLMDecision(
            should_use_llm=True,
            response_mode="llm",
            reason="Planner classified this as a language-generation response.",
            source_of_truth="planner",
        )

    decision.latency_ms = int((perf_counter() - started) * 1000)
    return decision.to_dict()


def should_use_llm(reasoning_context: dict | None) -> bool:
    return bool(decide_llm_usage(reasoning_context).get("should_use_llm"))


def compact_prompt_context(reasoning_context: dict | None) -> dict:
    context = reasoning_context or {}
    return {
        "planner_output": context.get("planner_output") or {},
        "workflow": context.get("workflow") or {},
        "business_context": context.get("business_context") or {},
        "conversation_summary": context.get("conversation_summary") or {},
        "store_profile": _compact_dict(context.get("store_profile") or {}),
        "business_memory": context.get("business_memory") or {},
        "current_goal": context.get("current_goal") or {},
        "missing_information": context.get("missing_information") or [],
        "current_task": context.get("current_task"),
        "capability": context.get("capability") or {},
        "loaded_skill": context.get("loaded_skill") or [],
    }
