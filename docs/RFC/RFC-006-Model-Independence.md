# RFC-006: Model Independence

# Status

Accepted

# Context

SME Brain depends on foundation models for language understanding and generation, but its architecture must not be defined by any particular model.

The architectural problem was whether the intelligence of SME Brain should be treated as the behavior of a selected model or as a constitutional reasoning architecture that models help execute.

Foundation models change over time. They vary in reasoning style, reliability, cost, latency, context handling, tool use, and conversational behavior. A model can produce persuasive language without preserving SME Brain's authority boundaries, evidence discipline, truth status, business judgment, or commit rules.

If SME Brain were defined by model behavior, then changing models would change the architecture. That would make the system unstable and would weaken the permanent architectural history of the product.

# Decision

SME Brain adopts Model Independence.

The constitutional reasoning architecture defines SME Brain. Foundation models execute language generation and may assist with interpretation, synthesis, and expression, but they do not define the architecture.

The Brain is the governed cognitive structure: its authorities, responsibilities, boundaries, and decision principles. A model may help carry out those responsibilities, but it is not the source of constitutional authority.

Model Independence means that SME Brain should remain recognizable across model upgrades, provider changes, and future language-generation mechanisms. The model is an execution dependency. The Constitution is the architecture.

# Alternatives Considered

Defining SME Brain as a prompt over a foundation model was rejected because prompts are not durable architecture. They can express instructions, but they do not by themselves establish permanent responsibility boundaries.

Choosing the strongest available model as the Brain was rejected because model capability does not equal constitutional governance. A capable model may still blur evidence, truth, judgment, policy, and conversation unless the architecture constrains it.

Optimizing architecture around one provider or model family was rejected because it would make SME Brain vulnerable to external model changes and would reduce long-term portability.

Treating model output as final reasoning was rejected because language generation can be fluent without being properly governed, sourced, or aligned with business judgment.

# Consequences

The positive consequence is architectural durability. SME Brain can evolve across model generations without redefining its cognitive identity.

This supports portability, resilience, and clearer evaluation. A model can be judged by how well it serves SME Brain's Constitution rather than by whether its default behavior appears intelligent.

The decision also protects constitutional boundaries. Authority, Evidence, Truth Status, Business Judgment, Decision, Conversation, and Commit remain architectural responsibilities rather than model tendencies.

The negative consequence is that model integration must be disciplined. Contributors cannot rely on model fluency as a substitute for architecture.

Another consequence is that some model-specific capabilities may remain subordinate even when they are powerful. Capability does not create authority.

# Constitutional Impact

This RFC defines SME Brain as architecture, not model behavior.

Foundation models are instruments of expression and reasoning support. They do not own cognition, authority, truth, judgment, decision, or commitment.

The decision ensures that SME Brain's constitutional identity survives model replacement and that future contributors evaluate models as servants of the architecture.

# Future Evolution

Future versions may use stronger models, multiple models, specialized models, local models, or non-model reasoning aids.

Those changes may improve quality, speed, cost, or capability, but they must not redefine SME Brain's constitutional reasoning architecture.

Model Independence may evolve into richer evaluation standards for model behavior, but those standards must measure service to the Constitution rather than replace the Constitution.
