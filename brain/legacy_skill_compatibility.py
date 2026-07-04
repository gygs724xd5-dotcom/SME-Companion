from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


LEGACY_SKILL_COMPATIBILITY_VERSION = "5.9.1"


@dataclass
class LegacySkillCompatibilityResult:
    skill_id: str
    source_path: str
    classification: str
    loadable: bool = True
    indexable: bool = False
    rankable: bool = False
    primary_eligible: bool = False
    secondary_eligible: bool = False
    diagnostic_only: bool = True
    inferred_domain: str = ""
    inferred_intents: list[str] = field(default_factory=list)
    inferred_knowledge_ids: list[str] = field(default_factory=list)
    inferred_metric_ids: list[str] = field(default_factory=list)
    inference_confidence: str = "UNUSABLE"
    compatibility_authority: str = "DIAGNOSTIC_ONLY"
    migration_priority: str = "LOW"
    migration_reasons: list[str] = field(default_factory=list)
    replacement_skill_id: str = ""
    warnings: list[str] = field(default_factory=list)
    version: str = LEGACY_SKILL_COMPATIBILITY_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SkillMigrationRecord:
    skill_id: str
    source_path: str
    current_classification: str
    target_skill_id: str = ""
    migration_status: str = "DISCOVERED"
    mapped_knowledge_ids: list[str] = field(default_factory=list)
    mapped_metric_ids: list[str] = field(default_factory=list)
    mapped_relationship_rules: list[str] = field(default_factory=list)
    unresolved_references: list[str] = field(default_factory=list)
    authority_issues: list[str] = field(default_factory=list)
    duplicate_candidates: list[str] = field(default_factory=list)
    migration_priority: str = "LOW"
    estimated_complexity: str = "LOW"
    review_required: bool = True
    last_updated_version: str = LEGACY_SKILL_COMPATIBILITY_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LegacyReferenceAlias:
    legacy_id: str
    canonical_id: str
    alias_type: str
    confidence: str
    approved: bool
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


def _text(skill: dict) -> str:
    return " ".join(str(skill.get(key) or "") for key in ("skill_id", "name", "skill_name", "content", "required_data", "intent", "source_path")).lower()


def evaluate_legacy_skill_compatibility(skill: dict[str, Any]) -> LegacySkillCompatibilityResult:
    source_path = str(skill.get("source_path") or "")
    skill_id = str(skill.get("skill_id") or Path(source_path).stem or "unknown_legacy_skill")
    status = str(skill.get("status") or "").lower()
    text = _text(skill)
    if status == "deprecated" or "deprecated" in text:
        return LegacySkillCompatibilityResult(skill_id, source_path, "DEPRECATED_LEGACY", loadable=True, compatibility_authority="DISABLED", warnings=["Deprecated legacy skill cannot rank."])
    if not text.strip():
        return LegacySkillCompatibilityResult(skill_id, source_path, "INVALID_LEGACY", loadable=False, warnings=["Legacy skill has no readable text."])
    has_sections = any(token in text for token in ("required data", "required_data", "workflow", "intent", "ai should ask"))
    inferred_knowledge: list[str] = []
    inferred_metrics: list[str] = []
    replacement = ""
    domain = ""
    if "cost" in text or "ต้นทุน" in text:
        inferred_knowledge.append("UNIT_ECONOMICS")
        inferred_metrics.extend(["selling_price", "unit_cost"])
        replacement = "calculate_product_margin"
        domain = "finance"
    if "profit" in text or "กำไร" in text:
        inferred_knowledge.extend(["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"])
        inferred_metrics.extend(["total_revenue", "net_profit"])
        domain = domain or "finance"
    if "inventory" in text or "stock" in text:
        inferred_knowledge.append("INVENTORY_HEALTH")
        inferred_metrics.append("current_stock")
        domain = domain or "inventory"
    confidence = "HIGH" if has_sections and inferred_knowledge else "MEDIUM" if inferred_knowledge else "LOW" if has_sections else "UNUSABLE"
    classification = "LEGACY_STRUCTURED" if has_sections else "LEGACY_UNSTRUCTURED"
    rankable = classification == "LEGACY_STRUCTURED" and confidence in {"HIGH", "MEDIUM"}
    return LegacySkillCompatibilityResult(
        skill_id=skill_id,
        source_path=source_path,
        classification=classification,
        loadable=True,
        indexable=rankable,
        rankable=rankable,
        primary_eligible=False,
        secondary_eligible=rankable,
        diagnostic_only=not rankable,
        inferred_domain=domain,
        inferred_intents=[],
        inferred_knowledge_ids=sorted(set(inferred_knowledge)),
        inferred_metric_ids=sorted(set(inferred_metrics)),
        inference_confidence=confidence,
        compatibility_authority="ADVISORY" if rankable else "DIAGNOSTIC_ONLY",
        migration_priority="MEDIUM" if inferred_knowledge else "LOW",
        migration_reasons=["front matter missing", "references inferred for diagnostics only"],
        replacement_skill_id=replacement,
        warnings=["Legacy references are not authoritative.", "Silent canonical upgrade prevented."],
    )


def create_migration_record(result: LegacySkillCompatibilityResult) -> SkillMigrationRecord:
    return SkillMigrationRecord(
        skill_id=result.skill_id,
        source_path=result.source_path,
        current_classification=result.classification,
        target_skill_id=result.replacement_skill_id,
        mapped_knowledge_ids=list(result.inferred_knowledge_ids),
        mapped_metric_ids=list(result.inferred_metric_ids),
        migration_priority=result.migration_priority,
        review_required=True,
    )
