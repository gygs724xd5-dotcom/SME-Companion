def _clean(value: str) -> str:
    return value.strip()


def generate_content_plan(
    store_type: str,
    product: str,
    target_customer: str,
    tone: str,
    strategy: dict,
    recent_topics: list[str] | None = None,
) -> dict:
    """Generate a deterministic Thai daily content plan for an SME."""
    clean_store_type = _clean(store_type)
    clean_product = _clean(product)
    clean_target_customer = _clean(target_customer)
    clean_tone = _clean(tone)
    recent_topics = recent_topics or []

    angle_options = [
        (
            "ประโยชน์หลักของสินค้า",
            f"เล่าให้เห็นว่า {clean_product} ช่วยให้วันของ{clean_target_customer}ง่ายขึ้นอย่างไร",
        ),
        (
            "เบื้องหลังร้าน",
            f"พาเห็นขั้นตอนหรือความใส่ใจของ{clean_store_type}ก่อนส่งมอบ {clean_product}",
        ),
        (
            "รีวิวหรือคำถามลูกค้า",
            f"ตอบคำถามที่{clean_target_customer}มักสงสัยก่อนตัดสินใจซื้อ {clean_product}",
        ),
        (
            "ไอเดียการใช้งาน",
            f"แนะนำวิธีใช้หรือโอกาสที่เหมาะกับ {clean_product} ในชีวิตประจำวัน",
        ),
        (
            "ข้อเสนอจำกัดเวลา",
            f"ทำให้{clean_target_customer}มีเหตุผลชัดเจนในการสั่ง {clean_product} วันนี้",
        ),
    ]
    recent_topic_set = {topic.strip().lower() for topic in recent_topics}
    selected_topic, selected_angle = next(
        (
            (topic, angle)
            for topic, angle in angle_options
            if topic.strip().lower() not in recent_topic_set
        ),
        angle_options[0],
    )

    hashtags = [
        f"#{clean_product.replace(' ', '')}",
        f"#{clean_store_type.replace(' ', '')}",
        "#SMEไทย",
        "#โปรโมทร้าน",
        "#ของดีบอกต่อ",
    ]

    facebook_caption = (
        f"วันนี้{clean_store_type}ขอแนะนำ {clean_product} สำหรับ{clean_target_customer}\n\n"
        f"มุมคอนเทนต์วันนี้: {selected_angle}\n"
        f"จุดเด่นของวันนี้คือ {strategy['sales_angle']} ในสไตล์{clean_tone} "
        f"พร้อมข้อเสนอ: {strategy['promotion_idea']}\n\n"
        "สนใจทักแชทหรือแวะมาที่ร้านได้เลย วันนี้พร้อมดูแลครับ/ค่ะ"
    )

    line_broadcast = (
        f"สวัสดีครับ/ค่ะ วันนี้มี {clean_product} จาก{clean_store_type} มาแนะนำ\n"
        f"เหมาะสำหรับ{clean_target_customer}ที่กำลังมองหาตัวเลือกดีๆ วันนี้\n"
        f"โปรวันนี้: {strategy['promotion_idea']}\n"
        "ทักกลับมาเพื่อสั่งซื้อหรือสอบถามรายละเอียดได้เลย"
    )

    tiktok_caption = (
        f"{clean_product} ที่{clean_target_customer}ควรลองวันนี้! "
        f"{selected_angle} ดูให้จบแล้วทักมารับโปรได้เลย #SMEไทย"
    )

    image_idea = (
        f"ถ่ายภาพ {clean_product} แบบใกล้ชิดในบริบทของ{clean_store_type} "
        f"พร้อมข้อความสั้นๆ ว่า 'เหมาะสำหรับ{clean_target_customer}' "
        "และให้เห็นรายละเอียดที่ช่วยตัดสินใจซื้อ"
    )

    call_to_action = "ทักแชทตอนนี้เพื่อสอบถามรายละเอียด รับโปรวันนี้ หรือจองสินค้าไว้ก่อนได้เลย"

    markdown = f"""## แผนวันนี้
{strategy['strategy_name']}

## เหตุผล
{strategy['strategy_reason']}

## แนวคอนเทนต์ใหม่
{selected_angle}

## เวลาที่เหมาะ
{strategy['best_posting_time']}

## มุมขาย
{strategy['sales_angle']}

## ไอเดียโปรโมชัน
{strategy['promotion_idea']}

## แคปชัน Facebook
{facebook_caption}

## ข้อความ LINE
{line_broadcast}

## แคปชัน TikTok
{tiktok_caption}

## แฮชแท็ก
{" ".join(hashtags)}

## ไอเดียภาพ
{image_idea}

## คำกระตุ้นการซื้อ
{call_to_action}
"""

    return {
        "strategy": strategy,
        "topic": selected_topic,
        "content_angle": selected_angle,
        "facebook_caption": facebook_caption,
        "line_broadcast": line_broadcast,
        "tiktok_caption": tiktok_caption,
        "hashtags": hashtags,
        "image_idea": image_idea,
        "call_to_action": call_to_action,
        "markdown": markdown,
    }


def generate_daily_content(
    store_type: str,
    product: str,
    target_customer: str,
    tone: str,
    strategy: dict | None = None,
    recent_topics: list[str] | None = None,
) -> dict:
    """Backward-compatible wrapper for the V0.1 function name."""
    if strategy is None:
        strategy = {
            "strategy_name": "Daily Value Reminder",
            "strategy_reason": "ช่วยให้ลูกค้าเข้าใจเร็วว่าสินค้าดีอย่างไรและควรซื้อวันนี้เพราะอะไร",
            "best_posting_time": "11:00-13:00 น. หรือ 19:00-21:00 น.",
            "sales_angle": "เน้นประโยชน์หลัก ความคุ้มค่า และความน่าเชื่อถือของร้าน",
            "promotion_idea": "ข้อเสนอพิเศษสำหรับลูกค้าที่ทักแชทหรือสั่งภายในวันนี้",
            "content_goal": "ทำให้ลูกค้าจำร้านได้และเริ่มบทสนทนาเพื่อปิดการขาย",
        }

    return generate_content_plan(
        store_type=store_type,
        product=product,
        target_customer=target_customer,
        tone=tone,
        strategy=strategy,
        recent_topics=recent_topics,
    )


def generate_sales_brief(
    store_type: str,
    product: str,
    target_customer: str,
    tone: str,
    strategy: dict,
    sales_strategy: dict,
    promotion: dict,
    campaign: list[dict],
) -> str:
    """Generate a Thai markdown sales brief for the Revenue Engine."""
    clean_store_type = _clean(store_type)
    clean_product = _clean(product)
    clean_target_customer = _clean(target_customer)
    clean_tone = _clean(tone)

    campaign_rows = "\n".join(
        [
            (
                f"### {item['day']}: {item['campaign_theme']}\n"
                f"- เป้าหมายขาย: {item['sales_objective']}\n"
                f"- มุมคอนเทนต์: {item['content_angle']}\n"
                f"- เวลาที่เหมาะ: {item['best_posting_time']}\n"
                f"- คำกระตุ้นการซื้อ: {item['call_to_action']}\n"
            )
            for item in campaign
        ]
    )
    ready_captions = "\n".join(
        [f"- **{item['day']}**: {item['caption']}" for item in campaign]
    )

    return f"""## แผนธุรกิจจาก AI
แผนเพิ่มยอดขายสำหรับ{clean_store_type}ที่ต้องการผลักดัน {clean_product} ไปยัง{clean_target_customer} ด้วยโทน{clean_tone}

## เป้าหมายยอดขาย
{sales_strategy['sales_goal']}

## เหตุผล
{sales_strategy['sales_reason']}

## สิ่งที่ควรทำ
{sales_strategy['recommended_action']}

## ไอเดียโปรโมชัน
**{promotion['promotion_name']}**

{promotion['promotion_mechanic']}

## เหตุผลที่ใช้ได้ผล
{promotion['why_it_works']}

มุมราคา: {promotion['suggested_price_angle']}

## แผนขาย 3 วัน
{campaign_rows}
## แคปชันพร้อมโพสต์
{ready_captions}

## คำแนะนำสุดท้าย
เริ่มจากคอนเทนต์ตามกลยุทธ์ "{strategy['strategy_name']}" แล้วใช้โปร "{promotion['promotion_name']}" ต่อเนื่อง 3 วัน วัดผลจากจำนวนทักแชท ออเดอร์ และลูกค้าที่กลับมาซื้อซ้ำ
"""
