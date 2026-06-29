import tempfile
import unittest
from pathlib import Path

from brain.business_skill_loader import (
    PUBLIC_FIELDS,
    get_business_skill,
    load_all_business_skills,
    load_business_skill,
    search_business_skills,
)


class BusinessSkillLoaderTest(unittest.TestCase):
    def test_loader_parses_all_business_skills(self):
        skills = load_all_business_skills()

        self.assertEqual(len(skills), 10)
        self.assertTrue(all(skill["available"] for skill in skills))
        self.assertTrue(all(skill["valid"] for skill in skills))

    def test_required_headings_exist(self):
        for skill in load_all_business_skills():
            with self.subTest(skill_id=skill["skill_id"]):
                for field in PUBLIC_FIELDS:
                    self.assertIn(field, skill)
                    self.assertTrue(skill[field], f"{field} should be populated")
                self.assertIn("conversation_stage", skill)
                self.assertIn("business_goal", skill)

    def test_search_works_for_thai_queries(self):
        examples = {
            "ราคาเท่าไร": "customer_asks_price",
            "แพง": "customer_says_expensive",
            "ลูกค้าหาย": "customer_disappears",
            "ค่าส่ง": "shipping_question",
            "คืนเงิน": "refund_request",
        }

        for query, expected_slug in examples.items():
            with self.subTest(query=query):
                results = search_business_skills(query)
                self.assertGreater(len(results), 0)
                self.assertTrue(results[0]["skill_id"].endswith(expected_slug))

    def test_get_business_skill_by_id_and_slug(self):
        by_id = get_business_skill("01.001.customer_asks_price")
        by_slug = get_business_skill("customer_asks_price")

        self.assertIsNotNone(by_id)
        self.assertIsNotNone(by_slug)
        self.assertEqual(by_id["skill_id"], "01.001.customer_asks_price")
        self.assertEqual(by_slug["skill_id"], "01.001.customer_asks_price")

    def test_invalid_file_returns_warning_not_crash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "invalid.md"
            invalid_path.write_text("This is not a valid business skill.", encoding="utf-8")

            skill = load_business_skill(invalid_path)

        self.assertTrue(skill["available"])
        self.assertFalse(skill["valid"])
        self.assertGreater(len(skill["warnings"]), 0)
        self.assertEqual(skill["skill_id"], "invalid")


if __name__ == "__main__":
    unittest.main()
