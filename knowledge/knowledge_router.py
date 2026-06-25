from knowledge.beauty_shop_playbook import BEAUTY_SHOP_PLAYBOOK
from knowledge.clothing_shop_playbook import CLOTHING_SHOP_PLAYBOOK
from knowledge.coffee_shop_playbook import COFFEE_SHOP_PLAYBOOK
from knowledge.construction_shop_playbook import CONSTRUCTION_SHOP_PLAYBOOK
from knowledge.restaurant_playbook import RESTAURANT_PLAYBOOK


DEFAULT_PLAYBOOK = {
    "best_content_types": [
        "ประโยชน์สินค้า",
        "รีวิวลูกค้า",
        "เบื้องหลังร้าน",
        "วิธีใช้หรือวิธีเลือก",
        "ข้อเสนอที่มีเหตุผลซื้อชัดเจน",
    ],
    "reels_ideas": [
        "ปัญหาลูกค้าก่อนเจอสินค้า แล้วตามด้วยวิธีแก้",
        "โชว์สินค้าในการใช้งานจริงแบบสั้น",
        "ตอบคำถามที่ลูกค้าถามบ่อยใน 15 วินาที",
    ],
    "photo_ideas": [
        "ภาพสินค้าในการใช้งานจริง",
        "ภาพรายละเอียดที่ทำให้เห็นคุณภาพ",
        "ภาพรีวิวหรือหลักฐานจากลูกค้าจริง",
    ],
    "sales_angles": [
        "แก้ปัญหาให้ลูกค้าได้ชัด",
        "คุ้มค่าและตัดสินใจง่าย",
        "มีหลักฐานความน่าเชื่อถือก่อนซื้อ",
    ],
    "promotion_ideas": [
        "โปรลูกค้าใหม่",
        "เซตแนะนำราคาพิเศษ",
        "ข้อเสนอจำกัดเวลาสำหรับคนที่ทักวันนี้",
    ],
    "customer_trust_ideas": [
        "รีวิวลูกค้าจริง",
        "เบื้องหลังการทำงาน",
        "วิธีสั่งซื้อและเงื่อนไขชัดเจน",
    ],
    "repeat_customer_ideas": [
        "สิทธิ์พิเศษลูกค้าเก่า",
        "ของแถมหรือส่วนลดสำหรับซื้อซ้ำ",
        "แจ้งสินค้าใหม่ตามสิ่งที่เคยซื้อ",
    ],
    "common_mistakes": [
        "โพสต์ขายตรงซ้ำโดยไม่เล่าคุณค่า",
        "ไม่มีรีวิวหรือหลักฐานสร้างความมั่นใจ",
        "ข้อเสนอไม่ชัดว่าลูกค้าต้องทำอะไรต่อ",
    ],
}


def get_playbook(store_type):
    """Return a local industry playbook based on Thai or English store type."""
    text = str(store_type or "").strip().lower()

    if any(keyword in text for keyword in ["กาแฟ", "คาเฟ่", "coffee", "cafe"]):
        return COFFEE_SHOP_PLAYBOOK
    if any(keyword in text for keyword in ["อาหาร", "restaurant", "ข้าว", "ครัว", "ฮาลาล"]):
        return RESTAURANT_PLAYBOOK
    if any(keyword in text for keyword in ["เสื้อ", "ผ้า", "แฟชั่น", "clothing", "fashion", "apparel"]):
        return CLOTHING_SHOP_PLAYBOOK
    if any(keyword in text for keyword in ["ก่อสร้าง", "วัสดุ", "เครื่องมือ", "ช่าง", "construction", "hardware"]):
        return CONSTRUCTION_SHOP_PLAYBOOK
    if any(keyword in text for keyword in ["บิวตี้", "ความงาม", "สกินแคร์", "เครื่องสำอาง", "beauty", "skincare", "cosmetic"]):
        return BEAUTY_SHOP_PLAYBOOK

    return DEFAULT_PLAYBOOK
