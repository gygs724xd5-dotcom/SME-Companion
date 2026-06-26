from knowledge.knowledge_router import get_playbook


CONTENT_INTENTS = {
    "ask_daily_post": {
        "keywords": ["โพสต์วันนี้", "โพสต์อะไร", "ควรโพสต์", "คอนเทนต์วันนี้", "ลงอะไรดี", "วันนี้ลง", "today", "daily post"],
        "suggested_action": "สร้างคอนเทนต์วันนี้จากมุมที่เหมาะกับร้าน",
        "related_module": "Daily Content",
    },
    "ask_content_idea": {
        "keywords": ["ไอเดียคอนเทนต์", "คิดคอนเทนต์", "ทำคอนเทนต์อะไร", "content idea", "idea"],
        "suggested_action": "ใช้มุมคอนเทนต์ใหม่ที่ไม่ซ้ำกับหัวข้อล่าสุด",
        "related_module": "Daily Content",
    },
    "ask_photo_idea": {
        "keywords": ["ไอเดียรูป", "ถ่ายรูป", "รูปสินค้า", "ภาพสินค้า", "photo idea", "ถ่ายอะไร"],
        "suggested_action": "ถ่ายภาพที่โชว์การใช้จริงหรือความน่าเชื่อถือของสินค้า",
        "related_module": "Daily Content",
    },
    "ask_video_idea": {
        "keywords": ["ไอเดียวิดีโอ", "ทำวิดีโอ", "คลิป", "video idea", "วิดีโอ"],
        "suggested_action": "ทำคลิปสั้นที่เริ่มจากปัญหาลูกค้าแล้วจบด้วยสินค้า",
        "related_module": "Daily Content",
    },
    "ask_reels_idea": {
        "keywords": ["reels", "รีล", "รีลส์", "ไอเดีย reels", "instagram"],
        "suggested_action": "ทำ Reels สั้น 10-20 วินาทีที่มี hook ชัดใน 3 วินาทีแรก",
        "related_module": "Daily Content",
    },
    "ask_tiktok_idea": {
        "keywords": ["tiktok", "ติ๊กต็อก", "ติ๊กต๊อก", "ไอเดีย tiktok"],
        "suggested_action": "ทำ TikTok แบบปัญหา-วิธีแก้-ชวนทักแชท",
        "related_module": "Daily Content",
    },
    "ask_caption": {
        "keywords": ["แคปชั่น", "caption", "เขียนโพสต์", "ข้อความโพสต์", "คำโปรย"],
        "suggested_action": "เขียนแคปชั่นที่มี hook เหตุผลซื้อ และคำชวนทักแชท",
        "related_module": "Daily Content",
    },
}

SALES_INTENTS = {
    "ask_sales_drop": {
        "keywords": ["ยอดตก", "ขายตก", "ยอดขายลด", "ยอดขายตก", "เงียบ", "ไม่มีออเดอร์", "sales drop"],
        "suggested_action": "ตรวจ Business Insight แล้วทำโพสต์สร้างความน่าเชื่อถือ 1 ชิ้น",
        "related_module": "Business Insight Dashboard",
    },
    "ask_sales_growth": {
        "keywords": ["เพิ่มยอดขาย", "ยอดขายเพิ่ม", "ขายดีขึ้น", "อยากขายดี", "sales growth", "boost sales"],
        "suggested_action": "สร้างแคมเปญเพิ่มยอดขายจาก Revenue Engine",
        "related_module": "Revenue Engine",
    },
    "ask_promotion": {
        "keywords": ["โปร", "โปรโมชั่น", "ส่วนลด", "ข้อเสนอ", "offer", "promotion", "discount"],
        "suggested_action": "ทำโปรที่มีเหตุผลซื้อชัดและไม่ลดราคาจนกลบคุณค่าสินค้า",
        "related_module": "Revenue Engine",
    },
    "ask_product_focus": {
        "keywords": ["ดันสินค้า", "ขายตัวไหนดี", "สินค้าไหน", "โฟกัสสินค้า", "product focus"],
        "suggested_action": "เลือกสินค้าที่อธิบายคุณค่าได้ชัดและทำคอนเทนต์ต่อเนื่อง",
        "related_module": "Revenue Engine",
    },
    "ask_price": {
        "keywords": ["ตั้งราคา", "ราคา", "แพงไปไหม", "ขายเท่าไหร่", "price", "pricing"],
        "suggested_action": "สื่อสารราคาโดยเทียบกับคุณค่า รีวิว และผลลัพธ์ที่ลูกค้าได้รับ",
        "related_module": "Revenue Engine",
    },
}

CUSTOMER_INTENTS = {
    "ask_new_customer": {
        "keywords": ["ลูกค้าใหม่", "หาลูกค้า", "คนยังไม่รู้จัก", "new customer"],
        "suggested_action": "ทำคอนเทนต์ลดความเสี่ยงครั้งแรก เช่น รีวิว วิธีสั่ง และโปรลูกค้าใหม่",
        "related_module": "Revenue Engine",
    },
    "ask_repeat_customer": {
        "keywords": ["ซื้อซ้ำ", "ลูกค้าซื้อซ้ำ", "กลับมาซื้อ", "repeat customer"],
        "suggested_action": "ทำข้อเสนอเฉพาะลูกค้าเก่าหรือเซตแนะนำสำหรับการซื้อซ้ำ",
        "related_module": "Revenue Engine",
    },
    "ask_customer_retention": {
        "keywords": ["รักษาลูกค้า", "ลูกค้าเก่า", "ไม่ให้ลูกค้าหาย", "retention"],
        "suggested_action": "สื่อสารกับลูกค้าเก่าด้วยสิทธิพิเศษและคอนเทนต์ที่ทำให้รู้สึกว่าร้านจำเขาได้",
        "related_module": "Revenue Engine",
    },
    "ask_customer_trust": {
        "keywords": ["ความน่าเชื่อถือ", "ลูกค้าไม่มั่นใจ", "ไว้ใจ", "น่าเชื่อถือ", "trust", "รีวิว"],
        "suggested_action": "สร้างรีวิวลูกค้า เบื้องหลังร้าน หรือหลักฐานการขายจริง",
        "related_module": "Business Insight Dashboard",
    },
}

PLANNING_INTENTS = {
    "ask_calendar": {
        "keywords": ["ปฏิทิน", "ตารางคอนเทนต์", "แผน 7 วัน", "calendar"],
        "suggested_action": "สร้างแผนคอนเทนต์ 7 วันเพื่อสลับมุมขายและมุมสร้างความเชื่อมั่น",
        "related_module": "แผนคอนเทนต์ 7 วัน",
    },
    "ask_week_plan": {
        "keywords": ["แผนสัปดาห์", "วางแผนสัปดาห์", "สัปดาห์นี้", "week plan", "weekly plan"],
        "suggested_action": "วางแผน 7 วันโดยสลับรีวิว ประโยชน์สินค้า เบื้องหลัง และโปร",
        "related_module": "แผนคอนเทนต์ 7 วัน",
    },
    "ask_month_plan": {
        "keywords": ["แผนเดือน", "เดือนนี้", "เดือนนี้ต้องทำอะไร", "ทั้งเดือน", "month plan", "monthly plan", "เป้าหมาย"],
        "suggested_action": "แบ่งเดือนเป็น 4 ธีม: รู้จักร้าน เชื่อมั่นสินค้า กระตุ้นซื้อ และซื้อซ้ำ",
        "related_module": "แผนคอนเทนต์ 7 วัน",
    },
}

BUSINESS_INTENTS = {
    "ask_competitor": {
        "keywords": ["คู่แข่ง", "แข่งกับร้านอื่น", "ร้านอื่น", "competitor"],
        "suggested_action": "หาจุดต่างของร้านแล้วทำคอนเทนต์เปรียบเทียบคุณค่าแบบไม่โจมตีคู่แข่ง",
        "related_module": "Business Insight Dashboard",
    },
    "ask_business_problem": {
        "keywords": ["ปัญหาธุรกิจ", "ร้านมีปัญหา", "ร้านมีปัญหาอะไร", "ติดปัญหา", "แก้ปัญหา", "business problem"],
        "suggested_action": "แยกปัญหาเป็นการมองเห็น ความน่าเชื่อถือ ข้อเสนอ และการปิดการขาย",
        "related_module": "Business Insight Dashboard",
    },
    "ask_business_growth": {
        "keywords": ["โตธุรกิจ", "ขยายร้าน", "ทำให้ร้านโต", "ทำยังไงให้ร้านดีขึ้น", "ร้านดีขึ้น", "business growth", "โตขึ้น"],
        "suggested_action": "สร้างระบบคอนเทนต์และโปรที่ทำซ้ำได้ทุกสัปดาห์",
        "related_module": "SME Companion",
    },
}

INTENT_GROUPS = [
    ("Content", CONTENT_INTENTS),
    ("Sales", SALES_INTENTS),
    ("Customers", CUSTOMER_INTENTS),
    ("Planning", PLANNING_INTENTS),
    ("Business", BUSINESS_INTENTS),
]


def _clean(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _profile_terms(store_profile: dict) -> list[str]:
    terms = []
    for key in ("store_type", "product", "target_customer"):
        value = _clean(store_profile.get(key))
        if value:
            terms.append(value.lower())
    return terms


def _score_intent(message: str, keywords: list[str]) -> tuple[int, list[str]]:
    matched = [keyword for keyword in keywords if keyword.lower() in message]
    return len(matched), matched


def _context_reasoning(
    intent: str,
    store_profile: dict,
    business_insight: dict,
    recent_topics: list[str],
    matched_keywords: list[str],
) -> str:
    product = _clean(store_profile.get("product"), "สินค้า")
    target_customer = _clean(store_profile.get("target_customer"), "ลูกค้า")
    next_angle = _clean(business_insight.get("next_best_content_angle"))
    repeated_warning = _clean(business_insight.get("repeated_topic_warning"))
    missing_types = business_insight.get("missing_content_types") or []

    reasons = []
    if matched_keywords:
        reasons.append("พบคำสำคัญ: " + ", ".join(matched_keywords[:3]))
    if product or target_customer:
        reasons.append(f"บริบทคือขาย {product} ให้{target_customer}")
    if next_angle:
        reasons.append(f"มุมถัดไปที่ระบบแนะนำคือ {next_angle}")
    if repeated_warning:
        reasons.append(repeated_warning)
    if missing_types:
        reasons.append("ยังขาดคอนเทนต์ประเภท " + ", ".join(missing_types[:2]))
    if recent_topics:
        reasons.append("หัวข้อล่าสุดคือ " + ", ".join(recent_topics[:3]))
    if not reasons:
        reasons.append(f"ข้อความใกล้เคียงกับ intent {intent}")

    return " | ".join(reasons)


def _first_playbook_item(playbook: dict, key: str, fallback: str) -> str:
    items = playbook.get(key) or []
    return items[0] if items else fallback


def _knowledge_suggested_action(intent: str, spec: dict, store_type: str) -> str:
    playbook = get_playbook(store_type)

    playbook_actions = {
        "ask_content_idea": ("best_content_types", "ใช้มุมคอนเทนต์ใหม่ที่เหมาะกับประเภทร้าน"),
        "ask_photo_idea": ("photo_ideas", "ถ่ายภาพที่โชว์การใช้จริงหรือความน่าเชื่อถือของสินค้า"),
        "ask_reels_idea": ("reels_ideas", "ทำ Reels สั้นที่เหมาะกับประเภทร้าน"),
        "ask_promotion": ("promotion_ideas", "ทำโปรที่มีเหตุผลซื้อชัดเจน"),
        "ask_customer_trust": ("customer_trust_ideas", "สร้างหลักฐานความน่าเชื่อถือก่อนขาย"),
        "ask_repeat_customer": ("repeat_customer_ideas", "สร้างเหตุผลให้ลูกค้าเก่ากลับมาซื้อซ้ำ"),
        "ask_customer_retention": ("repeat_customer_ideas", "สื่อสารกับลูกค้าเก่าด้วยข้อเสนอเฉพาะกลุ่ม"),
    }

    if intent not in playbook_actions:
        return spec["suggested_action"]

    key, fallback = playbook_actions[intent]
    return _first_playbook_item(playbook, key, fallback)


def analyze_chat_intent(
    user_message,
    store_profile,
    business_insight,
    recent_topics,
):
    """Classify a chat message into a business-coach intent using local context."""
    message = _clean(user_message).lower()
    profile = store_profile or {}
    insight = business_insight or {}
    topics = recent_topics or []

    best_match = None
    for category, intents in INTENT_GROUPS:
        for intent, spec in intents.items():
            score, matched = _score_intent(message, spec["keywords"])
            if score == 0:
                continue

            # A profile term in the message makes the intent more grounded in the store.
            context_bonus = 1 if any(term and term in message for term in _profile_terms(profile)) else 0
            weighted_score = score + context_bonus
            candidate = (weighted_score, score, category, intent, spec, matched)
            if best_match is None or candidate[:2] > best_match[:2]:
                best_match = candidate

    if best_match is None:
        intent = "ask_business_problem"
        category = "Business"
        spec = BUSINESS_INTENTS[intent]
        matched = []
        confidence = 0.35
    else:
        weighted_score, raw_score, category, intent, spec, matched = best_match
        confidence = min(0.95, 0.45 + (raw_score * 0.18) + ((weighted_score - raw_score) * 0.08))

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "reasoning": _context_reasoning(intent, profile, insight, topics, matched),
        "suggested_action": _knowledge_suggested_action(
            intent,
            spec,
            _clean(profile.get("store_type")),
        ),
        "related_module": spec["related_module"],
        "category": category,
    }
