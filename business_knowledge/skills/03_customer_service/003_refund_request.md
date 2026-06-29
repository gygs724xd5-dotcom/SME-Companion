# Skill ID

`03.003.refund_request`

# Skill Name

Refund request.

# Business Domain

03 Customer Service

# Business Principle

Refund handling must protect both trust and business rules. A good response acknowledges the problem, collects facts, avoids blame, follows policy, and offers the correct next step without promising more than the shop can deliver.

# Related Doctrine

- Doctrine 001: acknowledge clearly
- Doctrine 002: solve the real issue
- Doctrine 004: protect owner profit and policy
- Doctrine 008: rules prevent emotional decisions
- Doctrine 010: record issue patterns

# Conversation Stage

Recovery

# Business Goal

Solve Problem

# Situation

A customer asks for refund, return, replacement, exchange, cancellation, warranty claim, missing item correction, or compensation after purchase.

# Intent

The customer wants the problem fixed and may feel disappointed, anxious, angry, or unsure whether the shop will take responsibility.

# Thinking Pattern

1. Acknowledge the customer's issue calmly without admitting unknown fault.
2. Ask for facts: order, date, product condition, photos/videos, delivery evidence, and what resolution they want.
3. Check the store policy and product category.
4. Separate cases: shop error, damaged in transit, wrong item, customer changed mind, used product, expired claim period, or service dissatisfaction.
5. Offer the policy-based solution in a respectful tone.
6. Save the issue for future supplier, packing, delivery, or staff improvement.

# Decision Tree

```text
Customer requests refund
  -> Order details and evidence known?
    -> Yes: compare with policy and decide next step
    -> No: ask for order number/name, purchase date, and photo/video
  -> Shop error or defective item likely?
    -> Apologize for the inconvenience and offer replacement/refund path per policy
  -> Delivery damage likely?
    -> Collect packaging photos and delivery evidence
  -> Customer changed mind?
    -> Apply return/exchange policy without blame
  -> Policy unknown?
    -> Do not promise refund; escalate to owner decision
```

# Example Questions

- "ขอคืนเงินได้ไหม"
- "ของเสีย ขอเปลี่ยนได้ไหม"
- "ได้รับผิดสี"
- "ของแตกตอนส่ง"
- "อยากยกเลิกออเดอร์"
- "ใช้แล้วไม่ถูกใจ คืนได้ไหม"

# Required Data

- Order name, order number, phone number, or purchase channel
- Purchase date and delivery date
- Product, quantity, price, and condition
- Issue description with photos or video
- Packaging and courier evidence when shipping is involved
- Store refund, return, exchange, warranty, and cancellation policy
- Customer's preferred resolution

# AI Should Ask

Ask for order details and evidence before deciding. A good first ask is: "ขอเลขออเดอร์หรือชื่อที่สั่ง พร้อมรูปสินค้าและปัญหาที่พบหน่อยนะคะ เดี๋ยวทางร้านตรวจสอบให้ตามนโยบายค่ะ"

# Reasoning

Refund conversations can quickly become emotional. Thai SME shops need to sound responsible while avoiding instant promises that create unfair losses or inconsistent policy. Clear fact collection keeps the conversation fair and gives the owner enough information to decide.

# Recommended Response

"ขออภัยที่ได้รับสินค้าแล้วมีปัญหานะคะ รบกวนส่งชื่อที่สั่งซื้อ วันที่ได้รับสินค้า และรูปสินค้าพร้อมแพ็กเกจให้ทางร้านตรวจสอบหน่อยค่ะ ถ้าเป็นความผิดพลาดจากทางร้านหรือสินค้าเสียหายตามเงื่อนไข เราจะช่วยดำเนินการเปลี่ยนหรือคืนเงินตามนโยบายให้ค่ะ"

# Bad Response

"ร้านไม่รับคืนทุกกรณีค่ะ" or "ได้ค่ะ เดี๋ยวคืนเงินให้เลย" before checking facts.

# AI Should Avoid

- Avoid rejecting the customer before checking facts.
- Avoid promising refund, replacement, or compensation before policy is confirmed.
- Avoid blaming the customer or courier too early.
- Avoid arguing publicly in comments.
- Avoid asking for sensitive payment or address details in public.
- Avoid ignoring repeated issue patterns.

# Business Rules

- Acknowledge first, investigate second, decide third.
- Follow store policy consistently.
- Escalate to owner when policy is missing, high-value, emotional, or legally sensitive.
- Use private chat for order details and evidence.
- Record issue type and resolution for future improvement.

# Workflow Integration

- Customer Support: collect facts, explain policy, and manage tone.
- CRM: save complaint, evidence status, resolution, and customer sentiment.
- Business Analysis: identify recurring product, supplier, packing, or courier problems.
- Sales Planning: recover trust after resolution when appropriate.

# Response Mode

CLARIFICATION

# Tools Required

Business Memory when refund, exchange, warranty, or cancellation policy is saved. CRM when order history, customer status, or prior complaints are available.

# Confidence

Medium until order details, evidence, and policy are known. High when the facts match a saved policy. Low when the issue is high-value, legal, public, or emotionally escalated.

# Memory Tags

- refund_policy
- issue_type
- customer_sentiment
- order_status
- supplier_quality
- delivery_method

# Related Skills

- 03.001.shipping_question
- 03.002.payment_question
- 01.005.follow_up_customer

# Future Learning Notes

Track refund reasons by product, supplier, courier, staff member, packing method, and customer segment. Learn which recovery actions keep customers: replacement, partial refund, store credit, apology note, free delivery next time, or owner call.
