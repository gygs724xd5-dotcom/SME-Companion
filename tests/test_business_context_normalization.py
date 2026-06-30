import unittest
import json

from brain.business_context_engine import build_business_context, sanitize_user_context_text
from llm.prompt_context_builder import build_prompt_context


CHOUX_CREAM = "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21"
BAKERY = "\u0e40\u0e1a\u0e40\u0e01\u0e2d\u0e23\u0e35\u0e48"


class BusinessContextNormalizationTest(unittest.TestCase):
    def test_choux_cream_does_not_become_cosmetic_store(self):
        context = build_business_context({}, CHOUX_CREAM)

        self.assertEqual(context.get("current_product"), CHOUX_CREAM)
        self.assertNotEqual(context.get("business_type"), "cosmetic_store")
        self.assertEqual(context.get("source"), "current_message")

    def test_bakery_overrides_old_cosmetic_store(self):
        state = {
            "business_context": {
                "business_type": "cosmetic_store",
                "current_product": "cream",
                "current_discussion_topic": "cosmetic_store",
            }
        }

        context = build_business_context(state, f"{CHOUX_CREAM} / {BAKERY}")

        self.assertEqual(context.get("business_type"), "bakery")
        self.assertEqual(context.get("current_product"), CHOUX_CREAM)
        self.assertEqual(context.get("source"), "current_message")
        self.assertFalse(context.get("is_stale"))
        self.assertIn(
            {"field": "business_type", "source": "conversation_memory", "value": "cosmetic_store"},
            context.get("conflicts"),
        )

    def test_choux_cream_price_question_preserves_product(self):
        state = {"business_context": {"current_product": "cream", "current_discussion_topic": "old pricing"}}

        context = build_business_context(state, f"{CHOUX_CREAM}\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23")

        self.assertEqual(context.get("current_product"), CHOUX_CREAM)
        self.assertEqual(context.get("current_discussion_topic"), "pricing")
        self.assertNotEqual(context.get("current_discussion_topic"), "old pricing")

    def test_old_business_memory_does_not_override_current_message(self):
        state = {
            "business_memory": {
                "events": [
                    {"payload": {"business_type": "cosmetic_store", "current_product": "cream"}},
                ]
            }
        }

        context = build_business_context(state, BAKERY)

        self.assertEqual(context.get("business_type"), "bakery")
        self.assertEqual(context.get("source"), "current_message")
        self.assertIn(
            {"field": "business_type", "source": "business_memory", "value": "cosmetic_store"},
            context.get("conflicts"),
        )

    def test_context_priority_order_uses_workflow_before_store_profile_and_memory(self):
        state = {
            "workflow": {
                "workflow_state_v2": {
                    "workflow": "CONTENT_PLAN",
                    "step": "collecting_content_inputs",
                    "collected_fields": {"product": CHOUX_CREAM, "business_type": "bakery"},
                }
            },
            "store": {"store_type": "cosmetic_store", "product": "cream"},
            "business_context": {"business_type": "fashion_shop", "current_product": "shirt"},
            "business_memory": {"events": [{"payload": {"business_type": "tea_shop", "current_product": "tea"}}]},
        }

        context = build_business_context(state, "\u0e04\u0e23\u0e35\u0e21")

        self.assertEqual(context.get("business_type"), "bakery")
        self.assertEqual(context.get("current_product"), CHOUX_CREAM)
        self.assertEqual(context.get("source"), "workflow")

    def test_internal_labels_are_sanitized(self):
        text = sanitize_user_context_text("pricing_unclear cosmetic_store customer_says_expensive workflow_response")

        self.assertEqual(text, "")

    def test_prompt_context_omits_raw_conflicting_memory_by_default(self):
        context = build_business_context(
            {"business_context": {"business_type": "cosmetic_store", "current_product": "cream"}},
            BAKERY,
        )
        prompt_context = build_prompt_context(
            {"business_memory": {"events": [{"payload": {"business_type": "cosmetic_store"}}]}},
            planner={"goal": BAKERY, "task_type": "General Business Help"},
            business_context=context,
            business_memory={"events": [{"payload": {"business_type": "cosmetic_store"}}]},
        )

        self.assertNotIn("business_memory", prompt_context)
        self.assertNotIn("cosmetic_store", str(prompt_context))
        self.assertIn("prompt_context_size", prompt_context)

    def test_prompt_context_is_smaller_than_previous_large_context_shape(self):
        history = [
            {"role": "user", "content": "ช่วยคิดโพสต์ขายชูครีม " * 40},
            {"role": "assistant", "content": "ได้ครับ " * 80},
        ] * 5
        loaded_skills = [
            {"name": "content_creation", "available": True, "path": "skills/content.md", "content": "long skill " * 300},
            {"name": "sales_plan", "available": True, "path": "skills/sales.md", "content": "other skill " * 300},
        ]
        previous_large_context = {
            "conversation_summary": {"recent_messages": history[-6:], "memory": {"raw": "memory " * 400}},
            "loaded_skill": loaded_skills,
            "future_context_sources": {"business_memory": None, "inventory_agent": None},
        }

        prompt_context = build_prompt_context(
            {"conversation": {"chat_history": history}},
            planner={"goal": "ช่วยคิดโพสต์ขายชูครีม", "task_type": "Content Plan"},
            loaded_skill=loaded_skills,
            reasoning={"matched_skill": {"skill_id": "content_creation"}},
            prompt_budget_chars=20000,
        )

        self.assertLess(
            prompt_context["prompt_context_size"],
            len(json.dumps(previous_large_context, ensure_ascii=False, default=str)),
        )

    def test_prompt_context_removes_duplicate_recent_messages(self):
        duplicate = {"role": "user", "content": "ช่วยคิดโพสต์ขายชูครีม"}
        prompt_context = build_prompt_context(
            {"conversation": {"chat_history": [duplicate, duplicate, duplicate]}},
            planner={"goal": "ช่วยคิดโพสต์ขายชูครีม", "task_type": "Content Plan"},
        )

        recent = prompt_context["conversation_summary"]["recent_messages"]
        self.assertEqual(len(recent), 1)

    def test_prompt_context_diagnostics_are_developer_only(self):
        normal_context = build_prompt_context(
            {},
            planner={"goal": BAKERY, "task_type": "General Business Help"},
            business_context={"source": "current_message", "confidence": 0.95},
            developer_mode=False,
        )
        developer_context = build_prompt_context(
            {},
            planner={"goal": BAKERY, "task_type": "General Business Help"},
            business_context={"source": "current_message", "confidence": 0.95},
            developer_mode=True,
        )

        self.assertNotIn("diagnostics", normal_context)
        self.assertIn("diagnostics", developer_context)
        diagnostics = developer_context["diagnostics"]
        for field in [
            "prompt_context_size",
            "selected_business_skill",
            "selected_business_domain",
            "matched_intents",
            "context_source",
            "context_confidence",
            "context_conflicts",
            "stale_context_detected",
            "included_context_sections",
            "omitted_context_sections",
        ]:
            self.assertIn(field, diagnostics)

    def test_selected_skill_and_domain_diagnostics_are_recorded(self):
        developer_context = build_prompt_context(
            {},
            planner={
                "goal": "ลูกค้าบอกว่าแพง",
                "task_type": "Business Consulting",
                "business_intelligence": {
                    "matched_skill": {
                        "skill_id": "01.002.customer_says_expensive",
                        "business_domain": "01 Sales",
                    },
                    "matched_domain": "01 Sales",
                },
            },
            reasoning={"action": "business_reasoning"},
            developer_mode=True,
        )

        diagnostics = developer_context["diagnostics"]
        self.assertEqual(diagnostics["selected_business_skill"], "01.002.customer_says_expensive")
        self.assertEqual(diagnostics["selected_business_domain"], "01 Sales")

    def test_diagnostics_are_not_exposed_in_normal_prompt_context(self):
        prompt_context = build_prompt_context(
            {},
            planner={"goal": "ลูกค้าบอกว่าแพง", "task_type": "Business Consulting"},
            reasoning={"matched_skill": {"skill_id": "01.002.customer_says_expensive"}},
            business_context={"source": "current_message", "confidence": 0.95, "conflicts": [{"field": "business_type"}]},
            developer_mode=False,
        )

        self.assertNotIn("diagnostics", prompt_context)
        self.assertNotIn("included_context_sections", prompt_context)
        self.assertNotIn("omitted_context_sections", prompt_context)


if __name__ == "__main__":
    unittest.main()
