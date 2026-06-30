# V5 Workflow Architecture

## Purpose

Workflows are durable business processes that can span multiple turns. V5 treats workflows as first-class operating objects rather than incidental chat branches.

## Workflow Lifecycle

```text
Created
  |
  v
Collecting
  |
  v
Ready
  |
  v
Executing
  |
  v
Completed

Side states:
Paused
Interrupted
Cancelled
Failed
Chained
```

## Start

A workflow starts when:

- The user explicitly requests a structured task.
- Business Reasoning identifies a process requiring multiple fields.
- A skill requires workflow execution.
- A quick action invokes a workflow.
- A previous workflow chains into the next workflow.

Start should create workflow memory with required fields, collected fields, status, owner domain, owner skill, and diagnostics.

## Continue

A workflow continues when the user supplies missing information, confirms a step, corrects a field, or asks to proceed.

Continuation should:

- Resolve whether the message belongs to the active workflow.
- Extract new fields.
- Validate field completeness.
- Update missing fields.
- Produce the next prompt or result.

## Workflow Reuse

Reusable workflows should be defined independently of individual UI entry points.

A workflow can be reused by:

- Multiple skills.
- Quick actions.
- Planner decisions.
- LLM-assisted transformations.
- Dashboard or document surfaces.

Workflow definitions should not hardcode response wording. They should expose state and next action to Response Intelligence.

## Workflow Chaining

Workflow chaining allows one completed workflow to start or suggest another.

Examples:

- Product profile -> pricing workflow.
- Receipt OCR -> accounting categorization.
- Supplier comparison -> purchasing workflow.
- Sales objection handling -> follow-up workflow.
- Dashboard alert -> business intelligence diagnosis.

Chaining should be explicit. The owner should know whether a new workflow is being started automatically, suggested, or held for confirmation.

## Workflow Completion

A workflow completes when:

- Required fields are complete.
- Business rules pass.
- The intended output is generated.
- Completion memory is written.
- Active workflow lock is released.
- Any paused workflow can resume or remain paused.

Completion output should include:

- Result.
- Assumptions.
- Saved memory.
- Suggested next action.
- Diagnostics.

## Workflow Continuation After Completion

Users often continue after completion with corrections or follow-up requests.

V5 should support:

- Edit last workflow output.
- Reopen a completed workflow.
- Start a related workflow.
- Explain the completed result.
- Save or discard completion memory.

## Interruptions

An interruption occurs when the user asks a different question during an active workflow.

The system should decide whether to:

- Answer briefly and return to the workflow.
- Pause the workflow and handle the new request.
- Cancel the workflow.
- Ask the user to choose when ownership is ambiguous.

## Workflow Diagnostics

Each workflow decision should expose:

- Workflow ID.
- Status.
- Owner domain and skill.
- Collected fields.
- Missing fields.
- Last transition.
- Reason for transition.
- Confidence.
- Completion memory writes.

