from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SKILL_DIRECTORY = Path(__file__).resolve().parent.parent / "skills"

SKILL_FILES = {
    "sales_planning": "sales_planning.md",
    "cost_calculation": "cost_calculation.md",
    "content_creation": "content_creation.md",
    "receipt_capture": "receipt_capture.md",
    "dashboard_builder": "dashboard_builder.md",
    "marketing": "marketing.md",
    "developer_feedback": "developer_feedback.md",
}

CAPABILITY_SKILLS = {
    "Sales Plan": "sales_planning",
    "Content Plan": "content_creation",
    "Cost Calculation": "cost_calculation",
    "Dashboard Request": "dashboard_builder",
    "Receipt Upload": "receipt_capture",
    "Product Feedback": "developer_feedback",
    "Developer Intelligence": "developer_feedback",
    "Marketing": "marketing",
}


@dataclass(frozen=True)
class Skill:
    name: str
    path: str
    content: str
    available: bool


def _normalize_skill_name(name: str | None) -> str:
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


def load_skill(name: str | None) -> Skill | None:
    normalized = _normalize_skill_name(name)
    if not normalized:
        return None

    filename = SKILL_FILES.get(normalized)
    if not filename:
        return Skill(name=normalized, path="", content="", available=False)

    path = SKILL_DIRECTORY / filename
    if not path.exists():
        return Skill(name=normalized, path=str(path), content="", available=False)

    return Skill(
        name=normalized,
        path=str(path),
        content=path.read_text(encoding="utf-8"),
        available=True,
    )


def load_skills(names: list[str] | None) -> list[Skill]:
    skills = []
    for name in names or []:
        skill = load_skill(name)
        if skill is not None:
            skills.append(skill)
    return skills


def load_skill_for_capability(capability_name: str | None) -> Skill | None:
    skill_name = CAPABILITY_SKILLS.get(str(capability_name or "").strip())
    return load_skill(skill_name)
