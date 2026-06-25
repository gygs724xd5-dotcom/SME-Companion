import re
import time

import streamlit as st

from billing.budget_guard import DAILY_BUDGET_USD, can_call_llm, get_llm_usage_state, record_llm_call
from brain.business_insight_engine import analyze_business_insights
from brain.business_diagnosis_engine import diagnose_business_status
from brain.business_memory_engine import load_business_memory, save_business_event
from brain.business_os_engine import build_business_os_state
from brain.campaign_engine import generate_sales_campaign
from brain.chat_companion_engine import generate_chat_response
from brain.chat_intelligence_engine import analyze_chat_intent
from brain.content_calendar_engine import generate_content_calendar
from brain.content_strategy_engine import get_content_strategy
from brain.goal_engine import (
    create_business_goal,
    evaluate_business_goal,
    get_active_business_goal,
)
from brain.llm_context_builder import build_llm_context
from brain.promotion_engine import get_promotion_idea
from brain.sales_strategy_engine import get_sales_strategy
from brain.sme_companion_engine import generate_sme_companion
from content_engine import generate_content_plan, generate_sales_brief
from demo.demo_loader import inject_demo_store_to_session, list_demo_stores
from llm.llm_router import generate_llm_response, is_llm_available
from memory.store_memory import (
    get_content_history,
    get_recent_topics,
    get_store_profile,
    save_generated_content,
    save_store_profile,
)


st.set_page_config(
    page_title="SME Companion",
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
        background: var(--sme-surface);
        border: 1px solid var(--sme-border);
        border-radius: 24px;
        box-shadow: var(--sme-shadow);
        padding: 18px 18px 10px;
        margin: 8px 0 16px;
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
        background: rgba(255, 255, 255, 0.86);
        border: 1px solid var(--sme-border);
        border-radius: 18px;
        padding: 8px 10px;
    }

    [data-testid="stChatInput"] {
        border-radius: 18px;
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


def _format_baht(value) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0

    if amount.is_integer():
        return f"{amount:,.0f} บาท"
    return f"{amount:,.2f} บาท"


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


def _init_session_state() -> None:
    st.session_state.setdefault("demo_mode", False)
    st.session_state.setdefault("selected_demo_store", None)
    st.session_state.setdefault("demo_llm_tokens_used", 0)
    st.session_state.setdefault("demo_first_ai_success_shown", False)
    st.session_state.setdefault("show_manual_store_setup", False)
    st.session_state.setdefault("llm_usage_daily", {})
    st.session_state.setdefault("llm_usage_monthly", {})
    st.session_state.setdefault("generated_daily", None)
    st.session_state.setdefault("generated_calendar", None)
    st.session_state.setdefault("generated_revenue", None)
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("active_store_name", "")
    st.session_state.setdefault("last_diagnosis_signature", "")
    st.session_state.setdefault("use_llm_companion", False)


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
    with st.status("SME Companion กำลังเตรียมร้านตัวอย่าง...", expanded=True) as status:
        demo_data = inject_demo_store_to_session(st, store_key)
        st.write("✓ โหลดข้อมูลร้าน")
        time.sleep(0.2)
        st.write("✓ วิเคราะห์ธุรกิจ")
        time.sleep(0.2)
        st.write("✓ เตรียม AI Companion")
        time.sleep(0.2)
        st.write("✓ พร้อมใช้งาน")
        status.update(label="พร้อมใช้งาน", state="complete", expanded=True)

    store_name = (demo_data.get("store_profile") or {}).get("store_name", "")
    st.session_state["active_store_name"] = store_name.strip().lower()
    st.session_state["chat_history"] = [
        {
            "role": "assistant",
            "content": (
                "สวัสดีครับ ผมคือ SME Companion AI ตอนนี้ผมโหลดข้อมูลร้านตัวอย่างเรียบร้อยแล้ว "
                "ลองถามผมได้เลย เช่น วันนี้ควรโพสต์อะไร หรือควรเพิ่มยอดขายยังไง"
            ),
        }
    ]
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
            st.session_state["demo_mode"] = False
            st.session_state["selected_demo_store"] = None
            st.session_state["demo_llm_tokens_used"] = 0
            st.session_state["demo_first_ai_success_shown"] = False
            st.rerun()
        return

    if st.session_state.get("show_manual_store_setup"):
        return

    st.title("SME Companion AI")
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
        st.info("กรอกข้อมูลร้านเพื่อให้ SME Companion วิเคราะห์คำแนะนำวันนี้ โอกาส และสิ่งที่ควรทำ")
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

    with st.expander("คอนเทนต์วันนี้", expanded=True):
        strategy = daily["strategy"]
        content = daily["content"]
        st.markdown(
            f"""
**{strategy["strategy_name"]}**

**เป้าหมาย:** {strategy["content_goal"]}

**เวลาที่เหมาะ:** {strategy["best_posting_time"]}

**มุมคอนเทนต์:** {content["content_angle"]}
"""
        )
        st.divider()
        _render_markdown(content["markdown"])


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


def _show_chat_companion(
    profile: dict | None,
    business_insight: dict | None,
    recent_topics: list[str],
    diagnosis: dict | None,
    goal_status: dict | None,
    business_os_state: dict | None,
    use_llm_companion: bool,
) -> None:
    st.markdown("### คุยกับ SME Companion")

    if not profile:
        st.info("กรอกข้อมูลร้านก่อน เพื่อให้แชทตอบโดยใช้บริบทของร้านได้")
        return

    if st.session_state.get("demo_mode") and not st.session_state["chat_history"]:
        _show_demo_chat_suggestions()

    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            _render_markdown(message["content"])
            if message["role"] == "assistant":
                if message.get("suggested_action"):
                    st.caption(f"สิ่งที่แนะนำ: {message['suggested_action']}")
                if message.get("related_feature"):
                    st.caption(f"ฟีเจอร์ที่เกี่ยวข้อง: {message['related_feature']}")

    user_message = st.chat_input("ถามเรื่องโพสต์ โปร ยอดขาย หรือแผนคอนเทนต์")
    if not user_message:
        return

    st.session_state["chat_history"].append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        _render_markdown(user_message)

    intent_analysis = analyze_chat_intent(
        user_message,
        profile,
        business_insight or {},
        recent_topics,
    )
    deterministic_response = generate_chat_response(
        user_message=user_message,
        store_profile=profile,
        business_insight=business_insight or {},
        recent_topics=recent_topics,
        chat_history=st.session_state["chat_history"],
        diagnosis=diagnosis or {},
        goal_status=goal_status or {},
        business_os_state=business_os_state or {},
    )
    response = deterministic_response
    demo_ai_success = False
    if use_llm_companion:
        demo_mode = bool(st.session_state.get("demo_mode"))
        llm_context = build_llm_context(
            store_profile=profile,
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
        )
        llm_reply = None
        budget_allows_llm = can_call_llm(st)
        if not budget_allows_llm:
            usage = get_llm_usage_state(st)
            if usage["monthly_used_usd"] >= usage["monthly_budget_usd"]:
                st.info("เดือนนี้ระบบ AI ใช้งานครบโควต้าทดลองแล้ว แต่ยังสามารถดูภาพรวมธุรกิจและข้อมูลร้านตัวอย่างได้ตามปกติ")
            else:
                st.info("วันนี้ระบบ AI ใช้งานครบโควต้าทดลองแล้ว แต่ยังสามารถดูภาพรวมธุรกิจและข้อมูลร้านตัวอย่างได้ตามปกติ")
        elif not demo_mode or _allow_demo_llm_call(user_message, llm_context):
            with st.spinner("AI กำลังวิเคราะห์ข้อมูลร้าน..."):
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
            st.info("วันนี้ใช้ผู้ช่วย AI สำหรับร้านตัวอย่างครบโควต้าแล้ว แต่ยังสามารถคุยต่อด้วยคำตอบพื้นฐานและใช้ฟีเจอร์เดโมอื่นได้ตามปกติ")
        if budget_allows_llm and not llm_reply:
            st.caption("ระบบใช้คำตอบพื้นฐานแทนผู้ช่วย AI ชั่วคราว")
        if llm_reply:
            response = {
                **deterministic_response,
                "reply": llm_reply,
                "related_feature": "ผู้ช่วย AI",
                "related_module": "ผู้ช่วย AI",
            }

    save_business_event(
        store_name=profile["store_name"],
        event_type="chat_question",
        summary=user_message,
        metadata={
            "intent": response.get("intent"),
            "llm_enabled": bool(use_llm_companion),
            "llm_used": response.get("related_feature") == "ผู้ช่วย AI",
        },
    )
    if response.get("intent") == "ask_sales_drop":
        save_business_event(
            store_name=profile["store_name"],
            event_type="sales_problem",
            summary=user_message,
            metadata={"urgency_level": (diagnosis or {}).get("urgency_level")},
        )
    assistant_message = {
        "role": "assistant",
        "content": response["reply"],
        "suggested_action": response.get("suggested_action"),
        "related_feature": response.get("related_feature"),
    }
    st.session_state["chat_history"].append(assistant_message)

    with st.chat_message("assistant"):
        _render_markdown(response["reply"])
        if response.get("suggested_action"):
            st.caption(f"สิ่งที่แนะนำ: {response['suggested_action']}")
        if response.get("related_feature"):
            st.caption(f"ฟีเจอร์ที่เกี่ยวข้อง: {response['related_feature']}")
    if demo_ai_success:
        st.success("✨ คุณได้ทดลองใช้ AI แล้ว ลองดูภาพรวมธุรกิจ แผนงานวันนี้ หรือกดสร้างโพสต์ต่อได้เลย")


_init_session_state()

_show_demo_entry()

st.markdown(
    """
<section class="sme-hero">
    <h1>SME Companion</h1>
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

store_name = (demo_profile or {}).get("store_name", "") if demo_mode else st.text_input(
    "ชื่อร้าน",
    placeholder="เช่น บ้านกาแฟสุขใจ",
)

if demo_mode and demo_profile:
    store_name = demo_profile.get("store_name", "")

current_store_name = store_name.strip().lower()
if current_store_name != st.session_state["active_store_name"]:
    st.session_state["active_store_name"] = current_store_name
    st.session_state["generated_daily"] = None
    st.session_state["generated_calendar"] = None
    st.session_state["generated_revenue"] = None
    if not demo_mode:
        st.session_state["chat_history"] = []
    st.session_state["last_diagnosis_signature"] = ""

saved_profile = demo_profile or (get_store_profile(store_name) if store_name.strip() else None)
recent_history = demo_history or (get_content_history(store_name) if store_name.strip() else [])
recent_topics = demo_topics or (get_recent_topics(store_name) if store_name.strip() else [])

dashboard_slot = st.empty()

with st.expander("ข้อมูลร้าน", expanded=not bool(saved_profile)):
    store_type = st.text_input(
        "ประเภทร้านค้า",
        value=saved_profile["store_type"] if saved_profile else "",
        placeholder="เช่น ร้านกาแฟ, ร้านเสื้อผ้า, ร้านอาหารฮาลาล",
    )
    product = st.text_input(
        "สินค้า",
        value=saved_profile["product"] if saved_profile else "",
        placeholder="เช่น กาแฟสกัดเย็น, เสื้อเชิ้ต, ข้าวกล่อง",
    )
    target_customer = st.text_input(
        "กลุ่มลูกค้าเป้าหมาย",
        value=saved_profile["target_customer"] if saved_profile else "",
        placeholder="เช่น พนักงานออฟฟิศ, นักศึกษา, คุณแม่",
    )
    tone = st.selectbox(
        "โทนการสื่อสาร",
        TONE_OPTIONS,
        index=_tone_index(saved_profile["tone"]) if saved_profile else 0,
    )

st.markdown(
    """
<div class="sme-action-area">
    <div class="sme-section-title" style="margin-top: 0;">เริ่มทำงานกับร้านวันนี้</div>
</div>
""",
    unsafe_allow_html=True,
)
action_col1, action_col2, action_col3 = st.columns(3)
daily_submitted = action_col1.button("📝 สร้างโพสต์วันนี้", use_container_width=True)
calendar_submitted = action_col2.button("📅 สร้างแผน 7 วัน", use_container_width=True)
sales_submitted = action_col3.button("📈 วางแผนเพิ่มยอดขาย", use_container_width=True)

input_profile = _build_profile(store_name, store_type, product, target_customer, tone)
active_profile = input_profile or saved_profile

if daily_submitted or calendar_submitted or sales_submitted:
    if not input_profile:
        st.warning("กรุณากรอกชื่อร้าน ประเภทร้านค้า สินค้า และกลุ่มลูกค้าเป้าหมายให้ครบ")
    else:
        active_profile = save_store_profile(
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

with dashboard_slot.container():
    _show_dashboard(companion, business_os_state)
_show_daily_content()
_show_calendar()
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
    st.success("บันทึกเป้าหมายร้านแล้ว")
_show_revenue_engine()
llm_available = is_llm_available(demo_mode=demo_mode)
llm_default = llm_available if demo_mode else st.session_state["use_llm_companion"]
use_llm_companion = st.checkbox(
    "ใช้ผู้ช่วย AI เรียบเรียงคำตอบ",
    value=llm_default,
    disabled=not llm_available,
)
st.session_state["use_llm_companion"] = use_llm_companion
if use_llm_companion:
    st.caption("ผู้ช่วย AI จะเรียบเรียงคำตอบให้อ่านง่าย โดยยังยึดเหตุผลจากระบบเดิม")
elif not llm_available:
    st.caption("ยังไม่ได้ตั้งค่ากุญแจเชื่อมต่อสำหรับผู้ช่วย AI ระบบจะใช้แชทแบบกฎพื้นฐานตามเดิม")

_show_chat_companion(
    active_profile,
    business_insight,
    recent_topics,
    diagnosis,
    goal_status,
    business_os_state,
    use_llm_companion,
)
