from __future__ import annotations

import re


_NUMBER_PATTERN = r"\d+(?:,\d{3})*(?:\.\d+)?"
_CHANNELS = ["หน้าร้าน", "ออนไลน์", "facebook", "line", "tiktok", "ตลาดนัด"]
_PRODUCT_STOP_WORDS = [
    "ได้",
    "วันละ",
    "ขายช่วง",
    "ขายที่",
    "ขายทาง",
    "ขายช่องทาง",
    "ช่วง",
    "จำนวน",
    "ราคา",
    "บาท",
]


def _to_number(value: str) -> float:
    amount = float(str(value).replace(",", ""))
    return int(amount) if amount.is_integer() else amount


def _clean_product(value: str) -> str:
    product = re.sub(r"\s+", " ", str(value or "")).strip(" :,-")
    product = re.sub(r"^(ขนม|สินค้า|เมนู|อาหาร|ของ)\s*", "", product).strip()
    return product


def _extract_product(message: str) -> str | None:
    text = str(message or "").strip()
    for marker in ["ทำ", "ขาย"]:
        match = re.search(rf"{marker}\s*([^0-9\n]+)", text, flags=re.IGNORECASE)
        if not match:
            continue
        product = match.group(1)
        for stop_word in _PRODUCT_STOP_WORDS:
            product = product.split(stop_word, 1)[0]
        cleaned = _clean_product(product)
        if cleaned and cleaned not in {"อะไร", "ยังไง", "อย่างไร"}:
            return cleaned
    return None


def _extract_quantity(message: str) -> dict:
    text = str(message or "")
    patterns = [
        (r"วันละ\s*(" + _NUMBER_PATTERN + r")\s*(ลูก|ชิ้น|อัน|กล่อง|แก้ว)?", "daily_capacity"),
        (r"ได้\s*(" + _NUMBER_PATTERN + r")\s*(ลูก|ชิ้น|อัน|กล่อง|แก้ว)?\s*(?:ต่อวัน|วัน)?", "daily_capacity"),
        (r"(" + _NUMBER_PATTERN + r")\s*(ลูก|ชิ้น|อัน|กล่อง|แก้ว)\s*(?:ต่อวัน|/วัน)", "daily_capacity"),
        (r"มี\s*(" + _NUMBER_PATTERN + r")\s*(ลูก|ชิ้น|อัน|กล่อง|แก้ว)", "available_quantity"),
    ]
    for pattern, field in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return {field: _to_number(match.group(1))}
    return {}


def _extract_selling_window(message: str) -> str | None:
    text = str(message or "")
    range_match = re.search(r"(\d{1,2}(?:[.:]\d{2})?)\s*[-–ถึง]\s*(\d{1,2}(?:[.:]\d{2})?)", text)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"
    if "9 โมงถึงเที่ยง" in text:
        return "9 โมงถึงเที่ยง"
    for word in ["ช่วงเช้า", "ช่วงกลางวัน", "ช่วงบ่าย", "ช่วงเย็น", "ช่วงค่ำ"]:
        if word in text:
            window = word
            next_time = re.search(rf"{word}\s*({_NUMBER_PATTERN}(?:[.:]\d{{2}})?\s*[-–ถึง]\s*{_NUMBER_PATTERN}(?:[.:]\d{{2}})?)", text)
            if next_time:
                window = f"{word} {next_time.group(1)}"
            return window
    return None


def _extract_channel(message: str) -> str | None:
    lowered = str(message or "").lower()
    found = []
    for channel in _CHANNELS:
        if channel in lowered:
            found.append("Facebook" if channel == "facebook" else "LINE" if channel == "line" else "TikTok" if channel == "tiktok" else channel)
    return ", ".join(dict.fromkeys(found)) if found else None


def _extract_cost_fields(message: str) -> dict:
    ingredients = []
    total_units = None
    selling_price = None

    for raw_line in re.split(r"[\n,]+", str(message or "")):
        line = raw_line.strip()
        if not line:
            continue
        numbers = re.findall(_NUMBER_PATTERN, line)
        if not numbers:
            continue
        lowered = line.lower()
        amount = _to_number(numbers[-1])
        if any(keyword in lowered for keyword in ["ทำได้", "ได้", "จำนวน", "ผลิตได้"]):
            if any(unit in lowered for unit in ["ชิ้น", "ลูก", "อัน", "กล่อง", "แก้ว"]):
                total_units = amount
                continue
        if any(keyword in lowered for keyword in ["ขาย", "ราคาขาย", "ชิ้นละ", "ลูกละ"]):
            selling_price = amount
            continue
        name = re.sub(_NUMBER_PATTERN, "", line)
        name = re.sub(r"(บาท|บ\.|ราคา|ต้นทุน)", "", name, flags=re.IGNORECASE).strip(" :-")
        if name:
            ingredients.append({"name": name, "cost": amount})

    fields = {}
    if ingredients:
        fields["ingredients_costs"] = ingredients
    if total_units:
        fields["total_units"] = total_units
    if selling_price:
        fields["selling_price"] = selling_price
    return fields


def extract_workflow_fields(message: str, workflow: str | None = None) -> dict:
    if workflow == "COST_CALCULATION":
        return _extract_cost_fields(message)

    fields = {}
    product = _extract_product(message)
    if product:
        fields["product"] = product
    fields.update(_extract_quantity(message))
    selling_window = _extract_selling_window(message)
    if selling_window:
        fields["selling_window"] = selling_window
    channel = _extract_channel(message)
    if channel:
        fields["sales_channel"] = channel

    if any(word in str(message or "") for word in ["แป้ง", "ไข่", "น้ำตาล", "ทำได้", "ต้นทุน"]):
        fields.update(_extract_cost_fields(message))

    return fields
