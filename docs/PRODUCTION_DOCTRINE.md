# Production Doctrine

SME Companion is a production AI-native Business Operating System for SME owners. The product must prioritize trustworthy business operations over conversational novelty.

## Non-Negotiables

- Planner is the decision maker.
- Workflow executes deterministic business steps.
- Reasoning explains why a route or action was chosen.
- Response communicates the selected action to the owner.
- LLMs may improve language, but must not replace planner, workflow, inventory, revenue, or business memory truth.
- Generic fallback is allowed only when conversation understanding, intent resolution, planner, workflow, and memory all fail to resolve a useful next step.

## Production Data Rules

- Business data is source of truth for store context.
- Inventory ledger is source of truth for stock.
- Revenue records are source of truth for sales.
- Expense records are source of truth for cost.
- OCR output is untrusted until validated and converted into structured records.

## Compatibility

Working deterministic engines must be extended, not rewritten. New layers should be additive and preserve existing module contracts.
