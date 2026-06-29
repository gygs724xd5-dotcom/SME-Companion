import unittest

from brain.business_reasoning_engine import (
    extract_business_principle,
    extract_decision_tree,
    extract_memory_tags,
    extract_questions,
    reason_business_message,
)
from brain.business_skill_loader import get_business_skill


class BusinessReasoningEngineTest(unittest.TestCase):
    def test_no_skill(self):
        result = reason_business_message("hello", None)

        self.assertEqual(
            result,
            {
                "skill_found": False,
                "reasoning_summary": "No matching business skill.",
            },
        )

    def test_customer_asks_price(self):
        skill = get_business_skill("customer_asks_price")

        result = reason_business_message("price?", skill)

        self.assertTrue(result["skill_found"])
        self.assertEqual(result["skill_id"], "01.001.customer_asks_price")
        self.assertEqual(result["skill_name"], "Customer asks price.")
        self.assertGreaterEqual(result["confidence"], 0.8)
        self.assertIn("price", result["business_principle"].lower())
        self.assertIn("Customer asks price", result["decision_tree"][0])
        self.assertIn("pricing_strategy", result["memory_tags"])
        self.assertEqual(result["response_mode"], "NORMAL_CHAT")
        self.assertIn("CRM", result["workflow"])

    def test_customer_says_expensive(self):
        skill = get_business_skill("customer_says_expensive")

        result = reason_business_message("too expensive", skill)

        self.assertEqual(result["skill_id"], "01.002.customer_says_expensive")
        self.assertIn("objection", result["business_principle"].lower())
        self.assertTrue(
            any("discount" in item.lower() for item in result["things_to_avoid"])
        )
        self.assertTrue(
            any("budget" in item.lower() for item in result["reasoning_steps"])
        )

    def test_refund_request(self):
        skill = get_business_skill("refund_request")

        result = reason_business_message("refund please", skill)

        self.assertEqual(result["skill_id"], "03.003.refund_request")
        self.assertEqual(result["response_mode"], "CLARIFICATION")
        self.assertIn("refund", result["business_principle"].lower())
        self.assertTrue(any("policy" in item.lower() for item in result["decision_tree"]))
        self.assertIn("refund_policy", result["memory_tags"])

    def test_shipping_question(self):
        skill = get_business_skill("shipping_question")

        result = reason_business_message("do you ship?", skill)

        self.assertEqual(result["skill_id"], "03.001.shipping_question")
        self.assertEqual(result["response_mode"], "ASK_NEXT_FIELD")
        self.assertIn("Delivery", result["business_principle"])
        self.assertTrue(any("area" in item.lower() for item in result["questions_to_ask"]))
        self.assertIn("delivery_area", result["memory_tags"])

    def test_memory_tags_parsed_from_heading_style_skill(self):
        skill = {
            "Skill ID": "test.skill",
            "Skill Name": "Test skill",
            "Memory Tags": "- first_tag\n- second_tag\n- third_tag",
        }

        self.assertEqual(
            extract_memory_tags(skill),
            ["first_tag", "second_tag", "third_tag"],
        )

    def test_response_mode_parsed_from_heading_style_skill(self):
        skill = {
            "Skill ID": "test.skill",
            "Skill Name": "Test skill",
            "Response Mode": "ASK_NEXT_FIELD",
        }

        result = reason_business_message("question", skill)

        self.assertEqual(result["response_mode"], "ASK_NEXT_FIELD")

    def test_workflow_parsed_from_heading_style_skill(self):
        skill = {
            "Skill ID": "test.skill",
            "Skill Name": "Test skill",
            "Workflow Integration": "- CRM: save customer data",
        }

        result = reason_business_message("question", skill)

        self.assertIn("CRM", result["workflow"])

    def test_helper_extractors(self):
        skill = get_business_skill("customer_asks_price")

        self.assertTrue(extract_business_principle(skill))
        self.assertGreater(len(extract_decision_tree(skill)), 1)
        self.assertGreater(len(extract_questions(skill)), 0)


if __name__ == "__main__":
    unittest.main()
