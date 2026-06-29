# Skill ID

`01.003.customer_disappears`

# Skill Name

Customer disappears.

# Business Domain

01 Sales

# Business Principle

A silent customer is not automatically a lost customer. Follow up once with context and a useful reason to reply, then stop before the shop sounds desperate or pushy.

# Related Doctrine

- Doctrine 005: timing matters
- Doctrine 006: reduce reply effort
- Doctrine 009: protect relationship
- Doctrine 010: remember customer context

# Conversation Stage

Consideration

# Business Goal

Build Relationship

# Situation

A customer stops replying after asking about price, stock, size, delivery, payment, quotation, or product details.

# Intent

The customer may be busy, comparing shops, waiting for salary, asking a family member, uncertain about fit, or no longer interested.

# Thinking Pattern

1. Review the last customer message before writing anything.
2. Assume normal life interruption first, not rejection.
3. Follow up with one helpful context point, such as availability, delivery cut-off, size recommendation, or limited stock.
4. Make the reply easy: yes/no, one option, or one missing detail.
5. If there is no reply after a reasonable follow-up, set a reminder instead of repeatedly messaging.

# Decision Tree

```text
Customer disappeared
  -> Last message had a clear unanswered question?
    -> Answer or restate the useful answer briefly
  -> Customer was choosing between options?
    -> Recommend one option based on their need
  -> Stock, promotion, or delivery cut-off is time-sensitive?
    -> Mention it honestly without fake urgency
  -> Follow-up already sent?
    -> Wait, set CRM reminder, or stop
  -> Customer is a past buyer?
    -> Follow up with service or refill context, not only "buy now"
```

# Example Questions

- "ลูกค้าถามราคาแล้วหาย ควรทักว่ายังไง"
- "อ่านแล้วไม่ตอบ"
- "ส่งรายละเอียดไปแล้วเงียบ"
- "ลูกค้าบอกเดี๋ยวโอนแล้วหาย"
- "ตามใบเสนอราคายังไงไม่ให้ดูเร่ง"

# Required Data

- Last customer message and last owner reply
- Product, service, quotation, or offer discussed
- Time since last reply
- Stock status, promotion period, or delivery timing if relevant
- Whether this is a new prospect, active buyer, or repeat customer

# AI Should Ask

Ask the owner what the customer last asked and how long they have been silent. If context is already known, ask only one customer-facing question that is easy to answer, such as "ยังให้จัดไว้ให้ไหมคะ" or "สะดวกให้ส่งแถวไหนดีครับ".

# Reasoning

Follow-up is not begging; it is helping the customer finish a decision they already started. Thai customers often avoid saying no directly, so pressure can feel uncomfortable. A useful, calm follow-up keeps the door open and protects the shop's image.

# Recommended Response

"สวัสดีค่ะ ขออนุญาตตามเรื่องเซ็ตของขวัญที่ลูกค้าดูไว้เมื่อวานนะคะ ตอนนี้แบบ 590 บาทยังมีพร้อมส่ง ถ้าต้องการให้ทันพรุ่งนี้ รบกวนแจ้งพื้นที่จัดส่งได้เลยค่ะ เดี๋ยวเช็กค่าส่งให้"

# Bad Response

"ทำไมอ่านแล้วไม่ตอบคะ จะซื้อไหมคะ"

# AI Should Avoid

- Avoid guilt, sarcasm, or pressure.
- Avoid sending repeated "สนใจไหม" messages with no new value.
- Avoid fake urgency such as claiming stock is almost gone when it is not.
- Avoid long paragraphs that make replying feel like work.
- Avoid following up too frequently on high-value leads without CRM timing.

# Business Rules

- One follow-up message should have one purpose.
- Use the previous context so the message feels personal.
- Give a helpful reason to reply.
- After one or two polite attempts, stop or schedule a later reminder.
- If payment was promised, follow up with order confirmation tone, not accusation.

# Workflow Integration

- CRM: record last interaction, follow-up attempt, timing, and customer status.
- Sales Planning: choose the best reason to reopen the conversation.
- Workflow Engine: can trigger reminder sequence if the system supports it, but should not spam.

# Response Mode

NORMAL_CHAT

# Tools Required

CRM when customer history, last message, or reminder timing is available. Business Memory when product availability, promotion timing, or delivery rules are saved.

# Confidence

High when last message and silence duration are known. Medium when only "customer disappeared" is known. Low when the system has no conversation context and owner gives no details.

# Memory Tags

- follow_up_timing
- customer_segment
- favorite_product
- lead_status
- purchase_preference

# Related Skills

- 01.005.follow_up_customer
- 01.004.close_sale
- 02.002.create_promotion

# Future Learning Notes

Learn best follow-up timing by channel: Facebook comment, Messenger, LINE, phone, and in-store quote. Track which follow-up reasons recover sales without annoying customers.
