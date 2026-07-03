# RFC-002: Authority Is Not A Cognitive Layer

# Status

Accepted

# Context

SME Brain requires explicit responsibility for judgment, decision, constraint, and commitment. As the cognitive architecture expanded, Authority became necessary to prevent hidden ownership and overlapping control.

The architectural problem was whether Authority should be modeled as another cognitive layer in the reasoning flow or as a constitutional governance structure above the flow.

If Authority were treated as a cognitive layer, it could be misunderstood as one step among others, similar to Perception, Evidence, Business Judgment, or Decision. That would weaken its role. Authority does not merely transform inputs into outputs. Authority determines who owns a class of responsibility and which boundaries other cognitive responsibilities must respect.

SME Brain also needed to avoid a "God Brain" in which one vague center implicitly owns every decision. Without Authority, components, workflows, tools, memory, or language models could silently assume control over decisions they should only inform.

# Decision

Authority governs cognition but is not itself a cognitive layer.

Authority is constitutional. Cognitive layers perform reasoning responsibilities. Authority defines ownership of those responsibilities.

The accepted architecture separates responsibility governance from cognitive operation. Business Situation Authority owns situation framing. Evidence Authority owns evidence representation and quality evaluation. Truth Authority owns truth status. Business Judgment Authority owns judgment. Decision Authority owns selection of next action. Other authorities own their respective constitutional responsibilities.

Authority may constrain, delegate, challenge, or require explanation, but it does not become a sequential reasoning stage. It is the responsibility model that makes each stage accountable.

# Alternatives Considered

Modeling Authority as the first cognitive layer was rejected because Authority does not observe, classify, judge, decide, or communicate in the same sense as cognitive layers. It governs ownership of those acts.

Modeling Authority as the final approval layer was rejected because authority is not merely a gate at the end. Responsibility must shape cognition throughout the reasoning process, not only after an answer has been formed.

Allowing each component to carry its own implicit authority was rejected because it would create hidden control. Skills, tools, memory, workflow, and conversation mechanisms could begin making decisions outside their proper responsibility.

Centralizing all authority in a single Brain owner was rejected because it would make architecture unreviewable. A single undifferentiated authority cannot explain which responsibility controlled a decision or why another responsibility did not.

# Consequences

The positive consequence is clear accountability. SME Brain can identify which authority owns a decision, which authorities contributed, and which constraints applied.

This prevents subordinate mechanisms from becoming hidden governors of cognition. A workflow may execute a procedure, but it does not own judgment. A tool may return information, but it does not own truth. Memory may contribute context, but it does not own current reality.

The negative consequence is additional conceptual discipline. Contributors must distinguish authority from layer, responsibility from component, and governance from execution.

Authority boundaries may also require future architectural review when a new capability appears to span multiple responsibilities.

# Constitutional Impact

This RFC protects SME Brain from hidden or overlapping control.

It establishes that Authority is the constitutional responsibility model for cognition. It is not a layer that can be reordered, skipped, replaced, or merged into workflow execution.

The decision strengthens the constitutional architecture by requiring every major judgment, decision, persistence act, execution act, and user-facing commitment to remain traceable to an owning authority.

# Future Evolution

Future versions may refine the Authority Map as SME Brain matures. New authorities may be introduced when a stable responsibility cannot be governed by an existing authority without overlap or ambiguity.

Such evolution must preserve the distinction between Authority and cognitive layers. A future authority may govern a new responsibility, but it must not become a hidden procedural step or a vague super-component.

Authority should continue to define ownership, not mechanism.
