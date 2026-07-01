import unittest

from brain.response_envelope_runtime import (
    RESPONSE_ENVELOPE_SOURCE,
    RESPONSE_ENVELOPE_VERSION,
    build_response_envelope,
    response_envelope_diagnostics,
)
from brain.task_router import developer_diagnostics


class ResponseEnvelopeRuntimeTest(unittest.TestCase):
    def test_builds_envelope_from_legacy_text_without_rewriting(self):
        legacy_text = "ตอบแบบเดิมทุกตัวอักษร"
        route = {
            "response_source": "workflow_response",
            "selected_business_domain": "sales",
            "selected_business_skill": "customer_reply",
            "business_workflow": {"workflow_id": "reply", "workflow_status": "collecting"},
            "conversation_memory": {
                "read": ["last_customer_message"],
                "write": [{"memory_type": "last_response"}],
            },
            "confidence": "0.72",
        }

        envelope = build_response_envelope(legacy_text, route)
        data = envelope.to_dict()

        self.assertEqual(data["text"], legacy_text)
        self.assertEqual(data["source"], "workflow_response")
        self.assertEqual(data["domain"], "sales")
        self.assertEqual(data["skill_id"], "customer_reply")
        self.assertEqual(data["workflow"]["workflow_id"], "reply")
        self.assertEqual(data["memory_read"], ["last_customer_message"])
        self.assertEqual(data["memory_write"], [{"memory_type": "last_response"}])
        self.assertEqual(data["confidence"], 0.72)
        self.assertEqual(data["version"], RESPONSE_ENVELOPE_VERSION)

    def test_builds_envelope_from_legacy_dict_response(self):
        envelope = build_response_envelope(
            {"reply": "Legacy reply", "ignored": "not displayed"},
            {"final_response_origin": "legacy_response"},
        )

        self.assertEqual(envelope.text, "Legacy reply")
        self.assertEqual(envelope.source, "legacy_response")

    def test_defaults_are_safe_for_empty_inputs(self):
        envelope = build_response_envelope()
        data = envelope.to_dict()

        self.assertEqual(data["text"], "")
        self.assertEqual(data["source"], "legacy_response")
        self.assertEqual(data["workflow"], {})
        self.assertEqual(data["memory_read"], [])
        self.assertEqual(data["memory_write"], [])
        self.assertIsInstance(data["diagnostics"], dict)

    def test_diagnostics_flags_are_present(self):
        envelope = build_response_envelope("Done")
        diagnostics = response_envelope_diagnostics(envelope)

        self.assertTrue(diagnostics["response_envelope_created"])
        self.assertTrue(diagnostics["response_envelope_present"])
        self.assertEqual(diagnostics["response_envelope_version"], RESPONSE_ENVELOPE_VERSION)
        self.assertEqual(diagnostics["response_envelope_source"], RESPONSE_ENVELOPE_SOURCE)
        self.assertEqual(diagnostics["response_envelope"]["text"], "Done")

    def test_developer_diagnostics_exposes_response_envelope_group(self):
        diagnostics = developer_diagnostics(
            {
                "response_source": "direct_conversation_response",
                "final_response_text": "Existing response",
                "business_workflow": {},
                "business_context": {},
                "llm_reasoning_context": {},
                "planner_output": {},
                "business_intelligence": {},
                "loaded_skills": [],
            }
        )

        self.assertTrue(diagnostics["response_envelope_created"])
        self.assertEqual(diagnostics["response_envelope_version"], RESPONSE_ENVELOPE_VERSION)
        self.assertEqual(diagnostics["response_envelope_source"], RESPONSE_ENVELOPE_SOURCE)
        self.assertTrue(diagnostics["response_envelope_present"])
        self.assertIn("Response Envelope", diagnostics["diagnostic_groups"])
        self.assertEqual(
            diagnostics["diagnostic_groups"]["Response Envelope"]["response_envelope"]["text"],
            "Existing response",
        )


if __name__ == "__main__":
    unittest.main()
