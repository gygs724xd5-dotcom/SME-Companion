# RFC-005: Evidence Runtime

# Status

Accepted

# Context

SME Brain must reason from information of different kinds and quality. User statements, memory, documents, business records, knowledge, tool outputs, and external sources can all inform a business situation.

The architectural problem was how to represent information without allowing information itself to determine truth.

Evidence is necessary because not all information deserves equal reliance. Some information is fresh, direct, and specific. Some is stale, indirect, incomplete, or contradicted. Some supports a claim only weakly. Some is relevant only under a particular business frame.

However, evidence is not truth. A document, memory item, tool result, or user statement may support a claim, but it does not automatically establish what SME Brain should treat as true. That responsibility belongs to Truth Status, informed by Evidence but not replaced by it.

# Decision

Evidence only represents information.

Evidence must never determine truth.

Evidence classifies and evaluates information that may support, challenge, refine, or change understanding of the current business situation. It preserves source awareness, relevance, reliability, freshness, completeness, directness, conflicts, limitations, and confidence.

Evidence may suggest candidate truth status or expose the strength of support for a claim. It does not decide that a claim is true, false, assumed, unresolved, or sufficiently reliable for action. Truth Status owns justified reliance.

This separation ensures that SME Brain can reason with information without confusing information quality with belief.

# Alternatives Considered

Treating evidence as fact was rejected because source material can be wrong, outdated, partial, or misunderstood.

Letting tools determine truth was rejected because tool output is still information. It may be useful evidence, but it must be evaluated in context.

Letting memory determine truth was rejected because remembered information may not reflect the current business reality.

Merging Evidence and Truth Status was rejected because support and belief are different responsibilities. Evidence explains why a claim may be supported. Truth Status determines how that claim may be relied upon for the current decision.

Ignoring evidence quality was rejected because SME Brain would then treat all inputs as equivalent. That would weaken judgment and make explanations less reliable.

# Consequences

The positive consequence is disciplined reasoning under uncertainty. SME Brain can preserve multiple pieces of information, compare their quality, expose conflicts, and avoid premature certainty.

The architecture also improves explainability. It can distinguish the information available from the truth status ultimately assigned.

This decision protects against over-trusting memory, tool results, documents, or fluent model output.

The negative consequence is additional architectural complexity. Evidence representation must remain separate from truth determination, judgment, and decision.

Another consequence is that SME Brain may carry unresolved conflicts rather than forcing a single conclusion. That can require more careful communication to the user.

# Constitutional Impact

This RFC establishes Evidence as a constitutional responsibility distinct from Truth Status.

SME Brain is required to treat information as support, not as automatic truth. Evidence Authority owns representation and quality evaluation. Truth Authority owns justified reliance.

The decision strengthens the epistemic discipline of SME Brain and prevents subordinate information sources from becoming hidden truth-makers.

# Future Evolution

Future versions may extend evidence representation with richer source types, stronger conflict handling, better freshness awareness, and more precise confidence language.

Those extensions must preserve the constitutional boundary: Evidence may inform truth, but it must not determine truth.

Evidence may become more structured and more expressive over time, but truth determination must remain a separate governed responsibility.
