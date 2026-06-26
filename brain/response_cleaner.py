import re


LABEL_REPLACEMENTS = {
    "Business Operating System Dashboard": "แผนงานธุรกิจ",
    "Business Insight Dashboard": "ภาพรวมธุรกิจ",
    "Revenue Engine": "ระบบเพิ่มยอดขาย",
    "Daily Content": "คอนเทนต์ประจำวัน",
    "customer review": "รีวิวลูกค้า",
    "behind the scenes": "เบื้องหลังร้าน",
    "product education": "ความรู้สินค้า",
    "promotion": "โปรโมชัน",
    "social proof": "หลักฐานจากลูกค้า",
    "urgency campaign": "กระตุ้นการตัดสินใจ",
}


def _normalize_line(line: str) -> str:
    normalized = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line or "")
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


def remove_duplicate_lines(text: str) -> str:
    seen = set()
    output = []
    for line in str(text or "").splitlines():
        key = _normalize_line(line)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        output.append(line)
    return "\n".join(output).strip()


def remove_duplicate_bullets(text: str) -> str:
    seen = set()
    output = []
    bullet_pattern = re.compile(r"^(\s*(?:[-*•]|\d+[.)])\s+)(.+)$")
    for line in str(text or "").splitlines():
        match = bullet_pattern.match(line)
        if not match:
            output.append(line)
            continue

        key = _normalize_line(match.group(2))
        if key in seen:
            continue
        seen.add(key)
        output.append(line)
    return "\n".join(output).strip()


def localize_internal_labels(text: str) -> str:
    cleaned = str(text or "")
    for source, replacement in LABEL_REPLACEMENTS.items():
        cleaned = re.sub(re.escape(source), replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


def clean_response(text: str) -> str:
    cleaned = localize_internal_labels(str(text or "").strip())
    cleaned = remove_duplicate_bullets(cleaned)
    cleaned = remove_duplicate_lines(cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
