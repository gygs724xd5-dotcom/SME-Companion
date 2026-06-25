def _clean(value: str) -> str:
    return value.strip()


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


def generate_sales_campaign(
    store_type: str,
    product: str,
    target_customer: str,
    tone: str,
    sales_strategy: dict,
    promotion: dict,
) -> list[dict]:
    """Generate a 3-day sales campaign from strategy and promotion data."""
    clean_store_type = _clean(store_type)
    clean_product = _clean(product)
    clean_customer = _clean(target_customer)
    clean_tone = _clean(tone)

    campaign_steps = [
        {
            "day": "Day 1",
            "campaign_theme": "เปิดปัญหาและเหตุผลที่ควรสนใจ",
            "sales_objective": "สร้างการรับรู้และทำให้ลูกค้าเห็นว่าข้อเสนอนี้เกี่ยวกับเขา",
            "content_angle": sales_strategy["customer_behavior"],
            "caption": (
                f"{clean_customer} ที่กำลังมองหา {clean_product} ลองดูข้อเสนอนี้จาก{clean_store_type} "
                f"วันนี้เรามี {promotion['promotion_name']} ในโทน{clean_tone}ที่ช่วยให้ตัดสินใจง่ายขึ้น"
            ),
        },
        {
            "day": "Day 2",
            "campaign_theme": "โชว์ข้อเสนอและเหตุผลซื้อ",
            "sales_objective": "เปลี่ยนความสนใจให้เป็นการทักแชทหรือสั่งซื้อ",
            "content_angle": promotion["why_it_works"],
            "caption": (
                f"โปรวันนี้: {promotion['promotion_mechanic']} "
                f"เหมาะกับ{clean_customer}ที่อยากลอง {clean_product} แบบคุ้มและไม่ต้องคิดนาน"
            ),
        },
        {
            "day": "Day 3",
            "campaign_theme": "ปิดการขายด้วยความเร่งด่วน",
            "sales_objective": "กระตุ้นการตัดสินใจรอบสุดท้าย",
            "content_angle": sales_strategy["recommended_action"],
            "caption": (
                f"วันสุดท้ายสำหรับ {promotion['promotion_name']} ของ {clean_product} "
                f"ถ้ากำลังสนใจ ทักมาตอนนี้เพื่อให้ร้านช่วยแนะนำตัวเลือกที่เหมาะที่สุด"
            ),
        },
    ]

    return [
        {
            **step,
            "best_posting_time": _best_posting_time(clean_store_type, index),
            "call_to_action": promotion["call_to_action"],
        }
        for index, step in enumerate(campaign_steps)
    ]
