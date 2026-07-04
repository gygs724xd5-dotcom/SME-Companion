from __future__ import annotations

from typing import Any

from brain.business_knowledge_registry import BusinessKnowledgeRegistry
from brain.knowledge_skill_reference import IssueSeverity, ValidationStatus, as_dict, as_list, issue, status_from_issues
from brain.perspective_frame_registry import PerspectiveFrameRegistry


SKILL_REFERENCE_VALIDATOR_VERSION = "5.9.1"

KNOWN_INTENTS = {
    "analyze_operating_capacity",
    "assess_capacity_readiness",
    "analyze_profit_compression",
    "compare_revenue_and_profit",
    "evaluate_unit_economics",
    "evaluate_startup_cost",
    "estimate_startup_requirements",
    "analyze_inventory_risk",
    "analyze_cash_flow_stress",
    "plan_order_fulfillment",
    "calculate_product_margin",
    "structure_unit_cost_inputs",
    "analyze_sales_decline",
    "evaluate_sales_funnel",
    "identify_dashboard_metrics",
    "define_dashboard_requirements",
}
DERIVED_METRICS_WITH_RULES = {"utilization_rate", "contribution_margin", "gross_margin", "net_margin", "days_of_stock", "contribution_margin_rate"}
APPROVED_ALIASES = {"payment_timing": "receivable_days", "order_volume": "current_order_volume", "fulfillment_time": "average_fulfillment_time"}


def _metadata(skill_or_metadata: Any) -> dict:
    if isinstance(skill_or_metadata, dict) and "metadata" in skill_or_metadata:
        return as_dict(skill_or_metadata.get("metadata"))
    if hasattr(skill_or_metadata, "metadata"):
        return as_dict(skill_or_metadata.metadata)
    if hasattr(skill_or_metadata, "to_dict"):
        data = skill_or_metadata.to_dict()
        if "metadata" in data:
            return as_dict(data.get("metadata"))
    return as_dict(skill_or_metadata)


def validate_skill_references(skill_or_metadata: Any, *, knowledge_registry: BusinessKnowledgeRegistry | None = None, frame_registry: PerspectiveFrameRegistry | None = None) -> dict:
    metadata = _metadata(skill_or_metadata)
    knowledge_registry = knowledge_registry or BusinessKnowledgeRegistry()
    frame_registry = frame_registry or PerspectiveFrameRegistry()
    known_knowledge = {item.knowledge_id: item for item in knowledge_registry.list()}
    known_metrics = {metric for item in known_knowledge.values() for metric in item.metrics + item.required_evidence + item.optional_evidence}
    known_rules = {rule.rule_id: item.knowledge_id for item in known_knowledge.values() for rule in item.relationship_rules}
    known_frames = set(frame_registry.ids())
    issues = []

    refs = as_dict(metadata.get("canonical_references"))
    knowledge = as_dict(refs.get("knowledge"))
    metrics = as_dict(refs.get("metrics"))
    evidence = as_dict(refs.get("evidence"))
    knowledge_ids = as_list(knowledge.get("primary")) + as_list(knowledge.get("secondary"))
    for knowledge_id in knowledge_ids:
        if knowledge_id not in known_knowledge:
            issues.append(issue("UNKNOWN_KNOWLEDGE_ID", IssueSeverity.ERROR.value, "canonical_references.knowledge", raw_value=knowledge_id))

    referenced_knowledge_metrics = {metric for knowledge_id in knowledge_ids if knowledge_id in known_knowledge for metric in known_knowledge[knowledge_id].metrics + known_knowledge[knowledge_id].required_evidence + known_knowledge[knowledge_id].optional_evidence}
    for metric_id in as_list(metrics.get("input")) + as_list(metrics.get("derived")) + as_list(metrics.get("context")):
        canonical_metric = APPROVED_ALIASES.get(metric_id, metric_id)
        if metric_id in APPROVED_ALIASES:
            continue
        if canonical_metric not in known_metrics:
            issues.append(issue("UNKNOWN_METRIC_ID", IssueSeverity.ERROR.value, "canonical_references.metrics", raw_value=metric_id))
        elif knowledge_ids and canonical_metric not in referenced_knowledge_metrics:
            issues.append(issue("METRIC_OUTSIDE_REFERENCED_KNOWLEDGE", IssueSeverity.WARNING.value, "canonical_references.metrics", raw_value=metric_id))
    for metric_id in as_list(metrics.get("derived")):
        if metric_id not in DERIVED_METRICS_WITH_RULES:
            issues.append(issue("MISSING_CANONICAL_DERIVATION", IssueSeverity.ERROR.value, "canonical_references.metrics.derived", raw_value=metric_id))
    for rule_id in as_list(refs.get("relationship_rules")):
        if rule_id not in known_rules:
            issues.append(issue("UNKNOWN_RELATIONSHIP_RULE_ID", IssueSeverity.ERROR.value, "canonical_references.relationship_rules", raw_value=rule_id))
        elif known_rules[rule_id] not in knowledge_ids:
            issues.append(issue("RELATIONSHIP_OUTSIDE_REFERENCED_KNOWLEDGE", IssueSeverity.WARNING.value, "canonical_references.relationship_rules", raw_value=rule_id))
    for frame_id in as_list(refs.get("supported_frames")) + as_list(metadata.get("supported_frames")):
        if frame_id not in known_frames:
            issues.append(issue("UNKNOWN_FRAME_ID", IssueSeverity.ERROR.value, "supported_frames", raw_value=frame_id))
    for intent_id in as_list(refs.get("supported_intents")) + as_list(metadata.get("supported_intents")):
        if intent_id not in KNOWN_INTENTS:
            issues.append(issue("UNKNOWN_INTENT_ID", IssueSeverity.WARNING.value, "supported_intents", raw_value=intent_id))
    metric_or_alias = set(as_list(metrics.get("input")) + as_list(metrics.get("context")) + list(APPROVED_ALIASES))
    for evidence_id in as_list(evidence.get("required")) + as_list(evidence.get("conditionally_required")) + as_list(evidence.get("optional")):
        if evidence_id not in metric_or_alias and evidence_id not in known_metrics:
            issues.append(issue("UNKNOWN_EVIDENCE_ID", IssueSeverity.ERROR.value, "canonical_references.evidence", raw_value=evidence_id))

    return {
        "validation_status": status_from_issues(issues),
        "validation_issues": [item.to_dict() for item in issues],
        "canonical_reference_valid": not any(item.severity in {IssueSeverity.ERROR.value, IssueSeverity.FATAL.value} for item in issues),
        "validator_version": SKILL_REFERENCE_VALIDATOR_VERSION,
    }


def resolve_alias(reference_id: str, aliases: list[dict] | None = None) -> tuple[str, bool]:
    for alias in aliases or []:
        if alias.get("legacy_id") == reference_id and alias.get("approved"):
            return str(alias.get("canonical_id") or reference_id), True
    return reference_id, False
