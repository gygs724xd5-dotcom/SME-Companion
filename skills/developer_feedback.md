# Developer Feedback Skill

## Purpose
Route product feedback and Developer Mode diagnostics to existing Developer Intelligence surfaces.

## Required Inputs
- User feedback or developer diagnostic request
- Conversation context
- Developer Mode state when available

## Output
- Feedback classification
- Product learning signal
- Read-only platform diagnostics

## Workflow
1. Detect product feedback or developer intent.
2. Preserve user feedback through existing feedback modules.
3. Show planner, capability, skill, reasoning, workflow, and LLM diagnostics in Developer Mode.
4. Avoid changing business workflows.

## Limitations
- Does not auto-create tickets.
- Does not modify product backlog priorities directly.
- Does not change Developer Intelligence engines.

## Future improvements
- Automated issue grouping
- Sprint planning assistant
- Regression test recommendation engine
