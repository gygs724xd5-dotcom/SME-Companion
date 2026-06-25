DAY_LABELS = [
    "Day 1",
    "Day 2",
    "Day 3",
    "Day 4",
    "Day 5",
    "Day 6",
    "Day 7",
]


def _clean(value: str) -> str:
    return value.strip()


def _topic_pool(store_type: str, product: str, target_customer: str) -> list[dict]:
    return [
        {
            "content_theme": "ประโยชน์หลักของสินค้า",
            "sales_goal": "ทำให้ลูกค้าเข้าใจว่าสินค้าช่วยแก้ปัญหาอะไร",
            "suggested_product_angle": f"เล่าว่า {product} ช่วยให้วันของ{target_customer}ง่ายขึ้นอย่างไร",
            "short_caption_idea": f"{product} เหมาะกับ{target_customer}ที่อยากได้ตัวเลือกที่ง่ายและคุ้มกว่าเดิม",
        },
        {
            "content_theme": "เบื้องหลังร้าน",
            "sales_goal": "สร้างความน่าเชื่อถือและความผูกพันกับร้าน",
            "suggested_product_angle": f"พาเห็นความใส่ใจของ{store_type}ก่อนส่งมอบ {product}",
            "short_caption_idea": f"ก่อนถึงมือลูกค้า {product} มีรายละเอียดเล็กๆ ที่เราใส่ใจเสมอ",
        },
        {
            "content_theme": "รีวิวหรือคำถามลูกค้า",
            "sales_goal": "ลดความลังเลก่อนซื้อ",
            "suggested_product_angle": f"ตอบคำถามที่{target_customer}มักถามก่อนเลือก {product}",
            "short_caption_idea": f"ถ้ายังลังเลเรื่อง {product} โพสต์นี้ช่วยตัดสินใจได้ง่ายขึ้น",
        },
        {
            "content_theme": "ไอเดียการใช้งาน",
            "sales_goal": "ทำให้ลูกค้าเห็นภาพการใช้จริง",
            "suggested_product_angle": f"แนะนำโอกาสที่เหมาะกับการใช้ {product}",
            "short_caption_idea": f"ไม่ใช่แค่ซื้อ {product} แต่ใช้ให้คุ้มได้ในหลายโมเมนต์",
        },
        {
            "content_theme": "ข้อเสนอจำกัดเวลา",
            "sales_goal": "กระตุ้นให้ลูกค้าทักหรือสั่งซื้อวันนี้",
            "suggested_product_angle": f"เชื่อม {product} กับโปรหรือข้อเสนอที่มีเวลาจำกัด",
            "short_caption_idea": f"วันนี้มีเหตุผลดีๆ ให้ลอง {product} พร้อมโปรเฉพาะช่วงนี้",
        },
        {
            "content_theme": "เปรียบเทียบก่อนเลือก",
            "sales_goal": "ช่วยให้ลูกค้าเห็นจุดต่างและคุณค่าของสินค้า",
            "suggested_product_angle": f"เทียบให้เห็นว่า {product} เหมาะกับ{target_customer}แบบไหน",
            "short_caption_idea": f"เลือก {product} แบบไหนให้ตรงกับสิ่งที่คุณต้องการที่สุด",
        },
        {
            "content_theme": "เรื่องเล่าจากลูกค้า",
            "sales_goal": "สร้างหลักฐานทางสังคมและความมั่นใจ",
            "suggested_product_angle": f"เล่าประสบการณ์ของลูกค้าที่คล้ายกับ{target_customer}",
            "short_caption_idea": f"เสียงจากลูกค้าจริงที่ลอง {product} แล้วกลับมาบอกต่อ",
        },
        {
            "content_theme": "เคล็ดลับจากร้าน",
            "sales_goal": "เพิ่มคุณค่าให้แบรนด์และทำให้คนติดตามต่อ",
            "suggested_product_angle": f"แชร์ทิปเล็กๆ จาก{store_type}ที่เกี่ยวกับ {product}",
            "short_caption_idea": f"ทิปสั้นๆ จากร้านสำหรับคนที่อยากใช้ {product} ให้คุ้มกว่าเดิม",
        },
        {
            "content_theme": "ปัญหาที่ลูกค้าเจอบ่อย",
            "sales_goal": "ดึงความสนใจด้วยปัญหาที่ตรงใจ",
            "suggested_product_angle": f"เริ่มจากปัญหาของ{target_customer}แล้วโยงไปที่ {product}",
            "short_caption_idea": f"ถ้าคุณเจอปัญหานี้อยู่ {product} อาจเป็นคำตอบที่ง่ายกว่าที่คิด",
        },
    ]


def generate_content_calendar(store_profile: dict, recent_topics: list[str] | None = None) -> list[dict]:
    """Generate a deterministic 7-day content calendar from local store data."""
    recent_topics = recent_topics or []
    store_type = _clean(store_profile.get("store_type", "ร้านค้า"))
    product = _clean(store_profile.get("product", "สินค้า"))
    target_customer = _clean(store_profile.get("target_customer", "ลูกค้า"))

    recent_topic_set = {topic.strip().lower() for topic in recent_topics}
    pool = _topic_pool(store_type, product, target_customer)
    fresh_topics = [
        item for item in pool if item["content_theme"].strip().lower() not in recent_topic_set
    ]
    ordered_topics = fresh_topics + [
        item for item in pool if item["content_theme"].strip().lower() in recent_topic_set
    ]

    calendar = []
    used_topics = set()
    for day_index, day_label in enumerate(DAY_LABELS):
        topic = next(
            (
                item
                for item in ordered_topics
                if item["content_theme"].strip().lower() not in used_topics
            ),
            ordered_topics[day_index % len(ordered_topics)],
        )
        used_topics.add(topic["content_theme"].strip().lower())

        calendar.append(
            {
                "day_label": day_label,
                "content_theme": topic["content_theme"],
                "sales_goal": topic["sales_goal"],
                "suggested_product_angle": topic["suggested_product_angle"],
                "best_posting_time": _best_posting_time(store_type, day_index),
                "short_caption_idea": topic["short_caption_idea"],
            }
        )

    return calendar


def _best_posting_time(store_type: str, day_index: int) -> str:
    clean_store_type = store_type.lower()
    if "กาแฟ" in clean_store_type or "coffee" in clean_store_type or "คาเฟ่" in clean_store_type:
        times = ["07:00-09:00 น.", "13:00-14:00 น.", "08:00-10:00 น."]
    elif "อาหาร" in clean_store_type or "restaurant" in clean_store_type:
        times = ["10:30-12:00 น.", "16:30-18:00 น.", "11:00-12:30 น."]
    elif "เสื้อผ้า" in clean_store_type or "clothing" in clean_store_type or "แฟชั่น" in clean_store_type:
        times = ["19:00-21:00 น.", "12:00-13:00 น.", "20:00-22:00 น."]
    else:
        times = ["11:00-13:00 น.", "19:00-21:00 น.", "12:00-13:00 น."]

    return times[day_index % len(times)]
