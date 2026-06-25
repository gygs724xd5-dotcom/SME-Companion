from collections import Counter


CONTENT_TYPE_LABELS = {
    "customer review": "รีวิวลูกค้า",
    "behind the scenes": "เบื้องหลังการทำงาน",
    "promotion": "โปรโมชั่น",
    "product education": "ความรู้สินค้า",
    "social proof": "หลักฐานความน่าเชื่อถือ",
    "urgency campaign": "แคมเปญเร่งตัดสินใจ",
}

PROMOTION_WORDS = ("โปร", "promotion", "offer", "discount", "ส่วนลด", "ข้อเสนอ")


def _clean(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _content_type_label(content_type: str) -> str:
    return CONTENT_TYPE_LABELS.get(content_type, content_type)


def _count_promotion_signals(recent_topics: list[str], promotion: dict) -> int:
    topic_text = " ".join(recent_topics or []).lower()
    promotion_text = " ".join(
        [
            _clean(promotion.get("promotion_name")),
            _clean(promotion.get("promotion_mechanic")),
            _clean(promotion.get("why_it_works")),
        ]
    ).lower()
    return sum(1 for word in PROMOTION_WORDS if word in topic_text) + (
        1 if any(word in promotion_text for word in PROMOTION_WORDS) else 0
    )


def _repeated_topics(recent_topics: list[str]) -> list[str]:
    normalized_topics = [
        topic.strip() for topic in recent_topics or [] if topic and topic.strip()
    ]
    counts = Counter(normalized_topics)
    return [topic for topic, count in counts.items() if count > 1]


def _confidence(history_size: int, issue_count: int) -> int:
    base = 64 + min(history_size, 5) * 5
    if issue_count == 0:
        base += 8
    else:
        base -= min(issue_count, 3) * 3
    return max(55, min(92, base))


def generate_sme_companion(
    store_profile,
    strategy,
    sales_strategy,
    promotion,
    business_insight,
    recent_topics,
):
    """Generate deterministic Thai companion advice from local SME signals."""
    profile = store_profile or {}
    strategy = strategy or {}
    sales_strategy = sales_strategy or {}
    promotion = promotion or {}
    business_insight = business_insight or {}
    recent_topics = recent_topics or []

    store_name = _clean(profile.get("store_name"), "ร้านของคุณ")
    product = _clean(profile.get("product"), "สินค้า")
    target_customer = _clean(profile.get("target_customer"), "ลูกค้า")

    missing_types = business_insight.get("missing_content_types") or []
    repeated_topics = _repeated_topics(recent_topics)
    repeated_warning = _clean(business_insight.get("repeated_topic_warning"))
    promotion_signal_count = _count_promotion_signals(recent_topics, promotion)
    total_content = int(business_insight.get("total_generated_content") or len(recent_topics))

    has_repeated_warning = repeated_topics or (
        repeated_warning and "ยังไม่พบ" not in repeated_warning
    )
    too_many_promotions = promotion_signal_count >= 2 or (
        total_content >= 3 and "promotion" not in missing_types and len(missing_types) >= 3
    )

    if too_many_promotions:
        companion_message = (
            "ช่วงนี้ร้านของคุณใช้โปรโมชั่นบ่อยพอสมควร\n"
            "ลูกค้าอาจเริ่มรอช่วงลดราคา\n"
            "ลองเพิ่มคอนเทนต์รีวิวลูกค้าเพื่อสร้างความน่าเชื่อถือ"
        )
        priority_action = f"ทำโพสต์รีวิวหรือคำถามลูกค้าเกี่ยวกับ {product} ก่อนปล่อยโปรรอบถัดไป"
        warning = "อย่าให้ข้อเสนอพิเศษกลายเป็นเหตุผลเดียวที่ลูกค้าตัดสินใจซื้อ"
        opportunity = f"ใช้เสียงจากลูกค้าจริงช่วยให้{target_customer}มั่นใจและซื้อได้ง่ายขึ้น"
        issue_count = 2
    elif missing_types:
        missing_label = _content_type_label(missing_types[0])
        if missing_types[0] == "behind the scenes":
            companion_message = (
                "ร้านของคุณยังไม่เคยทำคอนเทนต์เบื้องหลังการทำงาน\n"
                "ลองพาผู้ติดตามดูขั้นตอนการเตรียมสินค้า"
            )
        else:
            companion_message = (
                f"ร้านของคุณยังขาดคอนเทนต์ประเภท{missing_label}\n"
                f"สัปดาห์นี้ควรเติมมุมนี้เพื่อให้ลูกค้าเข้าใจ {product} รอบด้านขึ้น"
            )
        priority_action = _clean(
            business_insight.get("next_best_content_angle"),
            f"สร้างคอนเทนต์{missing_label}สำหรับ {product}",
        )
        warning = "ถ้าคอนเทนต์มีมุมเดียวต่อเนื่อง ลูกค้าใหม่อาจยังไม่มั่นใจพอที่จะทักซื้อ"
        opportunity = f"เติมคอนเทนต์{missing_label}เพื่อสร้างเหตุผลซื้อใหม่ให้{target_customer}"
        issue_count = 1
    elif has_repeated_warning:
        topic_text = ", ".join(repeated_topics[:2]) if repeated_topics else "หัวข้อเดิม"
        companion_message = (
            f"คอนเทนต์ของ {store_name} เริ่มมีหัวข้อที่ใช้ซ้ำ\n"
            f"ลองเปลี่ยนจาก {topic_text} ไปเล่ามุมประโยชน์ รีวิว หรือเบื้องหลัง"
        )
        priority_action = f"เลือกหัวข้อใหม่ที่ยังไม่ซ้ำ และผูกกับเหตุผลซื้อของ {product}"
        warning = "หัวข้อซ้ำบ่อยอาจทำให้ผู้ติดตามเลื่อนผ่านเพราะรู้สึกว่าเห็นแล้ว"
        opportunity = _clean(
            strategy.get("sales_angle"),
            f"ใช้มุมใหม่ทำให้ {product} ถูกเห็นในสถานการณ์การใช้งานที่ต่างออกไป",
        )
        issue_count = 1
    else:
        companion_message = (
            "ทิศทางคอนเทนต์ของร้านเริ่มสมดุลแล้ว\n"
            "สัปดาห์นี้ควรเน้นการปิดการขายจากสินค้าที่ได้รับความสนใจสูง"
        )
        priority_action = _clean(
            sales_strategy.get("recommended_action"),
            f"ทำคอนเทนต์ปิดการขายสำหรับ {product} พร้อมคำสั่งซื้อที่ชัดเจน",
        )
        warning = "ยังควรวัดผลจากยอดทักแชท ออร์เดอร์ และหัวข้อที่ลูกค้าตอบสนองจริง"
        opportunity = _clean(
            business_insight.get("business_recommendation"),
            f"ต่อยอดคอนเทนต์ที่ทำงานดีให้กลายเป็นแคมเปญขายสำหรับ{target_customer}",
        )
        issue_count = 0

    return {
        "companion_message": companion_message,
        "confidence": _confidence(total_content, issue_count),
        "priority_action": priority_action,
        "warning": warning,
        "opportunity": opportunity,
    }
