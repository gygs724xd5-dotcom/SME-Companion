import ast
import dataclasses
from decimal import Decimal
from pathlib import Path

import pytest

from brain.canonical_cost_evidence_parser import (
    AMBIGUOUS,
    CANONICAL_COST_EVIDENCE_PARSER_SCOPE,
    CANONICAL_COST_EVIDENCE_PARSER_VERSION,
    CHANGE_SKILL_ID,
    COMPLETE,
    CURRENT_TURN,
    CURRENT_USER_MESSAGE,
    INVALID,
    NO_EVIDENCE,
    PARTIAL,
    PER_UNIT_SKILL_ID,
    get_canonical_cost_evidence_rule_registry,
    parse_canonical_cost_evidence,
    parse_canonical_decimal,
    verify_canonical_cost_evidence_parse_result,
    verify_canonical_cost_evidence_value,
)


def by_id(result):
    return {item.required_evidence_id: item for item in result.evidence_values}


@pytest.mark.parametrize("message,previous,current", (
    ("ต้นทุนเพิ่มจาก 30 เป็น 40 บาท", "30", "40"),
    ("ต้นทุนลดจาก 50 เหลือ 42 บาท", "50", "42"),
    ("cost changed from 30 to 40", "30", "40"),
    ("ต้นทุนเพิ่มจาก 30.50 เป็น 40.25", "30.5", "40.25"),
    ("ต้นทุนเพิ่มจาก 1,250 เป็น 1,500.75 บาท", "1250", "1500.75"),
    ("ต้นทุนเพิ่มจาก 0 เป็น -2", "0", "-2"),
))
def test_change_complete_exact_semantics(message, previous, current):
    result = parse_canonical_cost_evidence(CHANGE_SKILL_ID, message)
    values = by_id(result)
    assert result.status == COMPLETE
    assert (values["previous_cost"].canonical_decimal, values["current_cost"].canonical_decimal) == (previous, current)
    for value in result.evidence_values:
        assert message[value.raw_start:value.raw_end] == value.raw_text
        assert value.confidence == "1.0"
        assert value.source == CURRENT_USER_MESSAGE and value.freshness == CURRENT_TURN
        assert value.assumed is False and value.user_confirmed is False
        assert verify_canonical_cost_evidence_value(value, message, CHANGE_SKILL_ID)


def test_shared_and_absent_currency_are_not_fabricated():
    shared = by_id(parse_canonical_cost_evidence(CHANGE_SKILL_ID, "ต้นทุนจาก 30 เป็น 40 บาท"))
    absent = by_id(parse_canonical_cost_evidence(CHANGE_SKILL_ID, "ต้นทุนจาก 30 เป็น 40"))
    assert {item.currency for item in shared.values()} == {"THB"}
    assert {item.currency for item in absent.values()} == {None}


@pytest.mark.parametrize("message,status", (
    ("ต้นทุนเดิม 30", PARTIAL),
    ("ต้นทุนตอนนี้ 40", PARTIAL),
    ("แก้ใหม่ ต้นทุนตอนนี้ 30", PARTIAL),
    ("ต้นทุน 30 40", NO_EVIDENCE),
    ("30 40", NO_EVIDENCE),
    ("ต้นทุนเป็น 40 จาก 30", NO_EVIDENCE),
    ("ต้นทุนจาก 30 เป็น 40 และต้นทุนจาก 50 เป็น 60", AMBIGUOUS),
    ("ต้นทุนเดิม 30 ต้นทุนเดิม 31", AMBIGUOUS),
    ("ต้นทุนจาก 1,2 เป็น 40", INVALID),
    ("ต้นทุนจาก ๑๐ เป็น 20", INVALID),
))
def test_change_incomplete_ambiguous_and_invalid(message, status):
    assert parse_canonical_cost_evidence(CHANGE_SKILL_ID, message).status == status


@pytest.mark.parametrize("message,total,quantity", (
    ("ต้นทุนรวม 300 บาท ทำได้ 20 ชิ้น", "300", "20"),
    ("total cost 300, quantity 20 units", "300", "20"),
    ("ค่าใช้จ่ายรวม 1,250.75 บาท จำนวน 20.5 หน่วย", "1250.75", "20.5"),
    ("ต้นทุนรวม 300 ทำได้ 20 ชิ้น", "300", "20"),
))
def test_per_unit_complete(message, total, quantity):
    result = parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, message)
    values = by_id(result)
    assert result.status == COMPLETE
    assert values["total_cost"].canonical_decimal == total
    assert values["unit_quantity"].canonical_decimal == quantity
    assert values["total_cost"].currency == ("THB" if "บาท" in message else None)
    assert values["unit_quantity"].unit is not None
    assert verify_canonical_cost_evidence_parse_result(result)


@pytest.mark.parametrize("message,status", (
    ("ต้นทุนรวม 300 บาท", PARTIAL),
    ("ทำได้ 20 ชิ้น", PARTIAL),
    ("300 บาท 20 ชิ้น", NO_EVIDENCE),
    ("ต้นทุนต่อชิ้น 15 บาท", NO_EVIDENCE),
    ("ต้นทุนรวม 300 ต้นทุนรวม 400 ทำได้ 20 ชิ้น", AMBIGUOUS),
    ("ต้นทุนรวม 300 ทำได้ 20 ชิ้น จำนวน 21 ชิ้น", AMBIGUOUS),
    ("ต้นทุนรวม 0 ทำได้ 20 ชิ้น", INVALID),
    ("ต้นทุนรวม -1 ทำได้ 20 ชิ้น", INVALID),
    ("ต้นทุนรวม 300 ทำได้ 0 ชิ้น", INVALID),
    ("ต้นทุนรวม 300 ทำได้ -2 ชิ้น", INVALID),
    ("ต้นทุนรวม 1,2 ทำได้ 20 ชิ้น", INVALID),
    ("ต้นทุนรวม 300 ทำได้ ๒๐ ชิ้น", INVALID),
    ("ต้นทุนรวม 300 จำนวน 20", PARTIAL),
))
def test_per_unit_missing_ambiguous_invalid_and_wrong_unit(message, status):
    assert parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, message).status == status


def test_optional_waste_semantics():
    complete = parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, "ต้นทุนรวม 300 ทำได้ 20 ชิ้น ของเสีย 2 ชิ้น")
    zero = parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, "ต้นทุนรวม 300 ทำได้ 20 ชิ้น waste 0 units")
    absent = parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, "ต้นทุนรวม 300 ทำได้ 20 ชิ้น")
    assert by_id(complete)["waste_or_loss_quantity"].canonical_decimal == "2"
    assert by_id(zero)["waste_or_loss_quantity"].canonical_decimal == "0"
    assert "waste_or_loss_quantity" not in by_id(absent) and absent.status == COMPLETE
    assert parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, "ต้นทุนรวม 300 ทำได้ 20 ชิ้น loss -1 units").status == INVALID
    assert parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, "ต้นทุนรวม 300 ทำได้ 20 ชิ้น waste 1 units loss 2 units").status == AMBIGUOUS
    assert parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, "ต้นทุนรวม 300 ของเสีย 2 ชิ้น").status == PARTIAL


@pytest.mark.parametrize("raw,canonical", (("30", "30"), ("30.500", "30.5"), ("1,250.75", "1250.75"), ("-0", "0")))
def test_decimal_parser(raw, canonical):
    value = parse_canonical_decimal(raw)
    assert value.canonical_decimal == canonical
    assert Decimal(value.canonical_decimal) == Decimal(raw.replace(",", ""))


@pytest.mark.parametrize("raw", ("", "1,2", "12,34", "1,250,00", "1e3", "๑๐", ".5", "01"))
def test_decimal_parser_rejects_noncanonical_forms(raw):
    with pytest.raises(ValueError):
        parse_canonical_decimal(raw)


def test_contract_identity_order_immutability_and_determinism():
    message = "ต้นทุนรวม 300 ทำได้ 20 ชิ้น ของเสีย 2 ชิ้น"
    first = parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, message)
    second = parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, message)
    assert first == second
    assert first.parser_version == CANONICAL_COST_EVIDENCE_PARSER_VERSION
    assert first.parser_scope == CANONICAL_COST_EVIDENCE_PARSER_SCOPE
    assert [item.required_evidence_id for item in first.evidence_values] == ["total_cost", "unit_quantity", "waste_or_loss_quantity"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.status = NO_EVIDENCE
    assert verify_canonical_cost_evidence_parse_result(first)


@pytest.mark.parametrize("skill", ("", "cost.change_analysis", "cost.*", "global", "COST.CHANGE_ANALYSIS.V1", None))
def test_exact_skill_id_required(skill):
    with pytest.raises(ValueError):
        parse_canonical_cost_evidence(skill, "ต้นทุนจาก 30 เป็น 40")
    with pytest.raises(TypeError):
        parse_canonical_cost_evidence(CHANGE_SKILL_ID, None)


def test_strict_replay_rejects_tampering_and_substitution():
    result = parse_canonical_cost_evidence(CHANGE_SKILL_ID, "ต้นทุนจาก 30 เป็น 40 บาท")
    item = result.evidence_values[0]
    mutations = (
        dataclasses.replace(result, parser_version=""),
        dataclasses.replace(result, parser_scope="wrong"),
        dataclasses.replace(result, skill_id=PER_UNIT_SKILL_ID),
        dataclasses.replace(result, raw_message=result.raw_message + "!"),
        dataclasses.replace(result, raw_message_digest="A" * 64),
        dataclasses.replace(result, parse_digest="0" * 63),
        dataclasses.replace(result, status=PARTIAL),
        dataclasses.replace(result, evidence_values=tuple(reversed(result.evidence_values))),
        dataclasses.replace(result, routing_authority=True),
    )
    assert all(not verify_canonical_cost_evidence_parse_result(value) for value in mutations)
    bad_items = (
        dataclasses.replace(item, raw_start=item.raw_start + 1),
        dataclasses.replace(item, raw_text="30.0"),
        dataclasses.replace(item, canonical_decimal="30.0"),
        dataclasses.replace(item, semantic_role="current_cost"),
        dataclasses.replace(item, required_evidence_id="current_cost"),
        dataclasses.replace(item, currency="USD"),
        dataclasses.replace(item, confidence="0.9"),
        dataclasses.replace(item, assumed=True),
        dataclasses.replace(item, user_confirmed=True),
        dataclasses.replace(item, evidence_digest="F" * 64),
    )
    assert all(not verify_canonical_cost_evidence_value(value, result.raw_message, CHANGE_SKILL_ID) for value in bad_items)
    assert not verify_canonical_cost_evidence_value(item, result.raw_message, PER_UNIT_SKILL_ID)


def test_status_precedence_invalid_before_ambiguity():
    result = parse_canonical_cost_evidence(PER_UNIT_SKILL_ID, "ต้นทุนรวม 0 ต้นทุนรวม 300 ทำได้ 20 ชิ้น")
    assert result.status == INVALID
    assert result.reason_codes[0].startswith("INVALID_ROLE:")


def test_rule_registry_and_isolation_source_audit():
    registry = get_canonical_cost_evidence_rule_registry()
    assert registry and len({item[0] for item in registry}) == len(registry)
    path = Path("brain/canonical_cost_evidence_parser.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    forbidden = ("app", "streamlit", "requests", "business_skill_candidate_matcher", "business_skill_evidence_mapper", "business_skill_shadow_selector", "gateway", "runtime")
    assert not any(any(token in name for token in forbidden) for name in imports)
    assert "open(" not in source and "session_state" not in source and "business_memory" not in source
