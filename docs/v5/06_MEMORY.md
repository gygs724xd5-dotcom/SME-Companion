# V5 Memory Architecture

## Purpose

Memory in V5 exists to support business continuity. It should preserve useful state without mixing display history, workflow progress, business facts, and diagnostics into the same structure.

## Memory Types

```text
Conversation Memory
Business Memory
Store Memory
Workflow Memory
Transformation Memory
Knowledge Memory
```

## Conversation Memory

Conversation Memory owns conversational continuity.

It stores:

- Recent turn summaries.
- Current topic.
- Resolved references.
- Last user intent.
- Last assistant action.
- Active interruption context.
- Clarification state.

It does not own permanent business facts unless those facts are promoted to Business Memory or Store Memory.

## Business Memory

Business Memory owns event-level and learned business facts.

It stores:

- Business events.
- Customer interactions.
- Sales observations.
- Product notes.
- Supplier issues.
- Owner preferences.
- Completed workflow summaries.
- Historical decisions.

Every business memory item should include source, timestamp, confidence, and owner.

## Store Memory

Store Memory owns durable store profile facts.

It stores:

- Store name.
- Business type.
- Location and channels.
- Product categories.
- Operating model.
- Staff or role basics.
- Owner-defined preferences.

Store Memory is higher authority than inferred Business Memory for stable facts.

## Workflow Memory

Workflow Memory owns active and historical workflow state.

It stores:

- Active workflow ID.
- Workflow status.
- Collected fields.
- Missing fields.
- Validation state.
- Paused workflow stack.
- Completion summary.
- Chained workflow references.

Workflow Memory should be the only owner of workflow progress.

## Transformation Memory

Transformation Memory owns structured outputs derived from raw inputs.

It stores:

- Source input reference.
- Extracted fields.
- Normalized records.
- Generated documents.
- Draft scripts.
- Dashboard definitions.
- Correction history.
- Transformation confidence.

Transformation Memory allows the system to revise, reuse, and audit generated business assets.

## Knowledge Memory

Knowledge Memory owns what the system learned about knowledge usage.

It stores:

- Skills used.
- Domain match history.
- Knowledge gaps.
- Repeated owner needs.
- Failed matches.
- Suggested new skills.
- Doctrine or rule conflicts.

Knowledge Memory is for improving the system and diagnostics. It should not become a hidden source of business truth.

## State Ownership

| State | Owner |
| --- | --- |
| Rendered transcript | UI or Conversation Log |
| Current topic and reference | Conversation Memory |
| Stable store profile | Store Memory |
| Learned business fact | Business Memory |
| Active workflow progress | Workflow Memory |
| Generated structured output | Transformation Memory |
| Skill usage and gaps | Knowledge Memory |
| Final response for a turn | Response Envelope |

## Memory Priority

When facts conflict, V5 should prefer:

1. Current user message.
2. Active workflow fields.
3. Store Memory.
4. Recent Conversation Memory.
5. Business Memory.
6. Transformation Memory.
7. Knowledge Memory.

The response should disclose uncertainty when the selected fact is inferred or stale.

## Memory Write Rules

- Do not write everything.
- Write only facts that improve future business continuity.
- Include source and confidence.
- Prefer explicit owner confirmation for durable store facts.
- Expire or downgrade stale operational facts.
- Keep diagnostics separate from business truth.

