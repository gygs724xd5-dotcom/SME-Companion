import unittest

from brain.business_knowledge_runtime import create_knowledge_context
from brain.business_reasoning_runtime import (
    REASONING_RUNTIME_SOURCE,
    REASONING_RUNTIME_VERSION,
    build_reasoning_context,
    create_reasoning_context,
)
from brain.business_skill_registry import BusinessSkill, SkillRegistry
from brain.canonical_objects import ReasoningContext
from brain.task_router import build_task_route, developer_diagnostics


def registry_skill(skill_id="01.001.customer_asks_price", *, intent="Handle customer price question"):
    return BusinessSkill(
        skill_id=skill_id,
        skill_name="Customer asks price",
        domain_id="01",
        domain_name="Sales",
        intent=intent,
        description="A customer asks how much a product costs.",
        workflow_id="sales_reply",
        required_entities=["product", "price"],
        required_memory=["pricing_strategy"],
        business_rules=["Price first when known."],
        reasoning="Answer clearly and protect perceived value.",
        response_style="NORMAL_CHAT",
        confidence="High when product is clear.",
        status="test",
        version="test",
        metadata={"business_goal": "answer_price_question", "conversation_stage": "sales_objection"},
    )


class BusinessReasoningRuntimeTest(unittest.TestCase):
    def test_reasoning_context_creation(self):
        context = ReasoningContext(
            business_goal="answer_price_question",
            decision_type="Sales Plan",
            business_stage="sales_objection",
            selected_domain="01 Sales",
            selected_skill="01.001.customer_asks_price",
            known_entities={"product": "tea"},
            missing_entities=["price"],
            assumptions=["existing_planner_decision_is_source_of_truth"],
            recommended_next_action="ask_for_price",
            reasoning_pattern="Answer clearly and protect perceived value.",
            confidence=0.8,
        )

        data = context.to_dict()

        self.assertEqual(data["version"], REASONING_RUNTIME_VERSION)
        self.assertEqual(data["selected_skill"], "01.001.customer_asks_price")
        self.assertEqual(data["known_entities"], {"product": "tea"})
        self.assertEqual(data["missing_entities"], ["price"])

    def test_defaults(self):
        context = ReasoningContext()

        self.assertEqual(context.decision_type, "unknown")
        self.assertEqual(context.known_entities, {})
        self.assertEqual(context.missing_entities, [])
        self.assertEqual(context.assumptions, [])
        self.assertEqual(context.risks, [])
        self.assertEqual(context.opportunities, [])
        self.assertEqual(context.confidence, 0.0)
        self.assertEqual(context.version, REASONING_RUNTIME_VERSION)

    def test_dict_roundtrip(self):
        context = ReasoningContext(
            business_goal="create promotion",
            decision_type="Marketing",
            known_entities={"product": "coffee"},
            missing_entities=["offer"],
            confidence="0.6",
            diagnostics={"source": "test"},
        )

        roundtrip = ReasoningContext.from_dict(context.to_dict())

        self.assertEqual(roundtrip.business_goal, "create promotion")
        self.assertEqual(roundtrip.known_entities, {"product": "coffee"})
        self.assertEqual(roundtrip.missing_entities, ["offer"])
        self.assertEqual(roundtrip.confidence, 0.6)

    def test_adapter_creation(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())
        knowledge = create_knowledge_context(
            user_message="price question",
            business_intelligence={
                "matched_skill": {"skill_id": "01.001.customer_asks_price", "business_domain": "01 Sales"},
                "matched_domain": "01 Sales",
                "confidence": 0.8,
            },
            registry=registry,
        )
        route = {
            "planner_output": {"goal": "What price should I reply?", "task_type": "Sales Plan", "next_step": "ask_for_price"},
            "extracted_entities": {"extracted_entities": {"product": "tea"}},
            "business_workflow": {"missing_entities": ["price"], "workflow_stage": "collecting"},
        }

        context = build_reasoning_context(route, knowledge_context=knowledge)

        self.assertEqual(context.business_goal, "answer_price_question")
        self.assertEqual(context.decision_type, "Sales Plan")
        self.assertEqual(context.selected_domain, "01 Sales")
        self.assertEqual(context.selected_skill, "01.001.customer_asks_price")
        self.assertEqual(context.known_entities, {"product": "tea"})
        self.assertIn("price", context.missing_entities)
        self.assertEqual(context.reasoning_pattern, "Answer clearly and protect perceived value.")
        self.assertEqual(context.confidence, 0.8)

    def test_diagnostics(self):
        context = create_reasoning_context({})

        self.assertTrue(context.diagnostics["reasoning_runtime_created"])
        self.assertEqual(context.diagnostics["reasoning_runtime_version"], REASONING_RUNTIME_VERSION)
        self.assertEqual(context.diagnostics["reasoning_source"], REASONING_RUNTIME_SOURCE)
        self.assertEqual(context.diagnostics["runtime_mode"], "diagnostics_only")
        self.assertEqual(context.diagnostics["planner_decision_owner"], "existing_v4_path")

    def test_safe_behavior_with_empty_inputs(self):
        context = build_reasoning_context(None)

        self.assertEqual(context.business_goal, "")
        self.assertEqual(context.decision_type, "unknown")
        self.assertEqual(context.known_entities, {})
        self.assertEqual(context.missing_entities, [])
        self.assertEqual(context.confidence, 0.0)
        self.assertTrue(context.diagnostics["reasoning_runtime_created"])

    def test_registry_and_knowledge_runtime_compatibility(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())
        knowledge = create_knowledge_context(user_message="price question", registry=registry)
        context = build_reasoning_context(
            {"planner_output": {"task_type": "Sales Plan"}},
            knowledge_context=knowledge,
        )

        self.assertEqual(context.version, REASONING_RUNTIME_VERSION)
        self.assertEqual(context.selected_skill, "")
        self.assertIn("price", context.missing_entities)
        self.assertTrue(context.diagnostics["knowledge_context_present"])

    def test_task_router_adds_reasoning_diagnostics_without_planner_migration(self):
        route = build_task_route({}, "price?")
        diagnostics = developer_diagnostics(route)

        self.assertIn("reasoning_context", route)
        self.assertIn("business_reasoning", diagnostics)
        self.assertTrue(diagnostics["reasoning_runtime_created"])
        self.assertEqual(diagnostics["reasoning_runtime_version"], REASONING_RUNTIME_VERSION)
        self.assertEqual(diagnostics["reasoning_source"], REASONING_RUNTIME_SOURCE)
        self.assertTrue(diagnostics["reasoning_context_present"])
        self.assertIn("Business Reasoning", diagnostics["diagnostic_groups"])
        self.assertEqual(route["planner_output"], diagnostics["Planner Output"])
        self.assertNotEqual(route["planner_output"]["next_step"], "business_reasoning_runtime")


if __name__ == "__main__":
    unittest.main()
