from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from brain.business_skill import (
    BUSINESS_SKILL_DIAGNOSTIC_KEYS,
    CALCULATION,
    CASHFLOW,
    CHECKLIST,
    COMPARISON,
    CONTRACTED,
    COST,
    CUSTOMER,
    DECISION_SUPPORT,
    DIAGNOSTIC,
    EXPLANATION,
    INVENTORY,
    LIMITED_ACTIVE,
    OPERATIONS,
    PRICING,
    PROFITABILITY,
    REPORTING,
    SALES,
    STABLE,
    BusinessSkill as ContractBusinessSkill,
    RequiredEvidence,
    create_cost_change_analysis_skill,
    validate_business_skill,
)


BUSINESS_SKILL_REGISTRY_VERSION = "5.15.2"

EXPECTED_SEED_SKILL_IDS = (
    "cost.change_analysis.v1",
    "cost.per_unit_calculation.v1",
    "pricing.promotion_margin_check.v1",
    "pricing.basic_price_suggestion.v1",
    "profitability.gross_margin_explanation.v1",
    "inventory.low_stock_explanation.v1",
    "sales.daily_sales_summary.v1",
    "cashflow.warning_explanation.v1",
    "customer.complaint_triage.v1",
    "operations.daily_task_checklist.v1",
)


def _evidence(
    field_name: str,
    field_type: str,
    missing_question: str,
    *,
    source: str = "current_turn_or_business_memory",
    freshness: str = "current_or_recent",
    confidence_required: float = 0.75,
    validation_rule: str = "",
    example_values: tuple[str, ...] = (),
    required: bool = True,
) -> RequiredEvidence:
    return RequiredEvidence(
        field_name=field_name,
        field_type=field_type,
        required=required,
        source=source,
        freshness=freshness,
        confidence_required=confidence_required,
        example_values=example_values,
        validation_rule=validation_rule,
        missing_question=missing_question,
    )


def _contracted_skill(
    *,
    skill_id: str,
    skill_name: str,
    business_domain: str,
    skill_category: str,
    intent_patterns: tuple[str, ...],
    example_questions: tuple[str, ...],
    required_evidence: tuple[RequiredEvidence, ...],
    reasoning_steps: tuple[str, ...],
    business_rules: tuple[str, ...],
    business_subdomain: str = "",
    supported_situation_types: tuple[str, ...] = (),
    optional_evidence: tuple[RequiredEvidence, ...] = (),
    evidence_quality_rules: tuple[str, ...] = (),
    calculation_rules: tuple[str, ...] = (),
    response_template: str = "",
) -> ContractBusinessSkill:
    return ContractBusinessSkill(
        skill_id=skill_id,
        skill_version="1.0.0",
        skill_name=skill_name,
        business_domain=business_domain,
        business_subdomain=business_subdomain,
        skill_category=skill_category,
        intent_patterns=intent_patterns,
        example_questions=example_questions,
        supported_situation_types=supported_situation_types,
        required_evidence=required_evidence,
        optional_evidence=optional_evidence,
        evidence_quality_rules=evidence_quality_rules,
        reasoning_steps=reasoning_steps,
        calculation_rules=calculation_rules,
        business_rules=business_rules,
        response_template=response_template,
        follow_up_policy="ask_smallest_next_question_only_when_needed",
        confidence_policy="downgrade when required or useful evidence is missing, stale, contradictory, or assumed",
        risk_policy="block or narrow claims when evidence is insufficient for the skill scope",
        assumptions_policy="do not invent local business facts; disclose any allowed assumption to downstream layers",
        diagnostics_contract=BUSINESS_SKILL_DIAGNOSTIC_KEYS,
        tests_required=("tests/test_v5152_business_skill_registry.py",),
        active_status=CONTRACTED,
    )


def _create_cost_per_unit_calculation_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="cost.per_unit_calculation.v1",
        skill_name="Cost Per Unit Calculation",
        business_domain=COST,
        business_subdomain="Unit Economics",
        skill_category=CALCULATION,
        intent_patterns=("cost per unit", "unit cost", "calculate unit cost", "ต้นทุนต่อหน่วย"),
        example_questions=(
            "ต้นทุนรวม 1,200 บาท ได้สินค้า 40 ชิ้น ต้นทุนต่อชิ้นเท่าไหร่",
            "ช่วยคิดต้นทุนต่อหน่วยให้หน่อย",
        ),
        required_evidence=(
            _evidence("total_cost", "number", "What is the total cost?", confidence_required=0.8, validation_rule="positive_number"),
            _evidence("unit_quantity", "number", "How many units were produced or bought?", confidence_required=0.8, validation_rule="positive_number"),
        ),
        optional_evidence=(
            _evidence("waste_or_loss_quantity", "number", "How many units were lost or unusable?", required=False, validation_rule="non_negative_number"),
        ),
        reasoning_steps=("confirm total cost", "confirm usable unit quantity", "divide total cost by usable units", "state calculation boundary"),
        calculation_rules=("unit_cost = total_cost / unit_quantity when unit_quantity is greater than zero",),
        business_rules=("do not include selling price in cost per unit", "flag zero or missing quantity as blocked evidence"),
    )


def _create_promotion_margin_check_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="pricing.promotion_margin_check.v1",
        skill_name="Promotion Margin Check",
        business_domain=PRICING,
        business_subdomain="Promotion",
        skill_category=CALCULATION,
        intent_patterns=("promotion margin", "discount margin", "promo profit", "ลดราคาแล้วกำไร"),
        example_questions=(
            "ถ้าลดราคาเหลือ 89 บาท ต้นทุน 55 บาท ยังมีกำไรไหม",
            "โปรนี้เหลือมาร์จิ้นเท่าไหร่",
        ),
        required_evidence=(
            _evidence("regular_or_promo_price", "number", "What price will be charged in the promotion?", confidence_required=0.8, validation_rule="positive_number"),
            _evidence("unit_cost", "number", "What is the unit cost?", confidence_required=0.8, validation_rule="positive_number"),
        ),
        optional_evidence=(
            _evidence("discount_amount", "number", "What discount amount is being offered?", required=False, validation_rule="non_negative_number"),
            _evidence("target_margin", "number", "What margin target should be protected?", required=False, validation_rule="percentage_or_decimal"),
        ),
        reasoning_steps=("compare promotional price to unit cost", "calculate gross margin amount", "calculate margin rate when price is non-zero", "flag if target margin is not met"),
        calculation_rules=(
            "gross_margin_amount = regular_or_promo_price - unit_cost",
            "gross_margin_rate = gross_margin_amount / regular_or_promo_price when price is non-zero",
        ),
        business_rules=("do not approve a promotion when required cost or price evidence is missing", "treat fees and commissions as optional unless provided"),
    )


def _create_basic_price_suggestion_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="pricing.basic_price_suggestion.v1",
        skill_name="Basic Price Suggestion",
        business_domain=PRICING,
        business_subdomain="Price Setting",
        skill_category=DECISION_SUPPORT,
        intent_patterns=("suggest price", "set price", "basic pricing", "ควรขายราคาเท่าไหร่"),
        example_questions=(
            "ต้นทุน 60 บาท ควรตั้งราคาขายประมาณเท่าไหร่",
            "ช่วยแนะนำราคาขายแบบง่าย ๆ",
        ),
        required_evidence=(
            _evidence("unit_cost", "number", "What is the unit cost?", confidence_required=0.8, validation_rule="positive_number"),
        ),
        optional_evidence=(
            _evidence("target_margin", "number", "What margin target should be used?", required=False, validation_rule="percentage_or_decimal"),
            _evidence("competitor_price", "number", "What competitor price should be considered?", required=False, validation_rule="positive_number"),
        ),
        reasoning_steps=("start from confirmed unit cost", "consider target margin if supplied", "compare with competitor price if supplied", "return a bounded suggestion rather than a guarantee"),
        business_rules=("do not present suggested price as market proof", "avoid under-cost suggestions unless explicitly framed as loss leader risk"),
    )


def _create_gross_margin_explanation_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="profitability.gross_margin_explanation.v1",
        skill_name="Gross Margin Explanation",
        business_domain=PROFITABILITY,
        business_subdomain="Gross Margin",
        skill_category=EXPLANATION,
        intent_patterns=("gross margin", "margin meaning", "explain margin", "มาร์จิ้นคืออะไร"),
        example_questions=(
            "กำไรขั้นต้นต่างจากกำไรสุทธิยังไง",
            "ช่วยอธิบาย gross margin ของสินค้านี้",
        ),
        required_evidence=(
            _evidence("selling_price", "number", "What is the selling price?", confidence_required=0.75, validation_rule="positive_number"),
            _evidence("unit_cost", "number", "What is the unit cost?", confidence_required=0.75, validation_rule="positive_number"),
        ),
        optional_evidence=(
            _evidence("sales_channel_fee", "number", "Are there channel fees to consider?", required=False, validation_rule="non_negative_number"),
        ),
        reasoning_steps=("identify price and direct cost", "explain gross profit amount", "explain gross margin rate", "separate gross margin from net profit"),
        business_rules=("do not include overhead unless explicitly provided", "state that gross margin is before operating expenses"),
    )


def _create_low_stock_explanation_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="inventory.low_stock_explanation.v1",
        skill_name="Low Stock Explanation",
        business_domain=INVENTORY,
        business_subdomain="Stock Risk",
        skill_category=EXPLANATION,
        intent_patterns=("low stock", "stock running out", "reorder risk", "ของใกล้หมด"),
        example_questions=(
            "สินค้านี้เหลือ 5 ชิ้น ควรกังวลไหม",
            "ช่วยอธิบายความเสี่ยงของสต็อกต่ำ",
        ),
        required_evidence=(
            _evidence("current_stock_quantity", "number", "How many units are currently in stock?", confidence_required=0.75, validation_rule="non_negative_number"),
        ),
        optional_evidence=(
            _evidence("average_daily_sales", "number", "How many units sell per day on average?", required=False, validation_rule="non_negative_number"),
            _evidence("reorder_lead_time_days", "number", "How many days does restocking take?", required=False, validation_rule="non_negative_number"),
        ),
        reasoning_steps=("confirm current stock", "estimate urgency only when sales pace is available", "explain stockout risk boundary", "identify missing evidence for reorder timing"),
        business_rules=("do not claim a stockout date without sales pace", "treat seasonal spikes as unknown unless provided"),
    )


def _create_daily_sales_summary_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="sales.daily_sales_summary.v1",
        skill_name="Daily Sales Summary",
        business_domain=SALES,
        business_subdomain="Daily Reporting",
        skill_category=REPORTING,
        intent_patterns=("daily sales", "sales summary", "today sales", "สรุปยอดขายวันนี้"),
        example_questions=(
            "วันนี้ขายได้ 8,500 บาท ช่วยสรุปให้หน่อย",
            "ช่วยทำสรุปยอดขายรายวันแบบสั้น ๆ",
        ),
        required_evidence=(
            _evidence("sales_period", "text", "Which day or period should be summarized?", confidence_required=0.7),
            _evidence("total_sales", "number", "What was the total sales amount?", confidence_required=0.75, validation_rule="non_negative_number"),
        ),
        optional_evidence=(
            _evidence("order_count", "number", "How many orders were there?", required=False, validation_rule="non_negative_number"),
            _evidence("top_selling_items", "list", "Which items sold best?", required=False),
        ),
        reasoning_steps=("confirm reporting period", "summarize total sales", "include order count or top items if supplied", "avoid trend claims without comparison data"),
        business_rules=("do not infer missing sales channels", "do not compare to yesterday unless comparison evidence is present"),
    )


def _create_cashflow_warning_explanation_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="cashflow.warning_explanation.v1",
        skill_name="Cashflow Warning Explanation",
        business_domain=CASHFLOW,
        business_subdomain="Cash Risk",
        skill_category=EXPLANATION,
        intent_patterns=("cashflow warning", "cash shortage", "เงินสดไม่พอ", "cash risk"),
        example_questions=(
            "เงินสดเหลือ 20,000 แต่ต้องจ่ายบิล 35,000 อันตรายไหม",
            "ช่วยอธิบายสัญญาณเตือน cashflow",
        ),
        required_evidence=(
            _evidence("available_cash", "number", "How much cash is currently available?", confidence_required=0.8, validation_rule="non_negative_number"),
            _evidence("upcoming_obligations", "number", "How much must be paid soon?", confidence_required=0.8, validation_rule="non_negative_number"),
        ),
        optional_evidence=(
            _evidence("expected_cash_inflows", "number", "How much cash is expected to come in soon?", required=False, validation_rule="non_negative_number"),
            _evidence("obligation_due_date", "date_or_text", "When are the obligations due?", required=False),
        ),
        reasoning_steps=("compare available cash to upcoming obligations", "include expected inflows only when supplied", "explain shortfall or buffer", "avoid banking or legal claims"),
        business_rules=("treat cashflow warnings as owner-attention items", "do not recommend debt or payment delay without more context"),
    )


def _create_customer_complaint_triage_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="customer.complaint_triage.v1",
        skill_name="Customer Complaint Triage",
        business_domain=CUSTOMER,
        business_subdomain="Complaint Handling",
        skill_category=DIAGNOSTIC,
        intent_patterns=("customer complaint", "complaint triage", "ลูกค้าร้องเรียน", "refund issue"),
        example_questions=(
            "ลูกค้าบอกว่าสินค้าเสีย ควรจัดลำดับยังไง",
            "ช่วยแยกความเร่งด่วนของ complaint นี้",
        ),
        required_evidence=(
            _evidence("complaint_summary", "text", "What did the customer complain about?", confidence_required=0.75),
        ),
        optional_evidence=(
            _evidence("customer_impact", "text", "How was the customer affected?", required=False),
            _evidence("order_value", "number", "What is the order value?", required=False, validation_rule="non_negative_number"),
            _evidence("safety_or_legal_risk", "boolean_or_text", "Is there any safety or legal risk?", required=False),
        ),
        reasoning_steps=("identify complaint type", "separate urgency from compensation decision", "flag safety or legal risk if supplied", "suggest next evidence needed for resolution"),
        business_rules=("do not promise refund or compensation", "escalate safety, legal, or public reputation risk to owner review"),
    )


def _create_daily_task_checklist_skill() -> ContractBusinessSkill:
    return _contracted_skill(
        skill_id="operations.daily_task_checklist.v1",
        skill_name="Daily Task Checklist",
        business_domain=OPERATIONS,
        business_subdomain="Daily Operations",
        skill_category=CHECKLIST,
        intent_patterns=("daily checklist", "task checklist", "daily operations", "เช็กลิสต์งานวันนี้"),
        example_questions=(
            "ช่วยทำเช็กลิสต์เปิดร้านวันนี้",
            "วันนี้ทีมควรเช็กงานอะไรบ้าง",
        ),
        required_evidence=(
            _evidence("business_type_or_work_area", "text", "Which business area or work area is this checklist for?", confidence_required=0.7),
        ),
        optional_evidence=(
            _evidence("known_tasks", "list", "Are there known tasks that must be included?", required=False),
            _evidence("staff_count", "number", "How many staff are available?", required=False, validation_rule="non_negative_number"),
        ),
        reasoning_steps=("anchor checklist to business area", "include only high-level operational tasks", "separate must-do tasks from optional context", "avoid assigning staff unless staffing evidence is present"),
        business_rules=("do not mutate workflow or task state", "do not imply completion tracking without runtime support"),
    )


def build_seed_business_skills() -> tuple[ContractBusinessSkill, ...]:
    """Build the deterministic V5.15.2 seed registry entries.

    This is declarative seed data only. Building the tuple does not activate,
    match, execute, route, or render any skill.
    """
    return (
        create_cost_change_analysis_skill(),
        _create_cost_per_unit_calculation_skill(),
        _create_promotion_margin_check_skill(),
        _create_basic_price_suggestion_skill(),
        _create_gross_margin_explanation_skill(),
        _create_low_stock_explanation_skill(),
        _create_daily_sales_summary_skill(),
        _create_cashflow_warning_explanation_skill(),
        _create_customer_complaint_triage_skill(),
        _create_daily_task_checklist_skill(),
    )


def get_business_skill_registry() -> tuple[ContractBusinessSkill, ...]:
    return build_seed_business_skills()


def get_business_skill(skill_id: str) -> ContractBusinessSkill | None:
    normalized = str(skill_id or "").strip()
    for skill in build_seed_business_skills():
        if skill.skill_id == normalized:
            return skill
    return None


def list_business_skills(
    business_domain: str | None = None,
    skill_category: str | None = None,
    active_status: str | None = None,
) -> tuple[ContractBusinessSkill, ...]:
    domain = str(business_domain or "").strip()
    category = str(skill_category or "").strip()
    status = str(active_status or "").strip()
    skills = []
    for skill in build_seed_business_skills():
        if domain and skill.business_domain != domain:
            continue
        if category and skill.skill_category != category:
            continue
        if status and skill.active_status != status:
            continue
        skills.append(skill)
    return tuple(skills)


def _count_by(skills: Iterable[ContractBusinessSkill], field_name: str) -> dict[str, int]:
    return dict(Counter(str(getattr(skill, field_name, "") or "") for skill in skills))


def validate_business_skill_registry(registry: Iterable[ContractBusinessSkill | dict] | None = None) -> dict[str, Any]:
    skills = tuple(build_seed_business_skills() if registry is None else registry)
    errors: list[str] = []
    warnings: list[str] = []
    skill_ids = [str(getattr(skill, "skill_id", "") or (skill.get("skill_id", "") if isinstance(skill, dict) else "")) for skill in skills]
    duplicate_skill_ids = [skill_id for skill_id, count in Counter(skill_ids).items() if skill_id and count > 1]
    invalid_skill_ids: list[str] = []

    if duplicate_skill_ids:
        errors.extend(f"duplicate skill_id: {skill_id}" for skill_id in duplicate_skill_ids)

    for index, skill in enumerate(skills):
        validation = validate_business_skill(skill)
        skill_id = validation["normalized"].get("skill_id") or skill_ids[index] or f"<index:{index}>"
        if not validation["valid"]:
            invalid_skill_ids.append(skill_id)
            errors.extend(f"{skill_id}: {error}" for error in validation["errors"])
        warnings.extend(f"{skill_id}: {warning}" for warning in validation["warnings"])

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "total_skills": len(skills),
        "skill_ids": skill_ids,
        "duplicate_skill_ids": duplicate_skill_ids,
        "invalid_skill_ids": invalid_skill_ids,
        "domain_counts": _count_by(skills, "business_domain"),
        "category_counts": _count_by(skills, "skill_category"),
        "status_counts": _count_by(skills, "active_status"),
    }


# Deprecated compatibility surface for older diagnostics-only tests/modules.
# These adapters are not the V5.15.2 seed registry contract.

REGISTRY_VERSION = "5.1.0"
DEFAULT_SKILL_STATUS = "contracted_seed_adapter"
DEFAULT_SKILL_VERSION = BUSINESS_SKILL_REGISTRY_VERSION


@dataclass(frozen=True)
class BusinessDomain:
    domain_id: str
    domain_name: str
    description: str = ""
    status: str = DEFAULT_SKILL_STATUS
    version: str = DEFAULT_SKILL_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BusinessSkill:
    skill_id: str
    domain_id: str
    domain_name: str
    intent: str
    description: str
    workflow_id: str | None = None
    required_entities: list[Any] = field(default_factory=list)
    required_memory: list[Any] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    reasoning: Any = ""
    response_style: Any = ""
    confidence: Any = ""
    status: str = DEFAULT_SKILL_STATUS
    version: str = DEFAULT_SKILL_VERSION
    skill_name: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _adapt_contract_skill(skill: ContractBusinessSkill) -> BusinessSkill:
    return BusinessSkill(
        skill_id=skill.skill_id,
        domain_id=skill.business_domain,
        domain_name=skill.business_domain.title().replace("_", " "),
        intent="; ".join(skill.intent_patterns),
        description=skill.skill_name,
        required_entities=[evidence.field_name for evidence in skill.required_evidence],
        business_rules=list(skill.business_rules),
        reasoning="; ".join(skill.reasoning_steps),
        confidence=skill.confidence_policy,
        status=skill.active_status,
        version=skill.skill_version,
        skill_name=skill.skill_name,
        diagnostics={
            "source": "v5152_seed_registry_adapter",
            "active_status": skill.active_status,
        },
        metadata={
            "contract_skill_id": skill.skill_id,
            "skill_category": skill.skill_category,
            "example_questions": list(skill.example_questions),
            "tools": list(skill.tool_requirements),
        },
    )


def _legacy_adapter_skills() -> tuple[BusinessSkill, ...]:
    return (
        BusinessSkill(
            skill_id="01.001.customer_asks_price",
            skill_name="Customer asks price",
            domain_id="01",
            domain_name="Sales",
            intent="Customer asks price; price question",
            description="A customer asks how much a product costs.",
            workflow_id="sales_reply",
            required_entities=["product", "price"],
            required_memory=["pricing_strategy"],
            business_rules=["Price clearly when known."],
            reasoning="Answer clearly and protect perceived value.",
            response_style="NORMAL_CHAT",
            confidence="High when product is clear.",
        ),
        BusinessSkill(
            skill_id="01.002.customer_says_expensive",
            skill_name="Customer says expensive",
            domain_id="01",
            domain_name="Sales",
            intent="price objection; expensive",
            description="A customer says the offer is expensive.",
        ),
        BusinessSkill(
            skill_id="01.003.customer_disappears",
            skill_name="Customer disappears",
            domain_id="01",
            domain_name="Sales",
            intent="follow up silent customer",
            description="A customer stopped replying.",
        ),
        BusinessSkill(
            skill_id="01.004.close_sale",
            skill_name="Close sale",
            domain_id="01",
            domain_name="Sales",
            intent="close sale",
            description="Move a qualified customer toward purchase.",
        ),
        BusinessSkill(
            skill_id="01.005.follow_up_customer",
            skill_name="Follow up customer",
            domain_id="01",
            domain_name="Sales",
            intent="follow up customer",
            description="Follow up without pressure.",
        ),
        BusinessSkill(
            skill_id="02.001.create_facebook_post",
            skill_name="Create Facebook post",
            domain_id="02",
            domain_name="Marketing",
            intent="facebook post",
            description="Draft a marketing post.",
        ),
        BusinessSkill(
            skill_id="02.002.create_promotion",
            skill_name="Create promotion",
            domain_id="02",
            domain_name="Marketing",
            intent="promotion",
            description="Frame a promotion.",
        ),
        BusinessSkill(
            skill_id="03.001.shipping_question",
            skill_name="Shipping question",
            domain_id="03",
            domain_name="Customer Service",
            intent="shipping question",
            description="Answer a shipping question.",
        ),
        BusinessSkill(
            skill_id="03.002.payment_question",
            skill_name="Payment question",
            domain_id="03",
            domain_name="Customer Service",
            intent="payment question",
            description="Answer a payment question.",
        ),
        BusinessSkill(
            skill_id="03.003.refund_request",
            skill_name="Refund request",
            domain_id="03",
            domain_name="Customer Service",
            intent="refund request",
            description="Handle a refund request.",
        ),
    )


class SkillRegistry:
    def __init__(self, *, registry_version: str = REGISTRY_VERSION) -> None:
        self.registry_version = registry_version
        self._skills_by_id: dict[str, BusinessSkill] = {}
        self._domains_by_id: dict[str, BusinessDomain] = {}

    def register_domain(self, domain: BusinessDomain) -> BusinessDomain:
        key = domain.domain_id or domain.domain_name
        if not key:
            raise ValueError("domain_id or domain_name is required")
        existing = self._domains_by_id.get(key)
        if existing and existing != domain:
            raise ValueError(f"Duplicate domain registration: {key}")
        self._domains_by_id[key] = domain
        return domain

    def register_skill(self, skill: BusinessSkill | ContractBusinessSkill) -> BusinessSkill:
        if isinstance(skill, ContractBusinessSkill):
            skill = _adapt_contract_skill(skill)
        if not skill.skill_id:
            raise ValueError("skill_id is required")
        if skill.skill_id in self._skills_by_id:
            raise ValueError(f"Duplicate skill registration: {skill.skill_id}")
        self.register_domain(
            BusinessDomain(
                domain_id=skill.domain_id,
                domain_name=skill.domain_name,
                status=skill.status,
                version=skill.version,
            )
        )
        self._skills_by_id[skill.skill_id] = skill
        return skill

    def get_skill(self, skill_id: str) -> BusinessSkill | None:
        normalized = str(skill_id or "").strip()
        if normalized in self._skills_by_id:
            return self._skills_by_id[normalized]
        for skill in self._skills_by_id.values():
            if normalized and normalized == skill.skill_id.split(".")[-1]:
                return skill
        return None

    def find_skills(
        self,
        intent: str | None = None,
        *,
        domain_id: str | None = None,
        domain_name: str | None = None,
    ) -> list[BusinessSkill]:
        query = str(intent or "").lower().strip()
        domain_id = str(domain_id or "").strip()
        domain_name = str(domain_name or "").lower().strip()
        matches = []
        for skill in self._skills_by_id.values():
            if domain_id and skill.domain_id != domain_id:
                continue
            if domain_name and domain_name not in skill.domain_name.lower():
                continue
            if query and query not in " ".join([skill.skill_id, skill.skill_name, skill.intent, skill.description]).lower():
                continue
            matches.append(skill)
        return sorted(matches, key=lambda item: item.skill_id)

    def find_skill(self, intent: str | None = None, *, domain_id: str | None = None, domain_name: str | None = None) -> BusinessSkill | None:
        matches = self.find_skills(intent=intent, domain_id=domain_id, domain_name=domain_name)
        return matches[0] if matches else None

    def list_domains(self) -> list[BusinessDomain]:
        return sorted(self._domains_by_id.values(), key=lambda item: (item.domain_id, item.domain_name))

    def list_skills(self, domain_id: str | None = None, domain_name: str | None = None) -> list[BusinessSkill]:
        return self.find_skills(domain_id=domain_id, domain_name=domain_name)

    def skill_metadata(self, skill_id: str) -> dict[str, Any]:
        skill = self.get_skill(skill_id)
        if not skill:
            return {}
        return {
            "skill_id": skill.skill_id,
            "skill_name": skill.skill_name,
            "domain_id": skill.domain_id,
            "domain_name": skill.domain_name,
            "intent": skill.intent,
            "workflow_id": skill.workflow_id,
            "status": skill.status,
            "version": skill.version,
            "metadata": dict(skill.metadata),
        }

    def diagnostics(self) -> dict[str, Any]:
        return {
            "registry_version": self.registry_version,
            "registered_domains": len(self._domains_by_id),
            "registered_skills": len(self._skills_by_id),
            "domain_ids": [domain.domain_id for domain in self.list_domains()],
            "skill_ids": [skill.skill_id for skill in self.list_skills()],
        }


def create_registry(load_existing: bool = True) -> SkillRegistry:
    registry = SkillRegistry()
    if load_existing:
        for skill in _legacy_adapter_skills():
            registry.register_skill(skill)
    return registry


def get_default_registry() -> SkillRegistry:
    return create_registry(load_existing=True)


def get_skill(skill_id: str) -> BusinessSkill | None:
    return get_default_registry().get_skill(skill_id)


def find_skill(intent: str | None = None, *, domain_id: str | None = None, domain_name: str | None = None) -> BusinessSkill | None:
    return get_default_registry().find_skill(intent=intent, domain_id=domain_id, domain_name=domain_name)


def list_domains() -> list[BusinessDomain]:
    return get_default_registry().list_domains()


def list_skills(domain_id: str | None = None, domain_name: str | None = None) -> list[BusinessSkill]:
    return get_default_registry().list_skills(domain_id=domain_id, domain_name=domain_name)


def registry_diagnostics() -> dict[str, Any]:
    diagnostics = create_registry(load_existing=True).diagnostics()
    diagnostics["business_skill_registry_version"] = BUSINESS_SKILL_REGISTRY_VERSION
    diagnostics["contract_status"] = CONTRACTED
    diagnostics["runtime_active"] = False
    return diagnostics
