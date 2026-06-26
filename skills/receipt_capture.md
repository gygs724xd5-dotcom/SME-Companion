# Receipt Capture Skill

## Purpose
Capture receipt upload intent and preserve receipt state for future processing.

## Required Inputs
- Receipt upload request or uploaded file
- Conversation state
- Receipt state

## Output
- Upload acknowledgement
- Receipt capture state
- Clear limitation that OCR is not implemented

## Workflow
1. Detect receipt or slip upload intent.
2. Route to receipt capture workflow.
3. Store uploaded file state when the UI receives a file.
4. Do not analyze receipt contents.

## Limitations
- OCR is not implemented.
- Receipt totals are not extracted.
- Costs are not automatically calculated from images.

## Future improvements
- OCR Engine
- Financial Agent
- Cost Calculation integration
