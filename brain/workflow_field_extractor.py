from __future__ import annotations

import re

from brain.canonical_entity_adapter import merge_canonical_fields_first


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
    total_cost = None
    selling_price = None
    unit_cost = None
    requested_output = None
    component_costs = []
    text = str(message or "")

    if re.search(
        r"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19|cost\s*per\s*unit|unit\s*cost",
        text,
        flags=re.IGNORECASE,
    ):
        requested_output = "cost_per_unit"
    elif re.search(
        r"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21|\u0e23\u0e27\u0e21\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19|\u0e23\u0e27\u0e21\s*(?:\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23|\u0e01\u0e35\u0e48)|total\s*cost",
        text,
        flags=re.IGNORECASE,
    ):
        requested_output = "total_cost"

    total_cost_match = re.search(
        r"(?:\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21|total\s*cost)\D*(" + _NUMBER_PATTERN + r")",
        text,
        flags=re.IGNORECASE,
    )
    if total_cost_match:
        total_cost = _to_number(total_cost_match.group(1))

    unit_cost_match = re.search(
        r"(" + _NUMBER_PATTERN + r")\s*(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)\s*(?:\u0e15\u0e48\u0e2d|/)\s*(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|pcs?|units?)",
        text,
        flags=re.IGNORECASE,
    )
    if unit_cost_match:
        unit_cost = _to_number(unit_cost_match.group(1))
    unit_cost_prefix_match = re.search(
        r"(?:\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\s*(?:\u0e0a\u0e34\u0e49\u0e19\u0e25\u0e30|\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19)|unit\s*cost)\D*("
        + _NUMBER_PATTERN
        + r")",
        text,
        flags=re.IGNORECASE,
    )
    if unit_cost_prefix_match:
        unit_cost = _to_number(unit_cost_prefix_match.group(1))

    if requested_output == "total_cost" and total_cost is None and unit_cost is None:
        for match in re.finditer(
            r"(?P<name>[A-Za-z\u0e00-\u0e7f]{1,40}?)\s*(?P<amount>" + _NUMBER_PATTERN + r")\s*(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)?",
            text,
            flags=re.IGNORECASE,
        ):
            name = re.sub(r"[\s,:-]+", " ", match.group("name")).strip()
            lowered_name = name.lower()
            if not name or any(
                token in lowered_name
                for token in (
                    "total cost",
                    "cost",
                    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
                    "\u0e23\u0e27\u0e21",
                    "\u0e17\u0e33",
                    "\u0e44\u0e14\u0e49",
                    "\u0e02\u0e32\u0e22",
                    "\u0e23\u0e32\u0e04\u0e32",
                )
            ):
                continue
            currency_match = re.search(r"(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)", match.group(0), flags=re.IGNORECASE)
            amount = _to_number(match.group("amount"))
            component_costs.append(
                {
                    "label": name,
                    "name": name,
                    "amount": amount,
                    "cost": amount,
                    "currency": "THB" if currency_match else None,
                    "raw_text": match.group(0).strip(),
                    "source": "workflow_field_extractor",
                    "provenance": "deterministic_labeled_component_cost",
                    "order": len(component_costs),
                }
            )

    unit_match = re.search(
        r"(?:\u0e02\u0e32\u0e22\u0e27\u0e31\u0e19\u0e25\u0e30|\u0e27\u0e31\u0e19\u0e25\u0e30)\s*("
        + _NUMBER_PATTERN
        + r")\s*(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|\u0e01\u0e25\u0e48\u0e2d\u0e07|\u0e41\u0e01\u0e49\u0e27)?",
        text,
        flags=re.IGNORECASE,
    )
    if unit_match:
        total_units = _to_number(unit_match.group(1))

    quantity_matches = list(
        re.finditer(
            r"(" + _NUMBER_PATTERN + r")\s*(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|pcs?|units?)",
            text,
            flags=re.IGNORECASE,
        )
    )
    if quantity_matches:
        total_units = _to_number(quantity_matches[-1].group(1))

    cost_match = re.search(r"\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\s*(" + _NUMBER_PATTERN + r")", text, flags=re.IGNORECASE)
    if cost_match:
        ingredients.append({"name": "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19", "cost": _to_number(cost_match.group(1))})

    for raw_line in ([] if component_costs else re.split(r"[\n,]+", text)):
        line = raw_line.strip()
        if not line:
            continue
        numbers = re.findall(_NUMBER_PATTERN, line)
        if not numbers:
            continue
        lowered = line.lower()
        if re.match(r"^\s*" + _NUMBER_PATTERN, line):
            continue
        if any(daily_term in lowered for daily_term in ["ขายวันละ", "วันละ"]):
            line_without_daily = re.sub(
                r"(?:\u0e02\u0e32\u0e22\u0e27\u0e31\u0e19\u0e25\u0e30|\u0e27\u0e31\u0e19\u0e25\u0e30)\s*"
                + _NUMBER_PATTERN
                + r"\s*(?:\u0e0a\u0e34\u0e49\u0e19|\u0e25\u0e39\u0e01|\u0e2d\u0e31\u0e19|\u0e01\u0e25\u0e48\u0e2d\u0e07|\u0e41\u0e01\u0e49\u0e27)?",
                "",
                line,
                flags=re.IGNORECASE,
            ).strip()
            if not re.findall(_NUMBER_PATTERN, line_without_daily):
                continue
            line = line_without_daily
            lowered = line.lower()
            numbers = re.findall(_NUMBER_PATTERN, line)
        amount = _to_number(numbers[-1])
        if any(keyword in lowered for keyword in ["ทำได้", "ได้", "จำนวน", "ผลิตได้"]):
            if any(unit in lowered for unit in ["ชิ้น", "ลูก", "อัน", "กล่อง", "แก้ว"]):
                total_units = amount
                continue
        if any(keyword in lowered for keyword in ["ขาย", "ราคาขาย", "ชิ้นละ", "ลูกละ"]) and not any(
            daily_term in lowered for daily_term in ["ขายวันละ", "วันละ"]
        ):
            selling_price = amount
            continue
        name = re.sub(_NUMBER_PATTERN, "", line)
        name = re.sub(r"(บาท|บ\.|ราคา|ต้นทุน)", "", name, flags=re.IGNORECASE).strip(" :-")
        if name:
            ingredients.append({"name": name, "cost": amount})

    fields = {}
    if component_costs:
        ingredients.extend(component_costs)
        fields["component_costs"] = component_costs
    if ingredients:
        fields["ingredients_costs"] = ingredients
    if total_cost is not None:
        fields["total_cost"] = total_cost
    if unit_cost:
        fields["cost"] = unit_cost
        fields["unit_cost"] = unit_cost
        fields["cost_per_unit"] = unit_cost
    if total_units is not None:
        fields["total_units"] = total_units
    if selling_price and selling_price != total_units:
        fields["selling_price"] = selling_price
    if requested_output:
        fields["requested_output"] = requested_output
    return fields


def _extract_profit_fields(message: str) -> dict:
    text = str(message or "")
    fields = {}
    cost_match = re.search(r"(?:\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19|\u0e17\u0e38\u0e19|cost)\D*(" + _NUMBER_PATTERN + r")", text, flags=re.IGNORECASE)
    if cost_match:
        fields["cost"] = _to_number(cost_match.group(1))
    price_match = re.search(r"(?:\u0e02\u0e32\u0e22|\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22|sell|selling price)\D*(" + _NUMBER_PATTERN + r")", text, flags=re.IGNORECASE)
    if price_match:
        fields["price"] = _to_number(price_match.group(1))
        fields["selling_price"] = fields["price"]
    return fields


def extract_workflow_fields(
    message: str,
    workflow: str | None = None,
    canonical_entities: dict | None = None,
) -> dict:
    if workflow == "COST_CALCULATION":
        return merge_canonical_fields_first(_extract_cost_fields(message), canonical_entities, workflow=workflow)
    if workflow == "PROFIT_CALCULATION":
        return merge_canonical_fields_first(_extract_profit_fields(message), canonical_entities, workflow=workflow)

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

    return merge_canonical_fields_first(fields, canonical_entities, workflow=workflow)
