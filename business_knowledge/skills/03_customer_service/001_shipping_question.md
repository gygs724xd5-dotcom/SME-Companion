# Skill ID

`03.001.shipping_question`

# Skill Name

Shipping question.

# Business Domain

03 Customer Service

# Business Principle

Delivery questions are purchase blockers. The answer should make receiving the product feel clear, predictable, and easy by giving delivery availability, timing, cost, and one next step.

# Related Doctrine

- Doctrine 001: clear service terms create trust
- Doctrine 002: solve the blocker before selling more
- Doctrine 006: ask for the next required field
- Doctrine 010: remember delivery zones and preferences

# Conversation Stage

Consideration

# Business Goal

Solve Problem

# Situation

A customer asks about shipping, delivery area, delivery fee, delivery timing, same-day delivery, pickup, courier, tracking, or whether the shop can send to their province.

# Intent

The customer wants to know whether receiving the product is convenient, affordable, fast enough, and safe enough before ordering.

# Thinking Pattern

1. Identify whether the customer is asking about availability, cost, timing, tracking, or delivery method.
2. If location is known, answer with the most specific delivery option.
3. If location is missing, ask for area, province, postcode, or delivery address.
4. Mention restrictions honestly, such as frozen goods, fragile items, plants, live animals, large items, or installation.
5. Move toward order confirmation once delivery feasibility is clear.

# Decision Tree

```text
Customer asks shipping question
  -> Delivery location known?
    -> Yes: state method, fee, and estimated timing
    -> No: ask for area/province/postcode
  -> Product has delivery restriction?
    -> Explain safe delivery option or pickup requirement
  -> Same-day delivery requested?
    -> Check area and order cut-off time
  -> Delivery unavailable?
    -> Offer pickup, nearby meeting point, courier alternative, or preorder round
  -> Customer asks tracking?
    -> Explain when tracking is sent and where to check
```

# Example Questions

- "ส่งไหมคะ"
- "ค่าส่งเท่าไหร่"
- "ส่งกรุงเทพไหม"
- "ต่างจังหวัดส่งได้ไหม"
- "วันนี้ส่งทันไหม"
- "มีเก็บเงินปลายทางไหม"

# Required Data

- Customer area, province, postcode, or full address
- Product type, size, weight, fragility, temperature needs, or installation needs
- Available delivery methods, such as shop rider, Grab/Lalamove, EMS, Kerry, Flash, private courier, pickup, or COD
- Delivery fee rules and free delivery threshold
- Cut-off time, shipping days, and estimated arrival
- Tracking or proof-of-delivery process

# AI Should Ask

Ask for the delivery area or province first when missing. If the customer wants same-day delivery, ask for area and preferred receiving time. If the product has restrictions, ask for details needed to confirm safe delivery.

# Reasoning

Thai customers often decide based on total cost and speed, especially for food, gifts, urgent supplies, pet products, and local services. Vague answers like "ส่งได้ค่ะ" still leave uncertainty. A clear delivery answer reduces friction and prevents later complaints.

# Recommended Response

"ส่งได้ค่ะ ถ้าเป็นโซนลาดพร้าว-รัชดา ส่งแมสเซนเจอร์ได้วันนี้ ค่าส่งคิดตามระยะทางและจะแจ้งก่อนยืนยันออเดอร์ค่ะ รบกวนส่งโลเคชันหรือซอยให้หน่อยนะคะ เดี๋ยวเช็กค่าส่งให้ทันที"

# Bad Response

"ส่งได้ค่ะ ค่าส่งแล้วแต่ขนส่ง รอก่อนนะคะ"

# AI Should Avoid

- Avoid promising delivery before confirming area and product restrictions.
- Avoid hiding delivery fee until after payment.
- Avoid giving exact arrival guarantees if courier timing is uncertain.
- Avoid asking for full address publicly in Facebook comments.
- Avoid ignoring fragile, frozen, fresh, or high-value product handling.

# Business Rules

- Confirm area before confirming fee or same-day delivery.
- State delivery cost and timing when known.
- If exact fee is not known, explain how it will be calculated.
- For public comments, move sensitive address details to inbox.
- Offer pickup or alternative delivery when standard shipping is not suitable.

# Workflow Integration

- Customer Support: answer delivery terms and reduce uncertainty.
- Sales Planning: use delivery feasibility to close the sale.
- CRM: save customer delivery area and preferred method.
- Business Memory: reuse delivery zones, fees, cut-off times, and courier rules.

# Response Mode

ASK_NEXT_FIELD

# Tools Required

Business Memory when delivery rules, courier options, fees, and cut-off times are saved. CRM when customer address, area, or delivery preference is known.

# Confidence

High when location and delivery rules are known. Medium when only province or rough area is known. Low when product restrictions or courier availability are unknown.

# Memory Tags

- delivery_area
- delivery_method
- purchase_preference
- customer_segment
- shipping_cutoff

# Related Skills

- 01.004.close_sale
- 03.002.payment_question
- 03.003.refund_request

# Future Learning Notes

Learn common delivery zones, actual courier performance, complaint patterns, and best wording for delivery fees by business type and location.
