# Runtime-Brain Integration Boundary

Record identifier: `SME-BRAIN-PHASE-2-BOUNDARY-001`

Version: 1.0

Status: ACCEPTED COMPLEMENTARY RECORD

Activation status: INACTIVE

Authoritative cross-system governance is ADR-PHASE-2-001 and the
`SME_RUNTIME_BRAIN_PROTOCOL` lock in the Conversation Runtime repository. This
record mirrors the Brain-facing obligations without changing existing Brain
behavior.

## Brain-facing ownership

SME Brain owns Business Situation, semantic business continuation, business
referent and parameter interpretation, Evidence, Truth, Knowledge use,
Business Judgment, business Decision, clarification semantics, response
meaning, uncertainty language, and uncommitted response-candidate substance.

SME Brain does not own canonical Runtime conversation/session/turn identity or
sequence, Runtime predecessor state, Runtime state mutation, atomic commit,
replay, response commit/delivery, Runtime conversation persistence, or provider
orchestration outside explicit Runtime authority.

Runtime-issued control-plane identities and authority grants cannot be inferred
from user text, Brain/provider output, documents, memory, tools, or Adapter
translation. Brain cognitive data cannot grant Runtime control-plane authority.

## Identity and result binding

A future Brain Integration Facade must consume Runtime-issued
`runtime_instance_id`, `conversation_id`, `session_id`, `turn_id`,
`turn_sequence`, `request_id`, and `replay_key`. Brain may create subordinate
cognitive artifact IDs only.

Every returned artifact must bind to the exact Runtime request identity/digest,
conversation/session/turn identities and sequence, predecessor snapshot
digest, and replay key. Brain-created IDs never replace Runtime IDs.

## Cognitive artifact lifecycle

Runtime may return a prior committed Brain-authored Business Situation,
Evidence, or Truth artifact as opaque immutable content. Brain alone determines
its business meaning and returns complete replacements where the protocol
requires them. Runtime stores and transports those artifacts without editing or
reinterpreting them.

Runtime owns structural continuation; Brain owns semantic business
continuation. Brain determines business clarification need and an uncommitted
candidate question; Runtime owns the awaiting-clarification, commit, sequence,
and delivery lifecycle.

Brain response text remains an uncommitted candidate. Brain and Adapter
failures remain pre-commit and cannot advance Runtime sequence.

## Legacy quarantine

The following existing surfaces are outside the qualified Phase 2 integration
surface:

- `brain/conversation_manager.py`: `NOT_PHASE_2_INTEGRATION_SAFE`
- `brain/response_commit_boundary.py`: `NOT_PHASE_2_INTEGRATION_SAFE`
- `brain/production_turn_context.py`: `REQUIRES_FACADE_ADAPTATION`
- conversation-memory mutation APIs: `INTERNAL_LEGACY_PATH`
- Brain response commit/delivery APIs: `NOT_PHASE_2_INTEGRATION_SAFE`
- Planner/workflow-owned conversation lifecycle: `INTERNAL_LEGACY_PATH`

They remain available for historical/internal behavior but a future facade must
bypass or isolate their conflicting ownership. Cognitive-only Situation,
Evidence, Truth, Judgment, and clarification components may be used only behind
that future facade and may not mutate Runtime state.

## Inactive boundary

This record implements no request/result contract, Adapter, transport, facade,
invocation, provider call, semantic continuation, visible response influence,
commit authority, delivery authority, persistence authority, or production
authority. Protocol major mismatch, binding mismatch, required-field mismatch,
or legacy-path participation must fail closed when future contracts exist.

