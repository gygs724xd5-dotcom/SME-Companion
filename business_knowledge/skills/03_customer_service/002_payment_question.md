# Skill ID

`03.002.payment_question`

# Skill Name

Payment question.

# Business Domain

03 Customer Service

# Business Principle

Payment questions usually mean the customer is near purchase. The answer should be clear, trustworthy, and tied to confirmed order details so the shop avoids confusion, wrong totals, and payment disputes.

# Related Doctrine

- Doctrine 001: clear instructions reduce doubt
- Doctrine 006: one payment step at a time
- Doctrine 009: make checkout feel safe
- Doctrine 010: remember approved payment methods

# Conversation Stage

Purchase

# Business Goal

Close Sale

# Situation

A customer asks how to pay, whether bank transfer, QR, credit card, cash on delivery, deposit, installment, or cash pickup is accepted.

# Intent

The customer wants confidence that payment is legitimate, easy, and correctly connected to their order.

# Thinking Pattern

1. Treat payment intent as purchase-stage intent.
2. Check whether product, quantity, delivery, and total are confirmed.
3. Provide only approved payment methods.
4. Give simple instructions and one proof step, such as sending slip or order name.
5. Avoid exposing sensitive payment details unless the owner has explicitly saved them.

# Decision Tree

```text
Customer asks payment question
  -> Order total is confirmed?
    -> Yes: provide payment method and proof step
    -> No: ask for missing detail needed to calculate total
  -> Customer asks COD?
    -> Check whether COD is allowed for this product/area/order value
  -> Deposit required?
    -> Explain deposit amount, reason, and remaining payment timing
  -> Payment method unknown?
    -> Ask owner for approved methods before responding
  -> Customer already paid?
    -> Ask for slip/order name and confirm checking process
```

# Example Questions

- "โอนยังไงคะ"
- "จ่ายเงินยังไง"
- "รับปลายทางไหม"
- "มี QR ไหม"
- "มัดจำก่อนได้ไหม"
- "ส่งสลิปตรงไหน"

# Required Data

- Accepted payment methods
- Order summary and total amount
- Delivery fee or pickup details
- Deposit, COD, installment, or reservation policy
- Payment verification process
- Safe wording for bank account, QR, or payment link if owner provided it

# AI Should Ask

If order total is missing, ask for the missing order detail before giving final payment instructions. If payment methods are not saved, ask the owner which methods the store accepts. For the customer, ask for the transfer slip or order name after payment.

# Reasoning

Payment is where trust and operational accuracy matter most. A messy payment answer can lead to wrong transfers, unpaid orders, customer anxiety, or staff time wasted reconciling slips. A confident SME payment response feels organized and safe.

# Recommended Response

"ได้ค่ะ สรุปออเดอร์เป็นบราวนี่ 2 กล่อง ส่งพระราม 9 ยอดรวม 520 บาทนะคะ ชำระได้โดยโอนหรือสแกน QR ของร้าน หลังโอนแล้วรบกวนส่งสลิปในแชทนี้ พร้อมชื่อผู้รับค่ะ เดี๋ยวแอดมินยืนยันรอบจัดส่งให้"

# Bad Response

"โอนมาได้เลยค่ะ เดี๋ยวค่อยคิดยอด"

# AI Should Avoid

- Avoid giving payment details before confirming total when delivery fee or quantity is unclear.
- Avoid inventing bank accounts, QR codes, or payment links.
- Avoid posting sensitive payment or customer details in public comments.
- Avoid offering COD, installment, or deposit if the shop has not approved it.
- Avoid sounding casual about payment verification.

# Business Rules

- Confirm order summary and total before final payment.
- Use only approved payment methods.
- Request proof of payment and identify the order.
- If payment is made in public channel, move to private chat for details.
- For deposits, clearly state deposit amount, remaining balance, and cancellation rule.

# Workflow Integration

- Customer Support: answer payment method and proof steps.
- Sales Planning: close the sale after payment readiness.
- CRM: update payment status, order total, and customer preference.
- Business Memory: reuse payment methods and policies.

# Response Mode

ASK_NEXT_FIELD

# Tools Required

Business Memory when payment methods, deposit policy, COD rules, or account wording are saved. CRM when order total, payment status, or customer history is available.

# Confidence

High when order total and payment methods are known. Medium when total is missing. Low when no approved payment methods are saved.

# Memory Tags

- payment_method
- payment_status
- purchase_preference
- customer_segment
- order_total

# Related Skills

- 01.004.close_sale
- 03.001.shipping_question
- 03.003.refund_request

# Future Learning Notes

Learn which payment methods customers prefer by channel and order value. Track where customers drop off: before total, after payment details, after delivery fee, or after deposit request.
