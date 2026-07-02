from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import uuid4
from copy import deepcopy
import re


ENTITY_RUNTIME_VERSION = "5.3.0"
ENTITY_RUNTIME_SOURCE = "entity_runtime"
DEFAULT_CURRENCY = "THB"

T = TypeVar("T", bound="_CanonicalEntity")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _number(value: str) -> float | int:
    number = float(str(value).replace(",", ""))
    return int(number) if number.is_integer() else number


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n,.:;")


def _unique_dicts(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        marker = (
            item.get("entity_type"),
            item.get("role"),
            item.get("amount"),
            item.get("unit"),
            item.get("name"),
            item.get("raw_text"),
        )
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique


class _CanonicalEntity:
    """Shared serialization for canonical entity runtime objects."""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls: type[T], data: dict | None) -> T:
        source = data or {}
        allowed = {item.name for item in fields(cls)}
        values = {key: deepcopy(value) for key, value in source.items() if key in allowed}
        return cls(**values)


@dataclass
class MoneyEntity(_CanonicalEntity):
    entity_id: str = field(default_factory=lambda: _new_id("money"))
    entity_type: str = "money"
    role: str = "amount"
    amount: float | int = 0
    currency: str = DEFAULT_CURRENCY
    raw_text: str = ""
    normalized_field: str = ""
    confidence: float = 0.0
    source: str = ENTITY_RUNTIME_SOURCE
    span: tuple[int, int] | None = None
    metadata: dict = field(default_factory=dict)
    version: str = ENTITY_RUNTIME_VERSION


@dataclass
class QuantityEntity(_CanonicalEntity):
    entity_id: str = field(default_factory=lambda: _new_id("quantity"))
    entity_type: str = "quantity"
    role: str = "quantity"
    amount: float | int = 0
    unit: str = ""
    raw_text: str = ""
    normalized_field: str = "quantity"
    confidence: float = 0.0
    source: str = ENTITY_RUNTIME_SOURCE
    span: tuple[int, int] | None = None
    metadata: dict = field(default_factory=dict)
    version: str = ENTITY_RUNTIME_VERSION


@dataclass
class ProductEntity(_CanonicalEntity):
    entity_id: str = field(default_factory=lambda: _new_id("product"))
    entity_type: str = "product"
    role: str = "product"
    name: str = ""
    raw_text: str = ""
    normalized_field: str = "product"
    confidence: float = 0.0
    source: str = ENTITY_RUNTIME_SOURCE
    span: tuple[int, int] | None = None
    metadata: dict = field(default_factory=dict)
    version: str = ENTITY_RUNTIME_VERSION


@dataclass
class DateEntity(_CanonicalEntity):
    entity_id: str = field(default_factory=lambda: _new_id("date"))
    entity_type: str = "date"
    role: str = "date"
    value: str = ""
    raw_text: str = ""
    normalized_field: str = "date"
    confidence: float = 0.0
    source: str = ENTITY_RUNTIME_SOURCE
    span: tuple[int, int] | None = None
    metadata: dict = field(default_factory=dict)
    version: str = ENTITY_RUNTIME_VERSION


@dataclass
class EntityPayload(_CanonicalEntity):
    entity_payload_id: str = field(default_factory=lambda: _new_id("entity_payload"))
    version: str = ENTITY_RUNTIME_VERSION
    source: str = ENTITY_RUNTIME_SOURCE
    source_message: str = ""
    language: str = "th"
    entities: list[dict] = field(default_factory=list)
    grouped_entities: dict = field(default_factory=dict)
    slots: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)
    extracted_at: str = field(default_factory=_utc_now)


MONEY_LABELS = {
    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21": ("cost", "cost"),
    "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19": ("cost", "cost"),
    "\u0e17\u0e38\u0e19": ("cost", "cost"),
    "\u0e02\u0e32\u0e22": ("selling_price", "selling_price"),
    "\u0e23\u0e32\u0e04\u0e32": ("price", "price"),
}

QUANTITY_UNITS = (
    "\u0e0a\u0e34\u0e49\u0e19",
    "\u0e01\u0e25\u0e48\u0e2d\u0e07",
    "\u0e41\u0e01\u0e49\u0e27",
    "\u0e2d\u0e31\u0e19",
    "\u0e16\u0e38\u0e07",
    "\u0e08\u0e32\u0e19",
    "\u0e0a\u0e38\u0e14",
    "pcs",
    "units",
)

DATE_KEYWORDS = (
    "\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49",
    "\u0e40\u0e21\u0e37\u0e48\u0e2d\u0e27\u0e32\u0e19",
    "\u0e1e\u0e23\u0e38\u0e48\u0e07\u0e19\u0e35\u0e49",
    "\u0e2a\u0e31\u0e1b\u0e14\u0e32\u0e2b\u0e4c\u0e19\u0e35\u0e49",
    "\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49",
    "today",
    "yesterday",
    "tomorrow",
)

THAI_MONTHS = (
    "\u0e21\u0e01\u0e23\u0e32\u0e04\u0e21",
    "\u0e01\u0e38\u0e21\u0e20\u0e32\u0e1e\u0e31\u0e19\u0e18\u0e4c",
    "\u0e21\u0e35\u0e19\u0e32\u0e04\u0e21",
    "\u0e40\u0e21\u0e29\u0e32\u0e22\u0e19",
    "\u0e1e\u0e24\u0e29\u0e20\u0e32\u0e04\u0e21",
    "\u0e21\u0e34\u0e16\u0e38\u0e19\u0e32\u0e22\u0e19",
    "\u0e01\u0e23\u0e01\u0e0e\u0e32\u0e04\u0e21",
    "\u0e2a\u0e34\u0e07\u0e2b\u0e32\u0e04\u0e21",
    "\u0e01\u0e31\u0e19\u0e22\u0e32\u0e22\u0e19",
    "\u0e15\u0e38\u0e25\u0e32\u0e04\u0e21",
    "\u0e1e\u0e24\u0e28\u0e08\u0e34\u0e01\u0e32\u0e22\u0e19",
    "\u0e18\u0e31\u0e19\u0e27\u0e32\u0e04\u0e21",
)


def _money_entity(match: re.Match, role: str, field_name: str) -> MoneyEntity:
    return MoneyEntity(
        role=role,
        amount=_number(match.group("amount")),
        raw_text=_clean(match.group(0)),
        normalized_field=field_name,
        confidence=0.92,
        span=match.span(),
    )


def extract_money_entities(message: str | None) -> list[MoneyEntity]:
    text = str(message or "")
    entities = []
    label_pattern = "|".join(re.escape(label) for label in sorted(MONEY_LABELS, key=len, reverse=True))
    pattern = rf"(?P<label>{label_pattern})[\s:=\uff1a-]*(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)?"
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        role, field_name = MONEY_LABELS.get(match.group("label"), ("amount", "amount"))
        entities.append(_money_entity(match, role, field_name))

    unit_price_pattern = (
        rf"(?:\u0e02\u0e32\u0e22)?(?P<product>[A-Za-z\u0e00-\u0e7f]{{2,40}}?)"
        rf"(?P<unit>{'|'.join(re.escape(unit) for unit in QUANTITY_UNITS)})\u0e25\u0e30"
        rf"\s*(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?:\u0e1a\u0e32\u0e17|\u0e3f|thb|baht)?"
    )
    for match in re.finditer(unit_price_pattern, text, flags=re.IGNORECASE):
        entity = _money_entity(match, "price", "price")
        entity.metadata["unit"] = match.group("unit")
        entities.append(entity)

    return [MoneyEntity.from_dict(item) for item in _unique_dicts([entity.to_dict() for entity in entities])]


def extract_quantity_entities(message: str | None) -> list[QuantityEntity]:
    text = str(message or "")
    entities = []
    unit_pattern = "|".join(re.escape(unit) for unit in QUANTITY_UNITS)
    pattern = rf"(?:(?P<label>\u0e17\u0e33\u0e44\u0e14\u0e49)\s*)?(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>{unit_pattern})"
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        role = "production_output" if match.group("label") else "quantity"
        field_name = "quantity"
        entities.append(
            QuantityEntity(
                role=role,
                amount=_number(match.group("amount")),
                unit=match.group("unit"),
                raw_text=_clean(match.group(0)),
                normalized_field=field_name,
                confidence=0.9,
                span=match.span(),
            )
        )
    return [QuantityEntity.from_dict(item) for item in _unique_dicts([entity.to_dict() for entity in entities])]


def extract_product_entities(message: str | None) -> list[ProductEntity]:
    text = str(message or "")
    entities = []
    unit_pattern = "|".join(re.escape(unit) for unit in QUANTITY_UNITS)
    unit_price_pattern = (
        rf"\u0e02\u0e32\u0e22(?P<product>[A-Za-z\u0e00-\u0e7f]{{2,40}}?)"
        rf"(?P<unit>{unit_pattern})\u0e25\u0e30\s*\d[\d,]*(?:\.\d+)?"
    )
    for match in re.finditer(unit_price_pattern, text, flags=re.IGNORECASE):
        product = _clean(match.group("product"))
        if product:
            entities.append(
                ProductEntity(
                    name=product,
                    raw_text=product,
                    confidence=0.86,
                    span=match.span("product"),
                    metadata={"pattern": "sell_product_unit_price", "unit": match.group("unit")},
                )
            )
    return [ProductEntity.from_dict(item) for item in _unique_dicts([entity.to_dict() for entity in entities])]


def extract_date_entities(message: str | None) -> list[DateEntity]:
    text = str(message or "")
    lowered = text.lower()
    entities = []
    for keyword in DATE_KEYWORDS:
        index = lowered.find(keyword.lower())
        if index >= 0:
            entities.append(
                DateEntity(
                    value=keyword,
                    raw_text=keyword,
                    confidence=0.85,
                    span=(index, index + len(keyword)),
                    metadata={"date_type": "relative"},
                )
            )

    for match in re.finditer(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", text):
        entities.append(
            DateEntity(
                value=match.group(0),
                raw_text=match.group(0),
                confidence=0.84,
                span=match.span(),
                metadata={"date_type": "numeric"},
            )
        )

    month_pattern = r"\d{1,2}\s*(?:" + "|".join(re.escape(month) for month in THAI_MONTHS) + r")(?:\s*\d{2,4})?"
    for match in re.finditer(month_pattern, text):
        entities.append(
            DateEntity(
                value=_clean(match.group(0)),
                raw_text=_clean(match.group(0)),
                confidence=0.84,
                span=match.span(),
                metadata={"date_type": "thai_month"},
            )
        )
    return [DateEntity.from_dict(item) for item in _unique_dicts([entity.to_dict() for entity in entities])]


def _group_entities(entities: list[dict]) -> dict:
    grouped = {"money": [], "quantity": [], "product": [], "date": []}
    for entity in entities:
        entity_type = entity.get("entity_type")
        if entity_type in grouped:
            grouped[entity_type].append(entity)
    return grouped


def _slots(grouped_entities: dict) -> dict:
    slots: dict[str, Any] = {}
    for entity in grouped_entities.get("money", []):
        field_name = entity.get("normalized_field") or entity.get("role")
        if field_name and field_name not in slots:
            slots[field_name] = entity.get("amount")
    if grouped_entities.get("quantity"):
        quantity = grouped_entities["quantity"][0]
        slots["quantity"] = quantity.get("amount")
        if quantity.get("unit"):
            slots["quantity_unit"] = quantity.get("unit")
    if grouped_entities.get("product"):
        slots["product"] = grouped_entities["product"][0].get("name")
    if grouped_entities.get("date"):
        slots["date"] = grouped_entities["date"][0].get("value")
    return slots


def extract_canonical_entities(message: str | None) -> dict:
    """Return a V5.3 canonical entity payload without changing routing or workflow state."""
    text = str(message or "").strip()
    money = extract_money_entities(text)
    quantities = extract_quantity_entities(text)
    products = extract_product_entities(text)
    dates = extract_date_entities(text)
    entities = [
        *[entity.to_dict() for entity in money],
        *[entity.to_dict() for entity in quantities],
        *[entity.to_dict() for entity in products],
        *[entity.to_dict() for entity in dates],
    ]
    grouped = _group_entities(entities)
    payload = EntityPayload(
        source_message=text,
        entities=entities,
        grouped_entities=grouped,
        slots=_slots(grouped),
        diagnostics={
            "runtime_owns": "extracted_entities",
            "planner_routing_changed": False,
            "workflow_logic_changed": False,
            "business_memory_write": False,
            "entity_count": len(entities),
        },
    )
    return payload.to_dict()


def canonical_entity_payload(message: str | None) -> dict:
    return extract_canonical_entities(message)
