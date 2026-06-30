# Business Skill Standard

## Purpose

Every V5 Business Skill must follow one canonical schema so skills can be searched, ranked, reasoned over, tested, and used by workflows consistently.

The schema is documentation-first and implementation-neutral.

## Canonical Schema

```yaml
skill_id: "NN.NNN.skill_slug"
skill_name: "Skill display name"
domain: "NN Domain Name"
intent: "What the owner or customer is trying to achieve"
description: "What this skill does and when it applies"
example_questions:
  - "Example owner question"
  - "Example customer message"
required_entities:
  - name: "entity_name"
    description: "Business meaning"
    required: true
required_memory:
  - memory_type: "store_profile | business_memory | workflow_memory | conversation_memory | knowledge_memory"
    fields:
      - "field_name"
workflow:
  workflow_id: "workflow_name_or_none"
  start_conditions:
    - "When this skill should start a workflow"
  continuation_conditions:
    - "When this skill should continue an active workflow"
business_rules:
  - "Rule the system must follow"
reasoning:
  principle: "Business principle"
  pattern:
    - "Observe signal"
    - "Identify business goal"
    - "Check facts and risk"
    - "Recommend next action"
response_style:
  tone: "Owner-friendly, practical, specific"
  format: "Short answer, checklist, table, script, summary, or workflow prompt"
follow_up:
  required_when:
    - "Condition requiring a follow-up question"
  examples:
    - "One practical next question"
diagnostics:
  match_signals:
    - "Signal that increases match confidence"
  reject_signals:
    - "Signal that should prevent this skill from matching"
confidence:
  high: "When intent, entities, and memory match"
  medium: "When intent matches but some data is missing"
  low: "When only weak signals match"
tools:
  required:
    - "tool_name_or_none"
  optional:
    - "tool_name_or_none"
future_extensions:
  - "Planned expansion"
```

## Field Definitions

### Skill ID

Stable unique ID using `domain.skill_number.slug`.

Example: `03.002.customer_says_expensive`.

The ID should not change when wording changes.

### Domain

One of the 20 V5 business domains. A skill may reference related domains, but it has one owning domain.

### Intent

The business meaning of the user request. Intent should describe the owner goal, not only the literal phrase.

### Description

The operational scope of the skill. It should explain when the skill applies and what outcome it supports.

### Example Questions

Representative owner or customer messages. Examples should include natural wording and incomplete data cases.

### Required Entities

The facts required to complete the skill. Required entities should be explicit enough for workflow collection.

### Required Memory

Memory needed to improve the answer or complete the workflow. Memory use must name the memory type and fields.

### Workflow

Defines whether the skill can start, continue, complete, or chain a workflow.

### Business Rules

Rules that must be followed. These may include margin protection, no guessing, compliance reminders, or customer trust safeguards.

### Reasoning

The business thinking pattern used by the Reasoning Engine. This should be explainable and not depend on keyword matching.

### Response Style

Guidance for how the owner-facing response should be composed.

### Follow-Up

Rules for asking one useful next question when data is missing or action is incomplete.

### Diagnostics

Signals that help developers understand why the skill matched or did not match.

### Confidence

Defines high, medium, and low confidence conditions for routing and fallback.

### Tools

Names required and optional tools. A tool can be a calculator, OCR extractor, document parser, database lookup, external integration, or LLM capability.

### Future Extensions

Notes for future product expansion without changing the canonical schema.

## Skill Quality Rules

- A skill must have one owning domain.
- A skill must define what data is required.
- A skill must define what to do when data is missing.
- A skill must include business reasoning, not only a response template.
- A skill must identify confidence conditions.
- A skill must be safe to use without modifying runtime behavior.
- A skill should be narrow enough to route accurately and broad enough to be useful.

