from collections import Counter


PROMOTION_TERMS = {
    "โปร",
    "โปรโมชั่น",
    "ส่วนลด",
    "ลดราคา",
    "แถม",
    "offer",
    "promotion",
    "discount",
}
TRUST_TYPES = {"customer review", "social proof", "behind the scenes"}
RETENTION_TERMS = {
    "ลูกค้าเก่า",
    "ซื้อซ้ำ",
    "กลับมาซื้อ",
    "สมาชิก",
    "repeat",
    "retention",
    "loyalty",
}


def _clean(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _topic_counts(recent_topics: list[str]) -> Counter:
    topics = [_clean(topic).lower() for topic in recent_topics or [] if _clean(topic)]
    return Counter(topics)


def _has_keyword(text_items: list[str], keywords: set[str]) -> bool:
    joined = " ".join(text_items).lower()
    return any(keyword.lower() in joined for keyword in keywords)


def _urgency(problem_count: int, total_content: int, repeated_count: int) -> str:
    if problem_count >= 4 or repeated_count >= 2:
        return "สูง"
    if problem_count >= 2 or total_content < 3:
        return "กลาง"
    return "ต่ำ"


def diagnose_business_status(
    store_profile,
    business_insight,
    recent_topics,
    chat_history=None,
) -> dict:
    """Diagnose likely business bottlenecks from local store and content signals."""
    profile = store_profile or {}
    insight = business_insight or {}
    topics = recent_topics or []
    chat_messages = [
        _clean(item.get("content") if isinstance(item, dict) else item)
        for item in (chat_history or [])
    ]

    store_name = _clean(profile.get("store_name"), "ร้านของคุณ")
    product = _clean(profile.get("product"), "สินค้า")
    target_customer = _clean(profile.get("target_customer"), "ลูกค้า")
    missing_types = insight.get("missing_content_types") or []
    total_content = int(insight.get("total_generated_content") or 0)
    topic_counts = _topic_counts(topics)
    repeated_topics = [topic for topic, count in topic_counts.items() if count > 1]

    topic_text = [_clean(topic) for topic in topics]
    all_text = topic_text + chat_messages
    promotion_count = sum(
        1 for text in all_text if any(term.lower() in text.lower() for term in PROMOTION_TERMS)
    )
    overuse_promotion = bool(all_text) and promotion_count >= max(2, len(all_text) // 2)
    lack_trust = any(content_type in missing_types for content_type in TRUST_TYPES)
    lack_retention = not _has_keyword(all_text, RETENTION_TERMS)
    low_variety = len(set(topic.lower() for topic in topic_text if topic)) < min(3, len(topic_text))

    problems = []
    evidence = []

    if repeated_topics:
        problems.append("หัวข้อคอนเทนต์ซ้ำ")
        evidence.append("พบหัวข้อซ้ำ: " + ", ".join(repeated_topics[:3]))
    if missing_types:
        problems.append("คอนเทนต์บางประเภทหายไป")
        evidence.append("ประเภทที่ยังขาด: " + ", ".join(missing_types[:4]))
    if overuse_promotion:
        problems.append("ใช้มุมขายหรือโปรโมชันมากเกินไป")
        evidence.append(f"พบสัญญาณโปรโมชัน {promotion_count} ครั้งจากบริบทล่าสุด")
    if lack_trust:
        problems.append("ยังสร้างความน่าเชื่อถือไม่พอ")
        evidence.append("ยังขาดรีวิว หลักฐานจากลูกค้า หรือเบื้องหลังร้าน")
    if lack_retention:
        problems.append("ยังไม่มีระบบดึงลูกค้าเก่ากลับมา")
        evidence.append("ยังไม่พบมุมลูกค้าเก่า ซื้อซ้ำ หรือสมาชิกในบริบทล่าสุด")
    if low_variety:
        problems.append("ความหลากหลายคอนเทนต์ต่ำ")
        evidence.append("หัวข้อล่าสุดยังวนอยู่ในมุมใกล้เคียงกัน")

    if not evidence:
        evidence.append("คอนเทนต์ล่าสุดยังไม่พบสัญญาณเสี่ยงชัดเจน")

    if lack_trust:
        likely_problem = "ลูกค้ายังไม่มั่นใจก่อนซื้อ"
        root_cause = f"{target_customer} ยังเห็นหลักฐานไม่พอว่า {product} คุ้มและน่าเชื่อถือ"
        recommended_fix = "เพิ่มรีวิวลูกค้าจริง เบื้องหลังร้าน และวิธีสั่งซื้อให้ชัด ก่อนดันโปรแรง"
    elif overuse_promotion:
        likely_problem = "ลูกค้าจำร้านจากราคา มากกว่าคุณค่า"
        root_cause = "สัดส่วนคอนเทนต์ขายตรงสูง ทำให้เหตุผลซื้อและความต่างของร้านไม่ชัด"
        recommended_fix = "ลดโพสต์โปรลง แล้วสลับคอนเทนต์ความรู้ รีวิว และเบื้องหลัง"
    elif lack_retention:
        likely_problem = "ยอดขายพึ่งลูกค้าใหม่มากเกินไป"
        root_cause = "ยังไม่มีมุมสื่อสารที่ชวนลูกค้าเก่ากลับมาซื้อซ้ำ"
        recommended_fix = "ทำข้อเสนอสำหรับลูกค้าเก่าและโพสต์เตือนประโยชน์ของการซื้อซ้ำ"
    elif repeated_topics or low_variety:
        likely_problem = "ลูกค้าเห็นข้อความเดิมซ้ำจนไม่เกิดเหตุผลซื้อใหม่"
        root_cause = "คอนเทนต์ยังไม่พาลูกค้าไล่จากรู้จัก เชื่อมั่น ตัดสินใจ และซื้อซ้ำ"
        recommended_fix = "วางสัปดาห์ใหม่ด้วย 4 มุม: ความรู้ รีวิว เบื้องหลัง และข้อเสนอ"
    else:
        likely_problem = "ยังต้องสะสมข้อมูลและวัดผลต่อเนื่อง"
        root_cause = "ข้อมูลคอนเทนต์ยังน้อยหรือยังไม่มีจุดเสี่ยงเด่นพอ"
        recommended_fix = "สร้างคอนเทนต์ต่อเนื่องอย่างน้อย 3-5 ชิ้น แล้วดูว่ามุมไหนทำให้ลูกค้าทักมากขึ้น"

    urgency_level = _urgency(len(problems), total_content, len(repeated_topics))
    next_3_actions = [
        f"ทำโพสต์สร้างความเชื่อมั่น 1 ชิ้นให้ {store_name}: รีวิว วิธีใช้ หรือเบื้องหลัง",
        "ทำโพสต์ขายแบบมีเหตุผลซื้อชัด 1 ชิ้น พร้อมคำชวนทักแชท",
        "ทำโพสต์สำหรับลูกค้าเก่า 1 ชิ้น เช่น โปรซื้อซ้ำ เซตแนะนำ หรือสิทธิพิเศษ",
    ]

    return {
        "diagnosis_summary": f"{store_name} มีจุดที่ควรโฟกัสคือ {', '.join(problems[:3]) if problems else 'เพิ่มข้อมูลและทำต่อเนื่อง'}",
        "likely_problem": likely_problem,
        "evidence": evidence,
        "root_cause": root_cause,
        "recommended_fix": recommended_fix,
        "urgency_level": urgency_level,
        "next_3_actions": next_3_actions,
    }
