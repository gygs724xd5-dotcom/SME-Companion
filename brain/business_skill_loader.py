from __future__ import annotations

import re
from pathlib import Path
from typing import Any


BUSINESS_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "business_knowledge"
BUSINESS_SKILLS_DIR = BUSINESS_KNOWLEDGE_DIR / "skills"

FIELD_HEADINGS = {
    "Skill ID": "skill_id",
    "Skill Name": "skill_name",
    "Business Domain": "business_domain",
    "Business Principle": "business_principle",
    "Related Doctrine": "related_doctrine",
    "Conversation Stage": "conversation_stage",
    "Business Goal": "business_goal",
    "Situation": "situation",
    "Intent": "intent",
    "Thinking Pattern": "thinking_pattern",
    "Decision Tree": "decision_tree",
    "Example Questions": "example_questions",
    "Required Data": "required_data",
    "AI Should Ask": "ai_should_ask",
    "Reasoning": "reasoning",
    "Recommended Response": "recommended_response",
    "Bad Response": "bad_response",
    "AI Should Avoid": "ai_should_avoid",
    "Business Rules": "business_rules",
    "Workflow Integration": "workflow_integration",
    "Response Mode": "response_mode",
    "Tools Required": "tools_required",
    "Confidence": "confidence",
    "Memory Tags": "memory_tags",
    "Related Skills": "related_skills",
    "Future Learning Notes": "future_learning_notes",
}

REQUIRED_FIELDS = tuple(FIELD_HEADINGS.values())

PUBLIC_FIELDS = (
    "skill_id",
    "skill_name",
    "business_domain",
    "business_principle",
    "related_doctrine",
    "situation",
    "intent",
    "thinking_pattern",
    "decision_tree",
    "example_questions",
    "required_data",
    "ai_should_ask",
    "reasoning",
    "recommended_response",
    "bad_response",
    "ai_should_avoid",
    "business_rules",
    "workflow_integration",
    "response_mode",
    "tools_required",
    "confidence",
    "memory_tags",
    "related_skills",
    "future_learning_notes",
)

MATCH_ALIASES = {
    "customer_asks_price": (
        "ราคา",
        "ราคาเท่าไร",
        "เท่าไร",
        "กี่บาท",
        "how much",
        "price",
    ),
    "customer_says_expensive": (
        "แพง",
        "แพงไป",
        "ลดได้ไหม",
        "expensive",
    ),
    "customer_disappears": (
        "ลูกค้าหาย",
        "เงียบ",
        "ไม่ตอบ",
        "disappear",
        "ghost",
    ),
    "shipping_question": (
        "ค่าส่ง",
        "ส่งเท่าไร",
        "จัดส่ง",
        "shipping",
        "delivery",
    ),
    "refund_request": (
        "คืนเงิน",
        "ขอเงินคืน",
        "refund",
        "return",
    ),
}


def _empty_skill(path: str | Path | None = None) -> dict[str, Any]:
    skill = {field: "" for field in PUBLIC_FIELDS}
    skill.update(
        {
            "conversation_stage": "",
            "business_goal": "",
            "source_path": str(path or ""),
            "available": False,
            "valid": False,
            "warnings": [],
        }
    )
    return skill


def _strip_markdown_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        return value[1:-1].strip()
    return value


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _slug_from_skill_id(skill_id: str) -> str:
    parts = str(skill_id or "").split(".")
    return parts[-1] if parts else ""


def _parse_markdown_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for line in markdown.splitlines():
        heading_match = re.match(r"^#\s+(.+?)\s*$", line)
        if heading_match:
            heading = heading_match.group(1).strip()
            current_heading = FIELD_HEADINGS.get(heading)
            if current_heading:
                sections.setdefault(current_heading, [])
            continue

        if current_heading:
            sections[current_heading].append(line)

    return {
        field: _strip_markdown_value("\n".join(lines))
        for field, lines in sections.items()
    }


def load_business_skill(path: str | Path) -> dict[str, Any]:
    """Load one business skill markdown file into a safe structured dict."""
    skill_path = Path(path)
    skill = _empty_skill(skill_path)

    try:
        markdown = skill_path.read_text(encoding="utf-8")
    except Exception as exc:
        skill["warnings"].append(f"Could not read skill file: {exc}")
        return skill

    try:
        parsed = _parse_markdown_sections(markdown)
    except Exception as exc:
        skill["warnings"].append(f"Could not parse skill markdown: {exc}")
        skill["available"] = True
        return skill

    skill.update(parsed)
    skill["available"] = True

    missing_fields = [field for field in REQUIRED_FIELDS if not skill.get(field)]
    for field in missing_fields:
        skill["warnings"].append(f"Missing heading or content: {field}")

    if not skill.get("skill_id"):
        fallback_id = skill_path.stem
        skill["skill_id"] = fallback_id
        skill["warnings"].append(f"Using filename as fallback skill_id: {fallback_id}")

    skill["valid"] = not missing_fields
    return skill


def load_all_business_skills() -> list[dict[str, Any]]:
    """Load every markdown business skill under business_knowledge/skills/."""
    if not BUSINESS_SKILLS_DIR.exists():
        return []

    skills = [
        load_business_skill(path)
        for path in sorted(BUSINESS_SKILLS_DIR.rglob("*.md"))
        if path.is_file()
    ]
    return skills


def _skill_matches_domain(skill: dict[str, Any], domain: str | None) -> bool:
    if not domain:
        return True

    normalized_domain = _normalize_text(domain)
    domain_text = _normalize_text(skill.get("business_domain"))
    source_path = _normalize_text(skill.get("source_path"))
    return normalized_domain in domain_text or normalized_domain in source_path


def _score_skill(skill: dict[str, Any], query: str) -> int:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return 0

    skill_id = str(skill.get("skill_id") or "")
    slug = _slug_from_skill_id(skill_id)
    searchable_parts = [
        skill_id,
        slug,
        skill.get("skill_name", ""),
        skill.get("business_domain", ""),
        skill.get("situation", ""),
        skill.get("intent", ""),
        skill.get("example_questions", ""),
        skill.get("recommended_response", ""),
        skill.get("ai_should_avoid", ""),
        skill.get("business_rules", ""),
    ]
    searchable_text = _normalize_text(" ".join(str(part) for part in searchable_parts))

    score = 0
    if normalized_query in searchable_text:
        score += 5

    query_terms = [term for term in normalized_query.split(" ") if term]
    score += sum(1 for term in query_terms if term in searchable_text)

    for alias_slug, aliases in MATCH_ALIASES.items():
        if alias_slug != slug:
            continue
        for alias in aliases:
            normalized_alias = _normalize_text(alias)
            if normalized_alias and normalized_alias in normalized_query:
                score += 20

    return score


def search_business_skills(
    query: str,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    """Return matching business skills ordered by simple text relevance."""
    results = []
    for skill in load_all_business_skills():
        if not _skill_matches_domain(skill, domain):
            continue

        score = _score_skill(skill, query)
        if score > 0:
            result = dict(skill)
            result["match_score"] = score
            results.append(result)

    return sorted(
        results,
        key=lambda item: (-int(item.get("match_score", 0)), str(item.get("skill_id", ""))),
    )


def get_business_skill(skill_id: str) -> dict[str, Any] | None:
    """Return one business skill by full ID or slug."""
    normalized_id = str(skill_id or "").strip()
    normalized_slug = _slug_from_skill_id(normalized_id)
    if not normalized_id:
        return None

    for skill in load_all_business_skills():
        current_id = str(skill.get("skill_id") or "")
        current_slug = _slug_from_skill_id(current_id)
        if normalized_id == current_id or normalized_id == current_slug:
            return skill
        if normalized_slug and normalized_slug == current_slug:
            return skill

    return None
