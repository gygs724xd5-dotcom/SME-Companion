from __future__ import annotations

from copy import deepcopy


EMPTY_VALUES = (None, "", [], {})


def _has_value(value) -> bool:
    return value not in EMPTY_VALUES


def _money_entities(canonical_entities: dict | None, role: str) -> list[dict]:
    grouped = (canonical_entities or {}).get("grouped_entities") or {}
    return [
        deepcopy(entity)
        for entity in grouped.get("money", []) or []
        if entity.get("role") == role or entity.get("normalized_field") == role
    ]


def _quantity_entities(canonical_entities: dict | None) -> list[dict]:
    grouped = (canonical_entities or {}).get("grouped_entities") or {}
    return [deepcopy(entity) for entity in grouped.get("quantity", []) or []]


def canonical_workflow_fields(canonical_entities: dict | None, workflow: str | None = None) -> dict:
    """Map Entity Runtime slots into workflow field names without making decisions."""
    payload = canonical_entities or {}
    slots = payload.get("slots") or {}
    fields: dict = {}
    trace: list[dict] = []

    cost = slots.get("cost")
    if _has_value(cost):
        fields["cost"] = cost
        if workflow == "COST_CALCULATION":
            fields["total_cost"] = cost
        cost_entities = _money_entities(payload, "cost")
        if cost_entities:
            fields["costs"] = cost_entities
        trace.append(
            {
                "field": "cost",
                "source": "canonical_entities.slots.cost",
                "value": cost,
            }
        )

    selling_price = slots.get("selling_price")
    price = slots.get("price") if _has_value(slots.get("price")) else selling_price
    if _has_value(price):
        fields["price"] = price
        price_entities = _money_entities(payload, "price") or _money_entities(payload, "selling_price")
        if price_entities:
            fields["prices"] = price_entities
        trace.append(
            {
                "field": "price",
                "source": "canonical_entities.slots.price",
                "value": price,
            }
        )
    if _has_value(selling_price):
        fields["selling_price"] = selling_price
        trace.append(
            {
                "field": "selling_price",
                "source": "canonical_entities.slots.selling_price",
                "value": selling_price,
            }
        )

    quantity = slots.get("quantity")
    if _has_value(quantity):
        fields["quantity"] = quantity
        if workflow == "COST_CALCULATION":
            fields["total_units"] = quantity
        quantity_entities = _quantity_entities(payload)
        if quantity_entities:
            fields["quantities"] = quantity_entities
        trace.append(
            {
                "field": "quantity",
                "source": "canonical_entities.slots.quantity",
                "value": quantity,
            }
        )

    if trace:
        fields["entity_mapping_trace"] = trace
        fields["entity_source"] = "canonical_entity_runtime"
    return fields


def merge_canonical_fields_first(
    legacy_fields: dict | None,
    canonical_entities: dict | None,
    workflow: str | None = None,
) -> dict:
    canonical_fields = canonical_workflow_fields(canonical_entities, workflow=workflow)
    if not canonical_fields:
        return dict(legacy_fields or {})
    merged = dict(legacy_fields or {})
    trace = list(canonical_fields.pop("entity_mapping_trace", []))
    for key, value in canonical_fields.items():
        if _has_value(value):
            merged[key] = value
    if trace:
        merged["entity_mapping_trace"] = trace + list(merged.get("entity_mapping_trace") or [])
    return merged
