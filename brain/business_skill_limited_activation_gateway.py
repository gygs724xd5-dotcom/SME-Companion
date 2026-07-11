"""V5.15.14 pure, deny-by-default limited activation eligibility gateway.

Eligibility is only permission to enter a *limited execution path*.  This
module neither executes a skill nor owns runtime, response, tool, or storage
authority.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from brain.business_skill import LIMITED_ACTIVE
from brain.business_skill_candidate_matcher import match_business_skill_candidates
from brain.business_skill_evidence_mapper import map_candidate_skill_evidence
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry

LIMITED_ACTIVATION_GATEWAY_VERSION = "5.15.14"
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
    executed: bool = False
    calculated: bool = False
    reasoning_executed: bool = False
    runtime_routed: bool = False
    tools_invoked: bool = False
    persisted: bool = False
    follow_up_generated: bool = False
    response_generated: bool = False
    response_committed: bool = False


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
    return LimitedActivationDecision(str(rid) if isinstance(rid, str) else "", LIMITED_EXECUTION_ELIGIBLE if passed else LIMITED_EXECUTION_DENIED,
        str(skill_id) if isinstance(skill_id, str) else "", skill_id if passed else None, BUSINESS_SKILL_REGISTRY_VERSION,
        policy.policy_version, top.get("candidate_score") if top else None, top.get("candidate_confidence") if top else None,
        floor, gates, failures or ("ALL_ELIGIBILITY_GATES_PASSED",), denial)


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
