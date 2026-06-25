URGENCY_PENALTY = {"ต่ำ": 5, "กลาง": 15, "สูง": 25}
GOAL_RISK_PENALTY = {"ต่ำ": 0, "กลาง": 10, "สูง": 20}


def _safe_int(value, fallback=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _missing_text(missing_types: list[str]) -> str:
    if not missing_types:
        return "ยังไม่พบคอนเทนต์ที่ขาดชัดเจน"
    return "ยังขาด " + ", ".join(missing_types[:3])


def _operating_status(score: int, urgency: str) -> str:
    if score >= 80 and urgency == "ต่ำ":
        return "ระบบร้านแข็งแรง เดินหน้าขยายผลได้"
    if score >= 60:
        return "ระบบร้านพอใช้ แต่ยังมีจุดที่ต้องจัดระเบียบ"
    if score >= 40:
        return "ต้องโฟกัสแก้จุดอ่อนหลักก่อนเพิ่มแคมเปญ"
    return "ต้องรีบตั้งหลักเรื่องความน่าเชื่อถือและความสม่ำเสมอ"


def build_business_os_state(
    store_profile,
    business_insight,
    diagnosis,
    goal_status,
    recent_topics,
) -> dict:
    """Build a lightweight deterministic operating state for the SME dashboard."""
    profile = store_profile or {}
    insight = business_insight or {}
    diagnosis_data = diagnosis or {}
    goal = goal_status or {}
    topics = recent_topics or []

    store_name = profile.get("store_name") or "ร้านของคุณ"
    product = profile.get("product") or "สินค้า"
    missing_types = insight.get("missing_content_types") or []
    total_content = _safe_int(insight.get("total_generated_content"))
    unique_topics = len(set(topic.lower() for topic in topics if topic))
    repeated_topics = max(0, len(topics) - unique_topics)
    urgency = diagnosis_data.get("urgency_level") or "กลาง"
    progress_pct = _safe_int(goal.get("progress_pct"))
    goal_risk = goal.get("goal_risk") or "กลาง"

    score = 100
    score -= min(30, len(missing_types) * 6)
    score -= 15 if total_content < 3 else 0
    score -= min(20, repeated_topics * 7)
    score -= 10 if unique_topics < min(3, len(topics)) else 0
    score -= URGENCY_PENALTY.get(urgency, 15)
    score -= GOAL_RISK_PENALTY.get(goal_risk, 10)
    if goal and progress_pct < 35:
        score -= 10
    business_health_score = max(0, min(100, score))

    top_priority = diagnosis_data.get("recommended_fix") or "ทำคอนเทนต์ให้ต่อเนื่องและวัดผลจากยอดทักแชท"
    current_risk = diagnosis_data.get("likely_problem") or _missing_text(missing_types)
    growth_opportunity = insight.get("next_best_content_angle") or f"ทำให้ลูกค้าเห็นเหตุผลซื้อ {product} ชัดขึ้น"
    today_action = diagnosis_data.get("next_3_actions", [top_priority])[0]
    if goal.get("next_best_action"):
        today_action = goal["next_best_action"]

    weekly_focus = "สลับคอนเทนต์ 4 มุม: ความรู้ รีวิว เบื้องหลัง และข้อเสนอ"
    if missing_types:
        weekly_focus = f"เติมคอนเทนต์ที่ยังขาดก่อน: {', '.join(missing_types[:3])}"
    if goal.get("goal_type") == "repeat_customers":
        weekly_focus = "สร้างเหตุผลให้ลูกค้าเก่ากลับมาซื้อซ้ำ"
    elif goal.get("goal_type") == "trust_building":
        weekly_focus = "สะสมรีวิว หลักฐาน และเบื้องหลังร้านให้ลูกค้าเชื่อก่อนซื้อ"

    owner_message = (
        f"{store_name} ควรโฟกัสวันนี้ที่ {today_action} "
        f"เพราะความเสี่ยงหลักคือ {current_risk}"
    )

    return {
        "business_health_score": business_health_score,
        "operating_status": _operating_status(business_health_score, urgency),
        "top_priority": top_priority,
        "current_risk": current_risk,
        "growth_opportunity": growth_opportunity,
        "today_action": today_action,
        "weekly_focus": weekly_focus,
        "owner_message": owner_message,
    }
