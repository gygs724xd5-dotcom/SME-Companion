# Skill ID

`01.005.follow_up_customer`

# Skill Name

Follow up customer.

# Business Domain

01 Sales

# Business Principle

Good follow-up is customer-specific, timed, and useful. It should feel like the owner remembers the customer's need, not like a broadcast asking for money.

# Related Doctrine

- Doctrine 001: relevance earns attention
- Doctrine 006: ask one easy reply question
- Doctrine 009: relationship creates repeat sales
- Doctrine 010: memory improves timing

# Conversation Stage

Retention

# Business Goal

Build Relationship

# Situation

The owner wants to follow up with a prospect, active buyer, past buyer, repeat customer, quotation lead, or customer who may need refill or repurchase.

# Intent

The owner wants to restart the conversation, increase repeat orders, recover a lead, check satisfaction, or offer something relevant.

# Thinking Pattern

1. Identify the customer type: new lead, hot lead, buyer, repeat buyer, inactive customer, or after-service customer.
2. Identify the last interaction and product context.
3. Choose one follow-up goal: close order, check satisfaction, refill, upsell, collect review, or announce relevant offer.
4. Write like a Thai owner who remembers the customer.
5. End with one low-pressure question or action.

# Decision Tree

```text
Need follow-up
  -> Customer has not bought yet?
    -> Use last interest, answer the blocker, and ask if they want help choosing
  -> Customer recently bought?
    -> Check satisfaction before selling more
  -> Product has repeat cycle?
    -> Follow up near refill or repurchase time
  -> Customer bought high-value item?
    -> Offer care tips, warranty, or related item later
  -> No customer history?
    -> Ask owner for last interaction before writing
```

# Example Questions

- "ช่วยเขียนข้อความตามลูกค้าหน่อย"
- "ลูกค้าซื้อครีมไปเดือนที่แล้ว ทักไปยังไงดี"
- "อยากตามใบเสนอราคาที่ส่งไป"
- "ลูกค้าเคยซื้อขนมไปแล้ว อยากให้กลับมาซื้อซ้ำ"
- "อยากทักลูกค้าเก่าโดยไม่ดูขายของเกินไป"

# Required Data

- Customer type and relationship stage
- Last product, service, quotation, or problem discussed
- Time since last interaction
- Follow-up goal
- Relevant offer, refill timing, service reminder, or useful advice
- Brand voice and channel, such as LINE, Messenger, or Facebook comment

# AI Should Ask

Ask the owner for customer type and last interaction if unknown. If enough data exists, ask the customer one relevant question, such as "ใช้แล้วเป็นยังไงบ้างคะ", "ต้องการเติมรอบนี้ไหมคะ", or "ให้ช่วยล็อกโปรรอบนี้ไว้ให้ไหมครับ".

# Reasoning

Thai SME revenue often comes from repeat customers and warm relationships. Follow-up fails when it is generic, too frequent, or only asks people to buy. It works when the message reminds the customer of a real need and makes the next reply easy.

# Recommended Response

"สวัสดีค่ะคุณเมย์ ครบประมาณ 1 เดือนจากรอบที่รับเซรั่มไปแล้ว ใช้แล้วผิวเป็นยังไงบ้างคะ ถ้าใกล้หมด รอบนี้มีโปรคู่ประหยัดกว่าซื้อแยก เดี๋ยวช่วยจัดตัวที่เหมาะกับผิวเดิมให้ได้ค่ะ"

# Bad Response

"สวัสดีค่ะ กลับมาซื้ออีกไหมคะ ตอนนี้ร้านต้องการยอดค่ะ"

# AI Should Avoid

- Avoid sending the same message to every customer.
- Avoid selling before checking satisfaction for recent buyers.
- Avoid pretending to remember details that are not known.
- Avoid over-contacting inactive customers.
- Avoid using guilt, urgency, or pressure as the main tactic.

# Business Rules

- Use real customer context when available.
- Choose one follow-up goal per message.
- For recent buyers, check satisfaction before upsell.
- For refill products, time the message near expected usage cycle.
- For quotation leads, reference the quotation and ask about decision timing.

# Workflow Integration

- CRM: schedule reminders, save customer stage, last purchase, refill cycle, and follow-up result.
- Sales Planning: select message angle based on customer type.
- Promotion: include only relevant offers, not random discounts.
- Business Memory: keep brand voice and repeat purchase patterns.

# Response Mode

NORMAL_CHAT

# Tools Required

CRM for customer history, purchase date, and reminders. Business Memory for product cycle, brand voice, and promotion rules.

# Confidence

High when customer history, product, and timing are known. Medium when customer type is known but last interaction is vague. Low when no history is available.

# Memory Tags

- follow_up_timing
- customer_segment
- purchase_preference
- favorite_product
- promotion_style
- brand_voice

# Related Skills

- 01.003.customer_disappears
- 01.004.close_sale
- 02.002.create_promotion

# Future Learning Notes

Learn repeat purchase timing by product category, such as skincare 30 days, pet food 2 to 4 weeks, coffee beans 2 weeks, snacks for office weekly, or service maintenance quarterly.
