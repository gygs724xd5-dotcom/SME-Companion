import unittest

from brain.clarification_recovery import recover_from_clarification
from brain.context_freshness import evaluate_context_freshness
from brain.evidence_conflict_runtime import detect_current_correction, detect_evidence_conflicts
from brain.follow_up_resolution import resolve_follow_up
from brain.knowledge_skill_outcome_hardening import harden_knowledge_skill_outcome
from brain.skill_ambiguity import assess_skill_ambiguity
from brain.topic_transition import detect_topic_transition
from brain.workflow_interruption import detect_workflow_interruption
from brain.task_router import build_task_route


class V594KnowledgeSkillOutcomeHardeningTest(unittest.TestCase):
    def test_direct_partial_ambiguous_and_refusal_followups(self):
        self.assertEqual(resolve_follow_up("per day", {"metric_id": "output_time_period"})["answer_status"], "ANSWERED")
        partial = resolve_follow_up("revenue 50,000 and 45,000", {"metric_id": "total_revenue"})
        self.assertEqual(partial["answer_status"], "PARTIALLY_ANSWERED")
        self.assertEqual(resolve_follow_up("depends by day", {"metric_id": "output_time_period"})["answer_status"], "AMBIGUOUS")
        self.assertEqual(resolve_follow_up("not share", {"metric_id": "net_profit"})["answer_status"], "USER_DECLINED")

    def test_topic_switch_return_and_freshness(self):
        previous = {"active_topic_id": "INVENTORY_HEALTH", "unresolved_gap_ids": ["average_daily_sales"]}
        switch = detect_topic_transition("startup cost", previous)
        self.assertEqual(switch["transition_type"], "TOPIC_SWITCH")
        self.assertIn("average_daily_sales", switch["stale_gaps"])
        returned = detect_topic_transition("stock again now 2 pieces", previous)
        self.assertEqual(returned["transition_type"], "TOPIC_RETURN")
        self.assertEqual(evaluate_context_freshness("current_stock", turn_distance=3)["freshness_status"], "STALE")
        self.assertEqual(evaluate_context_freshness("business_model", turn_distance=3)["freshness_status"], "RECENT")

    def test_conflict_correction_and_ambiguity(self):
        conflict = detect_evidence_conflicts("current_stock", [{"value": 12, "source": "memory"}, {"value": 3, "source": "user"}])
        self.assertEqual(conflict["conflict_type"], "VALUE_CONFLICT")
        correction = detect_current_correction("actually now 3", "current_stock", 12, 3)
        self.assertFalse(correction["resolution_required"])
        ambiguity = assess_skill_ambiguity([], user_message="sales bad")
        self.assertTrue(ambiguity["ambiguity_detected"])
        self.assertEqual(ambiguity["status"], "NO_CONFIDENT_PRIMARY")

    def test_retry_cap_and_workflow_interruption(self):
        recovery = recover_from_clarification({"source_gap_id": "output_time_period"}, {"answer_status": "AMBIGUOUS"}, retry_count=2)
        self.assertFalse(recovery["retry_allowed"])
        interruption = detect_workflow_interruption("more customers lower profit", {"workflow_id": "PROFIT_CALCULATION"})
        self.assertTrue(interruption["interruption_detected"])
        self.assertTrue(interruption["workflow_preserved"])

    def test_route_ambiguous_sales_does_not_force_primary(self):
        route = build_task_route({}, "sales bad")
        bridge = route["business_situation"]["diagnostics"]["knowledge_skill_bridge"]
        outcome = bridge["conversation_outcome_hardening"]
        self.assertTrue(outcome["skill_ambiguity_detected"])
        self.assertIsNone(bridge["primary_skill_candidate"])
        self.assertFalse(bridge["constitutional_invariants"]["planner_invoked"])

    def test_hardening_outcome_has_no_judgment_or_memory_mutation(self):
        route = build_task_route({}, "stock 3 pieces")
        bridge = route["business_situation"]["diagnostics"]["knowledge_skill_bridge"]
        outcome = harden_knowledge_skill_outcome({"current_message": "startup cost"}, bridge)
        self.assertEqual(outcome["topic_transition_type"], "TOPIC_SWITCH")
        self.assertFalse(bridge["constitutional_invariants"]["judgment_generated"])
        self.assertFalse(bridge["constitutional_invariants"]["conversation_memory_mutated_by_bridge"])


if __name__ == "__main__":
    unittest.main()
