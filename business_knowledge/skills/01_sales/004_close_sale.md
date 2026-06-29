# Skill ID

`01.004.close_sale`

# Skill Name

Close sale.

# Business Domain

01 Sales

# Business Principle

When the customer has enough information, the seller's job changes from explaining to guiding action. A good close asks for the next required order detail or confirmation in a clear, low-friction way.

# Related Doctrine

- Doctrine 001: clarity closes hesitation
- Doctrine 006: one next action
- Doctrine 009: make buying easy
- Doctrine 010: save order intent

# Conversation Stage

Purchase

# Business Goal

Close Sale

# Situation

The customer says they want the product, asks how to order, asks to reserve, says "เอาค่ะ", chooses an option, or asks for payment.

# Intent

The customer is ready or nearly ready to buy and needs a simple path to complete the order without confusion.

# Thinking Pattern

1. Detect buying language and stop adding unnecessary persuasion.
2. Identify the minimum missing information needed to complete the sale.
3. Ask for that information in one clear step.
4. Confirm order summary before payment or fulfillment.
5. Use a confident owner tone: helpful, direct, and organized.

# Decision Tree

```text
Customer shows buying intent
  -> Product, option, and quantity known?
    -> Yes: confirm order and ask delivery/pickup/payment next
    -> No: ask only the missing order detail
  -> Delivery or pickup known?
    -> Yes: calculate total or prepare payment step
    -> No: ask for delivery area/address or pickup time
  -> Payment method asked?
    -> Provide approved payment method after confirming total
  -> Multiple choices remain?
    -> Recommend one best-fit choice instead of listing everything again
```

# Example Questions

- "เอาอันนี้ค่ะ"
- "สั่งยังไงครับ"
- "จองได้ไหม"
- "โอนยังไง"
- "ขอ 2 กล่อง ส่งลาดพร้าว"

# Required Data

- Product or service selected
- Variant, size, flavor, color, package, or service tier
- Quantity
- Delivery area, address, or pickup method
- Total price and delivery fee when possible
- Accepted payment method or reservation policy

# AI Should Ask

Ask for the single missing detail that blocks the order. For example, "รับกี่กล่องดีคะ", "สะดวกส่งหรือรับหน้าร้านคะ", or "ขอชื่อ เบอร์โทร และที่อยู่จัดส่งได้เลยค่ะ".

# Reasoning

Many sales are lost after the customer is ready because the shop keeps explaining or gives vague endings. Thai buyers respond well when the seller organizes the order for them and makes the next step obvious.

# Recommended Response

"ได้ค่ะ สรุปเป็นคุกกี้กล่องกลาง 2 กล่อง ส่งลาดพร้าวนะคะ ยอดสินค้า 780 บาท ค่าส่งขอเช็กตามระยะอีกครั้ง รบกวนส่งชื่อ เบอร์โทร และที่อยู่จัดส่งได้เลยค่ะ"

# Bad Response

"ขอบคุณที่สนใจนะคะ ดูสินค้าอื่นเพิ่มได้เลยค่ะ"

# AI Should Avoid

- Avoid continuing to sell after the customer has chosen.
- Avoid asking for information already provided.
- Avoid sending payment details before order total is clear, unless store policy allows deposit.
- Avoid vague phrases like "แจ้งมาได้เลย" without saying what information is needed.
- Avoid adding new options that reopen hesitation.

# Business Rules

- Ask for one next action only.
- Confirm order summary before final payment or fulfillment.
- If stock is limited, reserve only according to store policy.
- If delivery fee is unknown, say it will be confirmed before payment.
- Save confirmed order intent in CRM when available.

# Workflow Integration

- Sales Planning: move from persuasion to order completion.
- CRM: create or update lead/order status, product interest, quantity, and delivery preference.
- Customer Support: hand off to shipping or payment skill when needed.

# Response Mode

ASK_NEXT_FIELD

# Tools Required

CRM when saving order intent, customer details, or follow-up status. Business Memory when payment methods, delivery rules, or reservation policy are saved.

# Confidence

High when customer uses clear buying language. Medium when the customer asks logistical questions but has not chosen product. Low when product and order details are missing.

# Memory Tags

- purchase_preference
- favorite_product
- delivery_area
- payment_method
- lead_status

# Related Skills

- 01.001.customer_asks_price
- 03.001.shipping_question
- 03.002.payment_question

# Future Learning Notes

Learn which closing question works best by business type: food preorder, beauty product, clothing size, service booking, wholesale order, and local delivery.
