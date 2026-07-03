# RFC-004: Perception Runtime

# Status

Accepted

# Context

SME Brain needs to notice signals before it reasons about them. User messages, documents, memory, business records, tool outputs, conversation history, and environmental context can all contain signals relevant to cognition.

The architectural problem was whether Perception should merely observe these signals or also judge their meaning, truth, importance, or recommended action.

If Perception judged, it would collapse several cognitive responsibilities into the first contact point. It could decide what matters before Business Situation has framed the current reality. It could treat information as reliable before Evidence has evaluated it. It could imply truth before Truth Status has determined justified reliance. It could steer decisions before Business Judgment and Decision have acted.

SME Brain needed a clean boundary: Perception notices; later responsibilities interpret, evaluate, judge, and decide.

# Decision

Perception only observes.

Perception must never judge.

Perception identifies and preserves signals that may matter to cognition. It may notice entities, events, claims, documents, requests, changes, references, ambiguity, emotional tone, urgency, or possible relevance. It does not determine truth, decide importance, choose action, assign business meaning, or conclude what the user needs.

Perception supplies raw or lightly interpreted percepts to the rest of the cognitive architecture. Those percepts become meaningful only when Business Situation, Evidence, Truth Status, Perspective, Business Judgment, and Decision perform their respective responsibilities.

# Alternatives Considered

Allowing Perception to classify business meaning was rejected because business meaning depends on the current situation. The same signal can matter differently in different business contexts.

Allowing Perception to decide relevance was rejected because relevance depends on the situation frame and the decision context. Perception may flag possible relevance, but it must not make final relevance judgments.

Allowing Perception to determine truth was rejected because observation is not verification. A signal can be noticed without being reliable, current, complete, or true.

Allowing Perception to trigger immediate action was rejected because action requires judgment, authority, and decision. Perception can alert the system to possible urgency, but it must not decide the response.

# Consequences

The positive consequence is a cleaner cognitive architecture. Signals are preserved without prematurely converting them into conclusions.

This improves traceability. SME Brain can distinguish what was observed from what was later inferred, judged, or decided.

It also reduces the risk of early bias. Perception does not overfit the first signal into a business conclusion before the full situation and evidence are considered.

The negative consequence is that Perception may appear less powerful than a combined detection-and-decision system. More responsibility must be carried by later cognitive authorities.

Another consequence is that ambiguous signals may remain unresolved longer. That is intentional. Uncertainty should be preserved until the proper authority resolves or carries it.

# Constitutional Impact

This RFC protects the cognitive chain from premature judgment.

Perception becomes the constitutional boundary between signal intake and reasoning. By preventing Perception from judging, SME Brain preserves the difference between noticing, understanding, evaluating, believing, judging, deciding, and committing.

The decision strengthens SME Brain's reliability under uncertainty because observed information is not silently promoted into fact or action.

# Future Evolution

Future versions may make Perception more capable at noticing signal types, preserving context, detecting possible ambiguity, or identifying candidate relationships.

Those extensions must not give Perception authority to judge truth, importance, business meaning, or action. More sophisticated observation is allowed. Premature judgment is not.

Perception may evolve to support richer percepts, but those percepts must remain inputs to cognition rather than conclusions of cognition.
