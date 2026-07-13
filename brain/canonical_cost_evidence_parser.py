"""Pure current-message parser for canonical Business Skill cost evidence.

This module deliberately does not participate in routing, matching, mapping,
selection, workflow execution, or response production.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any


CANONICAL_COST_EVIDENCE_PARSER_VERSION = "5.15.24.6.0"
CANONICAL_COST_EVIDENCE_PARSER_SCOPE = "CURRENT_MESSAGE_CANONICAL_COST_EVIDENCE"

CHANGE_SKILL_ID = "cost.change_analysis.v1"
PER_UNIT_SKILL_ID = "cost.per_unit_calculation.v1"
SUPPORTED_COST_SKILL_IDS = (CHANGE_SKILL_ID, PER_UNIT_SKILL_ID)

COMPLETE = "COMPLETE"
PARTIAL = "PARTIAL"
AMBIGUOUS = "AMBIGUOUS"
NO_EVIDENCE = "NO_EVIDENCE"
INVALID = "INVALID"

CURRENT_USER_MESSAGE = "CURRENT_USER_MESSAGE"
CURRENT_TURN = "CURRENT_TURN"
EXACT_CONFIDENCE = "1.0"

_HEX = re.compile(r"^[0-9a-f]{64}$")
_NUMBER = r"[+-]?(?:0|[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)(?:\.\d+)?"
_NUMBER_BOUND = rf"{_NUMBER}(?!\d|[.,]\d)"
_NUMBER_FULL = re.compile(rf"^{_NUMBER}$", re.ASCII)
_NUMBER_TOKEN = r"[+-]?[0-9\u0e50-\u0e59][0-9\u0e50-\u0e59,]*(?:\.[0-9\u0e50-\u0e59]+)?"
_CURRENCY = r"(?P<currency>บาท|฿|THB|baht)"
_UNIT = r"(?P<unit>ชิ้น|อัน|ลูก|หน่วย|units?)"

REQUIRED_EVIDENCE_IDS = {
    CHANGE_SKILL_ID: ("previous_cost", "current_cost"),
    PER_UNIT_SKILL_ID: ("total_cost", "unit_quantity"),
}
OPTIONAL_EVIDENCE_IDS = {
    CHANGE_SKILL_ID: (),
    PER_UNIT_SKILL_ID: ("waste_or_loss_quantity",),
}

RULE_REGISTRY = (
    ("change.thai.from_transition.v1", CHANGE_SKILL_ID, ("จาก",), ("เป็น", "เหลือ", "ไปเป็น")),
    ("change.english.from_to.v1", CHANGE_SKILL_ID, ("from",), ("to",)),
    ("change.previous.explicit.v1", CHANGE_SKILL_ID, ("เดิม", "ก่อน", "previous"), ()),
    ("change.current.explicit.v1", CHANGE_SKILL_ID, ("ตอนนี้", "ปัจจุบัน", "now", "current"), ()),
    ("per_unit.total.explicit.v1", PER_UNIT_SKILL_ID, ("ต้นทุนรวม", "ค่าใช้จ่ายรวม", "total cost", "total expense"), ()),
    ("per_unit.quantity.explicit.v1", PER_UNIT_SKILL_ID, ("จำนวน", "ทำได้", "produced", "quantity"), ("ชิ้น", "อัน", "ลูก", "หน่วย", "unit", "units")),
    ("per_unit.waste.explicit.v1", PER_UNIT_SKILL_ID, ("ของเสีย", "สูญเสีย", "waste", "loss"), ("ชิ้น", "อัน", "ลูก", "หน่วย", "unit", "units")),
)


@dataclass(frozen=True)
class CanonicalNumericValue:
    canonical_decimal: str


@dataclass(frozen=True)
class CanonicalEvidenceSpan:
    raw_text: str
    raw_start: int
    raw_end: int


@dataclass(frozen=True)
class CanonicalCostEvidenceValue:
    skill_id: str
    required_evidence_id: str
    semantic_role: str
    canonical_decimal: str
    value_digest: str
    raw_text: str
    raw_start: int
    raw_end: int
    currency: str | None
    unit: str | None
    rule_id: str
    confidence: str = EXACT_CONFIDENCE
    source: str = CURRENT_USER_MESSAGE
    freshness: str = CURRENT_TURN
    assumed: bool = False
    user_confirmed: bool = False
    evidence_digest: str = ""


@dataclass(frozen=True)
class CanonicalCostEvidenceParseResult:
    parser_version: str
    parser_scope: str
    skill_id: str
    raw_message: str
    raw_message_digest: str
    evidence_values: tuple[CanonicalCostEvidenceValue, ...]
    missing_required_evidence_ids: tuple[str, ...]
    ambiguous_roles: tuple[str, ...]
    invalid_roles: tuple[str, ...]
    status: str
    reason_codes: tuple[str, ...]
    passive_observation: bool = True
    routing_authority: bool = False
    response_authority: bool = False
    workflow_authority: bool = False
    persistence_authority: bool = False
    runtime_authority: bool = False
    parse_digest: str = ""


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if is_dataclass(value):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    raise ValueError("unsupported canonical material")


def _digest(material: Any) -> str:
    encoded = json.dumps(_canonical(material), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_canonical_decimal(raw: str) -> CanonicalNumericValue:
    if type(raw) is not str or not _NUMBER_FULL.fullmatch(raw):
        raise ValueError("invalid canonical decimal grammar")
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("invalid canonical decimal") from exc
    if not value.is_finite():
        raise ValueError("non-finite canonical decimal")
    if value == 0:
        canonical = "0"
    else:
        canonical = format(value, "f")
        if "." in canonical:
            canonical = canonical.rstrip("0").rstrip(".")
    return CanonicalNumericValue(canonical)


def get_canonical_cost_evidence_rule_registry() -> tuple[tuple[Any, ...], ...]:
    return RULE_REGISTRY


def _value(skill: str, evidence_id: str, raw: str, start: int, end: int,
           currency: str | None, unit: str | None, rule_id: str) -> CanonicalCostEvidenceValue:
    decimal = parse_canonical_decimal(raw).canonical_decimal
    currency_id = "THB" if currency and currency.casefold() in {"บาท", "฿", "thb", "baht"} else None
    unit_id = unit.casefold() if unit else None
    value_digest = _digest(("CANONICAL_COST_NUMERIC_VALUE", evidence_id, decimal))
    draft = CanonicalCostEvidenceValue(
        skill, evidence_id, evidence_id, decimal, value_digest, raw, start, end,
        currency_id, unit_id, rule_id,
    )
    return replace(draft, evidence_digest=_evidence_digest(draft))


def _evidence_digest(value: CanonicalCostEvidenceValue) -> str:
    material = tuple(getattr(value, field.name) for field in fields(value) if field.name != "evidence_digest")
    return _digest(("CANONICAL_COST_EVIDENCE_VALUE", material))


def _result_digest(value: CanonicalCostEvidenceParseResult) -> str:
    material = tuple(getattr(value, field.name) for field in fields(value) if field.name != "parse_digest")
    return _digest(("CANONICAL_COST_EVIDENCE_PARSE_RESULT", material))


def _outside(span: tuple[int, int], occupied: tuple[tuple[int, int], ...]) -> bool:
    return not any(span[0] < end and start < span[1] for start, end in occupied)


def _malformed_after_markers(raw: str, markers: tuple[str, ...]) -> bool:
    marker_pattern = "|".join(re.escape(item) for item in sorted(markers, key=len, reverse=True))
    for match in re.finditer(rf"(?:{marker_pattern})\s*[^0-9\u0e50-\u0e59+-]{{0,12}}(?P<n>{_NUMBER_TOKEN})", raw, re.IGNORECASE):
        token = match.group("n")
        if token.endswith(",") and _NUMBER_FULL.fullmatch(token[:-1]):
            continue
        if not _NUMBER_FULL.fullmatch(token):
            return True
    return False


def _parse_change(raw: str) -> tuple[list[CanonicalCostEvidenceValue], set[str], set[str]]:
    values: list[CanonicalCostEvidenceValue] = []
    ambiguous: set[str] = set()
    invalid: set[str] = set()
    subject = r"(?:ต้นทุน|ทุน|cost)"
    pair_re = re.compile(
        rf"{subject}[^\d\u0e50-\u0e59]{{0,40}}?(?:จาก|from)\s*(?P<previous>{_NUMBER_BOUND})"
        rf"\s*(?:เป็น|เหลือ|ไปเป็น|to)\s*(?P<current>{_NUMBER_BOUND})\s*(?P<currency>บาท|฿|THB|baht)?",
        re.IGNORECASE | re.ASCII,
    )
    pairs = list(pair_re.finditer(raw))
    if len(pairs) > 1:
        ambiguous.update(REQUIRED_EVIDENCE_IDS[CHANGE_SKILL_ID])
        return values, ambiguous, invalid
    occupied: tuple[tuple[int, int], ...] = ()
    if pairs:
        match = pairs[0]
        occupied = ((match.start(), match.end()),)
        currency = match.group("currency")
        rule = "change.english.from_to.v1" if re.search(r"\bfrom\b", match.group(0), re.I) else "change.thai.from_transition.v1"
        for group, evidence_id in (("previous", "previous_cost"), ("current", "current_cost")):
            values.append(_value(CHANGE_SKILL_ID, evidence_id, match.group(group), match.start(group), match.end(group), currency, None, rule))

    role_specs = (
        ("previous_cost", r"(?:ต้นทุน|ทุน|cost)\s*(?:เดิม|ก่อน|previous)\s*", "change.previous.explicit.v1"),
        ("current_cost", r"(?:ต้นทุน|ทุน|cost)\s*(?:ตอนนี้|ปัจจุบัน|now|current)\s*", "change.current.explicit.v1"),
    )
    for evidence_id, prefix, rule in role_specs:
        matches = [m for m in re.finditer(rf"{prefix}(?P<n>{_NUMBER_BOUND})\s*(?P<c>บาท|฿|THB|baht)?", raw, re.I | re.ASCII)
                   if _outside((m.start(), m.end()), occupied)]
        if len(matches) > 1:
            ambiguous.add(evidence_id)
        elif matches:
            match = matches[0]
            values.append(_value(CHANGE_SKILL_ID, evidence_id, match.group("n"), match.start("n"), match.end("n"), match.group("c"), None, rule))
    if _malformed_after_markers(raw, ("จาก", "from", "เดิม", "ก่อน", "previous")):
        invalid.add("previous_cost")
    if _malformed_after_markers(raw, ("เป็น", "เหลือ", "ไปเป็น", "to", "ตอนนี้", "ปัจจุบัน", "now", "current")):
        invalid.add("current_cost")
    counts = {item: sum(value.required_evidence_id == item for value in values) for item in REQUIRED_EVIDENCE_IDS[CHANGE_SKILL_ID]}
    ambiguous.update(item for item, count in counts.items() if count > 1)
    if ambiguous or invalid:
        values = [item for item in values if item.required_evidence_id not in ambiguous | invalid]
    return values, ambiguous, invalid


def _role_matches(raw: str, pattern: re.Pattern[str], skill: str, evidence_id: str,
                  rule: str, *, positive: bool, non_negative: bool = False) -> tuple[list[CanonicalCostEvidenceValue], bool]:
    results = []
    invalid = False
    for match in pattern.finditer(raw):
        try:
            numeric = parse_canonical_decimal(match.group("n")).canonical_decimal
            decimal = Decimal(numeric)
        except ValueError:
            invalid = True
            continue
        if (positive and decimal <= 0) or (non_negative and decimal < 0):
            invalid = True
            continue
        results.append(_value(skill, evidence_id, match.group("n"), match.start("n"), match.end("n"),
                              match.groupdict().get("c"), match.groupdict().get("unit"), rule))
    return results, invalid


def _parse_per_unit(raw: str) -> tuple[list[CanonicalCostEvidenceValue], set[str], set[str]]:
    total_re = re.compile(rf"(?:ต้นทุนรวม|ค่าใช้จ่ายรวม|total\s+cost|total\s+expense)\s*[:=]?\s*(?P<n>{_NUMBER_BOUND})\s*(?P<c>บาท|฿|THB|baht)?", re.I | re.ASCII)
    quantity_re = re.compile(rf"(?:จำนวน|ทำได้|produced|quantity)\s*[:=]?\s*(?P<n>{_NUMBER_BOUND})\s*(?P<unit>ชิ้น|อัน|ลูก|หน่วย|units?)", re.I | re.ASCII)
    waste_re = re.compile(rf"(?:ของเสีย|สูญเสีย|waste|loss)\s*[:=]?\s*(?P<n>{_NUMBER_BOUND})\s*(?P<unit>ชิ้น|อัน|ลูก|หน่วย|units?)", re.I | re.ASCII)
    values: list[CanonicalCostEvidenceValue] = []
    ambiguous: set[str] = set()
    invalid: set[str] = set()
    for evidence_id, pattern, rule, positive, non_negative in (
        ("total_cost", total_re, "per_unit.total.explicit.v1", True, False),
        ("unit_quantity", quantity_re, "per_unit.quantity.explicit.v1", True, False),
        ("waste_or_loss_quantity", waste_re, "per_unit.waste.explicit.v1", False, True),
    ):
        found, bad = _role_matches(raw, pattern, PER_UNIT_SKILL_ID, evidence_id, rule, positive=positive, non_negative=non_negative)
        if bad:
            invalid.add(evidence_id)
        if len(found) > 1:
            ambiguous.add(evidence_id)
        elif found:
            values.extend(found)
    marker_map = {
        "total_cost": ("ต้นทุนรวม", "ค่าใช้จ่ายรวม", "total cost", "total expense"),
        "unit_quantity": ("จำนวน", "ทำได้", "produced", "quantity"),
        "waste_or_loss_quantity": ("ของเสีย", "สูญเสีย", "waste", "loss"),
    }
    for role, markers in marker_map.items():
        if _malformed_after_markers(raw, markers):
            invalid.add(role)
    if ambiguous or invalid:
        values = [item for item in values if item.required_evidence_id not in ambiguous | invalid]
    return values, ambiguous, invalid


def parse_canonical_cost_evidence(skill_id: str, raw_message: str) -> CanonicalCostEvidenceParseResult:
    if type(skill_id) is not str or skill_id not in SUPPORTED_COST_SKILL_IDS:
        raise ValueError("exact supported cost skill_id required")
    if type(raw_message) is not str:
        raise TypeError("raw_message must be a string")
    values, ambiguous, invalid = _parse_change(raw_message) if skill_id == CHANGE_SKILL_ID else _parse_per_unit(raw_message)
    ordered_ids = REQUIRED_EVIDENCE_IDS[skill_id] + OPTIONAL_EVIDENCE_IDS[skill_id]
    values = sorted(values, key=lambda item: ordered_ids.index(item.required_evidence_id))
    present = {item.required_evidence_id for item in values}
    missing = tuple(item for item in REQUIRED_EVIDENCE_IDS[skill_id] if item not in present)
    ambiguous_tuple = tuple(item for item in ordered_ids if item in ambiguous)
    invalid_tuple = tuple(item for item in ordered_ids if item in invalid)
    if invalid_tuple:
        status, reasons = INVALID, tuple(f"INVALID_ROLE:{item}" for item in invalid_tuple)
    elif ambiguous_tuple:
        status, reasons = AMBIGUOUS, tuple(f"AMBIGUOUS_ROLE:{item}" for item in ambiguous_tuple)
    elif not missing:
        status, reasons = COMPLETE, ("COMPLETE_REQUIRED_EVIDENCE",)
    elif present:
        status, reasons = PARTIAL, tuple(f"MISSING_REQUIRED_EVIDENCE:{item}" for item in missing)
    else:
        status, reasons = NO_EVIDENCE, ("NO_CANONICAL_EVIDENCE",)
    draft = CanonicalCostEvidenceParseResult(
        CANONICAL_COST_EVIDENCE_PARSER_VERSION, CANONICAL_COST_EVIDENCE_PARSER_SCOPE,
        skill_id, raw_message, _digest(("RAW_CURRENT_USER_MESSAGE", raw_message)), tuple(values),
        missing, ambiguous_tuple, invalid_tuple, status, reasons,
    )
    return replace(draft, parse_digest=_result_digest(draft))


def verify_canonical_cost_evidence_value(value: Any, raw_message: Any, skill_id: Any) -> bool:
    try:
        if type(value) is not CanonicalCostEvidenceValue or type(raw_message) is not str or skill_id not in SUPPORTED_COST_SKILL_IDS:
            return False
        if value.skill_id != skill_id or value.raw_start < 0 or value.raw_end <= value.raw_start or value.raw_end > len(raw_message):
            return False
        if raw_message[value.raw_start:value.raw_end] != value.raw_text:
            return False
        if value.required_evidence_id not in REQUIRED_EVIDENCE_IDS[skill_id] + OPTIONAL_EVIDENCE_IDS[skill_id]:
            return False
        if value.semantic_role != value.required_evidence_id or value.confidence != EXACT_CONFIDENCE:
            return False
        if value.source != CURRENT_USER_MESSAGE or value.freshness != CURRENT_TURN or value.assumed or value.user_confirmed:
            return False
        if not _HEX.fullmatch(value.value_digest) or not _HEX.fullmatch(value.evidence_digest):
            return False
        parse_canonical_decimal(value.raw_text)
        expected = parse_canonical_cost_evidence(skill_id, raw_message)
        return value in expected.evidence_values and value.evidence_digest == _evidence_digest(value)
    except (AttributeError, TypeError, ValueError):
        return False


def verify_canonical_cost_evidence_parse_result(value: Any) -> bool:
    try:
        if type(value) is not CanonicalCostEvidenceParseResult or type(value.raw_message) is not str:
            return False
        if value.parser_version != CANONICAL_COST_EVIDENCE_PARSER_VERSION or value.parser_scope != CANONICAL_COST_EVIDENCE_PARSER_SCOPE:
            return False
        if value.skill_id not in SUPPORTED_COST_SKILL_IDS or not value.passive_observation:
            return False
        if any(getattr(value, name) for name in ("routing_authority", "response_authority", "workflow_authority", "persistence_authority", "runtime_authority")):
            return False
        if not _HEX.fullmatch(value.raw_message_digest) or not _HEX.fullmatch(value.parse_digest):
            return False
        if not all(verify_canonical_cost_evidence_value(item, value.raw_message, value.skill_id) for item in value.evidence_values):
            return False
        expected = parse_canonical_cost_evidence(value.skill_id, value.raw_message)
        return value == expected and value.parse_digest == _result_digest(value)
    except (AttributeError, TypeError, ValueError):
        return False
