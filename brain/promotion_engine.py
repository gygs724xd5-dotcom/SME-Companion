def _clean(value: str) -> str:
    return value.strip()


def get_promotion_idea(
    store_type: str,
    product: str,
    target_customer: str,
    sales_strategy: dict,
) -> dict:
    """Return a practical promotion idea for the selected sales strategy."""
    clean_store_type = _clean(store_type)
    clean_product = _clean(product)
    clean_customer = _clean(target_customer)
    sales_goal = sales_strategy.get("sales_goal", "default_sales_growth")

    if sales_goal == "clear_stock":
        return {
            "promotion_name": "Limited Time Offer",
            "promotion_mechanic": f"{clean_product} ราคาพิเศษเฉพาะจำนวนจำกัดหรือภายในวันนี้",
            "why_it_works": "ความจำกัดช่วยลดการลังเลและทำให้ลูกค้าตัดสินใจเร็วขึ้น",
            "suggested_price_angle": "เน้นว่าคุ้มกว่าราคาปกติและมีจำนวนจำกัด",
            "call_to_action": "ทักแชทตอนนี้เพื่อจองก่อนหมด",
        }

    if sales_goal == "promote_high_margin_product":
        return {
            "promotion_name": "Bundle Deal",
            "promotion_mechanic": f"จัดเซต {clean_product} คู่กับสินค้าเสริมหรือบริการที่เพิ่มมูลค่า",
            "why_it_works": "ลูกค้าเห็นความคุ้มของเซตและร้านเพิ่มยอดต่อบิลได้โดยไม่ลดราคาหนัก",
            "suggested_price_angle": "ชูราคาต่อเซตและมูลค่ารวมที่ลูกค้าได้รับ",
            "call_to_action": "ทักมารับเซตแนะนำสำหรับวันนี้",
        }

    if sales_goal == "boost_low_traffic_hours":
        return {
            "promotion_name": "Buy 2 Discount",
            "promotion_mechanic": f"ซื้อ {clean_product} แก้ว/ชิ้นที่สองรับส่วนลดในช่วงเวลาคนน้อย",
            "why_it_works": "ช่วยดึงลูกค้าเข้าร้านในช่วงเงียบและเพิ่มยอดต่อออเดอร์",
            "suggested_price_angle": "เน้นส่วนลดเฉพาะช่วงเวลา เช่น บ่ายนี้เท่านั้น",
            "call_to_action": "ชวนเพื่อนมารับโปรช่วงเวลานี้",
        }

    if sales_goal == "weekend_push":
        return {
            "promotion_name": "Lunch Set",
            "promotion_mechanic": f"จัดเซต {clean_product} สำหรับมื้อกลางวันหรือมื้อครอบครัว",
            "why_it_works": f"{clean_customer} ตัดสินใจง่ายขึ้นเมื่อเห็นราคาเซตและเมนูครบ",
            "suggested_price_angle": "เน้นเซตอิ่มคุ้มและสั่งล่วงหน้าได้",
            "call_to_action": "สั่งล่วงหน้าหรือจองเซตก่อนถึงมื้ออาหาร",
        }

    if sales_goal == "bring_back_existing_customers":
        return {
            "promotion_name": "Member Reward",
            "promotion_mechanic": f"ลูกค้าเก่าที่กลับมาซื้อ {clean_product} รับของแถมหรือส่วนลดพิเศษ",
            "why_it_works": "รางวัลเล็กๆ ทำให้ลูกค้าเก่ารู้สึกว่าร้านจำเขาได้และมีเหตุผลกลับมา",
            "suggested_price_angle": "เน้นสิทธิ์เฉพาะลูกค้าที่เคยซื้อหรือเคยทักแชท",
            "call_to_action": "ส่งข้อความว่าเคยซื้อแล้วเพื่อรับสิทธิ์",
        }

    if sales_goal == "increase_new_customers":
        return {
            "promotion_name": "Free Delivery",
            "promotion_mechanic": f"ลูกค้าใหม่สั่ง {clean_product} รับค่าส่งฟรีหรือส่วนลดค่าส่ง",
            "why_it_works": "ลดความเสี่ยงครั้งแรกและทำให้การลองซื้อง่ายขึ้น",
            "suggested_price_angle": "ชูว่าเริ่มลองได้ง่ายเพราะไม่มีค่าส่งเพิ่ม",
            "call_to_action": "ทักแชทเพื่อรับโปรลูกค้าใหม่",
        }

    return {
        "promotion_name": "Social Proof Offer",
        "promotion_mechanic": f"นำรีวิวหรือยอดขายของ {clean_product} มาคู่กับข้อเสนอพิเศษวันนี้",
        "why_it_works": f"{clean_customer} เชื่อมั่นง่ายขึ้นเมื่อเห็นว่าคนอื่นลองแล้วพอใจ",
        "suggested_price_angle": "เน้นราคาเข้าถึงง่ายพร้อมหลักฐานความนิยม",
        "call_to_action": "ทักแชทเพื่อดูรีวิวและรับข้อเสนอวันนี้",
    }
