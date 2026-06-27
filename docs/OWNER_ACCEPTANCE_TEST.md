# Owner Acceptance Test

## AI Response Intelligence

- User: `สร้างโพสต์`
- Expected: assistant asks which product or business type the post should promote.
- Must not: answer with generic `เล่าเพิ่มอีกนิด...`

## Business Memory

- User: `ร้านขายครีม`
- Expected: system stores `business_type = cosmetic_store`.
- Next content request should reuse that context.

## Conversation Continuation

- User: `ต้นทุน 35 บาท ขายวันละ 100 ชิ้น`
- Expected: assistant continues the cost/pricing workflow and asks only for the next missing field if needed.
- Must not: ask `ต้องการช่วยเรื่องอะไร`

## Store Isolation

- Anonymous visitor opens the URL.
- Expected: no previous manual store is restored.
- Manual store restore requires login.

## OCR Foundation

- Upload receipt/invoice.
- Expected: file is stored and marked pending OCR.
- Must not: invent OCR results.
