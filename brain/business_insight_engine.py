from collections import Counter


CONTENT_TYPE_KEYWORDS = {
    "customer review": ["รีวิว", "ลูกค้า", "เรื่องเล่าจากลูกค้า", "social proof"],
    "behind the scenes": ["เบื้องหลัง", "ขั้นตอน", "ใส่ใจ", "หลังร้าน"],
    "promotion": ["โปร", "promotion", "offer", "discount", "ส่วนลด", "ข้อเสนอ"],
    "product education": ["ประโยชน์", "วิธีใช้", "ไอเดียการใช้งาน", "ความรู้", "education"],
    "social proof": ["รีวิว", "ยอดขาย", "ลูกค้าจริง", "บอกต่อ", "proof"],
    "urgency campaign": ["จำกัดเวลา", "วันสุดท้าย", "limited", "urgent", "ด่วน", "หมด"],
}


def _topic_text(item: dict) -> str:
    return " ".join(
        [
            item.get("topic", ""),
            item.get("content_angle", ""),
            item.get("strategy_name", ""),
            item.get("markdown", ""),
        ]
    ).lower()


def _detect_missing_content_types(history: list[dict]) -> list[str]:
    missing = []
    history_text = [_topic_text(item) for item in history]

    for content_type, keywords in CONTENT_TYPE_KEYWORDS.items():
        has_type = any(
            any(keyword.lower() in item_text for keyword in keywords)
            for item_text in history_text
        )
        if not has_type:
            missing.append(content_type)

    return missing


def _next_angle(missing_content_types: list[str], profile: dict) -> str:
    product = profile.get("product", "สินค้า")
    target_customer = profile.get("target_customer", "ลูกค้า")

    if not missing_content_types:
        return f"ทำแคมเปญต่อเนื่องที่รวมรีวิว โปร และเหตุผลซื้อ {product} ในโพสต์เดียว"

    first_missing = missing_content_types[0]
    angle_map = {
        "customer review": f"ชวนลูกค้าเก่าหรือรีวิวจริงมาเล่าว่าทำไม {product} ถึงเหมาะกับ{target_customer}",
        "behind the scenes": f"พาเห็นเบื้องหลังการเตรียม {product} เพื่อสร้างความน่าเชื่อถือ",
        "promotion": f"สร้างข้อเสนอชัดเจนสำหรับ {product} พร้อมเวลาหรือจำนวนจำกัด",
        "product education": f"อธิบายประโยชน์ วิธีใช้ หรือวิธีเลือก {product} ให้เหมาะกับ{target_customer}",
        "social proof": f"โชว์หลักฐานความนิยม รีวิว หรือจำนวนลูกค้าที่เลือก {product}",
        "urgency campaign": f"ทำโพสต์เร่งตัดสินใจสำหรับ {product} ด้วยโปรช่วงสั้น",
    }
    return angle_map.get(first_missing, f"เล่ามุมใหม่ของ {product} ที่ยังไม่เคยใช้บ่อย")


def analyze_business_insights(store_profile: dict | None, content_history: list[dict]) -> dict:
    """Analyze local store memory and return practical business insights."""
    profile = store_profile or {}
    history = content_history or []
    topics = [item.get("topic", "").strip() for item in history if item.get("topic")]
    topic_counts = Counter(topics)

    most_used_topic = "ยังไม่มีข้อมูล"
    if topic_counts:
        most_used_topic = topic_counts.most_common(1)[0][0]

    repeated_topics = [topic for topic, count in topic_counts.items() if count > 1]
    if repeated_topics:
        repeated_topic_warning = "พบหัวข้อซ้ำ: " + ", ".join(repeated_topics[:3])
    else:
        repeated_topic_warning = "ยังไม่พบหัวข้อซ้ำที่น่ากังวล"

    missing_content_types = _detect_missing_content_types(history)
    next_best_content_angle = _next_angle(missing_content_types, profile)

    product = profile.get("product", "สินค้า")
    target_customer = profile.get("target_customer", "ลูกค้า")
    if not history:
        business_recommendation = (
            f"เริ่มเก็บข้อมูลคอนเทนต์ของ {product} อย่างน้อย 3-5 โพสต์ "
            f"เพื่อดูว่ามุมไหนเหมาะกับ{target_customer}มากที่สุด"
        )
    elif repeated_topics:
        business_recommendation = (
            "ลดการใช้หัวข้อเดิมซ้ำ และเพิ่มคอนเทนต์ประเภทที่ยังขาด "
            f"โดยเริ่มจาก: {next_best_content_angle}"
        )
    elif missing_content_types:
        business_recommendation = (
            "คอนเทนต์เริ่มมีทิศทางแล้ว แต่ควรเติมประเภทที่ยังขาด "
            f"เพื่อให้ลูกค้าเห็นทั้งความน่าเชื่อถือ ความคุ้มค่า และเหตุผลซื้อ"
        )
    else:
        business_recommendation = (
            "คอนเทนต์ครอบคลุมดีแล้ว ขั้นต่อไปควรทำแคมเปญขายต่อเนื่องและวัดผลจากยอดทักแชท"
        )

    return {
        "total_generated_content": len(history),
        "most_used_topic": most_used_topic,
        "repeated_topic_warning": repeated_topic_warning,
        "missing_content_types": missing_content_types,
        "next_best_content_angle": next_best_content_angle,
        "business_recommendation": business_recommendation,
    }
