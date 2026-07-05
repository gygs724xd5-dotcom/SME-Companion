from __future__ import annotations

from copy import deepcopy
from typing import Any

from brain.judgment_alternative_comparison import build_candidate_evidence_profiles, compare_alternatives
from brain.judgment_candidate_registry import JudgmentCandidateRegistry, retrieve_judgment_candidates, validate_judgment_candidate_registry
from brain.judgment_contracts import (
    BUSINESS_JUDGMENT_VERSION,
    BusinessJudgment,
    BusinessJudgmentInput,
    BusinessJudgmentResult,
    CandidateReviewStatus,
    CandidateSpecificity,
    CausalClaimLevel,
    ConfidenceClass,
    JudgmentCandidate,
    JudgmentEligibility,
    JudgmentEligibilityStatus,
    JudgmentStatus,
    SupportStrength,
)
from brain.judgment_evidence_weighting import weigh_evidence_for_candidates


BUSINESS_JUDGMENT_RUNTIME_VERSION = "5.10.4"
BUSINESS_JUDGMENT_RUNTIME_SOURCE = "business_judgment_runtime"


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return deepcopy(value)
    if value in (None, "", {}, ()):
        return []
    return [deepcopy(value)]


def _ids(items: list, key: str = "knowledge_id") -> list[str]:
    result = []
    for item in items or []:
        if isinstance(item, dict) and item.get(key):
            result.append(str(item.get(key)))
        elif isinstance(item, str):
            result.append(item)
    return sorted(set(result))


def _metric(value: Any, *, metric_id: str, source: str = "judgment_input", value_type: str = "number", truth: str = "OBSERVED", freshness: str = "CURRENT", timeframe: str = "", unit: str = "", currency: str = "THB", scope: str = "business") -> dict:
    return {
        "metric_id": metric_id,
        "value": value,
        "value_type": value_type,
        "truth_classification": truth,
        "freshness": freshness,
        "timeframe": timeframe,
        "unit": unit,
        "currency": currency if metric_id in {"total_revenue", "net_profit", "unit_cost", "selling_price", "cash_received", "accounts_receivable"} else "",
        "entity_scope": scope,
        "completeness_status": "AVAILABLE_COMPLETE",
        "missing_components": [],
        "source": source,
        "evidence_ids": [f"evidence::{metric_id}"],
    }


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _direction(previous: Any, current: Any) -> str:
    prev = _number(previous)
    curr = _number(current)
    if prev is None or curr is None:
        return "unknown"
    if curr > prev:
        return "increased"
    if curr < prev:
        return "decreased"
    return "stable"


def _flatten_evidence(evidence_package: dict | None, workflow_outputs: dict | None = None) -> dict:
    source = _as_dict(evidence_package)
    metrics: dict[str, dict] = {}
    for key, value in source.items():
        if key in {"previous", "current", "previous_month", "current_month", "yesterday", "today"}:
            continue
        if isinstance(value, list) and len({str(_as_dict(item).get("value")) for item in value if isinstance(item, dict)}) > 1:
            first = _as_dict(value[0])
            metrics[key] = _metric(first.get("value"), metric_id=key, source="conflicting_sources", truth="CONFLICTING")
            metrics[key]["raw_conflicts"] = value
            continue
        if isinstance(value, dict):
            metric = deepcopy(value)
            metric.setdefault("metric_id", key)
            metric.setdefault("truth_classification", "OBSERVED")
            metric.setdefault("freshness", "CURRENT")
            metric.setdefault("completeness_status", "AVAILABLE_COMPLETE")
            metric.setdefault("missing_components", [])
            metric.setdefault("evidence_ids", [f"evidence::{key}"])
            metrics[key] = metric
        elif value not in (None, "", [], {}):
            metrics[key] = _metric(value, metric_id=key)
    previous = _as_dict(source.get("previous") or source.get("previous_month") or source.get("yesterday"))
    current = _as_dict(source.get("current") or source.get("current_month") or source.get("today"))
    if previous or current:
        metrics["analysis_timeframe"] = _metric("comparison", metric_id="analysis_timeframe", value_type="comparison_period", timeframe="matched_period")
    for metric_id in sorted(set(previous) | set(current)):
        if metric_id in metrics:
            continue
        if current.get(metric_id) not in (None, "", [], {}):
            metrics[metric_id] = _metric(current.get(metric_id), metric_id=metric_id, timeframe="current_period")
        if metric_id not in metrics and previous.get(metric_id) not in (None, "", [], {}):
            metrics[metric_id] = _metric(previous.get(metric_id), metric_id=metric_id, freshness="HISTORICAL_COMPARABLE", timeframe="previous_period")
        if previous.get(metric_id) not in (None, "", [], {}) and current.get(metric_id) not in (None, "", [], {}):
            metrics[f"{metric_id}__direction"] = _metric(_direction(previous.get(metric_id), current.get(metric_id)), metric_id=f"{metric_id}__direction", value_type="direction", timeframe="matched_period")
    prev_rev, curr_rev = _number(previous.get("total_revenue")), _number(current.get("total_revenue"))
    prev_orders, curr_orders = _number(previous.get("order_count")), _number(current.get("order_count"))
    if prev_rev is not None and curr_rev is not None and prev_orders and curr_orders:
        prev_aov = round(prev_rev / prev_orders, 3)
        curr_aov = round(curr_rev / curr_orders, 3)
        metrics["average_order_value"] = _metric(curr_aov, metric_id="average_order_value", timeframe="current_period")
        metrics["average_order_value__previous"] = _metric(prev_aov, metric_id="average_order_value__previous", freshness="HISTORICAL_COMPARABLE", timeframe="previous_period")
        metrics["average_order_value__direction"] = _metric(_direction(prev_aov, curr_aov), metric_id="average_order_value__direction", value_type="direction", timeframe="matched_period")
    if "current_stock" in metrics and "average_daily_sales" in metrics:
        stock = _number(metrics["current_stock"].get("value"))
        velocity = _number(metrics["average_daily_sales"].get("value"))
        if stock is not None and velocity:
            metrics["stock_coverage_days"] = _metric(round(stock / velocity, 3), metric_id="stock_coverage_days", unit="day", timeframe="current")
    for key, value in _as_dict(workflow_outputs).items():
        if key == "profit" and value not in (None, "", [], {}):
            metrics["profit_per_unit"] = _metric(value, metric_id="profit_per_unit", source="completed_workflow_result", truth="CALCULATED")
        elif key in {"price", "selling_price"}:
            metrics["selling_price"] = _metric(value, metric_id="selling_price", source="completed_workflow_result", truth="CALCULATED")
        elif key in {"cost", "unit_cost"}:
            metrics["unit_cost"] = _metric(value, metric_id="unit_cost", source="completed_workflow_result", truth="CALCULATED")
    return metrics


def _relationship_rule_ids(rules: list) -> list[str]:
    return sorted({str(item.get("rule_id") if isinstance(item, dict) else item) for item in rules if item})


def _candidate_supported(candidate_id: str, metrics: dict, profile: dict) -> bool:
    if candidate_id.endswith("AVERAGE_ORDER_VALUE_DECLINE"):
        return (
            (metrics.get("average_order_value__direction") or {}).get("value") == "decreased"
            and (metrics.get("net_profit__direction") or {}).get("value") == "decreased"
            and (metrics.get("order_count__direction") or {}).get("value") in {"increased", "stable"}
        )
    if candidate_id.endswith("UNIT_COST_INCREASE"):
        return (
            (metrics.get("unit_cost__direction") or {}).get("value") == "increased"
            and (metrics.get("net_profit__direction") or {}).get("value") == "decreased"
        )
    if candidate_id.endswith("PROFIT_PER_UNIT_OBSERVATION"):
        return (metrics.get("profit_per_unit") or {}).get("value") not in (None, "", [], {})
    if candidate_id.endswith("DEMAND_NEAR_CAPACITY"):
        cap = _number((metrics.get("maximum_capacity") or {}).get("value"))
        orders = _number((metrics.get("current_order_volume") or {}).get("value"))
        return bool(cap and orders is not None and orders / cap >= 0.9 and orders / cap <= 1.0)
    if candidate_id.endswith("DEMAND_EXCEEDS_THROUGHPUT"):
        cap = _number((metrics.get("maximum_capacity") or {}).get("value"))
        orders = _number((metrics.get("current_order_volume") or {}).get("value"))
        return bool(cap and orders is not None and orders / cap > 1.0)
    if candidate_id.endswith("STOCKOUT_EXPOSURE"):
        coverage = _number((metrics.get("stock_coverage_days") or {}).get("value"))
        lead = _number((metrics.get("supplier_lead_time") or {}).get("value"))
        return bool(coverage is not None and lead is not None and coverage < lead)
    if candidate_id.endswith("RECEIVABLE_TIMING_PRESSURE"):
        days = _number((metrics.get("receivable_days") or {}).get("value"))
        ar = _number((metrics.get("accounts_receivable") or {}).get("value"))
        return bool((days and days > 0) or (ar and ar > 0))
    if candidate_id.endswith("TRAFFIC_DECLINE"):
        return (metrics.get("traffic_count__direction") or {}).get("value") == "decreased"
    if candidate_id.endswith("CONVERSION_DECLINE"):
        return (
            (metrics.get("traffic_count__direction") or {}).get("value") in {"stable", "unknown", None}
            and (metrics.get("order_count__direction") or {}).get("value") == "decreased"
            and (metrics.get("conversion_rate__direction") or {}).get("value") == "decreased"
        )
    if candidate_id.endswith("OPERATING_EXPENSE_INCREASE"):
        return (
            (metrics.get("operating_expenses__direction") or {}).get("value") == "increased"
            and (metrics.get("net_profit__direction") or {}).get("value") == "decreased"
        )
    return profile.get("profile_status") == "SUPPORTED"


def _eligibility(judgment_input: BusinessJudgmentInput, metrics: dict) -> JudgmentEligibility:
    if judgment_input.judgment_policy.get("authority_available") is False:
        return JudgmentEligibility(status=JudgmentEligibilityStatus.BLOCKED_BY_AUTHORITY.value, reason="Judgment authority is unavailable.")
    conflicts = _as_list(judgment_input.unresolved_conflicts)
    critical_conflicts = [item for item in conflicts if _as_dict(item).get("severity") in {"CRITICAL", "CONSTITUTIONAL"}]
    if critical_conflicts or any(metric.get("truth_classification") == "CONFLICTING" for metric in metrics.values()):
        return JudgmentEligibility(status=JudgmentEligibilityStatus.BLOCKED_BY_CONFLICT.value, blocking_conflicts=critical_conflicts or ["conflicting_metric"], reason="Critical unresolved conflict blocks Judgment.")
    if not metrics:
        return JudgmentEligibility(status=JudgmentEligibilityStatus.BLOCKED_BY_EVIDENCE.value, missing_requirements=["evidence_package"], reason="No usable Evidence package.")
    missing = []
    if not (judgment_input.primary_skill_id or judgment_input.skill_readiness or judgment_input.judgment_policy.get("analysis_procedure")):
        missing.append("primary_skill_or_analysis_procedure")
    if not (judgment_input.primary_knowledge_ids or judgment_input.secondary_knowledge_ids):
        missing.append("knowledge_reference")
    if missing:
        return JudgmentEligibility(status=JudgmentEligibilityStatus.ELIGIBLE_WITH_LIMITATIONS.value, eligible=True, missing_requirements=missing, allowed_judgment_types=["EXPLANATORY", "CONDITION_ASSESSMENT", "RISK_ASSESSMENT"], reason="Judgment can proceed with limited handoff context.")
    return JudgmentEligibility(eligible=True, status=JudgmentEligibilityStatus.ELIGIBLE.value, allowed_judgment_types=["EXPLANATORY", "COMPARATIVE", "CONDITION_ASSESSMENT", "RISK_ASSESSMENT"], reason="Required Judgment context is available.")


def _invariants() -> dict:
    return {
        "judgment_runtime_created": True,
        "no_arbitrary_cause_generation": True,
        "recommendation_generated": False,
        "decision_made": False,
        "planner_invoked": False,
        "workflow_started_by_judgment": False,
        "tool_called_by_judgment": False,
        "skill_executed_by_judgment": False,
        "business_memory_mutated_by_judgment": False,
        "chat_history_mutated_by_judgment": False,
        "conversation_memory_mutated_by_judgment": False,
        "store_profile_mutated_by_judgment": False,
        "response_committed_by_judgment": False,
        "support_scores_rendered_as_probabilities": False,
    }


def _next_evidence_need(comparison: dict, profiles: list[dict]) -> dict:
    missing = comparison.get("missing_separator_evidence") or []
    if not missing:
        missing = [metric for profile in profiles for metric in profile.get("missing_core_evidence") or []]
    metric = sorted(set(missing))[0] if missing else ""
    if not metric:
        return {}
    return {
        "evidence_id": f"judgment_next_evidence::{metric}",
        "separates_candidate_ids": comparison.get("candidate_ids") or [],
        "expected_resolution": "Improve candidate separation.",
        "user_effort": "LOW",
        "availability": "UNKNOWN",
        "workflow_owned": False,
        "already_asked": False,
        "information_gain_strength": "HIGH",
        "priority": 1,
        "clarification_handoff_required": True,
    }


def build_business_judgment_runtime(judgment_input: dict | BusinessJudgmentInput | None = None) -> dict:
    raw = judgment_input.to_dict() if hasattr(judgment_input, "to_dict") else _as_dict(judgment_input)
    payload = BusinessJudgmentInput(**{key: raw.get(key) for key in BusinessJudgmentInput.__dataclass_fields__ if key in raw})
    selected_knowledge = _ids(payload.primary_knowledge_ids + payload.secondary_knowledge_ids, key="knowledge_id")
    metrics = _flatten_evidence(payload.evidence_package, payload.workflow_outputs)
    eligibility = _eligibility(payload, metrics)
    authority_trace = [
        "Business Judgment follows Knowledge-Skill readiness.",
        "Judgment explains best-supported explanation only.",
        "Decision, Planner, Workflow, Tool, and commit authorities remain blocked.",
    ]
    if not eligibility.eligible and eligibility.status != JudgmentEligibilityStatus.ELIGIBLE_WITH_LIMITATIONS.value:
        result = BusinessJudgmentResult(
            judgment_available=False,
            judgment_status=JudgmentStatus.CONFLICT_BLOCKED.value if eligibility.status == JudgmentEligibilityStatus.BLOCKED_BY_CONFLICT.value else JudgmentStatus.INSUFFICIENT_EVIDENCE.value,
            contradictions=eligibility.blocking_conflicts,
            limitations=[eligibility.reason],
            next_evidence_need={},
            decision_handoff={"ready_for_future_decision": False, "decision_made": False},
            authority_trace=authority_trace,
            constitutional_invariants=_invariants(),
        )
        return {
            **result.to_dict(),
            "eligibility": eligibility.to_dict(),
            "diagnostics": {
                "judgment_runtime_consulted": True,
                "judgment_eligibility_checked": True,
                "judgment_eligibility_status": eligibility.status,
                "judgment_candidate_registry_consulted": False,
                "judgment_selected": False,
                "judgment_status": result.judgment_status,
                "decision_made": False,
                "planner_invoked": False,
                "workflow_started_by_judgment": False,
                "business_memory_mutated_by_judgment": False,
            },
        }
    registry = JudgmentCandidateRegistry()
    retrieval = retrieve_judgment_candidates(
        selected_frame=payload.selected_frame,
        selected_knowledge_ids=selected_knowledge,
        evidence_package=metrics,
        registry=registry,
    )
    definitions = [registry.get(candidate_id).to_dict() for candidate_id in retrieval.get("available_candidate_ids") if registry.get(candidate_id)]
    validation = validate_judgment_candidate_registry(registry)
    weighted = weigh_evidence_for_candidates(metrics, definitions)
    profiles = build_candidate_evidence_profiles(definitions, weighted)
    for profile in profiles:
        if _candidate_supported(profile["candidate_id"], metrics, profile):
            profile["profile_status"] = "SUPPORTED"
            profile["direct_support_strength"] = SupportStrength.STRONG.value if profile.get("evidence_coverage", 0) >= 0.7 else SupportStrength.MODERATE.value
            profile["support_balance"]["support_class"] = profile["direct_support_strength"]
            profile["support_balance"]["net_support"] = max(120, int(profile["support_balance"].get("net_support") or 0))
        elif profile.get("profile_status") == "SUPPORTED":
            profile["profile_status"] = "PARTIALLY_SUPPORTED"
            profile["direct_support_strength"] = SupportStrength.WEAK.value
    comparison = compare_alternatives(profiles, [item.to_dict() for item in registry.conflicts()])
    selected_ids = []
    if comparison.get("coexisting_candidates"):
        selected_ids = comparison.get("coexisting_candidates") or []
        judgment_status = JudgmentStatus.JUDGMENT_SUPPORTED.value
    elif comparison.get("dominant_candidate"):
        selected_ids = [comparison.get("dominant_candidate")]
        judgment_status = JudgmentStatus.JUDGMENT_TENTATIVE.value if comparison.get("selection_margin") != "STRONG_MARGIN" else JudgmentStatus.JUDGMENT_SUPPORTED.value
    elif comparison.get("comparison_status") in {"MULTIPLE_PLAUSIBLE", "INSUFFICIENT_SEPARATION"}:
        judgment_status = JudgmentStatus.MULTIPLE_PLAUSIBLE_EXPLANATIONS.value
    else:
        judgment_status = JudgmentStatus.INSUFFICIENT_EVIDENCE.value
    candidates = []
    definition_by_id = {item.get("candidate_id"): item for item in definitions}
    profile_by_id = {item.get("candidate_id"): item for item in profiles}
    for index, candidate_id in enumerate(comparison.get("ranked_candidates") or [], start=1):
        definition = definition_by_id.get(candidate_id) or {}
        profile = profile_by_id.get(candidate_id) or {}
        candidates.append(JudgmentCandidate(
            candidate_id=candidate_id,
            explanation=definition.get("display_name") or candidate_id,
            knowledge_ids=definition.get("required_knowledge_ids") or [],
            relationship_rule_ids=definition.get("required_relationship_rule_ids") or [],
            required_evidence=definition.get("required_metric_ids") or [],
            supporting_evidence=profile.get("supporting_evidence") or [],
            contradicting_evidence=profile.get("contradicting_evidence") or [],
            missing_evidence=profile.get("missing_core_evidence") or [],
            support_strength=(profile.get("support_balance") or {}).get("support_class") or SupportStrength.INSUFFICIENT.value,
            contradiction_strength=profile.get("contradiction_strength") or SupportStrength.INSUFFICIENT.value,
            evidence_coverage=float(profile.get("evidence_coverage") or 0.0),
            specificity=definition.get("specificity") or CandidateSpecificity.SPECIFIC.value,
            causal_claim_level=definition.get("maximum_claim_level") or CausalClaimLevel.CONTRIBUTING_FACTOR.value,
            status=profile.get("profile_status") or "INSUFFICIENT_EVIDENCE",
            rank=index,
            selection_reason="selected by deterministic support comparison" if candidate_id in selected_ids else "preserved as alternative or diagnostic candidate",
        ).to_dict())
    selected_candidates = [item for item in candidates if item.get("candidate_id") in selected_ids]
    alternatives = [
        {
            "explanation_id": item.get("candidate_id"),
            "description": item.get("explanation"),
            "current_support": item.get("support_strength"),
            "missing_evidence": item.get("missing_evidence") or [],
            "contradiction": item.get("contradicting_evidence") or [],
            "why_not_selected": "coexisting selected" if item.get("candidate_id") in selected_ids else "lower support or missing separator evidence",
            "still_plausible": item.get("status") in {"SUPPORTED", "PARTIALLY_SUPPORTED"} and item.get("candidate_id") not in selected_ids,
        }
        for item in candidates
        if item.get("candidate_id") not in selected_ids
    ][:3]
    support = SupportStrength.STRONG.value if selected_candidates and all(item.get("support_strength") == SupportStrength.STRONG.value for item in selected_candidates) else SupportStrength.MODERATE.value if selected_candidates else SupportStrength.INSUFFICIENT.value
    confidence = ConfidenceClass.MEDIUM_CONFIDENCE.value if selected_candidates else ConfidenceClass.NO_RELIABLE_JUDGMENT.value
    if judgment_status == JudgmentStatus.MULTIPLE_PLAUSIBLE_EXPLANATIONS.value:
        confidence = ConfidenceClass.LOW_CONFIDENCE.value
        support = SupportStrength.WEAK.value
    selected_judgment = BusinessJudgment(
        judgment_id=f"judgment::{payload.active_topic_id or payload.selected_frame or 'context'}::{','.join(selected_ids) or 'none'}",
        judgment_type=definition_by_id.get(selected_ids[0], {}).get("judgment_type") if selected_ids else "EXPLANATORY",
        active_topic=payload.active_topic,
        active_topic_id=payload.active_topic_id,
        selected_frame=payload.selected_frame,
        selected_knowledge_ids=selected_knowledge,
        primary_skill_id=payload.primary_skill_id,
        candidate_explanations=candidates,
        selected_explanation=selected_candidates[0] if len(selected_candidates) == 1 else {"coexisting_candidates": selected_candidates} if selected_candidates else None,
        alternative_explanations=alternatives,
        supporting_evidence=[evidence for candidate in selected_candidates for evidence in candidate.get("supporting_evidence", [])],
        contradicting_evidence=[evidence for candidate in selected_candidates for evidence in candidate.get("contradicting_evidence", [])],
        missing_evidence=[metric for candidate in selected_candidates for metric in candidate.get("missing_evidence", [])],
        unresolved_conflicts=payload.unresolved_conflicts,
        confidence_class=confidence,
        support_strength=support,
        limitation_summary="Material alternatives remain unresolved." if alternatives else "",
        allowed_claims=["observation", "association", "contributing factor", "condition assessment", "risk assessment", "limitation"],
        forbidden_claims=["sole cause", "recommendation", "Decision", "plan", "execution", "PRIMARY_DRIVER", "CONFIRMED_CAUSE"],
        provenance={"candidate_registry_version": registry.version, "candidate_retrieval": retrieval, "registry_validation": validation},
        authority_trace=authority_trace,
    ).to_dict()
    result = BusinessJudgmentResult(
        judgment_available=bool(selected_candidates),
        judgment_status=judgment_status,
        selected_judgment=selected_judgment if selected_candidates else None,
        candidate_judgments=candidates,
        alternative_explanations=alternatives,
        evidence_summary={"metrics": metrics, "weighted_evidence": weighted, "candidate_profiles": profiles, "alternative_comparison": comparison},
        contradictions=[item for item in weighted.get("weights", []) if item.get("weight_class") == "CONFLICTED"],
        limitations=[selected_judgment.get("limitation_summary")] if selected_judgment.get("limitation_summary") else [],
        confidence_class=confidence,
        support_strength=support,
        next_evidence_need=_next_evidence_need(comparison, profiles),
        decision_handoff={"ready_for_future_decision": bool(selected_candidates), "decision_made": False, "recommendation_allowed": False, "planner_allowed": False, "workflow_allowed": False, "tool_allowed": False},
        authority_trace=authority_trace,
        constitutional_invariants=_invariants(),
    )
    return {
        **result.to_dict(),
        "eligibility": eligibility.to_dict(),
        "candidate_retrieval": retrieval,
        "diagnostics": {
            "judgment_runtime_consulted": True,
            "judgment_eligibility_checked": True,
            "judgment_eligibility_status": eligibility.status,
            "judgment_candidate_registry_consulted": True,
            "judgment_candidate_registry_version": registry.version,
            "judgment_candidate_ids_considered": retrieval.get("available_candidate_ids"),
            "judgment_candidate_ids_excluded": retrieval.get("excluded_candidate_ids"),
            "judgment_candidate_count": len(candidates),
            "judgment_selected": bool(selected_candidates),
            "judgment_status": judgment_status,
            "judgment_type": selected_judgment.get("judgment_type"),
            "judgment_support_strength": support,
            "judgment_confidence_class": confidence,
            "judgment_evidence_weighting_consulted": True,
            "evidence_double_count_prevented": bool(weighted.get("dependency_groups")),
            "candidate_evidence_profiles_created": True,
            "alternative_comparison_performed": True,
            "alternative_comparison_status": comparison.get("comparison_status"),
            "dominant_candidate": comparison.get("dominant_candidate"),
            "coexisting_candidates": comparison.get("coexisting_candidates"),
            "plausible_alternatives": [item.get("explanation_id") for item in alternatives if item.get("still_plausible")],
            "selection_margin": comparison.get("selection_margin"),
            "confirmation_bias_guard_applied": True,
            "next_separator_evidence": comparison.get("missing_separator_evidence"),
            "decision_made": False,
            "planner_invoked": False,
            "workflow_started_by_judgment": False,
            "business_memory_mutated_by_judgment": False,
        },
    }


def build_business_judgment_input_from_bridge(*, business_situation: dict | None = None, knowledge_skill_bridge: dict | None = None, conversation_context: dict | None = None, workflow_outputs: dict | None = None) -> dict:
    situation = _as_dict(business_situation)
    diagnostics = _as_dict(situation.get("diagnostics"))
    knowledge = _as_dict(diagnostics.get("knowledge"))
    bridge = _as_dict(knowledge_skill_bridge) or _as_dict(diagnostics.get("knowledge_skill_bridge"))
    judgment_handoff = _as_dict(bridge.get("judgment_handoff"))
    primary = _as_dict(bridge.get("primary_skill_candidate"))
    return BusinessJudgmentInput(
        active_topic=situation.get("business_topic") or "",
        active_topic_id=situation.get("business_topic") or "",
        selected_frame=knowledge.get("selected_frame") or _as_dict(diagnostics.get("perspective")).get("selected_frame") or "UNKNOWN_SITUATION",
        primary_knowledge_ids=_ids(knowledge.get("primary_knowledge")),
        secondary_knowledge_ids=_ids(knowledge.get("secondary_knowledge")),
        primary_skill_id=judgment_handoff.get("primary_skill_id") or primary.get("skill_id") or "",
        skill_readiness=primary.get("evidence_readiness_result") or {},
        applicable_relationship_rules=knowledge.get("applicable_relationship_rules") or [],
        evidence_package=judgment_handoff.get("evidence_package") or knowledge.get("available_metrics") or {},
        truth_runtime_result=_as_dict(diagnostics.get("truth")),
        shared_gaps=bridge.get("merged_evidence_gaps") or [],
        unresolved_conflicts=judgment_handoff.get("conflicting_evidence") or [],
        conversation_context=conversation_context or {},
        workflow_outputs=workflow_outputs or {},
        judgment_policy={"analysis_procedure": bool(primary), "authority_available": True},
    ).to_dict()
