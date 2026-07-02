import unittest

from brain.conversation_memory_engine import remember_turn
from brain.response_commit_boundary import commit_response_boundary


class V538ResponseCommitBoundaryTest(unittest.TestCase):
    def test_final_reply_memory_sync(self):
        session_state = {
            "conversation_id": "conv-1",
            "last_user_message": "What should I sell today?",
            "chat_history": [{"role": "user", "content": "What should I sell today?"}],
        }
        application_state = {"conversation": {"conversation_memory": {}}}

        result = commit_response_boundary(
            session_state=session_state,
            application_state=application_state,
            final_reply="Sell the high-margin bundle today.",
            intent="sales_advice",
            workflow=None,
            business_topic="Daily sales",
            response_metadata={"user_message": "What should I sell today?"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        memory = result["conversation_memory"]
        self.assertEqual(session_state["chat_history"][-1]["content"], "Sell the high-margin bundle today.")
        self.assertEqual(application_state["conversation"]["chat_history"][-1]["content"], "Sell the high-margin bundle today.")
        self.assertEqual(memory["last_assistant_reply"], "Sell the high-margin bundle today.")
        self.assertEqual(memory["recent_assistant_replies"][-1], "Sell the high-margin bundle today.")
        self.assertEqual(application_state["conversation"]["conversation_memory"], memory)
        self.assertEqual(application_state["conversation_memory"], memory)

    def test_guarded_reply_memory_sync(self):
        session_state = {
            "conversation_id": "conv-guard",
            "last_user_message": "Use the workflow answer?",
            "chat_history": [{"role": "user", "content": "Use the workflow answer?"}],
        }
        staged_memory = remember_turn(
            {"last_assistant_reply": "Previous visible reply", "recent_assistant_replies": ["Previous visible reply"]},
            "Use the workflow answer?",
            intent="pricing_question",
            workflow="PRICE_CHECK",
            business_topic="Pricing",
        )
        application_state = {"conversation": {"conversation_memory": staged_memory}}

        result = commit_response_boundary(
            session_state=session_state,
            application_state=application_state,
            final_reply="Guarded final answer shown to the user.",
            intent="pricing_question",
            workflow="PRICE_CHECK",
            business_topic="Pricing",
            response_metadata={"user_message": "Use the workflow answer?", "response_source": "response_guard"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        memory = result["conversation_memory"]
        self.assertEqual(session_state["chat_history"][-1]["content"], "Guarded final answer shown to the user.")
        self.assertEqual(memory["last_assistant_reply"], "Guarded final answer shown to the user.")
        self.assertEqual(memory["recent_assistant_replies"][-1], "Guarded final answer shown to the user.")

    def test_no_off_by_one_last_assistant_reply(self):
        previous_memory = remember_turn({}, "First user", assistant_reply="First assistant", intent="first_intent")
        staged_memory = remember_turn(previous_memory, "Second user", intent="second_intent")
        session_state = {
            "conversation_id": "conv-off-by-one",
            "last_user_message": "Second user",
            "chat_history": [
                {"role": "user", "content": "First user"},
                {"role": "assistant", "content": "First assistant"},
                {"role": "user", "content": "Second user"},
            ],
        }
        application_state = {"conversation": {"conversation_memory": staged_memory}}

        result = commit_response_boundary(
            session_state=session_state,
            application_state=application_state,
            final_reply="Second assistant actually rendered",
            intent="second_intent",
            workflow=None,
            business_topic=None,
            response_metadata={"user_message": "Second user"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        memory = result["conversation_memory"]
        self.assertEqual(memory["last_user_message"], "Second user")
        self.assertEqual(memory["last_assistant_reply"], "Second assistant actually rendered")
        self.assertEqual(memory["recent_assistant_replies"], ["First assistant", "Second assistant actually rendered"])
        self.assertEqual(memory["turn_count"], staged_memory["turn_count"])
        self.assertEqual(session_state["chat_history"][-1]["content"], memory["last_assistant_reply"])


if __name__ == "__main__":
    unittest.main()
