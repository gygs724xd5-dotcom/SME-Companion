# Cost Calculation Skill

## Purpose
Calculate basic cost and margin from user-provided ingredient or item costs.

## Required Inputs
- Ingredient or item costs
- Total units produced
- Optional target selling price

## Output
- Total cost
- Cost per unit
- Margin estimate when selling price is available
- Missing input prompt when incomplete

## Workflow
1. Collect cost line items.
2. Collect total unit count.
3. Calculate deterministic cost outputs.
4. Ask for missing inputs when needed.

## Limitations
- Does not read receipts with OCR.
- Does not import supplier invoices.
- Does not update accounting records.

## Future improvements
- OCR Engine
- Financial Agent
- Supplier cost history
