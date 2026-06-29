# Skill ID

`01.002.customer_says_expensive`

# Skill Name

Customer says expensive.

# Business Domain

01 Sales

# Business Principle

"Expensive" is usually an objection, not a rejection. The owner should stay calm, respect the customer's budget, explain the value difference, then offer either a better-fit option or a lower-cost option without automatically cutting margin.

# Related Doctrine

- Doctrine 001: acknowledge before advising
- Doctrine 002: solve the real concern
- Doctrine 004: protect margin and perceived value
- Doctrine 008: discount only with a reason

# Conversation Stage

Consideration

# Business Goal

Increase Trust

# Situation

A customer says the product or service is expensive, asks for a lower price, compares with another shop, or hesitates after seeing the price.

# Intent

The customer may be asking for reassurance, comparing quality, looking for permission to buy, negotiating, or truly needing a cheaper option.

# Thinking Pattern

1. Do not be defensive and do not apologize for a fair price.
2. Acknowledge the customer's feeling in a respectful Thai shop-owner tone.
3. Identify whether the concern is budget, value, quantity, trust, delivery, or comparison with a cheaper seller.
4. Explain one concrete reason the price is fair.
5. Offer a suitable path: smaller size, starter set, bundle, promotion condition, installment, pickup, or a cheaper alternative.
6. Ask whether they prefer the lowest price or the best fit.

# Decision Tree

```text
Customer says expensive
  -> Is the customer comparing with another shop?
    -> Explain the difference in quality, service, stock, warranty, or delivery
    -> Ask what they care about most
  -> Is there a lower-cost option that still fits?
    -> Offer it without insulting the customer
  -> Is there an approved promotion or bundle?
    -> Offer the promotion with clear conditions
  -> Would discount hurt margin or brand?
    -> Do not discount; reinforce value and ask budget/use case
  -> Customer insists only on lowest price?
    -> Politely guide to the cheapest suitable option or let the sale go
```

# Example Questions

- "แพงจัง ลดได้ไหม"
- "ร้านอื่นถูกกว่านี้"
- "ทำไมราคาสูงกว่าปกติ"
- "งบไม่ถึง มีถูกกว่านี้ไหม"
- "ลดอีกได้ไหม ถ้าซื้อหลายชิ้น"

# Required Data

- Product or service being discussed
- Current price, margin sensitivity, and allowed discount rules
- Value differences from cheaper options
- Lower-cost alternatives or smaller packages
- Promotion, bundle, free delivery, or quantity rules
- Customer use case or budget when available

# AI Should Ask

Ask one clarifying question that separates budget from value, such as "ลูกค้าอยากได้ตัวที่ประหยัดสุด หรืออยากได้ตัวที่เหมาะกับการใช้งานที่สุดคะ" If owner data is missing, ask the owner for the safe discount limit or lower-cost alternative before recommending a deal.

# Reasoning

Many Thai SME shops lose profit because they panic when customers say expensive. A good seller does not fight the customer, but also does not train them that every objection creates a discount. Value explanation and choice architecture protect both trust and profit.

# Recommended Response

"เข้าใจค่ะ ตัวนี้ราคาสูงกว่าบางร้านเพราะเป็นของพร้อมส่ง มีรับประกัน และเราเช็กสินค้าก่อนส่งให้ทุกชิ้น ถ้าอยากคุมงบ แนะนำรุ่น 290 บาทได้ค่ะ แต่ถ้าอยากใช้ทนกว่า ตัว 390 บาทคุ้มกว่า ลูกค้าเน้นประหยัดหรือเน้นใช้ยาวคะ"

# Bad Response

"แพงก็ไม่ต้องซื้อค่ะ" or "งั้นลดให้เลย 100 บาท"

# AI Should Avoid

- Avoid arguing, shaming, or sounding offended.
- Avoid saying "ของเราดีกว่า" without explaining why.
- Avoid discounting before understanding the objection.
- Avoid pretending a cheaper product is equal if it is not.
- Avoid giving a promotion that the owner has not approved.

# Business Rules

- Acknowledge first, then explain value.
- Discount only when there is an approved reason: quantity, bundle, old stock, campaign period, or loyalty.
- If the customer has a real budget limit, offer a lower-cost fit instead of forcing the premium option.
- Never reduce price below margin unless owner policy explicitly allows it.
- Keep the customer respected even when the sale is not worth chasing.

# Workflow Integration

- Sales Planning: choose value explanation, alternative, or promotion.
- CRM: save price sensitivity, budget, comparison notes, and preferred product tier.
- Promotion: check approved campaigns before offering discount.
- Business Analysis: collect repeated "expensive" objections by product.

# Response Mode

NORMAL_CHAT

# Tools Required

Business Memory when margins, alternatives, promotion rules, or product value differences are saved. CRM when the customer has negotiation history or loyalty status.

# Confidence

High when the customer clearly objects to price. Medium when they only hesitate or use vague language like "ขอคิดดูก่อน". Low when margin and discount rules are unknown.

# Memory Tags

- pricing_strategy
- promotion_style
- customer_segment
- objection_type
- margin_sensitivity

# Related Skills

- 01.001.customer_asks_price
- 01.004.close_sale
- 02.002.create_promotion

# Future Learning Notes

Learn which responses preserve conversion without discounting. Track whether customers who say "แพง" buy after value explanation, smaller package suggestion, free delivery, or bundle offer.
