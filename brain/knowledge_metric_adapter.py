from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Any


KNOWLEDGE_METRIC_ADAPTER_VERSION = "5.9.0"


class MetricCompletenessStatus(str, Enum):
    AVAILABLE_COMPLETE = "AVAILABLE_COMPLETE"
    AVAILABLE_INCOMPLETE = "AVAILABLE_INCOMPLETE"
    MISSING = "MISSING"
    HISTORICAL = "HISTORICAL"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"


class EvidenceUsabilityState(str, Enum):
    USABLE = "USABLE"
    PARTIALLY_USABLE = "PARTIALLY_USABLE"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    NOT_USABLE = "NOT_USABLE"
    CONFLICTED = "CONFLICTED"


@dataclass
class CanonicalMetricValue:
    metric_id: str
    value: Any = None
    value_type: str = ""
    unit: str = ""
    currency: str = ""
    timeframe: str = ""
    comparison_period: str = ""
    entity_scope: str = ""
    observed_at: str = ""
    source: str = "conversation_context"
    truth_classification: str = "REPORTED"
    freshness: str = "current_turn"
    confidence: float = 0.8
    completeness_status: str = MetricCompletenessStatus.MISSING.value
    missing_components: list[str] = field(default_factory=list)
    raw_text: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    knowledge_ids: list[str] = field(default_factory=list)
    usability_state: str = EvidenceUsabilityState.NOT_USABLE.value

    def to_dict(self) -> dict:
        return asdict(self)


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return deepcopy(value)
    if value in (None, "", {}, ()):
        return []
    return [deepcopy(value)]


def _compact(text: str) -> str:
    return "".join(str(text or "").lower().split())


def _to_number(value: str) -> int | float:
    cleaned = str(value or "").replace(",", "")
    number = float(cleaned)
    return int(number) if number.is_integer() else number


def _is_inventory_quantity_context(text: str) -> bool:
    compact = _compact(text)
    inventory_markers = (
        "\u0e02\u0e2d\u0e07\u0e40\u0e2b\u0e25\u0e37\u0e2d",
        "\u0e40\u0e2b\u0e25\u0e37\u0e2d",
        "\u0e2a\u0e15\u0e47\u0e2d\u0e01",
        "\u0e2a\u0e15\u0e4a\u0e2d\u0e01",
        "stock",
        "inventory",
        "remaining",
        "left",
    )
    return any(marker in compact for marker in inventory_markers)


def _period(text: str) -> str:
    compact = _compact(text)
    period_patterns = [
        ("day", ["ต่อวัน", "รายวัน", "วันละ", "perday", "/day"]),
        ("batch", ["ต่อรอบ", "รอบละ", "perbatch"]),
        ("week", ["ต่อสัปดาห์", "รายสัปดาห์", "สัปดาห์ละ", "perweek"]),
        ("month", ["ต่อเดือน", "รายเดือน", "เดือนละ", "permonth"]),
        ("hour", ["ต่อชั่วโมง", "ชั่วโมงละ", "perhour"]),
    ]
    for value, patterns in period_patterns:
        if any(pattern in compact for pattern in patterns):
            return value
    return ""


def _has_historical_marker(text: str) -> bool:
    compact = _compact(text)
    return any(token in compact for token in ("เมื่อก่อน", "เดือนก่อน", "สัปดาห์ก่อน", "lastmonth", "previous"))


def _has_unverified_marker(text: str) -> bool:
    compact = _compact(text)
    return any(token in compact for token in ("น่าจะ", "ประมาณ", "ไม่แน่ใจ", "maybe", "around"))


def _base_status(missing: list[str], text: str) -> tuple[str, str]:
    if _has_historical_marker(text):
        return MetricCompletenessStatus.HISTORICAL.value, EvidenceUsabilityState.REFERENCE_ONLY.value
    if _has_unverified_marker(text):
        return MetricCompletenessStatus.UNVERIFIED.value, EvidenceUsabilityState.PARTIALLY_USABLE.value
    if missing:
        return MetricCompletenessStatus.AVAILABLE_INCOMPLETE.value, EvidenceUsabilityState.PARTIALLY_USABLE.value
    return MetricCompletenessStatus.AVAILABLE_COMPLETE.value, EvidenceUsabilityState.USABLE.value


def _metric(metric_id: str, value: Any, text: str, *, unit: str = "", currency: str = "", timeframe: str = "", value_type: str = "number", missing: list[str] | None = None, scope: str = "") -> CanonicalMetricValue:
    missing = list(missing or [])
    status, usability = _base_status(missing, text)
    return CanonicalMetricValue(
        metric_id=metric_id,
        value=value,
        value_type=value_type,
        unit=unit,
        currency=currency,
        timeframe=timeframe,
        entity_scope=scope,
        raw_text=text,
        completeness_status=status,
        missing_components=missing,
        usability_state=usability,
        confidence=0.65 if status == MetricCompletenessStatus.UNVERIFIED.value else 0.86,
    )


def _add(metrics: dict[str, list[CanonicalMetricValue]], metric: CanonicalMetricValue) -> None:
    metrics.setdefault(metric.metric_id, []).append(metric)


def _extract_text_values(text: str, metrics: dict[str, list[CanonicalMetricValue]]) -> None:
    period = _period(text)
    inventory_quantity_context = _is_inventory_quantity_context(text)
    if not inventory_quantity_context:
        for match in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*(?:ชิ้น|pcs?|pieces?)", text, flags=re.IGNORECASE):
            missing = [] if period else ["timeframe"]
            _add(metrics, _metric("output_quantity", _to_number(match.group(1)), text, unit="pieces", timeframe=period, missing=missing))
    if re.search(r"(?:ทำได้|ผลิตได้|กำลังผลิต)\s*\d", text):
        number_match = re.search(r"(?:ทำได้|ผลิตได้|กำลังผลิต)\s*(\d[\d,]*(?:\.\d+)?)", text)
        if number_match and "output_quantity" not in metrics:
            missing = [] if period else ["unit", "timeframe"]
            _add(metrics, _metric("output_quantity", _to_number(number_match.group(1)), text, timeframe=period, missing=missing))

    for match in re.finditer(r"(?:ยอดขาย|รายได้)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:บาท|thb)?", text, flags=re.IGNORECASE):
        missing = [] if period else ["timeframe"]
        _add(metrics, _metric("total_revenue", _to_number(match.group(1)), text, currency="THB", timeframe=period, missing=missing))
    for match in re.finditer(r"(?:ต้นทุน)\s*(?:น่าจะ|ประมาณ|ราวๆ|ราว)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:บาท|thb)?", text, flags=re.IGNORECASE):
        missing = ["scope", "unit_basis"]
        _add(metrics, _metric("unit_cost", _to_number(match.group(1)), text, currency="THB", timeframe=period, missing=missing, scope="candidate_unit"))
    for match in re.finditer(r"(?:ขาย|ราคา)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:บาท|thb)?", text, flags=re.IGNORECASE):
        if "ยอดขาย" in text[max(0, match.start() - 8):match.start() + 8]:
            continue
        _add(metrics, _metric("selling_price", _to_number(match.group(1)), text, currency="THB", timeframe=period, missing=[]))
    for match in re.finditer(r"(?:เหลือ(?:แค่)?|สต็อกเหลือ|สต๊อกเหลือ)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:ชิ้น|pcs?|pieces?)?", text, flags=re.IGNORECASE):
        unit = "pieces" if re.search(r"ชิ้น|pcs?|pieces?", match.group(0), re.IGNORECASE) else ""
        _add(metrics, _metric("current_stock", _to_number(match.group(1)), text, unit=unit, missing=[] if unit else ["unit"]))

    compact = _compact(text)
    if "กำไรลด" in compact or "profitdown" in compact or "lowerprofit" in compact:
        _add(metrics, _metric("net_profit", "decreased", text, value_type="direction", missing=["comparison_period", "baseline_value", "current_value"]))
    if "ลูกค้าเพิ่ม" in compact or "customersincreasing" in compact or "morecustomers" in compact:
        _add(metrics, _metric("customer_count", "increased", text, value_type="direction", missing=["comparison_period", "baseline_value", "current_value"]))
    if "ขายได้" in compact or "ขายดี" in compact or "sellingwell" in compact:
        _add(metrics, _metric("order_count", "present", text, value_type="observation", missing=["timeframe", "value"]))
    if "ไม่มีเงินสด" in compact or "เงินสดไม่พอ" in compact or "nocash" in compact:
        _add(metrics, _metric("cash_balance", "insufficient", text, value_type="observation", missing=["amount", "timeframe"]))

    if any(token in compact for token in ("ตามออเดอร์", "รับออเดอร์", "madetoorder", "preorder")):
        _add(metrics, _metric("business_model", "made_to_order", text, value_type="category", missing=[]))
    if any(token in compact for token in ("หน้าร้าน", "storefront")):
        _add(metrics, _metric("location_model", "storefront", text, value_type="category", missing=[]))
    if any(token in compact for token in ("ทำจากบ้าน", "homebased", "จากบ้าน")):
        _add(metrics, _metric("location_model", "home_based", text, value_type="category", missing=[]))
    if period:
        if "output_quantity" in metrics:
            _add(metrics, _metric("output_time_period", period, text, value_type="period", missing=[]))
        _add(metrics, _metric("analysis_timeframe", period, text, value_type="period", missing=[]))
    if any(token in compact for token in ("เทียบเดือนนี้กับเดือนที่แล้ว", "เดือนนี้กับเดือนที่แล้ว", "comparethismonthlastmonth")):
        _add(metrics, _metric("analysis_timeframe", "this_month_vs_last_month", text, value_type="comparison_period", missing=[]))


def _metric_from_structured(metric_id: str, value: Any, source: str) -> CanonicalMetricValue:
    if isinstance(value, dict):
        raw_status = value.get("completeness_status")
        missing = list(value.get("missing_components") or [])
        timeframe = value.get("timeframe") or ""
        status = raw_status or (MetricCompletenessStatus.AVAILABLE_COMPLETE.value if not missing else MetricCompletenessStatus.AVAILABLE_INCOMPLETE.value)
        usability = EvidenceUsabilityState.USABLE.value if status == MetricCompletenessStatus.AVAILABLE_COMPLETE.value else EvidenceUsabilityState.PARTIALLY_USABLE.value
        return CanonicalMetricValue(
            metric_id=metric_id,
            value=value.get("value"),
            value_type=value.get("value_type") or "",
            unit=value.get("unit") or "",
            currency=value.get("currency") or "",
            timeframe=timeframe,
            comparison_period=value.get("comparison_period") or "",
            entity_scope=value.get("entity_scope") or "",
            observed_at=value.get("observed_at") or "",
            source=value.get("source") or source,
            truth_classification=value.get("truth_classification") or "REPORTED",
            freshness=value.get("freshness") or "",
            confidence=float(value.get("confidence") or 0.8),
            completeness_status=status,
            missing_components=missing,
            raw_text=value.get("raw_text") or "",
            evidence_ids=list(value.get("evidence_ids") or []),
            knowledge_ids=list(value.get("knowledge_ids") or []),
            usability_state=value.get("usability_state") or usability,
        )
    return CanonicalMetricValue(
        metric_id=metric_id,
        value=value,
        value_type="structured",
        source=source,
        completeness_status=MetricCompletenessStatus.AVAILABLE_COMPLETE.value,
        usability_state=EvidenceUsabilityState.USABLE.value,
    )


def _extract_structured_values(source: Any, metrics: dict[str, list[CanonicalMetricValue]], source_name: str) -> None:
    supported = {
        "total_revenue", "total_cost_of_goods", "operating_expenses", "net_profit", "selling_price", "unit_cost",
        "average_order_value", "current_stock", "average_daily_sales", "output_quantity", "output_time_period",
        "maximum_capacity", "current_order_volume", "cash_balance", "order_count", "customer_count",
        "analysis_timeframe", "business_model", "location_model",
    }
    data = _as_dict(source)
    for key, value in data.items():
        if key in supported and value not in (None, "", [], {}):
            _add(metrics, _metric_from_structured(key, value, source_name))
    slots = _as_dict(data.get("slots"))
    for key, value in slots.items():
        if key in supported and value not in (None, "", [], {}):
            _add(metrics, _metric_from_structured(key, value, f"{source_name}.slots"))


def _collapse_conflicts(metrics: dict[str, list[CanonicalMetricValue]]) -> dict[str, CanonicalMetricValue]:
    result: dict[str, CanonicalMetricValue] = {}
    for metric_id, values in metrics.items():
        if not values:
            continue
        distinct = {str(value.value) for value in values if value.value not in (None, "", [], {})}
        if len(distinct) > 1:
            first = deepcopy(values[0])
            first.completeness_status = MetricCompletenessStatus.CONFLICTING.value
            first.usability_state = EvidenceUsabilityState.CONFLICTED.value
            first.missing_components = ["conflict_resolution"]
            first.raw_text = " | ".join(str(value.raw_text or value.value) for value in values)
            result[metric_id] = first
            continue
        result[metric_id] = deepcopy(values[0])
    return result


def extract_canonical_metrics(
    *,
    user_message: str | None = None,
    normalized_user_message: str | None = None,
    business_situation: dict | None = None,
    evidence_runtime: dict | None = None,
    truth_runtime: dict | None = None,
    conversation_context: dict | None = None,
    structured_business_data: dict | None = None,
) -> dict:
    """Extract a minimal deterministic metric projection for Knowledge Runtime."""

    metrics: dict[str, list[CanonicalMetricValue]] = {}
    texts = [
        str(normalized_user_message or user_message or ""),
        str(_as_dict(business_situation).get("current_focus") or ""),
        str(_as_dict(business_situation).get("objective") or ""),
    ]
    for item in _as_list(_as_dict(business_situation).get("known_evidence")):
        if isinstance(item, dict) and item.get("summary") not in (None, "", [], {}):
            texts.append(str(item.get("summary")))
    for source in (_as_dict(conversation_context), _as_dict(structured_business_data), _as_dict(evidence_runtime), _as_dict(truth_runtime)):
        _extract_structured_values(source, metrics, "structured_context")
    for text in texts:
        if text.strip():
            _extract_text_values(text, metrics)
    collapsed = _collapse_conflicts(metrics)
    return {metric_id: value.to_dict() for metric_id, value in sorted(collapsed.items())}
