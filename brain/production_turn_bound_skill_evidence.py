"""Passive canonical cost extraction evidence bound to one production turn."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Mapping

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_candidate_matcher import (
    BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION, match_business_skill_candidates,
    normalize_candidate_message,
)
from brain.business_skill_evidence_mapper import (
    BUSINESS_SKILL_EVIDENCE_MAPPER_CURRENT_VERSION, map_candidate_skill_evidence,
)
from brain.business_skill_lifecycle_manifest import BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_shadow_selector import (
    AMBIGUOUS_CANDIDATES, BUSINESS_SKILL_SHADOW_SELECTOR_VERSION, SHADOW_SELECTED,
    select_shadow_business_skill,
)
from brain.canonical_cost_evidence_parser import (
    AMBIGUOUS, CANONICAL_COST_EVIDENCE_PARSER_SCOPE,
    CANONICAL_COST_EVIDENCE_PARSER_VERSION, COMPLETE, CURRENT_TURN,
    CURRENT_USER_MESSAGE, INVALID, NO_EVIDENCE, OPTIONAL_EVIDENCE_IDS, PARTIAL,
    REQUIRED_EVIDENCE_IDS, CanonicalCostEvidenceParseResult,
    parse_canonical_cost_evidence, verify_canonical_cost_evidence_parse_result,
)
from brain.language_normalization import LANGUAGE_NORMALIZATION_VERSION, normalize_user_language
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    ProductionFeatureGateEvaluation, verify_production_feature_gate_evaluation,
)
from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context


PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_HISTORICAL_VERSION = "5.15.24.6"
PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION = "5.15.24.6.1"
PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_SCOPE = "VERIFIED_USER_TURN_CANONICAL_COST_EVIDENCE"
PRODUCTION_SKILL_MATCHING_NORMALIZATION_IDENTITY = (
    f"language-normalization:{LANGUAGE_NORMALIZATION_VERSION}|"
    f"candidate-matcher-normalization:{BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION}"
)
SUPPORTED_COST_SKILL_IDS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class NormalizedMessageProvenance:
    provenance_version: str
    turn_digest: str
    raw_message_digest: str
    normalized_message: str
    normalized_message_digest: str
    normalization_identity: str
    language_normalization_version: str
    matcher_version: str
    normalization_changed: bool
    provenance_digest: str = ""


@dataclass(frozen=True)
class ProductionSkillCandidateBinding:
    skill_id: str
    lifecycle_state: str
    matcher_version: str
    normalized_message_digest: str
    match_status: str
    candidate_score: int
    candidate_confidence: float
    matched_intent_patterns: tuple[str, ...]
    matched_example_questions: tuple[str, ...]
    matched_terms: tuple[str, ...]
    candidate_reasons: tuple[str, ...]
    candidate_index: int
    ambiguity_state: str
    candidate_digest: str = ""


@dataclass(frozen=True)
class ParserMapperBinding:
    skill_id: str
    candidate_digest: str
    parse_digest: str
    parser_raw_message_digest: str
    ordered_evidence_ids: tuple[str, ...]
    mapper_version: str
    source_mapping: str
    freshness_mapping: str
    mapper_input_digest: str
    binding_digest: str = ""


@dataclass(frozen=True)
class ProductionEvidenceItem:
    skill_id: str
    evidence_id: str
    canonical_type: str
    required: bool
    present: bool
    value_digest: str | None
    value_type: str | None
    confidence: float | None
    confidence_required: float
    confidence_sufficient: bool
    source: str | None
    freshness: str | None
    freshness_requirement: str
    freshness_sufficient: bool
    assumed: bool
    can_assume: bool
    confirmation_required: bool
    user_confirmed: bool
    validation_rule: str
    validation_status: str
    mapping_status: str
    sensitive: bool
    reason_codes: tuple[str, ...]
    evidence_index: int
    evidence_digest: str = ""


@dataclass(frozen=True)
class ShadowSelectorResult:
    selector_version: str
    selection_status: str
    shadow_selected_skill_id: str | None
    eligible_candidate_ids: tuple[str, ...]
    rejected_candidate_ids: tuple[str, ...]
    selector_digest: str = ""


@dataclass(frozen=True)
class ProductionTurnBoundSkillEvidenceEnvelope:
    envelope_version: str
    envelope_scope: str
    parser_version: str
    parser_scope: str
    mapper_version: str
    selector_version: str
    registry_version: str
    lifecycle_version: str
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    raw_message_digest: str
    normalized_provenance: NormalizedMessageProvenance
    candidate_bindings: tuple[ProductionSkillCandidateBinding, ...]
    canonical_parse_results: tuple[CanonicalCostEvidenceParseResult, ...]
    parser_mapper_bindings: tuple[ParserMapperBinding, ...]
    evidence_items: tuple[ProductionEvidenceItem, ...]
    evidence_snapshot_digest: str
    selector_result: ShadowSelectorResult
    selected_skill_id: str | None
    selected_parser_digest: str | None
    selected_candidate_digest: str | None
    extraction_status: str
    feature_gate_name: str
    feature_gate_evaluation_digest: str
    passive_observation: bool = True
    reasons: tuple[str, ...] = ()
    routing_authority: bool = False
    planning_authority: bool = False
    workflow_selection_authority: bool = False
    response_selection_authority: bool = False
    response_guard_authority: bool = False
    response_resolution_authority: bool = False
    response_commit_authority: bool = False
    persistence_authority: bool = False
    tool_execution_authority: bool = False
    feature_gate_mutation_authority: bool = False
    limited_activation_authority: bool = False
    delivery_preparation_authority: bool = False
    bridge_request_authority: bool = False
    admission_authority: bool = False
    controlled_runtime_activation_authority: bool = False
    envelope_digest: str = ""


_AUTHORITY_FIELDS = tuple(name for name in ProductionTurnBoundSkillEvidenceEnvelope.__dataclass_fields__ if name.endswith("_authority"))


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite canonical value")
        return {"$float": format(value, ".17g")}
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        return {"$decimal": str(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if is_dataclass(value):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("canonical mapping keys must be strings")
        return [[key, _canonical(value[key])] for key in sorted(value)]
    raise ValueError("unsupported canonical value")


def _sha256(material: Any) -> str:
    encoded = json.dumps(_canonical(material), ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_normalized_message_digest(message: Any) -> str:
    if type(message) is not str or not message:
        return ""
    return _sha256(("PRODUCTION_NORMALIZED_SKILL_MESSAGE", PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION, message))


def _digest_dataclass(label: str, value: Any, digest_field: str) -> str:
    return _sha256((label, tuple(getattr(value, field.name) for field in fields(value) if field.name != digest_field)))


def _cost_registry() -> tuple[Any, ...]:
    by_id = {skill.skill_id: skill for skill in get_business_skill_registry()}
    result = tuple(by_id.get(skill_id) for skill_id in SUPPORTED_COST_SKILL_IDS)
    if any(skill is None for skill in result):
        raise ValueError("supported cost skill missing")
    return result


def convert_verified_cost_parse_result_to_mapper_evidence(result: Any) -> dict[str, dict[str, Any]]:
    """Pure, strict adapter. Decimal values and explicit parser claims are preserved."""
    if not verify_canonical_cost_evidence_parse_result(result):
        raise ValueError("strictly verified canonical parse result required")
    allowed = REQUIRED_EVIDENCE_IDS[result.skill_id] + OPTIONAL_EVIDENCE_IDS[result.skill_id]
    values = result.evidence_values
    ids = tuple(item.required_evidence_id for item in values)
    if len(ids) != len(set(ids)) or any(item not in allowed for item in ids):
        raise ValueError("duplicate or unknown parser evidence role")
    blocked = set(result.ambiguous_roles) | set(result.invalid_roles)
    if any(item in blocked for item in ids):
        raise ValueError("ambiguous or invalid role cannot be promoted")
    if result.status == NO_EVIDENCE and values:
        raise ValueError("NO_EVIDENCE must be empty")
    if result.status not in (COMPLETE, PARTIAL, AMBIGUOUS, INVALID, NO_EVIDENCE):
        raise ValueError("unknown extraction status")
    evidence: dict[str, dict[str, Any]] = {}
    for item in values:
        try:
            business_value = Decimal(item.canonical_decimal)
        except InvalidOperation as exc:
            raise ValueError("invalid canonical parser Decimal") from exc
        if not business_value.is_finite():
            raise ValueError("non-finite parser Decimal")
        if item.confidence != "1.0" or item.source != CURRENT_USER_MESSAGE or item.freshness != CURRENT_TURN:
            raise ValueError("non-canonical parser observation claims")
        if item.assumed is not False or item.user_confirmed is not False:
            raise ValueError("parser authority escalation")
        evidence[item.required_evidence_id] = {
            "value": business_value,
            "confidence": item.confidence,
            "source": "current_turn",
            "freshness": "current",
            "assumed": False,
            "user_confirmed": False,
        }
    return evidence


def _build(context: ProductionTurnContext, gate_evaluation: ProductionFeatureGateEvaluation) -> ProductionTurnBoundSkillEvidenceEnvelope:
    language = normalize_user_language(context.user_message)
    if language.get("original_text") != context.user_message or language.get("version") != LANGUAGE_NORMALIZATION_VERSION:
        raise ValueError("normalization provenance failed")
    normalized = normalize_candidate_message(language.get("normalized_text"))
    if not normalized:
        raise ValueError("empty normalized message")
    normalized_digest = compute_normalized_message_digest(normalized)
    provenance = NormalizedMessageProvenance(
        PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION, context.turn_digest, context.user_message_digest,
        normalized, normalized_digest, PRODUCTION_SKILL_MATCHING_NORMALIZATION_IDENTITY,
        LANGUAGE_NORMALIZATION_VERSION, BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
        normalized != context.user_message,
    )
    provenance = replace(provenance, provenance_digest=_digest_dataclass("NORMALIZED_MESSAGE_PROVENANCE", provenance, "provenance_digest"))
    registry = _cost_registry()
    candidates = match_business_skill_candidates(normalized, registry, limit=None)
    ambiguity = "AMBIGUOUS" if len(candidates) > 1 else "UNAMBIGUOUS"
    candidate_bindings = []
    for index, candidate in enumerate(candidates, 1):
        item = ProductionSkillCandidateBinding(
            candidate["skill_id"], candidate["active_status"], BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
            normalized_digest, "MATCHED", candidate["candidate_score"], candidate["candidate_confidence"],
            tuple(candidate["matched_intent_patterns"]), tuple(candidate["matched_example_questions"]),
            tuple(candidate["matched_terms"]), tuple(candidate["candidate_reasons"]), index, ambiguity,
        )
        candidate_bindings.append(replace(item, candidate_digest=_digest_dataclass("PRODUCTION_SKILL_CANDIDATE_BINDING", item, "candidate_digest")))
    candidate_bindings = tuple(candidate_bindings)
    parses = tuple(parse_canonical_cost_evidence(item.skill_id, context.user_message) for item in candidate_bindings)
    mapper_inputs = tuple(convert_verified_cost_parse_result_to_mapper_evidence(item) for item in parses)
    mappings = tuple(map_candidate_skill_evidence(candidate, evidence, registry) for candidate, evidence in zip(candidates, mapper_inputs))
    bindings = []
    evidence_items = []
    for candidate, parse, evidence, mapping in zip(candidate_bindings, parses, mapper_inputs, mappings):
        input_digest = _sha256(("CANONICAL_PARSER_MAPPER_INPUT", candidate.skill_id, evidence))
        binding = ParserMapperBinding(
            candidate.skill_id, candidate.candidate_digest, parse.parse_digest, parse.raw_message_digest,
            tuple(evidence), BUSINESS_SKILL_EVIDENCE_MAPPER_CURRENT_VERSION,
            "CURRENT_USER_MESSAGE->current_turn", "CURRENT_TURN->current", input_digest,
        )
        bindings.append(replace(binding, binding_digest=_digest_dataclass("PARSER_MAPPER_BINDING", binding, "binding_digest")))
        for index, mapped in enumerate(mapping["evidence_mappings"], 1):
            observed = mapped["observed_value"]
            value_digest = _sha256(("PRODUCTION_EVIDENCE_VALUE", candidate.skill_id, mapped["field_name"], observed)) if mapped["value_present"] else None
            item = ProductionEvidenceItem(
                candidate.skill_id, mapped["field_name"], mapped["expected_field_type"], bool(mapped["required"]),
                bool(mapped["value_present"]), value_digest, type(observed).__name__ if mapped["value_present"] else None,
                mapped["observed_confidence"], mapped["confidence_required"], bool(mapped["confidence_sufficient"]),
                mapped["observed_source"], mapped["observed_freshness"], mapped["freshness_requirement"],
                bool(mapped["freshness_sufficient"]), bool(mapped["assumed"]), bool(mapped["can_assume"]),
                bool(mapped["user_confirmation_required"]), bool(mapped["user_confirmed"]), mapped["validation_rule"],
                mapped["validation_status"], mapped["mapping_status"], bool(mapped["sensitive"]),
                tuple(mapped["reasons"]), index,
            )
            evidence_items.append(replace(item, evidence_digest=_digest_dataclass("PRODUCTION_SKILL_EVIDENCE_ITEM", item, "evidence_digest")))
    bindings, evidence_items = tuple(bindings), tuple(evidence_items)
    evidence_snapshot_digest = _sha256(("PRODUCTION_EVIDENCE_SNAPSHOT", tuple(item.evidence_digest for item in evidence_items)))
    selection = select_shadow_business_skill(candidates, mappings, registry)
    selector = ShadowSelectorResult(
        BUSINESS_SKILL_SHADOW_SELECTOR_VERSION, str(selection.get("selection_status")),
        selection.get("shadow_selected_skill_id"), tuple(selection.get("eligible_candidate_ids", ())),
        tuple(selection.get("rejected_candidate_ids", ())),
    )
    selector = replace(selector, selector_digest=_digest_dataclass("SHADOW_SELECTOR_RESULT", selector, "selector_digest"))
    selected_id = selector.shadow_selected_skill_id if selector.selection_status == SHADOW_SELECTED else None
    selected_index = next((i for i, item in enumerate(candidate_bindings) if item.skill_id == selected_id), None)
    if selected_index is not None:
        parse = parses[selected_index]
        mapping = mappings[selected_index]
        candidate = candidate_bindings[selected_index]
        valid = (candidate.lifecycle_state == LIMITED_ACTIVE and parse.status == COMPLETE and
                 verify_canonical_cost_evidence_parse_result(parse) and mapping.get("evidence_mapping_valid") is True and
                 mapping.get("evidence_ready") is True and not parse.ambiguous_roles and not parse.invalid_roles)
        if not valid:
            selected_id, selected_index = None, None
    extraction = "NO_CANDIDATES" if not parses else (parses[0].status if len(parses) == 1 else "MULTIPLE_CANDIDATES")
    envelope = ProductionTurnBoundSkillEvidenceEnvelope(
        PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION, PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_SCOPE,
        CANONICAL_COST_EVIDENCE_PARSER_VERSION, CANONICAL_COST_EVIDENCE_PARSER_SCOPE,
        BUSINESS_SKILL_EVIDENCE_MAPPER_CURRENT_VERSION, BUSINESS_SKILL_SHADOW_SELECTOR_VERSION,
        BUSINESS_SKILL_REGISTRY_VERSION, BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION,
        context.conversation_id, context.turn_id, context.turn_ordinal,
        context.turn_digest, context.user_message_digest, provenance, candidate_bindings, parses, bindings,
        evidence_items, evidence_snapshot_digest, selector, selected_id,
        parses[selected_index].parse_digest if selected_index is not None else None,
        candidate_bindings[selected_index].candidate_digest if selected_index is not None else None,
        extraction, gate_evaluation.gate_name, gate_evaluation.evaluation_digest,
        reasons=(selector.selection_status, "PASSIVE_OBSERVATION_ONLY"),
    )
    return replace(envelope, envelope_digest=_digest_dataclass("PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_ENVELOPE", envelope, "envelope_digest"))


def create_production_turn_bound_skill_evidence_envelope(context: Any, gate_evaluation: Any, available_evidence: Any = None) -> ProductionTurnBoundSkillEvidenceEnvelope:
    if available_evidence is not None:
        raise ValueError("external evidence is prohibited in canonical production extraction")
    if not verify_production_turn_context(context):
        raise ValueError("verified ProductionTurnContext required")
    if not verify_production_feature_gate_evaluation(gate_evaluation, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context):
        raise ValueError("verified current feature-gate evaluation required")
    if gate_evaluation.gate_name != LIMITED_COST_RESPONSE_RUNTIME_BRIDGE:
        raise ValueError("exact limited cost feature gate required")
    return _build(context, gate_evaluation)


def verify_production_turn_bound_skill_evidence_envelope(value: Any, context: Any, gate_evaluation: Any, available_evidence: Any = None) -> bool:
    try:
        if type(value) is not ProductionTurnBoundSkillEvidenceEnvelope or value.envelope_version != PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION:
            return False
        if value.envelope_scope != PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_SCOPE or value.passive_observation is not True:
            return False
        if any(type(getattr(value, name)) is not bool or getattr(value, name) for name in _AUTHORITY_FIELDS):
            return False
        if available_evidence is not None:
            return False
        digest_values = (value.turn_digest, value.raw_message_digest, value.normalized_provenance.normalized_message_digest,
                         value.normalized_provenance.provenance_digest, value.evidence_snapshot_digest,
                         value.selector_result.selector_digest, value.feature_gate_evaluation_digest, value.envelope_digest)
        digest_values += tuple(item.candidate_digest for item in value.candidate_bindings)
        digest_values += tuple(item.parse_digest for item in value.canonical_parse_results)
        digest_values += tuple(item.binding_digest for item in value.parser_mapper_bindings)
        digest_values += tuple(item.evidence_digest for item in value.evidence_items)
        if any(type(item) is not str or not _HEX.fullmatch(item) for item in digest_values):
            return False
        if any(item.value_digest is not None and not _HEX.fullmatch(item.value_digest) for item in value.evidence_items):
            return False
        expected = create_production_turn_bound_skill_evidence_envelope(context, gate_evaluation)
        return value == expected and value.envelope_digest == _digest_dataclass("PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_ENVELOPE", value, "envelope_digest")
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def resolve_production_turn_bound_skill_evidence_envelope(current: Any, context: ProductionTurnContext, gate_evaluation: ProductionFeatureGateEvaluation, available_evidence: Any = None) -> ProductionTurnBoundSkillEvidenceEnvelope | None:
    """Reuse exact current evidence; passive failures produce no artifact."""
    try:
        expected = create_production_turn_bound_skill_evidence_envelope(context, gate_evaluation, available_evidence)
        if verify_production_turn_bound_skill_evidence_envelope(current, context, gate_evaluation, available_evidence) and current == expected:
            return current
        return expected
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None
