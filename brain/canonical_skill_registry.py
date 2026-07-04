from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from brain.knowledge_skill_reference import (
    AuthorityScope,
    CanonicalSkillDefinition,
    CompatibilityMode,
    EvidenceRequirement,
    KnowledgeReferences,
    MetricReferences,
    ReferenceProvenance,
    ReviewStatus,
    ValidationStatus,
    as_dict,
    as_list,
    unique,
)
from brain.legacy_skill_compatibility import evaluate_legacy_skill_compatibility
from brain.skill_authority_validator import validate_skill_authority
from brain.skill_markdown_parser import ParsedSkillDocument, parse_skill_markdown
from brain.skill_reference_validator import validate_skill_references
from brain.skill_schema_validator import validate_skill_schema


CANONICAL_SKILL_REGISTRY_VERSION = "5.9.1"
DEFAULT_CANONICAL_SKILLS_DIR = Path(__file__).resolve().parent.parent / "business_knowledge" / "canonical_skills"


def _requirements(metadata: dict) -> list[EvidenceRequirement]:
    refs = as_dict(metadata.get("canonical_references"))
    evidence = as_dict(refs.get("evidence"))
    result: list[EvidenceRequirement] = []
    for level, key in (("REQUIRED", "required"), ("CONDITIONALLY_REQUIRED", "conditionally_required"), ("OPTIONAL", "optional")):
        for evidence_id in as_list(evidence.get(key)):
            result.append(EvidenceRequirement(evidence_id=str(evidence_id), requirement_level=level, accepted_metric_ids=[str(evidence_id)]))
    return result


def _definition(parsed: ParsedSkillDocument, validation: dict) -> CanonicalSkillDefinition:
    metadata = parsed.metadata
    refs = as_dict(metadata.get("canonical_references"))
    knowledge = as_dict(refs.get("knowledge"))
    metrics = as_dict(refs.get("metrics"))
    authority = as_dict(metadata.get("authority"))
    compatibility = as_dict(metadata.get("compatibility"))
    review = as_dict(metadata.get("review"))
    all_issues = []
    for key in ("schema", "reference", "authority"):
        all_issues.extend(validation.get(key, {}).get("validation_issues") or [])
    statuses = [validation.get(key, {}).get("validation_status") for key in ("schema", "reference", "authority")]
    status = ValidationStatus.VALID.value
    if ValidationStatus.FATAL.value in statuses:
        status = ValidationStatus.FATAL.value
    elif ValidationStatus.INVALID.value in statuses:
        status = ValidationStatus.INVALID.value
    elif ValidationStatus.VALID_WITH_WARNINGS.value in statuses:
        status = ValidationStatus.VALID_WITH_WARNINGS.value
    return CanonicalSkillDefinition(
        skill_id=str(metadata.get("skill_id") or Path(parsed.source_path).stem),
        display_name=str(metadata.get("display_name") or ""),
        skill_version=str(metadata.get("skill_version") or ""),
        schema_version=str(metadata.get("schema_version") or ""),
        status=str(metadata.get("status") or ""),
        domain=str(metadata.get("domain") or ""),
        procedural_role=str(metadata.get("procedural_role") or ""),
        stage=str(metadata.get("stage") or ""),
        knowledge_references=KnowledgeReferences(primary=unique(as_list(knowledge.get("primary"))), secondary=unique(as_list(knowledge.get("secondary")))),
        metric_references=MetricReferences(input=unique(as_list(metrics.get("input"))), derived=unique(as_list(metrics.get("derived"))), context=unique(as_list(metrics.get("context")))),
        relationship_rule_references=unique(as_list(refs.get("relationship_rules"))),
        evidence_requirements=_requirements(metadata),
        supported_frames=unique(as_list(refs.get("supported_frames")) + as_list(metadata.get("supported_frames"))),
        supported_intents=unique(as_list(refs.get("supported_intents")) + as_list(metadata.get("supported_intents"))),
        applicability=as_dict(metadata.get("applicability")),
        exclusion_conditions=as_dict(metadata.get("exclusion_conditions")),
        readiness_policy=as_dict(metadata.get("readiness")),
        authority_scope=AuthorityScope(allowed=unique(as_list(authority.get("allowed"))), forbidden=unique(as_list(authority.get("forbidden")))),
        compatibility_mode=str(compatibility.get("mode") or CompatibilityMode.STRICT_CANONICAL.value),
        review_status=str(review.get("status") or ReviewStatus.UNREVIEWED.value),
        procedural_sections=deepcopy(parsed.sections),
        source_path=parsed.source_path,
        provenance=ReferenceProvenance(source_path=parsed.source_path),
        validation_status=status,
        validation_issues=all_issues,
        content=parsed.raw_body,
    )


class CanonicalSkillRegistry:
    def __init__(self, skills_dir: str | Path | None = None) -> None:
        self.skills_dir = Path(skills_dir) if skills_dir else DEFAULT_CANONICAL_SKILLS_DIR
        self.skills: dict[str, CanonicalSkillDefinition] = {}
        self.duplicate_ids: list[str] = []
        self.invalid_skills: list[dict] = []
        self.legacy_skills: list[dict] = []
        self.schema_versions: list[str] = []
        self.indexes: dict[str, dict[str, list[str]]] = {
            "knowledge_to_skills": {},
            "frame_to_skills": {},
            "intent_to_skills": {},
            "metric_to_skills": {},
            "domain_to_skills": {},
        }
        self._load()

    @property
    def registry_version(self) -> str:
        return CANONICAL_SKILL_REGISTRY_VERSION

    def _index(self, key: str, value: str, skill_id: str) -> None:
        self.indexes[key].setdefault(value, [])
        if skill_id not in self.indexes[key][value]:
            self.indexes[key][value].append(skill_id)
            self.indexes[key][value].sort()

    def _load(self) -> None:
        if not self.skills_dir.exists():
            return
        for path in sorted(self.skills_dir.rglob("*.md")):
            parsed = parse_skill_markdown(path)
            if parsed.parse_status == "LEGACY_NO_FRONT_MATTER":
                self.legacy_skills.append(evaluate_legacy_skill_compatibility({"source_path": str(path), "content": parsed.raw_body}).to_dict())
                continue
            schema = validate_skill_schema(parsed)
            reference = validate_skill_references(parsed)
            authority = validate_skill_authority(parsed)
            definition = _definition(parsed, {"schema": schema, "reference": reference, "authority": authority})
            if definition.skill_id in self.skills:
                self.duplicate_ids.append(definition.skill_id)
                definition.validation_status = ValidationStatus.INVALID.value
                definition.validation_issues.append({"code": "DUPLICATE_SKILL_ID", "severity": "ERROR", "field": "skill_id", "message": "Duplicate skill_id."})
            self.schema_versions.append(definition.schema_version)
            if definition.validation_status in {ValidationStatus.INVALID.value, ValidationStatus.FATAL.value}:
                self.invalid_skills.append({"skill_id": definition.skill_id, "source_path": definition.source_path, "validation_issues": definition.validation_issues})
            self.skills[definition.skill_id] = definition
        for skill_id, skill in sorted(self.skills.items()):
            for knowledge_id in skill.knowledge_references.primary + skill.knowledge_references.secondary:
                self._index("knowledge_to_skills", knowledge_id, skill_id)
            for frame_id in skill.supported_frames:
                self._index("frame_to_skills", frame_id, skill_id)
            for intent_id in skill.supported_intents:
                self._index("intent_to_skills", intent_id, skill_id)
            for metric_id in skill.metric_references.input + skill.metric_references.derived + skill.metric_references.context:
                self._index("metric_to_skills", metric_id, skill_id)
            if skill.domain:
                self._index("domain_to_skills", skill.domain, skill_id)
        self.schema_versions = sorted(set(self.schema_versions))

    def get_skill(self, skill_id: str) -> CanonicalSkillDefinition | None:
        item = self.skills.get(str(skill_id or ""))
        return deepcopy(item) if item else None

    def list_skills(self) -> list[CanonicalSkillDefinition]:
        return [deepcopy(self.skills[key]) for key in sorted(self.skills)]

    def _find(self, index: str, key: str) -> list[CanonicalSkillDefinition]:
        return [self.get_skill(skill_id) for skill_id in self.indexes[index].get(str(key or ""), []) if self.get_skill(skill_id)]

    def find_skills_by_knowledge(self, knowledge_id: str) -> list[CanonicalSkillDefinition]:
        return self._find("knowledge_to_skills", knowledge_id)

    def find_skills_by_frame(self, frame_id: str) -> list[CanonicalSkillDefinition]:
        return self._find("frame_to_skills", frame_id)

    def find_skills_by_intent(self, intent_id: str) -> list[CanonicalSkillDefinition]:
        return self._find("intent_to_skills", intent_id)

    def find_skills_by_metric(self, metric_id: str) -> list[CanonicalSkillDefinition]:
        return self._find("metric_to_skills", metric_id)

    def find_skills_by_domain(self, domain: str) -> list[CanonicalSkillDefinition]:
        return self._find("domain_to_skills", domain)

    def to_dict(self) -> dict:
        return {
            "skills": {key: value.to_dict() for key, value in sorted(self.skills.items())},
            "duplicate_ids": list(self.duplicate_ids),
            "invalid_skills": deepcopy(self.invalid_skills),
            "legacy_skills": deepcopy(self.legacy_skills),
            "schema_versions": list(self.schema_versions),
            "registry_version": self.registry_version,
            **deepcopy(self.indexes),
        }
