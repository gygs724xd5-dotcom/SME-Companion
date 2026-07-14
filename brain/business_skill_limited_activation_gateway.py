"""V5.15.14 pure, deny-by-default limited activation eligibility gateway.

Eligibility is only permission to enter a *limited execution path*.  This
module neither executes a skill nor owns runtime, response, tool, or storage
authority.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_candidate_matcher import match_business_skill_candidates
from brain.business_skill_candidate_matcher import BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION
from brain.business_skill_evidence_mapper import BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION, map_candidate_skill_evidence
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry

LIMITED_ACTIVATION_GATEWAY_VERSION = "5.15.14.1"
HISTORICAL_LIMITED_ACTIVATION_GATEWAY_VERSION = "5.15.14"
ACTIVATION_BINDING_SCHEMA_VERSION = "1"
ACTIVATION_BINDING_DECIMAL_SCHEMA_VERSION = "5.15.24.6.3"
LIMITED_EXECUTION_ELIGIBLE = "LIMITED_EXECUTION_ELIGIBLE"
LIMITED_EXECUTION_DENIED = "LIMITED_EXECUTION_DENIED"
SUPPORTED_SKILL_IDS = ("cost.change_analysis.v1", "cost.per_unit_calculation.v1")
SUPPORTED_ACTIVATION_SCOPE = "COST_ANALYSIS_LIMITED"
CANONICAL_MINIMUM_CANDIDATE_SCORE = 70.0
CANONICAL_MINIMUM_CANDIDATE_CONFIDENCE = 0.58
CANONICAL_MINIMUM_EVIDENCE_CONFIDENCE = 0.8
GATE_ORDER = ("REQUEST_VALIDITY", "SKILL_IDENTITY", "LIFECYCLE", "ACTIVATION_SCOPE",
              "CANDIDATE_CONFIDENCE", "EVIDENCE_READINESS", "AMBIGUITY",
              "CURRENT_MESSAGE_ONLY", "AUTHORITY_BOUNDARY")
_AUTHORITY_KEYS = frozenset(("executed", "calculated", "reasoning_executed", "runtime_routed",
    "tools_invoked", "persisted", "follow_up_generated", "response_generated",
    "response_committed", "response", "answer", "callback", "execution_callback",
    "runtime_route", "tool_invocation", "persistence_command"))
_CANONICAL_EVIDENCE_ORDER = {
    "cost.change_analysis.v1": ("previous_cost", "current_cost"),
    "cost.per_unit_calculation.v1": ("total_cost", "unit_quantity", "waste_or_loss_quantity"),
}
_LOWER_HEX_DIGEST = re.compile(r"[0-9a-f]{64}")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple((str(k), _freeze(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)): return tuple(_freeze(v) for v in value)
    if isinstance(value, (set, frozenset)): return tuple(sorted((_freeze(v) for v in value), key=repr))
    try: return deepcopy(value)
    except Exception: return repr(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], str) for x in value):
            return {k: _thaw(v) for k, v in value}
        return [_thaw(v) for v in value]
    return deepcopy(value)


@dataclass(frozen=True)
class LimitedActivationPolicy:
    policy_version: str = LIMITED_ACTIVATION_GATEWAY_VERSION
    minimum_candidate_score: float = CANONICAL_MINIMUM_CANDIDATE_SCORE
    minimum_candidate_confidence: float = CANONICAL_MINIMUM_CANDIDATE_CONFIDENCE
    minimum_evidence_confidence: float = CANONICAL_MINIMUM_EVIDENCE_CONFIDENCE

    def __post_init__(self) -> None:
        values = (self.minimum_candidate_score, self.minimum_candidate_confidence,
                  self.minimum_evidence_confidence)
        if self.policy_version != LIMITED_ACTIVATION_GATEWAY_VERSION:
            raise ValueError("unsupported policy version")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in values):
            raise ValueError("policy thresholds must be numeric")
        if self.minimum_candidate_score < CANONICAL_MINIMUM_CANDIDATE_SCORE:
            raise ValueError("candidate score below canonical safety floor")
        if not CANONICAL_MINIMUM_CANDIDATE_CONFIDENCE <= self.minimum_candidate_confidence <= 1:
            raise ValueError("candidate confidence below safety floor or impossible")
        if not CANONICAL_MINIMUM_EVIDENCE_CONFIDENCE <= self.minimum_evidence_confidence <= 1:
            raise ValueError("evidence confidence below safety floor or impossible")


@dataclass(frozen=True)
class LimitedActivationRequest:
    request_id: Any
    current_message: Any
    evidence_inputs: Any
    reference_time: Any
    requested_skill_id: Any
    explicit_activation_scope: Any
    policy_version: Any
    authority_inputs: Any = ()

    def __post_init__(self) -> None:
        for name in ("request_id", "current_message", "evidence_inputs", "reference_time",
                     "requested_skill_id", "explicit_activation_scope", "policy_version", "authority_inputs"):
            object.__setattr__(self, name, _freeze(getattr(self, name)))


@dataclass(frozen=True)
class LimitedActivationGateResult:
    gate: str
    passed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ActivationEvidenceItem:
    evidence_id: str
    canonical_type: str
    normalized_value: Any
    required: bool
    confidence: float | None
    source: str | None
    freshness: str | None
    freshness_sufficient: bool
    confidence_sufficient: bool
    assumed: bool
    user_confirmed: bool
    validation_rule: str
    validation_status: str
    mapping_status: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "normalized_value", _freeze(self.normalized_value))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class ActivationRequestBinding:
    binding_schema_version: str
    request_id: str
    requested_skill_id: str
    matched_skill_id: str
    current_message: str
    activation_scope: str
    reference_time: str
    registry_version: str
    matcher_version: str
    evidence_mapper_version: str
    gateway_policy_version: str
    candidate_score: float
    candidate_confidence: float
    evidence_confidence: float
    evidence_ready: bool
    evidence_snapshot: tuple[ActivationEvidenceItem, ...]
    binding_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_snapshot", tuple(self.evidence_snapshot))


@dataclass(frozen=True)
class LimitedActivationDenial:
    reason_codes: tuple[str, ...]
    first_failed_gate: str


@dataclass(frozen=True)
class LimitedActivationDecision:
    request_id: str
    decision: str
    requested_skill_id: str
    eligible_skill_id: str | None
    registry_version: str
    policy_version: str
    candidate_score: float | None
    candidate_confidence: float | None
    evidence_confidence: float | None
    gate_results: tuple[LimitedActivationGateResult, ...]
    reason_codes: tuple[str, ...]
    denial: LimitedActivationDenial | None
    binding: ActivationRequestBinding | None = None
    executed: bool = False
    calculated: bool = False
    reasoning_executed: bool = False
    runtime_routed: bool = False
    tools_invoked: bool = False
    persisted: bool = False
    follow_up_generated: bool = False
    response_generated: bool = False
    response_committed: bool = False


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if type(value) is Decimal:
        return canonicalize_activation_binding_decimal(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite binding value")
        return {"$float": format(value, ".17g")}
    if isinstance(value, tuple):
        if all(isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], str) for x in value):
            return {k: _canonical_value(v) for k, v in value}
        return [_canonical_value(x) for x in value]
    raise ValueError("unsupported binding value")


def canonicalize_activation_binding_decimal(value: Any) -> dict[str, Any]:
    """Return the current exact, typed Decimal binding material."""
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError("binding Decimal must be an exact finite Decimal")
    sign, digits, exponent = value.as_tuple()
    return {
        "$decimal": [
            "DECIMAL",
            ACTIVATION_BINDING_DECIMAL_SCHEMA_VERSION,
            sign,
            list(digits),
            exponent,
        ]
    }


def _binding_payload(binding: ActivationRequestBinding) -> dict[str, Any]:
    return {
        "binding_schema_version": binding.binding_schema_version, "request_id": binding.request_id,
        "requested_skill_id": binding.requested_skill_id, "matched_skill_id": binding.matched_skill_id,
        "current_message": binding.current_message, "activation_scope": binding.activation_scope,
        "reference_time": binding.reference_time, "registry_version": binding.registry_version,
        "matcher_version": binding.matcher_version, "evidence_mapper_version": binding.evidence_mapper_version,
        "gateway_policy_version": binding.gateway_policy_version, "candidate_score": _canonical_value(binding.candidate_score),
        "candidate_confidence": _canonical_value(binding.candidate_confidence),
        "evidence_confidence": _canonical_value(binding.evidence_confidence), "evidence_ready": binding.evidence_ready,
        "evidence_snapshot": [{name: _canonical_value(getattr(item, name)) for name in (
            "evidence_id", "canonical_type", "normalized_value", "required", "confidence", "source", "freshness",
            "freshness_sufficient", "confidence_sufficient", "assumed", "user_confirmed", "validation_rule",
            "validation_status", "mapping_status", "reason_codes")} for item in binding.evidence_snapshot],
    }


def _digest(binding: ActivationRequestBinding) -> str:
    raw = json.dumps(_binding_payload(binding), ensure_ascii=False, sort_keys=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_activation_request_binding(binding: Any) -> bool:
    """Verify integrity inside the trusted Gateway flow; this is not a signature or caller authentication."""
    try:
        if not isinstance(binding, ActivationRequestBinding) or binding.binding_schema_version != ACTIVATION_BINDING_SCHEMA_VERSION:
            return False
        strings = (binding.request_id, binding.requested_skill_id, binding.matched_skill_id, binding.current_message,
                   binding.activation_scope, binding.reference_time, binding.registry_version, binding.matcher_version,
                   binding.evidence_mapper_version, binding.gateway_policy_version)
        if any(not isinstance(x, str) or not x for x in strings): return False
        if binding.requested_skill_id != binding.matched_skill_id: return False
        if binding.activation_scope != SUPPORTED_ACTIVATION_SCOPE: return False
        if binding.registry_version != BUSINESS_SKILL_REGISTRY_VERSION: return False
        if binding.matcher_version != BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION: return False
        if binding.evidence_mapper_version != BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION: return False
        if binding.gateway_policy_version != LIMITED_ACTIVATION_GATEWAY_VERSION: return False
        ids = tuple(x.evidence_id for x in binding.evidence_snapshot)
        if any(not isinstance(x, ActivationEvidenceItem) or not x.evidence_id or not x.canonical_type for x in binding.evidence_snapshot): return False
        if len(ids) != len(set(ids)): return False
        canonical = _CANONICAL_EVIDENCE_ORDER.get(binding.matched_skill_id)
        if canonical is None or any(x not in canonical for x in ids): return False
        if tuple(sorted(binding.evidence_snapshot, key=lambda x: canonical.index(x.evidence_id))) != binding.evidence_snapshot: return False
        return bool(_LOWER_HEX_DIGEST.fullmatch(binding.binding_digest)) and binding.binding_digest == _digest(binding)
    except (TypeError, ValueError, AttributeError):
        return False


def _make_binding(rid: str, skill_id: str, msg: str, scope: str, ref: str, policy_version: str,
                  top: dict[str, Any], mapped: dict[str, Any]) -> ActivationRequestBinding:
    order = _CANONICAL_EVIDENCE_ORDER[skill_id]
    items = tuple(sorted((ActivationEvidenceItem(
        x["field_name"], x["expected_field_type"], x["observed_value"], x["required"], x["observed_confidence"],
        x["observed_source"], x["observed_freshness"], x["freshness_sufficient"], x["confidence_sufficient"],
        x["assumed"], x["user_confirmed"], x["validation_rule"], x["validation_status"], x["mapping_status"],
        tuple(x["reasons"])) for x in mapped["evidence_mappings"] if x["value_present"]),
        key=lambda x: order.index(x.evidence_id)))
    base = ActivationRequestBinding(ACTIVATION_BINDING_SCHEMA_VERSION, rid, skill_id, top["skill_id"], msg.strip(), scope,
        ref, BUSINESS_SKILL_REGISTRY_VERSION, BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION, BUSINESS_SKILL_EVIDENCE_MAPPER_VERSION,
        policy_version, top["candidate_score"], top["candidate_confidence"], mapped["evidence_confidence_floor"],
        mapped["evidence_ready"], items, "")
    return ActivationRequestBinding(**{**base.__dict__, "binding_digest": _digest(base)})


@dataclass(frozen=True)
class LimitedActivationDecisionBatch:
    gateway_version: str
    decisions: tuple[LimitedActivationDecision, ...]


def _gate(name: str, reasons: Iterable[str]) -> LimitedActivationGateResult:
    codes = tuple(dict.fromkeys(reasons))
    return LimitedActivationGateResult(name, not codes, codes or ("PASSED",))


def decide_limited_activation(request: Any, policy: LimitedActivationPolicy | None = None) -> LimitedActivationDecision:
    policy = LimitedActivationPolicy() if policy is None else policy
    if not isinstance(policy, LimitedActivationPolicy): raise ValueError("policy must be LimitedActivationPolicy")
    valid_type = isinstance(request, LimitedActivationRequest)
    if not valid_type:
        request = LimitedActivationRequest("", "", {}, None, "", "", "")
    rid, msg, ref = (_thaw(request.request_id), _thaw(request.current_message), _thaw(request.reference_time))
    skill_id, scope, version = (_thaw(request.requested_skill_id), _thaw(request.explicit_activation_scope), _thaw(request.policy_version))
    evidence, authority = _thaw(request.evidence_inputs), _thaw(request.authority_inputs)
    validity = []
    if not valid_type: validity.append("MALFORMED_REQUEST")
    if not isinstance(rid, str) or not rid.strip() or rid != rid.strip(): validity.append("INVALID_REQUEST_ID")
    if not isinstance(msg, str) or not msg.strip(): validity.append("EMPTY_CURRENT_MESSAGE")
    if not isinstance(ref, str) or not ref.strip(): validity.append("REFERENCE_TIME_REQUIRED")
    if version != policy.policy_version: validity.append("UNSUPPORTED_POLICY_VERSION")
    if not isinstance(evidence, dict): validity.append("MALFORMED_EVIDENCE_INPUTS")
    registry = get_business_skill_registry()
    # Discovery retains canonical matcher's own floor; gateway policy is a
    # separate confidence gate and must not turn a weak candidate into "none".
    candidates = match_business_skill_candidates(msg if isinstance(msg, str) else "", registry, limit=None)
    top = candidates[0] if candidates else None
    canonical = next((x for x in registry if x.skill_id == skill_id), None)
    identity = []
    if skill_id not in SUPPORTED_SKILL_IDS: identity.append("UNKNOWN_OR_UNSUPPORTED_REQUESTED_SKILL")
    if top is None: identity.append("NO_CANDIDATE")
    elif top["skill_id"] != skill_id: identity.append("CANDIDATE_SKILL_MISMATCH")
    lifecycle = [] if canonical is not None and canonical.active_status == LIMITED_ACTIVE else ["LIFECYCLE_NOT_LIMITED_ACTIVE"]
    scope_reasons = [] if scope == SUPPORTED_ACTIVATION_SCOPE else ["ACTIVATION_SCOPE_NOT_ALLOWED"]
    confidence = []
    if top is None: confidence.append("CANDIDATE_CONFIDENCE_UNAVAILABLE")
    elif top["candidate_score"] < policy.minimum_candidate_score or top["candidate_confidence"] < policy.minimum_candidate_confidence:
        confidence.append("CANDIDATE_CONFIDENCE_BELOW_THRESHOLD")
    mapped = map_candidate_skill_evidence(top, evidence, registry) if top is not None and isinstance(evidence, dict) else {}
    evidence_reasons = []
    if not mapped.get("evidence_ready"): evidence_reasons.append("EVIDENCE_NOT_READY")
    floor = mapped.get("evidence_confidence_floor")
    if floor is None or floor < policy.minimum_evidence_confidence: evidence_reasons.append("EVIDENCE_CONFIDENCE_BELOW_THRESHOLD")
    for item in mapped.get("evidence_mappings", ()):
        if item.get("blocking"): evidence_reasons.append(f"EVIDENCE_{item.get('mapping_status')}:{item.get('field_name')}")
    known_evidence = {item.get("field_name") for item in mapped.get("evidence_mappings", ())}
    if isinstance(evidence, dict):
        for unknown in sorted(set(map(str, evidence)) - known_evidence):
            evidence_reasons.append(f"EVIDENCE_UNKNOWN:{unknown}")
    ambiguity = ["COMPETING_CANDIDATES"] if len(candidates) > 1 else []
    current = [] if top is not None and top.get("matched_intent_patterns") or top is not None and top.get("matched_example_questions") else ["CURRENT_MESSAGE_DOES_NOT_SUPPORT_REQUEST"]
    authority_reasons = []
    if authority not in (None, (), [], {}): authority_reasons.append("AUTHORITY_BEARING_INPUT_REJECTED")
    if isinstance(evidence, dict) and _AUTHORITY_KEYS.intersection(evidence): authority_reasons.append("AUTHORITY_BEARING_INPUT_REJECTED")
    gates = (_gate(GATE_ORDER[0], validity), _gate(GATE_ORDER[1], identity), _gate(GATE_ORDER[2], lifecycle),
             _gate(GATE_ORDER[3], scope_reasons), _gate(GATE_ORDER[4], confidence),
             _gate(GATE_ORDER[5], evidence_reasons), _gate(GATE_ORDER[6], ambiguity),
             _gate(GATE_ORDER[7], current), _gate(GATE_ORDER[8], authority_reasons))
    failures = tuple(code for gate in gates for code in gate.reason_codes if code != "PASSED")
    passed = not failures
    denial = None if passed else LimitedActivationDenial(failures, next(x.gate for x in gates if not x.passed))
    binding = (_make_binding(rid, skill_id, msg, scope, ref, policy.policy_version, top, mapped) if passed else None)
    return LimitedActivationDecision(str(rid) if isinstance(rid, str) else "", LIMITED_EXECUTION_ELIGIBLE if passed else LIMITED_EXECUTION_DENIED,
        str(skill_id) if isinstance(skill_id, str) else "", skill_id if passed else None, BUSINESS_SKILL_REGISTRY_VERSION,
        policy.policy_version, top.get("candidate_score") if top else None, top.get("candidate_confidence") if top else None,
        floor, gates, failures or ("ALL_ELIGIBILITY_GATES_PASSED",), denial, binding)


def decide_limited_activations(requests: Iterable[Any], policy: LimitedActivationPolicy | None = None) -> LimitedActivationDecisionBatch:
    try: items = tuple(requests)
    except TypeError: items = (requests,)
    ids = [(_thaw(x.request_id) if isinstance(x, LimitedActivationRequest) else None) for x in items]
    duplicate_ids = {x for x in ids if x is not None and ids.count(x) > 1}
    decisions = []
    for item in items:
        decision = decide_limited_activation(item, policy)
        if decision.request_id in duplicate_ids:
            gates = tuple(_gate(g.gate, tuple(c for c in g.reason_codes if c != "PASSED") + (("DUPLICATE_REQUEST_ID",) if g.gate == "REQUEST_VALIDITY" else ())) for g in decision.gate_results)
            reasons = tuple(c for g in gates for c in g.reason_codes if c != "PASSED")
            decision = LimitedActivationDecision(decision.request_id, LIMITED_EXECUTION_DENIED, decision.requested_skill_id, None,
                decision.registry_version, decision.policy_version, decision.candidate_score, decision.candidate_confidence,
                decision.evidence_confidence, gates, reasons, LimitedActivationDenial(reasons, next(g.gate for g in gates if not g.passed)))
        decisions.append(decision)
    return LimitedActivationDecisionBatch(LIMITED_ACTIVATION_GATEWAY_VERSION, tuple(decisions))
