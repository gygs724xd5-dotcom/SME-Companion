import unittest

from brain.business_knowledge_runtime import create_knowledge_context
from brain.business_reasoning_runtime import create_reasoning_context
from brain.canonical_objects import KnowledgeContext, PlannerContext, ReasoningContext
from brain.planner_adapter import (
    PLANNER_CONTEXT_SOURCE,
    PLANNER_CONTEXT_VERSION,
    build_planner_context,
)
from brain.task_router import build_task_route, developer_diagnostics


class PlannerAdapterTest(unittest.TestCase):
    def test_planner_context_creation(self):
        context = PlannerContext(
            selected_domain="01 Sales",
            selected_skill="01.001.customer_asks_price",
            business_goal="answer_price_question",
            decision_type="Sales Plan",
            workflow_owner="sales_reply",
            workflow_state={"workflow": "sales_reply"},
            planner_inputs={"planner_output": {"task_type": "Sales Plan"}},
            planner_hints={"recommended_next_action": "ask_for_price"},
            planner_constraints=["diagnostics_only"],
            confidence=0.8,
            diagnostics={"source": "test"},
        )

        data = context.to_dict()

        self.assertEqual(data["version"], PLANNER_CONTEXT_VERSION)
        self.assertEqual(data["selected_domain"], "01 Sales")
        self.assertEqual(data["planner_constraints"], ["diagnostics_only"])
        self.assertEqual(data["confidence"], 0.8)

    def test_defaults(self):
        context = PlannerContext()

        self.assertEqual(context.selected_domain, "")
        self.assertEqual(context.selected_skill, "")
        self.assertEqual(context.business_goal, "")
        self.assertEqual(context.decision_type, "unknown")
        self.assertEqual(context.workflow_state, {})
        self.assertEqual(context.planner_inputs, {})
        self.assertEqual(context.planner_hints, {})
        self.assertEqual(context.planner_constraints, [])
        self.assertEqual(context.confidence, 0.0)
        self.assertEqual(context.version, PLANNER_CONTEXT_VERSION)

    def test_dict_roundtrip(self):
        context = PlannerContext(
            business_goal="create promotion",
            decision_type="Marketing",
            planner_inputs={"planner_output": {"goal": "promo"}},
            confidence="0.6",
            diagnostics={"source": "test"},
        )

        roundtrip = PlannerContext.from_dict(context.to_dict())

        self.assertEqual(roundtrip.business_goal, "create promotion")
        self.assertEqual(roundtrip.decision_type, "Marketing")
        self.assertEqual(roundtrip.planner_inputs["planner_output"]["goal"], "promo")
        self.assertEqual(roundtrip.confidence, 0.6)

    def test_adapter_output(self):
        knowledge = KnowledgeContext(
            knowledge_context_id="knowledge-1",
            selected_domain="01 Sales",
            selected_skill="01.001.customer_asks_price",
            confidence=0.7,
        )
        reasoning = ReasoningContext(
            reasoning_context_id="reasoning-1",
            knowledge_context_id="knowledge-1",
            business_goal="answer_price_question",
            decision_type="Sales Plan",
            selected_domain="01 Sales",
            selected_skill="01.001.customer_asks_price",
            recommended_next_action="ask_for_price",
            confidence=0.8,
        )
        route = {
            "planner_output": {"goal": "What price should I reply?", "task_type": "Sales Plan", "next_step": "ask_for_price"},
            "intent_resolution": {"resolved_intent": "customer_asks_price"},
            "conversation_understanding": {"raw_text": "price?"},
        }

        context = build_planner_context(
            route,
            knowledge_context=knowledge,
            reasoning_context=reasoning,
            workflow_state={"workflow": "sales_reply"},
        )

        self.assertEqual(context.selected_domain, "01 Sales")
        self.assertEqual(context.selected_skill, "01.001.customer_asks_price")
        self.assertEqual(context.business_goal, "answer_price_question")
        self.assertEqual(context.decision_type, "Sales Plan")
        self.assertEqual(context.workflow_owner, "sales_reply")
        self.assertEqual(context.confidence, 0.8)
        self.assertEqual(context.planner_inputs["planner_output"], route["planner_output"])
        self.assertIn("diagnostics_only", context.planner_constraints)
        self.assertFalse(context.diagnostics["planner_logic_executed"])

    def test_empty_inputs(self):
        context = build_planner_context(None)

        self.assertEqual(context.selected_domain, "")
        self.assertEqual(context.selected_skill, "")
        self.assertEqual(context.business_goal, "")
        self.assertEqual(context.decision_type, "unknown")
        self.assertEqual(context.workflow_state, {})
        self.assertEqual(context.confidence, 0.0)
        self.assertTrue(context.diagnostics["planner_context_created"])

    def test_compatibility_with_knowledge_and_reasoning_contexts(self):
        knowledge = create_knowledge_context(user_message="price question")
        reasoning = create_reasoning_context(
            {"planner_output": {"goal": "Help answer price", "task_type": "Sales Plan"}},
            knowledge_context=knowledge,
        )

        context = build_planner_context(
            {"planner_output": {"goal": "Help answer price", "task_type": "Sales Plan"}},
            knowledge_context=knowledge,
            reasoning_context=reasoning,
        )

        self.assertEqual(context.version, PLANNER_CONTEXT_VERSION)
        self.assertEqual(context.business_goal, "Help answer price")
        self.assertEqual(context.decision_type, "Sales Plan")
        self.assertTrue(context.diagnostics["knowledge_context_present"])
        self.assertTrue(context.diagnostics["reasoning_context_present"])

    def test_task_router_adds_planner_context_diagnostics_only(self):
        route = build_task_route({}, "price?")
        diagnostics = developer_diagnostics(route)

        self.assertIn("planner_context", route)
        self.assertIn("planner_context", diagnostics)
        self.assertTrue(diagnostics["planner_context_created"])
        self.assertEqual(diagnostics["planner_context_version"], PLANNER_CONTEXT_VERSION)
        self.assertEqual(diagnostics["planner_context_source"], PLANNER_CONTEXT_SOURCE)
        self.assertTrue(diagnostics["planner_context_present"])
        self.assertIn("Planner Context", diagnostics["diagnostic_groups"])
        self.assertEqual(route["planner_output"], diagnostics["Planner Output"])
        self.assertNotEqual(route["planner_output"].get("next_step"), "planner_adapter")


if __name__ == "__main__":
    unittest.main()
