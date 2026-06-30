# SME Companion V5 System Vision

## Purpose

SME Companion V5 defines the next-generation AI-native Business Operating System for small and medium businesses. V5 builds on the completed V4 foundation by turning the product from a helpful chat interface into a persistent business companion that understands the owner, the store, the business state, active workflows, and long-term goals.

V5 is an architecture target. It does not describe a runtime change by itself.

## What SME Companion Becomes

In V5, SME Companion becomes the operating layer for running a small business:

- It understands business context across products, customers, inventory, pricing, documents, operations, sales, accounting, marketing, suppliers, HR, and executive decisions.
- It remembers useful facts with clear ownership and expiry rules.
- It recommends next actions instead of only answering isolated questions.
- It can continue work across turns, sessions, and workflows.
- It can explain business reasoning in practical owner language.
- It can transform raw owner input into structured business assets such as product records, sales scripts, purchase plans, dashboards, reports, and customer follow-ups.

The system should feel less like a chatbot and more like a business partner that is always aware of what is being built, what is missing, what risk exists, and what should happen next.

## AI-First Business Operating System

V5 treats AI as the coordination layer of the business system, not as a text generator attached to a form.

The AI-native operating system has five responsibilities:

1. Understand the owner request and business situation.
2. Select the right domain, skill, workflow, memory, and tools.
3. Reason about the business tradeoff.
4. Produce or continue useful work.
5. Preserve the right memory for future turns.

The LLM is not the architecture. The LLM is one execution component used after conversation intelligence, business knowledge, reasoning, workflow, memory, and response intelligence have prepared the turn.

## Business Companion, Not Chatbot

A chatbot answers a prompt. A business companion manages business continuity.

V5 should support:

- Contextual advice based on the store and owner history.
- Workflow continuation when the owner provides missing information later.
- Proactive surfacing of gaps, risks, and next steps.
- Practical business language instead of generic assistant language.
- Clear escalation when confidence is low or required data is missing.
- Long-running transformation from messy business input into structured operating assets.

The companion should never pretend to know facts it does not own. It should ask for missing data, identify assumptions, and separate business advice from confirmed business state.

## Long-Term Architecture Principles

V5 follows these principles:

- Explicit ownership: every state, memory, workflow, and response has one canonical owner.
- Business-first interpretation: user messages are interpreted through domains, skills, reasoning, and workflow state before LLM generation.
- Reasoning over keywords: intent is inferred from business meaning, current state, entities, memory, and goals.
- Workflows as durable business processes: workflows can start, pause, resume, chain, complete, and write memory.
- Response envelope before rendering: final responses are composed once, audited, and then rendered.
- Skills as product knowledge units: every business capability is represented by a canonical skill definition.
- Memory with purpose: memory exists to improve business continuity, not to store everything.
- Transformation as a first-class layer: raw input can become structured business output.
- Diagnostics by design: every turn should be explainable to developers through route, skill, workflow, memory, reasoning, tool, and response diagnostics.
- Incremental evolution: V5 should absorb V4 components gradually through adapters and registries without breaking completed behavior.

## V5 Success Definition

V5 is successful when SME Companion can reliably answer:

- What is the owner trying to accomplish?
- Which business domain owns the request?
- Which skill or workflow applies?
- What facts are known, missing, stale, or uncertain?
- What business reasoning supports the recommendation?
- What should happen now?
- What should be remembered?
- What should the owner see?

