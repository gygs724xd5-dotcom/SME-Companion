from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from brain.judgment_contracts import EvidenceRole, WeightClass


JUDGMENT_EVIDENCE_WEIGHTING_VERSION = "5.10.2"


@dataclass
class JudgmentEvidenceWeight:
    evidence_id: str
    metric_id: str
    candidate_ids: list[str] = field(default_factory=list)
    evidence_role: str = EvidenceRole.CONTEXT_ONLY.value
    truth_strength: str = "UNKNOWN"
    freshness_strength: str = "UNKNOWN"
    completeness_strength: str = "UNKNOWN"
    comparability_strength: str = "UNKNOWN_COMPARABILITY"
    source_strength: str = "UNKNOWN"
    directness_strength: str = "UNRELATED"
    specificity_strength: str = "GENERAL"
    consistency_strength: str = "UNKNOWN"
    independence_strength: str = "INDEPENDENT"
    scope_fit: str = "UNKNOWN"
    timeframe_fit: str = "UNKNOWN"
    assumption_burden: str = "MODERATE"
    contradiction_risk: str = "NONE"
    effective_weight: int = 0
    weight_class: str = WeightClass.NOT_USABLE.value
    limiting_factors: list[str] = field(default_factory=list)
    exclusion_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceDependencyGroup:
    group_id: str
    evidence_ids: list[str]
    dependency_type: str
    canonical_source_ids: list[str] = field(default_factory=list)
    maximum_combined_weight: str = WeightClass.STRONG.value

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceWeightPolicy:
    policy_id: str
    metric_type: str
    truth_weights: dict
    freshness_weights: dict
    completeness_weights: dict
    comparability_weights: dict
    source_adjustments: dict
    directness_adjustments: dict
    conflict_rules: dict
    dependency_rules: dict
    version: str = JUDGMENT_EVIDENCE_WEIGHTING_VERSION

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


def _truth(value: str) -> str:
    text = str(value or "").upper()
    if text in {"VERIFIED", "OBSERVED", "OFFICIAL", "RUNTIME", "DERIVED", "CALCULATED"}:
        return "HIGH"
    if text in {"REPORTED", "HISTORICAL"}:
        return "USABLE_WITH_LIMITS"
    if text in {"INFERRED", "UNVERIFIED"}:
        return "LOW"
    if text in {"CONFLICTING", "CONFLICTED"}:
        return "CONFLICTING"
    return "UNKNOWN"


def _freshness(value: str, metric_id: str) -> str:
    text = str(value or "").upper()
    volatile = metric_id in {"current_stock", "cash_balance", "backlog_count", "daily_order_volume", "current_order_volume", "current_output"}
    if text in {"CURRENT", "CURRENT_TURN", "TODAY", ""}:
        return "CURRENT" if text or volatile else "UNKNOWN"
    if text in {"RECENT", "THIS_MONTH", "THIS_WEEK"}:
        return "RECENT"
    if text in {"HISTORICAL", "HISTORICAL_COMPARABLE", "PREVIOUS"}:
        return "HISTORICAL_COMPARABLE"
    if text in {"STALE", "SUPERSEDED", "WITHDRAWN"}:
        return "STALE"
    return "UNKNOWN"


def _completeness(metric: dict) -> tuple[str, list[str]]:
    missing = list(metric.get("missing_components") or [])
    if metric.get("value") in (None, "", [], {}):
        missing.append("value")
    if metric.get("value_type") == "range":
        missing.append("range_not_collapsed")
    status = str(metric.get("completeness_status") or "").upper()
    if status in {"CONFLICTING", "CONFLICTED"}:
        return "CONFLICTING", missing
    return ("COMPLETE" if not missing and status not in {"AVAILABLE_INCOMPLETE", "MISSING"} else "INCOMPLETE"), missing


def _same_or_unknown(a: Any, b: Any) -> bool:
    return not a or not b or str(a) == str(b)


def _comparability(metric: dict, peers: list[dict]) -> str:
    if not peers:
        return "FULLY_COMPARABLE"
    for peer in peers:
        if not _same_or_unknown(metric.get("unit"), peer.get("unit")):
            return "NOT_COMPARABLE"
        if not _same_or_unknown(metric.get("currency"), peer.get("currency")):
            return "NOT_COMPARABLE"
        if metric.get("timeframe") and peer.get("timeframe") and metric.get("timeframe") != peer.get("timeframe"):
            return "NOT_COMPARABLE"
        if metric.get("entity_scope") and peer.get("entity_scope") and metric.get("entity_scope") != peer.get("entity_scope"):
            return "PARTIALLY_COMPARABLE"
    return "FULLY_COMPARABLE"


def _weight_class(score: int, limiting: list[str]) -> str:
    if "critical_conflict" in limiting:
        return WeightClass.CONFLICTED.value
    if "excluded" in limiting:
        return WeightClass.NOT_USABLE.value
    if score >= 90:
        return WeightClass.DECISIVE.value
    if score >= 70:
        return WeightClass.STRONG.value
    if score >= 45:
        return WeightClass.MODERATE.value
    if score > 0:
        return WeightClass.WEAK.value
    return WeightClass.NOT_USABLE.value


def _evidence_id(metric_id: str, metric: dict) -> str:
    ids = metric.get("evidence_ids") or []
    return str(ids[0]) if ids else f"evidence::{metric_id}"


def _dependency_groups(metrics: dict[str, dict]) -> list[dict]:
    groups = []
    if {"total_revenue", "order_count", "average_order_value"}.issubset(metrics):
        groups.append(EvidenceDependencyGroup(
            group_id="dependency::revenue_orders_aov",
            evidence_ids=[_evidence_id(metric_id, metrics[metric_id]) for metric_id in ("total_revenue", "order_count", "average_order_value")],
            dependency_type="DERIVED",
            canonical_source_ids=["average_order_value"],
            maximum_combined_weight=WeightClass.STRONG.value,
        ).to_dict())
    by_source: dict[str, list[str]] = {}
    for metric_id, metric in metrics.items():
        source = str(metric.get("source") or "")
        if source:
            by_source.setdefault(source, []).append(_evidence_id(metric_id, metric))
    for source, ids in sorted(by_source.items()):
        if len(ids) > 1:
            groups.append(EvidenceDependencyGroup(
                group_id=f"dependency::same_source::{source}",
                evidence_ids=sorted(ids),
                dependency_type="SAME_REPORT",
                canonical_source_ids=[source],
                maximum_combined_weight=WeightClass.STRONG.value,
            ).to_dict())
    return groups


def _normalize_metrics(evidence_package: dict | None) -> dict[str, dict]:
    data = _as_dict(evidence_package)
    metrics = {}
    for key, value in data.items():
        if isinstance(value, dict):
            metric = deepcopy(value)
            metric.setdefault("metric_id", key)
            metrics[key] = metric
        elif value not in (None, "", [], {}):
            metrics[key] = {"metric_id": key, "value": value, "completeness_status": "AVAILABLE_COMPLETE", "truth_classification": "REPORTED"}
    return metrics


def _role(metric_id: str, required_by_metric: dict[str, list[str]], optional_by_metric: dict[str, list[str]]) -> str:
    if metric_id in required_by_metric:
        return EvidenceRole.CORE_SUPPORT.value
    if metric_id in optional_by_metric:
        return EvidenceRole.SECONDARY_SUPPORT.value
    return EvidenceRole.CONTEXT_ONLY.value


def weigh_evidence_for_candidates(
    evidence_package: dict | None,
    candidate_definitions: list[dict],
    *,
    policy_id: str = "financial_comparison_policy",
) -> dict:
    metrics = _normalize_metrics(evidence_package)
    required_by_metric: dict[str, list[str]] = {}
    optional_by_metric: dict[str, list[str]] = {}
    for candidate in candidate_definitions:
        cid = candidate.get("candidate_id")
        for metric_id in candidate.get("required_metric_ids") or []:
            required_by_metric.setdefault(metric_id, []).append(cid)
        for metric_id in candidate.get("optional_metric_ids") or []:
            optional_by_metric.setdefault(metric_id, []).append(cid)
    weights = []
    metric_values = list(metrics.values())
    for metric_id, metric in sorted(metrics.items()):
        candidates = sorted(set(required_by_metric.get(metric_id, []) + optional_by_metric.get(metric_id, [])))
        truth = _truth(metric.get("truth_classification") or metric.get("truth_status"))
        freshness = _freshness(metric.get("freshness"), metric_id)
        completeness, missing = _completeness(metric)
        comparability = _comparability(metric, [peer for peer in metric_values if peer is not metric and peer.get("metric_id") == metric_id])
        limiting = []
        score = 50
        if truth == "HIGH":
            score += 25
        elif truth == "USABLE_WITH_LIMITS":
            score += 10
            limiting.append("reported")
        elif truth == "LOW":
            score -= 20
            limiting.append("low_truth_reliability")
        elif truth == "CONFLICTING":
            score = 0
            limiting.append("critical_conflict")
        else:
            score -= 30
            limiting.append("unknown_truth")
        if freshness == "CURRENT":
            score += 15
        elif freshness == "RECENT":
            score += 8
        elif freshness == "HISTORICAL_COMPARABLE":
            score += 4
            limiting.append("historical")
        elif freshness == "STALE":
            score = 0
            limiting.append("excluded")
            limiting.append("stale")
        if completeness == "COMPLETE":
            score += 15
        else:
            score -= 25
            limiting.extend(missing)
        if comparability == "NOT_COMPARABLE":
            score = 0
            limiting.append("excluded")
            limiting.append("not_comparable")
        elif comparability == "PARTIALLY_COMPARABLE":
            score -= 15
            limiting.append("partial_comparability")
        scope_fit = "MATCH" if metric.get("entity_scope") else "UNKNOWN"
        if metric.get("wrong_scope"):
            score = 0
            scope_fit = "MISMATCH"
            limiting.extend(["excluded", "wrong_scope"])
        score = max(0, min(100, score))
        weights.append(JudgmentEvidenceWeight(
            evidence_id=_evidence_id(metric_id, metric),
            metric_id=metric_id,
            candidate_ids=candidates,
            evidence_role=_role(metric_id, required_by_metric, optional_by_metric),
            truth_strength=truth,
            freshness_strength=freshness,
            completeness_strength=completeness,
            comparability_strength=comparability,
            source_strength="CANONICAL_OR_REPORTED" if metric.get("source") else "UNKNOWN",
            directness_strength="DIRECT" if candidates else "UNRELATED",
            specificity_strength="SPECIFIC" if metric.get("entity_scope") else "GENERAL",
            consistency_strength="CONFLICTING" if truth == "CONFLICTING" else "CONSISTENT",
            independence_strength="DEPENDENCY_CHECKED",
            scope_fit=scope_fit,
            timeframe_fit="MATCH" if metric.get("timeframe") else "UNKNOWN",
            assumption_burden="HIGH" if missing else "LOW",
            contradiction_risk="CRITICAL" if truth == "CONFLICTING" else "NONE",
            effective_weight=score,
            weight_class=_weight_class(score, limiting),
            limiting_factors=sorted(set(limiting)),
            exclusion_reason=";".join(sorted(set(limiting))) if "excluded" in limiting or "critical_conflict" in limiting else "",
        ).to_dict())
    return {
        "weights": weights,
        "excluded_evidence": [item for item in weights if item.get("weight_class") in {WeightClass.NOT_USABLE.value, WeightClass.CONFLICTED.value}],
        "dependency_groups": _dependency_groups(metrics),
        "policy": EvidenceWeightPolicy(
            policy_id=policy_id,
            metric_type="business_metric",
            truth_weights={},
            freshness_weights={},
            completeness_weights={},
            comparability_weights={},
            source_adjustments={},
            directness_adjustments={},
            conflict_rules={"critical_conflict_blocks": True},
            dependency_rules={"derived_metrics_not_double_counted": True},
        ).to_dict(),
        "version": JUDGMENT_EVIDENCE_WEIGHTING_VERSION,
    }
