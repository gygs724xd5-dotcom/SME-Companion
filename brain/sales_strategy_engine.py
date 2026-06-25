def _clean(value: str) -> str:
    return value.strip()


def _normalize(value: str) -> str:
    return value.strip().lower()


def _strategy(
    sales_goal: str,
    sales_reason: str,
    customer_behavior: str,
    recommended_action: str,
    urgency_level: str,
) -> dict:
    return {
        "sales_goal": sales_goal,
        "sales_reason": sales_reason,
        "customer_behavior": customer_behavior,
        "recommended_action": recommended_action,
        "urgency_level": urgency_level,
    }


def get_sales_strategy(
    store_type: str,
    product: str,
    target_customer: str,
    tone: str,
    recent_topics: list[str],
) -> dict:
    """Choose a revenue-focused sales strategy for a Thai SME."""
    clean_store_type = _normalize(store_type)
    clean_product = _normalize(product)
    display_product = _clean(product)
    display_customer = _clean(target_customer)
    recent_text = " ".join(recent_topics).lower()

    if any(word in clean_product for word in ["เก่า", "ค้าง", "stock", "clearance", "ล้างสต๊อก"]):
        return _strategy(
            "clear_stock",
            f"{display_product} ควรถูกเร่งขายด้วยข้อเสนอที่ชัดเจนก่อนที่ลูกค้าจะหมดความสนใจ",
            f"{display_customer} มักตัดสินใจเร็วขึ้นเมื่อเห็นจำนวนจำกัดหรือราคาพิเศษ",
            "ทำโปรจำกัดจำนวน พร้อมบอกเหตุผลว่าทำไมควรซื้อวันนี้",
            "high",
        )

    if any(word in clean_product for word in ["พรีเมียม", "premium", "เซต", "signature", "ซิกเนเจอร์"]):
        return _strategy(
            "promote_high_margin_product",
            f"{display_product} มีโอกาสสร้างยอดขายต่อบิลสูงกว่าสินค้าทั่วไป",
            f"{display_customer} ต้องเห็นคุณค่า ความแตกต่าง และเหตุผลที่ราคาคุ้ม",
            "ดันสินค้าหลักด้วยเรื่องคุณภาพ รีวิว และการจัดเซตเพิ่มมูลค่า",
            "medium",
        )

    if any(word in clean_store_type for word in ["กาแฟ", "coffee", "คาเฟ่"]):
        return _strategy(
            "boost_low_traffic_hours",
            "ร้านกาแฟมักมีช่วงขายดีตอนเช้า แต่ยังเพิ่มยอดได้ในช่วงบ่ายหรือหลังอาหาร",
            f"{display_customer} มักซื้อเมื่ออยากพัก เติมพลัง หรือหาของกินคู่เครื่องดื่ม",
            "ทำข้อเสนอช่วงเวลาคนน้อย เช่น โปรบ่ายหรือคอมโบเครื่องดื่มกับขนม",
            "medium",
        )

    if any(word in clean_store_type for word in ["อาหาร", "restaurant", "ฮาลาล"]):
        return _strategy(
            "weekend_push",
            "ร้านอาหารขายดีขึ้นเมื่อผูกกับมื้ออาหาร กลุ่มเพื่อน ครอบครัว หรือวันหยุด",
            f"{display_customer} มักตัดสินใจจากความน่ากิน ความคุ้ม และความสะดวก",
            "ทำแคมเปญเซตมื้ออิ่มหรือโปรสั่งล่วงหน้าสำหรับช่วงพีค",
            "high",
        )

    if any(word in recent_text for word in ["รีวิว", "ลูกค้า", "เรื่องเล่าจากลูกค้า"]):
        return _strategy(
            "bring_back_existing_customers",
            "มีสัญญาณว่าคอนเทนต์เดิมเน้นลูกค้าหรือรีวิว จึงเหมาะกับการดึงลูกค้าเก่ากลับมาซื้อซ้ำ",
            f"{display_customer} ที่เคยซื้อแล้วต้องการเหตุผลใหม่หรือรางวัลเล็กๆ เพื่อกลับมา",
            "ใช้ข้อเสนอสำหรับลูกค้าเก่า สมาชิก หรือคนที่เคยทักแชท",
            "medium",
        )

    if any(word in clean_store_type for word in ["ออนไลน์", "online", "seller"]):
        return _strategy(
            "increase_new_customers",
            "ร้านออนไลน์ต้องสร้างความเชื่อมั่นเร็วเพื่อเปลี่ยนคนเห็นโพสต์ให้เป็นลูกค้าใหม่",
            f"{display_customer} จะซื้อเมื่อเห็นรีวิว วิธีสั่งง่าย และความเสี่ยงต่ำ",
            "ใช้คอนเทนต์รีวิวจริง โปรส่งฟรี และคำสั่งซื้อที่ชัดเจน",
            "medium",
        )

    return _strategy(
        "default_sales_growth",
        f"เป้าหมายหลักคือทำให้ {display_product} ถูกเห็นบ่อยขึ้นและมีเหตุผลซื้อที่ชัดเจน",
        f"{display_customer} ต้องเข้าใจเร็วว่าสินค้าช่วยอะไรและคุ้มอย่างไร",
        "ใช้ข้อเสนอเรียบง่ายพร้อมแคปชันที่ปิดท้ายด้วยการทักแชทหรือสั่งซื้อ",
        "low",
    )
