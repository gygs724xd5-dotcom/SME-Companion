# Dashboard Builder Skill

## Purpose
Route dashboard requests to the existing basic dashboard and product feedback flow.

## Required Inputs
- Dashboard request
- Store profile when available
- Existing business state when available

## Output
- Dashboard routing decision
- Feature request capture when dashboard needs exceed current scope
- Read-only current dashboard context

## Workflow
1. Detect dashboard intent.
2. Route to dashboard request workflow.
3. Record request as product feedback when needed.
4. Keep response deterministic.

## Limitations
- Does not build custom dashboards.
- Does not create new charts dynamically.
- Does not connect POS, inventory, or accounting systems.

## Future improvements
- Business Memory
- POS Sync
- Inventory Engine
