# RFC-001: Cognitive Constitution

# Status

Accepted

# Context

SME Brain evolved from a workflow-centered product architecture into a system expected to help business owners reason about ambiguous business situations.

Workflow systems are effective when the task is already known, the sequence is stable, required inputs are clear, and success can be defined as completion of a procedure. They are weak when the user is asking for judgment, interpretation, prioritization, or help under uncertainty.

The architectural problem was that expanding workflow systems would make SME Brain more procedurally capable while leaving the center of cognition unchanged. A larger workflow library would still ask what step comes next. SME Brain needed to ask what the business owner needs now, what situation the business is in, what evidence matters, what uncertainty remains, and what action would improve the business situation.

Without a constitutional cognitive architecture, future contributors could continue adding planners, routers, skills, and workflows until those mechanisms became the de facto Brain. That would preserve procedural control while obscuring responsibility for judgment.

# Decision

SME Brain adopts a Constitutional Cognitive Architecture.

The Constitution defines the stable cognitive responsibilities of SME Brain before execution mechanisms are selected. It establishes that SME Brain is organized around contextual business judgment, not procedural completion.

Workflow, planning, routing, skills, tools, and execution mechanisms may remain valuable, but they are subordinate instruments. They do not define the architecture. They are used only when the constitutional cognitive authorities determine that they are appropriate for the current business situation.

The adopted architecture treats cognition as a governed structure of responsibilities: perception, business situation framing, evidence representation, truth status, perspective, knowledge, business judgment, decision, execution, conversation, and commit. These responsibilities define how SME Brain thinks, regardless of how any future version implements them.

# Alternatives Considered

Expanding workflow coverage was rejected because it would improve procedural reach without solving the core cognitive problem. More workflows would help with known repeatable tasks, but they would not create judgment.

Renaming workflows as goals, missions, journeys, or plans was rejected because terminology does not change control. If the system still detects an intent, collects fields, follows a path, and treats missing inputs as blockers, the architecture remains procedural.

Using a general planner as the primary intelligence layer was rejected because planning is not judgment. Planning can sequence activity, but it does not by itself determine what matters, what is true enough, what perspective applies, or what help is appropriate.

Letting a foundation model act as an implicit Brain was rejected because model behavior is not an architectural contract. A model may produce fluent reasoning, but without constitutional boundaries the system cannot preserve responsibility, authority, or durable cognitive principles across models and versions.

# Consequences

The positive consequence is that SME Brain has a stable architectural center. Future capabilities can be evaluated by whether they serve constitutional cognition rather than by whether they add another procedural path.

The architecture makes responsibility more explicit. It becomes possible to ask which authority owns a judgment, decision, constraint, or commitment.

The approach also prevents workflow expansion from silently becoming product strategy. Workflows remain useful but cannot govern cognition.

The negative consequence is that architecture becomes more demanding. Contributors must understand cognitive responsibility boundaries before adding major behavior. Some simple procedural features may require clearer placement within the constitutional model.

The architecture may also feel less immediately concrete than workflow design. It defines why the system thinks a certain way before defining how a mechanism executes that thinking.

# Constitutional Impact

This RFC establishes the Constitution as the highest architectural frame for SME Brain.

SME Brain is defined by judgment-centered cognition. It exists to improve the business owner's situation through contextual business judgment. Its permanent architecture is not the set of workflows it can run, the tools it can call, or the model it uses to produce language.

All future architectural changes must preserve the distinction between cognition and procedure. Procedure may serve cognition. Procedure must not replace cognition.

# Future Evolution

Future versions may add new authorities, refine existing cognitive responsibilities, or introduce stronger execution mechanisms, provided they remain subordinate to constitutional cognition.

Workflow systems may become more capable, adaptive, or specialized. That evolution is valid only if workflows continue to execute under cognitive authority rather than becoming the source of judgment.

The Constitution may be extended as SME Brain encounters new classes of business reasoning, but extensions must preserve the principle that architecture defines responsibility before mechanism.
