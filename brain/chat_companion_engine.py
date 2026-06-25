from brain.chat_intelligence_engine import analyze_chat_intent
from knowledge.knowledge_router import get_playbook


def _clean(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _history_summary(recent_topics: list[str]) -> str:
    topics = [topic.strip() for topic in recent_topics or [] if topic and topic.strip()]
    if not topics:
        return "ยังไม่มีหัวข้อคอนเทนต์ล่าสุดให้เทียบ จึงควรเริ่มจากมุมที่สร้างความน่าเชื่อถือก่อน"
    return "หัวข้อล่าสุดคือ " + ", ".join(topics[:3])


def _context(profile: dict, insight: dict, recent_topics: list[str]) -> dict:
    product = _clean(profile.get("product"), "สินค้า")
    target_customer = _clean(profile.get("target_customer"), "ลูกค้า")
    store_type = _clean(profile.get("store_type"), "ร้านค้า")
    return {
        "store_name": _clean(profile.get("store_name"), "ร้านของคุณ"),
        "store_type": store_type,
        "product": product,
        "target_customer": target_customer,
        "tone": _clean(profile.get("tone"), "เป็นกันเอง"),
        "playbook": get_playbook(store_type),
        "next_angle": _clean(
            insight.get("next_best_content_angle"),
            f"เล่าประโยชน์ของ {product} ให้ชัดและปิดท้ายด้วยการชวนทักแชท",
        ),
        "recommendation": _clean(
            insight.get("business_recommendation"),
            f"เริ่มจากคอนเทนต์ที่ทำให้{target_customer}เข้าใจเร็วว่า {product} ช่วยอะไร",
        ),
        "repeated_warning": _clean(
            insight.get("repeated_topic_warning"),
            "ยังไม่มีสัญญาณหัวข้อซ้ำที่น่ากังวล",
        ),
        "missing_types": insight.get("missing_content_types") or [],
        "history_text": _history_summary(recent_topics),
    }


def _missing_text(ctx: dict) -> str:
    missing_types = ctx["missing_types"]
    if not missing_types:
        return "คอนเทนต์ยังไม่มีช่องว่างชัดเจน แต่ยังควรสลับมุมขาย มุมรีวิว และมุมให้ความรู้"
    return "ยังขาดคอนเทนต์ประเภท " + ", ".join(missing_types[:3])


def _ideas(playbook: dict, key: str, fallback: list[str], limit: int = 3) -> list[str]:
    items = [item for item in playbook.get(key, []) if item]
    return (items or fallback)[:limit]


def _idea_text(playbook: dict, key: str, fallback: list[str], limit: int = 3) -> str:
    return "\n".join(
        f"{index}. {idea}"
        for index, idea in enumerate(_ideas(playbook, key, fallback, limit), start=1)
    )


def _intent_answer(intent: str, ctx: dict) -> tuple[str, str]:
    product = ctx["product"]
    target_customer = ctx["target_customer"]
    store_name = ctx["store_name"]
    store_type = ctx["store_type"]
    next_angle = ctx["next_angle"]
    recommendation = ctx["recommendation"]
    history_text = ctx["history_text"]
    missing_text = _missing_text(ctx)
    playbook = ctx["playbook"]
    content_ideas = _idea_text(
        playbook,
        "best_content_types",
        ["ประโยชน์สินค้า", "รีวิวลูกค้า", "เบื้องหลังร้าน"],
    )
    reels_ideas = _idea_text(
        playbook,
        "reels_ideas",
        ["โชว์สินค้าในการใช้งานจริง", "ตอบคำถามลูกค้าบ่อย", "เล่าปัญหาแล้วเสนอวิธีแก้"],
    )
    photo_ideas = _idea_text(
        playbook,
        "photo_ideas",
        ["ภาพสินค้าในการใช้งานจริง", "ภาพรายละเอียดสินค้า", "ภาพรีวิวลูกค้า"],
    )
    promotion_ideas = _idea_text(
        playbook,
        "promotion_ideas",
        ["โปรลูกค้าใหม่", "เซตแนะนำราคาพิเศษ", "ข้อเสนอจำกัดเวลา"],
    )
    trust_ideas = _idea_text(
        playbook,
        "customer_trust_ideas",
        ["รีวิวลูกค้าจริง", "เบื้องหลังร้าน", "วิธีสั่งซื้อชัดเจน"],
    )
    repeat_ideas = _idea_text(
        playbook,
        "repeat_customer_ideas",
        ["สิทธิ์พิเศษลูกค้าเก่า", "โปรซื้อซ้ำ", "แจ้งสินค้าใหม่ให้ลูกค้าเก่าก่อน"],
    )

    answers = {
        "ask_daily_post": (
            f"วันนี้ {store_name} ควรโพสต์มุมที่ช่วยให้{target_customer}ตัดสินใจง่ายขึ้น: {next_angle}",
            f"{history_text} และ {missing_text}",
        ),
        "ask_content_idea": (
            f"ไอเดียคอนเทนต์ที่เหมาะกับ {store_type} ตอนนี้คือ\n\n{content_ideas}",
            f"{recommendation} และควรหลีกเลี่ยงการใช้หัวข้อซ้ำกับช่วงล่าสุด",
        ),
        "ask_photo_idea": (
            f"รูปที่ควรถ่ายสำหรับ {store_type} คือ\n\n{photo_ideas}",
            f"{target_customer} มักตัดสินใจง่ายขึ้นเมื่อเห็น {product} ในสถานการณ์จริง ไม่ใช่แค่ภาพสินค้าเดี่ยว",
        ),
        "ask_video_idea": (
            f"ทำวิดีโอสั้นแบบ 3 ช่วง: ปัญหาของลูกค้า, วิธีที่ {product} ช่วย, แล้วชวนทักแชท",
            f"วิดีโอควรทำให้เห็นเหตุผลซื้อเร็วกว่าโพสต์ข้อความ และช่วยอธิบายคุณค่าของ {product} ได้ชัด",
        ),
        "ask_reels_idea": (
            f"Reels ที่เหมาะกับ {store_type} คือ\n\n{reels_ideas}",
            "Reels เหมาะกับการทำให้คนหยุดดูเร็ว จึงต้องเริ่มจากปัญหาหรือผลลัพธ์ที่ลูกค้าสนใจ",
        ),
        "ask_tiktok_idea": (
            f"ทำ TikTok แบบเล่าเร็ว: ก่อนใช้ {product}, หลังใช้, แล้วปิดด้วยเหตุผลว่าทำไมเหมาะกับ{target_customer}",
            "TikTok ต้องเห็นภาพไวและมีเรื่องเล่าชัด จึงควรใช้สถานการณ์จริงมากกว่าขายตรงตั้งแต่ต้น",
        ),
        "ask_caption": (
            f"แคปชั่นควรเริ่มจากปัญหาของ{target_customer} ตามด้วยคุณค่าของ {product} และจบด้วยคำชวนทัก",
            f"โทนของร้านคือ{ctx['tone']} จึงควรเขียนให้เข้าใจง่ายและไม่ขายแข็งเกินไป",
        ),
        "ask_sales_drop": (
            "ยอดขายตกอาจเกิดจาก 3 สาเหตุ\n\n1. คนเห็นโพสต์น้อยลง\n2. คอนเทนต์ซ้ำ\n3. ข้อเสนอไม่น่าสนใจ",
            f"จากข้อมูลร้านของคุณ {missing_text} และ {ctx['repeated_warning']}",
        ),
        "ask_sales_growth": (
            f"ถ้าอยากเพิ่มยอดขาย ให้ดัน {product} ด้วยข้อเสนอที่ชัดและคอนเทนต์ที่ทำให้เห็นเหตุผลซื้อทันที",
            f"{target_customer} ต้องเห็นทั้งความคุ้ม ความน่าเชื่อถือ และวิธีสั่งที่ง่ายในโพสต์เดียว",
        ),
        "ask_promotion": (
            f"โปรที่เหมาะกับ {store_type} คือ\n\n{promotion_ideas}",
            f"โปรควรเสริมคุณค่าของ {product} ไม่ใช่ทำให้ลูกค้าจำร้านได้แค่ราคาถูก",
        ),
        "ask_product_focus": (
            f"ให้โฟกัสสินค้าที่อธิบายประโยชน์ได้ชัดที่สุด และโยงกับความต้องการของ{target_customer}ได้เร็ว",
            "สินค้าที่ขายง่ายไม่ใช่แค่ราคาดี แต่ต้องมีเหตุผลซื้อที่เล่าเป็นคอนเทนต์ต่อเนื่องได้",
        ),
        "ask_price": (
            f"ถ้าลูกค้าลังเลเรื่องราคา ให้สื่อสารว่า {product} คุ้มอย่างไร แก้ปัญหาอะไร และต่างจากตัวเลือกทั่วไปตรงไหน",
            "ลูกค้าจะรับราคาได้ง่ายขึ้นเมื่อเห็นคุณค่า รีวิว และผลลัพธ์ก่อนเห็นตัวเลขราคา",
        ),
        "ask_new_customer": (
            f"ถ้าต้องการลูกค้าใหม่ ให้เริ่มจากคอนเทนต์ลดความเสี่ยงครั้งแรกของ {product}",
            "ลูกค้าใหม่ยังไม่เชื่อร้าน จึงต้องเห็นรีวิว วิธีสั่ง ความชัดเจน และข้อเสนอเริ่มต้นที่ตัดสินใจง่าย",
        ),
        "ask_repeat_customer": (
            f"ถ้าต้องการซื้อซ้ำ ให้ใช้ไอเดียสำหรับลูกค้าเก่าแบบนี้\n\n{repeat_ideas}",
            "ลูกค้าเก่าต้องการเหตุผลใหม่ในการกลับมา เช่น สิทธิ์พิเศษ ของแถม หรือสินค้าเซตที่คุ้มกว่าเดิม",
        ),
        "ask_customer_retention": (
            f"รักษาลูกค้าด้วยไอเดียซื้อซ้ำเหล่านี้\n\n{repeat_ideas}",
            "ความสัมพันธ์ระยะยาวเกิดจากความใส่ใจ รีวิวต่อเนื่อง และข้อเสนอที่เหมาะกับคนที่เคยซื้อ",
        ),
        "ask_customer_trust": (
            f"ถ้าลูกค้ายังไม่มั่นใจ ให้เพิ่มคอนเทนต์สร้างความเชื่อถือแบบนี้\n\n{trust_ideas}",
            f"{missing_text} ซึ่งมีผลโดยตรงต่อความมั่นใจก่อนซื้อ",
        ),
        "ask_calendar": (
            f"แผนคอนเทนต์ควรสลับ 4 มุม: ประโยชน์สินค้า รีวิว เบื้องหลัง และโปรจำกัดเวลา",
            f"{history_text} ดังนั้นแผนถัดไปควรเติมมุมใหม่: {next_angle}",
        ),
        "ask_week_plan": (
            f"สัปดาห์นี้ควรวาง 7 วันให้ครบทั้งรู้จักร้าน เชื่อมั่นสินค้า เห็นวิธีใช้ และมีเหตุผลซื้อ",
            f"การสลับมุมช่วยไม่ให้คอนเทนต์ซ้ำและทำให้{target_customer}เจอเหตุผลซื้อหลายแบบ",
        ),
        "ask_month_plan": (
            "แผนเดือนควรแบ่งเป็น 4 สัปดาห์: สร้างการรู้จัก, สร้างความเชื่อมั่น, กระตุ้นซื้อ, และดึงลูกค้าเก่ากลับมา",
            "แผนรายเดือนที่ดีต้องไม่ใช่โพสต์ขายซ้ำทุกวัน แต่ต้องพาลูกค้าจากรู้จักไปจนถึงซื้อซ้ำ",
        ),
        "ask_competitor": (
            f"อย่าแข่งด้วยราคาก่อน ให้หาจุดต่างของ {store_name} แล้วเล่าให้ลูกค้าเห็นว่าทำไม {product} ถึงเหมาะกับเขา",
            "การโจมตีคู่แข่งทำให้แบรนด์ดูอ่อน แต่การเล่าคุณค่า รีวิว และเบื้องหลังทำให้ร้านน่าเชื่อถือกว่า",
        ),
        "ask_business_problem": (
            "ให้แยกปัญหาร้านเป็น 4 จุด: คนเห็นน้อย, คนไม่เชื่อ, ข้อเสนอไม่ชัด, หรือปิดการขายยาก",
            f"จากบริบทตอนนี้ {recommendation}",
        ),
        "ask_business_growth": (
            f"ถ้าต้องการให้ร้านโต ให้สร้างระบบคอนเทนต์ประจำสัปดาห์คู่กับโปรที่วัดผลได้",
            f"{store_type} จะโตได้ดีขึ้นเมื่อมีทั้งคอนเทนต์สร้างความเชื่อมั่นและแคมเปญปิดการขาย",
        ),
    }

    return answers.get(
        intent,
        (
            f"จากบริบทของ {store_name} คำแนะนำตอนนี้คือโฟกัสมุมที่ทำให้ลูกค้าเข้าใจเหตุผลซื้อเร็วที่สุด",
            f"{recommendation} และ {history_text}",
        ),
    )


def _format_reply(direct_answer: str, why: str, suggested_action: str, related_module: str) -> str:
    return (
        f"{direct_answer}\n\n"
        f"ทำไม:\n{why}\n\n"
        f"แนะนำ:\n{suggested_action}\n\n"
        f"ฟีเจอร์ที่เกี่ยวข้อง:\n{related_module}"
    )


def _needs_os_answer(message: str, intent: str) -> bool:
    os_keywords = [
        "ยอดขายตก",
        "ทำยังไงให้ร้านดีขึ้น",
        "เป้าหมาย",
        "เดือนนี้ต้องทำอะไร",
        "ร้านมีปัญหาอะไร",
    ]
    return intent in {
        "ask_sales_drop",
        "ask_business_problem",
        "ask_business_growth",
        "ask_month_plan",
    } or any(keyword in message for keyword in os_keywords)


def _format_os_reply(
    ctx: dict,
    diagnosis: dict,
    goal_status: dict,
    business_os_state: dict,
    fallback_action: str,
) -> str:
    store_name = ctx["store_name"]
    health_score = business_os_state.get("business_health_score", "-")
    today_action = business_os_state.get("today_action") or diagnosis.get("recommended_fix") or fallback_action
    weekly_focus = business_os_state.get("weekly_focus") or "สลับคอนเทนต์ให้ครบความรู้ รีวิว เบื้องหลัง และข้อเสนอ"
    current_risk = business_os_state.get("current_risk") or diagnosis.get("likely_problem") or "ยังไม่มีข้อมูลพอ"
    opportunity = business_os_state.get("growth_opportunity") or ctx["next_angle"]

    direct_answer = (
        f"ตอนนี้ {store_name} ควรโฟกัสที่: {today_action}\n\n"
        f"คะแนนสุขภาพธุรกิจ: {health_score}%\n"
        f"ความเสี่ยงหลัก: {current_risk}\n"
        f"โอกาสเติบโต: {opportunity}\n"
        f"เป้าหมายสัปดาห์นี้: {weekly_focus}"
    )

    evidence = diagnosis.get("evidence") or [ctx["history_text"]]
    why_lines = [
        diagnosis.get("root_cause") or ctx["recommendation"],
        "หลักฐาน: " + " | ".join(evidence[:3]),
    ]
    if goal_status:
        why_lines.append(
            f"เป้าหมาย {goal_status['goal_label']} อยู่ที่ {goal_status['progress_pct']}% "
            f"ยังขาด {goal_status['gap_to_goal']:g}"
        )

    actions = diagnosis.get("next_3_actions") or [today_action, fallback_action]
    if goal_status and goal_status.get("recommended_actions"):
        actions = [goal_status["next_best_action"], *goal_status["recommended_actions"]]
    action_text = "\n".join(
        f"{index}. {action}"
        for index, action in enumerate(actions[:3], start=1)
    )

    return _format_reply(
        direct_answer=direct_answer,
        why="\n".join(why_lines),
        suggested_action=action_text,
        related_module="Business Operating System Dashboard",
    )


def generate_chat_response(
    user_message,
    store_profile,
    business_insight,
    recent_topics,
    chat_history=None,
    diagnosis=None,
    goal_status=None,
    business_os_state=None,
):
    """Return local Thai business-coach advice for SME store owners."""
    profile = store_profile or {}
    insight = business_insight or {}
    topics = recent_topics or []
    intent_analysis = analyze_chat_intent(user_message, profile, insight, topics)
    ctx = _context(profile, insight, topics)
    message = _clean(user_message).lower()

    direct_answer, why = _intent_answer(intent_analysis["intent"], ctx)
    if _needs_os_answer(message, intent_analysis["intent"]) and (diagnosis or business_os_state or goal_status):
        reply = _format_os_reply(
            ctx=ctx,
            diagnosis=diagnosis or {},
            goal_status=goal_status or {},
            business_os_state=business_os_state or {},
            fallback_action=intent_analysis["suggested_action"],
        )
        related_feature = "Business Operating System Dashboard"
    else:
        reply = _format_reply(
            direct_answer=direct_answer,
            why=why,
            suggested_action=intent_analysis["suggested_action"],
            related_module=intent_analysis["related_module"],
        )
        related_feature = intent_analysis["related_module"]

    return {
        "reply": reply,
        "suggested_action": intent_analysis["suggested_action"],
        "related_feature": related_feature,
        "intent": intent_analysis["intent"],
        "confidence": intent_analysis["confidence"],
        "reasoning": intent_analysis["reasoning"],
        "related_module": related_feature,
    }
