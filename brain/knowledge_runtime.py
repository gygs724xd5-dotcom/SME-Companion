from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from brain.business_knowledge_registry import (
    BUSINESS_KNOWLEDGE_REGISTRY_VERSION,
    BusinessKnowledgeDefinition,
    BusinessKnowledgeRegistry,
    FRAME_TO_KNOWLEDGE,
    validate_knowledge_registry,
)
from brain.clarification_handoff import ClarificationHandoff
from brain.knowledge_metric_adapter import (
    MetricCompletenessStatus,
    extract_canonical_metrics,
)


KNOWLEDGE_RUNTIME_VERSION = "5.9.0"
KNOWLEDGE_RUNTIME_SOURCE = "knowledge_runtime"


class KnowledgeSelectionTier(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    DEFERRED = "DEFERRED"
    EXCLUDED = "EXCLUDED"


class GapPriorityTier(str, Enum):
    BLOCKING = "BLOCKING"
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class KnowledgeCandidate:
    knowledge_id: str
    selected_by: list[str] = field(default_factory=list)
    frame_matches: list[str] = field(default_factory=list)
    context_matches: list[str] = field(default_factory=list)
    applicability_matches: list[str] = field(default_factory=list)
    metric_matches: list[str] = field(default_factory=list)
    missing_critical_evidence_matches: list[str] = field(default_factory=list)
    relationship_relevance: list[str] = field(default_factory=list)
    specificity_score: float = 0.0
    registry_priority: int = 0
    contradiction_penalty: float = 0.0
    redundancy_penalty: float = 0.0
    misuse_risk: float = 0.0
    support_strength: float = 0.0
    rank: int = 0
    selection_tier: str = KnowledgeSelectionTier.DEFERRED.value
    selection_reason: str = ""
    excluded_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KnowledgeGap:
    gap_id: str
    knowledge_id: str
    metric_id: str
    gap_type: str
    missing_components: list[str] = field(default_factory=list)
    current_partial_value: dict = field(default_factory=dict)
    blocking_relationship_rules: list[str] = field(default_factory=list)
    blocked_capabilities: list[str] = field(default_factory=list)
    importance: float = 0.0
    information_gain: float = 0.0
    user_effort: float = 0.0
    dependency_depth: int = 0
    context_relevance: float = 0.0
    already_asked: bool = False
    already_answered: bool = False
    duplicate_guard_status: str = "not_checked"
    workflow_owned: bool = False
    priority_strength: float = 0.0
    priority_tier: str = GapPriorityTier.LOW.value
    prioritization_reason: str = ""
    question_intent: str = ""
    safe_wording_constraints: list[str] = field(default_factory=list)
    suppressed: bool = False
    suppression_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KnowledgeRuntimeResult:
    knowledge_available: bool = False
    selected_frame: str = "UNKNOWN_SITUATION"
    candidate_frames: list = field(default_factory=list)
    primary_knowledge: list = field(default_factory=list)
    secondary_knowledge: list = field(default_factory=list)
    deferred_knowledge: list = field(default_factory=list)
    excluded_knowledge: list = field(default_factory=list)
    relevant_concepts: list = field(default_factory=list)
    relevant_metrics: list = field(default_factory=list)
    applicable_relationship_rules: list = field(default_factory=list)
    available_metrics: dict = field(default_factory=dict)
    incomplete_metrics: dict = field(default_factory=dict)
    missing_metrics: list = field(default_factory=list)
    knowledge_gaps: list = field(default_factory=list)
    merged_gaps: list = field(default_factory=list)
    suppressed_gaps: list = field(default_factory=list)
    next_knowledge_gap: dict = field(default_factory=dict)
    clarification_handoff: dict = field(default_factory=dict)
    selection_reason: str = ""
    selection_support_strength: float = 0.0
    retrieval_method: str = "none"
    registry_version: str = BUSINESS_KNOWLEDGE_REGISTRY_VERSION
    source_layers: dict = field(default_factory=dict)
    constitutional_invariants: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)
    version: str = KNOWLEDGE_RUNTIME_VERSION
    source: str = KNOWLEDGE_RUNTIME_SOURCE
    runtime_only: bool = True
    diagnostic_only: bool = True

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


def _compact(text: str) -> str:
    return "".join(str(text or "").lower().split())


def _unique(values: list[Any]) -> list:
    result = []
    seen = set()
    for value in values:
        key = str(value)
        if value in (None, "", [], {}) or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _constitutional_invariants(clarification_context_changed: bool = False) -> dict:
    return {
        "knowledge_runtime_created": True,
        "knowledge_retrieval_performed": True,
        "knowledge_selection_performed": True,
        "metric_completeness_interpreted": True,
        "knowledge_gap_prioritization_performed": True,
        "clarification_handoff_created": clarification_context_changed,
        "clarification_context_changed": clarification_context_changed,
        "response_source_for_specific_gap_changed": clarification_context_changed,
        "root_causes_diagnosed": False,
        "business_judgment_produced": False,
        "decision_made": False,
        "recommendations_generated": False,
        "workflow_admission_changed": False,
        "workflow_internal_logic_changed": False,
        "planner_logic_changed": False,
        "execution_engine_changed": False,
        "commit_boundary_changed": False,
        "business_memory_schema_changed": False,
        "business_memory_mutated": False,
        "external_model_called": False,
    }


def _message_text(user_message: str | None, normalized_user_message: str | None, business_situation: dict, conversation_context: dict) -> str:
    values = [
        normalized_user_message or user_message or "",
        business_situation.get("current_focus") or "",
        business_situation.get("objective") or "",
        _as_dict(conversation_context.get("conversation_memory")).get("business_topic") or "",
    ]
    for item in _as_list(business_situation.get("known_evidence")):
        if isinstance(item, dict):
            values.append(str(item.get("summary") or ""))
    return " ".join(str(value) for value in values if value)


def _current_turn_text(user_message: str | None, normalized_user_message: str | None) -> str:
    return str(normalized_user_message or user_message or "")


def _context_matches(definition: BusinessKnowledgeDefinition, text: str, current_text: str, metrics: dict[str, dict]) -> tuple[list[str], list[str], list[str], float]:
    compact_all = _compact(text)
    compact_current = _compact(current_text)
    matches: list[str] = []
    selected_by: list[str] = []
    applicability: list[str] = []
    stale_penalty = 0.0

    def has_any(patterns: list[str], current_only: bool = False) -> bool:
        target = compact_current if current_only else compact_all
        return any(_compact(pattern) in target for pattern in patterns)

    if definition.knowledge_id == "STARTUP_COST_STRUCTURE" and has_any(["อยากเปิดร้าน", "เปิดร้าน", "ใช้ทุน", "ทุนเท่าไร", "startup", "start business"]):
        matches.append("startup_cost_topic")
        selected_by.append("EXPLICIT_USER_TOPIC")
    if definition.knowledge_id == "ORDER_FULFILLMENT" and (has_any(["ทำตามออเดอร์", "รับออเดอร์", "made to order", "preorder"]) or _metric_value(metrics, "business_model") == "made_to_order"):
        matches.append("made_to_order_context")
        selected_by.append("BUSINESS_MODEL")
        applicability.append("Business accepts orders before production or fulfillment.")
    if definition.knowledge_id == "OPERATING_CAPACITY" and (has_any(["ทำได้", "ผลิตได้", "กำลังผลิต", "capacity"]) or "output_quantity" in metrics):
        matches.append("output_quantity_context")
        selected_by.append("AVAILABLE_METRIC" if "output_quantity" in metrics else "EXPLICIT_USER_TOPIC")
    if definition.knowledge_id == "UNIT_ECONOMICS" and has_any(["ขายชูครีม", "ราคา", "ต้นทุน", "ขาย ", "ขายได้", "choux", "cream puff"]):
        matches.append("unit_economics_product_or_price")
        selected_by.append("PRODUCT_CONTEXT")
    if definition.knowledge_id == "INVENTORY_HEALTH" and (has_any(["เหลือ", "สต็อก", "สต๊อก", "ของเหลือ", "stock", "inventory"], current_only=True) or "current_stock" in metrics):
        matches.append("inventory_quantity_context")
        selected_by.append("AVAILABLE_METRIC")
    if definition.knowledge_id == "CASH_CONVERSION" and has_any(["ไม่มีเงินสด", "เงินสดไม่พอ", "ขายได้แต่ไม่มีเงินสด", "cash"]):
        matches.append("cash_conversion_context")
        selected_by.append("EXPLICIT_USER_TOPIC")
    if definition.knowledge_id == "SALES_FUNNEL" and has_any(["ลูกค้าเพิ่ม", "ยอดขายลด", "ยอดขายไม่ดี", "ยอดตก", "ขายไม่ดี", "ขายดี", "ขายได้", "orders", "customers", "sales decline", "sales bad", "dashboard", "metrics"]):
        matches.append("sales_or_customer_context")
        selected_by.append("EXPLICIT_USER_TOPIC")
    if definition.knowledge_id == "PROFITABILITY_STRUCTURE" and has_any(["dashboard", "metrics", "ตัวเลขอะไร", "ควรดูตัวเลข"]):
        matches.append("dashboard_metric_context")
        selected_by.append("EXPLICIT_USER_TOPIC")
    if definition.knowledge_id == "PROFITABILITY_STRUCTURE" and has_any(["กำไรลด", "กำไร", "profit"]):
        matches.append("profitability_context")
        selected_by.append("EXPLICIT_USER_TOPIC")

    if matches and not any(_compact(match) in compact_current for match in matches) and not any(match in {"output_quantity_context", "inventory_quantity_context"} for match in matches):
        stale_penalty = 0.08
    return matches, selected_by, applicability, stale_penalty


def _metric_value(metrics: dict[str, dict], metric_id: str) -> Any:
    return _as_dict(metrics.get(metric_id)).get("value")


def retrieve_knowledge_candidates(
    *,
    selected_frame: str,
    candidate_frames: list | None,
    user_message: str | None,
    normalized_user_message: str | None,
    business_situation: dict,
    metrics: dict[str, dict],
    registry: BusinessKnowledgeRegistry | None = None,
) -> list[dict]:
    registry = registry or BusinessKnowledgeRegistry()
    text = _message_text(user_message, normalized_user_message, business_situation, {})
    current_text = _current_turn_text(user_message, normalized_user_message)
    primary_frame_ids = FRAME_TO_KNOWLEDGE.get(selected_frame, [])
    secondary_frames = [
        str(item.get("frame_id"))
        for item in _as_list(candidate_frames)
        if isinstance(item, dict) and item.get("frame_id") and item.get("frame_id") != selected_frame
    ]
    secondary_frame_ids = _unique([knowledge_id for frame in secondary_frames for knowledge_id in FRAME_TO_KNOWLEDGE.get(frame, [])])
    candidates: list[KnowledgeCandidate] = []
    for definition in registry.list():
        candidate = KnowledgeCandidate(knowledge_id=definition.knowledge_id, registry_priority=definition.priority)
        if definition.knowledge_id in primary_frame_ids:
            candidate.frame_matches.append(selected_frame)
            candidate.selected_by.append("PRIMARY_FRAME")
        if definition.knowledge_id in secondary_frame_ids:
            candidate.frame_matches.extend([frame for frame in secondary_frames if definition.knowledge_id in FRAME_TO_KNOWLEDGE.get(frame, [])])
            candidate.selected_by.append("SECONDARY_FRAME")
        context_matches, selected_by, applicability, stale_penalty = _context_matches(definition, text, current_text, metrics)
        candidate.context_matches = context_matches
        candidate.selected_by.extend(selected_by)
        candidate.applicability_matches = applicability
        candidate.metric_matches = [metric_id for metric_id in definition.metrics if metric_id in metrics]
        for metric_id in candidate.metric_matches:
            metric = _as_dict(metrics.get(metric_id))
            if metric.get("completeness_status") == MetricCompletenessStatus.AVAILABLE_INCOMPLETE.value:
                candidate.selected_by.append("MISSING_CRITICAL_EVIDENCE")
                candidate.missing_critical_evidence_matches.extend(metric.get("missing_components") or [])
        candidate.relationship_relevance = [
            rule.rule_id
            for rule in definition.relationship_rules
            if any(metric_id in metrics or metric_id in candidate.missing_critical_evidence_matches for metric_id in rule.input_metrics)
        ]
        candidate.specificity_score = round(min(1.0, 0.2 + 0.1 * len(candidate.metric_matches) + 0.12 * len(candidate.context_matches) + 0.08 * len(candidate.relationship_relevance)), 2)
        candidate.contradiction_penalty = 1.0 if _contradicted(definition, current_text, metrics) else 0.0
        candidate.misuse_risk = 0.12 if definition.misuse_constraints and not (candidate.frame_matches or candidate.context_matches or candidate.metric_matches) else 0.0
        if definition.knowledge_id == "CASH_CONVERSION" and selected_frame == "PROFIT_COMPRESSION" and "cash_balance" not in metrics:
            candidate.redundancy_penalty = 0.22
        candidate.support_strength = _support_strength(candidate, primary_frame_ids, stale_penalty)
        candidate.selection_reason = _selection_reason(candidate)
        if candidate.support_strength > 0 or candidate.contradiction_penalty:
            candidates.append(candidate)
    return [candidate.to_dict() for candidate in candidates]


def _contradicted(definition: BusinessKnowledgeDefinition, current_text: str, metrics: dict[str, dict]) -> bool:
    compact = _compact(current_text)
    if definition.knowledge_id == "INVENTORY_HEALTH" and any(token in compact for token in ("ไม่มีสต็อก", "ไม่เกี่ยวกับสต็อก", "noinventory")):
        return True
    if definition.knowledge_id == "STARTUP_COST_STRUCTURE" and any(token in compact for token in ("ไม่ได้เปิดร้าน", "notstartup")):
        return True
    return False


def _support_strength(candidate: KnowledgeCandidate, primary_frame_ids: list[str], stale_penalty: float) -> float:
    score = 0.0
    if "PRIMARY_FRAME" in candidate.selected_by:
        score += 0.5
    if "SECONDARY_FRAME" in candidate.selected_by:
        score += 0.28
    if "EXPLICIT_USER_TOPIC" in candidate.selected_by:
        score += 0.52
    if "BUSINESS_MODEL" in candidate.selected_by:
        score += 0.25
    if "PRODUCT_CONTEXT" in candidate.selected_by:
        score += 0.18
    if "AVAILABLE_METRIC" in candidate.selected_by:
        score += 0.32
    if "MISSING_CRITICAL_EVIDENCE" in candidate.selected_by:
        score += 0.2
    score += min(0.18, 0.04 * len(candidate.relationship_relevance))
    score += min(0.08, candidate.registry_priority / 1000)
    score -= candidate.contradiction_penalty
    score -= candidate.redundancy_penalty
    score -= candidate.misuse_risk
    score -= stale_penalty
    return round(max(0.0, min(1.0, score)), 3)


def _selection_reason(candidate: KnowledgeCandidate) -> str:
    if candidate.excluded_reason:
        return candidate.excluded_reason
    reasons = []
    if candidate.frame_matches:
        reasons.append(f"frame match: {', '.join(_unique(candidate.frame_matches))}")
    if candidate.context_matches:
        reasons.append(f"context match: {', '.join(candidate.context_matches)}")
    if candidate.metric_matches:
        reasons.append(f"metric match: {', '.join(candidate.metric_matches)}")
    if candidate.missing_critical_evidence_matches:
        reasons.append("critical evidence is incomplete")
    return "; ".join(reasons) or "low deterministic support"


def rank_knowledge_candidates(candidates: list[dict]) -> list[dict]:
    ranked = sorted(
        deepcopy(candidates),
        key=lambda item: (
            0 if "PRIMARY_FRAME" in item.get("selected_by", []) else 1,
            0 if "EXPLICIT_USER_TOPIC" in item.get("selected_by", []) else 1,
            0 if item.get("missing_critical_evidence_matches") else 1,
            -float(item.get("specificity_score") or 0.0),
            -int(item.get("registry_priority") or 0),
            str(item.get("knowledge_id") or ""),
        ),
    )
    final = []
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
        final.append(item)
    return final


def build_knowledge_selection(candidates: list[dict]) -> dict:
    primary: list[dict] = []
    secondary: list[dict] = []
    deferred: list[dict] = []
    excluded: list[dict] = []
    seen_metric_sets: set[tuple[str, ...]] = set()
    for item in rank_knowledge_candidates(candidates):
        if item.get("contradiction_penalty"):
            item["selection_tier"] = KnowledgeSelectionTier.EXCLUDED.value
            item["excluded_reason"] = "strong_contradiction"
            excluded.append({"knowledge_id": item.get("knowledge_id"), "excluded_reason": item["excluded_reason"]})
            continue
        metric_key = tuple(sorted(item.get("metric_matches") or []))
        if metric_key and metric_key in seen_metric_sets and "PRIMARY_FRAME" not in item.get("selected_by", []):
            item["redundancy_penalty"] = 0.18
            item["selection_tier"] = KnowledgeSelectionTier.DEFERRED.value
            item["selection_reason"] = "deferred as redundant with higher-ranked Knowledge"
            deferred.append(item)
            continue
        if metric_key:
            seen_metric_sets.add(metric_key)
        if len(primary) < 2 and item.get("support_strength", 0) >= 0.5:
            item["selection_tier"] = KnowledgeSelectionTier.PRIMARY.value
            primary.append(item)
        elif len(secondary) < 3 and item.get("support_strength", 0) >= 0.28:
            item["selection_tier"] = KnowledgeSelectionTier.SECONDARY.value
            secondary.append(item)
        else:
            item["selection_tier"] = KnowledgeSelectionTier.DEFERRED.value
            deferred.append(item)
    return {
        "primary": primary[:2],
        "secondary": secondary[:3],
        "deferred": deferred,
        "excluded": excluded,
    }


def _definition_map(registry: BusinessKnowledgeRegistry, selection: dict) -> dict[str, BusinessKnowledgeDefinition]:
    ids = [item.get("knowledge_id") for tier in ("primary", "secondary", "deferred") for item in selection.get(tier, [])]
    return {knowledge_id: registry.get(knowledge_id) for knowledge_id in ids if knowledge_id and registry.get(knowledge_id)}


def identify_relevant_metrics(selection: dict, registry: BusinessKnowledgeRegistry) -> list[str]:
    metrics = []
    for tier in ("primary", "secondary"):
        for item in selection.get(tier, []):
            definition = registry.get(item.get("knowledge_id"))
            if definition:
                metrics.extend(definition.metrics)
                metrics.extend(definition.required_evidence)
    return _unique(metrics)


def _gap_type(metric_id: str, missing: list[str], metric: dict | None = None) -> str:
    metric = metric or {}
    status = metric.get("completeness_status")
    if status == MetricCompletenessStatus.CONFLICTING.value:
        return "CONFLICT_UNRESOLVED"
    if status == MetricCompletenessStatus.HISTORICAL.value:
        return "FRESHNESS_INSUFFICIENT"
    if status == MetricCompletenessStatus.UNVERIFIED.value:
        return "SOURCE_UNVERIFIED"
    if "timeframe" in missing:
        return "TIMEFRAME_MISSING"
    if "unit" in missing:
        return "UNIT_MISSING"
    if "scope" in missing or "unit_basis" in missing:
        return "SCOPE_MISSING"
    if "comparison_period" in missing:
        return "COMPARISON_MISSING"
    if metric_id == "business_model":
        return "BUSINESS_MODEL_UNKNOWN"
    return "VALUE_MISSING"


def _gap_intent(metric_id: str, gap_type: str, knowledge_id: str) -> str:
    if metric_id == "output_time_period" or (metric_id == "output_quantity" and gap_type == "TIMEFRAME_MISSING"):
        return "COMPLETE_CAPACITY_DEFINITION"
    if metric_id in {"analysis_timeframe"}:
        return "ESTABLISH_COMPARISON_PERIOD"
    if metric_id == "total_revenue":
        return "COMPLETE_REVENUE_PERIOD"
    if metric_id == "unit_cost":
        return "COMPLETE_COST_BASIS"
    if metric_id == "business_model":
        return "ESTABLISH_BUSINESS_MODEL"
    if metric_id == "location_model":
        return "ESTABLISH_LOCATION_MODEL"
    if metric_id in {"current_order_volume", "order_count"}:
        return "ESTABLISH_CURRENT_DEMAND"
    if metric_id == "average_daily_sales":
        return "ESTABLISH_SALES_VELOCITY"
    if knowledge_id == "CASH_CONVERSION":
        return "ESTABLISH_PAYMENT_TIMING"
    if gap_type == "CONFLICT_UNRESOLVED":
        return "RESOLVE_METRIC_CONFLICT"
    return "REQUEST_MISSING_VALUE"


def _missing_for_required(metric_id: str, metrics: dict[str, dict]) -> tuple[bool, list[str], dict]:
    if metric_id == "output_time_period" and "output_quantity" in metrics:
        quantity = _as_dict(metrics.get("output_quantity"))
        if "timeframe" in (quantity.get("missing_components") or []) or not quantity.get("timeframe"):
            return True, ["timeframe"], quantity
    metric = _as_dict(metrics.get(metric_id))
    if not metric:
        return True, ["value"], {}
    if metric_id == "cash_balance" and metric.get("value") in {"insufficient", "present"}:
        return False, [], metric
    status = metric.get("completeness_status")
    if status == MetricCompletenessStatus.AVAILABLE_COMPLETE.value:
        return False, [], metric
    return True, list(metric.get("missing_components") or ["value"]), metric


def _relationship_rules_for_metric(definition: BusinessKnowledgeDefinition, metric_id: str, missing: list[str]) -> list[str]:
    rules = []
    for rule in definition.relationship_rules:
        if metric_id in rule.input_metrics or (metric_id == "output_time_period" and "output_time_period" in rule.input_metrics):
            rules.append(rule.rule_id)
    if metric_id == "output_quantity" and "timeframe" in missing:
        rules.append("capacity_requires_time_unit")
    return _unique(rules)


def _priority_tier(score: float, blocking: bool) -> str:
    if blocking or score >= 0.86:
        return GapPriorityTier.BLOCKING.value
    if score >= 0.72:
        return GapPriorityTier.CRITICAL.value
    if score >= 0.58:
        return GapPriorityTier.HIGH.value
    if score >= 0.38:
        return GapPriorityTier.MEDIUM.value
    return GapPriorityTier.LOW.value


def _previous_questions(conversation_context: dict | None) -> list[str]:
    context = _as_dict(conversation_context)
    questions = []
    for item in _as_list(_as_dict(context.get("application_state")).get("conversation", {}).get("chat_history")):
        if isinstance(item, dict) and item.get("role") == "assistant":
            questions.append(str(item.get("content") or ""))
    memory = _as_dict(context.get("conversation_memory"))
    for key in ("last_assistant_reply", "latest_assistant_message"):
        if memory.get(key):
            questions.append(str(memory.get(key)))
    return questions


def _is_recent_duplicate(gap: KnowledgeGap, previous_questions: list[str]) -> bool:
    compact_questions = [_compact(question) for question in previous_questions]
    anchors = {
        "output_time_period": ["ต่อวัน", "ต่อรอบ", "กี่ชั่วโมง", "period"],
        "analysis_timeframe": ["ช่วง", "รายวัน", "รายสัปดาห์", "รายเดือน"],
        "business_model": ["ทำจากบ้าน", "ทำสต๊อก", "หน้าร้าน", "โมเดล"],
        "average_daily_sales": ["ขายได้กี่ชิ้น", "เฉลี่ยต่อวัน"],
        "receivable_days": ["รับเงิน", "เครดิต", "จ่ายเงิน"],
    }
    return any(any(_compact(anchor) in question for anchor in anchors.get(gap.metric_id, [])) for question in compact_questions)


def identify_knowledge_gaps(
    *,
    selection: dict,
    metrics: dict[str, dict],
    registry: BusinessKnowledgeRegistry | None = None,
    conversation_context: dict | None = None,
    workflow_owned_fields: list[str] | None = None,
) -> dict:
    registry = registry or BusinessKnowledgeRegistry()
    workflow_owned = set(workflow_owned_fields or [])
    gaps: list[KnowledgeGap] = []
    previous = _previous_questions(conversation_context)
    for tier_name in ("primary", "secondary"):
        for candidate in selection.get(tier_name, []):
            knowledge_id = candidate.get("knowledge_id")
            definition = registry.get(knowledge_id)
            if not definition:
                continue
            required = list(definition.required_evidence)
            if knowledge_id == "OPERATING_CAPACITY" and "output_quantity" in metrics and "output_time_period" not in required:
                required.insert(1, "output_time_period")
            if knowledge_id == "INVENTORY_HEALTH" and "current_stock" in metrics and "average_daily_sales" not in required:
                required.append("average_daily_sales")
            if knowledge_id == "CASH_CONVERSION":
                required.extend(["receivable_days"])
            for metric_id in _unique(required):
                missing, missing_components, current = _missing_for_required(metric_id, metrics)
                if not missing:
                    continue
                gap_type = _gap_type(metric_id, missing_components, current)
                blocking_rules = _relationship_rules_for_metric(definition, metric_id, missing_components)
                blocking = bool(
                    tier_name == "primary"
                    and (
                        metric_id in {"output_time_period", "analysis_timeframe", "business_model"}
                        or (knowledge_id == "CASH_CONVERSION" and metric_id in {"receivable_days", "accounts_receivable"})
                        or blocking_rules
                    )
                )
                score = 0.35
                score += 0.25 if tier_name == "primary" else 0.08
                score += 0.22 if current else 0.0
                score += 0.18 if blocking else 0.0
                score += 0.03 if knowledge_id == "CASH_CONVERSION" and metric_id in {"receivable_days", "accounts_receivable"} else 0.0
                score += 0.1 if gap_type in {"TIMEFRAME_MISSING", "BUSINESS_MODEL_UNKNOWN", "COMPARISON_MISSING", "CONFLICT_UNRESOLVED"} else 0.0
                user_effort = 0.15 if metric_id in {"output_time_period", "business_model", "analysis_timeframe", "average_daily_sales", "receivable_days"} else 0.35
                score += max(0.0, 0.12 - user_effort / 5)
                gap = KnowledgeGap(
                    gap_id=f"knowledge_gap_{knowledge_id.lower()}_{metric_id}",
                    knowledge_id=knowledge_id,
                    metric_id=metric_id,
                    gap_type=gap_type,
                    missing_components=missing_components,
                    current_partial_value=current,
                    blocking_relationship_rules=blocking_rules,
                    blocked_capabilities=["interpret_capacity"] if metric_id == "output_time_period" else ["interpret_relevant_knowledge"],
                    importance=0.9 if tier_name == "primary" else 0.55,
                    information_gain=0.9 if blocking else 0.55,
                    user_effort=user_effort,
                    dependency_depth=0 if blocking else 1,
                    context_relevance=float(candidate.get("support_strength") or 0.0),
                    workflow_owned=metric_id in workflow_owned,
                    priority_strength=round(max(0.0, min(1.0, score)), 3),
                    priority_tier=_priority_tier(score, blocking),
                    prioritization_reason="definition-blocking gap in primary Knowledge" if blocking else "missing evidence for relevant Knowledge",
                    question_intent=_gap_intent(metric_id, gap_type, knowledge_id),
                    safe_wording_constraints=["Ask for evidence only.", "Do not diagnose.", "Do not recommend action.", "Ask one compact question."],
                )
                if _is_recent_duplicate(gap, previous):
                    gap.already_asked = True
                    gap.duplicate_guard_status = "suppressed_recent_duplicate"
                    gap.suppressed = True
                    gap.suppression_reasons.append("recently_asked")
                if gap.workflow_owned:
                    gap.suppressed = True
                    gap.suppression_reasons.append("workflow_owned")
                gaps.append(gap)
    merged: dict[tuple[str, str], KnowledgeGap] = {}
    merged_notes: list[dict] = []
    for gap in gaps:
        key = (gap.metric_id, gap.gap_type)
        if key not in merged:
            merged[key] = deepcopy(gap)
            continue
        existing = merged[key]
        existing.knowledge_id = existing.knowledge_id
        existing.blocking_relationship_rules = _unique(existing.blocking_relationship_rules + gap.blocking_relationship_rules)
        existing.priority_strength = max(existing.priority_strength, gap.priority_strength)
        existing.priority_tier = _priority_tier(existing.priority_strength, existing.priority_tier == GapPriorityTier.BLOCKING.value or gap.priority_tier == GapPriorityTier.BLOCKING.value)
        existing.suppression_reasons = _unique(existing.suppression_reasons + gap.suppression_reasons)
        existing.suppressed = existing.suppressed and gap.suppressed
        merged_notes.append({"metric_id": gap.metric_id, "merged_from": [existing.knowledge_id, gap.knowledge_id]})
    active = [gap for gap in merged.values() if not gap.suppressed]
    suppressed = [gap for gap in merged.values() if gap.suppressed]
    ordered = sorted(
        active,
        key=lambda gap: (
            0 if gap.priority_tier == GapPriorityTier.BLOCKING.value else 1,
            -gap.priority_strength,
            gap.dependency_depth,
            gap.user_effort,
            gap.metric_id,
            gap.knowledge_id,
        ),
    )
    return {
        "gaps": [gap.to_dict() for gap in ordered],
        "merged_gaps": merged_notes,
        "suppressed_gaps": [gap.to_dict() for gap in suppressed],
        "next_gap": ordered[0].to_dict() if ordered else {},
    }


def _handoff_type(gap: dict) -> str:
    metric_id = gap.get("metric_id")
    gap_type = gap.get("gap_type")
    if metric_id == "output_time_period" or gap_type == "TIMEFRAME_MISSING":
        return "REQUEST_TIMEFRAME"
    if metric_id == "business_model":
        return "CONFIRM_BUSINESS_MODEL"
    if gap_type == "UNIT_MISSING":
        return "REQUEST_UNIT"
    if gap_type == "SCOPE_MISSING":
        return "REQUEST_SCOPE"
    if gap_type == "COMPARISON_MISSING":
        return "REQUEST_COMPARISON_PERIOD"
    if gap_type == "CONFLICT_UNRESOLVED":
        return "RESOLVE_CONFLICT"
    if gap_type == "SOURCE_UNVERIFIED":
        return "VERIFY_SOURCE"
    if gap_type == "FRESHNESS_INSUFFICIENT":
        return "VERIFY_CURRENTNESS"
    if gap:
        return "REQUEST_MISSING_VALUE"
    return "NO_CLARIFICATION_NEEDED"


def _expected_schema(gap: dict) -> dict:
    intent = gap.get("question_intent")
    if intent == "COMPLETE_CAPACITY_DEFINITION":
        return {"type": "one_of_or_short_period", "accepted_fields": ["output_time_period"], "examples": ["day", "batch", "hour", "other_period"]}
    if intent == "ESTABLISH_BUSINESS_MODEL":
        return {"type": "choice", "accepted_fields": ["business_model", "location_model"], "examples": ["home_made_to_order", "stock_ready_to_sell", "storefront"]}
    if intent == "ESTABLISH_SALES_VELOCITY":
        return {"type": "number_with_period", "accepted_fields": ["average_daily_sales", "current_order_volume"]}
    if intent == "ESTABLISH_PAYMENT_TIMING":
        return {"type": "short_text_or_days", "accepted_fields": ["receivable_days", "payment_timing"]}
    return {"type": "short_answer", "accepted_fields": [gap.get("metric_id")]}


def _why_it_matters(gap: dict) -> str:
    intent = gap.get("question_intent")
    if intent == "COMPLETE_CAPACITY_DEFINITION":
        return "Capacity requires both quantity and time period before it can be interpreted."
    if intent == "ESTABLISH_BUSINESS_MODEL":
        return "Startup cost structure changes by business and location model."
    if intent == "ESTABLISH_COMPARISON_PERIOD":
        return "Profit and revenue comparisons require compatible periods."
    if intent == "ESTABLISH_SALES_VELOCITY":
        return "Stock quantity is incomplete without demand or sales velocity."
    if intent == "ESTABLISH_PAYMENT_TIMING":
        return "Cash understanding depends on when sales turn into cash."
    return "This evidence completes the selected Knowledge definition."


def _build_handoff(next_gap: dict, selection: dict, business_situation: dict) -> dict:
    if not next_gap:
        return ClarificationHandoff(handoff_id="clarification_handoff_none").to_dict()
    source_ids = _unique([item.get("knowledge_id") for item in selection.get("primary", []) + selection.get("secondary", [])])
    handoff = ClarificationHandoff(
        handoff_id=f"clarification_handoff_{next_gap.get('gap_id') or 'selected_gap'}",
        source_knowledge_ids=source_ids,
        source_gap_id=next_gap.get("gap_id") or "",
        source_metric_id=next_gap.get("metric_id") or "",
        handoff_type=_handoff_type(next_gap),
        question_intent=next_gap.get("question_intent") or "",
        user_goal=business_situation.get("objective") or "",
        active_business_topic=business_situation.get("business_topic") or "",
        known_context={
            "current_business": business_situation.get("current_business"),
            "current_focus": business_situation.get("current_focus"),
        },
        known_partial_value=next_gap.get("current_partial_value") or {},
        missing_information=next_gap.get("missing_components") or [],
        why_it_matters=_why_it_matters(next_gap),
        blocking_relationship_rules=next_gap.get("blocking_relationship_rules") or [],
        expected_answer_schema=_expected_schema(next_gap),
        suggested_question_focus=next_gap.get("metric_id") or "",
        wording_guidance=["Use natural Thai when the user used Thai.", "Ask the smallest useful question."],
        safe_wording_constraints=next_gap.get("safe_wording_constraints") or [],
        forbidden_claims=["root cause", "insufficient capacity", "recommendation", "decision"],
        conversation_constraints={
            "max_questions": 1,
            "max_requested_fields": 2,
            "preferred_answer_effort": "LOW",
            "avoid_reasking_known_information": True,
            "avoid_multi_part_form": True,
        },
        duplicate_guard={"applied": bool(next_gap.get("already_asked")), "status": next_gap.get("duplicate_guard_status")},
        workflow_coordination={"workflow_owned": bool(next_gap.get("workflow_owned"))},
        fallback_strategy={"if_suppressed": "use_next_ranked_gap"},
        handoff_support_strength=float(next_gap.get("priority_strength") or 0.0),
        authority_trace=["Perspective selects frame.", "Knowledge selects relevant definitions.", "Knowledge Gap Prioritization selects next evidence need.", "Clarification Authority owns wording."],
    )
    return handoff.to_dict()


def build_knowledge_runtime(
    *,
    user_message: str | None = None,
    normalized_user_message: str | None = None,
    business_situation: dict | None = None,
    perspective_runtime: dict | None = None,
    evidence_runtime: dict | None = None,
    truth_runtime: dict | None = None,
    conversation_context: dict | None = None,
    structured_business_data: dict | None = None,
    workflow_owned_fields: list[str] | None = None,
) -> dict:
    situation = _as_dict(business_situation)
    perspective = _as_dict(perspective_runtime) or _as_dict(_as_dict(situation.get("diagnostics")).get("perspective"))
    registry = BusinessKnowledgeRegistry()
    selected_frame = perspective.get("selected_frame") or "UNKNOWN_SITUATION"
    candidate_frames = perspective.get("candidate_frames") or []
    metrics = extract_canonical_metrics(
        user_message=user_message,
        normalized_user_message=normalized_user_message,
        business_situation=situation,
        evidence_runtime=evidence_runtime,
        truth_runtime=truth_runtime,
        conversation_context=conversation_context,
        structured_business_data=structured_business_data,
    )
    candidates = retrieve_knowledge_candidates(
        selected_frame=selected_frame,
        candidate_frames=candidate_frames,
        user_message=user_message,
        normalized_user_message=normalized_user_message,
        business_situation=situation,
        metrics=metrics,
        registry=registry,
    )
    selection = build_knowledge_selection(candidates)
    gaps = identify_knowledge_gaps(
        selection=selection,
        metrics=metrics,
        registry=registry,
        conversation_context=conversation_context,
        workflow_owned_fields=workflow_owned_fields,
    )
    next_gap = gaps["next_gap"]
    handoff = _build_handoff(next_gap, selection, situation)
    selected_ids = [item.get("knowledge_id") for item in selection["primary"] + selection["secondary"]]
    definitions = [registry.get(knowledge_id) for knowledge_id in selected_ids if registry.get(knowledge_id)]
    concepts = _unique([concept for definition in definitions for concept in definition.concepts])
    relevant_metrics = identify_relevant_metrics(selection, registry)
    relationship_rules = _unique([
        rule.to_dict()
        for definition in definitions
        for rule in definition.relationship_rules
        if any(metric in relevant_metrics or metric in metrics for metric in rule.input_metrics)
    ])
    complete_statuses = {MetricCompletenessStatus.AVAILABLE_COMPLETE.value}
    available_metrics = {key: value for key, value in metrics.items() if value.get("completeness_status") in complete_statuses}
    incomplete_metrics = {key: value for key, value in metrics.items() if value.get("completeness_status") not in complete_statuses}
    missing_metrics = [metric for metric in relevant_metrics if metric not in metrics]
    invariants = _constitutional_invariants(bool(next_gap))
    validation = validate_knowledge_registry(registry)
    diagnostics = {
        "knowledge_runtime_created": True,
        "knowledge_runtime_version": KNOWLEDGE_RUNTIME_VERSION,
        "knowledge_runtime_source": KNOWLEDGE_RUNTIME_SOURCE,
        "knowledge_available": bool(selection["primary"] or selection["secondary"]),
        "selected_frame": selected_frame,
        "primary_knowledge_ids": [item.get("knowledge_id") for item in selection["primary"]],
        "secondary_knowledge_ids": [item.get("knowledge_id") for item in selection["secondary"]],
        "deferred_knowledge_ids": [item.get("knowledge_id") for item in selection["deferred"]],
        "candidate_count": len(candidates),
        "knowledge_gap_count": len(gaps["gaps"]),
        "next_knowledge_gap": next_gap,
        "clarification_handoff_created": bool(next_gap),
        "registry_validation": validation,
        "constitutional_invariants": invariants,
        **invariants,
    }
    result = KnowledgeRuntimeResult(
        knowledge_available=bool(selection["primary"] or selection["secondary"]),
        selected_frame=selected_frame,
        candidate_frames=deepcopy(candidate_frames),
        primary_knowledge=selection["primary"],
        secondary_knowledge=selection["secondary"],
        deferred_knowledge=selection["deferred"],
        excluded_knowledge=selection["excluded"],
        relevant_concepts=concepts,
        relevant_metrics=relevant_metrics,
        applicable_relationship_rules=relationship_rules,
        available_metrics=available_metrics,
        incomplete_metrics=incomplete_metrics,
        missing_metrics=missing_metrics,
        knowledge_gaps=gaps["gaps"],
        merged_gaps=gaps["merged_gaps"],
        suppressed_gaps=gaps["suppressed_gaps"],
        next_knowledge_gap=next_gap,
        clarification_handoff=handoff,
        selection_reason="deterministic frame and context retrieval" if candidates else "no supported Knowledge selected",
        selection_support_strength=round(max([float(item.get("support_strength") or 0.0) for item in selection["primary"]] or [0.0]), 3),
        retrieval_method="frame_and_context" if selected_frame != "UNKNOWN_SITUATION" else "context_only" if candidates else "none",
        registry_version=registry.version,
        source_layers={
            "perspective": bool(perspective),
            "business_situation": bool(situation),
            "evidence_runtime": bool(evidence_runtime),
            "truth_runtime": bool(truth_runtime),
            "conversation_context": bool(conversation_context),
        },
        constitutional_invariants=invariants,
        diagnostics=diagnostics,
    )
    return result.to_dict()
