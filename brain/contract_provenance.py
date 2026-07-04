from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any

from brain.business_knowledge_registry import BusinessKnowledgeRegistry
from brain.canonical_skill_registry import CanonicalSkillRegistry
from brain.knowledge_skill_reference import as_list
from brain.perspective_frame_registry import PerspectiveFrameRegistry
from brain.skill_markdown_parser import parse_skill_markdown


CONTRACT_PROVENANCE_VERSION = "5.9.2"


class ContractType(str, Enum):
    KNOWLEDGE = "KNOWLEDGE"
    METRIC = "METRIC"
    RELATIONSHIP_RULE = "RELATIONSHIP_RULE"
    SKILL = "SKILL"
    FRAME = "FRAME"
    INTENT = "INTENT"
    EVIDENCE_REQUIREMENT = "EVIDENCE_REQUIREMENT"
    AUTHORITY_POLICY = "AUTHORITY_POLICY"
    SCHEMA = "SCHEMA"


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"


class DeprecationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    REPLACED = "REPLACED"
    REMOVED = "REMOVED"


@dataclass(frozen=True)
class ContractProvenance:
    contract_type: str
    contract_id: str
    contract_version: str = ""
    registry_version: str = ""
    source_path: str = ""
    source_checksum: str = ""
    created_in_version: str = ""
    last_modified_version: str = ""
    last_validated_version: str = ""
    review_status: str = ReviewStatus.UNREVIEWED.value
    authoritative: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SkillReferenceSnapshot:
    skill_id: str
    skill_version: str = ""
    knowledge_versions: dict[str, str] = field(default_factory=dict)
    metric_versions: dict[str, str] = field(default_factory=dict)
    relationship_rule_versions: dict[str, str] = field(default_factory=dict)
    frame_registry_version: str = ""
    authority_policy_version: str = ""
    schema_version: str = ""
    source_checksum: str = ""
    validated_at_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ContractRename:
    old_id: str
    new_id: str
    contract_type: str
    effective_version: str
    approved: bool = False
    migration_note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def deterministic_checksum(value: Any) -> str:
    text = repr(_plain(value))
    return sha256(text.encode("utf-8")).hexdigest()


def file_checksum(path: str | Path | None) -> str:
    if not path:
        return ""
    source = Path(path)
    try:
        return sha256(source.read_bytes()).hexdigest()
    except Exception:
        return ""


def _plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if hasattr(value, "__dataclass_fields__"):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): _plain(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in sorted(value, key=str)] if isinstance(value, set) else [_plain(item) for item in value]
    return deepcopy(value)


def build_skill_reference_snapshot(skill: Any, *, validated_at_version: str = CONTRACT_PROVENANCE_VERSION) -> SkillReferenceSnapshot:
    knowledge_registry = BusinessKnowledgeRegistry()
    frame_registry = PerspectiveFrameRegistry()
    knowledge_ids = list(getattr(skill.knowledge_references, "primary", [])) + list(getattr(skill.knowledge_references, "secondary", []))
    metric_ids = list(getattr(skill.metric_references, "input", [])) + list(getattr(skill.metric_references, "derived", [])) + list(getattr(skill.metric_references, "context", []))
    relationship_ids = list(getattr(skill, "relationship_rule_references", []))
    knowledge_versions = {knowledge_id: (knowledge_registry.get(knowledge_id).version if knowledge_registry.get(knowledge_id) else "") for knowledge_id in sorted(set(knowledge_ids))}
    metric_versions = {metric_id: knowledge_registry.version for metric_id in sorted(set(metric_ids))}
    relationship_versions = {rule_id: knowledge_registry.version for rule_id in sorted(set(relationship_ids))}
    checksum = file_checksum(getattr(skill, "source_path", "")) or deterministic_checksum(getattr(skill, "content", ""))
    return SkillReferenceSnapshot(
        skill_id=str(getattr(skill, "skill_id", "")),
        skill_version=str(getattr(skill, "skill_version", "")),
        knowledge_versions=knowledge_versions,
        metric_versions=metric_versions,
        relationship_rule_versions=relationship_versions,
        frame_registry_version=frame_registry.version,
        authority_policy_version="5.9.2",
        schema_version=str(getattr(skill, "schema_version", "")),
        source_checksum=checksum,
        validated_at_version=validated_at_version,
    )


def canonical_contract_provenance() -> list[dict]:
    knowledge_registry = BusinessKnowledgeRegistry()
    skill_registry = CanonicalSkillRegistry()
    frame_registry = PerspectiveFrameRegistry()
    records: list[ContractProvenance] = []
    for item in knowledge_registry.list():
        records.append(ContractProvenance(ContractType.KNOWLEDGE.value, item.knowledge_id, item.version, knowledge_registry.version, review_status=ReviewStatus.APPROVED.value))
        for metric_id in item.metrics + item.required_evidence + item.optional_evidence:
            records.append(ContractProvenance(ContractType.METRIC.value, metric_id, item.version, knowledge_registry.version, review_status=ReviewStatus.APPROVED.value))
        for rule in item.relationship_rules:
            records.append(ContractProvenance(ContractType.RELATIONSHIP_RULE.value, rule.rule_id, item.version, knowledge_registry.version, review_status=ReviewStatus.APPROVED.value))
    for frame in frame_registry.list():
        records.append(ContractProvenance(ContractType.FRAME.value, frame.frame_id, frame.version, frame_registry.version, review_status=ReviewStatus.APPROVED.value))
    for skill in skill_registry.list_skills():
        parsed = parse_skill_markdown(skill.source_path)
        review = (parsed.metadata.get("review") or {}) if isinstance(parsed.metadata, dict) else {}
        records.append(
            ContractProvenance(
                ContractType.SKILL.value,
                skill.skill_id,
                skill.skill_version,
                skill_registry.registry_version,
                skill.source_path,
                parsed.checksum,
                created_in_version=skill.schema_version,
                last_modified_version=skill.skill_version,
                last_validated_version=str(review.get("reviewed_version") or ""),
                review_status=skill.review_status,
                authoritative=skill.compatibility_mode == "strict_canonical",
            )
        )
        for evidence in skill.evidence_requirements:
            records.append(ContractProvenance(ContractType.EVIDENCE_REQUIREMENT.value, evidence.evidence_id, skill.skill_version, skill_registry.registry_version, skill.source_path, parsed.checksum, review_status=skill.review_status))
        for intent in as_list(getattr(skill, "supported_intents", [])):
            records.append(ContractProvenance(ContractType.INTENT.value, str(intent), skill.skill_version, skill_registry.registry_version, skill.source_path, parsed.checksum, review_status=skill.review_status))
    records.append(ContractProvenance(ContractType.AUTHORITY_POLICY.value, "skill_authority_policy", "5.9.2", "5.9.2", review_status=ReviewStatus.APPROVED.value))
    records.append(ContractProvenance(ContractType.SCHEMA.value, "canonical_skill_schema", "5.9.1", skill_registry.registry_version, review_status=ReviewStatus.APPROVED.value))
    return [item.to_dict() for item in sorted(records, key=lambda item: (item.contract_type, item.contract_id, item.source_path))]
