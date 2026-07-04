import unittest

from brain.legacy_skill_compatibility import create_migration_record, evaluate_legacy_skill_compatibility


class V591LegacySkillCompatibilityTest(unittest.TestCase):
    def test_structured_legacy_is_advisory_not_primary(self):
        result = evaluate_legacy_skill_compatibility({"skill_id": "cost_calculation", "content": "# Intent\ncost\n# Required Data\nprice cost"})
        self.assertEqual(result.classification, "LEGACY_STRUCTURED")
        self.assertEqual(result.compatibility_authority, "ADVISORY")
        self.assertFalse(result.primary_eligible)
        self.assertTrue(result.secondary_eligible)
        self.assertTrue(result.warnings)

    def test_low_confidence_legacy_is_diagnostic_only_and_migration_record_created(self):
        result = evaluate_legacy_skill_compatibility({"source_path": "legacy.md", "content": "unstructured note"})
        record = create_migration_record(result)
        self.assertEqual(result.classification, "LEGACY_UNSTRUCTURED")
        self.assertTrue(result.diagnostic_only)
        self.assertEqual(record.migration_status, "DISCOVERED")


if __name__ == "__main__":
    unittest.main()
