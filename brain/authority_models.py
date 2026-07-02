from __future__ import annotations

from dataclasses import asdict, dataclass, field


AUTHORITY_CONTEXT_VERSION = "5.4.1"

SALES_AUTHORITY = "sales_authority"
PRICING_AUTHORITY = "pricing_authority"
MARKETING_AUTHORITY = "marketing_authority"
CUSTOMER_SERVICE_AUTHORITY = "customer_service_authority"
FINANCE_AUTHORITY = "finance_authority"
INVENTORY_AUTHORITY = "inventory_authority"
OPERATIONS_AUTHORITY = "operations_authority"
POLICY_AUTHORITY = "policy_authority"
PRINCIPLES_AUTHORITY = "principles_authority"
GENERAL_BUSINESS_AUTHORITY = "general_business_authority"

AUTHORITY_NAMES = {
    SALES_AUTHORITY,
    PRICING_AUTHORITY,
    MARKETING_AUTHORITY,
    CUSTOMER_SERVICE_AUTHORITY,
    FINANCE_AUTHORITY,
    INVENTORY_AUTHORITY,
    OPERATIONS_AUTHORITY,
    POLICY_AUTHORITY,
    PRINCIPLES_AUTHORITY,
    GENERAL_BUSINESS_AUTHORITY,
}

AUTHORITY_CONFIDENCE_VALUES = {"high", "medium", "low", "conflicted"}


@dataclass
class AuthorityContext:
    authority_context_id: str = ""
    business_situation_id: str = ""
    primary_authority: str = GENERAL_BUSINESS_AUTHORITY
    secondary_authorities: list = field(default_factory=list)
    authority_resolution: dict = field(default_factory=dict)
    authority_confidence: str = "low"
    authority_path: list = field(default_factory=list)
    authority_diagnostics: dict = field(default_factory=dict)
    assumptions: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    version: str = AUTHORITY_CONTEXT_VERSION

    def to_dict(self) -> dict:
        return asdict(self)
