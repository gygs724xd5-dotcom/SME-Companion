import unittest
from unittest.mock import patch

from brain import pipeline_debugger
from memory.application_state import application_state, reset_application_state


class PipelineDebuggerTest(unittest.TestCase):
    def setUp(self):
        reset_application_state()
        pipeline_debugger._fallback_trace = None

    def test_trace_object_creation(self):
        with patch.object(pipeline_debugger, "st", None):
            trace = pipeline_debugger.start_pipeline_trace("hello")

        self.assertEqual(trace["user_message"], "hello")
        self.assertEqual(trace["status"], "started")
        self.assertEqual(len(trace["events"]), 1)
        self.assertEqual(trace["events"][0]["step_id"], 1)
        self.assertEqual(trace["events"][0]["message"], "user input received")
        self.assertIs(application_state["debug"]["last_pipeline_trace"], trace)

    def test_event_append_order(self):
        with patch.object(pipeline_debugger, "st", None):
            pipeline_debugger.start_pipeline_trace("hello")
            pipeline_debugger.add_pipeline_event("stage_a", "fn_a", "first")
            trace = pipeline_debugger.add_pipeline_event("stage_b", "fn_b", "second")

        messages = [event["message"] for event in trace["events"]]
        step_ids = [event["step_id"] for event in trace["events"]]
        self.assertEqual(messages, ["user input received", "first", "second"])
        self.assertEqual(step_ids, [1, 2, 3])

    def test_finalization(self):
        with patch.object(pipeline_debugger, "st", None):
            pipeline_debugger.start_pipeline_trace("hello")
            trace = pipeline_debugger.finalize_pipeline_trace()

        self.assertEqual(trace["status"], "completed")
        self.assertIsNotNone(trace["finalized_at"])
        self.assertIs(application_state["debug"]["last_pipeline_trace"], trace)

    def test_safe_failure_behavior(self):
        with patch.object(pipeline_debugger, "_set_trace", side_effect=RuntimeError("boom")):
            self.assertEqual(pipeline_debugger.start_pipeline_trace("hello"), {})
            self.assertEqual(pipeline_debugger.add_pipeline_event("stage", "fn"), {})
            self.assertEqual(pipeline_debugger.finalize_pipeline_trace(), {})


if __name__ == "__main__":
    unittest.main()
