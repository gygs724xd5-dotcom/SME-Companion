# Skill ID

`01.001.customer_asks_price`

# Skill Name

Customer asks price.

# Business Domain

01 Sales

# Business Principle

When a customer asks price, they are not only asking for a number; they are testing whether the offer feels worth continuing. A strong SME seller answers the price clearly, adds one practical value reason, then asks one buying question that moves the customer closer to a decision.

# Related Doctrine

- Doctrine 001: clarity creates trust
- Doctrine 004: protect margin before giving discount
- Doctrine 006: one next step beats many explanations
- Doctrine 010: remember useful customer context

# Conversation Stage

Interest

# Business Goal

Close Sale

# Situation

A customer asks how much a product or service costs in chat, comment, DM, phone, or in-store conversation.

# Intent

The customer is interested enough to compare price, budget, size, quantity, or suitability. They may be ready to buy, but they may also need a short reason to believe the price is fair.

# Thinking Pattern

1. Treat the price question as buying interest, not casual curiosity.
2. If the exact product is known, answer the price first so the shop feels honest.
3. Add one value reason that matters to Thai SME buyers, such as freshness, warranty, delivery, portion size, authentic material, after-sales care, or ready stock.
4. Ask one practical buying question, such as quantity, color, size, delivery area, pickup time, or intended use.
5. Do not over-explain. The goal is to keep the conversation moving.

# Decision Tree

```text
Customer asks price
  -> Product or package is clear?
    -> Yes: answer price directly
      -> Add one value reason
      -> Ask one buying question
    -> No: ask which product, size, model, flavor, package, or service tier they mean
  -> Customer seems only comparing?
    -> Mention the most relevant difference from cheaper options
    -> Ask what they will use it for or how many they need
  -> Customer has already asked delivery/payment?
    -> Include total or next purchase step if enough details are known
```

# Example Questions

- "ตัวนี้เท่าไหร่คะ"
- "ราคาเท่าไรครับ"
- "เซ็ตนี้กี่บาท"
- "ถ้าสั่ง 10 ชิ้นคิดยังไง"
- "รวมส่งไหม"

# Required Data

- Product, service, model, size, flavor, or package being asked about
- Price and unit, such as per piece, per box, per set, per kilo, per month, or per job
- Whether price includes VAT, delivery, installation, packaging, or service fee
- One strong value point, such as ready stock, made fresh daily, genuine item, local delivery, warranty, or owner support
- Next order detail needed to move forward

# AI Should Ask

Ask the owner for the missing product or package only when the customer's target is unclear. If the product and price are already known, ask the customer one buying question, such as "รับกี่ชิ้นดีคะ" or "ส่งแถวไหนดีครับ จะได้เช็กค่าส่งให้".

# Reasoning

Thai customers often ask price early because they do not want to waste time or feel embarrassed later. Hiding price can make the shop look difficult, but giving only a number turns the conversation into a pure price comparison. The best shop-owner response gives the number, protects perceived value, and gently opens the buying path.

# Recommended Response

"ตัวนี้ราคา 390 บาทต่อกล่องค่ะ เป็นล็อตใหม่พร้อมส่ง เหมาะกับคนที่อยากได้แบบใช้ได้เลยไม่ต้องรอพรีออเดอร์ รับ 1 กล่องก่อน หรือให้ช่วยจัดเป็นเซ็ตคุ้มกว่าดีคะ"

# Bad Response

"ทักแชทค่ะ" or "ราคาอยู่ในรูปแล้วค่ะ ไปดูเองนะคะ"

# AI Should Avoid

- Avoid hiding the price when the shop has already provided it.
- Avoid replying with only a number and no value.
- Avoid giving discount immediately after the price question.
- Avoid asking three or four questions at once.
- Avoid sounding annoyed when the same customer asks about several items.

# Business Rules

- Price first when known.
- Value second, but keep it to one concise reason.
- Ask one next question tied to buying.
- If delivery cost changes by area, separate product price from delivery fee.
- If price depends on quantity or customization, explain the pricing basis before asking for details.

# Workflow Integration

- Sales Planning: identify the strongest value point and next buying question.
- CRM: save product interest, budget clues, preferred quantity, and delivery area.
- Business Memory: reuse known prices, package rules, delivery rules, and brand tone.

# Response Mode

NORMAL_CHAT

# Tools Required

Business Memory when product price, package details, delivery fee, or brand voice is saved. CRM when the customer has previous buying history or an open order.

# Confidence

High when the customer asks price and the product is clear. Medium when the product, quantity, or package is unclear. Low when pricing depends on custom work and no pricing rule exists.

# Memory Tags

- pricing_strategy
- favorite_product
- customer_segment
- delivery_area
- purchase_preference

# Related Skills

- 01.002.customer_says_expensive
- 01.004.close_sale
- 03.001.shipping_question
- 03.002.payment_question

# Future Learning Notes

Track which value points lead to replies after price answers, such as "พร้อมส่ง", "รับประกัน", "ทำสด", "ส่งด่วนในกรุงเทพ", or "เจ้าของตอบเอง". Learn whether each product sells better with a single-item close, bundle suggestion, or delivery-area question.
