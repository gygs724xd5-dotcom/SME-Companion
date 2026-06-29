# Business Skill Schema

Version: `v4.foundation`

Every Business Skill must use the same ordered fields. A future Skill Loader
can validate required fields, supported values, and cross-system compatibility.

## Field Reference

### Skill ID

- Purpose: Stable identifier for loader, tests, analytics, and references.
- Validation: Required. Format `domain_number.sequence.slug`.
- Example: `01.001.customer_asks_price`.
- Why it exists: Prevents ambiguity when file names or display names change.

### Skill Name

- Purpose: Human-readable name.
- Validation: Required. Short noun or verb phrase.
- Example: `Customer asks price`.
- Why it exists: Makes skill libraries readable for owners and developers.

### Business Domain

- Purpose: Assigns the skill to one official domain.
- Validation: Required. Must match a folder under `domains/`.
- Example: `01 Sales`.
- Why it exists: Enables domain routing and agent specialization.

### Business Principle

- Purpose: Teaches one reusable business principle.
- Validation: Required. Exactly one principle.
- Example: `Answer the price, explain value, then ask one buying question.`
- Why it exists: Keeps the skill focused on business judgment instead of scripts.

### Related Doctrine

- Purpose: Links the skill to permanent doctrine.
- Validation: Required. One or more doctrine IDs.
- Example: `Doctrine 001, Doctrine 004, Doctrine 006`.
- Why it exists: Makes behavior auditable against the constitution.

### Conversation Stage

- Purpose: Defines where the customer or owner is in the journey.
- Validation: Required. One of `Awareness`, `Interest`, `Consideration`,
  `Purchase`, `After Sale`, `Retention`, `Recovery`.
- Example: `Interest`.
- Why it exists: Response strategy changes by stage.

### Business Goal

- Purpose: Defines the immediate business outcome.
- Validation: Required. One of `Collect Information`, `Close Sale`,
  `Increase Trust`, `Upsell`, `Cross Sell`, `Retention`, `Solve Problem`,
  `Build Relationship`.
- Example: `Close Sale`.
- Why it exists: Prevents vague responses that do not move the business forward.

### Situation

- Purpose: Describes when the skill applies.
- Validation: Required. Plain-language business condition.
- Example: `A customer asks for the product price.`
- Why it exists: Helps intent routing choose the right skill.

### Intent

- Purpose: Interprets what the customer or owner is trying to do.
- Validation: Required. One concise intent.
- Example: `Check affordability before deciding.`
- Why it exists: Keeps the assistant from responding only to surface words.

### Thinking Pattern

- Purpose: Teaches the AI how to reason step by step.
- Validation: Required. Must be a sequence.
- Example: `Customer asks price -> interest exists -> answer price -> explain value -> ask next question`.
- Why it exists: Makes expert business reasoning explicit.

### Decision Tree

- Purpose: Defines branching logic for different data conditions.
- Validation: Required. Must include at least one branch.
- Example: `If customer understands product, answer price and ask closing question; otherwise explain product first.`
- Why it exists: Enables deterministic reasoning before language generation.

### Example Questions

- Purpose: Provides example user or customer inputs.
- Validation: Required. At least two examples.
- Example: `How much is this?`
- Why it exists: Improves intent matching and test coverage.

### Required Data

- Purpose: Lists data needed for a confident response.
- Validation: Required. Use `None` only when no data is needed.
- Example: `Product, price, unit, customer need`.
- Why it exists: Connects skills to memory and workflow fields.

### AI Should Ask

- Purpose: Defines the next question when data is missing.
- Validation: Required. Must be specific and owner-friendly.
- Example: `Which product is the customer asking about?`
- Why it exists: Enforces ask-before-guess behavior.

### Reasoning

- Purpose: Explains why the recommended response works.
- Validation: Required. Business reasoning, not hidden chain-of-thought.
- Example: `A customer who asks price has interest but still needs confidence.`
- Why it exists: Makes recommendations auditable and teachable.

### Recommended Response

- Purpose: Provides the target response style.
- Validation: Required. Practical, concise, and stage-appropriate.
- Example: `This one is 250 baht. It is good for daily use because... Which color do you prefer?`
- Why it exists: Gives the response engine a concrete pattern.

### Bad Response

- Purpose: Shows what the AI should not do.
- Validation: Required.
- Example: `Please check our catalog for pricing.`
- Why it exists: Reduces generic or harmful replies.

### AI Should Avoid

- Purpose: Lists risky behaviors.
- Validation: Required. At least one item.
- Example: `Avoid apologizing for the price without explaining value.`
- Why it exists: Protects trust, margin, and owner authority.

### Business Rules

- Purpose: Defines constraints that must be respected.
- Validation: Required. Use bullets.
- Example: `Do not discount before understanding price objection.`
- Why it exists: Keeps reasoning aligned with owner profit and operations.

### Workflow Integration

- Purpose: Declares where this skill can be used.
- Validation: Required. Use known workflow names when possible.
- Example: `Sales Planning, CRM`.
- Why it exists: Allows workflow routing without modifying workflows.

### Response Mode

- Purpose: Declares compatible Response Mode Engine output.
- Validation: Required. One of `SHORT_REPLY`, `ASK_NEXT_FIELD`,
  `NORMAL_CHAT`, `BUSINESS_CONSULTING`, `WORKFLOW`, `WORKFLOW_COMPLETE`,
  `BUSINESS_ANALYSIS`, `CLARIFICATION`, `SMALL_TALK`.
- Example: `NORMAL_CHAT`.
- Why it exists: Keeps business skill output compatible with existing UX modes.

### Tools Required

- Purpose: Lists required runtime tools or engines.
- Validation: Required. Use `None` when no tool is needed.
- Example: `Business Memory, CRM`.
- Why it exists: Helps agents decide whether they can execute or must ask.

### Confidence

- Purpose: Defines when the skill should be used.
- Validation: Required. Use `Low`, `Medium`, or `High`.
- Example: `High when message contains price intent and product is known.`
- Why it exists: Prevents overconfident routing.

### Memory Tags

- Purpose: Lists context that Business Memory may save or read.
- Validation: Required. Use snake_case tags.
- Example: `favorite_product, pricing_strategy, customer_segment`.
- Why it exists: Creates a bridge to future memory learning.

### Related Skills

- Purpose: Links adjacent skills.
- Validation: Required. Use skill IDs or `None`.
- Example: `01.002.customer_says_expensive`.
- Why it exists: Supports multi-step sales and service reasoning.

### Future Learning Notes

- Purpose: Records future improvements and observed learning opportunities.
- Validation: Required. Can be `None`.
- Example: `Learn common objections by product category.`
- Why it exists: Keeps future AI learning explicit and governed.

## Supported Values

Conversation Stage:

- Awareness
- Interest
- Consideration
- Purchase
- After Sale
- Retention
- Recovery

Business Goal:

- Collect Information
- Close Sale
- Increase Trust
- Upsell
- Cross Sell
- Retention
- Solve Problem
- Build Relationship

Response Mode:

- SHORT_REPLY
- ASK_NEXT_FIELD
- NORMAL_CHAT
- BUSINESS_CONSULTING
- WORKFLOW
- WORKFLOW_COMPLETE
- BUSINESS_ANALYSIS
- CLARIFICATION
- SMALL_TALK

