import unittest

from brain.response_transformation_engine import build_response_memory, transform_response
from brain.task_router import build_task_route, developer_diagnostics
from brain.workflow_readiness import WORKFLOW_COST_CALCULATION


class V410FoundationPipelineTest(unittest.TestCase):
    def _state_with_memory(self, memory):
        return {
            "conversation": {
                **memory,
                "response_memory": memory,
                "chat_history": [
                    {"role": "assistant", "content": memory["last_generated_response"]},
                ],
            }
        }

    def test_transformation_chain_skips_planner_and_reuses_previous_response(self):
        memory = build_response_memory(
            "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e0a\u0e32\u0e44\u0e17\u0e22 \u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e2d\u0e2d\u0e1f\u0e1f\u0e34\u0e28\u0e14\u0e37\u0e48\u0e21\u0e41\u0e25\u0e49\u0e27\u0e2a\u0e14\u0e0a\u0e37\u0e48\u0e19 \u0e17\u0e31\u0e01\u0e41\u0e0a\u0e17\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e2a\u0e31\u0e48\u0e07\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22.\n\n\u0e08\u0e38\u0e14\u0e02\u0e32\u0e22\u0e04\u0e37\u0e2d\u0e23\u0e2a\u0e0a\u0e31\u0e14 \u0e0a\u0e07\u0e2a\u0e14 \u0e41\u0e25\u0e30\u0e40\u0e2b\u0e21\u0e32\u0e30\u0e01\u0e31\u0e1a\u0e0a\u0e48\u0e27\u0e07\u0e1e\u0e31\u0e01\u0e07\u0e32\u0e19\u0e02\u0e2d\u0e07\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e2d\u0e2d\u0e1f\u0e1f\u0e34\u0e28.",
            response_type="content_post",
        )
        sequence = [
            ("\u0e41\u0e1a\u0e1a\u0e2a\u0e31\u0e49\u0e19", "SHORTEN"),
            ("emoji", "EMOJI"),
            ("SEO", "SEO"),
            ("translate English", "TRANSLATE"),
            ("formal", "FORMAL"),
            ("young", "YOUTH"),
            ("bullet", "BULLET"),
            ("one sentence", "COMPRESS"),
        ]

        previous_reply = memory["last_generated_response"]
        for message, expected_type in sequence:
            state = self._state_with_memory(memory)
            route = build_task_route(state, message)

            self.assertTrue(route["planner_skipped"])
            self.assertEqual(route["continuation_mode"], "response_transformation")
            self.assertEqual(route["transformation_type"], expected_type)
            self.assertEqual((route["planner_output"] or {})["next_step"], "skip_planner")

            result = transform_response(message, state)
            self.assertTrue(result["handled"])
            self.assertEqual(result["previous_response"], previous_reply)
            self.assertNotEqual(result["reply"], previous_reply)
            memory = build_response_memory(
                result["reply"],
                response_type=result["response_type"],
                previous_memory=memory,
                transformation_result=result,
            )
            previous_reply = result["reply"]

    def test_completed_cost_followup_chain_does_not_skip_planner(self):
        state = {
            "store": {
                "last_completed_workflow": {
                    "workflow_id": WORKFLOW_COST_CALCULATION,
                    "workflow_name": "cost_calculation",
                    "collected_fields": {"unit_cost": 35, "total_units": 100},
                }
            }
        }

        for message in ["profit 40", "sell 50", "profit 15 baht"]:
            with self.subTest(message=message):
                route = build_task_route(state, message)
                self.assertFalse(route.get("planner_skipped", False))
                self.assertFalse(route.get("reuse_completed_workflow", False))
                self.assertNotEqual(route.get("continuation_mode"), "completed_workflow_followup")
                self.assertNotEqual(route.get("response_source"), "completed_workflow")
                self.assertNotEqual((route["planner_output"] or {})["next_step"], "skip_planner")

    def test_diagnostics_are_grouped_without_removing_flat_fields(self):
        memory = build_response_memory("Original response", response_type="content_post")
        route = build_task_route(self._state_with_memory(memory), "shorter")
        diagnostics = developer_diagnostics(route)

        self.assertTrue(diagnostics["planner_skipped"])
        self.assertEqual(diagnostics["transformation_type"], "SHORTEN")
        self.assertIn("diagnostic_groups", diagnostics)
        for group in ["Routing", "Conversation", "Workflow", "Transformation", "Planner", "Memory", "Response"]:
            self.assertIn(group, diagnostics["diagnostic_groups"])
        self.assertTrue(diagnostics["diagnostic_groups"]["Planner"]["planner_skipped"])
        self.assertEqual(diagnostics["diagnostic_groups"]["Transformation"]["transformation_type"], "SHORTEN")


if __name__ == "__main__":
    unittest.main()
