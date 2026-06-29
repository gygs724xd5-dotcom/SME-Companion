from __future__ import annotations

import re

from brain.response_mode_engine import (
    ASK_NEXT_FIELD,
    BUSINESS_CONSULTING,
    CLARIFICATION,
    GENERATE_OUTPUT,
    INTERRUPTION,
    NORMAL_CHAT,
    RESUME_WORKFLOW,
    SHORT_REPLY,
    SMALL_TALK,
    WORKFLOW_COMPLETE,
)


FORBIDDEN_COLLECTION_HEADINGS = (
    "สิ่งที่ผมเข้าใจ",
    "วิเคราะห์",
    "คำแนะนำ",
    "ขั้นตอนถัดไป",
)

_HEADING_REPLACEMENTS = {
    "สิ่งที่ผมเข้าใจ": "โอเคครับ",
    "วิเคราะห์": "เข้าใจครับ",
    "คำแนะนำ": "ลองแบบนี้ครับ",
    "ขั้นตอนถัดไป": "ขอข้อมูลอีกนิดครับ",
}


def contains_structured_noise(reply: str | None) -> bool:
    text = str(reply or "")
    return any(heading in text for heading in FORBIDDEN_COLLECTION_HEADINGS)


def strip_collection_noise(reply: str | None) -> str:
    text = str(reply or "").strip()
    for heading, replacement in _HEADING_REPLACEMENTS.items():
        text = re.sub(rf"#+\s*{re.escape(heading)}\s*", replacement + "\n", text)
        text = text.replace(heading, replacement)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def naturalize_response(reply: str | None, response_mode: str, *, preserve_structured: bool = False) -> str:
    """Turn deterministic reasoning text into a short Thai chat-style reply."""
    text = str(reply or "").strip()
    if not text:
        return ""

    if response_mode == ASK_NEXT_FIELD:
        lines = [line.strip(" -•") for line in text.splitlines() if line.strip()]
        question = next((line for line in reversed(lines) if line.endswith("ครับ") or line.endswith("?")), lines[-1] if lines else text)
        return question.strip()

    if response_mode in {SHORT_REPLY, SMALL_TALK, NORMAL_CHAT, CLARIFICATION, INTERRUPTION, RESUME_WORKFLOW}:
        return strip_collection_noise(text)

    if response_mode in {GENERATE_OUTPUT, WORKFLOW_COMPLETE, BUSINESS_CONSULTING} and preserve_structured:
        return text

    return strip_collection_noise(text)
