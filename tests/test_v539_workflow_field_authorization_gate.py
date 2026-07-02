import unittest

from brain.workflow_authorization_gate import (
    authorize_workflow_mutation,
    update_workflow_state_if_authorized,
)
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_state_machine import new_workflow_state


class V539WorkflowFieldAuthorizationGateTest(unittest.TestCase):
    def test_planner_authorizes_current_workflow_mutation(self):
        current = new_workflow_state(WORKFLOW_COST_CALCULATION)

        updated, extracted, authorization = update_workflow_state_if_authorized(
            current,
            "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20",
            authorized_workflow=WORKFLOW_COST_CALCULATION,
            detected_workflow=WORKFLOW_COST_CALCULATION,
        )

        self.assertTrue(authorization["workflow_mutation_authorized"])
        self.assertEqual(updated["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertTrue(extracted)
        self.assertNotEqual(updated["collected_fields"], current["collected_fields"])

    def test_planner_switches_workflow_and_authorizes_new_workflow_only(self):
        current = new_workflow_state(WORKFLOW_COST_CALCULATION)
        current["collected_fields"] = {"ingredients_costs": [{"name": "flour", "cost": 40}]}

        updated, extracted, authorization = update_workflow_state_if_authorized(
            current,
            "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e01\u0e32\u0e41\u0e1f",
            authorized_workflow=WORKFLOW_CONTENT_PLAN,
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertTrue(authorization["workflow_mutation_authorized"])
        self.assertEqual(updated["workflow"], WORKFLOW_CONTENT_PLAN)
        self.assertNotIn("ingredients_costs", updated["collected_fields"])
        self.assertTrue(extracted)

    def test_planner_release_blocks_workflow_mutation(self):
        current = new_workflow_state(WORKFLOW_COST_CALCULATION)
        current["collected_fields"] = {"ingredients_costs": [{"name": "flour", "cost": 40}]}

        updated, extracted, authorization = update_workflow_state_if_authorized(
            current,
            "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e34\u0e14\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e0a\u0e31\u0e48\u0e19\u0e23\u0e49\u0e32\u0e19",
            authorized_workflow=None,
            detected_workflow=WORKFLOW_COST_CALCULATION,
        )

        self.assertFalse(authorization["workflow_mutation_authorized"])
        self.assertEqual(authorization["workflow_authorization_reason"], "planner_released_workflow")
        self.assertIs(updated, current)
        self.assertEqual(extracted, {})
        self.assertEqual(updated["collected_fields"], {"ingredients_costs": [{"name": "flour", "cost": 40}]})

    def test_workflow_mutation_skipped_when_candidate_is_unauthorized(self):
        current = new_workflow_state(WORKFLOW_COST_CALCULATION)
        current["collected_fields"] = {"ingredients_costs": [{"name": "flour", "cost": 40}]}

        updated, extracted, authorization = update_workflow_state_if_authorized(
            current,
            "100 \u0e0a\u0e34\u0e49\u0e19",
            authorized_workflow=WORKFLOW_CONTENT_PLAN,
            detected_workflow=WORKFLOW_COST_CALCULATION,
        )

        self.assertFalse(authorization["workflow_mutation_authorized"])
        self.assertEqual(
            authorization["workflow_authorization_reason"],
            "candidate_workflow_not_authorized_by_planner",
        )
        self.assertIs(updated, current)
        self.assertEqual(extracted, {})
        self.assertNotIn("total_units", updated["collected_fields"])

    def test_authorization_allows_planner_selected_switch_from_active_workflow(self):
        authorization = authorize_workflow_mutation(
            authorized_workflow=WORKFLOW_CONTENT_PLAN,
            candidate_workflow=WORKFLOW_CONTENT_PLAN,
            current_state={"workflow": WORKFLOW_COST_CALCULATION},
        )

        self.assertTrue(authorization["workflow_mutation_authorized"])
        self.assertEqual(authorization["current_workflow"], WORKFLOW_COST_CALCULATION)
        self.assertEqual(authorization["candidate_workflow"], WORKFLOW_CONTENT_PLAN)


if __name__ == "__main__":
    unittest.main()
