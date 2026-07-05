from __future__ import annotations

from dataclasses import asdict, dataclass, field

from brain.judgment_contracts import ComparisonStatus, SupportStrength, WeightClass


JUDGMENT_ALTERNATIVE_COMPARISON_VERSION = "5.10.2"


@dataclass
class CandidateSupportBalance:
    positive_weight: int = 0
    contradiction_weight: int = 0
    unresolved_weight: int = 0
    net_support: int = 0
    support_class: str = SupportStrength.INSUFFICIENT.value

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CandidateEvidenceProfile:
    candidate_id: str
    supporting_evidence: list = field(default_factory=list)
    contradicting_evidence: list = field(default_factory=list)
    neutral_evidence: list = field(default_factory=list)
    missing_core_evidence: list = field(default_factory=list)
    dependency_groups: list = field(default_factory=list)
    evidence_coverage: float = 0.0
    direct_support_strength: str = SupportStrength.INSUFFICIENT.value
    indirect_support_strength: str = SupportStrength.INSUFFICIENT.value
    contradiction_strength: str = SupportStrength.INSUFFICIENT.value
    assumption_burden: str = "LOW"
    unresolved_conflicts: list = field(default_factory=list)
    support_balance: dict = field(default_factory=dict)
    profile_status: str = "INSUFFICIENT_EVIDENCE"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CandidatePairComparison:
    candidate_a: str
    candidate_b: str
    support_difference: int = 0
    contradiction_difference: int = 0
    evidence_quality_difference: int = 0
    assumption_difference: int = 0
    specificity_difference: int = 0
    coexistence_status: str = "UNKNOWN"
    separator_metrics: list[str] = field(default_factory=list)
    missing_separator_evidence: list[str] = field(default_factory=list)
    preferred_candidate: str = ""
    comparison_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _support_class(net: int, coverage: float, contradicted: bool) -> str:
    if contradicted:
        return SupportStrength.CONTRADICTED.value
    if coverage < 0.4:
        return SupportStrength.INSUFFICIENT.value
    if net >= 150 and coverage >= 0.8:
        return SupportStrength.STRONG.value
    if net >= 90:
        return SupportStrength.MODERATE.value
    if net > 0:
        return SupportStrength.WEAK.value
    return SupportStrength.INSUFFICIENT.value


def build_candidate_evidence_profiles(
    candidate_definitions: list[dict],
    weighted_evidence: dict,
) -> list[dict]:
    weights = weighted_evidence.get("weights") or []
    dependency_groups = weighted_evidence.get("dependency_groups") or []
    profiles = []
    for candidate in candidate_definitions:
        cid = candidate.get("candidate_id")
        required = list(candidate.get("required_metric_ids") or [])
        candidate_weights = [item for item in weights if cid in (item.get("candidate_ids") or [])]
        supporting = [item for item in candidate_weights if item.get("weight_class") not in {WeightClass.NOT_USABLE.value, WeightClass.CONFLICTED.value}]
        conflicted = [item for item in candidate_weights if item.get("weight_class") == WeightClass.CONFLICTED.value]
        missing = [metric for metric in required if metric not in {item.get("metric_id") for item in supporting}]
        positive = sum(int(item.get("effective_weight") or 0) for item in supporting)
        contradiction = sum(int(item.get("effective_weight") or 100) for item in conflicted)
        unresolved = len(missing) * 25
        coverage = 1.0 if not required else round((len(required) - len(missing)) / len(required), 3)
        support_class = _support_class(positive - contradiction - unresolved, coverage, bool(conflicted))
        status = "SUPPORTED" if support_class in {SupportStrength.STRONG.value, SupportStrength.MODERATE.value} else "CONTRADICTED" if conflicted else "PARTIALLY_SUPPORTED" if support_class == SupportStrength.WEAK.value else "INSUFFICIENT_EVIDENCE"
        balance = CandidateSupportBalance(
            positive_weight=positive,
            contradiction_weight=contradiction,
            unresolved_weight=unresolved,
            net_support=positive - contradiction - unresolved,
            support_class=support_class,
        ).to_dict()
        profiles.append(CandidateEvidenceProfile(
            candidate_id=cid,
            supporting_evidence=supporting,
            contradicting_evidence=conflicted,
            missing_core_evidence=missing,
            dependency_groups=[group for group in dependency_groups if set(group.get("evidence_ids") or []).intersection({item.get("evidence_id") for item in candidate_weights})],
            evidence_coverage=coverage,
            direct_support_strength=support_class,
            contradiction_strength=SupportStrength.CONTRADICTED.value if conflicted else SupportStrength.INSUFFICIENT.value,
            assumption_burden="HIGH" if any("value" in item.get("limiting_factors", []) for item in candidate_weights) else "LOW",
            unresolved_conflicts=conflicted,
            support_balance=balance,
            profile_status=status,
        ).to_dict())
    return profiles


def _conflict_lookup(conflicts: list[dict]) -> dict[tuple[str, str], dict]:
    result = {}
    for conflict in conflicts:
        a = conflict.get("candidate_a")
        b = conflict.get("candidate_b")
        result[(a, b)] = conflict
        result[(b, a)] = conflict
    return result


def compare_alternatives(
    profiles: list[dict],
    conflicts: list[dict],
) -> dict:
    ranked = sorted(
        profiles,
        key=lambda item: (
            0 if item.get("profile_status") == "SUPPORTED" else 1,
            -float(item.get("evidence_coverage") or 0.0),
            -int((item.get("support_balance") or {}).get("net_support") or 0),
            item.get("candidate_id") or "",
        ),
    )
    supported = [item for item in ranked if item.get("profile_status") == "SUPPORTED"]
    partial = [item for item in ranked if item.get("profile_status") == "PARTIALLY_SUPPORTED"]
    lookup = _conflict_lookup(conflicts)
    pairwise = []
    for index, a in enumerate(ranked):
        for b in ranked[index + 1:]:
            conflict = lookup.get((a.get("candidate_id"), b.get("candidate_id")), {})
            diff = int((a.get("support_balance") or {}).get("net_support") or 0) - int((b.get("support_balance") or {}).get("net_support") or 0)
            coexist = conflict.get("conflict_type") or "UNKNOWN"
            pairwise.append(CandidatePairComparison(
                candidate_a=a.get("candidate_id"),
                candidate_b=b.get("candidate_id"),
                support_difference=diff,
                coexistence_status=coexist,
                separator_metrics=conflict.get("resolution_metrics") or [],
                missing_separator_evidence=sorted(set((a.get("missing_core_evidence") or []) + (b.get("missing_core_evidence") or []))),
                preferred_candidate=a.get("candidate_id") if diff >= 40 else "",
                comparison_reason="deterministic support and conflict matrix comparison",
            ).to_dict())
    coexisting = []
    if len(supported) > 1:
        for item in supported:
            if all((lookup.get((item.get("candidate_id"), other.get("candidate_id")), {}).get("coexistence_allowed") is not False) for other in supported if other is not item):
                coexisting.append(item.get("candidate_id"))
    dominant = supported[0].get("candidate_id") if supported else ""
    if coexisting:
        status = ComparisonStatus.MULTIPLE_COEXISTING.value
        margin = "NO_MARGIN"
        dominant = ""
    elif len(supported) >= 2:
        first = (supported[0].get("support_balance") or {}).get("net_support") or 0
        second = (supported[1].get("support_balance") or {}).get("net_support") or 0
        delta = int(first) - int(second)
        status = ComparisonStatus.CLEAR_LEADER.value if delta >= 70 else ComparisonStatus.MODERATE_LEADER.value if delta >= 40 else ComparisonStatus.MULTIPLE_PLAUSIBLE.value
        margin = "STRONG_MARGIN" if delta >= 70 else "MODERATE_MARGIN" if delta >= 40 else "NARROW_MARGIN"
        if margin == "NARROW_MARGIN":
            dominant = ""
    elif supported:
        status = ComparisonStatus.MODERATE_LEADER.value
        margin = "MODERATE_MARGIN"
    elif partial:
        status = ComparisonStatus.MULTIPLE_PLAUSIBLE.value if len(partial) > 1 else ComparisonStatus.INSUFFICIENT_SEPARATION.value
        margin = "NO_MARGIN"
    else:
        status = ComparisonStatus.NO_SUPPORTED_CANDIDATE.value
        margin = "NO_MARGIN"
    return {
        "candidate_ids": [item.get("candidate_id") for item in ranked],
        "pairwise_comparisons": pairwise,
        "ranked_candidates": [item.get("candidate_id") for item in ranked],
        "dominant_candidate": dominant,
        "coexisting_candidates": coexisting,
        "unresolved_candidates": [item.get("candidate_id") for item in partial],
        "excluded_candidates": [item.get("candidate_id") for item in ranked if item.get("profile_status") == "CONTRADICTED"],
        "separation_metrics": sorted({metric for pair in pairwise for metric in pair.get("separator_metrics", [])}),
        "missing_separator_evidence": sorted({metric for pair in pairwise for metric in pair.get("missing_separator_evidence", [])}),
        "comparison_status": status,
        "selection_margin": margin,
        "ambiguity_status": "AMBIGUOUS" if status in {ComparisonStatus.MULTIPLE_PLAUSIBLE.value, ComparisonStatus.INSUFFICIENT_SEPARATION.value} else "RESOLVED",
        "version": JUDGMENT_ALTERNATIVE_COMPARISON_VERSION,
    }

