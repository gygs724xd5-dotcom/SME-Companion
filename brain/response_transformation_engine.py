from __future__ import annotations

import re
from copy import deepcopy

from brain.cost_intent_isolation import is_strong_cost_calculation_message


TRANSFORMATION_TYPES = {
    "SHORTEN",
    "EXPAND",
    "REWRITE",
    "VARIANT",
    "TRANSLATE",
    "BULLET",
    "CTA",
    "EMOJI",
    "CASUAL",
    "FORMAL",
    "YOUTH",
    "PROFESSIONAL",
    "SEO",
    "SALES",
    "SUMMARIZE",
    "COMPRESS",
    "IMPROVE",
}


_TYPE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("COMPRESS", ("เหลือ 1 ประโยค", "หนึ่งประโยค", "1 sentence", "one sentence")),
    ("SHORTEN", ("เอาแบบสั้น", "แบบสั้น", "สั้นลง", "shorten", "shorter")),
    ("EXPAND", ("ยาวขึ้น", "ละเอียดขึ้น", "ขยาย", "expand", "longer")),
    ("TRANSLATE", ("แปลอังกฤษ", "ภาษาอังกฤษ", "translate", "english")),
    ("BULLET", ("bullet", "บูลเล็ต", "เป็นข้อ", "หัวข้อ")),
    ("CTA", ("cta", "call to action", "ปิดการขาย", "ชวนซื้อ", "กระตุ้นให้ซื้อ")),
    ("EMOJI", ("emoji", "อีโมจิ", "เพิ่ม emoji", "เพิ่มอีโมจิ")),
    ("FORMAL", ("สุภาพขึ้น", "ทางการ", "formal", "polite")),
    ("CASUAL", ("กันเอง", "สบายๆ", "casual", "friendly")),
    ("YOUTH", ("วัยรุ่น", "teen", "young", "gen z")),
    ("PROFESSIONAL", ("professional", "มืออาชีพ", "น่าเชื่อถือ")),
    ("SEO", ("seo", "คีย์เวิร์ด", "keyword", "hashtag", "แฮชแท็ก")),
    ("SALES", ("ขายเก่ง", "ขายเก่งกว่าเดิม", "ขายดีขึ้น", "sales", "ขายมากขึ้น")),
    ("SUMMARIZE", ("สรุป", "summary", "summarize")),
    ("IMPROVE", ("ดีขึ้น", "ปรับให้ดี", "improve", "better")),
    ("VARIANT", ("ขออีกแบบ", "อีกแบบ", "อีกอัน", "อีกโพสต์", "แบบใหม่", "variant", "another")),
    ("REWRITE", ("rewrite", "เขียนใหม่", "ปรับใหม่", "แก้ให้")),
)


def _normalize(text: str | None) -> str:
    return str(text or "").strip().lower()


def detect_response_transformation(user_message: str | None) -> dict:
    normalized = _normalize(user_message)
    base = {
        "is_transformation": False,
        "transformation_type": None,
        "transformation_reason": None,
        "rewrite_mode": None,
        "translation_mode": None,
    }
    if not normalized:
        return base

    for transformation_type, patterns in _TYPE_PATTERNS:
        if any(pattern in normalized for pattern in patterns):
            return {
                **base,
                "is_transformation": True,
                "transformation_type": transformation_type,
                "transformation_reason": f"matched_{transformation_type.lower()}_instruction",
                "rewrite_mode": _rewrite_mode(transformation_type),
                "translation_mode": "thai_to_english" if transformation_type == "TRANSLATE" else None,
            }
    return base


def _rewrite_mode(transformation_type: str | None) -> str | None:
    if transformation_type in {"REWRITE", "FORMAL", "CASUAL", "YOUTH", "PROFESSIONAL", "SEO", "SALES", "IMPROVE", "VARIANT"}:
        return str(transformation_type or "").lower()
    if transformation_type in {"SHORTEN", "EXPAND", "SUMMARIZE", "COMPRESS", "BULLET", "CTA", "EMOJI"}:
        return "edit_previous_response"
    return None


def _latest_assistant_from_history(application_state: dict | None) -> str | None:
    chat_history = ((application_state or {}).get("conversation") or {}).get("chat_history") or []
    for message in reversed(chat_history):
        if isinstance(message, dict) and message.get("role") == "assistant" and str(message.get("content") or "").strip():
            return str(message.get("content")).strip()
    return None


def _response_memory(application_state: dict | None) -> dict:
    state = application_state or {}
    conversation = state.get("conversation") or {}
    return conversation.get("response_memory") or conversation


def transformation_source(application_state: dict | None) -> dict:
    memory = _response_memory(application_state)
    last_response = memory.get("last_generated_response")
    if last_response:
        return {
            "source": "completed_response",
            "text": str(last_response).strip(),
            "response_type": memory.get("last_response_type") or "assistant_response",
            "generation_context": deepcopy(memory.get("last_generation_context") or {}),
            "variant_history": list(memory.get("last_variant_history") or []),
            "transformation_chain": list(memory.get("last_transformation_chain") or []),
            "transformation_history": list(memory.get("transformation_history") or []),
        }

    latest = _latest_assistant_from_history(application_state)
    if latest:
        return {
            "source": "conversation_context",
            "text": latest,
            "response_type": "assistant_response",
            "generation_context": {},
            "variant_history": [],
            "transformation_chain": [],
            "transformation_history": [],
        }

    return {
        "source": None,
        "text": None,
        "response_type": None,
        "generation_context": {},
        "variant_history": [],
        "transformation_chain": [],
        "transformation_history": [],
    }


def build_response_memory(
    reply: str | None,
    *,
    response_type: str | None = None,
    generation_context: dict | None = None,
    previous_memory: dict | None = None,
    transformation_result: dict | None = None,
) -> dict:
    previous = previous_memory or {}
    text = str(reply or "").strip()
    chain = list(previous.get("last_transformation_chain") or [])
    history = list(previous.get("transformation_history") or [])
    variants = list(previous.get("last_variant_history") or [])

    if transformation_result:
        transformation_type = transformation_result.get("transformation_type")
        if transformation_type:
            chain.append(transformation_type)
            history.append(
                {
                    "transformation_type": transformation_type,
                    "transformation_reason": transformation_result.get("transformation_reason"),
                    "transformation_source": transformation_result.get("transformation_source"),
                }
            )
        if transformation_type == "VARIANT":
            variants.append(text)
    else:
        chain = []
        history = []
        variants = []

    return {
        "last_generated_response": text,
        "last_response_type": response_type or previous.get("last_response_type") or "assistant_response",
        "last_generation_context": deepcopy(generation_context or previous.get("last_generation_context") or {}),
        "last_variant_history": variants[-10:],
        "last_transformation_chain": chain[-20:],
        "transformation_history": history[-20:],
    }


def transform_response(user_message: str | None, application_state: dict | None) -> dict:
    detection = detect_response_transformation(user_message)
    source = transformation_source(application_state)
    if is_strong_cost_calculation_message(user_message):
        return {
            **detection,
            "handled": False,
            "reply": None,
            "transformation_source": None,
            "used_previous_response": False,
            "transformation_chain": [],
            "transformation_history": [],
            "response_reason": "strong_cost_calculation_intent_isolated",
        }
    if not detection.get("is_transformation") or not source.get("text"):
        return {
            **detection,
            "handled": False,
            "reply": None,
            "transformation_source": source.get("source"),
            "used_previous_response": False,
            "transformation_chain": source.get("transformation_chain") or [],
            "transformation_history": source.get("transformation_history") or [],
        }

    transformation_type = detection["transformation_type"]
    previous_text = source["text"]
    reply = _apply_transformation(previous_text, transformation_type)
    chain = [*(source.get("transformation_chain") or []), transformation_type]
    history = [
        *(source.get("transformation_history") or []),
        {
            "transformation_type": transformation_type,
            "transformation_reason": detection.get("transformation_reason"),
            "transformation_source": source.get("source"),
        },
    ]
    return {
        **detection,
        "handled": True,
        "reply": reply,
        "response_type": f"transformation_{str(transformation_type).lower()}",
        "response_source": "response_transformation",
        "response_reason": "transformed_previous_generated_response",
        "transformation_source": source.get("source"),
        "transformation_chain": chain,
        "transformation_history": history,
        "used_previous_response": True,
        "previous_response": previous_text,
        "last_response_type": source.get("response_type"),
        "last_generation_context": source.get("generation_context") or {},
        "last_variant_history": source.get("variant_history") or [],
        "planner_skipped": True,
        "direct_answer_mode": True,
        "conversation_style": "chatgpt_continuation",
        "continuation_mode": "response_transformation",
        "reuse_reason": "previous_generated_response_available",
        "response_generation_mode": "response_transformation",
    }


def _content_lines(text: str) -> list[str]:
    return [line.strip(" -•\t") for line in str(text or "").splitlines() if line.strip()]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", str(text or "").strip())
    return [part.strip(" -•\t") for part in parts if part.strip(" -•\t")]


def _first_content_sentence(text: str) -> str:
    for sentence in _sentences(text):
        if sentence.lower() in {"ได้เลยครับ", "ได้เลยค่ะ", "english version:"}:
            continue
        return sentence
    return str(text or "").strip()


def _apply_transformation(previous_text: str, transformation_type: str) -> str:
    text = str(previous_text or "").strip()
    if transformation_type == "SHORTEN":
        return _shorten(text)
    if transformation_type == "EXPAND":
        return _expand(text)
    if transformation_type == "VARIANT":
        return _variant(text)
    if transformation_type == "TRANSLATE":
        return _translate_to_english(text)
    if transformation_type == "BULLET":
        return _bullet(text)
    if transformation_type == "CTA":
        return _cta(text)
    if transformation_type == "EMOJI":
        return _emoji(text)
    if transformation_type == "CASUAL":
        return _tone(text, "casual")
    if transformation_type == "FORMAL":
        return _tone(text, "formal")
    if transformation_type == "YOUTH":
        return _tone(text, "youth")
    if transformation_type == "PROFESSIONAL":
        return _tone(text, "professional")
    if transformation_type == "SEO":
        return _seo(text)
    if transformation_type == "SALES":
        return _sales(text)
    if transformation_type == "SUMMARIZE":
        return _summarize(text)
    if transformation_type == "COMPRESS":
        return _compress(text)
    if transformation_type == "IMPROVE":
        return _improve(text)
    return _rewrite(text)


def _shorten(text: str) -> str:
    sentence = _first_content_sentence(text)
    return sentence[:220].rstrip()


def _expand(text: str) -> str:
    return f"{text}\n\nเพิ่มเหตุผลให้ลูกค้าตัดสินใจง่ายขึ้น: จุดเด่นชัด ประโยชน์ตรง และสั่งซื้อได้ทันที"


def _rewrite(text: str) -> str:
    sentence = _first_content_sentence(text)
    return f"ปรับใหม่:\n{sentence}\n\nอ่านลื่นขึ้น ชัดขึ้น และยังคงใจความเดิม"


def _variant(text: str) -> str:
    sentence = _first_content_sentence(text)
    return f"ได้เลยครับ อีกแบบ:\n\nวันนี้ลองเปลี่ยนมุมขายให้น่าสนใจกว่าเดิม: {sentence}"


def _translate_to_english(text: str) -> str:
    sentence = _first_content_sentence(text)
    return (
        "English version:\n\n"
        f"Try this version for your customers: {sentence}\n\n"
        "Clear benefit, easy decision, and a simple call to order today."
    )


def _bullet(text: str) -> str:
    lines = _content_lines(text)
    selected = lines[:5] if lines else [_first_content_sentence(text)]
    return "\n".join(f"- {line}" for line in selected)


def _cta(text: str) -> str:
    base = _first_content_sentence(text)
    return f"{base}\n\nทักแชทตอนนี้เพื่อสั่งซื้อหรือจองก่อนของหมด"


def _emoji(text: str) -> str:
    lines = _content_lines(text)
    if not lines:
        return f"✨ {text} 🧡"
    return "\n".join(f"{icon} {line}" for icon, line in zip(["✨", "🧡", "🔥", "📩", "✅"], lines + lines))


def _tone(text: str, mode: str) -> str:
    sentence = _first_content_sentence(text)
    prefixes = {
        "casual": "เอาแบบเป็นกันเอง:\n\n",
        "formal": "เรียนลูกค้าทุกท่าน\n\n",
        "youth": "สายชาไทยต้องลอง:\n\n",
        "professional": "ข้อความแบบมืออาชีพ:\n\n",
    }
    suffixes = {
        "casual": "\n\nอยากลองทักมาได้เลยนะครับ",
        "formal": "\n\nสอบถามรายละเอียดหรือสั่งซื้อได้ทางแชทครับ",
        "youth": "\n\nใครอยากลองของอร่อย ทักมาเลย",
        "professional": "\n\nเหมาะสำหรับลูกค้าที่ต้องการคุณภาพและบริการที่ชัดเจน",
    }
    return f"{prefixes.get(mode, '')}{sentence}{suffixes.get(mode, '')}"


def _seo(text: str) -> str:
    sentence = _first_content_sentence(text)
    return f"{sentence}\n\nคีย์เวิร์ด: ชาไทย, เครื่องดื่มไทย, ชาไทยอร่อย, เมนูขายดี\n#ชาไทย #เครื่องดื่มไทย #ชาไทยอร่อย #เมนูขายดี"


def _sales(text: str) -> str:
    sentence = _first_content_sentence(text)
    return f"{sentence}\n\nเหตุผลที่ควรซื้อวันนี้: รสชัด ตัดสินใจง่าย และสั่งได้ทันทีก่อนรอบนี้หมด"


def _summarize(text: str) -> str:
    return f"สรุป: {_first_content_sentence(text)}"


def _compress(text: str) -> str:
    sentence = _first_content_sentence(text).rstrip(".!?")
    return f"{sentence} ทักแชทเพื่อสั่งซื้อได้เลย"


def _improve(text: str) -> str:
    sentence = _first_content_sentence(text)
    return f"{sentence}\n\nปรับให้เด่นขึ้น: บอกประโยชน์ชัดขึ้น เพิ่มความน่าซื้อ และปิดท้ายให้ลูกค้าทักแชททันที"
