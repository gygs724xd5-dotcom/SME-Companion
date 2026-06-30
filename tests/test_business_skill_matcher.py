import unittest

from brain.business_skill_matcher import rank_business_skills


def skill(
    skill_id,
    *,
    name="",
    domain="01 Sales",
    stage="Interest",
    goal="Close Sale",
    situation="",
    intent="",
    examples="",
    memory_tags="",
):
    return {
        "skill_id": skill_id,
        "skill_name": name or skill_id,
        "business_domain": domain,
        "conversation_stage": stage,
        "business_goal": goal,
        "situation": situation,
        "intent": intent,
        "example_questions": examples,
        "memory_tags": memory_tags,
    }


class BusinessSkillMatcherTest(unittest.TestCase):
    def test_exact_keyword_ranks_price_skill_first(self):
        candidates = [
            skill(
                "01.004.close_sale",
                name="Close sale",
                stage="Purchase",
                situation="Customer is ready to order.",
                examples="order now",
            ),
            skill(
                "01.001.customer_asks_price",
                name="Customer asks price",
                situation="A customer asks how much a product costs.",
                examples="\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
            ),
        ]

        ranked = rank_business_skills("\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23", {}, candidates)

        self.assertEqual(ranked[0]["skill_id"], "01.001.customer_asks_price")
        self.assertGreaterEqual(ranked[0]["confidence"], 0.97)
        self.assertIn("\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23", ranked[0]["matched_aliases"])

    def test_alias_ranks_expensive_objection_first(self):
        candidates = [
            skill("01.001.customer_asks_price", name="Customer asks price"),
            skill(
                "01.002.customer_says_expensive",
                name="Customer says expensive",
                stage="Consideration",
                situation="Customer objects to price.",
                examples="\u0e41\u0e1e\u0e07\u0e08\u0e31\u0e07",
            ),
            skill("02.002.create_promotion", name="Create promotion", domain="02 Marketing"),
        ]

        ranked = rank_business_skills("\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e1a\u0e2d\u0e01\u0e27\u0e48\u0e32\u0e41\u0e1e\u0e07", {}, candidates)

        self.assertEqual(ranked[0]["skill_id"], "01.002.customer_says_expensive")
        self.assertGreaterEqual(ranked[0]["confidence"], 0.97)
        self.assertIn("\u0e41\u0e1e\u0e07", ranked[0]["matched_aliases"])

    def test_business_context_improves_relevant_skill(self):
        candidates = [
            skill(
                "02.002.create_promotion",
                name="Create promotion",
                domain="02 Marketing",
                stage="Consideration",
                memory_tags="promotion_style\ncustomer_segment",
            ),
            skill(
                "01.002.customer_says_expensive",
                name="Customer says expensive",
                domain="01 Sales",
                stage="Consideration",
                memory_tags="pricing_strategy\nmargin_sensitivity",
            ),
        ]
        context = {
            "business_context": {
                "business_domain": "01 Sales",
                "business_stage": "Consideration",
                "memory_tags": ["pricing_strategy"],
            }
        }

        ranked = rank_business_skills("\u0e0a\u0e48\u0e27\u0e22\u0e41\u0e19\u0e30\u0e19\u0e33\u0e2b\u0e19\u0e48\u0e2d\u0e22", context, candidates)

        self.assertEqual(ranked[0]["skill_id"], "01.002.customer_says_expensive")
        self.assertGreater(ranked[0]["components"]["business_domain"], 0)
        self.assertGreater(ranked[0]["components"]["memory_tag"], 0)

    def test_tie_breaking_uses_skill_id(self):
        candidates = [
            skill("02.002.same_match", name="Same", examples="same phrase"),
            skill("01.001.same_match", name="Same", examples="same phrase"),
        ]

        ranked = rank_business_skills("same phrase", {}, candidates)

        self.assertEqual([item["skill_id"] for item in ranked], ["01.001.same_match", "02.002.same_match"])

    def test_unknown_message_returns_no_ranked_skills_without_context(self):
        candidates = [
            skill("01.001.customer_asks_price", name="Customer asks price"),
            skill("01.002.customer_says_expensive", name="Customer says expensive"),
        ]

        ranked = rank_business_skills("xyzzy unrelated sentence", {}, candidates)

        self.assertEqual(ranked, [])

    def test_fallback_can_rank_broad_startup_candidates(self):
        candidates = [
            skill(
                "startup_business",
                name="Startup business",
                domain="00 Strategy",
                stage="Awareness",
                situation="Owner wants to open a new shop.",
                intent="Start a business and choose the first selling plan.",
            ),
            skill(
                "sales_planning",
                name="Sales planning",
                domain="01 Sales",
                stage="Interest",
                situation="Owner needs a plan for selling.",
            ),
            skill(
                "marketing",
                name="Marketing",
                domain="02 Marketing",
                stage="Awareness",
                situation="Owner needs marketing guidance.",
            ),
        ]

        ranked = rank_business_skills("\u0e2d\u0e22\u0e32\u0e01\u0e40\u0e1b\u0e34\u0e14\u0e23\u0e49\u0e32\u0e19\u0e02\u0e32\u0e22\u0e02\u0e19\u0e21", {}, candidates)

        self.assertEqual(ranked[0]["skill_id"], "startup_business")
        self.assertGreaterEqual(ranked[0]["confidence"], 0.97)


if __name__ == "__main__":
    unittest.main()
