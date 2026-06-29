# Skill ID

`02.002.create_promotion`

# Skill Name

Create promotion.

# Business Domain

02 Marketing

# Business Principle

A promotion should create action without destroying profit, trust, or future pricing power. The best SME promotion has a clear business reason, simple terms, protected margin, and a deadline customers believe.

# Related Doctrine

- Doctrine 003: promotion must serve a business goal
- Doctrine 004: margin comes before vanity sales
- Doctrine 008: discounts need rules
- Doctrine 009: loyal customers should feel respected

# Conversation Stage

Consideration

# Business Goal

Close Sale

# Situation

The owner wants to run a promotion to increase sales, clear stock, launch a product, bring back old customers, increase order size, fill empty booking slots, or compete during a seasonal period.

# Intent

The owner wants an offer customers notice and act on, while keeping the business profitable and manageable for staff.

# Thinking Pattern

1. Start with the goal, not the discount.
2. Check why the promotion is needed: slow sales, old stock, new product, low weekday traffic, repeat purchase, or higher average order value.
3. Protect margin by choosing mechanics before percentage discount.
4. Make the condition simple enough for customers and staff to remember.
5. Add honest urgency: date, quantity, booking slots, delivery round, or stock.
6. Prepare the sales response for customers who ask questions.

# Decision Tree

```text
Owner asks for promotion
  -> Goal is sales volume?
    -> Consider bundle, minimum spend, or free delivery threshold
  -> Goal is clear old stock?
    -> Use limited-time clearance or bundle with popular item
  -> Goal is new customer acquisition?
    -> Use starter set, first-order benefit, or trial size
  -> Goal is repeat purchase?
    -> Use member reward, refill reminder, or second-purchase offer
  -> Margin is unknown?
    -> Ask cost, safe discount limit, or choose non-discount value add
  -> Staff cannot execute complex rules?
    -> Simplify promotion before publishing
```

# Example Questions

- "ช่วยคิดโปรให้ร้านหน่อย"
- "ยอดตก อยากทำโปร"
- "อยากเคลียร์สต๊อกเก่า"
- "เปิดตัวสินค้าใหม่ ทำโปรอะไรดี"
- "อยากให้ลูกค้าซื้อเยอะขึ้นต่อบิล"

# Required Data

- Promotion goal
- Product or category
- Cost, gross margin, or safe discount limit
- Stock level, expiry, seasonality, or booking capacity
- Target customer: new, repeat, inactive, local, wholesale, or high-value
- Promotion period and channel
- Operational limits such as delivery, staff time, or stock quantity

# AI Should Ask

Ask the owner what the promotion must achieve: more orders, higher bill size, clear stock, new customers, old customers returning, or booking slots filled. If discount is requested, ask for cost or maximum safe discount before recommending a percentage.

# Reasoning

SME owners often feel pressure to discount when sales slow, but discounting everything teaches customers to wait and can create busy work without profit. A good promotion changes behavior in a controlled way: buy sooner, buy more, try once, return again, or choose old stock.

# Recommended Response

"ถ้าเป้าหมายคือเพิ่มยอดต่อบิลโดยไม่ลดกำไรหนัก แนะนำโปร 'ซื้อครบ 600 บาท ส่งฟรีในโซนร้าน' แทนลดทั้งร้านค่ะ ลูกค้ารู้สึกได้ประโยชน์ ร้านยังรักษาราคาสินค้า และช่วยดันให้ลูกค้าเพิ่มอีก 1-2 รายการ เงื่อนไขควรใช้ 3 วัน หรือจำกัด 30 ออเดอร์แรกเพื่อให้ตัดสินใจง่าย"

# Bad Response

"ลด 50% ทุกอย่างทั้งร้าน จะได้มีคนซื้อเยอะๆ"

# AI Should Avoid

- Avoid recommending high discounts without margin data.
- Avoid promotions with many conditions customers cannot understand.
- Avoid fake scarcity.
- Avoid discounting best sellers unnecessarily when a bundle or threshold would work.
- Avoid promotions that punish loyal customers while rewarding only new customers.

# Business Rules

- Promotion must have one primary goal.
- Prefer value-add, bundles, thresholds, or limited sets before deep discount.
- Discount old stock more aggressively than core best sellers.
- State period, quantity, channel, and conditions clearly.
- Make sure staff can explain the promotion in one sentence.

# Workflow Integration

- Promotion: design mechanics, terms, and owner approval points.
- Create Post: turn promotion into Facebook/LINE captions.
- Sales Planning: prepare objection handling and upsell path.
- Business Analysis: measure profit, not only number of orders.

# Response Mode

BUSINESS_CONSULTING

# Tools Required

Business Memory when costs, margins, best sellers, stock, customer segments, or past promotion results are saved. Cost Calculation when margin or discount impact must be checked.

# Confidence

High when goal, product, margin, and stock situation are known. Medium when goal and product are known but cost is missing. Low when owner asks for a discount without business context.

# Memory Tags

- promotion_style
- pricing_strategy
- margin_sensitivity
- customer_segment
- favorite_product
- stock_status

# Related Skills

- 02.001.create_facebook_post
- 01.002.customer_says_expensive
- 01.005.follow_up_customer

# Future Learning Notes

Track which promotion mechanics increase profit and repeat purchase: free delivery threshold, bundle set, buy more save more, starter set, member reward, clearance set, limited booking slot, or add-on gift.
