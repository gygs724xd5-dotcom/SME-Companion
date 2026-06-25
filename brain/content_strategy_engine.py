def _normalize(value: str) -> str:
    return value.strip().lower()


def _strategy(
    strategy_name: str,
    strategy_reason: str,
    best_posting_time: str,
    sales_angle: str,
    promotion_idea: str,
    content_goal: str,
) -> dict:
    return {
        "strategy_name": strategy_name,
        "strategy_reason": strategy_reason,
        "best_posting_time": best_posting_time,
        "sales_angle": sales_angle,
        "promotion_idea": promotion_idea,
        "content_goal": content_goal,
    }


def get_content_strategy(
    store_type: str,
    product: str,
    target_customer: str,
    tone: str,
) -> dict:
    """Return a daily content strategy for a Thai SME without using AI APIs."""
    clean_store_type = _normalize(store_type)
    clean_product = product.strip()
    clean_target_customer = target_customer.strip()
    clean_tone = tone.strip()

    if "halal" in clean_store_type or "ฮาลาล" in clean_store_type:
        return _strategy(
            "Trust-first Halal Choice",
            f"ลูกค้า{clean_target_customer}ต้องการความมั่นใจเรื่องฮาลาล ความสะอาด และแหล่งที่มาของ {clean_product}",
            "10:30-11:30 น. ก่อนมื้อกลางวัน หรือ 16:30-17:30 น. ก่อนมื้อเย็น",
            "เน้นความอร่อยที่มั่นใจได้ พร้อมบอกจุดเด่นด้านฮาลาลและความสะอาด",
            "จัดเซตอิ่มคุ้มสำหรับครอบครัวหรือเพื่อนร่วมงาน พร้อมส่วนลดเมื่อสั่งล่วงหน้า",
            "สร้างความเชื่อมั่นและกระตุ้นการสั่งอาหารในมื้อถัดไป",
        )

    if "coffee" in clean_store_type or "กาแฟ" in clean_store_type or "คาเฟ่" in clean_store_type:
        return _strategy(
            "Morning Energy Hook",
            f"{clean_product} เหมาะกับการเริ่มวันของ{clean_target_customer} และคอนเทนต์แนว{clean_tone}ช่วยทำให้ร้านดูใกล้ตัว",
            "07:00-09:00 น. ช่วงก่อนเริ่มงาน และ 13:00-14:00 น. ช่วงบ่าย",
            "ขายความสดชื่น ความหอม และโมเมนต์พักสั้นๆ ระหว่างวัน",
            "โปรแก้วที่สองลดราคา หรือคอมโบเครื่องดื่มกับขนมเฉพาะวันนี้",
            "เพิ่มออเดอร์ช่วงเช้าและทำให้ลูกค้านึกถึงร้านเป็นตัวเลือกประจำวัน",
        )

    if "restaurant" in clean_store_type or "อาหาร" in clean_store_type:
        return _strategy(
            "Meal-time Craving Push",
            f"อาหารตัดสินใจซื้อง่ายเมื่อเห็นก่อนเวลาอาหาร โดยเฉพาะถ้าทำให้{clean_target_customer}เห็นภาพความคุ้มและความอร่อย",
            "10:30-12:00 น. ก่อนมื้อกลางวัน หรือ 16:30-18:00 น. ก่อนมื้อเย็น",
            "เน้นภาพน่ากิน ปริมาณคุ้ม และความสะดวกในการสั่ง",
            "โปรเซตมื้อเดียวจบ หรือส่งฟรีเมื่อสั่งครบยอดที่กำหนด",
            "กระตุ้นยอดสั่งทันทีในช่วงเวลามื้ออาหาร",
        )

    if "clothing" in clean_store_type or "เสื้อผ้า" in clean_store_type or "แฟชั่น" in clean_store_type:
        return _strategy(
            "Style Confidence Story",
            f"{clean_product} ต้องขายด้วยภาพการใช้งานจริง เพื่อให้{clean_target_customer}จินตนาการตัวเองใส่ได้ง่าย",
            "19:00-21:00 น. ช่วงลูกค้ามีเวลาช้อปและดูไอเดียแต่งตัว",
            "ขายลุค ความมั่นใจ และโอกาสในการใช้งาน เช่น ทำงาน เที่ยว หรือออกงาน",
            "ซื้อครบ 2 ชิ้นรับส่วนลด หรือจัดเซตลุคพร้อมราคาพิเศษ",
            "เพิ่มการทักแชทถามไซซ์ สี และปิดการขายผ่านอินบ็อกซ์",
        )

    if "online" in clean_store_type or "ออนไลน์" in clean_store_type or "seller" in clean_store_type:
        return _strategy(
            "Fast Decision Offer",
            f"ร้านออนไลน์ต้องลดความลังเลของ{clean_target_customer}ด้วยเหตุผลซื้อที่ชัดเจน รีวิว และข้อเสนอที่จบไว",
            "12:00-13:00 น. หรือ 20:00-22:00 น. ช่วงพักและก่อนนอน",
            "เน้นปัญหาที่สินค้าแก้ได้ รีวิวจริง และความง่ายในการสั่ง",
            "โปรส่งฟรีหรือโค้ดลดเฉพาะวันนี้สำหรับลูกค้าที่ทักแชท",
            "เพิ่มการคลิก ทักแชท และคำสั่งซื้อจากโพสต์เดียว",
        )

    if "beauty" in clean_store_type or "ความงาม" in clean_store_type or "บิวตี้" in clean_store_type or "สกินแคร์" in clean_store_type:
        return _strategy(
            "Before-after Benefit",
            f"สินค้า/บริการความงามต้องทำให้{clean_target_customer}เห็นผลลัพธ์และรู้สึกว่าเริ่มได้ง่ายกับ {clean_product}",
            "11:00-13:00 น. หรือ 19:00-21:00 น. ช่วงลูกค้าดูแลตัวเอง",
            "ขายผลลัพธ์ ความมั่นใจ และความเหมาะกับปัญหาของลูกค้า",
            "โปรทดลองครั้งแรก หรือเซตดูแลตัวเองราคาพิเศษ",
            "สร้างความสนใจและกระตุ้นให้ลูกค้าทักมาปรึกษา",
        )

    return _strategy(
        "Daily Value Reminder",
        f"SME ควรสื่อสารให้{clean_target_customer}เข้าใจเร็วว่า {clean_product} ช่วยอะไรและทำไมควรเลือกวันนี้",
        "11:00-13:00 น. หรือ 19:00-21:00 น. ช่วงลูกค้าเปิดดูโซเชียล",
        "เน้นประโยชน์หลัก ความคุ้มค่า และความน่าเชื่อถือของร้าน",
        "ข้อเสนอพิเศษสำหรับลูกค้าที่ทักแชทหรือสั่งภายในวันนี้",
        "ทำให้ลูกค้าจำร้านได้และเริ่มบทสนทนาเพื่อปิดการขาย",
    )
