from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from brain.business_knowledge_registry import BusinessKnowledgeRegistry
from brain.contract_change_manifest import build_contract_change_manifest
from brain.contract_provenance import ContractRename, SkillReferenceSnapshot, build_skill_reference_snapshot
from brain.knowledge_skill_reference import as_dict
from brain.perspective_frame_registry import PerspectiveFrameRegistry
from brain.skill_reference_validator import APPROVED_ALIASES


CONTRACT_DRIFT_DETECTOR_VERSION = "5.9.2"


class DriftType(str, Enum):
    KNOWLEDGE_DEFINITION_DRIFT = "KNOWLEDGE_DEFINITION_DRIFT"
    METRIC_DEFINITION_DRIFT = "METRIC_DEFINITION_DRIFT"
    RELATIONSHIP_RULE_DRIFT = "RELATIONSHIP_RULE_DRIFT"
    EVIDENCE_REQUIREMENT_DRIFT = "EVIDENCE_REQUIREMENT_DRIFT"
    SKILL_METADATA_DRIFT = "SKILL_METADATA_DRIFT"
    SKILL_BODY_DRIFT = "SKILL_BODY_DRIFT"
    AUTHORITY_POLICY_DRIFT = "AUTHORITY_POLICY_DRIFT"
    FRAME_REGISTRY_DRIFT = "FRAME_REGISTRY_DRIFT"
    INTENT_REGISTRY_DRIFT = "INTENT_REGISTRY_DRIFT"
    SCHEMA_VERSION_DRIFT = "SCHEMA_VERSION_DRIFT"


class DriftSeverity(str, Enum):
    NONE = "NONE"
    INFORMATIONAL = "INFORMATIONAL"
    NON_BREAKING = "NON_BREAKING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BREAKING = "BREAKING"
    CONSTITUTIONAL = "CONSTITUTIONAL"


class CompatibilityStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    COMPATIBLE_WITH_WARNINGS = "COMPATIBLE_WITH_WARNINGS"
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"
    MIGRATION_REQUIRED = "MIGRATION_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class ContractDriftResult:
    skill_id: str
    drift_detected: bool = False
    drift_types: list[str] = field(default_factory=list)
    changed_contracts: list[dict] = field(default_factory=list)
    previous_snapshot: dict = field(default_factory=dict)
    current_snapshot: dict = field(default_factory=dict)
    severity: str = DriftSeverity.NONE.value
    compatibility_status: str = CompatibilityStatus.COMPATIBLE.value
    revalidation_required: bool = False
    rereview_required: bool = False
    migration_required: bool = False
    authority_restricted: bool = False
    ranking_penalty: float = 0.0
    blocking_reason: str = ""
    declared_review_status: str = ""
    effective_review_status: str = ""
    reference_freshness: str = "CURRENT"
    body_metadata_diagnostics: list[dict] = field(default_factory=list)
    registry_integrity: dict = field(default_factory=dict)
    change_manifest: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ContractMigrationRecord:
    contract_type: str
    source_id: str
    affected_skill_ids: list[str]
    drift_type: str
    severity: str
    required_action: str
    migration_status: str = "OPEN"
    blocking_runtime_use: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ContractMigrationQueue:
    records: list[dict] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    next_item: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _snapshot_dict(snapshot: SkillReferenceSnapshot | dict | None) -> dict:
    if snapshot is None:
        return {}
    if hasattr(snapshot, "to_dict"):
        return snapshot.to_dict()
    return deepcopy(snapshot) if isinstance(snapshot, dict) else {}


def _known_contracts() -> dict:
    registry = BusinessKnowledgeRegistry()
    frames = PerspectiveFrameRegistry()
    knowledge = {item.knowledge_id: item for item in registry.list()}
    metrics: dict[str, str] = {}
    rules: dict[str, str] = {}
    for item in knowledge.values():
        for metric in item.metrics + item.required_evidence + item.optional_evidence:
            metrics[metric] = item.knowledge_id
        for rule in item.relationship_rules:
            rules[rule.rule_id] = item.knowledge_id
    return {
        "knowledge": knowledge,
        "metrics": metrics,
        "rules": rules,
        "frames": set(frames.ids()),
        "registry_version": registry.version,
        "frame_registry_version": frames.version,
    }


def validate_registry_integrity(skill: Any | None = None) -> dict:
    contracts = _known_contracts()
    issues: list[dict] = []
    if skill:
        knowledge_ids = list(getattr(skill.knowledge_references, "primary", [])) + list(getattr(skill.knowledge_references, "secondary", []))
        metric_ids = list(getattr(skill.metric_references, "input", [])) + list(getattr(skill.metric_references, "derived", [])) + list(getattr(skill.metric_references, "context", []))
        rule_ids = list(getattr(skill, "relationship_rule_references", []))
        for knowledge_id in knowledge_ids:
            if knowledge_id not in contracts["knowledge"]:
                issues.append({"code": "UNKNOWN_KNOWLEDGE_REFERENCE", "severity": "ERROR", "contract_id": knowledge_id})
        for metric_id in metric_ids:
            canonical_metric = APPROVED_ALIASES.get(metric_id, metric_id)
            owner = contracts["metrics"].get(canonical_metric)
            if not owner:
                issues.append({"code": "UNKNOWN_METRIC_REFERENCE", "severity": "ERROR", "contract_id": metric_id})
            elif owner not in knowledge_ids:
                issues.append({"code": "CROSS_REGISTRY_OWNERSHIP_MISMATCH", "severity": "WARNING", "metric_id": metric_id, "owner_knowledge_id": owner})
        for rule_id in rule_ids:
            owner = contracts["rules"].get(rule_id)
            if not owner:
                issues.append({"code": "BROKEN_RELATIONSHIP_DEPENDENCY", "severity": "ERROR", "contract_id": rule_id})
            elif owner not in knowledge_ids:
                issues.append({"code": "BROKEN_RELATIONSHIP_DEPENDENCY", "severity": "ERROR", "contract_id": rule_id, "owner_knowledge_id": owner})
        for frame_id in getattr(skill, "supported_frames", []):
            if frame_id not in contracts["frames"]:
                issues.append({"code": "UNKNOWN_FRAME_REFERENCE", "severity": "ERROR", "contract_id": frame_id})
        for authority in getattr(getattr(skill, "authority_scope", None), "allowed", []):
            if authority in {"final_judgment", "final_decision", "planner_invocation", "workflow_execution", "business_memory_mutation"}:
                issues.append({"code": "UNKNOWN_AUTHORITY_REFERENCE", "severity": "ERROR", "contract_id": authority})
    return {
        "registry_integrity_checked": True,
        "registry_integrity_passed": not any(item.get("severity") in {"ERROR", "FATAL"} for item in issues),
        "issues": issues,
        "cross_registry_issues": [item for item in issues if item["code"].startswith("CROSS_") or item["code"].startswith("BROKEN") or item["code"].startswith("UNKNOWN_")],
        "checksum_deterministic": True,
        "version": CONTRACT_DRIFT_DETECTOR_VERSION,
    }


def inspect_body_metadata_consistency(skill: Any) -> list[dict]:
    body = str(getattr(skill, "content", "") or "")
    checks = [
        ("BODY_AUTHORITY_CONFLICT", ["Final Decision", "Best action", "Recommend borrowing"]),
        ("BODY_WORKFLOW_EXECUTION_CONFLICT", ["Execute", "Automatically reorder"]),
        ("BODY_DECISION_CONFLICT", ["Final Decision", "Best action"]),
        ("BODY_PLANNER_CONFLICT", ["Create plan"]),
        ("BODY_MEMORY_MUTATION_CONFLICT", ["Write to memory"]),
        ("BODY_CANONICAL_FORMULA_CONFLICT", ["final formula", "always calculate"]),
    ]
    diagnostics = []
    for code, phrases in checks:
        matched = [phrase for phrase in phrases if phrase.lower() in body.lower()]
        if matched:
            diagnostics.append({"code": code, "severity": "WARNING", "phrases": matched})
    return diagnostics


def _severity(types: set[str], body_diagnostics: list[dict], registry_ok: bool) -> str:
    if DriftType.AUTHORITY_POLICY_DRIFT.value in types:
        return DriftSeverity.CONSTITUTIONAL.value
    if not registry_ok or DriftType.METRIC_DEFINITION_DRIFT.value in types or DriftType.RELATIONSHIP_RULE_DRIFT.value in types or DriftType.EVIDENCE_REQUIREMENT_DRIFT.value in types or DriftType.FRAME_REGISTRY_DRIFT.value in types:
        return DriftSeverity.BREAKING.value
    if DriftType.SKILL_BODY_DRIFT.value in types or body_diagnostics:
        return DriftSeverity.REVIEW_REQUIRED.value
    if types:
        return DriftSeverity.NON_BREAKING.value
    return DriftSeverity.NONE.value


def _compatibility(severity: str) -> str:
    if severity == DriftSeverity.CONSTITUTIONAL.value:
        return CompatibilityStatus.UNSUPPORTED.value
    if severity == DriftSeverity.BREAKING.value:
        return CompatibilityStatus.MIGRATION_REQUIRED.value
    if severity == DriftSeverity.REVIEW_REQUIRED.value:
        return CompatibilityStatus.REVALIDATION_REQUIRED.value
    if severity in {DriftSeverity.NON_BREAKING.value, DriftSeverity.INFORMATIONAL.value}:
        return CompatibilityStatus.COMPATIBLE_WITH_WARNINGS.value
    return CompatibilityStatus.COMPATIBLE.value


def detect_contract_drift(skill: Any, previous_snapshot: SkillReferenceSnapshot | dict | None = None, *, renames: list[ContractRename | dict] | None = None, current_snapshot: SkillReferenceSnapshot | dict | None = None) -> ContractDriftResult:
    current = _snapshot_dict(current_snapshot) or build_skill_reference_snapshot(skill).to_dict()
    previous = _snapshot_dict(previous_snapshot) or deepcopy(current)
    types: set[str] = set()
    changed: list[dict] = []
    contracts = _known_contracts()
    integrity = validate_registry_integrity(skill)
    body_diagnostics = inspect_body_metadata_consistency(skill)
    for key, drift_type in (
        ("knowledge_versions", DriftType.KNOWLEDGE_DEFINITION_DRIFT.value),
        ("metric_versions", DriftType.METRIC_DEFINITION_DRIFT.value),
        ("relationship_rule_versions", DriftType.RELATIONSHIP_RULE_DRIFT.value),
    ):
        previous_values = as_dict(previous.get(key))
        current_values = as_dict(current.get(key))
        for contract_id in sorted(set(previous_values) | set(current_values)):
            if previous_values.get(contract_id) != current_values.get(contract_id):
                types.add(drift_type)
                changed.append({"contract_id": contract_id, "snapshot_field": key, "previous": previous_values.get(contract_id), "current": current_values.get(contract_id)})
    if previous.get("frame_registry_version") != current.get("frame_registry_version"):
        types.add(DriftType.FRAME_REGISTRY_DRIFT.value)
        changed.append({"contract_id": "frame_registry", "previous": previous.get("frame_registry_version"), "current": current.get("frame_registry_version")})
    if previous.get("authority_policy_version") != current.get("authority_policy_version"):
        types.add(DriftType.AUTHORITY_POLICY_DRIFT.value)
        changed.append({"contract_id": "skill_authority_policy", "previous": previous.get("authority_policy_version"), "current": current.get("authority_policy_version")})
    if previous.get("schema_version") != current.get("schema_version"):
        types.add(DriftType.SCHEMA_VERSION_DRIFT.value)
        changed.append({"contract_id": "canonical_skill_schema", "previous": previous.get("schema_version"), "current": current.get("schema_version")})
    if previous.get("skill_version") != current.get("skill_version"):
        types.add(DriftType.SKILL_METADATA_DRIFT.value)
        changed.append({"contract_id": getattr(skill, "skill_id", ""), "snapshot_field": "skill_version", "previous": previous.get("skill_version"), "current": current.get("skill_version")})
    if previous.get("source_checksum") and previous.get("source_checksum") != current.get("source_checksum"):
        types.add(DriftType.SKILL_BODY_DRIFT.value)
        changed.append({"contract_id": getattr(skill, "skill_id", ""), "snapshot_field": "source_checksum", "previous": previous.get("source_checksum"), "current": current.get("source_checksum")})
    for rename in renames or []:
        item = rename.to_dict() if hasattr(rename, "to_dict") else dict(rename)
        if not item.get("approved"):
            types.add(DriftType.KNOWLEDGE_DEFINITION_DRIFT.value)
            changed.append({"contract_id": item.get("old_id"), "rename_target": item.get("new_id"), "silent_rename_prevented": True})
    for metric_id in current.get("metric_versions", {}):
        if metric_id not in contracts["metrics"]:
            types.add(DriftType.METRIC_DEFINITION_DRIFT.value)
            changed.append({"contract_id": metric_id, "lifecycle": "REMOVED"})
    for rule_id in current.get("relationship_rule_versions", {}):
        if rule_id not in contracts["rules"]:
            types.add(DriftType.RELATIONSHIP_RULE_DRIFT.value)
            changed.append({"contract_id": rule_id, "lifecycle": "REMOVED"})
    for frame_id in getattr(skill, "supported_frames", []):
        if frame_id not in contracts["frames"]:
            types.add(DriftType.FRAME_REGISTRY_DRIFT.value)
            changed.append({"contract_id": frame_id, "lifecycle": "REMOVED"})
    severity = _severity(types, body_diagnostics, bool(integrity["registry_integrity_passed"]))
    effective_review = getattr(skill, "review_status", "")
    if severity in {DriftSeverity.REVIEW_REQUIRED.value, DriftSeverity.BREAKING.value}:
        effective_review = "needs_revision"
    if severity == DriftSeverity.CONSTITUTIONAL.value:
        effective_review = "rejected"
    result = ContractDriftResult(
        skill_id=str(getattr(skill, "skill_id", "")),
        drift_detected=bool(types or body_diagnostics or not integrity["registry_integrity_passed"]),
        drift_types=sorted(types),
        changed_contracts=changed,
        previous_snapshot=previous,
        current_snapshot=current,
        severity=severity,
        compatibility_status=_compatibility(severity),
        revalidation_required=severity in {DriftSeverity.REVIEW_REQUIRED.value, DriftSeverity.BREAKING.value, DriftSeverity.CONSTITUTIONAL.value},
        rereview_required=severity in {DriftSeverity.REVIEW_REQUIRED.value, DriftSeverity.BREAKING.value, DriftSeverity.CONSTITUTIONAL.value},
        migration_required=severity in {DriftSeverity.BREAKING.value, DriftSeverity.CONSTITUTIONAL.value},
        authority_restricted=severity in {DriftSeverity.BREAKING.value, DriftSeverity.CONSTITUTIONAL.value},
        ranking_penalty={DriftSeverity.NONE.value: 0.0, DriftSeverity.NON_BREAKING.value: 0.05, DriftSeverity.REVIEW_REQUIRED.value: 1.5, DriftSeverity.BREAKING.value: 99.0, DriftSeverity.CONSTITUTIONAL.value: 999.0}.get(severity, 0.1),
        blocking_reason="constitutional_authority_drift" if severity == DriftSeverity.CONSTITUTIONAL.value else "breaking_contract_drift" if severity == DriftSeverity.BREAKING.value else "",
        declared_review_status=str(getattr(skill, "review_status", "")),
        effective_review_status=effective_review,
        reference_freshness="UNSUPPORTED" if severity == DriftSeverity.CONSTITUTIONAL.value else "STALE_REFERENCE" if severity in {DriftSeverity.BREAKING.value, DriftSeverity.REVIEW_REQUIRED.value} else "CURRENT_WITH_WARNINGS" if severity == DriftSeverity.NON_BREAKING.value else "CURRENT",
        body_metadata_diagnostics=body_diagnostics,
        registry_integrity=integrity,
        change_manifest=build_contract_change_manifest(previous={"version": previous.get("validated_at_version"), "contracts": previous}, current={"version": current.get("validated_at_version"), "contracts": current}, renamed_contracts=renames),
    )
    return result


def build_contract_migration_queue(results: list[dict | ContractDriftResult]) -> dict:
    severity_order = {"CONSTITUTIONAL": 0, "BREAKING": 1, "REVIEW_REQUIRED": 2, "NON_BREAKING": 3, "INFORMATIONAL": 4, "NONE": 5}
    records: list[ContractMigrationRecord] = []
    for raw in results:
        result = raw.to_dict() if hasattr(raw, "to_dict") else dict(raw)
        if not result.get("drift_detected"):
            continue
        action = "UPDATE_AUTHORITY_SCOPE" if result.get("severity") == "CONSTITUTIONAL" else "UPDATE_REFERENCE" if result.get("migration_required") else "REREVIEW" if result.get("rereview_required") else "REVALIDATE"
        for changed in result.get("changed_contracts") or [{"contract_id": result.get("skill_id")}]:
            records.append(ContractMigrationRecord(
                contract_type=str(changed.get("snapshot_field") or changed.get("contract_type") or "SKILL"),
                source_id=str(changed.get("contract_id") or result.get("skill_id")),
                affected_skill_ids=[result.get("skill_id")],
                drift_type=(result.get("drift_types") or ["SKILL_METADATA_DRIFT"])[0],
                severity=result.get("severity") or "NONE",
                required_action=action,
                blocking_runtime_use=bool(result.get("authority_restricted")),
            ))
    ordered = sorted(records, key=lambda item: (severity_order.get(item.severity, 9), item.source_id, item.affected_skill_ids))
    payloads = [item.to_dict() for item in ordered]
    return ContractMigrationQueue(
        records=payloads,
        critical_count=len([item for item in payloads if item["severity"] == "CONSTITUTIONAL"]),
        high_count=len([item for item in payloads if item["severity"] == "BREAKING"]),
        medium_count=len([item for item in payloads if item["severity"] == "REVIEW_REQUIRED"]),
        low_count=len([item for item in payloads if item["severity"] in {"NON_BREAKING", "INFORMATIONAL"}]),
        next_item=payloads[0] if payloads else {},
    ).to_dict()
