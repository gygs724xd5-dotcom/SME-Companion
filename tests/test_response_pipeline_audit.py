import unittest

from brain.response_intelligence_engine import RESPONSE_CANDIDATE_SOURCES, select_final_response
from brain.task_router import build_task_route


class ResponsePipelineAuditTest(unittest.TestCase):
    def assert_audit_source(self, prompt, source, reply, **extra):
        route = build_task_route({}, prompt)
        result = select_final_response(
            [{"source": source, "text": reply}],
            route,
            {
                "final_response_text": reply,
                "response_source_before_gate": extra.get("before_gate", source),
                "response_source_after_gate": source,
                "selected_by": extra.get("selected_by", "unit_test"),
                "response_builder": extra.get("response_builder", source),
                "reply_builder": extra.get("reply_builder", source),
                "legacy_response_used": extra.get("legacy_response_used"),
                "legacy_response_reason": extra.get("legacy_response_reason"),
                "legacy_response_source_file": extra.get("legacy_response_source_file"),
                "legacy_response_source_function": extra.get("legacy_response_source_function"),
            },
        )
        audit = result["diagnostics"]

        self.assertEqual(audit["final_response_origin"], source)
        self.assertEqual(audit["response_source_after_gate"], source)
        self.assertTrue(audit["final_response_text_preview"])
        self.assertEqual(audit["final_response_selector"], "select_final_response")
        self.assertEqual(audit["final_response_selected_by"], extra.get("selected_by", "unit_test"))
        self.assertEqual(
            set(RESPONSE_CANDIDATE_SOURCES),
            {candidate["source"] for candidate in audit["final_response_candidates"] if candidate["source"] in RESPONSE_CANDIDATE_SOURCES},
        )
        self.assertEqual(
            1,
            sum(1 for candidate in audit["final_response_candidates"] if candidate.get("selected")),
        )
        return audit

    def test_sme_companion_question_identifies_direct_response(self):
        audit = self.assert_audit_source(
            "SME Companion คืออะไร",
            "direct_conversation_response",
            "SME Companion คือผู้ช่วยสำหรับร้าน SME ครับ",
            response_builder="conversation_understanding_engine",
            reply_builder="build_direct_reply",
        )

        self.assertTrue(audit["response_gate_applied"])
        self.assertFalse(audit["legacy_response_used"])
        self.assertFalse(audit["workflow_response_used"])

    def test_pricing_unclear_question_can_expose_legacy_response_source(self):
        audit = self.assert_audit_source(
            "pricing_unclear คืออะไร",
            "legacy_response",
            "รับทราบครับ เป็น pricing_unclear คืออะไร",
            response_builder="chat_companion_engine",
            reply_builder="legacy_response_pipeline",
            legacy_response_used=True,
            legacy_response_reason="observed_template_like_reply",
            legacy_response_source_file="brain/chat_companion_engine.py",
            legacy_response_source_function="generate_chat_response",
        )

        self.assertTrue(audit["legacy_response_used"])
        self.assertEqual(audit["legacy_response_reason"], "observed_template_like_reply")
        self.assertEqual(audit["legacy_response_source_function"], "generate_chat_response")

    def test_customer_expensive_question_identifies_deterministic_response(self):
        audit = self.assert_audit_source(
            "ลูกค้าบอกว่าชูครีมแพงไป ควรตอบยังไง",
            "deterministic_response",
            "ตอบโดยย้ำคุณค่าและเสนอทางเลือกให้ลูกค้าครับ",
            response_builder="chat_companion_engine",
            reply_builder="generate_chat_response",
        )

        self.assertTrue(audit["deterministic_response_used"])
        self.assertFalse(audit["workflow_response_used"])

    def test_complete_profit_prompt_identifies_reasoning_after_workflow_gate(self):
        audit = self.assert_audit_source(
            "ขายชูครีม 20 ชิ้น ราคา 35 บาท ต้นทุน 18 บาท กำไรเท่าไร",
            "reasoning_response",
            "กำไรต่อชิ้น 17 บาท รวมกำไร 340 บาทครับ",
            before_gate="workflow_response",
            response_builder="business_reasoning_engine",
            reply_builder="profit_calculation_reasoning",
        )

        self.assertEqual(audit["response_source_before_gate"], "workflow_response")
        self.assertEqual(audit["response_source_after_gate"], "reasoning_response")
        self.assertTrue(audit["response_gate_applied"])
        self.assertTrue(audit["reasoning_response_used"])
        self.assertFalse(audit["workflow_response_used"])


if __name__ == "__main__":
    unittest.main()
