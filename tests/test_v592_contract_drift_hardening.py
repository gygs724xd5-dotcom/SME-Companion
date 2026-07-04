import unittest

from brain.canonical_skill_registry import CanonicalSkillRegistry
from brain.contract_drift_detector import build_contract_migration_queue, detect_contract_drift
from brain.contract_provenance import ContractRename, build_skill_reference_snapshot, deterministic_checksum
from brain.knowledge_skill_bridge import build_knowledge_skill_bridge
from brain.knowledge_runtime import build_knowledge_runtime


class V592ContractDriftHardeningTest(unittest.TestCase):
    def setUp(self):
        self.registry = CanonicalSkillRegistry()
        self.skill = self.registry.get_skill("analyze_operating_capacity")
        self.snapshot = build_skill_reference_snapshot(self.skill).to_dict()

    def test_matching_snapshot_has_no_drift(self):
        result = detect_contract_drift(self.skill, self.snapshot)
        self.assertFalse(result.drift_detected)
        self.assertEqual(result.severity, "NONE")
        self.assertEqual(result.compatibility_status, "COMPATIBLE")

    def test_required_metric_change_is_breaking_and_blocks_primary(self):
        previous = dict(self.snapshot)
        previous["metric_versions"] = {}
        result = detect_contract_drift(self.skill, previous)
        self.assertTrue(result.drift_detected)
        self.assertIn("METRIC_DEFINITION_DRIFT", result.drift_types)
        self.assertEqual(result.severity, "BREAKING")
        self.assertTrue(result.migration_required)

    def test_authority_policy_change_is_constitutional(self):
        previous = dict(self.snapshot)
        previous["authority_policy_version"] = "5.9.1"
        result = detect_contract_drift(self.skill, previous)
        self.assertEqual(result.severity, "CONSTITUTIONAL")
        self.assertTrue(result.authority_restricted)

    def test_body_checksum_change_requires_review_not_source_mutation(self):
        previous = dict(self.snapshot)
        previous["source_checksum"] = "old"
        result = detect_contract_drift(self.skill, previous)
        self.assertEqual(result.severity, "REVIEW_REQUIRED")
        self.assertEqual(result.effective_review_status, "needs_revision")
        self.assertEqual(self.registry.get_skill("analyze_operating_capacity").review_status, "approved")

    def test_silent_rename_rejected_and_migration_record_created(self):
        rename = ContractRename("old_metric", "unit_cost", "METRIC", "5.9.2", approved=False)
        result = detect_contract_drift(self.skill, self.snapshot, renames=[rename]).to_dict()
        queue = build_contract_migration_queue([result])
        self.assertTrue(result["drift_detected"])
        self.assertTrue(result["change_manifest"]["breaking_changes"])
        self.assertTrue(queue["records"])

    def test_registry_checksum_is_deterministic(self):
        self.assertEqual(deterministic_checksum({"b": 2, "a": 1}), deterministic_checksum({"a": 1, "b": 2}))

    def test_bridge_exposes_drift_invariants_without_execution(self):
        knowledge = build_knowledge_runtime(user_message="ตอนนี้ทำได้ 100 ชิ้น", business_situation={"known_evidence": [{"summary": "ขายชูครีม ทำตามออเดอร์"}]}, perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"})
        bridge = build_knowledge_skill_bridge({"knowledge_runtime_result": knowledge, "business_context": {"business_model": "made_to_order"}, "current_message": "ตอนนี้ทำได้ 100 ชิ้น"})
        self.assertTrue(bridge["contract_provenance"]["contract_provenance_checked"])
        self.assertTrue(bridge["contract_drift"]["contract_drift_checked"])
        self.assertFalse(bridge["constitutional_invariants"]["skill_executed"])
        self.assertFalse(bridge["constitutional_invariants"]["business_memory_mutated"])


if __name__ == "__main__":
    unittest.main()
