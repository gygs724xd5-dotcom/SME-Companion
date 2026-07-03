# RFC-003: Business Situation Runtime

# Status

Accepted

# Context

SME Brain needs to reason about the business owner's current reality. Earlier architecture already recognized Business Memory as a durable source of context about the business. However, memory alone cannot represent the live situation under attention.

The architectural problem was the distinction between what the system remembers and what is currently happening.

Business Memory may contain durable facts, prior observations, historical decisions, known preferences, business profile information, and past interactions. Those records are useful, but they are not automatically current reality. A stored fact may be stale, incomplete, contradicted by new evidence, or irrelevant to the present concern.

SME Brain needed a runtime structure for framing the current business situation without treating memory as the situation itself. It also needed a way to represent Current Business Reality: the best available understanding of what is happening now, under uncertainty, for the purpose of judgment and decision.

# Decision

SME Brain separates Business Memory from Business Situation Runtime.

Business Memory is durable context. Business Situation Runtime is the active cognitive frame for the present business concern.

Business Situation Runtime represents Current Business Reality. It frames the business state under attention, including relevant actors, constraints, risks, opportunities, objectives, uncertainty, and material context. It may use Business Memory, user input, evidence, knowledge, and other signals, but it does not merely replay them.

Current Business Reality is not absolute truth. It is the current, governed understanding of the situation that SME Brain can reason from. It may contain confirmed facts, observations, assumptions, hypotheses, unresolved conflicts, and uncertainty markers.

Business Situation Runtime exists so SME Brain can ask: What business reality is this user facing now, and what about that reality matters for judgment?

# Alternatives Considered

Using Business Memory as the situation model was rejected because memory is durable context, not live framing. Treating memory as current reality would cause stale or partial information to dominate present judgment.

Building each response directly from the current user message was rejected because business situations often require continuity. The current message may be only one signal within a larger ongoing reality.

Treating Business Situation as a workflow state was rejected because a business situation is not a procedural step. It is a cognitive frame that may change as evidence, truth status, perspective, and judgment evolve.

Treating Current Business Reality as confirmed truth was rejected because SME Brain often works under uncertainty. A useful situation frame must preserve assumptions, conflicts, and gaps rather than flatten them into facts.

# Consequences

The positive consequence is that SME Brain can reason about the present without losing the value of durable memory. Memory informs the situation, but the situation governs what memory means now.

This separation supports better judgment under uncertainty. The system can recognize that something is remembered, but not necessarily current, relevant, complete, or reliable for the present decision.

It also creates a clearer place for business context to be synthesized before judgment and decision occur.

The negative consequence is that future contributors must avoid collapsing durable memory and runtime situation into a single concept. The distinction adds architectural precision and requires careful language.

Another consequence is that situation framing becomes a first-class responsibility. It must be treated as cognition, not as simple retrieval or summarization.

# Constitutional Impact

This RFC establishes Business Situation Runtime as the constitutional frame for Current Business Reality.

It protects SME Brain from confusing stored business context with present business reality. It also protects the owner from decisions based on memory that has not been evaluated against the current situation.

The decision strengthens SME Brain's purpose: improving the business owner's situation requires first understanding which situation is actually under attention.

# Future Evolution

Future versions may enrich Business Situation Runtime with stronger representations of uncertainty, actor roles, timelines, business constraints, competing objectives, and situation change over time.

Business Memory may become more comprehensive and better organized. That evolution must not erase the runtime distinction. Memory can inform Current Business Reality, but it must not be treated as Current Business Reality by default.

Future extensions may also refine how situations persist, close, resume, or evolve, provided the architecture continues to distinguish durable memory from active situation framing.
