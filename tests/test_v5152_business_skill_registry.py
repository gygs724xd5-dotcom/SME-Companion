import dataclasses
import unittest

import brain.business_skill_registry as registry_module
from brain.business_skill import (
    CALCULATION,
    CONTRACTED,
    COST,
    LIMITED_ACTIVE,
    PRICING,
    STABLE,
    SHADOW_AVAILABLE,
    UNIT_TESTED,
    BusinessSkill,
    validate_business_skill,
)
from brain.business_skill_registry import (
    BUSINESS_SKILL_REGISTRY_VERSION,
    EXPECTED_SEED_SKILL_IDS,
    build_seed_business_skills,
    get_business_skill,
    get_business_skill_registry,
    list_business_skills,
    validate_business_skill_registry,
)


class V5152BusinessSkillRegistryTest(unittest.TestCase):
    def test_registry_contains_exact_seed_ids_in_order(self):
        skills = get_business_skill_registry()

        self.assertEqual(len(skills), 10)
        self.assertEqual(tuple(skill.skill_id for skill in skills), EXPECTED_SEED_SKILL_IDS)

    def test_all_ids_are_unique(self):
        skill_ids = [skill.skill_id for skill in get_business_skill_registry()]

        self.assertEqual(len(skill_ids), len(set(skill_ids)))

    def test_every_seed_uses_business_skill_contract_and_validates(self):
        for skill in get_business_skill_registry():
            self.assertIsInstance(skill, BusinessSkill)
            result = validate_business_skill(skill)
            self.assertTrue(result["valid"], result["errors"])

    def test_current_registry_has_two_shadow_available_promotions(self):
        skills = get_business_skill_registry()
        statuses = {skill.active_status for skill in skills}

        self.assertEqual({skill.skill_id for skill in skills if skill.active_status == SHADOW_AVAILABLE}, {
            "cost.change_analysis.v1", "cost.per_unit_calculation.v1",
        })
        self.assertEqual(sum(skill.active_status == CONTRACTED for skill in skills), 8)
        self.assertNotIn(LIMITED_ACTIVE, statuses)
        self.assertNotIn(STABLE, statuses)

    def test_exact_lookup_returns_correct_skill(self):
        skill = get_business_skill("pricing.basic_price_suggestion.v1")

        self.assertIsNotNone(skill)
        self.assertEqual(skill.skill_id, "pricing.basic_price_suggestion.v1")

    def test_unknown_lookup_returns_none(self):
        self.assertIsNone(get_business_skill("pricing.unknown.v1"))

    def test_domain_filter_works(self):
        skills = list_business_skills(business_domain=COST)

        self.assertEqual([skill.skill_id for skill in skills], [
            "cost.change_analysis.v1",
            "cost.per_unit_calculation.v1",
        ])

    def test_category_filter_works(self):
        skills = list_business_skills(skill_category=CALCULATION)

        self.assertEqual([skill.skill_id for skill in skills], [
            "cost.change_analysis.v1",
            "cost.per_unit_calculation.v1",
            "pricing.promotion_margin_check.v1",
        ])

    def test_lifecycle_status_filter_works(self):
        skills = list_business_skills(active_status=CONTRACTED)

        self.assertEqual(len(skills), 8)
        self.assertEqual(tuple(skill.skill_id for skill in skills), EXPECTED_SEED_SKILL_IDS[2:])

    def test_combined_filters_work(self):
        skills = list_business_skills(
            business_domain=PRICING,
            skill_category=CALCULATION,
            active_status=CONTRACTED,
        )

        self.assertEqual([skill.skill_id for skill in skills], ["pricing.promotion_margin_check.v1"])

    def test_returned_registry_data_cannot_mutate_future_reads(self):
        first_read = list(get_business_skill_registry())
        first_read.pop()

        second_read = get_business_skill_registry()

        self.assertEqual(len(second_read), 10)
        self.assertEqual(tuple(skill.skill_id for skill in second_read), EXPECTED_SEED_SKILL_IDS)
        self.assertIsNot(first_read[0], second_read[0])

    def test_validation_report_is_deterministic(self):
        first = validate_business_skill_registry()
        second = validate_business_skill_registry()

        self.assertEqual(first, second)
        self.assertTrue(first["valid"])
        self.assertEqual(first["total_skills"], 10)
        self.assertEqual(tuple(first["skill_ids"]), EXPECTED_SEED_SKILL_IDS)
        self.assertEqual(first["duplicate_skill_ids"], [])
        self.assertEqual(first["invalid_skill_ids"], [])
        self.assertEqual(first["status_counts"], {SHADOW_AVAILABLE: 2, CONTRACTED: 8})

    def test_duplicate_detection_works_with_injected_registry(self):
        skills = list(build_seed_business_skills())
        report = validate_business_skill_registry([*skills, skills[0]])

        self.assertFalse(report["valid"])
        self.assertEqual(report["duplicate_skill_ids"], ["cost.change_analysis.v1"])
        self.assertIn("duplicate skill_id: cost.change_analysis.v1", report["errors"])

    def test_invalid_skill_detection_works(self):
        invalid = dataclasses.replace(build_seed_business_skills()[0], business_domain="UNKNOWN")

        report = validate_business_skill_registry([invalid])

        self.assertFalse(report["valid"])
        self.assertEqual(report["invalid_skill_ids"], ["cost.change_analysis.v1"])
        self.assertIn("cost.change_analysis.v1: business_domain must be canonical", report["errors"])

    def test_registry_module_does_not_import_runtime_layers(self):
        forbidden = (
            "streamlit",
            "app",
            "planner",
            "router",
            "workflow",
            "response",
            "llm",
        )

        for name in forbidden:
            self.assertNotIn(name, registry_module.__dict__)

    def test_registry_version_reflects_lifecycle_promotion(self):
        self.assertEqual(BUSINESS_SKILL_REGISTRY_VERSION, "5.15.9")


if __name__ == "__main__":
    unittest.main()
