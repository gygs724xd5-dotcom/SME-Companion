from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
import re
from typing import Any


SKILL_MARKDOWN_PARSER_VERSION = "5.9.1"


@dataclass(frozen=True)
class SkillParseIssue:
    code: str
    severity: str
    field: str = ""
    message: str = ""
    line_number: int | None = None
    raw_value: Any = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParsedSkillDocument:
    source_path: str
    raw_front_matter: str = ""
    raw_body: str = ""
    metadata: dict = field(default_factory=dict)
    sections: dict = field(default_factory=dict)
    parse_status: str = "EMPTY_DOCUMENT"
    parse_issues: list[dict] = field(default_factory=list)
    schema_version: str = ""
    checksum: str = ""
    version: str = SKILL_MARKDOWN_PARSER_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _issue(code: str, severity: str, field: str = "", message: str = "", line_number: int | None = None, raw_value: Any = None) -> SkillParseIssue:
    return SkillParseIssue(code, severity, field, message or code, line_number, raw_value)


def _parse_scalar(value: str) -> Any:
    text = value.strip()
    if text.startswith("[") and not text.endswith("]"):
        raise ValueError("invalid list literal")
    if text == "[]":
        return []
    if text in {"true", "True"}:
        return True
    if text in {"false", "False"}:
        return False
    if text in {"null", "None", "~"}:
        return None
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    return text


def _simple_yaml_load(raw: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    pending_key: tuple[int, dict, str] | None = None
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if stripped.startswith("- "):
            value_text = stripped[2:].strip()
            if not isinstance(parent, list):
                if pending_key is None:
                    raise ValueError(f"list item without key at line {line_number}")
                p_indent, p_map, p_key = pending_key
                if indent <= p_indent:
                    raise ValueError(f"bad list indentation at line {line_number}")
                parent = []
                p_map[p_key] = parent
                stack.append((indent - 1, parent))
            if ":" in value_text and not value_text.startswith(("'", '"')):
                key, value = value_text.split(":", 1)
                item = {key.strip(): _parse_scalar(value)}
                parent.append(item)
                stack.append((indent, item))
                pending_key = None
            else:
                parent.append(_parse_scalar(value_text))
            continue
        if ":" not in stripped:
            raise ValueError(f"invalid mapping at line {line_number}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        if not isinstance(parent, dict):
            raise ValueError(f"mapping inside list is not supported at line {line_number}")
        if value.strip():
            parent[key] = _parse_scalar(value)
            pending_key = None
        else:
            child: dict = {}
            parent[key] = child
            pending_key = (indent, parent, key)
            stack.append((indent, child))
    return root


def safe_load_front_matter(raw: str) -> dict:
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(raw) or {}
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return _simple_yaml_load(raw)


def _split_front_matter(text: str) -> tuple[str, str, str, list[SkillParseIssue]]:
    issues: list[SkillParseIssue] = []
    if not text.strip():
        return "", "", "EMPTY_DOCUMENT", issues
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", text, "LEGACY_NO_FRONT_MATTER", issues
    for index, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return "\n".join(lines[1:index - 1]), "\n".join(lines[index:]), "PARSED", issues
    issues.append(_issue("UNCLOSED_FRONT_MATTER", "FATAL", line_number=1))
    return "\n".join(lines[1:]), "", "INVALID_FRONT_MATTER", issues


def _sections(body: str) -> dict:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in body.splitlines():
        match = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if match:
            current = match.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def parse_skill_markdown(path: str | Path) -> ParsedSkillDocument:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except Exception as exc:
        return ParsedSkillDocument(
            source_path=str(source),
            parse_status="INVALID_FRONT_MATTER",
            parse_issues=[_issue("READ_ERROR", "FATAL", message=str(exc)).to_dict()],
        )
    raw_front_matter, body, status, issues = _split_front_matter(text)
    metadata: dict = {}
    if raw_front_matter:
        try:
            metadata = safe_load_front_matter(raw_front_matter)
            if not isinstance(metadata, dict):
                metadata = {}
                issues.append(_issue("FRONT_MATTER_NOT_OBJECT", "FATAL"))
                status = "INVALID_FRONT_MATTER"
        except Exception as exc:
            issues.append(_issue("INVALID_YAML", "FATAL", message=str(exc)))
            status = "INVALID_FRONT_MATTER"
    if status == "PARSED" and issues:
        status = "PARSED_WITH_WARNINGS"
    return ParsedSkillDocument(
        source_path=str(source),
        raw_front_matter=raw_front_matter,
        raw_body=body,
        metadata=deepcopy(metadata),
        sections=_sections(body),
        parse_status=status,
        parse_issues=[item.to_dict() for item in issues],
        schema_version=str(metadata.get("schema_version") or ""),
        checksum=sha256(text.encode("utf-8")).hexdigest(),
    )


def parse_skill_markdown_text(text: str, source_path: str = "<memory>") -> ParsedSkillDocument:
    temp = ParsedSkillDocument(source_path=source_path, checksum=sha256(str(text or "").encode("utf-8")).hexdigest())
    raw_front_matter, body, status, issues = _split_front_matter(str(text or ""))
    metadata = {}
    if raw_front_matter:
        try:
            metadata = safe_load_front_matter(raw_front_matter)
        except Exception as exc:
            issues.append(_issue("INVALID_YAML", "FATAL", message=str(exc)))
            status = "INVALID_FRONT_MATTER"
    temp.raw_front_matter = raw_front_matter
    temp.raw_body = body
    temp.metadata = deepcopy(metadata)
    temp.sections = _sections(body)
    temp.parse_status = status if not (status == "PARSED" and issues) else "PARSED_WITH_WARNINGS"
    temp.parse_issues = [item.to_dict() for item in issues]
    temp.schema_version = str(metadata.get("schema_version") or "")
    return temp
