from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from brain.authority_models import (
    CUSTOMER_SERVICE_AUTHORITY,
    FINANCE_AUTHORITY,
    GENERAL_BUSINESS_AUTHORITY,
    INVENTORY_AUTHORITY,
    MARKETING_AUTHORITY,
    OPERATIONS_AUTHORITY,
    POLICY_AUTHORITY,
    PRICING_AUTHORITY,
    PRINCIPLES_AUTHORITY,
    SALES_AUTHORITY,
)


AUTHORITY_REGISTRY_VERSION = "5.4.2"

COMMERCIAL_FAMILY = "commercial"
OPERATIONS_FAMILY = "operations"
FINANCIAL_FAMILY = "financial"
CUSTOMER_FAMILY = "customer"
GOVERNANCE_FAMILY = "governance"
GENERAL_FAMILY = "general"


@dataclass(frozen=True)
class AuthorityDefinition:
    authority_id: str
    authority_name: str
    authority_family: str
    description: str
    owns_truth_for: list
    supported_domains: list
    policy_hooks: list
    principle_hooks: list
    risk_lens: list
    reasoning_lens: list
    judgment_hooks: list
    secondary_authority_candidates: list
    version: str = AUTHORITY_REGISTRY_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


AUTHORITY_REGISTRY: dict[str, AuthorityDefinition] = {
    SALES_AUTHORITY: AuthorityDefinition(
        authority_id=SALES_AUTHORITY,
        authority_name="Sales Authority",
        authority_family=COMMERCIAL_FAMILY,
        description="Interprets situations where revenue generation, selling motion, conversion, orders, and closing are the main business truth.",
        owns_truth_for=["sales objective", "conversion path", "order intent", "revenue opportunity"],
        supported_domains=["sales", "lead conversion", "customer purchase intent", "sales planning"],
        policy_hooks=["discount policy", "sales approval rules", "offer eligibility"],
        principle_hooks=["honesty", "customer respect", "avoid exploitation"],
        risk_lens=["overpromising", "misaligned offer", "short-term revenue over trust"],
        reasoning_lens=["conversion reasoning", "offer fit", "buyer readiness"],
        judgment_hooks=["sales recommendation", "next sales action", "conversion tradeoff"],
        secondary_authority_candidates=[PRICING_AUTHORITY, CUSTOMER_SERVICE_AUTHORITY, MARKETING_AUTHORITY],
    ),
    PRICING_AUTHORITY: AuthorityDefinition(
        authority_id=PRICING_AUTHORITY,
        authority_name="Pricing Authority",
        authority_family=COMMERCIAL_FAMILY,
        description="Interprets situations where price, perceived value, discounting, margin, and price objections determine business truth.",
        owns_truth_for=["price meaning", "discount rationale", "margin sensitivity", "value perception"],
        supported_domains=["pricing", "discounting", "margin", "value communication"],
        policy_hooks=["minimum margin policy", "discount policy", "approval limits"],
        principle_hooks=["transparency", "fairness", "avoid deception"],
        risk_lens=["margin erosion", "brand devaluation", "unfair price treatment"],
        reasoning_lens=["value-based pricing", "margin reasoning", "price objection reasoning"],
        judgment_hooks=["pricing recommendation", "discount alternative", "price explanation"],
        secondary_authority_candidates=[FINANCE_AUTHORITY, SALES_AUTHORITY, CUSTOMER_SERVICE_AUTHORITY],
    ),
    MARKETING_AUTHORITY: AuthorityDefinition(
        authority_id=MARKETING_AUTHORITY,
        authority_name="Marketing Authority",
        authority_family=COMMERCIAL_FAMILY,
        description="Interprets situations where campaigns, content, ads, positioning, audience, and demand creation are central.",
        owns_truth_for=["campaign intent", "audience fit", "message positioning", "demand generation"],
        supported_domains=["marketing", "content", "advertising", "promotion", "brand messaging"],
        policy_hooks=["brand voice", "campaign approval", "platform rules"],
        principle_hooks=["honesty", "transparent claims", "avoid false urgency"],
        risk_lens=["misleading claims", "brand mismatch", "audience confusion"],
        reasoning_lens=["audience-message fit", "campaign strategy", "positioning reasoning"],
        judgment_hooks=["campaign recommendation", "content direction", "message risk"],
        secondary_authority_candidates=[SALES_AUTHORITY, PRICING_AUTHORITY, PRINCIPLES_AUTHORITY],
    ),
    CUSTOMER_SERVICE_AUTHORITY: AuthorityDefinition(
        authority_id=CUSTOMER_SERVICE_AUTHORITY,
        authority_name="Customer Service Authority",
        authority_family=CUSTOMER_FAMILY,
        description="Interprets situations where customer relationship, complaint handling, replies, refunds, service recovery, and trust are central.",
        owns_truth_for=["customer relationship context", "service recovery path", "complaint meaning", "reply intent"],
        supported_domains=["customer service", "complaints", "refunds", "customer replies", "service recovery"],
        policy_hooks=["refund policy", "service policy", "escalation policy"],
        principle_hooks=["respect", "fairness", "accountability"],
        risk_lens=["customer trust damage", "reputation harm", "unfair resolution"],
        reasoning_lens=["relationship repair", "customer expectation", "service recovery reasoning"],
        judgment_hooks=["customer reply recommendation", "complaint handling", "trust-preserving action"],
        secondary_authority_candidates=[POLICY_AUTHORITY, PRICING_AUTHORITY, PRINCIPLES_AUTHORITY],
    ),
    FINANCE_AUTHORITY: AuthorityDefinition(
        authority_id=FINANCE_AUTHORITY,
        authority_name="Finance Authority",
        authority_family=FINANCIAL_FAMILY,
        description="Interprets situations where cost, profit, cash flow, accounting, expenses, and financial sustainability own business truth.",
        owns_truth_for=["cost meaning", "profit implication", "cash flow risk", "financial constraint"],
        supported_domains=["finance", "accounting", "cash flow", "profit", "cost calculation"],
        policy_hooks=["spending limits", "approval thresholds", "recordkeeping rules"],
        principle_hooks=["evidence-based advice", "disclose material uncertainty", "accountability"],
        risk_lens=["cash pressure", "false precision", "margin error", "unsustainable commitment"],
        reasoning_lens=["financial reasoning", "unit economics", "cash flow reasoning"],
        judgment_hooks=["financial recommendation", "calculation caution", "profit tradeoff"],
        secondary_authority_candidates=[PRICING_AUTHORITY, OPERATIONS_AUTHORITY, POLICY_AUTHORITY],
    ),
    INVENTORY_AUTHORITY: AuthorityDefinition(
        authority_id=INVENTORY_AUTHORITY,
        authority_name="Inventory Authority",
        authority_family=OPERATIONS_FAMILY,
        description="Interprets situations where stock, shortage, overstock, fulfillment, warehouse, and inventory availability own business truth.",
        owns_truth_for=["stock availability", "shortage impact", "fulfillment constraint", "inventory risk"],
        supported_domains=["inventory", "stock control", "warehouse", "fulfillment", "supply"],
        policy_hooks=["stock policy", "supplier rules", "fulfillment rules"],
        principle_hooks=["customer transparency", "accountability", "responsible constraints"],
        risk_lens=["stockout", "overstock", "waste", "unfulfilled orders"],
        reasoning_lens=["inventory reasoning", "fulfillment constraint reasoning", "capacity reasoning"],
        judgment_hooks=["inventory recommendation", "substitution path", "fulfillment warning"],
        secondary_authority_candidates=[OPERATIONS_AUTHORITY, SALES_AUTHORITY, CUSTOMER_SERVICE_AUTHORITY],
    ),
    OPERATIONS_AUTHORITY: AuthorityDefinition(
        authority_id=OPERATIONS_AUTHORITY,
        authority_name="Operations Authority",
        authority_family=OPERATIONS_FAMILY,
        description="Interprets situations where process, capacity, staffing, execution feasibility, suppliers, and operating constraints own business truth.",
        owns_truth_for=["execution feasibility", "capacity constraint", "process impact", "operational readiness"],
        supported_domains=["operations", "staffing", "capacity", "supplier coordination", "process improvement"],
        policy_hooks=["operating rules", "staff policy", "supplier policy"],
        principle_hooks=["responsibility", "sustainability", "respect for stakeholders"],
        risk_lens=["capacity overload", "quality decline", "execution failure"],
        reasoning_lens=["operational feasibility", "capacity reasoning", "process reasoning"],
        judgment_hooks=["operations recommendation", "execution constraint", "process improvement"],
        secondary_authority_candidates=[INVENTORY_AUTHORITY, FINANCE_AUTHORITY, CUSTOMER_SERVICE_AUTHORITY],
    ),
    POLICY_AUTHORITY: AuthorityDefinition(
        authority_id=POLICY_AUTHORITY,
        authority_name="Policy Authority",
        authority_family=GOVERNANCE_FAMILY,
        description="Interprets situations where organization-specific rules, permissions, constraints, and approval requirements determine what is allowed.",
        owns_truth_for=["organization policy", "approval requirement", "business rule constraint", "permitted action"],
        supported_domains=["policy", "business rules", "compliance constraints", "approval rules"],
        policy_hooks=["all organization policies"],
        principle_hooks=["respect lawful constraints", "accountability", "consistency"],
        risk_lens=["policy violation", "unauthorized commitment", "compliance exposure"],
        reasoning_lens=["policy interpretation", "permission reasoning", "constraint reasoning"],
        judgment_hooks=["policy check", "permission constraint", "required confirmation"],
        secondary_authority_candidates=[PRINCIPLES_AUTHORITY, FINANCE_AUTHORITY, CUSTOMER_SERVICE_AUTHORITY],
    ),
    PRINCIPLES_AUTHORITY: AuthorityDefinition(
        authority_id=PRINCIPLES_AUTHORITY,
        authority_name="Principles Authority",
        authority_family=GOVERNANCE_FAMILY,
        description="Interprets situations where universal principles, selected principle sets, ethical acceptability, and value tradeoffs constrain judgment.",
        owns_truth_for=["ethical acceptability", "principle conflict", "value tradeoff", "universal moral floor"],
        supported_domains=["business principles", "ethics", "trust", "fairness", "responsible business"],
        policy_hooks=["principle set selection", "governance policy"],
        principle_hooks=["all universal principles", "selected principle set"],
        risk_lens=["deception", "exploitation", "hidden uncertainty", "trust damage"],
        reasoning_lens=["principle evaluation", "value-balancing reasoning", "acceptable alternative reasoning"],
        judgment_hooks=["principle rejection", "principled alternative", "trust-preserving constraint"],
        secondary_authority_candidates=[POLICY_AUTHORITY, CUSTOMER_SERVICE_AUTHORITY, MARKETING_AUTHORITY],
    ),
    GENERAL_BUSINESS_AUTHORITY: AuthorityDefinition(
        authority_id=GENERAL_BUSINESS_AUTHORITY,
        authority_name="General Business Authority",
        authority_family=GENERAL_FAMILY,
        description="Interprets broad or uncertain business situations where no specialized authority should claim primary ownership yet.",
        owns_truth_for=["general business context", "broad business help", "uncertain authority fallback"],
        supported_domains=["general business", "business advice", "business context", "open-ended help"],
        policy_hooks=["general business policy"],
        principle_hooks=["universal principles"],
        risk_lens=["premature specialization", "overconfident routing", "generic advice"],
        reasoning_lens=["general business reasoning", "authority discovery", "situation interpretation"],
        judgment_hooks=["broad recommendation", "authority clarification", "safe fallback"],
        secondary_authority_candidates=[SALES_AUTHORITY, FINANCE_AUTHORITY, OPERATIONS_AUTHORITY],
    ),
}


def _as_dict(value: Any) -> dict:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return deepcopy(value)
    return {}


def get_authority_definition(authority_id: str | None) -> dict | None:
    definition = AUTHORITY_REGISTRY.get(str(authority_id or ""))
    return definition.to_dict() if definition else None


def list_authorities() -> list[dict]:
    return [
        AUTHORITY_REGISTRY[authority_id].to_dict()
        for authority_id in sorted(AUTHORITY_REGISTRY)
    ]


def authority_exists(authority_id: str | None) -> bool:
    return str(authority_id or "") in AUTHORITY_REGISTRY


def get_authorities_by_family(family: str | None) -> list[dict]:
    family_id = str(family or "").strip()
    return [
        definition
        for definition in list_authorities()
        if definition.get("authority_family") == family_id
    ]


def get_secondary_authority_candidates(authority_id: str | None) -> list[str]:
    definition = AUTHORITY_REGISTRY.get(str(authority_id or ""))
    if not definition:
        return []
    return list(definition.secondary_authority_candidates)


def enrich_authority_context(authority_context) -> dict:
    context = _as_dict(authority_context)
    primary_authority = context.get("primary_authority")
    primary_definition = get_authority_definition(primary_authority)
    secondary_definitions = [
        definition
        for definition in (
            get_authority_definition(authority_id)
            for authority_id in (context.get("secondary_authorities") or [])
        )
        if definition
    ]
    diagnostics = dict(context.get("authority_diagnostics") or {})
    diagnostics.update(
        {
            "authority_registry_enriched": True,
            "authority_registry_version": AUTHORITY_REGISTRY_VERSION,
            "authority_registry_mode": "diagnostics_only",
            "primary_authority_definition_found": bool(primary_definition),
        }
    )

    enriched = deepcopy(context)
    enriched["authority_diagnostics"] = diagnostics
    enriched["authority_registry"] = {
        "primary_authority_definition": primary_definition,
        "secondary_authority_definitions": secondary_definitions,
    }
    return enriched
