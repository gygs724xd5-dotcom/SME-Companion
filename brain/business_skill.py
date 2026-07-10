from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any


DRAFT = "DRAFT"
CONTRACTED = "CONTRACTED"
UNIT_TESTED = "UNIT_TESTED"
SHADOW_AVAILABLE = "SHADOW_AVAILABLE"
ACCEPTANCE_GUARDED = "ACCEPTANCE_GUARDED"
RUNTIME_AUDITED = "RUNTIME_AUDITED"
LIMITED_ACTIVE = "LIMITED_ACTIVE"
STABLE = "STABLE"

SKILL_LIFECYCLE_STATUSES = (
    DRAFT,
    CONTRACTED,
    UNIT_TESTED,
    SHADOW_AVAILABLE,
    ACCEPTANCE_GUARDED,
    RUNTIME_AUDITED,
    LIMITED_ACTIVE,
    STABLE,
)

EXPLANATION = "EXPLANATION"
CALCULATION = "CALCULATION"
DIAGNOSTIC = "DIAGNOSTIC"
COMPARISON = "COMPARISON"
PLANNING = "PLANNING"
CHECKLIST = "CHECKLIST"
DATA_CAPTURE = "DATA_CAPTURE"
WORKFLOW_SUPPORT = "WORKFLOW_SUPPORT"
DECISION_SUPPORT = "DECISION_SUPPORT"
REPORTING = "REPORTING"

SKILL_CATEGORIES = (
    EXPLANATION,
    CALCULATION,
    DIAGNOSTIC,
    COMPARISON,
    PLANNING,
    CHECKLIST,
    DATA_CAPTURE,
    WORKFLOW_SUPPORT,
    DECISION_SUPPORT,
    REPORTING,
)

PRODUCT = "PRODUCT"
INVENTORY = "INVENTORY"
SALES = "SALES"
CUSTOMER = "CUSTOMER"
PRICING = "PRICING"
COST = "COST"
ACCOUNTING = "ACCOUNTING"
MARKETING = "MARKETING"
SUPPLIER = "SUPPLIER"
PURCHASING = "PURCHASING"
RECIPE_PRODUCTION = "RECIPE_PRODUCTION"
OPERATIONS = "OPERATIONS"
HR_STAFF = "HR_STAFF"
DOCUMENTS = "DOCUMENTS"
DASHBOARD_REPORTING = "DASHBOARD_REPORTING"
CASHFLOW = "CASHFLOW"
PROFITABILITY = "PROFITABILITY"
WORKFLOW_ENGINE = "WORKFLOW_ENGINE"
BUSINESS_KNOWLEDGE = "BUSINESS_KNOWLEDGE"
EXECUTIVE_INTELLIGENCE = "EXECUTIVE_INTELLIGENCE"

CANONICAL_BUSINESS_DOMAINS = (
    PRODUCT,
    INVENTORY,
    SALES,
    CUSTOMER,
    PRICING,
    COST,
    ACCOUNTING,
    MARKETING,
    SUPPLIER,
    PURCHASING,
    RECIPE_PRODUCTION,
    OPERATIONS,
    HR_STAFF,
    DOCUMENTS,
    DASHBOARD_REPORTING,
    CASHFLOW,
    PROFITABILITY,
    WORKFLOW_ENGINE,
    BUSINESS_KNOWLEDGE,
    EXECUTIVE_INTELLIGENCE,
)

BUSINESS_SKILL_DIAGNOSTIC_KEYS = (
    "business_skill_profile",
    "business_skill_selected",
    "business_skill_id",
    "business_skill_name",
    "business_skill_domain",
    "business_skill_category",
    "business_skill_confidence",
    "business_skill_required_evidence",
    "business_skill_missing_evidence",
    "business_skill_optional_evidence",
    "business_skill_reasoning_ready",
    "business_skill_blocked_reason",
    "business_skill_follow_up_question",
    "business_skill_shadow_mode",
    "business_skill_active_status",
)


@dataclass(frozen=True)
class RequiredEvidence:
    field_name: str
    field_type: str
    required: bool = True
    source: str = "current_turn_or_business_memory"
    freshness: str = "current_or_recent"
    confidence_required: float = 0.7
    example_values: tuple[str, ...] = ()
    validation_rule: str = ""
    missing_question: str = ""
    can_assume: bool = False
    assumption_default: object | None = None
    sensitive: bool = False
    user_confirmation_required: bool = False


@dataclass(frozen=True)
class BusinessSkill:
    skill_id: str
    skill_version: str
    skill_name: str
    business_domain: str
    business_subdomain: str = ""
    skill_category: str = EXPLANATION
    intent_patterns: tuple[str, ...] = ()
    example_questions: tuple[str, ...] = ()
    supported_situation_types: tuple[str, ...] = ()
    required_evidence: tuple[RequiredEvidence, ...] = ()
    optional_evidence: tuple[RequiredEvidence, ...] = ()
    evidence_quality_rules: tuple[str, ...] = ()
    reasoning_steps: tuple[str, ...] = ()
    calculation_rules: tuple[str, ...] = ()
    business_rules: tuple[str, ...] = ()
    response_template: str = ""
    follow_up_policy: str = "ask_smallest_next_question_only_when_needed"
    tool_requirements: tuple[str, ...] = ()
    memory_requirements: tuple[str, ...] = ()
    confidence_policy: str = ""
    risk_policy: str = ""
    assumptions_policy: str = ""
    diagnostics_contract: tuple[str, ...] = ()
    tests_required: tuple[str, ...] = ()
    active_status: str = CONTRACTED


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _as_tuple(value: Any) -> tuple:
    if value in (None, "", [], {}, ()):
        return ()
    if isinstance(value, tuple):
        return tuple(value)
    if isinstance(value, (list, set)):
        return tuple(value)
    return (value,)


def _to_json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _dataclass_to_dict(value)
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_json_value(item) for key, item in value.items()}
    return value


def _dataclass_to_dict(value: Any) -> dict:
    return {field.name: _to_json_value(getattr(value, field.name)) for field in fields(value)}


def _evidence_defaults() -> dict:
    return _dataclass_to_dict(RequiredEvidence(field_name="", field_type=""))


def _skill_defaults() -> dict:
    return _dataclass_to_dict(BusinessSkill(skill_id="", skill_version="", skill_name="", business_domain=""))


def _normalize_required_evidence(evidence: RequiredEvidence | dict) -> dict:
    normalized = _evidence_defaults()
    if isinstance(evidence, RequiredEvidence):
        normalized.update(_dataclass_to_dict(evidence))
    elif isinstance(evidence, dict):
        normalized.update(_to_json_value(dict(evidence)))
    else:
        normalized["field_name"] = _normalized_text(evidence)

    normalized["field_name"] = _normalized_text(normalized.get("field_name"))
    normalized["field_type"] = _normalized_text(normalized.get("field_type"))
    normalized["required"] = bool(normalized.get("required"))
    normalized["source"] = _normalized_text(normalized.get("source"))
    normalized["freshness"] = _normalized_text(normalized.get("freshness"))
    normalized["example_values"] = list(_as_tuple(normalized.get("example_values")))
    normalized["validation_rule"] = _normalized_text(normalized.get("validation_rule"))
    normalized["missing_question"] = _normalized_text(normalized.get("missing_question"))
    normalized["can_assume"] = bool(normalized.get("can_assume"))
    normalized["sensitive"] = bool(normalized.get("sensitive"))
    normalized["user_confirmation_required"] = bool(normalized.get("user_confirmation_required"))

    try:
        normalized["confidence_required"] = float(normalized.get("confidence_required"))
    except (TypeError, ValueError):
        normalized["confidence_required"] = normalized.get("confidence_required")
    return normalized


def normalize_business_skill(skill: BusinessSkill | dict) -> dict:
    """Return a deterministic JSON-like BusinessSkill dictionary.

    This helper is pure: it does not mutate input, import runtime layers, call
    tools, or generate final user-facing text.
    """
    normalized = _skill_defaults()
    if isinstance(skill, BusinessSkill):
        normalized.update(_dataclass_to_dict(skill))
    elif isinstance(skill, dict):
        normalized.update(_to_json_value(dict(skill)))
    else:
        return normalized

    for key in (
        "skill_id",
        "skill_version",
        "skill_name",
        "business_domain",
        "business_subdomain",
        "skill_category",
        "response_template",
        "follow_up_policy",
        "confidence_policy",
        "risk_policy",
        "assumptions_policy",
        "active_status",
    ):
        normalized[key] = _normalized_text(normalized.get(key))

    for key in (
        "intent_patterns",
        "example_questions",
        "supported_situation_types",
        "evidence_quality_rules",
        "reasoning_steps",
        "calculation_rules",
        "business_rules",
        "tool_requirements",
        "memory_requirements",
        "diagnostics_contract",
        "tests_required",
    ):
        normalized[key] = list(_as_tuple(normalized.get(key)))

    normalized["required_evidence"] = [
        _normalize_required_evidence(item) for item in _as_tuple(normalized.get("required_evidence"))
    ]
    normalized["optional_evidence"] = [
        _normalize_required_evidence(item) for item in _as_tuple(normalized.get("optional_evidence"))
    ]
    return normalized


def validate_required_evidence(evidence: RequiredEvidence | dict) -> dict:
    normalized = _normalize_required_evidence(evidence)
    errors: list[str] = []
    warnings: list[str] = []

    if not normalized["field_name"]:
        errors.append("field_name is required")
    if not normalized["field_type"]:
        errors.append("field_type is required")

    confidence = normalized.get("confidence_required")
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        errors.append("confidence_required must be between 0 and 1")

    if normalized["required"] and not normalized["missing_question"]:
        warnings.append("required evidence should define missing_question")
    if normalized["can_assume"] and not normalized["user_confirmation_required"]:
        warnings.append("assumable evidence without user confirmation should be reviewed")
    if normalized["sensitive"] and normalized["can_assume"]:
        warnings.append("sensitive evidence should not normally be assumable")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "normalized": normalized,
    }


def validate_business_skill(skill: BusinessSkill | dict) -> dict:
    normalized = normalize_business_skill(skill)
    errors: list[str] = []
    warnings: list[str] = []

    if not normalized["skill_id"]:
        errors.append("skill_id is required")
    if not normalized["skill_version"]:
        errors.append("skill_version is required")
    if not normalized["skill_name"]:
        errors.append("skill_name is required")
    if normalized["business_domain"] not in CANONICAL_BUSINESS_DOMAINS:
        errors.append("business_domain must be canonical")
    if normalized["skill_category"] not in SKILL_CATEGORIES:
        errors.append("skill_category must be canonical")
    if normalized["active_status"] not in SKILL_LIFECYCLE_STATUSES:
        errors.append("active_status must be canonical")
    if not normalized["intent_patterns"] and not normalized["example_questions"]:
        warnings.append("skill should define at least one intent_pattern or example_question")
    if normalized["active_status"] in {LIMITED_ACTIVE, STABLE} and not normalized["tests_required"]:
        warnings.append("active or stable skill should define tests_required before activation")

    validated_required = []
    for index, evidence in enumerate(normalized["required_evidence"]):
        result = validate_required_evidence(evidence)
        validated_required.append(result["normalized"])
        errors.extend(f"required_evidence[{index}]: {error}" for error in result["errors"])
        warnings.extend(f"required_evidence[{index}]: {warning}" for warning in result["warnings"])
    normalized["required_evidence"] = validated_required

    validated_optional = []
    for index, evidence in enumerate(normalized["optional_evidence"]):
        result = validate_required_evidence(evidence)
        validated_optional.append(result["normalized"])
        errors.extend(f"optional_evidence[{index}]: {error}" for error in result["errors"])
        warnings.extend(f"optional_evidence[{index}]: {warning}" for warning in result["warnings"])
    normalized["optional_evidence"] = validated_optional

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "normalized": normalized,
    }


def _value_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def determine_skill_evidence_readiness(skill: BusinessSkill | dict, available_evidence: dict | None = None) -> dict:
    normalized = normalize_business_skill(skill)
    evidence_source = dict(available_evidence) if isinstance(available_evidence, dict) else {}
    missing_evidence: list[str] = []
    present_evidence: list[str] = []
    assumable_evidence: list[str] = []
    confidences: list[float] = []

    for evidence in normalized["required_evidence"]:
        field_name = evidence["field_name"]
        confidence = evidence.get("confidence_required")
        if isinstance(confidence, (int, float)):
            confidences.append(float(confidence))

        if field_name in evidence_source and _value_present(evidence_source.get(field_name)):
            present_evidence.append(field_name)
        elif evidence.get("can_assume"):
            assumable_evidence.append(field_name)
        else:
            missing_evidence.append(field_name)

    reasoning_ready = not missing_evidence
    return {
        "reasoning_ready": reasoning_ready,
        "missing_evidence": missing_evidence,
        "present_evidence": present_evidence,
        "assumable_evidence": assumable_evidence,
        "blocked_reason": "" if reasoning_ready else "missing_required_evidence",
        "confidence_floor": min(confidences) if confidences else 1.0,
    }


def build_business_skill_diagnostics(
    skill: BusinessSkill | dict,
    available_evidence: dict | None = None,
    shadow_mode: bool = True,
) -> dict:
    validation = validate_business_skill(skill)
    normalized = validation["normalized"]
    readiness = determine_skill_evidence_readiness(normalized, available_evidence)
    valid = bool(validation["valid"])
    reasoning_ready = bool(readiness["reasoning_ready"])
    confidence = 0.0
    if valid and reasoning_ready:
        confidence = 1.0
    elif valid:
        confidence = 0.6

    follow_up_question = ""
    missing = set(readiness["missing_evidence"])
    for evidence in normalized["required_evidence"]:
        if evidence["field_name"] in missing and evidence.get("missing_question"):
            follow_up_question = evidence["missing_question"]
            break

    return {
        "business_skill_profile": {
            "valid": valid,
            "errors": list(validation["errors"]),
            "warnings": list(validation["warnings"]),
            "readiness": readiness,
        },
        "business_skill_selected": valid,
        "business_skill_id": normalized["skill_id"],
        "business_skill_name": normalized["skill_name"],
        "business_skill_domain": normalized["business_domain"],
        "business_skill_category": normalized["skill_category"],
        "business_skill_confidence": confidence,
        "business_skill_required_evidence": [
            evidence["field_name"] for evidence in normalized["required_evidence"]
        ],
        "business_skill_missing_evidence": list(readiness["missing_evidence"]),
        "business_skill_optional_evidence": [
            evidence["field_name"] for evidence in normalized["optional_evidence"]
        ],
        "business_skill_reasoning_ready": reasoning_ready,
        "business_skill_blocked_reason": readiness["blocked_reason"],
        "business_skill_follow_up_question": follow_up_question,
        "business_skill_shadow_mode": bool(shadow_mode),
        "business_skill_active_status": normalized["active_status"],
    }


def create_cost_change_analysis_skill() -> BusinessSkill:
    return BusinessSkill(
        skill_id="cost.change_analysis.v1",
        skill_version="1.0.0",
        skill_name="Cost Change Analysis",
        business_domain=COST,
        skill_category=CALCULATION,
        intent_patterns=(
            "cost increased",
            "cost decreased",
            "cost changed",
            "cost went up",
            "cost went down",
        ),
        example_questions=(
            "ต้นทุนเพิ่มจาก 30 เป็น 40 บาท กระทบยังไง",
            "แก้ใหม่ ต้นทุนยัง 30 บาทเท่าเดิม",
        ),
        required_evidence=(
            RequiredEvidence(
                field_name="previous_cost",
                field_type="number",
                confidence_required=0.8,
                validation_rule="number",
                missing_question="What was the previous cost?",
            ),
            RequiredEvidence(
                field_name="current_cost",
                field_type="number",
                confidence_required=0.8,
                validation_rule="number",
                missing_question="What is the current cost?",
            ),
        ),
        reasoning_steps=(
            "compare current cost with previous cost",
            "calculate absolute difference",
            "calculate percentage change when previous cost is non-zero",
            "explain business implication",
        ),
        calculation_rules=(
            "absolute_difference = current_cost - previous_cost",
            "percentage_change = absolute_difference / previous_cost when previous_cost is non-zero",
        ),
        business_rules=(
            "do not infer prior or current cost when missing",
            "treat zero previous cost as blocking percentage change calculation",
        ),
        confidence_policy="downgrade when cost evidence is missing, stale, contradictory, or assumed",
        risk_policy="block reasoning when required cost evidence is missing and cannot be assumed",
        assumptions_policy="do not assume financial inputs unless explicitly allowed by evidence contract",
        diagnostics_contract=BUSINESS_SKILL_DIAGNOSTIC_KEYS,
        tests_required=("tests/test_v5151_business_skill.py",),
        active_status=CONTRACTED,
    )
