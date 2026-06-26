from brain.chat_intelligence_engine import analyze_chat_intent
from brain.conversation_intent_engine import (
    FOLLOW_UP,
    GENERAL_CHAT,
    GREETING,
    OTHER,
    START_BUSINESS,
    detect_conversation_intent,
    get_conversation_mode,
    should_show_business_insights,
)
from brain.response_cleaner import clean_response, localize_internal_labels
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


def _format_reply(
    direct_answer: str,
    why: str,
    suggested_action: str,
    related_module: str,
    include_feature_block: bool = True,
) -> str:
    reply = (
        f"{direct_answer}\n\n"
        f"ทำไม:\n{why}\n\n"
        f"แนะนำ:\n{suggested_action}"
    )
    if include_feature_block:
        reply = f"{reply}\n\nฟีเจอร์ที่เกี่ยวข้อง:\n{related_module}"
    return localize_internal_labels(reply)


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


def _startup_advisor_reply(user_message: str) -> str:
    product_hint = "ธุรกิจ"
    message = _clean(user_message)
    for marker in ["เปิดร้าน", "เริ่มร้าน", "เริ่มธุรกิจ", "จะขาย", "อยากขาย", "เริ่มขาย"]:
        if marker in message:
            product_hint = message.split(marker, 1)[-1].strip() or product_hint
            break
    for phrase in ["ต้องเริ่มยังไง", "เริ่มยังไง", "ยังไง", "อย่างไร", "ดีไหม", "ดีมั้ย"]:
        product_hint = product_hint.replace(phrase, "").strip()
    product_hint = product_hint or "ธุรกิจ"

    return (
        f"ถ้าจะเริ่ม{product_hint} ให้เริ่มจาก 5 เรื่องนี้ก่อนครับ:\n"
        "1. เลือกกลุ่มลูกค้าที่ชัดเจน\n"
        "2. เลือกแนวสินค้าหรือบริการที่จะแก้ปัญหาเขา\n"
        "3. คำนวณต้นทุน ราคาขาย และกำไรต่อชิ้น\n"
        "4. เตรียมช่องทางขายหลัก เช่น หน้าร้าน เพจ หรือไลน์\n"
        "5. ทดลองขายล็อตเล็กก่อน แล้วดูว่าลูกค้าถามหรือซื้อเพราะอะไร\n\n"
        "ตอนนี้คุณอยากขายแนวไหนครับ?"
    )


def _casual_reply(intent: str) -> str:
    if intent == GREETING:
        return "สวัสดีครับ ผมช่วยคิดเรื่องร้าน การขาย คอนเทนต์ หรือการเริ่มธุรกิจได้ครับ\nวันนี้อยากให้ช่วยเรื่องไหน?"
    if intent == FOLLOW_UP:
        return "ขอโทษครับ ผมอาจตีความผิด\nคุณหมายถึงเรื่องไหนครับ?"
    return "ได้ครับ เล่าเพิ่มอีกนิดว่าต้องการให้ช่วยเรื่องอะไร\nถ้าเป็นเรื่องร้าน ผมจะช่วยคิดให้เป็นขั้นตอนสั้นๆ ครับ"


def _mobile_lines(lines: list[str], limit: int = 8) -> str:
    clean_lines = [str(line or "").strip() for line in lines if str(line or "").strip()]
    return "\n".join(clean_lines[:limit])


def _first_action_line(text: str, fallback: str) -> str:
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.lstrip("-*• ").strip()
        if len(line) > 3 and line[0].isdigit() and line[1:2] in {".", ")"}:
            line = line[2:].strip()
        if line:
            return line
    return fallback


def _format_reply(
    direct_answer: str,
    why: str,
    suggested_action: str,
    related_module: str,
    include_feature_block: bool = True,
) -> str:
    action = _first_action_line(suggested_action, direct_answer)
    lines = [
        direct_answer,
        why,
        f"ถ้าต้องเลือกทำอย่างเดียววันนี้ ผมแนะนำให้{action}ครับ",
    ]
    if include_feature_block:
        lines.append(f"ดูภาพรวมประกอบได้จาก {localize_internal_labels(related_module)}")
    return localize_internal_labels(_mobile_lines(lines))


def _format_os_reply(
    ctx: dict,
    diagnosis: dict,
    goal_status: dict,
    business_os_state: dict,
    fallback_action: str,
) -> str:
    store_name = ctx["store_name"]
    today_action = business_os_state.get("today_action") or diagnosis.get("recommended_fix") or fallback_action
    current_risk = business_os_state.get("current_risk") or diagnosis.get("likely_problem") or ""
    opportunity = business_os_state.get("growth_opportunity") or ctx["next_angle"]
    root_cause = diagnosis.get("root_cause") or ctx["recommendation"]

    lines = [
        f"ตอนนี้ {store_name} ควรโฟกัสเรื่องนี้ก่อนครับ: {today_action}",
        root_cause,
    ]
    if current_risk:
        lines.append(f"จุดที่ควรระวังคือ {current_risk}")
    lines.extend(
        [
            f"โอกาสที่น่าลองต่อคือ {opportunity}",
            f"วันนี้เริ่มจาก {today_action} ก่อนครับ",
        ]
    )
    return localize_internal_labels(_mobile_lines(lines))


def _startup_advisor_reply(user_message: str) -> str:
    product_hint = "ธุรกิจนี้"
    message = _clean(user_message)
    for marker in ["เปิดร้าน", "เริ่มร้าน", "เริ่มธุรกิจ", "จะขาย", "อยากขาย", "เริ่มขาย"]:
        if marker in message:
            product_hint = message.split(marker, 1)[-1].strip() or product_hint
            break
    for phrase in ["ต้องเริ่มยังไง", "เริ่มยังไง", "ยังไง", "อย่างไร", "ดีไหม", "ดีมั้ย", "?"]:
        product_hint = product_hint.replace(phrase, "").strip()
    if "ไม่ใช่" in product_hint:
        product_hint = product_hint.split("ไม่ใช่", 1)[0].strip()
    product_hint = product_hint or "ธุรกิจนี้"

    return _mobile_lines(
        [
            f"ถ้าจะเริ่ม{product_hint} ผมแนะนำให้เริ่มเล็กก่อนครับ",
            "อย่าเพิ่งรีบทำครบทุกอย่างตั้งแต่วันแรก",
            "ให้ชัดก่อนว่าใครคือลูกค้าหลัก และเขาซื้อเพราะปัญหาอะไร",
            "จากนั้นคำนวณต้นทุน ราคาขาย และกำไรต่อชิ้นให้เห็นตัวเลขจริง",
            "ลองขายล็อตเล็กก่อน เพื่อดูว่าลูกค้าถามอะไรและตัดสินใจตรงไหน",
            "ตอนนี้คุณจะเริ่มขายออนไลน์หรือมีหน้าร้านก่อนครับ?",
        ]
    )


def _casual_reply(intent: str) -> str:
    if intent == GREETING:
        return _mobile_lines(
            [
                "สวัสดีครับ ผมช่วยคิดเรื่องร้าน การขาย คอนเทนต์ หรือการเริ่มธุรกิจได้ครับ",
                "วันนี้อยากให้ช่วยเรื่องไหนครับ?",
            ]
        )
    if intent == FOLLOW_UP:
        return _mobile_lines(
            [
                "ขอโทษครับ ผมน่าจะจับประเด็นไม่ตรง",
                "คุณหมายถึงเรื่องไหนครับ?",
            ]
        )
    return _mobile_lines(
        [
            "ได้ครับ เล่าเพิ่มอีกนิดว่าต้องการให้ช่วยเรื่องอะไร",
            "ผมจะช่วยจัดเป็นขั้นตอนสั้นๆ ให้ครับ",
        ]
    )


def _thai_business_intent(user_message: str, broad_intent: str) -> str:
    message = _clean(user_message).lower()
    if any(word in message for word in ["โพสต์", "คอนเทนต์", "ลงอะไร"]):
        return "ask_daily_post"
    if any(word in message for word in ["แคปชั่น", "caption"]):
        return "ask_caption"
    if any(word in message for word in ["รูป", "ถ่ายรูป", "ภาพ"]):
        return "ask_photo_idea"
    if any(word in message for word in ["วิดีโอ", "คลิป", "reels", "รีล", "tiktok"]):
        return "ask_video_idea"
    if any(word in message for word in ["โปร", "โปรโมชั่น", "โปรโมชัน", "ส่วนลด", "แคมเปญ"]):
        return "ask_promotion"
    if any(word in message for word in ["ยอดตก", "ขายตก", "เงียบ", "ไม่มีออเดอร์"]):
        return "ask_sales_drop"
    if any(word in message for word in ["เพิ่มยอด", "ขายดี", "ปิดการขาย"]):
        return "ask_sales_growth"
    if any(word in message for word in ["ลูกค้าใหม่", "หาลูกค้า"]):
        return "ask_new_customer"
    if any(word in message for word in ["ซื้อซ้ำ", "ลูกค้าเก่า", "กลับมาซื้อ", "รักษาลูกค้า"]):
        return "ask_repeat_customer"
    if any(word in message for word in ["รีวิว", "น่าเชื่อถือ", "ไว้ใจ", "มั่นใจ"]):
        return "ask_customer_trust"
    if any(word in message for word in ["สัปดาห์", "7 วัน"]):
        return "ask_week_plan"
    if any(word in message for word in ["เดือน", "เป้าหมาย"]):
        return "ask_month_plan"
    if any(word in message for word in ["คู่แข่ง", "ร้านอื่น"]):
        return "ask_competitor"
    if broad_intent == CONTENT:
        return "ask_content_idea"
    if broad_intent == MARKETING:
        return "ask_promotion"
    if broad_intent == SALES:
        return "ask_sales_growth"
    if broad_intent == CUSTOMER_RETENTION:
        return "ask_repeat_customer"
    return "ask_business_problem"


def _thai_suggested_action(intent: str) -> str:
    actions = {
        "ask_daily_post": "โพสต์รีวิวลูกค้าหรือผลลัพธ์จริง 1 ชิ้น",
        "ask_content_idea": "เลือกมุมคอนเทนต์ใหม่ที่ไม่ซ้ำกับโพสต์ล่าสุด",
        "ask_caption": "เขียนแคปชั่นที่เริ่มจากปัญหาลูกค้า แล้วปิดด้วยคำชวนทัก",
        "ask_photo_idea": "ถ่ายภาพที่เห็นสินค้าในการใช้งานจริง",
        "ask_video_idea": "ทำคลิปสั้นแบบปัญหา วิธีแก้ และชวนทักแชท",
        "ask_promotion": "ทำโปรที่มีเหตุผลซื้อชัด ไม่ลดราคาจนเสียคุณค่า",
        "ask_sales_drop": "ทำโพสต์สร้างความน่าเชื่อถือ 1 ชิ้น",
        "ask_sales_growth": "ดันสินค้าหลักด้วยข้อเสนอที่ตัดสินใจง่าย",
        "ask_new_customer": "ทำคอนเทนต์ลดความเสี่ยงสำหรับลูกค้าใหม่",
        "ask_repeat_customer": "ทำข้อเสนอเฉพาะลูกค้าเก่า",
        "ask_customer_trust": "โพสต์รีวิวลูกค้าจริงหรือเบื้องหลังร้าน",
        "ask_week_plan": "วางแผน 7 วันให้สลับรีวิว ความรู้ เบื้องหลัง และโปร",
        "ask_month_plan": "แบ่งเดือนนี้เป็นรู้จักร้าน เชื่อมั่น กระตุ้นซื้อ และซื้อซ้ำ",
        "ask_competitor": "เล่าจุดต่างของร้านโดยไม่โจมตีคู่แข่ง",
    }
    return actions.get(intent, "เริ่มจากแยกปัญหาว่าอยู่ที่คนเห็นน้อย ความเชื่อมั่น ข้อเสนอ หรือการปิดการขาย")


def _intent_answer(intent: str, ctx: dict) -> tuple[str, str]:
    product = ctx["product"]
    target_customer = ctx["target_customer"]
    store_name = ctx["store_name"]
    store_type = ctx["store_type"]
    next_angle = ctx["next_angle"]

    answers = {
        "ask_daily_post": (
            f"วันนี้ผมแนะนำให้ {store_name} โพสต์มุมที่ช่วยให้{target_customer}ตัดสินใจง่ายขึ้นครับ",
            f"มุมที่เหมาะตอนนี้คือ {next_angle}",
        ),
        "ask_content_idea": (
            f"สำหรับ{store_type} ให้สลับ 3 มุมนี้ครับ: ประโยชน์สินค้า รีวิวลูกค้า และเบื้องหลังร้าน",
            f"อย่าโพสต์ขายตรงซ้ำๆ เพราะลูกค้าจะเลื่อนผ่านเร็ว",
        ),
        "ask_caption": (
            f"แคปชั่นควรเริ่มจากปัญหาของ{target_customer} แล้วค่อยพาไปที่คุณค่าของ {product}",
            "ปิดท้ายด้วยคำชวนทักที่ชัด เช่น ทักแชทเพื่อดูราคา หรือจองวันนี้",
        ),
        "ask_photo_idea": (
            f"ภาพที่ควรถ่ายคือภาพ {product} ตอนใช้งานจริงครับ",
            "ภาพแบบนี้ช่วยให้ลูกค้านึกออกว่าเขาจะได้ประโยชน์อะไร",
        ),
        "ask_video_idea": (
            f"ทำคลิปสั้น 3 ช่วงครับ: ปัญหาลูกค้า วิธีที่ {product} ช่วย และคำชวนทัก",
            "คลิปไม่ต้องยาว แต่ต้องเห็นเหตุผลซื้อใน 3 วินาทีแรก",
        ),
        "ask_promotion": (
            f"โปรที่เหมาะกับ{store_type}ควรทำให้ลูกค้าตัดสินใจง่าย ไม่ใช่ลดราคาอย่างเดียว",
            "ลองใช้เซตแนะนำ ของแถม หรือโปรสำหรับลูกค้าใหม่ก่อนครับ",
        ),
        "ask_sales_drop": (
            "ยอดตกมักเริ่มจากคนเห็นน้อยลง ความน่าเชื่อถือลด หรือข้อเสนอไม่น่าตัดสินใจพอ",
            "ให้เริ่มจากโพสต์รีวิวจริงก่อน เพราะช่วยลดความลังเลได้เร็ว",
        ),
        "ask_sales_growth": (
            f"ถ้าอยากเพิ่มยอด ให้เลือกดัน {product} ด้วยข้อเสนอที่เข้าใจง่ายครับ",
            "ลูกค้าควรเห็นความคุ้ม รีวิว และวิธีสั่งในโพสต์เดียว",
        ),
        "ask_new_customer": (
            "ลูกค้าใหม่ยังไม่เชื่อร้าน จึงต้องเห็นหลักฐานก่อนซื้อครับ",
            "เริ่มจากรีวิว วิธีสั่งที่ชัด และข้อเสนอแรกซื้อที่ไม่เสี่ยง",
        ),
        "ask_repeat_customer": (
            "ลูกค้าเก่าต้องมีเหตุผลใหม่ให้กลับมาครับ",
            "ใช้สิทธิพิเศษ เซตคุ้มกว่าเดิม หรือแจ้งสินค้าใหม่ให้เขาก่อน",
        ),
        "ask_customer_trust": (
            "ถ้าลูกค้ายังไม่มั่นใจ ให้เพิ่มหลักฐานจากคนจริงครับ",
            "รีวิว เบื้องหลังร้าน และวิธีสั่งที่ชัดช่วยได้มาก",
        ),
        "ask_week_plan": (
            "สัปดาห์นี้ควรวางคอนเทนต์ให้ครบทั้งรู้จักร้าน เชื่อมั่น และตัดสินใจซื้อครับ",
            "อย่าให้ทั้งสัปดาห์เป็นโพสต์ขายแบบเดียวกัน",
        ),
        "ask_month_plan": (
            "แผนเดือนนี้ควรแบ่งเป็น 4 ช่วง: รู้จักร้าน เชื่อมั่น กระตุ้นซื้อ และดึงลูกค้าเก่ากลับมา",
            "แบบนี้จะไม่กดขายซ้ำทุกวัน และยังพาลูกค้าไปถึงการซื้อได้",
        ),
        "ask_competitor": (
            "อย่าเริ่มจากแข่งราคา ให้เริ่มจากจุดต่างของร้านก่อนครับ",
            f"เล่าให้ชัดว่า {product} เหมาะกับ{target_customer}ตรงไหนมากกว่าตัวเลือกทั่วไป",
        ),
    }
    return answers.get(
        intent,
        (
            f"ตอนนี้คำแนะนำของผมคือมองปัญหา {store_name} ให้เป็น 4 จุดก่อนครับ",
            "คนเห็นน้อย ความเชื่อมั่น ข้อเสนอ และการปิดการขาย จุดไหนตัน ให้แก้จุดนั้นก่อน",
        ),
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
    conversation_intent=None,
    conversation_mode=None,
    show_business_insights=None,
):
    """Return local Thai business-coach advice for SME store owners."""
    profile = store_profile or {}
    insight = business_insight or {}
    topics = recent_topics or []
    broad_intent = conversation_intent or detect_conversation_intent(user_message)
    mode = conversation_mode or get_conversation_mode(broad_intent)

    if broad_intent == START_BUSINESS:
        reply = clean_response(_startup_advisor_reply(user_message))
        return {
            "reply": reply,
            "suggested_action": None,
            "related_feature": None,
            "intent": broad_intent,
            "conversation_mode": mode,
            "confidence": 0.9,
            "reasoning": "startup advisor mode without current store context",
            "related_module": None,
        }

    if broad_intent in {GREETING, GENERAL_CHAT, FOLLOW_UP, OTHER}:
        reply = clean_response(_casual_reply(broad_intent))
        return {
            "reply": reply,
            "suggested_action": None,
            "related_feature": None,
            "intent": broad_intent,
            "conversation_mode": mode,
            "confidence": 0.85,
            "reasoning": "casual conversation without current store context",
            "related_module": None,
        }

    intent_analysis = analyze_chat_intent(user_message, profile, insight, topics)
    thai_intent = _thai_business_intent(user_message, broad_intent)
    intent_analysis = {
        **intent_analysis,
        "intent": thai_intent,
        "suggested_action": _thai_suggested_action(thai_intent),
        "related_module": intent_analysis.get("related_module") or "SME Companion",
        "confidence": max(float(intent_analysis.get("confidence") or 0), 0.75),
    }
    ctx = _context(profile, insight, topics)
    message = _clean(user_message).lower()
    show_os = should_show_business_insights(broad_intent, user_message) if show_business_insights is None else show_business_insights

    direct_answer, why = _intent_answer(intent_analysis["intent"], ctx)
    if show_os and _needs_os_answer(message, intent_analysis["intent"]) and (diagnosis or business_os_state or goal_status):
        reply = _format_os_reply(
            ctx=ctx,
            diagnosis=diagnosis or {},
            goal_status=goal_status or {},
            business_os_state=business_os_state or {},
            fallback_action=intent_analysis["suggested_action"],
        )
        related_feature = "แผนงานธุรกิจ"
    else:
        reply = _format_reply(
            direct_answer=direct_answer,
            why=why,
            suggested_action=intent_analysis["suggested_action"],
            related_module=intent_analysis["related_module"],
            include_feature_block=show_os,
        )
        related_feature = localize_internal_labels(intent_analysis["related_module"]) if show_os else None

    return {
        "reply": clean_response(reply),
        "suggested_action": intent_analysis["suggested_action"],
        "related_feature": related_feature,
        "intent": broad_intent,
        "business_intent": intent_analysis["intent"],
        "conversation_mode": mode,
        "confidence": intent_analysis["confidence"],
        "reasoning": intent_analysis["reasoning"],
        "related_module": related_feature,
    }
