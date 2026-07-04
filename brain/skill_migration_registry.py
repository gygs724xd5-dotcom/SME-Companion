from __future__ import annotations

from pathlib import Path

from brain.canonical_skill_migration import PHASE_1_BATCH_ID, build_migration_record, decide_legacy_skill_migration, migration_coverage
from brain.skill_migration_assessment import assess_legacy_skill


SKILL_MIGRATION_REGISTRY_VERSION = "5.9.3"
DEFAULT_LEGACY_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

PHASE_1_SKILLS = [
    "cost_calculation",
    "sales_planning",
    "dashboard_builder",
    "marketing",
    "content_creation",
    "receipt_capture",
    "developer_feedback",
]


ROLLOUT_MODES = {
    "cost_calculation": "CANONICAL_PREFERRED",
    "sales_planning": "SHADOW_CANONICAL",
    "dashboard_builder": "SHADOW_CANONICAL",
    "marketing": "DIAGNOSTIC_ONLY",
    "content_creation": "DIAGNOSTIC_ONLY",
    "receipt_capture": "DIAGNOSTIC_ONLY",
    "developer_feedback": "LEGACY_UNCHANGED",
}


def rollout_mode_for_legacy_skill(legacy_skill_id: str) -> str:
    return ROLLOUT_MODES.get(str(legacy_skill_id or ""), "DIAGNOSTIC_ONLY")


def canonical_preferred_for_skill(skill_id: str) -> bool:
    return str(skill_id or "") in {"calculate_product_margin", "analyze_sales_decline", "evaluate_sales_funnel", "identify_dashboard_metrics"}


def load_skill_migration_registry(skills_dir: str | Path | None = None) -> dict:
    base = Path(skills_dir) if skills_dir else DEFAULT_LEGACY_SKILLS_DIR
    assessments = []
    decisions = []
    records = []
    coverage = []
    for legacy_id in PHASE_1_SKILLS:
        path = base / f"{legacy_id}.md"
        assessments.append(assess_legacy_skill(path))
        decision = decide_legacy_skill_migration(path)
        decisions.append(decision)
        coverage.append(migration_coverage(path))
        for target in decision.get("target_skill_ids") or []:
            if not target.startswith("future_"):
                records.append(build_migration_record(path, target))
    return {
        "canonical_skill_migration_consulted": True,
        "migration_batch_id": PHASE_1_BATCH_ID,
        "assessments": assessments,
        "decisions": decisions,
        "records": records,
        "coverage": coverage,
        "rollout_modes": dict(ROLLOUT_MODES),
        "legacy_deprecation_blocked": True,
        "version": SKILL_MIGRATION_REGISTRY_VERSION,
    }
