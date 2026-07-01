from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

from brain.business_skill_loader import load_all_business_skills


REGISTRY_VERSION = "5.1.0"
DEFAULT_SKILL_STATUS = "adapter_loaded"
DEFAULT_SKILL_VERSION = "v4-adapter"


@dataclass(frozen=True)
class BusinessDomain:
    domain_id: str
    domain_name: str
    description: str = ""
    status: str = DEFAULT_SKILL_STATUS
    version: str = DEFAULT_SKILL_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BusinessSkill:
    skill_id: str
    domain_id: str
    domain_name: str
    intent: str
    description: str
    workflow_id: str | None = None
    required_entities: list[Any] = field(default_factory=list)
    required_memory: list[Any] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    reasoning: Any = ""
    response_style: Any = ""
    confidence: Any = ""
    status: str = DEFAULT_SKILL_STATUS
    version: str = DEFAULT_SKILL_VERSION
    skill_name: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_lookup(value: Any) -> str:
    text = str(value or "").lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _split_lines(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "")
    return [
        item.strip(" -\t\r\n")
        for item in re.split(r"[\n;]+", text)
        if item.strip(" -\t\r\n")
    ]


def _parse_domain(value: Any) -> tuple[str, str]:
    text = str(value or "").strip()
    match = re.match(r"^(\d+)\s+(.+)$", text)
    if match:
        return match.group(1), match.group(2).strip()
    return "", text


def _slug_from_skill_id(skill_id: Any) -> str:
    parts = str(skill_id or "").split(".")
    return parts[-1] if parts else ""


def _workflow_id(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    first_line = _split_lines(text)[0] if _split_lines(text) else text
    first_line = first_line.strip(" .")
    if not first_line:
        return None
    return first_line.split(":", 1)[0].strip() or None


def _adapt_legacy_skill(skill: dict[str, Any]) -> BusinessSkill:
    domain_id, domain_name = _parse_domain(skill.get("business_domain"))
    skill_id = str(skill.get("skill_id") or "").strip()
    diagnostics = {
        "adapter": "business_skill_loader",
        "source_path": skill.get("source_path"),
        "available": bool(skill.get("available")),
        "valid": bool(skill.get("valid")),
        "warnings": list(skill.get("warnings") or []),
    }
    metadata = {
        "source": "business_knowledge.skills",
        "legacy_fields": dict(skill),
        "business_principle": skill.get("business_principle"),
        "conversation_stage": skill.get("conversation_stage"),
        "business_goal": skill.get("business_goal"),
        "example_questions": _split_lines(skill.get("example_questions")),
        "follow_up": skill.get("ai_should_ask"),
        "tools": _split_lines(skill.get("tools_required")),
        "related_skills": _split_lines(skill.get("related_skills")),
        "future_extensions": skill.get("future_learning_notes"),
    }
    return BusinessSkill(
        skill_id=skill_id,
        skill_name=str(skill.get("skill_name") or skill_id),
        domain_id=domain_id,
        domain_name=domain_name or str(skill.get("business_domain") or ""),
        intent=str(skill.get("intent") or skill.get("situation") or ""),
        description=str(skill.get("situation") or skill.get("description") or ""),
        workflow_id=_workflow_id(skill.get("workflow_integration")),
        required_entities=_split_lines(skill.get("required_data")),
        required_memory=_split_lines(skill.get("memory_tags")),
        business_rules=_split_lines(skill.get("business_rules")),
        reasoning=skill.get("reasoning") or skill.get("thinking_pattern") or "",
        response_style=skill.get("response_mode") or skill.get("recommended_response") or "",
        confidence=skill.get("confidence") or "",
        diagnostics=diagnostics,
        metadata=metadata,
    )


class SkillRegistry:
    def __init__(self, *, registry_version: str = REGISTRY_VERSION) -> None:
        self.registry_version = registry_version
        self._skills_by_id: dict[str, BusinessSkill] = {}
        self._domains_by_id: dict[str, BusinessDomain] = {}

    def register_domain(self, domain: BusinessDomain) -> BusinessDomain:
        if not domain.domain_id and not domain.domain_name:
            raise ValueError("domain_id or domain_name is required")

        key = domain.domain_id or _normalize_lookup(domain.domain_name)
        existing = self._domains_by_id.get(key)
        if existing and existing != domain:
            raise ValueError(f"Duplicate domain registration: {key}")

        self._domains_by_id[key] = domain
        return domain

    def register_skill(self, skill: BusinessSkill | dict[str, Any]) -> BusinessSkill:
        if isinstance(skill, dict):
            skill = _adapt_legacy_skill(skill)
        if not skill.skill_id:
            raise ValueError("skill_id is required")
        if skill.skill_id in self._skills_by_id:
            raise ValueError(f"Duplicate skill registration: {skill.skill_id}")

        domain = BusinessDomain(
            domain_id=skill.domain_id,
            domain_name=skill.domain_name,
            status=skill.status,
            version=skill.version,
        )
        self.register_domain(domain)
        self._skills_by_id[skill.skill_id] = skill
        return skill

    def get_skill(self, skill_id: str) -> BusinessSkill | None:
        normalized = str(skill_id or "").strip()
        if not normalized:
            return None
        if normalized in self._skills_by_id:
            return self._skills_by_id[normalized]

        requested_slug = _slug_from_skill_id(normalized)
        for skill in self._skills_by_id.values():
            current_slug = _slug_from_skill_id(skill.skill_id)
            if normalized == current_slug or (requested_slug and requested_slug == current_slug):
                return skill
        return None

    def find_skill(
        self,
        intent: str | None = None,
        *,
        domain_id: str | None = None,
        domain_name: str | None = None,
    ) -> BusinessSkill | None:
        matches = self.find_skills(intent=intent, domain_id=domain_id, domain_name=domain_name)
        return matches[0] if matches else None

    def find_skills(
        self,
        intent: str | None = None,
        *,
        domain_id: str | None = None,
        domain_name: str | None = None,
    ) -> list[BusinessSkill]:
        intent_query = _normalize_lookup(intent)
        domain_id_query = str(domain_id or "").strip()
        domain_name_query = _normalize_lookup(domain_name)
        matches: list[BusinessSkill] = []

        for skill in self._skills_by_id.values():
            if domain_id_query and skill.domain_id != domain_id_query:
                continue
            if domain_name_query and domain_name_query not in _normalize_lookup(skill.domain_name):
                continue
            if intent_query:
                searchable = _normalize_lookup(
                    " ".join(
                        [
                            skill.skill_id,
                            skill.skill_name,
                            skill.intent,
                            skill.description,
                            " ".join(skill.business_rules),
                        ]
                    )
                )
                if intent_query not in searchable:
                    continue
            matches.append(skill)

        return sorted(matches, key=lambda item: item.skill_id)

    def list_domains(self) -> list[BusinessDomain]:
        return sorted(
            self._domains_by_id.values(),
            key=lambda item: (item.domain_id, item.domain_name),
        )

    def list_skills(self, domain_id: str | None = None, domain_name: str | None = None) -> list[BusinessSkill]:
        return self.find_skills(domain_id=domain_id, domain_name=domain_name)

    def skill_metadata(self, skill_id: str) -> dict[str, Any]:
        skill = self.get_skill(skill_id)
        if not skill:
            return {}
        return {
            "skill_id": skill.skill_id,
            "skill_name": skill.skill_name,
            "domain_id": skill.domain_id,
            "domain_name": skill.domain_name,
            "intent": skill.intent,
            "workflow_id": skill.workflow_id,
            "status": skill.status,
            "version": skill.version,
            "metadata": dict(skill.metadata),
        }

    def diagnostics(self) -> dict[str, Any]:
        return {
            "registry_version": self.registry_version,
            "registered_domains": len(self._domains_by_id),
            "registered_skills": len(self._skills_by_id),
            "domain_ids": [domain.domain_id for domain in self.list_domains()],
            "skill_ids": [skill.skill_id for skill in self.list_skills()],
        }


def create_registry(load_existing: bool = True) -> SkillRegistry:
    registry = SkillRegistry()
    if load_existing:
        for skill in load_all_business_skills():
            registry.register_skill(skill)
    return registry


def get_default_registry() -> SkillRegistry:
    return create_registry(load_existing=True)


def get_skill(skill_id: str) -> BusinessSkill | None:
    return get_default_registry().get_skill(skill_id)


def find_skill(
    intent: str | None = None,
    *,
    domain_id: str | None = None,
    domain_name: str | None = None,
) -> BusinessSkill | None:
    return get_default_registry().find_skill(intent=intent, domain_id=domain_id, domain_name=domain_name)


def list_domains() -> list[BusinessDomain]:
    return get_default_registry().list_domains()


def list_skills(domain_id: str | None = None, domain_name: str | None = None) -> list[BusinessSkill]:
    return get_default_registry().list_skills(domain_id=domain_id, domain_name=domain_name)


def registry_diagnostics() -> dict[str, Any]:
    return get_default_registry().diagnostics()
