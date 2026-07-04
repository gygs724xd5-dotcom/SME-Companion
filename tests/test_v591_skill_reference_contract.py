import unittest

from brain.canonical_skill_registry import CanonicalSkillRegistry
from brain.knowledge_skill_reference import KnowledgeSkillReference, KnowledgeReferences, MetricReferences


class V591SkillReferenceContractTest(unittest.TestCase):
    def test_reference_id_is_not_file_path(self):
        ref = KnowledgeSkillReference(
            reference_id="knowledge_skill_ref::analyze_operating_capacity::v1",
            skill_id="analyze_operating_capacity",
            skill_version="1.0.0",
            schema_version="5.9.1",
            knowledge_ids=KnowledgeReferences(primary=["OPERATING_CAPACITY"]),
            metric_ids=MetricReferences(input=["output_quantity"]),
        )
        self.assertEqual(ref.reference_id, "knowledge_skill_ref::analyze_operating_capacity::v1")
        self.assertNotIn("\\", ref.reference_id)

    def test_registry_indexes_are_deterministic(self):
        registry = CanonicalSkillRegistry()
        self.assertIn("analyze_operating_capacity", [skill.skill_id for skill in registry.find_skills_by_knowledge("OPERATING_CAPACITY")])
        self.assertIn("analyze_profit_compression", [skill.skill_id for skill in registry.find_skills_by_frame("PROFIT_COMPRESSION")])
        self.assertEqual([skill.skill_id for skill in registry.list_skills()], sorted(skill.skill_id for skill in registry.list_skills()))


if __name__ == "__main__":
    unittest.main()
