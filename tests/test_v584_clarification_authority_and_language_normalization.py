import copy
import unittest

from brain.brain_observatory import build_brain_observatory
from brain.clarification_authority import build_clarification_response
from brain.language_normalization import normalize_user_language
from brain.task_router import build_task_route, developer_diagnostics


MISSPELLED_CALC = "ช่วยคำนวนกำไรให้หน่อย"
EXPLICIT_CALC = "ช่วยคำนวณกำไรให้หน่อย"
NUMERIC_PROFIT = "ขาย 80 บาท ต้นทุน 35 บาท กำไรกี่บาท"
PROFIT_DROP = "ลูกค้าเพิ่มแต่กำไรลด"
BUSINESS_PROFIT = "ร้านของฉันกำไรดีไหม"
INVENTORY_QUERY = "ตอนนี้ในสต๊อกเหลืออะไรบ้าง"
GENERIC_FALLBACK = "ขอข้อมูลอีกนิดครับ"


class V584ClarificationAuthorityAndLanguageNormalizationTest(unittest.TestCase):
    def test_language_normalization_rules(self):
        result = normalize_user_language("คำนวน")
        self.assertEqual(result["normalized_text"], "คำนวณ")
        self.assertEqual(result["original_text"], "คำนวน")
        self.assertEqual(normalize_user_language("ขายดีแต่กำไรน้อย")["normalized_text"], "ขายดีแต่กำไรน้อย")
        self.assertEqual(normalize_user_language(MISSPELLED_CALC), normalize_user_language(MISSPELLED_CALC))

    def test_language_normalization_does_not_mutate_input_container(self):
        payload = {"text": MISSPELLED_CALC}
        before = copy.deepcopy(payload)
        normalize_user_language(payload["text"])
        self.assertEqual(payload, before)

    def test_misspelled_profit_request_becomes_executable(self):
        route = build_task_route({}, MISSPELLED_CALC)
        self.assertEqual(route["language_normalization"]["normalized_text"], EXPLICIT_CALC)
        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual((route["business_workflow"]["workflow_state"] or {}).get("workflow_id"), "PROFIT_CALCULATION")

    def test_business_profit_assessment_requests_business_metrics(self):
        route = build_task_route({}, BUSINESS_PROFIT)
        clarification = route["clarification_authority"]
        text = clarification["clarification_text"]

        self.assertNotEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(clarification["reason"], "BUSINESS_ASSESSMENT_NEEDS_METRICS")
        self.assertIn("timeframe", clarification["requested_fields"])
        self.assertIn("revenue", clarification["requested_fields"])
        self.assertIn("cost", clarification["requested_fields"])
        self.assertIn("expenses", clarification["requested_fields"])
        self.assertIn("รายได้", text)
        self.assertIn("ต้นทุนสินค้า", text)
        self.assertIn("ค่าใช้จ่าย", text)
        self.assertNotIn("ขายราคากี่บาทครับ", text)
        self.assertNotEqual(text, GENERIC_FALLBACK)

    def test_analytical_relationship_receives_specific_non_diagnostic_clarification(self):
        route = build_task_route({}, PROFIT_DROP)
        text = route["final_response_text"]

        self.assertNotEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(route["clarification_authority"]["reason"], "ANALYTICAL_RELATIONSHIP_NEEDS_EVIDENCE")
        self.assertIn("ลูกค้า", text)
        self.assertIn("กำไร", text)
        self.assertIn("ยอดขายเฉลี่ยต่อบิล", text)
        self.assertIn("ต้นทุน", text)
        self.assertNotIn("ต้นทุนสูงแน่นอน", text)
        self.assertNotIn("ควรขึ้นราคา", text)
        self.assertNotIn("ควรลดพนักงาน", text)
        self.assertNotEqual(text, GENERIC_FALLBACK)

    def test_inventory_query_without_data_requests_inventory_input(self):
        route = build_task_route({}, INVENTORY_QUERY)
        text = route["final_response_text"]

        self.assertEqual(route["clarification_authority"]["reason"], "INVENTORY_QUERY_NEEDS_CURRENT_DATA")
        self.assertIn("ยังไม่มีข้อมูลสต๊อกล่าสุด", text)
        self.assertIn("ส่งรายการสินค้า", text)

    def test_existing_inventory_data_prevents_unnecessary_clarification(self):
        route = build_task_route({"inventory": {"tea": 10}}, INVENTORY_QUERY)

        self.assertEqual(route["clarification_authority"]["decision"], "NO_CLARIFICATION_NEEDED")
        self.assertNotEqual(route.get("response_source"), "clarification_authority")

    def test_duplicate_question_guard_suppresses_repeated_question(self):
        previous = (
            "ตอนนี้ยังสรุปไม่ได้ครับ เพราะต้องดูรายได้ ต้นทุนสินค้า ค่าใช้จ่าย และช่วงเวลาเดียวกัน "
            "คุณอยากวิเคราะห์รายวัน รายสัปดาห์ หรือรายเดือนครับ?"
        )
        result = build_clarification_response(
            user_message=BUSINESS_PROFIT,
            normalized_user_message=BUSINESS_PROFIT,
            workflow_admission_gate={"decision": "REJECT_TO_CONVERSATION", "reason": "AMBIGUOUS_BUSINESS_ASSESSMENT", "workflow_candidate": "PROFIT_CALCULATION"},
            application_state={"conversation": {"chat_history": [{"role": "assistant", "content": previous}]}},
        )

        self.assertTrue(result["duplicate_guard_applied"])
        self.assertEqual(result["suppressed_question"], previous)
        self.assertIn("ยอดขายรวม", result["replacement_question"])

    def test_previously_supplied_fields_are_not_requested_again(self):
        result = build_clarification_response(
            user_message="ร้านของฉันกำไรดีไหม รายเดือน",
            normalized_user_message="ร้านของฉันกำไรดีไหม รายเดือน",
            workflow_admission_gate={"decision": "REJECT_TO_CONVERSATION", "reason": "AMBIGUOUS_BUSINESS_ASSESSMENT", "workflow_candidate": "PROFIT_CALCULATION"},
        )

        self.assertNotIn("timeframe", result["requested_fields"])
        self.assertIn("ยอดขายรวม", result["clarification_text"])

    def test_specific_clarification_replaces_generic_fallback_and_no_gap_preserves_path(self):
        specific = build_task_route({}, PROFIT_DROP)
        no_gap = build_task_route({}, "hello")

        self.assertEqual(specific["response_source"], "clarification_authority")
        self.assertTrue(specific["generic_fallback_avoided"])
        self.assertEqual(no_gap["clarification_authority"]["decision"], "USE_EXISTING_CONVERSATION_RESPONSE")
        self.assertNotEqual(no_gap.get("response_source"), "clarification_authority")

    def test_workflow_compatibility(self):
        explicit = build_task_route({}, EXPLICIT_CALC)
        misspelled = build_task_route({}, MISSPELLED_CALC)
        numeric = build_task_route({}, NUMERIC_PROFIT)
        analytical = build_task_route({}, PROFIT_DROP)
        assessment = build_task_route({}, BUSINESS_PROFIT)

        self.assertEqual(explicit["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(explicit["business_workflow"]["next_question"], "ขายราคากี่บาทครับ")
        self.assertEqual(misspelled["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(misspelled["business_workflow"]["next_question"], "ขายราคากี่บาทครับ")
        self.assertEqual(numeric["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertTrue((numeric["business_workflow"]["readiness_decision"] or {}).get("workflow_executable"))
        self.assertEqual(numeric["business_workflow"]["extracted_entities"]["price"] - numeric["business_workflow"]["extracted_entities"]["cost"], 45)
        self.assertNotEqual(analytical["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertNotEqual(assessment["workflow_admission_gate"]["decision"], "ADMIT")

    def test_authority_audit_records_new_authority_fields(self):
        route = build_task_route({}, PROFIT_DROP)
        audit = route["cognitive_authority_audit"]

        self.assertTrue(audit["language_normalization_consulted"])
        self.assertTrue(audit["clarification_authority_consulted"])
        self.assertTrue(audit["clarification_authority_used"])
        self.assertEqual(audit["clarification_reason"], "ANALYTICAL_RELATIONSHIP_NEEDS_EVIDENCE")
        self.assertEqual(audit["winning_authority"], "clarification_authority")
        self.assertEqual(audit["winning_stage"], "CLARIFICATION_AUTHORITY")
        self.assertEqual(audit["commit_source"], None)
        self.assertFalse(audit["cognitive_runtime_authoritative"])
        self.assertEqual(audit["constitutional_invariants"]["commit_boundary_changed"], False)
        self.assertEqual(audit["constitutional_invariants"]["perspective_logic_changed"], False)
        self.assertEqual(audit["constitutional_invariants"]["knowledge_invoked"], False)
        self.assertEqual(audit["constitutional_invariants"]["judgment_invoked"], False)
        self.assertEqual(audit["constitutional_invariants"]["decision_invoked"], False)
        self.assertEqual(audit["constitutional_invariants"]["recommendations_generated"], False)
        self.assertEqual(audit["constitutional_invariants"]["root_causes_diagnosed"], False)

    def test_commit_source_remains_response_commit_boundary_when_committed(self):
        route = build_task_route({}, PROFIT_DROP)
        route["commit_source"] = "response_commit_boundary"
        from brain.cognitive_authority_audit import build_cognitive_authority_audit

        audit = build_cognitive_authority_audit(route)
        self.assertEqual(audit["commit_source"], "response_commit_boundary")
        self.assertEqual(audit["winning_stage"], "COMMIT")

    def test_developer_diagnostics_and_observatory_expose_new_groups(self):
        route = build_task_route({}, MISSPELLED_CALC)
        diagnostics = developer_diagnostics(route)
        observatory = build_brain_observatory(route)

        self.assertIn("Language Normalization", diagnostics["diagnostic_groups"])
        self.assertIn("Clarification Authority", diagnostics["diagnostic_groups"])
        self.assertEqual(observatory["language_normalization"]["normalized_text"], EXPLICIT_CALC)
        self.assertIn("clarification_authority", observatory)

    def test_outcome_regressions(self):
        relationship = build_task_route({}, PROFIT_DROP)
        assessment = build_task_route({}, BUSINESS_PROFIT)
        misspelled = build_task_route({}, MISSPELLED_CALC)

        self.assertNotEqual(relationship["final_response_text"], GENERIC_FALLBACK)
        self.assertIn("ลูกค้า", relationship["final_response_text"])
        self.assertIn("ยอดขาย", relationship["final_response_text"])
        self.assertIn("รายได้", assessment["final_response_text"])
        self.assertNotIn("ขายราคากี่บาทครับ", assessment["final_response_text"])
        self.assertEqual(misspelled["workflow_admission_gate"]["decision"], "ADMIT")


if __name__ == "__main__":
    unittest.main()
