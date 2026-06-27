import json
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st

from billing.budget_guard import DAILY_BUDGET_USD, can_call_llm, get_llm_usage_state, record_llm_call
from brain.business_insight_engine import analyze_business_insights
from brain.business_diagnosis_engine import diagnose_business_status
from brain.business_memory_engine import load_business_memory, save_business_event
from brain.business_os_engine import build_business_os_state
from brain.campaign_engine import generate_sales_campaign
from brain.chat_companion_engine import generate_chat_response
from brain.chat_intelligence_engine import analyze_chat_intent
from brain.conversation_intent_engine import (
    detect_conversation_intent,
    get_conversation_mode,
    is_product_feedback,
    should_show_business_insights,
    should_use_business_context,
)
from brain.conversation_understanding_engine import (
    build_direct_reply as build_understanding_direct_reply,
    should_answer_directly,
    understand_conversation,
)
from brain.conversation_workflow_engine import (
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_PRODUCT_FEEDBACK,
    WORKFLOW_RECEIPT_CAPTURE,
    detect_workflow,
)
from brain.workflow_state_machine import (
    detect_workflow_intent,
    update_workflow_state,
)
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN as V2_WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION as V2_WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST as V2_WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE as V2_WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY as V2_WORKFLOW_SALES_PLAN_7_DAY,
)
from brain.content_calendar_engine import generate_content_calendar
from brain.content_strategy_engine import get_content_strategy
from brain.goal_engine import (
    create_business_goal,
    evaluate_business_goal,
    get_active_business_goal,
)
from brain.llm_context_builder import build_llm_context
from brain.promotion_engine import get_promotion_idea
from brain.reasoning_engine import build_reasoning
from brain.response_cleaner import clean_response, localize_internal_labels
from brain.response_intelligence_engine import guard_response, select_planner_first_response
from brain.sales_strategy_engine import get_sales_strategy
from brain.sme_companion_engine import generate_sme_companion
from brain.task_router import build_task_route, developer_diagnostics
from content_engine import generate_content_plan, generate_sales_brief
from demo.demo_loader import inject_demo_store_to_session, list_demo_stores
from feedback.chatgpt_export_builder import (
    JSON_EXPORT_PATH,
    MARKDOWN_EXPORT_PATH,
    build_chatgpt_markdown_report,
    build_product_report_data,
    save_json_report,
    save_markdown_report,
)
from feedback.conversation_replay import build_problem_conversation_replay
from feedback.developer_alert_engine import (
    build_smart_warnings,
    build_system_health,
    collect_developer_alerts,
)
from feedback.product_learning_engine import prepare_dashboard_data, record_product_feedback
from feedback.sprint_recommendation_engine import recommend_next_sprint
from feedback.trend_engine import generate_trends
from llm.llm_router import generate_llm_response, is_llm_available, provider_has_api_key
from llm.prompt_context_builder import build_prompt_context
from memory.application_state import application_state, ensure_application_state
from memory.auth import authenticate, create_user, has_users, normalize_owner_id, session_for_owner, update_user_profile
from memory.receipt_state import ensure_receipt_state, mark_receipt_uploaded
from memory.receipt_storage import save_uploaded_receipt
from memory.store_profile_storage import (
    clear_store_profile as clear_persistent_store_profile,
    load_store_profile as load_persistent_store_profile,
    save_store_profile as save_persistent_store_profile,
)
from memory.store_memory import (
    get_content_history,
    get_recent_topics,
    save_generated_content,
    save_store_profile as save_store_memory_profile,
)


st.set_page_config(
    page_title="ผู้ช่วยธุรกิจของคุณ",
    page_icon="🏪",
    layout="centered",
)

DEMO_LLM_TOKEN_LIMIT = 4000

TONE_OPTIONS = ["เป็นกันเอง", "น่าเชื่อถือ", "สนุกสนาน", "หรูหรา", "อบอุ่น"]

CONTENT_TYPE_LABELS = {
    "promotion": "โปรโมชัน",
    "behind_the_scenes": "เบื้องหลังร้าน",
    "behind the scenes": "เบื้องหลังร้าน",
    "product_education": "ความรู้เกี่ยวกับสินค้า",
    "product education": "ความรู้เกี่ยวกับสินค้า",
    "social_proof": "รีวิวลูกค้า",
    "social proof": "รีวิวลูกค้า",
    "urgency_campaign": "กระตุ้นการตัดสินใจ",
    "urgency campaign": "กระตุ้นการตัดสินใจ",
}


def _content_type_label(content_type: str) -> str:
    normalized = (content_type or "").strip()
    return CONTENT_TYPE_LABELS.get(normalized, normalized)


st.markdown(
    """
<style>
    :root {
        --sme-bg: #f7f4ef;
        --sme-surface: #ffffff;
        --sme-surface-soft: #fbfaf7;
        --sme-primary: #4f46e5;
        --sme-primary-dark: #3730a3;
        --sme-blue: #2563eb;
        --sme-green: #16a34a;
        --sme-orange: #f97316;
        --sme-text: #1f2937;
        --sme-muted: #6b7280;
        --sme-border: #e8e2d8;
        --sme-shadow: 0 16px 40px rgba(31, 41, 55, 0.08);
        --sme-radius: 20px;
    }

    html, body, [class*="css"] {
        font-family: "Inter", "Noto Sans Thai", "Sarabun", "Tahoma", sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 0%, rgba(79, 70, 229, 0.10), transparent 30%),
            radial-gradient(circle at 88% 8%, rgba(249, 115, 22, 0.10), transparent 28%),
            var(--sme-bg);
        color: var(--sme-text);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 980px;
    }

    .sme-hero {
        background: linear-gradient(135deg, #4338ca 0%, #2563eb 58%, #14b8a6 100%);
        border-radius: 28px;
        box-shadow: var(--sme-shadow);
        color: #ffffff;
        padding: 34px 34px 30px;
        margin-bottom: 22px;
        overflow: hidden;
    }

    .sme-hero h1 {
        font-size: clamp(2.1rem, 5vw, 4rem);
        line-height: 1.05;
        margin: 0 0 10px;
        letter-spacing: 0;
    }

    .sme-hero .subtitle {
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .sme-hero .promise {
        color: rgba(255, 255, 255, 0.90);
        font-size: 1rem;
        max-width: 680px;
        margin: 0;
    }

    .sme-section-title {
        font-size: 1.28rem;
        font-weight: 800;
        color: var(--sme-text);
        margin: 18px 0 10px;
    }

    .sme-action-area {
        display: none;
    }

    div[data-testid="stForm"] {
        border: 0;
        background: transparent;
        padding: 0;
    }

    div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
        min-height: 3.35rem;
        border-radius: 16px;
        border: 0;
        background: linear-gradient(135deg, var(--sme-primary), var(--sme-blue));
        color: #ffffff;
        font-size: 1rem;
        font-weight: 800;
        box-shadow: 0 12px 26px rgba(79, 70, 229, 0.22);
    }

    div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
        background: linear-gradient(135deg, var(--sme-primary-dark), var(--sme-blue));
        color: #ffffff;
        border: 0;
    }

    .stButton > button {
        border-radius: 16px;
        min-height: 3rem;
        border: 0;
        background: linear-gradient(135deg, var(--sme-primary), var(--sme-blue));
        color: #ffffff;
        font-weight: 800;
        box-shadow: 0 12px 26px rgba(79, 70, 229, 0.20);
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, var(--sme-primary-dark), var(--sme-blue));
        color: #ffffff;
        border: 0;
    }

    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid var(--sme-border);
        border-radius: 18px;
        box-shadow: 0 10px 28px rgba(31, 41, 55, 0.05);
        margin-bottom: 12px;
    }

    div[data-testid="stChatMessage"] {
        background: transparent;
        border: 0;
        border-radius: 8px;
        padding: 4px 0;
        margin: 10px 0;
    }

    div[data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] {
        background: #111111;
        color: #111111;
        width: 22px;
        height: 22px;
        min-width: 22px;
        border-radius: 50%;
        box-shadow: 0 0 0 4px rgba(17, 17, 17, 0.06);
    }

    div[data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"]:has(svg),
    div[data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] svg {
        display: none;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
        line-height: 1.62;
    }

    .sme-thinking-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #111111;
        animation: sme-pulse 1.1s ease-in-out infinite;
    }

    @keyframes sme-pulse {
        0%, 100% { opacity: .35; transform: scale(.86); }
        50% { opacity: 1; transform: scale(1); }
    }

    [data-testid="stChatInput"] {
        border-radius: 18px;
    }

    .sme-command-welcome {
        background: #ffffff;
        border: 1px solid var(--sme-border);
        border-radius: 8px;
        box-shadow: var(--sme-shadow);
        padding: 24px;
        margin: 8px 0 18px;
    }

    .sme-command-welcome h2 {
        font-size: 1.65rem;
        line-height: 1.2;
        margin: 6px 0 10px;
        letter-spacing: 0;
    }

    .sme-command-welcome p {
        color: var(--sme-text);
        margin: 0 0 18px;
        white-space: pre-line;
    }

    .sme-kicker {
        color: var(--sme-primary-dark);
        font-size: .8rem;
        font-weight: 900;
        letter-spacing: .06em;
        text-transform: uppercase;
    }

    .sme-brief-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
    }

    .sme-brief-grid div {
        background: var(--sme-surface-soft);
        border: 1px solid var(--sme-border);
        border-radius: 8px;
        padding: 12px;
        min-height: 112px;
    }

    .sme-brief-grid span {
        display: block;
        color: var(--sme-muted);
        font-size: .78rem;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .sme-brief-grid strong {
        display: block;
        color: var(--sme-text);
        font-size: .96rem;
        line-height: 1.35;
    }

    .sme-chat-prompts {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 4px 0 12px;
    }

    .sme-chat-prompts span {
        border: 1px solid var(--sme-border);
        border-radius: 999px;
        background: #ffffff;
        color: var(--sme-text);
        font-size: .86rem;
        font-weight: 700;
        padding: 7px 11px;
    }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }

        .sme-hero {
            padding: 26px 22px;
            border-radius: 22px;
        }

        .sme-brief-grid {
            grid-template-columns: 1fr;
        }

    }
</style>
""",
    unsafe_allow_html=True,
)


def _tone_index(tone: str) -> int:
    return TONE_OPTIONS.index(tone) if tone in TONE_OPTIONS else 0


HTML_FRAGMENT_RE = re.compile(r"</?(?:div|section|span|p|h[1-6]|style)\b", re.IGNORECASE)


def _render_markdown(content: str) -> None:
    if HTML_FRAGMENT_RE.search(content):
        st.markdown(content, unsafe_allow_html=True)
    else:
        st.markdown(content)


def _stream_text(content: str):
    for token in re.split(r"(\s+)", str(content or "")):
        if token:
            yield token
            time.sleep(0.006)


def _render_assistant_response(content: str, stream: bool = True) -> None:
    if stream and not HTML_FRAGMENT_RE.search(str(content or "")):
        st.write_stream(_stream_text(content))
    else:
        _render_markdown(content)


def _format_baht(value) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0

    if amount.is_integer():
        return f"{amount:,.0f} บาท"
    return f"{amount:,.2f} บาท"


def _format_number(value) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "0"
    if amount.is_integer():
        return f"{amount:,.0f}"
    return f"{amount:,.2f}".rstrip("0").rstrip(".")


def _valid_inputs(
    store_name: str,
    store_type: str,
    product: str,
    target_customer: str,
) -> bool:
    return all(
        [
            store_name.strip(),
            store_type.strip(),
            product.strip(),
            target_customer.strip(),
        ]
    )


def _build_profile(
    store_name: str,
    store_type: str,
    product: str,
    target_customer: str,
    tone: str,
) -> dict | None:
    if not _valid_inputs(store_name, store_type, product, target_customer):
        return None

    return {
        "store_name": store_name.strip(),
        "store_type": store_type.strip(),
        "product": product.strip(),
        "target_customer": target_customer.strip(),
        "tone": tone.strip(),
    }


def normalize_store_profile(profile: dict | None, current_store_name: str | None = None) -> dict:
    source = profile if isinstance(profile, dict) else {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    store_name = source.get("store_name") or current_store_name or st.session_state.get("current_store_name") or ""
    customer = source.get("customer") or source.get("target_customer") or ""
    normalized = {
        "store_name": store_name,
        "store_type": "",
        "product": "",
        "customer": customer,
        "channel": "",
        "goal": "",
        "created_at": now,
        "updated_at": now,
        "target_customer": customer,
        "tone": TONE_OPTIONS[0],
    }
    normalized.update(source)
    normalized["store_name"] = normalized.get("store_name") or store_name
    normalized["store_type"] = normalized.get("store_type") or ""
    normalized["product"] = normalized.get("product") or ""
    normalized["customer"] = normalized.get("customer") or normalized.get("target_customer") or ""
    normalized["channel"] = normalized.get("channel") or ""
    normalized["goal"] = normalized.get("goal") or ""
    normalized["created_at"] = normalized.get("created_at") or now
    normalized["updated_at"] = normalized.get("updated_at") or now
    normalized["target_customer"] = normalized.get("target_customer") or normalized.get("customer") or ""
    normalized["tone"] = normalized.get("tone") or TONE_OPTIONS[0]
    return normalized


def _build_companion(profile: dict | None, history: list[dict]) -> dict | None:
    if not profile:
        return None

    profile_topics = [item.get("topic", "") for item in history if item.get("topic")]
    strategy = get_content_strategy(
        store_type=profile["store_type"],
        product=profile["product"],
        target_customer=profile["target_customer"],
        tone=profile["tone"],
    )
    sales_strategy = get_sales_strategy(
        store_type=profile["store_type"],
        product=profile["product"],
        target_customer=profile["target_customer"],
        tone=profile["tone"],
        recent_topics=profile_topics,
    )
    promotion = get_promotion_idea(
        store_type=profile["store_type"],
        product=profile["product"],
        target_customer=profile["target_customer"],
        sales_strategy=sales_strategy,
    )
    business_insight = analyze_business_insights(profile, history)

    return generate_sme_companion(
        store_profile=profile,
        strategy=strategy,
        sales_strategy=sales_strategy,
        promotion=promotion,
        business_insight=business_insight,
        recent_topics=profile_topics,
    )


DEFAULT_CONVERSATION_STATE = {
    "current_topic": None,
    "business_type": None,
    "latest_business_goal": None,
    "last_question": None,
    "last_answer": None,
    "follow_up_expected": False,
    "last_intent": None,
    "previous_intent": None,
    "conversation_stage": "new",
    "last_feedback": None,
    "last_correction": None,
    "greeted": False,
    "current_workflow": None,
    "workflow_step": None,
    "workflow_data": {},
    "workflow_started_at": None,
    "last_workflow_message": None,
    "workflow_state_v2": {},
    "workflow_blocked_phrases": {},
}


def _new_conversation_state() -> dict:
    state = dict(DEFAULT_CONVERSATION_STATE)
    state["workflow_data"] = {}
    state["workflow_state_v2"] = {}
    state["workflow_blocked_phrases"] = {}
    return state


def _chat_avatar(role: str) -> str | None:
    return "\u25cf" if role == "assistant" else None


def _get_application_state() -> dict:
    state = st.session_state.setdefault("application_state", application_state)
    ensure_application_state(state)
    return state


def _sync_global_application_state() -> dict:
    state = _get_application_state()
    application_state.clear()
    application_state.update(state)
    return state


def _update_application_section(section: str, values: dict | None) -> dict:
    state = _get_application_state()
    state.setdefault(section, {})
    if values:
        state[section].update(values)
    return _sync_global_application_state()


def _sync_chat_history_to_application_state() -> None:
    _update_application_section(
        "conversation",
        {
            "conversation_id": st.session_state.get("conversation_id"),
            "chat_history": st.session_state.get("chat_history", []),
        },
    )


def _sync_session_to_application_state() -> dict:
    state = _get_application_state()
    conversation_state = st.session_state.get("conversation_state") or _new_conversation_state()
    workflow_state_v2 = conversation_state.get("workflow_state_v2") or {}
    state["conversation"] = {
        **(state.get("conversation") or {}),
        **conversation_state,
        "conversation_id": st.session_state.get("conversation_id"),
        "chat_history": st.session_state.get("chat_history", []),
        "pending_followup": st.session_state.get("pending_followup"),
    }
    state["workflow"] = {
        **(state.get("workflow") or {}),
        "current_workflow": conversation_state.get("current_workflow"),
        "workflow_step": conversation_state.get("workflow_step"),
        "workflow_data": conversation_state.get("workflow_data") or {},
        "workflow_state_v2": workflow_state_v2,
        "workflow": workflow_state_v2.get("workflow") or conversation_state.get("current_workflow"),
        "step": workflow_state_v2.get("step") or conversation_state.get("workflow_step"),
        "is_ready": bool(workflow_state_v2.get("is_ready")),
        "last_workflow_message": conversation_state.get("last_workflow_message"),
    }
    state["receipt"] = ensure_receipt_state(state.get("receipt"))
    state["ui"] = {
        **(state.get("ui") or {}),
        "demo_mode": bool(st.session_state.get("demo_mode")),
        "llm_response_mode": st.session_state.get("llm_response_mode", "Workflow Only"),
    }
    state["developer"] = {
        **(state.get("developer") or {}),
        "developer_mode": bool(st.session_state.get("developer_mode")),
        "use_llm_companion": bool(st.session_state.get("use_llm_companion")),
        "llm_response_mode": st.session_state.get("llm_response_mode", "Workflow Only"),
    }
    return _sync_global_application_state()


def _record_reasoning(user_message: str) -> dict:
    state = _sync_session_to_application_state()
    task_route = build_task_route(state, user_message)
    reasoning = task_route.get("reasoning") or build_reasoning(state, user_message)
    st.session_state["last_task_route"] = task_route
    st.session_state["last_reasoning"] = reasoning
    _update_application_section(
        "developer",
        {
            "task_route": task_route,
            "planner_output": task_route.get("planner_output"),
            "selected_capability": task_route.get("selected_capability"),
            "loaded_skills": task_route.get("loaded_skills"),
            "reasoning_mode": task_route.get("reasoning_mode"),
            "capability_available": bool(task_route.get("capability_available")),
            "reasoning_result": reasoning,
            "conversation_understanding": task_route.get("conversation_understanding"),
            "current_action": reasoning.get("action"),
            "llm_needed": bool(reasoning.get("llm_needed")),
            "workflow_ready": bool(reasoning.get("workflow_ready")),
        },
    )
    return reasoning


def _sync_route_intelligence_to_session(route: dict | None) -> None:
    route = route or {}
    conversation_state = _ensure_conversation_state()
    business_context = route.get("business_context") or {}
    memory_context = route.get("conversation_memory") or {}
    intent_resolution = route.get("intent_resolution") or {}
    if business_context.get("business_type"):
        conversation_state["business_type"] = business_context.get("business_type")
    if business_context.get("current_discussion_topic"):
        conversation_state["current_topic"] = business_context.get("current_discussion_topic")
    if intent_resolution.get("resolved_intent"):
        conversation_state["previous_intent"] = conversation_state.get("last_intent")
        conversation_state["last_intent"] = intent_resolution.get("resolved_intent")
    _update_application_section(
        "conversation",
        {
            **conversation_state,
            "conversation_memory": memory_context,
            "business_context": business_context,
            "intent_resolution": intent_resolution,
            "conversation_intelligence": route.get("conversation_intelligence") or {},
        },
    )
    _update_application_section("business_context", business_context)


def _loaded_skill_names(route: dict | None) -> list[str]:
    names = []
    for skill in (route or {}).get("loaded_skills") or []:
        name = skill.get("name") if isinstance(skill, dict) else None
        if name:
            names.append(name)
    return names


def _selected_capability_name(route: dict | None):
    capability = (route or {}).get("selected_capability")
    if isinstance(capability, dict):
        return capability.get("name")
    return capability


def _workflow_debug_state(extra: dict | None = None) -> dict:
    conversation_state = st.session_state.get("conversation_state") or {}
    workflow_state_v2 = conversation_state.get("workflow_state_v2") or {}
    app_workflow = (_sync_session_to_application_state().get("workflow") or {})
    state = {
        "current_workflow": conversation_state.get("current_workflow") or app_workflow.get("current_workflow"),
        "workflow_step": conversation_state.get("workflow_step") or app_workflow.get("workflow_step"),
        "workflow_data": conversation_state.get("workflow_data") or app_workflow.get("workflow_data") or {},
        "workflow_state_v2": workflow_state_v2 or app_workflow.get("workflow_state_v2") or {},
        "route": app_workflow.get("workflow") or conversation_state.get("current_workflow"),
        "step": app_workflow.get("step") or conversation_state.get("workflow_step"),
        "is_ready": bool(app_workflow.get("is_ready") or workflow_state_v2.get("is_ready")),
    }
    if extra:
        state.update(extra)
    return state


def _new_ai_pipeline_debug_trace(user_message: str, conversation_understanding: dict | None) -> dict:
    understanding = conversation_understanding or {}
    return {
        "raw_user_message": user_message,
        "conversation_understanding": {
            "intent": understanding.get("detected_intent") or understanding.get("intent") or understanding.get("legacy_intent"),
            "confidence": understanding.get("confidence"),
            "requires_clarification": understanding.get("requires_clarification"),
            "references": understanding.get("references"),
            "planner_message": understanding.get("planner_message"),
        },
        "planner": {
            "task_type": None,
        },
        "selected_capability": None,
        "loaded_skill_names": [],
        "workflow": _workflow_debug_state(),
        "response_source": None,
        "final_response_preview": None,
    }


def _update_ai_pipeline_debug_trace_from_route(trace: dict, route: dict | None) -> dict:
    route = route or {}
    planner = route.get("planner_output") or {}
    trace["planner"] = {
        "task_type": route.get("task_type") or planner.get("task_type"),
        "next_step": planner.get("next_step"),
        "estimated_response_mode": planner.get("estimated_response_mode"),
        "missing_information": planner.get("missing_information") or [],
        "can_execute": planner.get("can_execute"),
    }
    trace["selected_capability"] = _selected_capability_name(route)
    trace["loaded_skill_names"] = _loaded_skill_names(route)
    trace["reasoning"] = route.get("reasoning") or {}
    trace["reasoning_mode"] = route.get("reasoning_mode")
    return trace


def _is_generic_fallback_reply(reply: str | None) -> bool:
    text = str(reply or "")
    return "เล่าเพิ่มอีกนิด" in text or "à¹€à¸¥à¹ˆà¸²à¹€à¸žà¸´à¹ˆà¸¡à¸­à¸µà¸à¸™à¸´à¸”" in text


def _finalize_ai_pipeline_debug_trace(
    trace: dict | None,
    response_source: str,
    final_reply: str | None,
    workflow_extra: dict | None = None,
) -> dict | None:
    if not trace:
        return None
    source = "generic_fallback" if _is_generic_fallback_reply(final_reply) else response_source
    trace["workflow"] = _workflow_debug_state(workflow_extra)
    trace["response_source"] = source
    trace["final_response_preview"] = str(final_reply or "").strip()[:500]
    st.session_state["ai_pipeline_debug_trace"] = trace
    if st.session_state.get("developer_mode"):
        print("AI Pipeline Debug Trace:")
        print(json.dumps(trace, ensure_ascii=False, indent=2, default=str))
    return trace


# Future hooks. These are intentionally placeholders only.
def _future_engine_hooks() -> dict:
    return {
        "ocr_engine": None,
        "inventory_engine": None,
        "sales_forecast_engine": None,
        "business_memory": None,
        "marketing_agent": None,
        "financial_agent": None,
        "inventory_agent": None,
    }


def _ensure_conversation_state() -> dict:
    state = st.session_state.setdefault("conversation_state", _new_conversation_state())
    for key, value in DEFAULT_CONVERSATION_STATE.items():
        state.setdefault(key, value)
    _update_application_section("conversation", state)
    return state


def _reset_conversation_memory() -> None:
    st.session_state["conversation_state"] = _new_conversation_state()
    st.session_state["pending_followup"] = None
    _sync_session_to_application_state()


def _reset_chat_session() -> None:
    st.session_state["chat_history"] = []
    st.session_state["conversation_id"] = str(uuid4())
    st.session_state["last_reasoning"] = None
    st.session_state["cached_prompt"] = None
    st.session_state["last_ai_state"] = None
    _reset_conversation_memory()
    _sync_session_to_application_state()


def _init_session_state() -> None:
    st.session_state.setdefault("application_state", application_state)
    ensure_application_state(st.session_state["application_state"])
    st.session_state.setdefault("demo_mode", False)
    st.session_state.setdefault("store_source", None)
    st.session_state.setdefault("selected_demo_store", None)
    st.session_state.setdefault("demo_llm_tokens_used", 0)
    st.session_state.setdefault("demo_first_ai_success_shown", False)
    st.session_state.setdefault("show_manual_store_setup", False)
    st.session_state.setdefault("manual_store_restored", False)
    st.session_state.setdefault("manual_store_storage_status", None)
    st.session_state.setdefault("manual_store_created_at", None)
    st.session_state.setdefault("llm_usage_daily", {})
    st.session_state.setdefault("llm_usage_monthly", {})
    st.session_state.setdefault("generated_daily", None)
    st.session_state.setdefault("generated_calendar", None)
    st.session_state.setdefault("generated_revenue", None)
    st.session_state.setdefault("conversation_id", str(uuid4()))
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("last_reasoning", None)
    st.session_state.setdefault("cached_prompt", None)
    st.session_state.setdefault("last_ai_state", None)
    st.session_state.setdefault("pending_followup", None)
    st.session_state.setdefault("ai_pipeline_debug_trace", {})
    st.session_state.setdefault("active_store_name", "")
    st.session_state.setdefault("last_diagnosis_signature", "")
    st.session_state.setdefault("use_llm_companion", False)
    st.session_state.setdefault("llm_response_mode", "Workflow Only")
    st.session_state.setdefault("developer_mode", False)
    st.session_state.setdefault("auth_session", {})
    st.session_state.setdefault("auth_owner_id", None)
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("current_owner_id", None)
    st.session_state.setdefault("current_store_id", None)
    st.session_state.setdefault("current_store_name", None)
    _get_application_state()["receipt"] = ensure_receipt_state(_get_application_state().get("receipt"))
    _get_application_state()["developer"].setdefault("future_hooks", _future_engine_hooks())
    _ensure_conversation_state()
    _sync_session_to_application_state()


MANUAL_STORE_SESSION_KEYS = (
    "store_profile",
    "business_memory",
    "business_goals",
    "business_diagnosis",
    "business_os",
    "knowledge_layer",
    "manual_store_created_at",
    "manual_store_restored",
    "manual_store_storage_status",
)


def _is_manual_store_active() -> bool:
    return (
        not bool(st.session_state.get("demo_mode"))
        and st.session_state.get("store_source") == "manual"
        and bool(st.session_state.get("store_profile"))
    )


def _current_owner_id() -> str | None:
    if not st.session_state.get("authenticated"):
        return None
    return st.session_state.get("current_owner_id")


def _current_store_id() -> str | None:
    if not st.session_state.get("authenticated"):
        return None
    return st.session_state.get("current_store_id")


def _is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated") and _current_owner_id() and _current_store_id())


def _clear_authenticated_store_session() -> None:
    for key in MANUAL_STORE_SESSION_KEYS:
        st.session_state.pop(key, None)
    st.session_state["store_source"] = None
    st.session_state["store_profile"] = None
    st.session_state["active_store_name"] = ""
    st.session_state["generated_daily"] = None
    st.session_state["generated_calendar"] = None
    st.session_state["generated_revenue"] = None
    st.session_state["last_diagnosis_signature"] = ""
    _reset_chat_session()
    app_state = _get_application_state()
    app_state["store"] = {}
    app_state["dashboard"] = {}
    _sync_global_application_state()


def _set_authenticated_session(auth_result: dict) -> None:
    auth_session = session_for_owner(
        auth_result["owner_id"],
        store_id=auth_result.get("store_id"),
        store_name=auth_result.get("store_name"),
        username=auth_result.get("username"),
    )
    st.session_state["auth_session"] = auth_session
    st.session_state["auth_owner_id"] = auth_session["owner_id"]
    st.session_state["authenticated"] = True
    st.session_state["current_user"] = auth_session["username"]
    st.session_state["current_owner_id"] = auth_session["owner_id"]
    st.session_state["current_store_id"] = auth_session["store_id"]
    st.session_state["current_store_name"] = auth_session["store_name"]


def _show_first_run_setup() -> None:
    st.markdown("### ตั้งค่าร้านแรก")
    st.caption("สร้างบัญชีเจ้าของร้านแรกเพื่อเริ่มใช้งาน SME Companion")

    store_name = st.text_input("ชื่อร้าน")
    username = st.text_input("ชื่อผู้ใช้")
    password = st.text_input("รหัสผ่าน", type="password")
    confirm_password = st.text_input("ยืนยันรหัสผ่าน", type="password")

    if not st.button("สร้างร้านและเข้าสู่ระบบ", use_container_width=True):
        st.stop()

    clean_store_name = str(store_name or "").strip()
    clean_username = str(username or "").strip()
    normalized_username = normalize_owner_id(clean_username)

    if not clean_store_name or not clean_username or not password or not confirm_password:
        st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")
        st.stop()
    if clean_username != normalized_username:
        st.error("ชื่อผู้ใช้ต้องใช้ตัวอักษรอังกฤษ ตัวเลข จุด ขีดกลาง หรือขีดล่างเท่านั้น และต้องเป็นตัวพิมพ์เล็ก")
        st.stop()
    if password != confirm_password:
        st.error("รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน")
        st.stop()

    created = create_user(normalized_username, password)
    if not created.get("ok"):
        st.error("ไม่สามารถสร้างบัญชีแรกได้ กรุณาตรวจสอบชื่อผู้ใช้และรหัสผ่าน")
        st.stop()

    owner_id = created["owner_id"]
    store_id = owner_id
    updated = update_user_profile(owner_id, store_id=store_id, store_name=clean_store_name, username=owner_id)
    if not updated.get("ok"):
        st.error("สร้างบัญชีแล้ว แต่ไม่สามารถบันทึกข้อมูลร้านได้")
        st.stop()

    profile = normalize_store_profile({"store_name": clean_store_name}, current_store_name=clean_store_name)
    save_persistent_store_profile(
        {
            "store_source": "manual",
            "store_profile": profile,
        },
        owner_id=owner_id,
        store_id=store_id,
    )

    _set_authenticated_session(
        {
            "owner_id": owner_id,
            "username": owner_id,
            "store_id": store_id,
            "store_name": clean_store_name,
        }
    )
    st.session_state["demo_mode"] = False
    st.session_state["selected_demo_store"] = None
    st.session_state["store_source"] = "manual"
    st.session_state["store_profile"] = profile
    st.session_state["active_store_name"] = clean_store_name.strip().lower()
    st.session_state["manual_store_storage_status"] = "saved"
    saved_data = load_persistent_store_profile(owner_id, store_id) or {}
    st.session_state["manual_store_created_at"] = saved_data.get("created_at")
    st.session_state["manual_store_restored"] = True
    _update_application_section(
        "store",
        {
            "active_store_name": st.session_state["active_store_name"],
            "profile": profile,
            "store_source": "manual",
        },
    )
    st.rerun()


def _show_auth_gate() -> None:
    if _is_authenticated():
        return

    st.session_state["authenticated"] = False
    st.session_state["demo_mode"] = False
    st.session_state["developer_mode"] = False
    _clear_authenticated_store_session()

    if not has_users():
        _show_first_run_setup()

    st.markdown("### เข้าสู่ระบบ SME Companion")
    st.caption("กรุณาเข้าสู่ระบบก่อนใช้งานข้อมูลร้านจริง")
    username = st.text_input("ชื่อผู้ใช้")
    password = st.text_input("รหัสผ่าน", type="password")

    if st.button("เข้าสู่ระบบ", use_container_width=True):
        result = authenticate(username, password)
        if result.get("ok"):
            _set_authenticated_session(result)
            st.rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    st.stop()


def _show_logout_control() -> None:
    owner_id = _current_owner_id()
    if not owner_id:
        return
    st.sidebar.caption(f"Signed in: {owner_id}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state["auth_session"] = {}
        st.session_state["auth_owner_id"] = None
        st.session_state["authenticated"] = False
        st.session_state["current_user"] = None
        st.session_state["current_owner_id"] = None
        st.session_state["current_store_id"] = None
        st.session_state["current_store_name"] = None
        st.session_state["demo_mode"] = False
        st.session_state["developer_mode"] = False
        _clear_authenticated_store_session()
        st.rerun()


def _manual_store_profile() -> dict | None:
    if _is_manual_store_active():
        return st.session_state.get("store_profile") or {}
    return None


def _restore_manual_store_profile() -> bool:
    if st.session_state.get("demo_mode") or _is_manual_store_active() or not _is_authenticated():
        return False

    store_data = load_persistent_store_profile(_current_owner_id(), _current_store_id())
    if not store_data:
        return False

    raw_profile = store_data.get("store_profile") or {}
    profile = normalize_store_profile(raw_profile)
    if profile != raw_profile:
        store_data = {**store_data, "store_profile": profile}
        save_persistent_store_profile(store_data, owner_id=_current_owner_id(), store_id=_current_store_id())
        store_data = load_persistent_store_profile(_current_owner_id(), _current_store_id()) or store_data
    st.session_state["demo_mode"] = False
    st.session_state["selected_demo_store"] = None
    st.session_state["store_source"] = "manual"
    st.session_state["store_profile"] = profile
    st.session_state["business_memory"] = store_data.get("business_memory") or {}
    st.session_state["business_goals"] = store_data.get("business_goals") or {}
    st.session_state["business_diagnosis"] = store_data.get("business_diagnosis") or {}
    st.session_state["business_os"] = store_data.get("business_os") or {}
    st.session_state["knowledge_layer"] = store_data.get("knowledge_layer") or {}
    st.session_state["manual_store_created_at"] = store_data.get("created_at")
    st.session_state["manual_store_restored"] = True
    st.session_state["manual_store_storage_status"] = "restored"
    st.session_state["show_manual_store_setup"] = False
    st.session_state["active_store_name"] = str(profile.get("store_name", "")).strip().lower()
    st.session_state["current_store_name"] = profile.get("store_name") or st.session_state.get("current_store_name")
    _update_application_section(
        "store",
        {
            "active_store_name": st.session_state["active_store_name"],
            "profile": profile,
            "store_source": "manual",
        },
    )
    return True


def _manual_store_payload(
    profile: dict,
    *,
    business_memory: dict | None = None,
    business_goals: dict | None = None,
    business_diagnosis: dict | None = None,
    business_os: dict | None = None,
    knowledge_layer: dict | None = None,
) -> dict:
    existing = load_persistent_store_profile(_current_owner_id(), _current_store_id()) or {}
    return {
        "store_source": "manual",
        "store_profile": normalize_store_profile(profile),
        "business_memory": business_memory if business_memory is not None else st.session_state.get("business_memory", {}),
        "business_goals": business_goals if business_goals is not None else st.session_state.get("business_goals", {}),
        "business_diagnosis": business_diagnosis if business_diagnosis is not None else st.session_state.get("business_diagnosis", {}),
        "business_os": business_os if business_os is not None else st.session_state.get("business_os", {}),
        "knowledge_layer": knowledge_layer if knowledge_layer is not None else st.session_state.get("knowledge_layer", {}),
        "created_at": st.session_state.get("manual_store_created_at") or existing.get("created_at"),
    }


def _save_manual_store_profile(
    profile: dict | None = None,
    *,
    business_memory: dict | None = None,
    business_goals: dict | None = None,
    business_diagnosis: dict | None = None,
    business_os: dict | None = None,
    knowledge_layer: dict | None = None,
) -> None:
    if st.session_state.get("demo_mode"):
        return
    if not _is_authenticated():
        return
    raw_active_profile = profile or st.session_state.get("store_profile")
    if not raw_active_profile:
        return
    active_profile = normalize_store_profile(raw_active_profile)

    st.session_state["store_source"] = "manual"
    st.session_state["store_profile"] = active_profile
    st.session_state["current_store_name"] = active_profile.get("store_name") or st.session_state.get("current_store_name")
    if business_memory is not None:
        st.session_state["business_memory"] = business_memory
    if business_goals is not None:
        st.session_state["business_goals"] = business_goals
    if business_diagnosis is not None:
        st.session_state["business_diagnosis"] = business_diagnosis
    if business_os is not None:
        st.session_state["business_os"] = business_os
    if knowledge_layer is not None:
        st.session_state["knowledge_layer"] = knowledge_layer

    payload = _manual_store_payload(
        active_profile,
        business_memory=business_memory,
        business_goals=business_goals,
        business_diagnosis=business_diagnosis,
        business_os=business_os,
        knowledge_layer=knowledge_layer,
    )
    save_persistent_store_profile(payload, owner_id=_current_owner_id(), store_id=_current_store_id())
    saved_data = load_persistent_store_profile(_current_owner_id(), _current_store_id()) or {}
    st.session_state["manual_store_created_at"] = saved_data.get("created_at")
    st.session_state["manual_store_storage_status"] = "saved"


def _clear_manual_store_session() -> None:
    for key in MANUAL_STORE_SESSION_KEYS:
        st.session_state.pop(key, None)
    st.session_state["store_source"] = None
    st.session_state["show_manual_store_setup"] = True
    st.session_state["active_store_name"] = ""
    st.session_state["generated_daily"] = None
    st.session_state["generated_calendar"] = None
    st.session_state["generated_revenue"] = None
    st.session_state["last_diagnosis_signature"] = ""
    _reset_chat_session()
    app_state = _get_application_state()
    app_state["store"] = {}
    app_state["dashboard"] = {}
    _sync_global_application_state()


def _show_manual_store_storage_caption() -> None:
    if st.session_state.get("demo_mode"):
        return
    status = st.session_state.get("manual_store_storage_status")
    if status == "restored":
        st.caption("โหลดข้อมูลร้านเดิมแล้ว")
    elif status == "saved":
        st.caption("บันทึกข้อมูลร้านไว้แล้ว")


def _show_clear_manual_store_control() -> None:
    if not _is_manual_store_active():
        return

    with st.expander("จัดการข้อมูลร้าน", expanded=False):
        confirm_clear = st.checkbox("ยืนยันว่าต้องการล้างข้อมูลร้านนี้", key="confirm_clear_manual_store")
        if st.button("ล้างข้อมูลร้านนี้", disabled=not confirm_clear, use_container_width=True):
            clear_persistent_store_profile(_current_owner_id(), _current_store_id())
            _clear_manual_store_session()
            st.rerun()


def _legacy_reset_conversation_state_for_demo_switch() -> None:
    st.session_state["chat_history"] = []
    st.session_state["conversation_id"] = str(uuid4())
    st.session_state["last_reasoning"] = None
    st.session_state["cached_prompt"] = None
    st.session_state["last_ai_state"] = None
    st.session_state["pending_followup"] = None
    _reset_conversation_memory()
    st.session_state["demo_first_ai_success_shown"] = False
    if st.session_state["chat_history"]:
        st.session_state["chat_history"][0]["content"] = (
        "สวัสดีครับ ผมช่วยคิดเรื่องร้าน การขาย และคอนเทนต์ให้เป็นขั้นตอนสั้นๆ ได้ครับ\n"
        "วันนี้อยากให้ช่วยเรื่องไหนครับ?"
    )
    st.session_state["demo_llm_tokens_used"] = 0
    for key in [
        "llm_context_cache",
        "business_context_cache",
        "cached_llm_context",
        "cached_business_context",
    ]:
        st.session_state.pop(key, None)


def _reset_conversation_state_for_demo_switch() -> None:
    st.session_state["chat_history"] = []
    st.session_state["conversation_id"] = str(uuid4())
    st.session_state["last_reasoning"] = None
    st.session_state["cached_prompt"] = None
    st.session_state["last_ai_state"] = None
    st.session_state["pending_followup"] = None
    _reset_conversation_memory()
    st.session_state["demo_first_ai_success_shown"] = False
    st.session_state["demo_llm_tokens_used"] = 0
    for key in [
        "llm_context_cache",
        "business_context_cache",
        "cached_llm_context",
        "cached_business_context",
    ]:
        st.session_state.pop(key, None)
    _sync_session_to_application_state()


def _content_examples_to_history(content_examples: list[dict]) -> list[dict]:
    history = []
    for item in content_examples or []:
        history.append(
            {
                "created_at": item.get("created_at", "ตัวอย่าง"),
                "topic": item.get("topic", item.get("type", "คอนเทนต์ตัวอย่าง")),
                "content_angle": item.get("caption", ""),
                "strategy_name": item.get("type", "Demo Content"),
                "markdown": item.get("caption", ""),
            }
        )
    return history


def _allow_demo_llm_call(user_message: str, context: dict | None) -> bool:
    used_tokens = int(st.session_state.get("demo_llm_tokens_used") or 0)
    estimated_tokens = max(1, (len(str(user_message or "")) + len(str(context or {}))) // 4)
    if used_tokens + estimated_tokens > DEMO_LLM_TOKEN_LIMIT:
        return False

    st.session_state["demo_llm_tokens_used"] = used_tokens + estimated_tokens
    return True


DEMO_STORE_CARDS = {
    "coffee": {
        "emoji": "☕",
        "description": "ลองดูร้านกาแฟที่ต้องเพิ่มยอดช่วงเช้าและขายเมนูเป็นเซต",
    },
    "restaurant": {
        "emoji": "🍲",
        "description": "ดูตัวอย่างร้านอาหารที่อยากขายชุดกลางวันและอาหารกล่อง",
    },
    "clothing": {
        "emoji": "👗",
        "description": "สำรวจร้านเสื้อผ้าที่ต้องลดความลังเลเรื่องไซซ์และสไตล์",
    },
    "beauty": {
        "emoji": "✨",
        "description": "ลองร้านบิวตี้ที่ต้องสร้างความมั่นใจด้วยรีวิวและวิธีใช้",
    },
    "construction": {
        "emoji": "🧰",
        "description": "ดูร้านวัสดุก่อสร้างที่ต้องจัดชุดสินค้าตามงานซ่อม",
    },
    "online_store": {
        "emoji": "🛒",
        "description": "ลองร้านออนไลน์ที่ต้องตอบแชทเร็วและขายสินค้าเป็นเซต",
    },
}


def _start_demo_store(store_key: str) -> None:
    with st.status("ผู้ช่วย AI กำลังเตรียมร้านตัวอย่าง...", expanded=True) as status:
        demo_data = inject_demo_store_to_session(st, store_key)
        st.session_state["store_source"] = "demo"
        st.write("✓ โหลดข้อมูลร้าน")
        time.sleep(0.2)
        st.write("✓ วิเคราะห์ธุรกิจ")
        time.sleep(0.2)
        st.write("✓ เตรียมผู้ช่วย AI")
        time.sleep(0.2)
        st.write("✓ พร้อมใช้งาน")
        status.update(label="พร้อมใช้งาน", state="complete", expanded=True)

    store_name = (demo_data.get("store_profile") or {}).get("store_name", "")
    _reset_conversation_state_for_demo_switch()
    st.session_state["active_store_name"] = store_name.strip().lower()
    st.session_state["chat_history"] = [
        {
            "role": "assistant",
            "content": (
                "สวัสดีครับ ผมคือผู้ช่วยธุรกิจ ตอนนี้ผมโหลดข้อมูลร้านตัวอย่างเรียบร้อยแล้ว "
                "ลองถามผมได้เลย เช่น วันนี้ควรโพสต์อะไร หรือควรเพิ่มยอดขายยังไง"
            ),
        }
    ]
    _sync_chat_history_to_application_state()
    st.session_state["chat_history"][0]["content"] = (
        "สวัสดีครับ ผมช่วยคิดเรื่องร้าน การขาย และคอนเทนต์ให้เป็นขั้นตอนสั้นๆ ได้ครับ\n"
        "วันนี้อยากให้ช่วยเรื่องไหนครับ?"
    )
    _sync_conversation_business_context(demo_data.get("store_profile") or {}, None, None)
    _update_conversation_state_after_assistant(
        st.session_state["chat_history"][0]["content"],
        "GREETING",
    )
    st.session_state["demo_llm_tokens_used"] = 0
    st.session_state["demo_first_ai_success_shown"] = False


def _show_demo_chat_suggestions() -> None:
    with st.container(border=True):
        st.markdown("**ลองถาม AI เช่น**")
        st.write("- วันนี้ควรโพสต์อะไรดี")
        st.write("- ช่วยคิดโปรโมชันให้ร้านนี้")
        st.write("- ทำไมยอดขายตก")
        st.write("- เดือนนี้ควรโฟกัสอะไร")


def _show_demo_entry() -> None:
    if st.session_state.get("demo_mode"):
        profile = st.session_state.get("store_profile") or {}
        usage = get_llm_usage_state(st)
        st.caption(
            f"งบทดลอง AI วันนี้: ใช้ไป ${usage['daily_used_usd']:.3f} / ${DAILY_BUDGET_USD:.2f}"
        )
        store_name = profile.get("store_name", "ร้านตัวอย่าง")
        st.info(f"กำลังทดลองร้านตัวอย่าง: {store_name}")
        if st.button("เปลี่ยนร้านตัวอย่าง", use_container_width=True):
            _reset_conversation_state_for_demo_switch()
            st.session_state["demo_mode"] = False
            st.session_state["store_source"] = None
            st.session_state["selected_demo_store"] = None
            st.rerun()
        return

    _restore_manual_store_profile()
    if _is_manual_store_active():
        return

    if st.session_state.get("show_manual_store_setup"):
        return

    st.title("ผู้ช่วยธุรกิจของคุณ")
    st.subheader("ผู้ช่วยเจ้าของร้านไทย")
    st.write("ทดลองให้ AI วิเคราะห์ร้าน วางแผนธุรกิจ และช่วยคิดคอนเทนต์ได้ทันที")
    st.caption("ทดลองใช้ฟรี • ไม่ต้องสมัคร • ใช้ได้ทันที")

    st.markdown("### เริ่มทดลองใน 3 ขั้นตอน")
    step_cols = st.columns(3)
    steps = [
        ("1", "เลือกร้านตัวอย่าง"),
        ("2", "ลองถาม AI / สร้างโพสต์ / ดูภาพรวมธุรกิจ"),
        ("3", "ถ้าชอบ กดสร้างร้านของฉัน"),
    ]
    for col, (step_no, step_text) in zip(step_cols, steps):
        with col.container(border=True):
            st.markdown(f"**{step_no}. {step_text}**")

    st.markdown("### เลือกร้านตัวอย่าง")
    demo_stores = list_demo_stores()
    for row_start in range(0, len(demo_stores), 3):
        cols = st.columns(3)
        for col, demo_store in zip(cols, demo_stores[row_start : row_start + 3]):
            card = DEMO_STORE_CARDS.get(demo_store["key"], {})
            with col.container(border=True):
                st.markdown(f"### {card.get('emoji', '🏪')} {demo_store['label']}")
                st.write(card.get("description", "ทดลองให้ AI วิเคราะห์ร้านตัวอย่างนี้"))
                if st.button(
                    "ทดลองร้านนี้",
                    key=f"demo_{demo_store['key']}",
                    use_container_width=True,
                ):
                    _start_demo_store(demo_store["key"])
                    st.rerun()

    st.divider()
    st.markdown("### อยากใช้กับร้านของคุณจริง ๆ?")
    if st.button("สร้างร้านของฉัน", use_container_width=True):
        st.session_state["show_manual_store_setup"] = True
        st.session_state["demo_mode"] = False
        st.session_state["selected_demo_store"] = None
        st.session_state["demo_llm_tokens_used"] = 0
        st.session_state["demo_first_ai_success_shown"] = False
        st.rerun()

    st.stop()


def _show_dashboard(companion: dict | None, os_state: dict | None) -> None:
    st.subheader("ภาพรวมธุรกิจ")
    if not companion:
        st.info("กรอกข้อมูลร้านเพื่อให้ผู้ช่วย AI วิเคราะห์คำแนะนำวันนี้ โอกาส และสิ่งที่ควรทำ")
        return

    score = (
        f"{os_state['business_health_score']}%"
        if os_state and os_state.get("business_health_score") is not None
        else f"{companion['confidence']}%"
    )

    overview_col, recommendation_col = st.columns([1, 2])
    with overview_col.container(border=True):
        st.metric("คะแนนสุขภาพธุรกิจ", score)
        st.caption(f"ความมั่นใจ: {companion['confidence']}%")
    with recommendation_col.container(border=True):
        st.markdown("**คำแนะนำวันนี้**")
        _render_markdown(companion["companion_message"])

    action_col, opportunity_col, risk_col = st.columns(3)
    with action_col.container(border=True):
        st.markdown("**สิ่งที่ควรทำ**")
        _render_markdown((os_state or {}).get("today_action") or companion["priority_action"])
    with opportunity_col.container(border=True):
        st.markdown("**โอกาสเติบโต**")
        _render_markdown((os_state or {}).get("growth_opportunity") or companion["opportunity"])
    with risk_col.container(border=True):
        st.markdown("**ความเสี่ยงหลัก**")
        _render_markdown((os_state or {}).get("current_risk") or companion["warning"])

    if os_state:
        with st.expander("รายละเอียดสถานะร้าน", expanded=False):
            st.markdown("**สถานะร้านตอนนี้**")
            _render_markdown(os_state["operating_status"])
            st.markdown("**เป้าหมายสัปดาห์นี้**")
            _render_markdown(os_state["weekly_focus"])


def _show_business_os(
    profile: dict | None,
    os_state: dict | None,
    active_goal: dict | None,
    goal_status: dict | None,
) -> dict | None:
    with st.expander("แผนงานวันนี้", expanded=False):
        if not profile or not os_state:
            st.info("กรอกข้อมูลร้านเพื่อเปิดระบบบริหารร้านและตั้งเป้าหมายร้าน")
            return None

        score_col, status_col = st.columns([1, 2])
        with score_col.container(border=True):
            st.metric("คะแนนสุขภาพธุรกิจ", f"{os_state['business_health_score']}%")
        with status_col.container(border=True):
            st.markdown("**สถานะร้านตอนนี้**")
            _render_markdown(os_state["operating_status"])

        priority_col, risk_col = st.columns(2)
        with priority_col.container(border=True):
            st.markdown("**สิ่งสำคัญที่สุดวันนี้**")
            _render_markdown(os_state["today_action"])
        with risk_col.container(border=True):
            st.markdown("**ความเสี่ยงหลัก**")
            _render_markdown(os_state["current_risk"])

        opportunity_col, focus_col = st.columns(2)
        with opportunity_col.container(border=True):
            st.markdown("**โอกาสเติบโต**")
            _render_markdown(os_state["growth_opportunity"])
        with focus_col.container(border=True):
            st.markdown("**เป้าหมายสัปดาห์นี้**")
            _render_markdown(os_state["weekly_focus"])

        if goal_status:
            st.progress(goal_status["progress_pct"] / 100)
            st.caption(
                f"ความคืบหน้าเป้าหมาย {goal_status['goal_label']}: {goal_status['progress_pct']}% "
                f"| ยังขาด {_format_baht(goal_status['gap_to_goal'])} | ความเสี่ยง {goal_status['goal_risk']}"
            )

    if not profile:
        return None

    goal_options = {
        "ยอดขายรายเดือน": "monthly_sales",
        "ความสม่ำเสมอของคอนเทนต์": "content_consistency",
        "ลูกค้าซื้อซ้ำ": "repeat_customers",
        "ลูกค้าใหม่": "new_customers",
        "สร้างความน่าเชื่อถือ": "trust_building",
    }
    reverse_goal_options = {value: key for key, value in goal_options.items()}
    default_goal_label = reverse_goal_options.get(
        (active_goal or {}).get("goal_type"),
        "ยอดขายรายเดือน",
    )

    with st.expander("เป้าหมายธุรกิจ", expanded=False):
        with st.form("business_goal_form"):
            goal_type_label = st.selectbox(
                "เป้าหมาย",
                list(goal_options.keys()),
                index=list(goal_options.keys()).index(default_goal_label),
            )
            target_value = st.number_input(
                "เป้าหมายรายได้ต่อเดือน",
                min_value=0.0,
                value=float((active_goal or {}).get("target_value") or 0),
                step=1.0,
            )
            st.caption(f"เป้าหมายรายได้ต่อเดือน: {_format_baht(target_value)}")
            current_value = st.number_input(
                "รายได้ปัจจุบัน",
                min_value=0.0,
                value=float((active_goal or {}).get("current_value") or 0),
                step=1.0,
            )
            st.caption(f"รายได้ปัจจุบัน: {_format_baht(current_value)}")
            deadline = st.text_input(
                "กำหนดวันเสร็จ",
                value=(active_goal or {}).get("deadline") or "",
                placeholder="เช่น 2026-07-31",
            )
            goal_submitted = st.form_submit_button("บันทึกเป้าหมาย")

    if goal_submitted:
        return create_business_goal(
            store_name=profile["store_name"],
            goal_type=goal_options[goal_type_label],
            target_value=target_value,
            current_value=current_value,
            deadline=deadline,
        )

    return None


def _show_store_profile(profile: dict | None) -> None:
    if not profile:
        return

    with st.expander("ข้อมูลร้าน", expanded=False):
        st.markdown(
            f"""
**{profile["store_name"]}**

ประเภทร้าน: {profile["store_type"]}

สินค้า: {profile["product"]}

ลูกค้าเป้าหมาย: {profile["target_customer"]}

โทน: {profile["tone"]}
"""
        )


def _show_daily_content() -> None:
    daily = st.session_state.get("generated_daily")
    if not daily:
        return

    with st.expander("แผนวันนี้", expanded=True):
        strategy = daily["strategy"]
        content = daily["content"]
        st.markdown(
            f"""
**แผนวันนี้**
{strategy["strategy_name"]}

**เหตุผล**
{strategy["strategy_reason"]}

**แนวคอนเทนต์**
{content["content_angle"]}

**เวลาที่เหมาะ**
{strategy["best_posting_time"]}
"""
        )
        with st.expander("สร้างแคปชัน", expanded=False):
            st.markdown("**แคปชัน Facebook**")
            st.markdown(content["facebook_caption"])
            st.markdown("**คำกระตุ้นการซื้อ**")
            st.markdown(content["call_to_action"])
            st.markdown("**แฮชแท็ก**")
            st.markdown(" ".join(content["hashtags"]))
        with st.expander("ไอเดียภาพ", expanded=False):
            st.markdown("**ไอเดียภาพ**")
            st.markdown(content["image_idea"])
        with st.expander("ข้อความสำหรับ LINE / TikTok", expanded=False):
            st.markdown("**ข้อความ LINE**")
            st.markdown(content["line_broadcast"])
            st.markdown("**แคปชัน TikTok**")
            st.markdown(content["tiktok_caption"])


def _show_calendar() -> None:
    calendar = st.session_state.get("generated_calendar")
    if not calendar:
        return

    with st.expander("แผนคอนเทนต์ 7 วัน", expanded=True):
        st.table(
            [
                {
                    "วัน": item["day_label"],
                    "ธีม": item["content_theme"],
                    "เป้าหมายขาย": item["sales_goal"],
                    "มุมสินค้า": item["suggested_product_angle"],
                    "เวลาโพสต์": item["best_posting_time"],
                    "ไอเดียแคปชัน": item["short_caption_idea"],
                }
                for item in calendar
            ]
        )


def _show_revenue_engine() -> None:
    revenue = st.session_state.get("generated_revenue")
    if not revenue:
        return

    with st.expander("แผนเพิ่มยอดขาย", expanded=True):
        sales_strategy = revenue["sales_strategy"]
        promotion = revenue["promotion"]
        campaign = revenue["campaign"]
        sales_brief = revenue["sales_brief"]

        st.markdown(
            f"""
**เป้าหมายยอดขาย:** {sales_strategy["sales_goal"]}

**สิ่งที่ควรทำ:** {sales_strategy["recommended_action"]}

**ไอเดียโปรโมชัน:** {promotion["promotion_name"]} - {promotion["promotion_mechanic"]}

**ระดับความเร่งด่วน:** {sales_strategy["urgency_level"]}
"""
        )
        st.divider()
        _render_markdown(sales_brief)
        st.divider()
        st.table(
            [
                {
                    "ธีม": item["campaign_theme"],
                    "มุมขาย": item["content_angle"],
                    "แคปชัน": item["caption"],
                }
                for item in campaign
            ]
        )


def _show_business_insights(profile: dict | None, history: list[dict]) -> dict | None:
    if not profile:
        return None

    insights = analyze_business_insights(profile, history)
    missing_types = insights["missing_content_types"]
    missing_labels = [_content_type_label(content_type) for content_type in missing_types]
    missing_text = ", ".join(missing_labels) if missing_labels else "ไม่มีประเภทคอนเทนต์ที่ขาดชัดเจน"

    with st.expander("ภาพรวมธุรกิจ", expanded=False):
        col1, col2 = st.columns(2)
        col1.metric("คอนเทนต์ที่สร้างทั้งหมด", insights["total_generated_content"])
        col2.metric("หัวข้อที่ใช้บ่อย", insights["most_used_topic"])
        _render_markdown(f"**คำเตือนหัวข้อซ้ำ:** {insights['repeated_topic_warning']}")
        _render_markdown(f"**ประเภทคอนเทนต์ที่ยังขาด:** {missing_text}")
        _render_markdown(f"**มุมถัดไปที่ควรลอง:** {insights['next_best_content_angle']}")
        _render_markdown(f"**คำแนะนำจาก AI:** {insights['business_recommendation']}")

    return insights


def _show_recent_history(history: list[dict]) -> None:
    if not history:
        return

    with st.expander("ประวัติคอนเทนต์", expanded=False):
        for item in history:
            created_at = item.get("created_at", "")
            topic = item.get("topic", "ไม่ระบุหัวข้อ")
            angle = item.get("content_angle", "")
            _render_markdown(f"- **{topic}** ({created_at})  \n  {angle}")


def _html_escape(value: object) -> str:
    text = str(value or "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _show_dashboard(companion: dict | None, os_state: dict | None) -> None:
    st.subheader("ผู้ช่วยธุรกิจของคุณ")
    if not companion:
        st.info("กรอกข้อมูลร้านก่อนครับ แล้วผมจะสรุปสุขภาพร้าน สิ่งที่ควรทำ โอกาส และสิ่งที่ต้องระวังให้")
        return

    score_value = (
        os_state.get("business_health_score")
        if os_state and os_state.get("business_health_score") is not None
        else companion.get("confidence")
    )
    score = f"{score_value}%"
    health = (os_state or {}).get("operating_status") or companion.get("companion_message")
    today_action = (os_state or {}).get("today_action") or companion.get("priority_action")
    opportunity = (os_state or {}).get("growth_opportunity") or companion.get("opportunity")
    risk = (os_state or {}).get("current_risk") or companion.get("warning")
    weekly_focus = (os_state or {}).get("weekly_focus") or today_action
    trend = "ควรดูแลเป็นพิเศษ" if int(score_value or 0) < 70 else "ไปได้ดี"
    store_profile = (_get_application_state().get("store") or {}).get("profile") or {}
    store_name = store_profile.get("store_name") or "เจ้าของร้าน"
    hero_message = (
        f"สวัสดีครับ {store_name}\n"
        "วันนี้ผมตรวจข้อมูลร้านของคุณแล้ว\n\n"
        "ตอนนี้ร้านยังมีโอกาสเติบโตได้อีกมาก\n"
        "สิ่งที่ควรเริ่มก่อนคือการเพิ่มรีวิวและคอนเทนต์ที่ช่วยสร้างความน่าเชื่อถือให้ลูกค้า"
    )
    hero_message_html = _html_escape(hero_message).replace("\n", "<br>")

    st.markdown(
        f"""
<section class="sme-command-welcome">
    <div class="sme-kicker">สรุปธุรกิจเช้านี้</div>
    <h2>{hero_message_html}</h2>
    <p>{_html_escape(companion.get("companion_message"))}</p>
    <div class="sme-brief-grid">
        <div><span>สุขภาพธุรกิจ</span><strong>{_html_escape(score)}</strong></div>
        <div><span>สิ่งที่ควรโฟกัสวันนี้</span><strong>{_html_escape(today_action)}</strong></div>
        <div><span>สิ่งที่ต้องระวัง</span><strong>{_html_escape(risk)}</strong></div>
        <div><span>โอกาสที่น่าลอง</span><strong>{_html_escape(opportunity)}</strong></div>
    </div>
</section>
""",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("##### สิ่งที่ควรโฟกัสวันนี้")
        st.markdown(f"**สิ่งที่ควรทำ:** {today_action}")
        st.markdown(f"**ทำไมควรทำ:** {risk}")
        st.markdown(f"**สิ่งที่ AI แนะนำให้ทำ:** {today_action}")
        st.markdown(f"**ผลลัพธ์ที่คาดว่าจะได้:** {opportunity}")

    with st.container(border=True):
        st.markdown("##### สรุปวันนี้")
        cols = st.columns(3)
        cols[0].metric("สุขภาพธุรกิจ", score)
        cols[1].metric("ทิศทางร้าน", trend)
        cols[2].metric("ความมั่นใจของ AI", f"{companion.get('confidence', 0)}%")
        st.markdown(f"**สุขภาพธุรกิจ:** {health}")
        st.markdown(f"**โอกาสที่น่าลอง:** {opportunity}")
        st.markdown(f"**สิ่งที่ต้องระวัง:** {risk}")
        st.markdown(f"**เป้าหมายสัปดาห์นี้:** {weekly_focus}")


def _show_ai_ranked_actions(companion: dict | None, os_state: dict | None) -> tuple[bool, bool, bool]:
    st.markdown("### สิ่งที่ AI แนะนำให้ทำ")
    if not companion:
        st.info("สร้างหรือเลือกร้านก่อนครับ แล้วผมจะเรียงสิ่งที่ควรทำถัดไปให้")
        return False, False, False

    confidence = int(companion.get("confidence") or 75)
    risk = (os_state or {}).get("current_risk") or companion.get("warning") or "ลูกค้าใหม่ยังไม่มีรีวิวให้อ่านก่อนตัดสินใจซื้อ"
    opportunity = (os_state or {}).get("growth_opportunity") or companion.get("opportunity") or "ช่วยให้ลูกค้ามั่นใจและตัดสินใจซื้อง่ายขึ้น"
    weekly_focus = (os_state or {}).get("weekly_focus") or "ทำงานให้ต่อเนื่องตลอดสัปดาห์นี้"

    actions = [
        ("สร้างโพสต์รีวิวลูกค้า", risk, "ช่วยเพิ่มความน่าเชื่อถือ และทำให้ลูกค้าตัดสินใจง่ายขึ้น", min(96, confidence + 4), "สูง", "สร้างโพสต์รีวิว"),
        ("วางแผนโฟกัส 7 วัน", weekly_focus, "ช่วยให้รู้ว่าควรทำอะไรก่อนหลังในแต่ละวัน", max(70, confidence - 3), "กลาง", "สร้างแผน 7 วัน"),
        ("วางแผนเพิ่มยอดขาย", opportunity, "ช่วยให้มีแคมเปญขายที่ชัดเจนและทำตามได้ทันที", max(68, confidence - 6), "กลาง", "วางแผนเพิ่มยอดขาย"),
    ]

    cols = st.columns(3)
    clicks = []
    for index, (title, reason, impact, action_confidence, priority, button_label) in enumerate(actions):
        with cols[index].container(border=True):
            st.markdown(f"**{index + 1}. {title}**")
            st.caption(f"ความสำคัญ: {priority} | ความมั่นใจของ AI: {action_confidence}%")
            st.markdown(f"**ทำไมควรทำ:** {reason}")
            st.markdown(f"**ผลลัพธ์ที่คาดว่าจะได้:** {impact}")
            clicks.append(st.button(button_label, key=f"ai_ranked_action_{index}", use_container_width=True))

    return clicks[0], clicks[1], clicks[2]


def _show_product_brain_card(profile: dict | None, business_insight: dict | None, diagnosis: dict | None) -> None:
    if not profile:
        return

    insight = business_insight or {}
    missing = insight.get("missing_content_types") or []
    weakness = (diagnosis or {}).get("likely_problem") or (", ".join(missing[:2]) if missing else "ยังมีข้อมูลร้านไม่มากพอ")
    strength = insight.get("business_recommendation") or "มีข้อมูลสินค้าและกลุ่มลูกค้าพอให้เริ่มแนะนำได้"
    confidence = 72 + min(20, int(insight.get("total_generated_content") or 0) * 4)

    with st.container(border=True):
        st.markdown("### สิ่งที่ AI เข้าใจเกี่ยวกับร้านคุณ")
        cols = st.columns(2)
        cols[0].markdown(f"**สินค้าหลัก:** {profile.get('product')}")
        cols[1].markdown(f"**กลุ่มลูกค้า:** {profile.get('target_customer')}")
        cols[0].markdown(f"**จุดที่ควรปรับ:** {weakness}")
        cols[1].markdown(f"**จุดที่นำไปต่อยอดได้:** {strength}")
        st.progress(min(100, confidence) / 100)
        st.caption(f"ความมั่นใจของ AI: {min(100, confidence)}%")


def _show_business_journey(profile: dict | None, active_goal: dict | None, business_os_state: dict | None) -> None:
    receipt = ensure_receipt_state(_get_application_state().get("receipt"))
    steps = [
        ("สร้างข้อมูลร้านแล้ว", bool(profile)),
        ("วางกลยุทธ์แล้ว", bool(business_os_state)),
        ("ตั้งเป้าหมายแล้ว", bool(active_goal)),
        ("อ่านบิล / ใบเสร็จ", bool(receipt.get("receipt_uploaded"))),
        ("จัดการสต็อก", False),
        ("ความจำธุรกิจ", bool(profile)),
        ("ระบบช่วยทำงานอัตโนมัติ", False),
    ]

    with st.container(border=True):
        st.markdown("### เส้นทางการพัฒนาร้าน")
        cols = st.columns(len(steps))
        for col, (label, done) in zip(cols, steps):
            status = "เสร็จแล้ว" if done else "ขั้นถัดไป"
            col.markdown(f"**{status}**  \n{label}")


def _show_smart_chat_prompts() -> None:
    prompts = [
        "วันนี้ควรทำอะไร",
        "ช่วยเพิ่มยอดขาย",
        "วิเคราะห์ร้านของฉัน",
        "สร้างโพสต์",
        "คำนวณต้นทุน",
        "อ่านบิล / ใบเสร็จ",
    ]
    chips = "".join(f"<span>{_html_escape(prompt)}</span>" for prompt in prompts)
    st.markdown(f'<div class="sme-chat-prompts">{chips}</div>', unsafe_allow_html=True)


def _latest_chat_context(chat_history: list[dict]) -> tuple[str | None, str | None]:
    previous_user_message = None
    assistant_reply = None
    for message in reversed(chat_history or []):
        if message.get("role") == "assistant" and assistant_reply is None:
            assistant_reply = message.get("content")
        elif message.get("role") == "user" and previous_user_message is None:
            previous_user_message = message.get("content")
        if previous_user_message is not None and assistant_reply is not None:
            break
    return previous_user_message, assistant_reply


def _contains_any_text(message: str, keywords: list[str]) -> bool:
    normalized = str(message or "").strip().lower()
    return any(keyword in normalized for keyword in keywords)


def _is_reset_command(message: str) -> bool:
    normalized = str(message or "").strip().lower()
    return normalized in {
        "reset",
        "new conversation",
        "เริ่มใหม่",
        "เริ่มแชทใหม่",
        "ล้างบทสนทนา",
        "คุยใหม่",
    }


def _is_correction_message(message: str) -> bool:
    normalized = str(message or "").strip().lower()
    return normalized in {"ไม่ใช่", "ผิด", "ยังไม่ตรง", "ไม่ได้ถามแบบนั้น"} or _contains_any_text(
        normalized,
        ["ไม่ใช่แบบนั้น", "ตอบผิด", "เข้าใจผิด", "ไม่ตรงที่ถาม"],
    )


def _extract_business_type(message: str, profile: dict | None = None) -> str | None:
    normalized = str(message or "").strip().lower()
    business_types = {
        "กาแฟ": "ร้านกาแฟ",
        "coffee": "ร้านกาแฟ",
        "อาหาร": "ร้านอาหาร",
        "restaurant": "ร้านอาหาร",
        "เสื้อ": "ร้านเสื้อผ้า",
        "ผ้า": "ร้านเสื้อผ้า",
        "clothing": "ร้านเสื้อผ้า",
        "บิวตี้": "ร้านบิวตี้",
        "beauty": "ร้านบิวตี้",
        "ออนไลน์": "ร้านออนไลน์",
        "online": "ร้านออนไลน์",
        "วัสดุก่อสร้าง": "ร้านวัสดุก่อสร้าง",
        "ก่อสร้าง": "ร้านวัสดุก่อสร้าง",
    }
    for keyword, label in business_types.items():
        if keyword in normalized:
            return label
    if profile and profile.get("store_type"):
        return str(profile["store_type"]).strip()
    return None


def _topic_from_intent(intent: str, user_message: str) -> str:
    topic_by_intent = {
        "MARKETING": "โปรโมชัน",
        "CONTENT": "คอนเทนต์",
        "SALES": "ยอดขาย",
        "CUSTOMER_RETENTION": "ลูกค้าเก่า",
        "BUSINESS_ANALYSIS": "ภาพรวมธุรกิจ",
        "START_BUSINESS": "เริ่มธุรกิจ",
        "PRODUCT_FEEDBACK": "Product Feedback",
    }
    return topic_by_intent.get(intent) or str(user_message or "").strip()[:60] or "บทสนทนานี้"


def _sync_conversation_business_context(
    profile: dict | None,
    goal_status: dict | None,
    business_os_state: dict | None,
) -> dict:
    state = _ensure_conversation_state()
    if profile:
        state["business_type"] = _extract_business_type(profile.get("store_type", ""), profile)
    goal = (goal_status or {}).get("goal_label") or (business_os_state or {}).get("active_goal")
    if goal:
        state["latest_business_goal"] = goal
    return state


def _profile_with_conversation_memory(profile: dict | None) -> dict | None:
    if not profile:
        return None
    state = _ensure_conversation_state()
    business_type = state.get("business_type")
    if not business_type:
        return profile
    return {**profile, "store_type": business_type}


def _update_conversation_state_after_user(
    user_message: str,
    intent: str,
    profile: dict | None,
) -> dict:
    state = _ensure_conversation_state()
    business_type = _extract_business_type(user_message, profile)
    if business_type:
        state["business_type"] = business_type
    if _is_correction_message(user_message):
        state["last_correction"] = user_message
        state["last_feedback"] = user_message
    state["last_answer"] = user_message
    state["previous_intent"] = state.get("last_intent")
    state["last_intent"] = intent
    if intent not in {"GREETING", "FOLLOW_UP", "OTHER"}:
        state["current_topic"] = _topic_from_intent(intent, user_message)
    return state


def _update_conversation_state_after_assistant(reply: str, intent: str, topic: str | None = None) -> None:
    state = _ensure_conversation_state()
    if topic:
        state["current_topic"] = topic
    state["last_intent"] = intent
    state["conversation_stage"] = "active"
    stripped = str(reply or "").strip()
    question_lines = [line.strip() for line in stripped.splitlines() if line.strip().endswith(("?", "ครับ", "ครับ?"))]
    state["last_question"] = question_lines[-1] if question_lines else None
    state["follow_up_expected"] = bool(state["last_question"] and any(token in state["last_question"] for token in ["หรือ", "ไหม", "?"]))
    if "สวัสดีครับ" in stripped:
        state["greeted"] = True


def _one_question_correction_reply() -> str:
    state = _ensure_conversation_state()
    topic = state.get("current_topic") or "เรื่องก่อนหน้า"
    return (
        "เข้าใจแล้วครับ ผมตีความผิดเอง\n\n"
        f"เมื่อกี้เราคุยเรื่อง{topic}\n\n"
        "คุณต้องการให้ผมช่วยปรับคำตอบไปทางไหนครับ?"
    )


def _greeting_reply() -> str:
    state = _ensure_conversation_state()
    if state.get("greeted"):
        return "สวัสดีครับ\n\nมีอะไรให้ช่วยต่อได้เลยครับ"
    return "สวัสดีครับ\n\nวันนี้อยากให้ช่วยเรื่องอะไรครับ"


def _follow_up_reply(user_message: str, profile: dict | None) -> str | None:
    state = _ensure_conversation_state()
    if not state.get("follow_up_expected"):
        return None
    answer = str(user_message or "").strip()
    state["last_answer"] = answer
    business_type = state.get("business_type") or _extract_business_type(answer, profile) or "ร้านของคุณ"
    topic = state.get("current_topic") or "เรื่องนี้"
    if state.get("current_workflow") == WORKFLOW_COST_CALCULATION:
        return "รับทราบครับ ส่งตัวเลขวัตถุดิบ จำนวนชิ้นที่ทำได้ และราคาขายต่อชิ้นมาได้เลยครับ"
    if state.get("current_workflow") == WORKFLOW_RECEIPT_CAPTURE:
        return "รับทราบครับ ส่งไฟล์ที่ช่องอัปโหลดบิล / สลิปได้เลยครับ ตอนนี้ระบบจะบันทึกไฟล์ไว้ก่อน"
    if state.get("previous_intent") not in {"CONTENT", "MARKETING", "SALES"}:
        return (
            f"รับทราบครับ เป็น{answer}\n\n"
            f"ผมจะต่อจากเรื่อง{topic}ของ{business_type}ให้ครับ\n\n"
            "อยากให้ผมช่วยต่อจากข้อมูลไหนครับ?"
        )
    return (
        f"รับทราบครับ เป็น{answer}\n\n"
        f"ผมจะต่อจากเรื่อง{topic}ของ{business_type}เลย\n\n"
        "อยากให้ผมช่วยคิดเป็นโปรโมชัน ตัวอย่างโพสต์ หรือแผนขายสั้นๆ ครับ?"
    )


def _clean_chat_reply(reply: str, preserve_greeting: bool = False) -> str:
    text = clean_response(reply)
    state = _ensure_conversation_state()
    while text.count("สวัสดีครับ") > 1:
        first = text.find("สวัสดีครับ")
        second = text.find("สวัสดีครับ", first + len("สวัสดีครับ"))
        text = text[:second] + text[second + len("สวัสดีครับ"):].lstrip()
    if state.get("greeted") and not preserve_greeting and text.startswith("สวัสดีครับ"):
        text = text[len("สวัสดีครับ"):].lstrip(" \n")
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        return text

    split_paragraphs = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if len(words) <= 150:
            split_paragraphs.append(paragraph)
            continue
        chunk = []
        for word in words:
            chunk.append(word)
            if len(chunk) >= 120:
                split_paragraphs.append(" ".join(chunk))
                chunk = []
        if chunk:
            split_paragraphs.append(" ".join(chunk))
    return "\n\n".join(split_paragraphs)


def _should_show_chat_footer(message: dict) -> bool:
    return bool(message.get("show_business_insights") and (message.get("suggested_action") or message.get("related_feature")))


def _render_assistant_footer(message: dict) -> None:
    if not _should_show_chat_footer(message):
        return
    if message.get("suggested_action"):
        st.caption(f"สิ่งที่แนะนำ: {localize_internal_labels(message['suggested_action'])}")
    if message.get("related_feature"):
        st.caption(f"ฟีเจอร์ที่เกี่ยวข้อง: {localize_internal_labels(message['related_feature'])}")


def _handle_product_feedback(
    user_message: str,
    profile: dict,
    previous_user_message: str | None,
    assistant_reply: str | None,
) -> dict:
    del profile, previous_user_message, assistant_reply
    conversation_id = st.session_state.get("conversation_id")
    result = record_product_feedback(user_message, conversation_id=conversation_id)
    record = result["record"]
    category = record["category"]
    priority = record["priority"]
    if category == "Feature Request":
        reply = "✅ บันทึกเป็น Feature Request แล้ว\n\nความสำคัญ:\n\n" + priority
    elif category == "Bug":
        reply = "✅ บันทึกเป็น Bug Report แล้ว\n\nความสำคัญ:\n\n" + priority
    else:
        reply = (
            "✅ รับข้อเสนอแล้วครับ\n\n"
            "หมวด:\n\n"
            f"{category}\n\n"
            "ความสำคัญ:\n\n"
            f"{priority}\n\n"
            "ถูกเพิ่มเข้า Product Backlog แล้ว"
        )
    return {
        "reply": reply,
        "intent": "PRODUCT_FEEDBACK",
        "conversation_mode": "developer_feedback",
        "category": category,
        "priority": priority,
    }


def _set_workflow_state(workflow: str, step: str, user_message: str, data: dict | None = None) -> None:
    state = _ensure_conversation_state()
    state["current_workflow"] = workflow
    state["workflow_step"] = step
    state["workflow_data"] = data or state.get("workflow_data") or {}
    state["workflow_started_at"] = state.get("workflow_started_at") or datetime.now(timezone.utc).isoformat()
    state["last_workflow_message"] = user_message
    _update_application_section(
        "workflow",
        {
            "current_workflow": workflow,
            "workflow": workflow,
            "workflow_step": step,
            "step": step,
            "workflow_data": state["workflow_data"],
            "workflow_started_at": state["workflow_started_at"],
            "last_workflow_message": user_message,
        },
    )


def _clear_workflow_state() -> None:
    state = _ensure_conversation_state()
    state["current_workflow"] = None
    state["workflow_step"] = None
    state["workflow_data"] = {}
    state["workflow_started_at"] = None
    state["last_workflow_message"] = None
    _update_application_section(
        "workflow",
        {
            "current_workflow": None,
            "workflow": None,
            "workflow_step": None,
            "step": None,
            "workflow_data": {},
            "workflow_state_v2": {},
            "is_ready": False,
            "workflow_started_at": None,
            "last_workflow_message": None,
        },
    )


def _cost_intro_reply() -> str:
    return """ได้ครับ ผมช่วยคำนวณต้นทุนต่อชิ้นให้ได้

ช่วยส่งข้อมูลแบบนี้ครับ:

1. วัตถุดิบแต่ละอย่าง + ราคา
2. จำนวนชิ้นที่ทำได้ทั้งหมด
3. ราคาขายต่อชิ้น ถ้ามี

ตัวอย่าง:
แป้ง 40 บาท
ไข่ 30 บาท
น้ำตาล 20 บาท
ทำได้ 50 ชิ้น
ขายชิ้นละ 15 บาท"""


def _parse_cost_inputs(message: str) -> dict:
    ingredients = []
    total_pieces = None
    selling_price = None

    for raw_line in str(message or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        numbers = [float(value.replace(",", "")) for value in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", line)]
        if not numbers:
            continue

        lowered = line.lower()
        if any(keyword in lowered for keyword in ["ทำได้", "ได้ทั้งหมด", "จำนวนชิ้น", "ผลิตได้"]):
            total_pieces = numbers[-1]
            continue
        if any(keyword in lowered for keyword in ["ขาย", "ราคาขาย", "ชิ้นละ"]):
            selling_price = numbers[-1]
            continue
        ingredients.append({"name": re.sub(r"\d+(?:,\d{3})*(?:\.\d+)?|บาท", "", line).strip() or "วัตถุดิบ", "cost": numbers[-1]})

    total_cost = sum(item["cost"] for item in ingredients)
    return {
        "ingredients": ingredients,
        "total_cost": total_cost,
        "total_pieces": total_pieces,
        "selling_price": selling_price,
    }


def _cost_result_reply(parsed: dict) -> tuple[str, bool]:
    ingredients = parsed.get("ingredients") or []
    total_cost = float(parsed.get("total_cost") or 0)
    total_pieces = parsed.get("total_pieces")
    selling_price = parsed.get("selling_price")

    if not ingredients:
        return "ขอราคาวัตถุดิบแต่ละอย่างก่อนครับ เช่น แป้ง 40 ไข่ 30 น้ำตาล 20", False
    if not total_pieces:
        return "รวมต้นทุนวัตถุดิบได้แล้วครับ ขอจำนวนชิ้นที่ทำได้ทั้งหมดอีกอย่างเดียวครับ", False

    cost_per_piece = total_cost / float(total_pieces)
    lines = [
        "คำนวณเบื้องต้นได้แบบนี้ครับ",
        "",
        f"ต้นทุนรวม: {_format_number(total_cost)} บาท",
        f"จำนวนที่ทำได้: {_format_number(total_pieces)} ชิ้น",
        f"ต้นทุนต่อชิ้น: {_format_number(cost_per_piece)} บาท",
    ]

    if selling_price:
        gross_profit = float(selling_price) - cost_per_piece
        margin = (gross_profit / float(selling_price)) * 100 if float(selling_price) else 0
        lines.extend(
            [
                f"ราคาขายต่อชิ้น: {_format_number(selling_price)} บาท",
                f"กำไรขั้นต้นต่อชิ้น: {_format_number(gross_profit)} บาท",
                f"มาร์จิ้น: {_format_number(margin)}%",
                "",
                "ขั้นต่อไปลองเช็กต้นทุนแฝง เช่น กล่อง ถุง ค่าแก๊ส หรือค่าขนส่งครับ",
            ]
        )
    else:
        lines.extend(["", "ถ้าต้องการคำนวณกำไรต่อชิ้น ส่งราคาขายต่อชิ้นมาได้ครับ"])

    return "\n".join(lines), True


def _handle_cost_workflow(user_message: str, starting: bool = False) -> dict:
    if starting:
        _set_workflow_state(WORKFLOW_COST_CALCULATION, "collecting_cost_inputs", user_message)
        return {"reply": _cost_intro_reply(), "intent": WORKFLOW_COST_CALCULATION, "done": False}

    parsed = _parse_cost_inputs(user_message)
    reply, done = _cost_result_reply(parsed)
    _set_workflow_state(WORKFLOW_COST_CALCULATION, "completed" if done else "collecting_cost_inputs", user_message, parsed)
    return {"reply": reply, "intent": WORKFLOW_COST_CALCULATION, "done": done}


def _format_workflow_value(value) -> str:
    return _format_number(value)


def _sync_workflow_state_v2(workflow_state: dict) -> None:
    state = _ensure_conversation_state()
    state["workflow_state_v2"] = workflow_state
    state["current_workflow"] = workflow_state.get("workflow")
    state["workflow_step"] = workflow_state.get("step")
    state["workflow_data"] = workflow_state.get("collected_fields") or {}
    state["last_workflow_message"] = workflow_state.get("last_updated")
    if not state.get("workflow_started_at"):
        state["workflow_started_at"] = workflow_state.get("last_updated")
    _update_application_section(
        "workflow",
        {
            "workflow_state_v2": workflow_state,
            "current_workflow": workflow_state.get("workflow"),
            "workflow": workflow_state.get("workflow"),
            "workflow_step": workflow_state.get("step"),
            "step": workflow_state.get("step"),
            "workflow_data": workflow_state.get("collected_fields") or {},
            "is_ready": bool(workflow_state.get("is_ready")),
            "last_workflow_message": workflow_state.get("last_updated"),
        },
    )


def _clear_workflow_state_v2() -> None:
    state = _ensure_conversation_state()
    state["workflow_state_v2"] = {}
    state["workflow_blocked_phrases"] = {}
    _clear_workflow_state()


def _workflow_missing_reply(workflow_state: dict) -> str:
    workflow = workflow_state.get("workflow")
    missing = workflow_state.get("missing_fields") or []

    if workflow == V2_WORKFLOW_SALES_PLAN_7_DAY:
        if len(missing) >= 3:
            return (
                "ได้ครับ ผมช่วยทำแผนขาย 7 วันให้ได้\n\n"
                "ขอข้อมูลสั้น ๆ 3 อย่างครับ:\n"
                "1. ขายสินค้าอะไร\n"
                "2. ทำได้วันละกี่ชิ้น\n"
                "3. ขายช่วงเวลาไหน หรือขายช่องทางไหน"
            )
        if "product" in missing:
            return "ขอชื่อสินค้าที่ต้องการทำแผนขายครับ"
        if "daily_capacity_or_available_quantity" in missing:
            return "สินค้านี้ทำได้วันละกี่ชิ้น หรือมีพร้อมขายกี่ชิ้นครับ"
        if "selling_window_or_sales_channel" in missing:
            return "ขายช่วงเวลาไหน หรือขายผ่านช่องทางไหนครับ"

    if workflow == V2_WORKFLOW_COST_CALCULATION:
        if "ingredients_costs" in missing and "total_units" in missing:
            return (
                "ได้ครับ ผมช่วยคำนวณต้นทุนต่อชิ้นให้ได้\n\n"
                "ส่งข้อมูล 3 อย่างนี้มาครับ:\n"
                "1. วัตถุดิบแต่ละอย่าง + ราคา\n"
                "2. ทำได้ทั้งหมดกี่ชิ้น\n"
                "3. ราคาขายต่อชิ้น ถ้ามี"
            )
        if "ingredients_costs" in missing:
            return "ขอราคาวัตถุดิบแต่ละอย่างครับ เช่น แป้ง 40 ไข่ 30 น้ำตาล 20"
        if "total_units" in missing:
            return "รวมแล้วทำได้ทั้งหมดกี่ชิ้นครับ"

    if workflow == V2_WORKFLOW_CONTENT_PLAN:
        return "อยากทำคอนเทนต์ให้สินค้าอะไร หรือธุรกิจประเภทไหนครับ"

    return "ขอข้อมูลที่ขาดอีกนิดเดียวครับ"


def _generate_sales_plan_7_day(workflow_state: dict) -> str:
    fields = workflow_state.get("collected_fields") or {}
    product = fields.get("product") or "สินค้า"
    capacity = fields.get("daily_capacity") or fields.get("available_quantity")
    window = fields.get("selling_window") or fields.get("sales_channel") or "ช่องทางหลัก"
    capacity_line = f"จำนวนจำกัด {_format_workflow_value(capacity)} ชิ้น" if capacity else "จำนวนจำกัด"
    return (
        f"แผนขาย 7 วันสำหรับ{product}\n\n"
        f"Day 1:\nเป้าหมาย: ขายให้คนรู้จักและลูกค้าใกล้ตัว\nทำวันนี้: โพสต์รูปสินค้า + ราคา + {capacity_line}\n\n"
        f"Day 2:\nเป้าหมาย: เก็บออเดอร์ช่วง {window}\nทำวันนี้: เปิดรับจองล่วงหน้า และแจ้งเวลารับสินค้าให้ชัด\n\n"
        "Day 3:\nเป้าหมาย: เพิ่มความน่าเชื่อถือ\nทำวันนี้: ลงรีวิวหรือรูปตอนทำจริง พร้อมบอกจำนวนที่ทำได้ต่อวัน\n\n"
        "Day 4:\nเป้าหมาย: ดันยอดจากลูกค้าเดิม\nทำวันนี้: ทักลูกค้าที่เคยซื้อและเสนอให้จองรอบถัดไป\n\n"
        "Day 5:\nเป้าหมาย: เพิ่มออเดอร์แบบกลุ่ม\nทำวันนี้: เสนอชุดซื้อหลายชิ้นสำหรับออฟฟิศ เพื่อนบ้าน หรือครอบครัว\n\n"
        "Day 6:\nเป้าหมาย: ปิดยอดก่อนหมดรอบขาย\nทำวันนี้: แจ้งจำนวนคงเหลือและเวลาปิดรับออเดอร์\n\n"
        "Day 7:\nเป้าหมาย: สรุปยอดและทำซ้ำสิ่งที่ได้ผล\nทำวันนี้: ดูว่าวันไหนขายดีที่สุด แล้วใช้ข้อความและช่องทางนั้นต่อ"
    )


def _generate_cost_calculation(workflow_state: dict) -> str:
    fields = workflow_state.get("collected_fields") or {}
    ingredients = fields.get("ingredients_costs") or []
    total_units = float(fields.get("total_units") or 0)
    selling_price = fields.get("selling_price")
    total_cost = sum(float(item.get("cost") or 0) for item in ingredients)
    cost_per_unit = total_cost / total_units if total_units else 0
    lines = [
        "คำนวณต้นทุนต่อชิ้น",
        "",
        f"ต้นทุนรวม: {_format_number(total_cost)} บาท",
        f"จำนวนที่ทำได้: {_format_number(total_units)} ชิ้น",
        f"ต้นทุนต่อชิ้น: {_format_number(cost_per_unit)} บาท",
    ]
    if selling_price:
        selling_price = float(selling_price)
        gross_profit = selling_price - cost_per_unit
        gross_margin = (gross_profit / selling_price) * 100 if selling_price else 0
        lines.extend(
            [
                f"ราคาขายต่อชิ้น: {_format_number(selling_price)} บาท",
                f"กำไรขั้นต้นต่อชิ้น: {_format_number(gross_profit)} บาท",
                f"Gross margin: {_format_number(gross_margin)}%",
            ]
        )
    return "\n".join(lines)


def _generate_content_plan(workflow_state: dict) -> str:
    fields = workflow_state.get("collected_fields") or {}
    product = fields.get("product") or fields.get("business_type") or "สินค้า"
    return (
        f"แผนคอนเทนต์สั้นสำหรับ{product}\n\n"
        "1. โพสต์สินค้าเด่น: รูปชัด + ราคา + วิธีสั่งซื้อ\n"
        "2. โพสต์เบื้องหลัง: ขั้นตอนทำหรือคัดสินค้า\n"
        "3. โพสต์รีวิว: ความเห็นลูกค้าหรือผลลัพธ์หลังใช้\n"
        "4. โพสต์ปิดการขาย: จำนวนจำกัดหรือรอบส่งถัดไป"
    )


def _generate_workflow_reply(workflow_state: dict) -> str:
    workflow = workflow_state.get("workflow")
    if workflow == V2_WORKFLOW_SALES_PLAN_7_DAY:
        return _generate_sales_plan_7_day(workflow_state)
    if workflow == V2_WORKFLOW_COST_CALCULATION:
        return _generate_cost_calculation(workflow_state)
    if workflow == V2_WORKFLOW_CONTENT_PLAN:
        return _generate_content_plan(workflow_state)
    return _workflow_missing_reply(workflow_state)


def _workflow_llm_context(workflow_state: dict, profile: dict | None, user_message: str) -> dict:
    return {
        "current_workflow": workflow_state.get("workflow"),
        "collected_fields": workflow_state.get("collected_fields") or {},
        "missing_fields": workflow_state.get("missing_fields") or [],
        "store_profile": profile or {},
        "user_message": user_message,
        "instruction": [
            "Do not ask for information that is already present.",
            "Do not switch topic.",
            "Do not suggest promotion/content unless workflow is content or sales.",
            "Keep Thai reply short.",
        ],
    }


def _maybe_improve_workflow_reply_with_llm(
    base_reply: str,
    workflow_state: dict,
    profile: dict | None,
    user_message: str,
) -> tuple[str, bool]:
    mode = st.session_state.get("llm_response_mode", "Workflow Only")
    if mode != "Workflow + LLM":
        return base_reply, False

    demo_mode = bool(st.session_state.get("demo_mode"))
    context = _workflow_llm_context(workflow_state, profile, user_message)
    context["deterministic_reply"] = base_reply
    route = st.session_state.get("last_task_route") or {}
    context = build_prompt_context(
        application_state=_sync_session_to_application_state(),
        planner=route.get("planner_output"),
        capability=route.get("selected_capability"),
        loaded_skill=route.get("loaded_skills"),
        reasoning=route.get("reasoning"),
        workflow_state=context,
        store_profile=profile,
        developer_mode=bool(st.session_state.get("developer_mode")),
    )
    if not can_call_llm(st):
        print("Fallback reason: budget guard")
        return base_reply, False
    if demo_mode and not _allow_demo_llm_call(user_message, context):
        print("Fallback reason: demo token guard")
        return base_reply, False
    with st.spinner("AI กำลังเรียบเรียงคำตอบ..."):
        llm_reply = generate_llm_response(
            user_message,
            context=context,
            demo_mode=demo_mode,
        )
    if not llm_reply:
        print("Fallback reason: workflow provider error")
        return base_reply, True
    record_llm_call(st, 0.002 if demo_mode else 0.01)
    return clean_response(llm_reply), True


def _handle_state_machine_workflow(
    user_message: str,
    detected_workflow: str,
    profile: dict | None,
) -> dict:
    state = _ensure_conversation_state()
    workflow_state, extracted_fields = update_workflow_state(
        state.get("workflow_state_v2") or {},
        user_message,
        detected_workflow=detected_workflow,
    )
    _sync_workflow_state_v2(workflow_state)

    if workflow_state.get("is_ready"):
        reply = _generate_workflow_reply(workflow_state)
        reply, llm_attempted = _maybe_improve_workflow_reply_with_llm(reply, workflow_state, profile, user_message)
        workflow_state["next_action"] = "completed"
        workflow_state["step"] = "completed"
        _sync_workflow_state_v2(workflow_state)
        return {
            "reply": reply,
            "intent": workflow_state.get("workflow"),
            "done": True,
            "llm_attempted": llm_attempted,
            "extracted_fields": extracted_fields,
        }

    reply = _workflow_missing_reply(workflow_state)
    return {
        "reply": reply,
        "intent": workflow_state.get("workflow"),
        "done": False,
        "llm_attempted": False,
        "extracted_fields": extracted_fields,
    }


def _show_workflow_diagnostics() -> None:
    if not st.session_state.get("developer_mode"):
        return
    workflow_state = (_ensure_conversation_state().get("workflow_state_v2") or {})
    with st.expander("Workflow Diagnostics", expanded=False):
        st.json(
            {
                "Current Workflow": workflow_state.get("workflow"),
                "Workflow Step": workflow_state.get("step"),
                "Collected Fields": workflow_state.get("collected_fields") or {},
                "Missing Fields": workflow_state.get("missing_fields") or [],
                "Ready?": bool(workflow_state.get("is_ready")),
                "LLM Response Mode": st.session_state.get("llm_response_mode", "Workflow Only"),
            }
        )


def _show_shared_application_state_diagnostics() -> None:
    if not st.session_state.get("developer_mode"):
        return
    state = _sync_session_to_application_state()
    reasoning = st.session_state.get("last_reasoning") or (state.get("developer") or {}).get("reasoning_result") or {}
    with st.expander("Shared Application State", expanded=False):
        st.json(
            {
                "Conversation": state.get("conversation") or {},
                "Workflow": state.get("workflow") or {},
                "Receipt": state.get("receipt") or {},
                "Dashboard": state.get("dashboard") or {},
                "Store": state.get("store") or {},
                "Developer": state.get("developer") or {},
                "Reasoning Result": reasoning,
                "Current Action": reasoning.get("action") or (state.get("developer") or {}).get("current_action"),
                "LLM Needed": bool(reasoning.get("llm_needed") or (state.get("developer") or {}).get("llm_needed")),
                "Workflow Ready": bool(reasoning.get("workflow_ready") or (state.get("developer") or {}).get("workflow_ready")),
            }
        )


def _show_platform_diagnostics() -> None:
    if not st.session_state.get("developer_mode"):
        return
    state = _sync_session_to_application_state()
    route = st.session_state.get("last_task_route") or (state.get("developer") or {}).get("task_route") or {}
    with st.expander("Platform Planner Diagnostics", expanded=False):
        st.json(developer_diagnostics(route))


def _show_ai_pipeline_debug_trace() -> None:
    if not st.session_state.get("developer_mode"):
        return
    trace = st.session_state.get("ai_pipeline_debug_trace") or {}
    with st.expander(" AI Pipeline Debug", expanded=False):
        if trace:
            st.json(trace)
        else:
            st.caption("No chat request traced yet.")


def _handle_dashboard_workflow(user_message: str) -> dict:
    record_product_feedback(user_message, conversation_id=st.session_state.get("conversation_id"))
    _clear_workflow_state_v2()
    _update_application_section(
        "dashboard",
        {
            "last_request": user_message,
            "status": "available_basic_dashboard",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {
        "reply": """ตอนนี้ระบบมีแดชบอร์ดพื้นฐานให้แล้วครับ
ถ้าต้องการแดชบอร์ดเฉพาะร้าน ผมบันทึกเป็นคำขอฟีเจอร์ให้ทีมพัฒนาแล้ว

ตัวอย่างแดชบอร์ดที่ทำได้ในอนาคต:
- ยอดขายรายวัน
- ต้นทุน / กำไร
- สต๊อกสินค้า
- ลูกค้าประจำ
- คอนเทนต์ที่ได้ผลดี""",
        "intent": WORKFLOW_DASHBOARD_REQUEST,
    }


def _receipt_uploaded_reply(action: str | None = None) -> str:
    if action == "receipt_ocr_pending":
        return (
            "ระบบอ่านบิลอัตโนมัติยังไม่เปิดใช้งาน\n\n"
            "เมื่อพร้อมจะคำนวณให้อัตโนมัติ"
        )
    return (
        "เห็นแล้วครับ\n\n"
        "รับบิลเรียบร้อย\n\n"
        "ระบบอ่านบิลอัตโนมัติกำลังรอการพัฒนา\n\n"
        "เมื่อเปิดใช้งานแล้วจะช่วยอ่าน\n\n"
        "• รายการสินค้า\n"
        "• ราคาวัตถุดิบ\n"
        "• ต้นทุน\n"
        "• กำไร\n\n"
        "ได้อัตโนมัติ"
    )


def _handle_receipt_workflow(user_message: str) -> dict:
    _set_workflow_state(WORKFLOW_RECEIPT_CAPTURE, "waiting_for_upload", user_message)
    reasoning = build_reasoning(_sync_session_to_application_state(), user_message)
    if reasoning.get("action") in {"receipt_uploaded_ack", "receipt_ocr_pending"}:
        st.session_state["last_reasoning"] = reasoning
        _update_application_section(
            "developer",
            {
                "reasoning_result": reasoning,
                "current_action": reasoning.get("action"),
                "llm_needed": False,
                "workflow_ready": False,
            },
        )
        return {"reply": _receipt_uploaded_reply(reasoning.get("action")), "intent": WORKFLOW_RECEIPT_CAPTURE}

    normalized = str(user_message or "").strip().lower()
    if any(term in normalized for term in ["เดี๋ยวส่งบิล", "เดี๋ยวส่ง", "จะส่งบิล", "ส่งบิลนะ"]):
        return {"reply": "ได้ครับ รอรับบิล", "intent": WORKFLOW_RECEIPT_CAPTURE}
    if "อ่าน" in normalized:
        reply = "ตอนนี้บันทึกบิลได้แล้ว แต่ยังอ่านตัวเลขอัตโนมัติไม่ได้เต็มรูปแบบ ขั้นต่อไปคือเพิ่มระบบอ่านบิล"
    else:
        reply = "ส่งไฟล์ที่ช่องอัปโหลดบิล / สลิปได้ครับ ตอนนี้ระบบจะบันทึกไฟล์ไว้ก่อน และขั้นถัดไปจะเพิ่มระบบอ่านบิลเพื่อดึงยอดเงินให้อัตโนมัติ"
    return {"reply": reply, "intent": WORKFLOW_RECEIPT_CAPTURE}


def _append_workflow_reply(reply: str, intent: str, topic: str | None = None) -> None:
    assistant_message = {"role": "assistant", "content": reply, "show_business_insights": False}
    _update_conversation_state_after_assistant(reply, intent, topic)
    st.session_state["chat_history"].append(assistant_message)
    _sync_chat_history_to_application_state()
    with st.chat_message("assistant", avatar=_chat_avatar("assistant")):
        _render_assistant_response(reply)


def _show_feedback_summary() -> None:
    if not st.session_state.get("developer_mode"):
        return

    with st.expander("ระบบเรียนรู้จากผู้ใช้", expanded=False):
        show_summary = st.checkbox("แสดงแดชบอร์ดทีมพัฒนา", value=False)
        if not show_summary:
            st.caption("ส่วนนี้ใช้สำหรับทีมพัฒนาเท่านั้น")
            return

        dashboard = prepare_dashboard_data()
        counts = dashboard["counts"]
        st.metric("Feedback ทั้งหมด", counts["total_count"])
        st.metric("Backlog เปิดอยู่", counts["backlog_open"])

        st.write("จำนวนตามหมวด")
        st.json(
            {
                "category": counts["by_category"],
                "priority": counts["by_priority"],
                "severity": counts["by_severity"],
            }
        )

        st.write("ฟีเจอร์ที่ถูกขอมากที่สุด")
        for issue in dashboard["top_requested_features"]:
            st.markdown(f"- **{issue['title']}** ({issue['priority']}) x{issue['count']}")

        st.write("บั๊กที่พบบ่อย")
        for issue in dashboard["top_bugs"]:
            st.markdown(f"- **{issue['title']}** ({issue['priority']}) x{issue['count']}")

        st.write("ปัญหาประสบการณ์ใช้งาน")
        for issue in dashboard["top_ux_problems"]:
            st.markdown(f"- **{issue['title']}** ({issue['priority']}) x{issue['count']}")

        st.write("แนวโน้มฟีดแบ็ก")
        st.json(dashboard["feedback_trend"]["daily_counts"])

        st.write("ฟีดแบ็กล่าสุด")
        for record in dashboard["latest_feedback"]:
            st.markdown(
                f"- **{record.get('category', 'Other')} / {record.get('priority', 'Low')}**: "
                f"{record.get('raw_message', '')}"
            )


def _count_feedback_keywords(records: list[dict], keywords: list[str]) -> int:
    total = 0
    for record in records:
        text = str(record.get("raw_message") or record.get("summary") or "").lower()
        if any(keyword in text for keyword in keywords):
            total += 1
    return total


def _render_alert_list(alerts: list[dict], limit: int = 8) -> None:
    if not alerts:
        st.caption("No alerts detected.")
        return
    for alert in alerts[:limit]:
        st.markdown(
            f"- **{alert.get('priority')} / {alert.get('category')}**: "
            f"{alert.get('title')} x{alert.get('count')}"
        )
        if alert.get("recommended_action"):
            st.caption(alert["recommended_action"])


def _show_developer_alert_center() -> None:
    if not st.session_state.get("developer_mode"):
        return

    chat_history = st.session_state.get("chat_history", [])
    alerts = collect_developer_alerts(
        chat_history=chat_history,
        conversation_id=st.session_state.get("conversation_id"),
    )
    health = build_system_health(alerts, chat_history)
    trends = generate_trends(chat_history)
    replay = build_problem_conversation_replay(chat_history, limit=20)
    recommendations = recommend_next_sprint(chat_history)
    product_dashboard = prepare_dashboard_data()
    feedback_records = product_dashboard.get("latest_feedback", [])
    counts = product_dashboard.get("counts", {})
    category_counts = counts.get("by_category", {})
    warnings = build_smart_warnings(alerts)

    with st.expander("Developer Alert Center", expanded=False):
        for warning in warnings:
            st.warning(warning)

        st.markdown("### Product Intelligence Dashboard")
        metric_rows = [
            st.columns(4),
            st.columns(4),
            st.columns(4),
        ]
        metric_rows[0][0].metric("Total Conversations", health["total_conversations"])
        metric_rows[0][1].metric("Feedback", counts.get("total_count", 0))
        metric_rows[0][2].metric("Conversation Failure Rate", f"{health['conversation_failure_rate']}%")
        metric_rows[0][3].metric("Silent Signal Rate", f"{health['silent_signal_rate']}%")
        metric_rows[1][0].metric("AI Success Rate", f"{health['ai_success_rate']}%")
        metric_rows[1][1].metric("Workflow Completion Rate", f"{health['workflow_completion_rate']}%")
        metric_rows[1][2].metric("Receipt Requests", _count_feedback_keywords(feedback_records, ["บิล", "สลิป", "receipt", "ocr"]))
        metric_rows[1][3].metric("Dashboard Requests", _count_feedback_keywords(feedback_records, ["dashboard", "แดชบอร์ด"]))
        metric_rows[2][0].metric("Feature Requests", category_counts.get("Feature Request", 0))
        metric_rows[2][1].metric("Bug Reports", category_counts.get("Bug", 0))
        metric_rows[2][2].metric("UX Issues", category_counts.get("UX", 0) + category_counts.get("UI", 0))
        metric_rows[2][3].metric("High Alerts", len([alert for alert in alerts if alert.get("priority") == "High"]))

        st.markdown("### System Health")
        system_cols = st.columns(4)
        system_cols[0].metric("System Health", "Watch" if alerts else "Stable")
        system_cols[1].metric("Conversation Health", f"{health['ai_success_rate']}%")
        system_cols[2].metric("Product Health", counts.get("backlog_open", 0))
        system_cols[3].metric("Workflow Health", f"{health['workflow_completion_rate']}%")

        high_count = len([alert for alert in alerts if alert.get("priority") == "High"])
        medium_count = len([alert for alert in alerts if alert.get("priority") == "Medium"])
        low_count = len([alert for alert in alerts if alert.get("priority") == "Low"])
        st.markdown("### Alert Summary")
        alert_cols = st.columns(3)
        alert_cols[0].metric("High", high_count)
        alert_cols[1].metric("Medium", medium_count)
        alert_cols[2].metric("Low", low_count)

        tabs = st.tabs(
            [
                "Latest Alerts",
                "Conversation",
                "Product",
                "Replay",
                "Sprint",
                "ChatGPT Export",
            ]
        )

        with tabs[0]:
            st.markdown("#### Latest Alerts")
            _render_alert_list(alerts, limit=10)
            st.markdown("#### 7-Day Trend")
            st.json(trends.get("seven_day_trend", {}))
            st.markdown("#### 30-Day Trend")
            st.json(trends.get("thirty_day_trend", {}))
            st.markdown("#### Category Growth")
            st.json(trends.get("category_growth", {}))

        with tabs[1]:
            st.markdown("#### Top Conversation Failures")
            ai_problems = trends.get("most_repeated_ai_problems", {})
            if ai_problems:
                for issue, count in ai_problems.items():
                    st.markdown(f"- **{issue}** x{count}")
            else:
                st.caption("No conversation failures detected in the active session.")
            st.markdown("#### Top AI Issues")
            ai_alerts = [alert for alert in alerts if alert.get("category") in {"Conversation Failure", "Silent Signals"}]
            _render_alert_list(ai_alerts, limit=8)
            st.markdown("#### Latest Conversations With Problems")
            for item in replay[:5]:
                st.markdown(f"- **{item['detected_issue']}**: {item['conversation'][:140]}")

        with tabs[2]:
            st.markdown("#### Top Feature Requests")
            for issue in product_dashboard.get("top_requested_features", []):
                st.markdown(f"- **{issue.get('title')}** ({issue.get('priority')}) x{issue.get('count')}")
            st.markdown("#### Top Bugs")
            for issue in product_dashboard.get("top_bugs", []):
                st.markdown(f"- **{issue.get('title')}** ({issue.get('priority')}) x{issue.get('count')}")
            st.markdown("#### Top UX Issues")
            for issue in product_dashboard.get("top_ux_problems", []):
                st.markdown(f"- **{issue.get('title')}** ({issue.get('priority')}) x{issue.get('count')}")
            st.markdown("#### Issue Frequency")
            st.json(trends.get("issue_frequency", {}))

        with tabs[3]:
            st.markdown("#### Conversation Replay")
            if not replay:
                st.caption("No problem conversations detected.")
            for index, item in enumerate(replay, start=1):
                with st.container(border=True):
                    st.markdown(f"**{index}. Detected Issue:** {item['detected_issue']}")
                    st.markdown("**Conversation**")
                    st.write(item["conversation"])
                    st.markdown("**Assistant**")
                    st.write(item["assistant"])
                    st.markdown("**User Reaction**")
                    st.write(item["user_reaction"] or "No later user reply")
                    st.markdown("**Suggested Fix**")
                    st.write(item["suggested_fix"])

        with tabs[4]:
            st.markdown("#### Top 5 Next Sprint Priorities")
            for item in recommendations:
                with st.container(border=True):
                    st.markdown(f"**{item['rank']}. {item['priority']}**")
                    st.write(f"Impact: {item['impact']}")
                    st.write(f"Expected User Impact: {item['expected_user_impact']}")
                    st.write(item["reason"])
                    st.markdown("Evidence")
                    for evidence in item.get("evidence", []):
                        st.markdown(f"- {evidence}")
                    st.markdown("Recommended files/modules")
                    for module in item.get("recommended_files_modules", []):
                        st.markdown(f"- `{module}`")

        with tabs[5]:
            report_markdown = build_chatgpt_markdown_report(chat_history)
            report_data = build_product_report_data(chat_history)
            col1, col2, col3 = st.columns(3)
            if col1.button("Copy Report", use_container_width=True):
                st.session_state["show_chatgpt_report_copy"] = True
            if col2.button("Save Markdown", use_container_width=True):
                saved_path = save_markdown_report(report_markdown)
                st.success(f"Saved Markdown: {saved_path}")
            if col3.button("Export JSON", use_container_width=True):
                saved_path = save_json_report(report_data)
                st.success(f"Saved JSON: {saved_path}")

            st.caption(f"Markdown path: {MARKDOWN_EXPORT_PATH}")
            st.caption(f"JSON path: {JSON_EXPORT_PATH}")
            if st.session_state.get("show_chatgpt_report_copy"):
                st.text_area("ChatGPT Report", value=report_markdown, height=360)
            st.download_button(
                "Download Markdown",
                data=report_markdown,
                file_name="chatgpt_feedback_report.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.download_button(
                "Download JSON",
                data=json.dumps(report_data, ensure_ascii=False, indent=2),
                file_name="product_report.json",
                mime="application/json",
                use_container_width=True,
            )


def _show_receipt_upload(profile: dict | None) -> None:
    with st.expander("อัปโหลดบิล / สลิป", expanded=False):
        uploaded_file = st.file_uploader(
            "เลือกไฟล์บิลหรือสลิป",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=False,
            key="receipt_uploader",
        )
        if not uploaded_file:
            st.caption("รองรับไฟล์ jpg, jpeg, png และ pdf")
            return

        if st.button("บันทึกไฟล์บิล", use_container_width=True):
            metadata = save_uploaded_receipt(
                uploaded_file,
                store_name=(profile or {}).get("store_name"),
            )
            st.session_state["last_receipt_upload"] = metadata
            receipt_state = mark_receipt_uploaded(metadata, _get_application_state().get("receipt"))
            _get_application_state()["receipt"] = receipt_state
            _update_application_section(
                "workflow",
                {
                    "current_workflow": WORKFLOW_RECEIPT_CAPTURE,
                    "workflow": WORKFLOW_RECEIPT_CAPTURE,
                    "workflow_step": "waiting_for_ocr",
                    "step": "waiting_for_ocr",
                    "is_ready": False,
                },
            )
            _update_application_section(
                "developer",
                {
                    "current_action": "receipt_uploaded",
                    "llm_needed": False,
                    "workflow_ready": False,
                },
            )
            st.success("รับไฟล์บิลแล้วครับ ตอนนี้ระบบบันทึกไฟล์ไว้ก่อน ขั้นถัดไปจะเพิ่มระบบอ่านบิลเพื่อดึงยอดเงินให้อัตโนมัติ")


def _show_chat_companion(
    profile: dict | None,
    business_insight: dict | None,
    recent_topics: list[str],
    diagnosis: dict | None,
    goal_status: dict | None,
    business_os_state: dict | None,
    use_llm_companion: bool,
) -> None:
    st.markdown("### คุยกับผู้ช่วยธุรกิจ")
    _sync_conversation_business_context(profile, goal_status, business_os_state)

    if st.button("เริ่มบทสนทนาใหม่", use_container_width=True):
        _reset_chat_session()
        st.rerun()

    if not profile:
        st.info("กรอกข้อมูลร้านก่อน เพื่อให้แชทตอบโดยใช้บริบทของร้านได้")
        return

    _show_workflow_diagnostics()
    _show_shared_application_state_diagnostics()
    _show_platform_diagnostics()
    _show_ai_pipeline_debug_trace()

    if st.session_state.get("demo_mode") and not st.session_state["chat_history"]:
        _show_demo_chat_suggestions()

    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"], avatar=_chat_avatar(message["role"])):
            _render_markdown(clean_response(message["content"]))
            if message["role"] == "assistant":
                _render_assistant_footer(message)

    _show_smart_chat_prompts()
    user_message = st.chat_input("ถามเรื่องโพสต์ โปร ยอดขาย หรือแผนคอนเทนต์")
    if not user_message:
        return

    if _is_reset_command(user_message):
        _reset_chat_session()
        reset_reply = "เริ่มบทสนทนาใหม่แล้วครับ\n\nวันนี้อยากให้ช่วยเรื่องอะไรครับ"
        _update_conversation_state_after_assistant(reset_reply, "GREETING")
        st.session_state["chat_history"].append({"role": "user", "content": user_message})
        st.session_state["chat_history"].append({"role": "assistant", "content": reset_reply})
        _sync_chat_history_to_application_state()
        with st.chat_message("user", avatar=_chat_avatar("user")):
            _render_markdown(user_message)
        with st.chat_message("assistant", avatar=_chat_avatar("assistant")):
            _render_assistant_response(reset_reply)
        return

    previous_user_message, assistant_reply = _latest_chat_context(st.session_state["chat_history"])
    st.session_state["chat_history"].append({"role": "user", "content": user_message})
    _sync_chat_history_to_application_state()
    with st.chat_message("user", avatar=_chat_avatar("user")):
        _render_markdown(user_message)

    understanding_state = _sync_session_to_application_state()
    conversation_understanding = understand_conversation(user_message, understanding_state)
    conversation_state = _ensure_conversation_state()
    conversation_state["understanding"] = conversation_understanding
    conversation_state["last_understanding"] = conversation_understanding
    _update_application_section("conversation", {"understanding": conversation_understanding, "last_understanding": conversation_understanding})

    conversation_intent = conversation_understanding.get("legacy_intent") or detect_conversation_intent(user_message)
    conversation_mode = get_conversation_mode(conversation_intent)
    planner_message = conversation_understanding.get("planner_message") or user_message
    debug_trace = _new_ai_pipeline_debug_trace(user_message, conversation_understanding)
    workflow_detection = detect_workflow(planner_message, is_product_feedback=is_product_feedback(user_message))
    state = _update_conversation_state_after_user(user_message, conversation_intent, profile)
    chat_profile = _profile_with_conversation_memory(profile) or profile
    reasoning = _record_reasoning(user_message)
    task_route = st.session_state.get("last_task_route") or {}
    _sync_route_intelligence_to_session(task_route)
    _update_ai_pipeline_debug_trace_from_route(debug_trace, task_route)

    def finalize_debug(response_source: str, final_reply: str | None, workflow_extra: dict | None = None) -> None:
        _finalize_ai_pipeline_debug_trace(debug_trace, response_source, final_reply, workflow_extra)

    if reasoning.get("action") in {"receipt_uploaded_ack", "receipt_ocr_pending"}:
        reply = _receipt_uploaded_reply(reasoning.get("action"))
        finalize_debug("reasoning_response", reply, {"reasoning_action": reasoning.get("action")})
        _append_workflow_reply(
            reply,
            WORKFLOW_RECEIPT_CAPTURE,
            "บิล / สลิป",
        )
        return

    planner_first = select_planner_first_response(task_route, st.session_state["chat_history"])
    if planner_first.get("handled"):
        reply = _clean_chat_reply(planner_first["reply"])
        finalize_debug("planner_first_response", reply, {"response_guard": "planner_first"})
        _append_workflow_reply(
            reply,
            planner_first.get("intent") or conversation_intent,
            planner_first.get("topic") or state.get("current_topic"),
        )
        return

    active_workflow = state.get("current_workflow")
    detected_workflow = workflow_detection.get("workflow")
    llm_response_mode = st.session_state.get("llm_response_mode", "Workflow Only")
    active_workflow_v2_state = state.get("workflow_state_v2") or {}
    active_workflow_v2 = active_workflow_v2_state.get("workflow")
    active_workflow_step_v2 = active_workflow_v2_state.get("step")
    detected_workflow_v2 = detect_workflow_intent(planner_message, is_product_feedback=is_product_feedback(user_message))
    if conversation_understanding.get("detected_intent") == "continue_previous_workflow" and active_workflow_v2:
        detected_workflow_v2 = active_workflow_v2
    if (
        not detected_workflow_v2
        and active_workflow_v2
        and active_workflow_step_v2 not in {"completed", "route_to_product_brain"}
        and detected_workflow not in {WORKFLOW_DASHBOARD_REQUEST, WORKFLOW_RECEIPT_CAPTURE, WORKFLOW_PRODUCT_FEEDBACK}
    ):
        detected_workflow_v2 = active_workflow_v2
    debug_trace["workflow"] = _workflow_debug_state(
        {
            "detected_workflow": detected_workflow,
            "detected_workflow_v2": detected_workflow_v2,
            "active_workflow": active_workflow,
            "active_workflow_v2": active_workflow_v2,
            "active_workflow_step_v2": active_workflow_step_v2,
        }
    )

    direct_reply = None
    if should_answer_directly(conversation_understanding):
        direct_reply = build_understanding_direct_reply(
            conversation_understanding,
            profile=chat_profile,
            diagnosis=diagnosis or {},
            goal_status=goal_status or {},
            business_os_state=business_os_state or {},
        )
    if direct_reply:
        direct_reply = _clean_chat_reply(direct_reply, preserve_greeting=False)
        topic = state.get("current_topic")
        _update_conversation_state_after_assistant(direct_reply, conversation_intent, topic)
        assistant_message = {
            "role": "assistant",
            "content": direct_reply,
            "show_business_insights": conversation_understanding.get("detected_intent") in {"store_summary", "business_status"},
        }
        st.session_state["chat_history"].append(assistant_message)
        _sync_chat_history_to_application_state()
        finalize_debug("direct_conversation_response", direct_reply)
        with st.chat_message("assistant", avatar=_chat_avatar("assistant")):
            _render_assistant_response(direct_reply)
        return

    if llm_response_mode != "LLM Only" and detected_workflow_v2 == V2_WORKFLOW_DASHBOARD_REQUEST:
        response = _handle_dashboard_workflow(user_message)
        finalize_debug("workflow_response", response["reply"], {"workflow_handler": "dashboard_v2"})
        _append_workflow_reply(response["reply"], response["intent"], "à¹à¸”à¸Šà¸šà¸­à¸£à¹Œà¸”à¸£à¹‰à¸²à¸™à¸„à¹‰à¸²")
        return

    if llm_response_mode != "LLM Only" and detected_workflow_v2 == V2_WORKFLOW_RECEIPT_CAPTURE:
        response = _handle_receipt_workflow(user_message)
        finalize_debug("workflow_response", response["reply"], {"workflow_handler": "receipt_v2"})
        _append_workflow_reply(response["reply"], response["intent"], "à¸šà¸´à¸¥ / à¸ªà¸¥à¸´à¸›")
        return

    if llm_response_mode != "LLM Only" and detected_workflow_v2 in {
        V2_WORKFLOW_SALES_PLAN_7_DAY,
        V2_WORKFLOW_COST_CALCULATION,
        V2_WORKFLOW_CONTENT_PLAN,
    }:
        response = _handle_state_machine_workflow(
            user_message=user_message,
            detected_workflow=detected_workflow_v2,
            profile=chat_profile,
        )
        source = "llm_response" if response.get("llm_attempted") and st.session_state.get("llm_response_mode") == "Workflow + LLM" else "workflow_response"
        finalize_debug(
            source,
            response["reply"],
            {"workflow_handler": "state_machine_v2", "extracted_fields": response.get("extracted_fields") or {}},
        )
        topic_labels = {
            V2_WORKFLOW_SALES_PLAN_7_DAY: "แผนขาย 7 วัน",
            V2_WORKFLOW_COST_CALCULATION: "คำนวณต้นทุน",
            V2_WORKFLOW_CONTENT_PLAN: "แผนคอนเทนต์",
        }
        _append_workflow_reply(
            response["reply"],
            response["intent"],
            topic_labels.get(response["intent"]),
        )
        return

    if llm_response_mode != "LLM Only" and active_workflow == WORKFLOW_COST_CALCULATION and state.get("workflow_step") == "collecting_cost_inputs" and detected_workflow not in {
        WORKFLOW_DASHBOARD_REQUEST,
        WORKFLOW_RECEIPT_CAPTURE,
        WORKFLOW_PRODUCT_FEEDBACK,
    }:
        response = _handle_cost_workflow(user_message, starting=False)
        finalize_debug("workflow_response", response["reply"], {"workflow_handler": "cost_legacy_continue"})
        _append_workflow_reply(response["reply"], response["intent"], "คำนวณต้นทุน")
        return

    if llm_response_mode != "LLM Only" and detected_workflow == WORKFLOW_COST_CALCULATION:
        response = _handle_cost_workflow(user_message, starting=True)
        finalize_debug("workflow_response", response["reply"], {"workflow_handler": "cost_legacy_start"})
        _append_workflow_reply(response["reply"], response["intent"], "คำนวณต้นทุน")
        return

    if llm_response_mode != "LLM Only" and detected_workflow == WORKFLOW_DASHBOARD_REQUEST:
        response = _handle_dashboard_workflow(user_message)
        finalize_debug("workflow_response", response["reply"], {"workflow_handler": "dashboard_legacy"})
        _append_workflow_reply(response["reply"], response["intent"], "แดชบอร์ดร้านค้า")
        return

    if llm_response_mode != "LLM Only" and detected_workflow == WORKFLOW_RECEIPT_CAPTURE:
        response = _handle_receipt_workflow(user_message)
        finalize_debug("workflow_response", response["reply"], {"workflow_handler": "receipt_legacy"})
        _append_workflow_reply(response["reply"], response["intent"], "บิล / สลิป")
        return

    simple_reply = None
    if conversation_intent == "GREETING":
        simple_reply = _greeting_reply()
    elif _is_correction_message(user_message):
        simple_reply = _one_question_correction_reply()
    elif conversation_intent in {"FOLLOW_UP", "OTHER", "GENERAL_CHAT"}:
        simple_reply = _follow_up_reply(user_message, chat_profile)

    if simple_reply:
        simple_reply = _clean_chat_reply(simple_reply, preserve_greeting=conversation_intent == "GREETING")
        topic = state.get("current_topic")
        _update_conversation_state_after_assistant(simple_reply, conversation_intent, topic)
        assistant_message = {
            "role": "assistant",
            "content": simple_reply,
            "show_business_insights": False,
        }
        st.session_state["chat_history"].append(assistant_message)
        _sync_chat_history_to_application_state()
        finalize_debug("direct_conversation_response", simple_reply)
        with st.chat_message("assistant", avatar=_chat_avatar("assistant")):
            _render_assistant_response(simple_reply)
        return

    if conversation_intent == "PRODUCT_FEEDBACK":
        response = _handle_product_feedback(
            user_message=user_message,
            profile=profile,
            previous_user_message=previous_user_message,
            assistant_reply=assistant_reply,
        )
        assistant_message = {
            "role": "assistant",
            "content": response["reply"],
            "show_business_insights": False,
        }
        _update_conversation_state_after_assistant(response["reply"], conversation_intent, "Product Feedback")
        st.session_state["chat_history"].append(assistant_message)
        _sync_chat_history_to_application_state()
        finalize_debug("planner_response", response["reply"], {"workflow_handler": "product_feedback"})
        with st.chat_message("assistant", avatar=_chat_avatar("assistant")):
            _render_assistant_response(response["reply"])
        return

    use_business_context = should_use_business_context(conversation_intent)
    show_business_insights = should_show_business_insights(conversation_intent, user_message)
    intent_analysis = (
        analyze_chat_intent(
            user_message,
            chat_profile,
            business_insight or {},
            recent_topics,
        )
        if use_business_context
        else {
            "intent": conversation_intent,
            "confidence": 0.85,
            "reasoning": "No current store context needed for this message",
            "suggested_action": None,
            "related_module": None,
            "category": conversation_mode,
        }
    )
    deterministic_response = generate_chat_response(
        user_message=user_message,
        store_profile=chat_profile,
        business_insight=business_insight or {},
        recent_topics=recent_topics,
        chat_history=st.session_state["chat_history"],
        diagnosis=diagnosis or {},
        goal_status=goal_status or {},
        business_os_state=business_os_state or {},
        conversation_intent=conversation_intent,
        conversation_mode=conversation_mode,
        show_business_insights=show_business_insights,
    )
    response = deterministic_response
    response_source = "planner_response"
    demo_ai_success = False
    demo_mode = bool(st.session_state.get("demo_mode"))
    llm_allowed_for_intent = conversation_intent not in {"GREETING", "FOLLOW_UP", "START_BUSINESS"}
    if use_llm_companion and llm_allowed_for_intent:
        llm_context = build_llm_context(
            store_profile=chat_profile,
            business_diagnosis=diagnosis or {},
            goal_status=goal_status or {},
            business_memory=(
                st.session_state.get("business_memory")
                if demo_mode
                else load_business_memory(profile["store_name"])
            ),
            business_os=business_os_state or {},
            recent_topics=recent_topics,
            intent_analysis=intent_analysis,
            conversation_intent=conversation_intent,
            conversation_mode=conversation_mode,
            include_business_context=use_business_context,
            show_business_insights=show_business_insights,
        )
        route = st.session_state.get("last_task_route") or {}
        llm_context = build_prompt_context(
            application_state=_sync_session_to_application_state(),
            planner=route.get("planner_output"),
            capability=route.get("selected_capability"),
            loaded_skill=route.get("loaded_skills"),
            reasoning=route.get("reasoning"),
            conversation_memory=(application_state.get("conversation") or {}),
            workflow_state=(application_state.get("workflow") or {}),
            store_profile=chat_profile,
            product_brain=llm_context,
            developer_mode=bool(st.session_state.get("developer_mode")),
        )
        llm_reply = None
        llm_attempted = False
        budget_allows_llm = can_call_llm(st)
        if not budget_allows_llm:
            print("Fallback reason: budget guard")
            usage = get_llm_usage_state(st)
            if usage["monthly_used_usd"] >= usage["monthly_budget_usd"]:
                st.info("เดือนนี้ระบบ AI ใช้งานครบโควต้าทดลองแล้ว แต่ยังสามารถดูภาพรวมธุรกิจและข้อมูลร้านตัวอย่างได้ตามปกติ")
            else:
                st.info("วันนี้ระบบ AI ใช้งานครบโควต้าทดลองแล้ว แต่ยังสามารถดูภาพรวมธุรกิจและข้อมูลร้านตัวอย่างได้ตามปกติ")
        elif not demo_mode or _allow_demo_llm_call(user_message, llm_context):
            spinner_text = "AI กำลังตอบ..." if not use_business_context else "AI กำลังวิเคราะห์ข้อมูลร้าน..."
            with st.spinner(spinner_text):
                llm_attempted = True
                llm_reply = generate_llm_response(
                    user_message,
                    context=llm_context,
                    demo_mode=demo_mode,
                )
            if llm_reply:
                record_llm_call(st, 0.002 if demo_mode else 0.01)
                if demo_mode and not st.session_state.get("demo_first_ai_success_shown"):
                    st.session_state["demo_first_ai_success_shown"] = True
                    demo_ai_success = True
        else:
            print("Fallback reason: demo token guard")
            st.info("วันนี้ใช้ผู้ช่วย AI สำหรับร้านตัวอย่างครบโควต้าแล้ว แต่ยังสามารถคุยต่อด้วยคำตอบพื้นฐานและใช้ฟีเจอร์เดโมอื่นได้ตามปกติ")
        if llm_attempted and not llm_reply:
            fallback_reason = (
                "missing key"
                if not provider_has_api_key(demo_mode=demo_mode)
                else "provider error"
            )
            print(f"Fallback reason: {fallback_reason}")
            st.caption("ระบบใช้คำตอบพื้นฐานแทนผู้ช่วย AI ชั่วคราว")
        if llm_reply:
            llm_reply = clean_response(llm_reply)
            response = {
                **deterministic_response,
                "reply": llm_reply,
                "related_feature": "ผู้ช่วย AI" if show_business_insights else None,
                "related_module": "ผู้ช่วย AI" if show_business_insights else None,
            }
            response_source = "llm_response"
    elif use_llm_companion and not llm_allowed_for_intent:
        pass
    elif not provider_has_api_key(demo_mode=demo_mode):
        print("Fallback reason: missing key")

    save_business_event(
        store_name=profile["store_name"],
        event_type="chat_question",
        summary=user_message,
        metadata={
            "intent": response.get("intent"),
            "business_intent": response.get("business_intent"),
            "conversation_mode": response.get("conversation_mode"),
            "llm_enabled": bool(use_llm_companion),
            "llm_used": response.get("related_feature") == "ผู้ช่วย AI",
        },
    )
    if response.get("business_intent") == "ask_sales_drop":
        save_business_event(
            store_name=profile["store_name"],
            event_type="sales_problem",
            summary=user_message,
            metadata={"urgency_level": (diagnosis or {}).get("urgency_level")},
        )
    if not st.session_state.get("demo_mode"):
        persisted_goals = dict(st.session_state.get("business_goals") or {})
        persisted_goals["goal_status"] = goal_status or persisted_goals.get("goal_status") or {}
        _save_manual_store_profile(
            profile,
            business_memory=load_business_memory(profile["store_name"]),
            business_goals=persisted_goals,
            business_diagnosis=diagnosis or {},
            business_os=business_os_state or {},
        )
    response["reply"] = _clean_chat_reply(response["reply"])
    guarded_response = guard_response(response["reply"], task_route, st.session_state["chat_history"])
    if guarded_response.get("changed"):
        response["reply"] = _clean_chat_reply(guarded_response["reply"])
        response["intent"] = guarded_response.get("intent") or response.get("intent")
        response_source = "response_guard"
    if response.get("suggested_action"):
        response["suggested_action"] = localize_internal_labels(response["suggested_action"])
    if response.get("related_feature"):
        response["related_feature"] = localize_internal_labels(response["related_feature"])
    assistant_message = {
        "role": "assistant",
        "content": response["reply"],
        "suggested_action": response.get("suggested_action") if show_business_insights else None,
        "related_feature": response.get("related_feature") if show_business_insights else None,
        "show_business_insights": show_business_insights,
    }
    _update_conversation_state_after_assistant(
        response["reply"],
        response.get("intent") or conversation_intent,
        state.get("current_topic"),
    )
    st.session_state["chat_history"].append(assistant_message)
    _sync_chat_history_to_application_state()
    finalize_debug(response_source, response["reply"])

    with st.chat_message("assistant", avatar=_chat_avatar("assistant")):
        _render_assistant_response(response["reply"])
        _render_assistant_footer(assistant_message)
    if demo_ai_success:
        st.success("✨ คุณได้ทดลองใช้ AI แล้ว ลองดูภาพรวมธุรกิจ แผนงานวันนี้ หรือกดสร้างโพสต์ต่อได้เลย")


_init_session_state()

_show_auth_gate()
_show_logout_control()
_show_demo_entry()

st.markdown(
    """
<section class="sme-hero">
    <h1>ผู้ช่วยธุรกิจของคุณ</h1>
    <div class="subtitle">ผู้ช่วย AI สำหรับร้านค้าไทย</div>
    <p class="promise">วันนี้ควรโพสต์อะไร ควรขายอะไร และควรแก้ปัญหาอะไร</p>
</section>
""",
    unsafe_allow_html=True,
)

demo_mode = bool(st.session_state.get("demo_mode"))
demo_profile = st.session_state.get("store_profile") if demo_mode else None
demo_history = _content_examples_to_history(st.session_state.get("content_examples", [])) if demo_mode else []
demo_topics = [item["topic"] for item in demo_history if item.get("topic")]
manual_profile = _manual_store_profile()

store_name = (demo_profile or {}).get("store_name", "") if demo_mode else st.text_input(
    "ชื่อร้าน",
    value=(manual_profile or {}).get("store_name", ""),
    placeholder="เช่น บ้านกาแฟสุขใจ",
)

if demo_mode and demo_profile:
    store_name = demo_profile.get("store_name", "")

current_store_name = store_name.strip().lower()
if current_store_name != st.session_state["active_store_name"]:
    previous_store_name = st.session_state["active_store_name"]
    st.session_state["active_store_name"] = current_store_name
    st.session_state["generated_daily"] = None
    st.session_state["generated_calendar"] = None
    st.session_state["generated_revenue"] = None
    st.session_state["last_diagnosis_signature"] = ""
    if previous_store_name and current_store_name:
        _reset_chat_session()

saved_profile = demo_profile or manual_profile
recent_history = demo_history or (get_content_history(store_name) if store_name.strip() else [])
recent_topics = demo_topics or (get_recent_topics(store_name) if store_name.strip() else [])

dashboard_slot = st.empty()
action_slot = st.empty()
brain_slot = st.empty()
journey_slot = st.empty()

_show_manual_store_storage_caption()
_show_clear_manual_store_control()

store_info_expander = st.sidebar.expander("Store Information", expanded=not bool(saved_profile)) if saved_profile else st.expander("ข้อมูลร้าน", expanded=True)
with store_info_expander:
    store_type = st.text_input(
        "ประเภทร้านค้า",
        value=saved_profile.get("store_type", "") if saved_profile else "",
        placeholder="เช่น ร้านกาแฟ, ร้านเสื้อผ้า, ร้านอาหารฮาลาล",
    )
    product = st.text_input(
        "สินค้า",
        value=saved_profile.get("product", "") if saved_profile else "",
        placeholder="เช่น กาแฟสกัดเย็น, เสื้อเชิ้ต, ข้าวกล่อง",
    )
    target_customer = st.text_input(
        "กลุ่มลูกค้าเป้าหมาย",
        value=saved_profile.get("target_customer", saved_profile.get("customer", "")) if saved_profile else "",
        placeholder="เช่น พนักงานออฟฟิศ, นักศึกษา, คุณแม่",
    )
    tone = st.selectbox(
        "โทนการสื่อสาร",
        TONE_OPTIONS,
        index=_tone_index(saved_profile.get("tone", "")) if saved_profile else 0,
    )

st.markdown(
    """
<div class="sme-action-area">
    <div class="sme-section-title" style="margin-top: 0;">เริ่มทำงานกับร้านวันนี้</div>
</div>
""",
    unsafe_allow_html=True,
)
daily_submitted = False
calendar_submitted = False
sales_submitted = False

input_profile = _build_profile(store_name, store_type, product, target_customer, tone)
active_profile = input_profile or saved_profile
if input_profile and not demo_mode:
    if st.session_state.get("store_profile") != input_profile or st.session_state.get("store_source") != "manual":
        save_store_memory_profile(
            store_name=store_name,
            store_type=store_type,
            product=product,
            target_customer=target_customer,
            tone=tone,
        )
        st.session_state["show_manual_store_setup"] = False
        _save_manual_store_profile(input_profile)
    active_profile = input_profile
_update_application_section(
    "store",
    {
        "active_store_name": current_store_name,
        "profile": active_profile or {},
        "store_source": "demo" if demo_mode else ("manual" if active_profile else None),
        "recent_topics": recent_topics,
    },
)
companion = _build_companion(active_profile, recent_history)
business_insight = analyze_business_insights(active_profile, recent_history) if active_profile else None
diagnosis = (
    st.session_state.get("business_diagnosis")
    if demo_mode
    else (
        diagnose_business_status(
            active_profile,
            business_insight or {},
            recent_topics,
            st.session_state["chat_history"],
        )
        if active_profile
        else None
    )
)
demo_goals = st.session_state.get("business_goals") if demo_mode else None
active_goal = (
    (demo_goals or {}).get("active_goal")
    if demo_mode
    else (get_active_business_goal(active_profile["store_name"]) if active_profile else None)
)
goal_status = (
    evaluate_business_goal(
        active_profile["store_name"],
        active_goal,
        business_insight or {},
        recent_topics,
    )
    if active_profile and active_goal
    else None
)
business_os_state = (
    st.session_state.get("business_os")
    if demo_mode
    else (
        build_business_os_state(
            active_profile,
            business_insight or {},
            diagnosis or {},
            goal_status or {},
            recent_topics,
        )
        if active_profile
        else None
    )
)
with dashboard_slot.container():
    _show_dashboard(companion, business_os_state)
with action_slot.container():
    daily_submitted, calendar_submitted, sales_submitted = _show_ai_ranked_actions(companion, business_os_state)
with brain_slot.container():
    _show_product_brain_card(active_profile, business_insight, diagnosis)
with journey_slot.container():
    _show_business_journey(active_profile, active_goal, business_os_state)
_update_application_section(
    "ui",
    {
        "daily_button_clicked": bool(daily_submitted),
        "calendar_button_clicked": bool(calendar_submitted),
        "sales_button_clicked": bool(sales_submitted),
        "demo_mode": bool(demo_mode),
    },
)

if daily_submitted or calendar_submitted or sales_submitted:
    if not input_profile:
        st.warning("กรุณากรอกชื่อร้าน ประเภทร้านค้า สินค้า และกลุ่มลูกค้าเป้าหมายให้ครบ")
    else:
        active_profile = save_store_memory_profile(
            store_name=store_name,
            store_type=store_type,
            product=product,
            target_customer=target_customer,
            tone=tone,
        )

        if daily_submitted:
            strategy = get_content_strategy(
                store_type=store_type,
                product=product,
                target_customer=target_customer,
                tone=tone,
            )
            content = generate_content_plan(
                store_type=store_type,
                product=product,
                target_customer=target_customer,
                tone=tone,
                strategy=strategy,
                recent_topics=recent_topics,
            )
            save_generated_content(
                store_name=store_name,
                topic=content["topic"],
                content_angle=content["content_angle"],
                strategy_name=strategy["strategy_name"],
                markdown=content["markdown"],
            )
            save_business_event(
                store_name=store_name,
                event_type="content_generated",
                summary=content["topic"],
                metadata={
                    "content_angle": content["content_angle"],
                    "strategy_name": strategy["strategy_name"],
                },
            )
            st.session_state["generated_daily"] = {
                "strategy": strategy,
                "content": content,
            }

        if calendar_submitted:
            calendar = generate_content_calendar(
                store_profile=active_profile,
                recent_topics=recent_topics,
            )
            for item in calendar:
                save_generated_content(
                    store_name=store_name,
                    topic=item["content_theme"],
                    content_angle=item["suggested_product_angle"],
                    strategy_name="แผนคอนเทนต์ 7 วัน",
                    markdown=item["short_caption_idea"],
                )
            save_business_event(
                store_name=store_name,
                event_type="campaign_generated",
                summary="สร้างแผนคอนเทนต์ 7 วัน",
                metadata={"items": len(calendar)},
            )
            st.session_state["generated_calendar"] = calendar

        if sales_submitted:
            strategy = get_content_strategy(
                store_type=store_type,
                product=product,
                target_customer=target_customer,
                tone=tone,
            )
            sales_strategy = get_sales_strategy(
                store_type=store_type,
                product=product,
                target_customer=target_customer,
                tone=tone,
                recent_topics=recent_topics,
            )
            promotion = get_promotion_idea(
                store_type=store_type,
                product=product,
                target_customer=target_customer,
                sales_strategy=sales_strategy,
            )
            campaign = generate_sales_campaign(
                store_type=store_type,
                product=product,
                target_customer=target_customer,
                tone=tone,
                sales_strategy=sales_strategy,
                promotion=promotion,
            )
            sales_brief = generate_sales_brief(
                store_type=store_type,
                product=product,
                target_customer=target_customer,
                tone=tone,
                strategy=strategy,
                sales_strategy=sales_strategy,
                promotion=promotion,
                campaign=campaign,
            )

            for item in campaign:
                save_generated_content(
                    store_name=store_name,
                    topic=item["campaign_theme"],
                    content_angle=item["content_angle"],
                    strategy_name="แผนเพิ่มรายได้ 3 วัน",
                    markdown=item["caption"],
                )
            save_business_event(
                store_name=store_name,
                event_type="campaign_generated",
                summary="สร้างแผนเพิ่มรายได้ 3 วัน",
                metadata={
                    "sales_goal": sales_strategy["sales_goal"],
                    "promotion_name": promotion["promotion_name"],
                },
            )
            st.session_state["generated_revenue"] = {
                "sales_strategy": sales_strategy,
                "promotion": promotion,
                "campaign": campaign,
                "sales_brief": sales_brief,
            }

        recent_history = get_content_history(store_name)
        recent_topics = get_recent_topics(store_name)

companion = _build_companion(active_profile, recent_history)
business_insight = analyze_business_insights(active_profile, recent_history) if active_profile else None
diagnosis = (
    st.session_state.get("business_diagnosis")
    if demo_mode
    else (
        diagnose_business_status(
            active_profile,
            business_insight or {},
            recent_topics,
            st.session_state["chat_history"],
        )
        if active_profile
        else None
    )
)
demo_goals = st.session_state.get("business_goals") if demo_mode else None
active_goal = (
    (demo_goals or {}).get("active_goal")
    if demo_mode
    else (get_active_business_goal(active_profile["store_name"]) if active_profile else None)
)
goal_status = (
    evaluate_business_goal(
        active_profile["store_name"],
        active_goal,
        business_insight or {},
        recent_topics,
    )
    if active_profile and active_goal
    else None
)
business_os_state = (
    st.session_state.get("business_os")
    if demo_mode
    else (
        build_business_os_state(
            active_profile,
            business_insight or {},
            diagnosis or {},
            goal_status or {},
            recent_topics,
        )
        if active_profile
        else None
    )
)
_update_application_section(
    "dashboard",
    {
        "companion": companion or {},
        "business_os_state": business_os_state or {},
        "business_insight": business_insight or {},
        "diagnosis": diagnosis or {},
        "goal_status": goal_status or {},
    },
)
if active_profile and not demo_mode:
    manual_business_memory = load_business_memory(active_profile["store_name"])
    manual_business_goals = {
        "active_goal": active_goal or {},
        "goal_status": goal_status or {},
    }
    _save_manual_store_profile(
        active_profile,
        business_memory=manual_business_memory,
        business_goals=manual_business_goals,
        business_diagnosis=diagnosis or {},
        business_os=business_os_state or {},
        knowledge_layer=st.session_state.get("knowledge_layer", {}),
    )

if active_profile and diagnosis:
    diagnosis_signature = "|".join(
        [
            active_profile["store_name"],
            diagnosis["diagnosis_summary"],
            diagnosis["urgency_level"],
            str(len(recent_history)),
        ]
    )
if (
    active_profile
    and diagnosis
    and diagnosis_signature != st.session_state["last_diagnosis_signature"]
    and not demo_mode
):
    save_business_event(
        store_name=active_profile["store_name"],
        event_type="diagnosis",
        summary=diagnosis["diagnosis_summary"],
        metadata={
            "likely_problem": diagnosis["likely_problem"],
            "urgency_level": diagnosis["urgency_level"],
        },
    )
    st.session_state["last_diagnosis_signature"] = diagnosis_signature
    _save_manual_store_profile(
        active_profile,
        business_memory=load_business_memory(active_profile["store_name"]),
        business_goals={"active_goal": active_goal or {}, "goal_status": goal_status or {}},
        business_diagnosis=diagnosis or {},
        business_os=business_os_state or {},
    )

with dashboard_slot.container():
    _show_dashboard(companion, business_os_state)
_show_daily_content()
_show_calendar()
with st.sidebar:
    _show_receipt_upload(active_profile)
    _show_business_insights(active_profile, recent_history)
    _show_recent_history(recent_history)
    saved_goal = _show_business_os(active_profile, business_os_state, active_goal, goal_status)
if saved_goal:
    save_business_event(
        store_name=active_profile["store_name"],
        event_type="goal_update",
        summary=f"ตั้งเป้าหมาย {saved_goal['goal_label']} = {_format_baht(saved_goal['target_value'])}",
        metadata=saved_goal,
    )
    active_goal = saved_goal
    goal_status = evaluate_business_goal(
        active_profile["store_name"],
        active_goal,
        business_insight or {},
        recent_topics,
    )
    business_os_state = build_business_os_state(
        active_profile,
        business_insight or {},
        diagnosis or {},
        goal_status or {},
        recent_topics,
    )
    if not demo_mode:
        _save_manual_store_profile(
            active_profile,
            business_memory=load_business_memory(active_profile["store_name"]),
            business_goals={"active_goal": active_goal or {}, "goal_status": goal_status or {}},
            business_diagnosis=diagnosis or {},
            business_os=business_os_state or {},
        )
    st.success("บันทึกเป้าหมายร้านแล้ว")
with st.sidebar:
    st.caption("Production account and store controls.")
_show_revenue_engine()

developer_mode = st.sidebar.checkbox(
    "โหมดทีมพัฒนา",
    value=bool(st.session_state.get("developer_mode")),
)
st.session_state["developer_mode"] = developer_mode
_update_application_section("developer", {"developer_mode": bool(developer_mode)})
if not developer_mode:
    st.session_state["llm_response_mode"] = "Workflow Only"

llm_available = is_llm_available(demo_mode=demo_mode)
use_llm_companion = bool(st.session_state.get("use_llm_companion")) if developer_mode else False
if developer_mode:
    llm_response_options = ["Workflow Only", "Workflow + LLM", "LLM Only"]
    current_llm_response_mode = st.session_state.get("llm_response_mode", "Workflow Only")
    if current_llm_response_mode not in llm_response_options:
        current_llm_response_mode = "Workflow Only"
    llm_response_mode = st.sidebar.selectbox(
        "LLM Response Mode",
        llm_response_options,
        index=llm_response_options.index(current_llm_response_mode),
    )
    st.session_state["llm_response_mode"] = llm_response_mode
    llm_default = llm_available if demo_mode else st.session_state["use_llm_companion"]
    if llm_response_mode == "Workflow Only":
        llm_default = False
    elif llm_response_mode == "LLM Only":
        llm_default = llm_available
    use_llm_companion = st.checkbox(
        "ใช้ผู้ช่วย AI เรียบเรียงคำตอบ",
        value=llm_default,
        disabled=(not llm_available) or llm_response_mode == "Workflow Only",
    )
    st.session_state["use_llm_companion"] = use_llm_companion
    _update_application_section(
        "developer",
        {
            "developer_mode": True,
            "use_llm_companion": bool(use_llm_companion),
            "llm_response_mode": llm_response_mode,
        },
    )
    _update_application_section("ui", {"llm_response_mode": llm_response_mode})
    if use_llm_companion:
        st.caption("ผู้ช่วย AI จะเรียบเรียงคำตอบให้อ่านง่าย โดยยังยึดเหตุผลจากระบบเดิม")
    elif not llm_available:
        st.caption("ยังไม่ได้ตั้งค่ากุญแจเชื่อมต่อสำหรับผู้ช่วย AI ระบบจะใช้แชทแบบกฎพื้นฐานตามเดิม")

_update_application_section(
    "developer",
    {
        "developer_mode": bool(developer_mode),
        "use_llm_companion": bool(use_llm_companion),
        "llm_response_mode": st.session_state.get("llm_response_mode", "Workflow Only"),
    },
)
_update_application_section("ui", {"llm_response_mode": st.session_state.get("llm_response_mode", "Workflow Only")})

_show_feedback_summary()
_show_developer_alert_center()

_show_chat_companion(
    active_profile,
    business_insight,
    recent_topics,
    diagnosis,
    goal_status,
    business_os_state,
    use_llm_companion,
)
