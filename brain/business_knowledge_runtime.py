from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from brain.business_skill_registry import (
    BusinessDomain,
    BusinessSkill,
    SkillRegistry,
    create_registry,
)
from brain.canonical_objects import KnowledgeContext


KNOWLEDGE_CONTEXT_VERSION = "5.1.2"
KNOWLEDGE_RUNTIME_SOURCE = "business_skill_registry"


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return dict(value)
    return {}


def _dedupe(values: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for value in values:
        key = repr(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _skill_id(value: Any) -> str | None:
    if isinstance(value, BusinessSkill):
        return value.skill_id
    if isinstance(value, dict):
        return value.get("skill_id")
    text = str(value or "").strip()
    return text or None


def _domain_id_from_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.split(" ", 1)[0] if text[:2].isdigit() else text


class BusinessKnowledgeRuntime:
    """Read-only V5 Business Knowledge runtime foundation.

    This layer exposes registry-backed knowledge to diagnostics and future
    reasoning migration work. It does not choose routes, change planner output,
    start workflows, or render responses.
    """

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or create_registry(load_existing=True)

    @property
    def registry_version(self) -> str:
        return self.registry.registry_version

    def candidate_domains(
        self,
        *,
        intent: str | None = None,
        domain_id: str | None = None,
        domain_name: str | None = None,
        candidate_skills: list[BusinessSkill] | None = None,
    ) -> list[dict[str, Any]]:
        domains_by_id = {domain.domain_id: domain for domain in self.registry.list_domains()}
        domains: list[BusinessDomain] = []

        for skill in candidate_skills or []:
            domain = domains_by_id.get(skill.domain_id) or BusinessDomain(
                domain_id=skill.domain_id,
                domain_name=skill.domain_name,
                status=skill.status,
                version=skill.version,
            )
            domains.append(domain)

        if not domains and (intent or domain_id or domain_name):
            for skill in self.registry.find_skills(intent=intent, domain_id=domain_id, domain_name=domain_name):
                domain = domains_by_id.get(skill.domain_id)
                if domain:
                    domains.append(domain)

        if not domains and (domain_id or domain_name):
            for domain in self.registry.list_domains():
                if domain_id and domain.domain_id == domain_id:
                    domains.append(domain)
                elif domain_name and str(domain_name).lower() in domain.domain_name.lower():
                    domains.append(domain)

        return [_as_dict(domain) for domain in _dedupe(domains)]

    def candidate_skills(
        self,
        *,
        intent: str | None = None,
        domain_id: str | None = None,
        domain_name: str | None = None,
        skill_ids: list[Any] | None = None,
    ) -> list[BusinessSkill]:
        skills: list[BusinessSkill] = []
        for requested in skill_ids or []:
            skill = self.registry.get_skill(str(requested or ""))
            if skill:
                skills.append(skill)

        for skill in self.registry.find_skills(intent=intent, domain_id=domain_id, domain_name=domain_name):
            skills.append(skill)

        if not skills and (domain_id or domain_name):
            skills.extend(self.registry.list_skills(domain_id=domain_id, domain_name=domain_name))

        return _dedupe(skills)

    def domain_metadata(self, domain_id: str | None = None, domain_name: str | None = None) -> dict[str, Any]:
        domain_id = str(domain_id or "").strip()
        domain_name = str(domain_name or "").strip().lower()
        for domain in self.registry.list_domains():
            if domain_id and domain.domain_id == domain_id:
                return domain.to_dict()
            if domain_name and domain_name in domain.domain_name.lower():
                return domain.to_dict()
        return {}

    def skill_metadata(self, skill_id: str | None) -> dict[str, Any]:
        return self.registry.skill_metadata(str(skill_id or ""))

    def workflow_candidates(self, skills: list[BusinessSkill]) -> list[dict[str, Any]]:
        return _dedupe(
            [
                _compact(
                    {
                        "workflow_id": skill.workflow_id,
                        "skill_id": skill.skill_id,
                        "domain_id": skill.domain_id,
                        "domain_name": skill.domain_name,
                    }
                )
                for skill in skills
                if skill.workflow_id
            ]
        )

    def required_entities(self, skills: list[BusinessSkill]) -> list[Any]:
        return _dedupe([entity for skill in skills for entity in (skill.required_entities or [])])

    def required_memory(self, skills: list[BusinessSkill]) -> list[Any]:
        return _dedupe([memory for skill in skills for memory in (skill.required_memory or [])])

    def business_rules(self, skills: list[BusinessSkill]) -> list[str]:
        return _dedupe([rule for skill in skills for rule in (skill.business_rules or [])])

    def reasoning_patterns(self, skills: list[BusinessSkill]) -> list[Any]:
        return _dedupe([skill.reasoning for skill in skills if skill.reasoning not in (None, "", [], {})])

    def tool_candidates(self, skills: list[BusinessSkill]) -> list[Any]:
        tools: list[Any] = []
        for skill in skills:
            tools.extend((skill.metadata or {}).get("tools") or [])
        return _dedupe(tools)

    def create_context(
        self,
        *,
        user_message: str | None = None,
        conversation_context: dict[str, Any] | None = None,
        planner_output: dict[str, Any] | None = None,
        business_intelligence: dict[str, Any] | None = None,
    ) -> KnowledgeContext:
        context = conversation_context or {}
        plan = planner_output or {}
        bridge = business_intelligence or {}
        business_context = context.get("business_context") or {}

        matched_skill = bridge.get("matched_skill") if isinstance(bridge.get("matched_skill"), dict) else {}
        selected_skill = (
            matched_skill.get("skill_id")
            or bridge.get("top_skill")
            or plan.get("selected_business_skill")
            or context.get("selected_business_skill")
        )
        selected_domain = (
            bridge.get("matched_domain")
            or matched_skill.get("business_domain")
            or plan.get("selected_business_domain")
            or context.get("selected_business_domain")
            or business_context.get("business_domain")
        )
        domain_id = _domain_id_from_label(selected_domain)
        skill_ids = [
            selected_skill,
            *[
                item.get("skill_id")
                for item in (bridge.get("matched_skills") or bridge.get("ranking_table") or [])
                if isinstance(item, dict)
            ],
        ]
        intent = (
            context.get("detected_intent")
            or (context.get("business_intent") or {}).get("detected_intent")
            or business_context.get("detected_intent")
            or user_message
        )
        skills = self.candidate_skills(
            intent=str(intent or ""),
            domain_id=domain_id,
            skill_ids=[skill_id for skill_id in skill_ids if skill_id],
        )
        selected = self.registry.get_skill(str(selected_skill or "")) if selected_skill else None
        knowledge_skills = [selected] if selected else skills[:5]
        knowledge_skills = [skill for skill in knowledge_skills if skill]
        domains = self.candidate_domains(
            intent=str(intent or ""),
            domain_id=domain_id,
            candidate_skills=skills,
        )
        workflows = self.workflow_candidates(knowledge_skills or skills)
        tools = self.tool_candidates(knowledge_skills or skills)
        reasoning_patterns = self.reasoning_patterns(knowledge_skills or skills)
        confidence = float(bridge.get("confidence") or bridge.get("top_confidence") or 0.0)

        diagnostics = {
            "knowledge_context_created": True,
            "knowledge_context_version": KNOWLEDGE_CONTEXT_VERSION,
            "registry_version": self.registry_version,
            "candidate_domain_count": len(domains),
            "candidate_skill_count": len(skills),
            "knowledge_runtime_source": KNOWLEDGE_RUNTIME_SOURCE,
            "runtime_mode": "diagnostics_only",
            "routing_decision_owner": "existing_v4_path",
        }

        return KnowledgeContext(
            candidate_domains=domains,
            candidate_skills=[skill.to_dict() for skill in skills],
            selected_domain=str(selected_domain or ""),
            selected_skill=str(selected_skill or ""),
            selected_domain_hint=str(selected_domain or ""),
            business_rules=self.business_rules(knowledge_skills or skills),
            reasoning_pattern=str(reasoning_patterns[0]) if reasoning_patterns else "",
            reasoning_patterns=reasoning_patterns,
            required_entities=self.required_entities(knowledge_skills or skills),
            required_memory=self.required_memory(knowledge_skills or skills),
            workflow_candidates=workflows,
            workflow_links=workflows,
            tool_candidates=tools,
            tool_requirements=tools,
            confidence=confidence,
            diagnostics=diagnostics,
            version=KNOWLEDGE_CONTEXT_VERSION,
        )


def create_knowledge_context(
    *,
    user_message: str | None = None,
    conversation_context: dict[str, Any] | None = None,
    planner_output: dict[str, Any] | None = None,
    business_intelligence: dict[str, Any] | None = None,
    registry: SkillRegistry | None = None,
) -> KnowledgeContext:
    return BusinessKnowledgeRuntime(registry=registry).create_context(
        user_message=user_message,
        conversation_context=conversation_context,
        planner_output=planner_output,
        business_intelligence=business_intelligence,
    )

