# Business Knowledge Architecture

## Purpose

Business Knowledge is the structured operating knowledge of SME Companion V5. It defines the domains, skills, rules, examples, workflows, response styles, and reasoning patterns that make the system business-native.

## Twenty Business Domains

V5 organizes business capability into 20 domains.

| ID | Domain | Responsibility |
| --- | --- | --- |
| 01 | Products | Product catalog, descriptions, variants, bundles, positioning, product readiness. |
| 02 | Inventory | Stock levels, reorder points, shrinkage, availability, inventory risk. |
| 03 | Sales | Sales conversations, objections, closing, follow-up, pipeline actions. |
| 04 | Pricing | Price setting, discounts, margins, bundles, price testing, value framing. |
| 05 | Cost | Cost calculation, contribution margin, break-even, hidden costs. |
| 06 | Marketing | Campaigns, promotions, content, audience, channels, launch planning. |
| 07 | Customers | Customer profiles, service history, segmentation, retention, complaints. |
| 08 | Accounting | Revenue, expenses, cash flow, reconciliation, owner summaries. |
| 09 | Supplier | Supplier records, terms, reliability, negotiation, alternatives. |
| 10 | Purchasing | Purchase planning, order quantities, budget fit, approval, receiving. |
| 11 | HR | Staff roles, schedules, hiring, training, performance, internal communication. |
| 12 | Operations | Daily process, SOPs, task execution, issue tracking, service consistency. |
| 13 | Documents | Business documents, templates, contracts, invoices, forms, policy records. |
| 14 | OCR | Receipt, invoice, label, and document extraction from images or files. |
| 15 | Dashboard | Business health surfaces, KPIs, alerts, owner summaries. |
| 16 | Business Intelligence | Trends, comparisons, anomalies, opportunities, performance interpretation. |
| 17 | Business Memory | Long-term fact storage, profile enrichment, historical events, preferences. |
| 18 | Workflow | Process orchestration, workflow lifecycle, multi-step business tasks. |
| 19 | Reasoning | Decision frameworks, tradeoff analysis, risk identification, recommendations. |
| 20 | Executive Intelligence | Owner-level priorities, strategic planning, delegation, expansion, governance. |

## Domain Expansion Into Skills

Each domain expands into multiple Business Skills. A Business Skill is a specific business capability with a standard schema, examples, required data, workflow integration, rules, reasoning, and response behavior.

The first V5 knowledge target is 100+ skills:

- 20 domains.
- Minimum 5 skills per domain.
- Shared canonical schema.
- Stable skill IDs.
- Skill registry for discovery and ranking.
- Skill diagnostics for routing and confidence.

Example expansion:

| Domain | Example Skills |
| --- | --- |
| Products | Create product profile, improve product description, compare product variants, identify missing product data, prepare product launch checklist. |
| Inventory | Check stock risk, calculate reorder need, explain stockout impact, identify slow-moving stock, prepare inventory count workflow. |
| Sales | Answer price question, handle expensive objection, follow up customer, recover disappeared customer, close sale. |
| Pricing | Calculate selling price, evaluate discount, protect margin, design bundle price, compare competitor pricing. |
| Cost | Capture cost components, calculate gross margin, find hidden cost, estimate break-even, compare supplier cost. |
| Marketing | Create promotion, write social post, plan campaign, define target audience, analyze offer clarity. |
| Customers | Summarize customer issue, suggest retention action, segment customer list, prepare reply, identify churn risk. |
| Accounting | Summarize daily sales, categorize expense, estimate cash flow, identify missing record, prepare owner report. |
| Supplier | Compare suppliers, negotiate terms, record supplier issue, evaluate reliability, prepare reorder contact. |
| Purchasing | Create purchase plan, validate quantity, compare purchase options, approve purchase, track receiving. |
| HR | Write job post, create staff checklist, prepare training plan, handle staff issue, summarize role responsibility. |
| Operations | Create SOP, identify process bottleneck, prepare daily checklist, handle service issue, improve fulfillment flow. |
| Documents | Generate invoice draft, prepare policy, summarize contract, create form, organize document metadata. |
| OCR | Extract receipt data, extract invoice fields, validate OCR confidence, ask correction, map extracted fields. |
| Dashboard | Explain KPI, create dashboard card, detect alert, summarize week, recommend metric. |
| Business Intelligence | Find trend, explain anomaly, compare periods, identify opportunity, diagnose performance drop. |
| Business Memory | Save business fact, update store profile, resolve memory conflict, retrieve known fact, expire stale memory. |
| Workflow | Start workflow, continue workflow, chain workflow, complete workflow, recover interrupted workflow. |
| Reasoning | Evaluate tradeoff, choose response strategy, detect risk, recommend next action, explain confidence. |
| Executive Intelligence | Set business priority, plan next quarter, evaluate expansion, delegate task, create executive summary. |

## Skill Registry

The V5 skill registry should support:

- Domain browsing.
- Skill lookup by ID.
- Intent and entity matching.
- Workflow capability matching.
- Required memory lookup.
- Tool requirement discovery.
- Version and status tracking.
- Diagnostic output for planner decisions.

### Runtime Foundation

`brain/business_skill_registry.py` is the V5.1.0 runtime foundation for Business Skill registration and discovery.

Current scope:

- Loads existing markdown business skills through adapters.
- Exposes `get_skill()`, `find_skill()`, `list_domains()`, and `list_skills()`.
- Provides canonical runtime models for `BusinessSkill`, `BusinessDomain`, and `SkillRegistry`.
- Adds developer diagnostics for `registry_version`, `registered_domains`, and `registered_skills`.

Compatibility rules:

- Existing V4 skill loading, matching, routing, planner behavior, workflows, and responses remain unchanged.
- Existing skills are not migrated yet.
- The registry is available for discovery and diagnostics before it becomes the routing owner.

## Knowledge Layer Contracts

Business Knowledge should provide downstream components with:

- Candidate domains.
- Candidate skills with scores and reasons.
- Required entities.
- Required memory.
- Business rules.
- Reasoning pattern.
- Response guidance.
- Workflow links.
- Tool requirements.
- Confidence and diagnostics.

It should not render the final response directly.
