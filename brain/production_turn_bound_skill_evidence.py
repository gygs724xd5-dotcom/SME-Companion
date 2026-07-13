"""Passive, immutable skill-evidence provenance for one verified production turn."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_candidate_matcher import (
    BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
    match_business_skill_candidates,
    normalize_candidate_message,
)
from brain.business_skill_evidence_mapper import (
    BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION,
    map_candidate_skill_evidence,
)
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_shadow_selector import (
    AMBIGUOUS_CANDIDATES,
    BUSINESS_SKILL_SHADOW_SELECTOR_VERSION,
    SHADOW_SELECTED,
    select_shadow_business_skill,
)
from brain.language_normalization import LANGUAGE_NORMALIZATION_VERSION, normalize_user_language
from brain.production_feature_gate_owner import (
    LIMITED_COST_RESPONSE_RUNTIME_BRIDGE,
    PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION,
    ProductionFeatureGateEvaluation,
    verify_production_feature_gate_evaluation,
)
from brain.production_turn_context import ProductionTurnContext, verify_production_turn_context


PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION = "5.15.24.6"
PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_SCOPE = "VERIFIED_USER_TURN_SKILL_EVIDENCE"
PRODUCTION_SKILL_MATCHING_NORMALIZATION_IDENTITY = (
    f"language-normalization:{LANGUAGE_NORMALIZATION_VERSION}|"
    f"candidate-matcher-normalization:{BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION}"
)
SUPPORTED_COST_SKILL_IDS = (
    "cost.change_analysis.v1",
    "cost.per_unit_calculation.v1",
)
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
class ProductionEvidenceItem:
    skill_id: str
    evidence_id: str
    canonical_type: str
    required: bool
    present: bool
    value_digest: str | None
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
class ProductionTurnBoundSkillEvidenceEnvelope:
    envelope_version: str
    envelope_scope: str
    registry_version: str
    conversation_id: str
    turn_id: str
    turn_ordinal: int
    turn_digest: str
    raw_message_digest: str
    normalized_provenance: NormalizedMessageProvenance
    candidate_bindings: tuple[ProductionSkillCandidateBinding, ...]
    selected_skill_id: str | None
    selection_status: str
    ambiguity_status: str
    selected_candidate_digest: str | None
    evidence_items: tuple[ProductionEvidenceItem, ...]
    evidence_snapshot_digest: str
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


_AUTHORITY_FIELDS = tuple(
    name for name in ProductionTurnBoundSkillEvidenceEnvelope.__dataclass_fields__
    if name.endswith("_authority")
)


def _canonical(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite canonical value")
        return {"$float": format(value, ".17g")}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if is_dataclass(value):
        return [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]
    if isinstance(value, Mapping):
        return [[str(key), _canonical(value[key])] for key in sorted(value, key=str)]
    raise ValueError("unsupported canonical value")


def _sha256(material: Any) -> str:
    encoded = json.dumps(
        _canonical(material), ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_normalized_message_digest(message: Any) -> str:
    if type(message) is not str or not message:
        return ""
    return _sha256(("PRODUCTION_NORMALIZED_SKILL_MESSAGE", PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION, message))


def _provenance_digest(value: NormalizedMessageProvenance) -> str:
    return _sha256(("NORMALIZED_MESSAGE_PROVENANCE",) + tuple(
        getattr(value, name) for name in value.__dataclass_fields__ if name != "provenance_digest"
    ))


def _candidate_digest(value: ProductionSkillCandidateBinding) -> str:
    return _sha256(("PRODUCTION_SKILL_CANDIDATE_BINDING",) + tuple(
        getattr(value, name) for name in value.__dataclass_fields__ if name != "candidate_digest"
    ))


def _evidence_digest(value: ProductionEvidenceItem) -> str:
    return _sha256(("PRODUCTION_SKILL_EVIDENCE_ITEM",) + tuple(
        getattr(value, name) for name in value.__dataclass_fields__ if name != "evidence_digest"
    ))


def _envelope_digest(value: ProductionTurnBoundSkillEvidenceEnvelope) -> str:
    material = tuple(
        getattr(value, name) for name in value.__dataclass_fields__ if name != "envelope_digest"
    )
    return _sha256(("PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_ENVELOPE", material))


def _cost_registry() -> tuple[Any, ...]:
    by_id = {skill.skill_id: skill for skill in get_business_skill_registry()}
    result = tuple(by_id.get(skill_id) for skill_id in SUPPORTED_COST_SKILL_IDS)
    if any(skill is None for skill in result):
        raise ValueError("supported cost skill missing from canonical registry")
    return result


def _evidence_input_copy(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("evidence inputs must be an explicit mapping")
    # Canonical round-trip copies only JSON-like evidence and rejects object identity.
    canonical = _canonical(value)
    def thaw(item: Any) -> Any:
        if isinstance(item, list):
            if all(isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], str) for pair in item):
                return {pair[0]: thaw(pair[1]) for pair in item}
            return [thaw(part) for part in item]
        if isinstance(item, dict) and set(item) == {"$float"}:
            return float(item["$float"])
        return item
    copied = thaw(canonical)
    if not isinstance(copied, dict):
        raise ValueError("evidence inputs must canonicalize to a mapping")
    return copied


def create_production_turn_bound_skill_evidence_envelope(
    context: Any,
    gate_evaluation: Any,
    available_evidence: Any = None,
) -> ProductionTurnBoundSkillEvidenceEnvelope:
    if not verify_production_turn_context(context):
        raise ValueError("verified ProductionTurnContext required")
    if not verify_production_feature_gate_evaluation(
        gate_evaluation, PRODUCTION_DEFAULT_DENY_FEATURE_GATE_CONFIGURATION, context
    ):
        raise ValueError("verified current production feature-gate evaluation required")
    if gate_evaluation.gate_name != LIMITED_COST_RESPONSE_RUNTIME_BRIDGE:
        raise ValueError("exact limited cost feature gate required")

    language = normalize_user_language(context.user_message)
    if language.get("original_text") != context.user_message or language.get("version") != LANGUAGE_NORMALIZATION_VERSION:
        raise ValueError("canonical language normalization provenance failed")
    normalized_message = normalize_candidate_message(language.get("normalized_text"))
    if not normalized_message:
        raise ValueError("canonical matcher normalization produced an empty message")
    normalized_digest = compute_normalized_message_digest(normalized_message)
    provenance_draft = NormalizedMessageProvenance(
        provenance_version=PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION,
        turn_digest=context.turn_digest,
        raw_message_digest=context.user_message_digest,
        normalized_message=normalized_message,
        normalized_message_digest=normalized_digest,
        normalization_identity=PRODUCTION_SKILL_MATCHING_NORMALIZATION_IDENTITY,
        language_normalization_version=LANGUAGE_NORMALIZATION_VERSION,
        matcher_version=BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
        normalization_changed=normalized_message != context.user_message,
    )
    provenance = replace(provenance_draft, provenance_digest=_provenance_digest(provenance_draft))

    registry = _cost_registry()
    candidates = match_business_skill_candidates(normalized_message, registry, limit=None)
    evidence_input = _evidence_input_copy(available_evidence)
    mappings = [map_candidate_skill_evidence(candidate, evidence_input, registry) for candidate in candidates]
    selection = select_shadow_business_skill(candidates, mappings, registry)
    ambiguity = "AMBIGUOUS" if selection.get("selection_status") == AMBIGUOUS_CANDIDATES else "UNAMBIGUOUS"

    candidate_bindings = []
    for index, candidate in enumerate(candidates, 1):
        draft = ProductionSkillCandidateBinding(
            skill_id=candidate["skill_id"], lifecycle_state=candidate["active_status"],
            matcher_version=BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
            normalized_message_digest=normalized_digest, match_status="MATCHED",
            candidate_score=candidate["candidate_score"], candidate_confidence=candidate["candidate_confidence"],
            matched_intent_patterns=tuple(candidate["matched_intent_patterns"]),
            matched_example_questions=tuple(candidate["matched_example_questions"]),
            matched_terms=tuple(candidate["matched_terms"]), candidate_reasons=tuple(candidate["candidate_reasons"]),
            candidate_index=index, ambiguity_state=ambiguity,
        )
        candidate_bindings.append(replace(draft, candidate_digest=_candidate_digest(draft)))
    candidate_bindings = tuple(candidate_bindings)

    evidence_items = []
    for mapping in mappings:
        skill_id = mapping["skill_id"]
        for index, item in enumerate(mapping["evidence_mappings"], 1):
            present = bool(item["value_present"])
            value_digest = _sha256(("PRODUCTION_EVIDENCE_VALUE", skill_id, item["field_name"], item["observed_value"])) if present else None
            draft = ProductionEvidenceItem(
                skill_id=skill_id, evidence_id=item["field_name"], canonical_type=item["expected_field_type"],
                required=bool(item["required"]), present=present, value_digest=value_digest,
                confidence=item["observed_confidence"], confidence_required=float(item["confidence_required"]),
                confidence_sufficient=bool(item["confidence_sufficient"]), source=item["observed_source"],
                freshness=item["observed_freshness"], freshness_requirement=item["freshness_requirement"],
                freshness_sufficient=bool(item["freshness_sufficient"]), assumed=bool(item["assumed"]),
                can_assume=bool(item["can_assume"]), confirmation_required=bool(item["user_confirmation_required"]),
                user_confirmed=bool(item["user_confirmed"]), validation_rule=item["validation_rule"],
                validation_status=item["validation_status"], mapping_status=item["mapping_status"],
                sensitive=bool(item["sensitive"]), reason_codes=tuple(item["reasons"]), evidence_index=index,
            )
            evidence_items.append(replace(draft, evidence_digest=_evidence_digest(draft)))
    evidence_items = tuple(evidence_items)
    evidence_snapshot_digest = _sha256(("PRODUCTION_EVIDENCE_SNAPSHOT", tuple(x.evidence_digest for x in evidence_items)))

    selected_skill_id = selection.get("shadow_selected_skill_id") if selection.get("selection_status") == SHADOW_SELECTED else None
    selected = next((item for item in candidate_bindings if item.skill_id == selected_skill_id), None)
    if selected is not None and selected.lifecycle_state != LIMITED_ACTIVE:
        selected_skill_id, selected = None, None
    reasons = (str(selection.get("selection_status") or "INVALID_SELECTION"), "PASSIVE_OBSERVATION_ONLY")
    draft = ProductionTurnBoundSkillEvidenceEnvelope(
        envelope_version=PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION,
        envelope_scope=PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_SCOPE,
        registry_version=BUSINESS_SKILL_REGISTRY_VERSION,
        conversation_id=context.conversation_id, turn_id=context.turn_id, turn_ordinal=context.turn_ordinal,
        turn_digest=context.turn_digest, raw_message_digest=context.user_message_digest,
        normalized_provenance=provenance, candidate_bindings=candidate_bindings,
        selected_skill_id=selected_skill_id, selection_status=str(selection.get("selection_status")),
        ambiguity_status=ambiguity, selected_candidate_digest=selected.candidate_digest if selected else None,
        evidence_items=evidence_items, evidence_snapshot_digest=evidence_snapshot_digest,
        feature_gate_name=gate_evaluation.gate_name,
        feature_gate_evaluation_digest=gate_evaluation.evaluation_digest,
        reasons=reasons,
    )
    return replace(draft, envelope_digest=_envelope_digest(draft))


def verify_production_turn_bound_skill_evidence_envelope(
    value: Any,
    context: Any,
    gate_evaluation: Any,
    available_evidence: Any = None,
) -> bool:
    try:
        if type(value) is not ProductionTurnBoundSkillEvidenceEnvelope:
            return False
        if value.envelope_version != PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_VERSION:
            return False
        if value.envelope_scope != PRODUCTION_TURN_BOUND_SKILL_EVIDENCE_SCOPE:
            return False
        if value.passive_observation is not True:
            return False
        if any(type(getattr(value, name)) is not bool or getattr(value, name) for name in _AUTHORITY_FIELDS):
            return False
        digests = (value.turn_digest, value.raw_message_digest, value.normalized_provenance.normalized_message_digest,
                   value.normalized_provenance.provenance_digest, value.evidence_snapshot_digest,
                   value.feature_gate_evaluation_digest, value.envelope_digest)
        if any(type(item) is not str or not _HEX.fullmatch(item) for item in digests):
            return False
        if any(not _HEX.fullmatch(item.candidate_digest) for item in value.candidate_bindings):
            return False
        if any(not _HEX.fullmatch(item.evidence_digest) or
               (item.value_digest is not None and not _HEX.fullmatch(item.value_digest)) for item in value.evidence_items):
            return False
        expected = create_production_turn_bound_skill_evidence_envelope(
            context, gate_evaluation, available_evidence
        )
        return value == expected and value.envelope_digest == _envelope_digest(value)
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False


def resolve_production_turn_bound_skill_evidence_envelope(
    current: Any,
    context: ProductionTurnContext,
    gate_evaluation: ProductionFeatureGateEvaluation,
    available_evidence: Any = None,
) -> ProductionTurnBoundSkillEvidenceEnvelope | None:
    """Reuse exact current evidence; passive failures produce no artifact."""
    try:
        expected = create_production_turn_bound_skill_evidence_envelope(
            context, gate_evaluation, available_evidence
        )
        if verify_production_turn_bound_skill_evidence_envelope(
            current, context, gate_evaluation, available_evidence
        ) and current == expected:
            return current
        return expected
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeEncodeError):
        return None
