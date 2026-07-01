import unittest

from brain.canonical_objects import (
    BusinessMemoryItem,
    ConversationFrame,
    KnowledgeContext,
    PlannerDecision,
    ReasoningContext,
    ReasoningDecision,
    ResponseEnvelope,
    TransformationResult,
    WorkflowState,
    to_canonical_dict,
    workflow_state_from_legacy,
)


class CanonicalObjectsTest(unittest.TestCase):
    def test_objects_create_with_safe_defaults(self):
        objects = [
            ConversationFrame(),
            KnowledgeContext(),
            ReasoningContext(),
            ReasoningDecision(),
            PlannerDecision(),
            WorkflowState(),
            BusinessMemoryItem(),
            TransformationResult(),
            ResponseEnvelope(),
        ]

        for item in objects:
            with self.subTest(item=item.__class__.__name__):
                data = item.to_dict()
                self.assertIsInstance(data, dict)
                self.assertIsInstance(data.get("diagnostics"), dict)

        self.assertEqual(ConversationFrame().candidate_entities, {})
        self.assertEqual(KnowledgeContext().candidate_skills, [])
        self.assertEqual(ReasoningContext().known_entities, {})
        self.assertEqual(ReasoningDecision().known_facts, {})
        self.assertEqual(PlannerDecision().primary_engine_path, [])
        self.assertEqual(WorkflowState().collected_fields, {})
        self.assertEqual(BusinessMemoryItem().provenance, {})
        self.assertEqual(TransformationResult().structured_output, {})
        self.assertEqual(ResponseEnvelope().rendering_hints, {})

    def test_roundtrip_preserves_dict_shape(self):
        frame = ConversationFrame(
            turn_id="turn-1",
            user_message="Create a post",
            normalized_message="create a post",
            conversation_act="command",
            store_id="store-1",
            candidate_entities={"product": "tea"},
            diagnostics={"source": "test"},
        )

        self.assertEqual(ConversationFrame.from_dict(frame.to_dict()).to_dict(), frame.to_dict())

        reasoning = ReasoningDecision(
            reasoning_decision_id="reason-1",
            conversation_frame_id="turn-1",
            knowledge_context_id="knowledge-1",
            business_goal="create_content",
            decision_type="recommendation",
            selected_domain="marketing",
            selected_skill_id="content_plan",
            known_facts={"product": "tea"},
            missing_facts=["audience"],
            assumptions=["default channel"],
            recommended_action="ask_follow_up",
            confidence=0.7,
            diagnostics={"rules": ["missing_audience"]},
        )

        self.assertEqual(ReasoningDecision.from_dict(reasoning.to_dict()).to_dict(), reasoning.to_dict())

        reasoning_context = ReasoningContext(
            business_goal="answer price question",
            decision_type="Sales Plan",
            selected_domain="01 Sales",
            selected_skill="01.001.customer_asks_price",
            known_entities={"product": "tea"},
            missing_entities=["price"],
            confidence=0.8,
            diagnostics={"source": "test"},
        )

        self.assertEqual(ReasoningContext.from_dict(reasoning_context.to_dict()).to_dict(), reasoning_context.to_dict())

    def test_response_envelope_structure(self):
        envelope = ResponseEnvelope(
            response_id="response-1",
            turn_id="turn-1",
            text="What product should I write about?",
            source="workflow",
            domain="marketing",
            skill_id="content_plan",
            confidence=0.8,
            workflow={"workflow_id": "CONTENT_PLAN", "status": "collecting_content_inputs"},
            memory={"write_proposals": []},
            reasoning_summary={"recommended_action": "ask_follow_up"},
            follow_up="Which product should I use?",
            diagnostics={"selected_by": "response_intelligence"},
        )
        data = envelope.to_dict()

        self.assertEqual(data["response_id"], "response-1")
        self.assertEqual(data["turn_id"], "turn-1")
        self.assertEqual(data["text"], "What product should I write about?")
        self.assertEqual(data["source"], "workflow")
        self.assertEqual(data["workflow"]["workflow_id"], "CONTENT_PLAN")
        self.assertEqual(data["memory"], {"write_proposals": []})
        self.assertEqual(data["diagnostics"]["selected_by"], "response_intelligence")
        self.assertFalse(data["fallback_used"])

    def test_workflow_state_structure(self):
        workflow = WorkflowState(
            workflow_id="CONTENT_PLAN",
            workflow_instance_id="workflow-1",
            owner_domain="marketing",
            owner_skill_id="content_plan",
            status="collecting_content_inputs",
            required_fields=["product_or_business_type"],
            collected_fields={},
            missing_fields=["product_or_business_type"],
            last_transition="started",
            next_required_action="collect_fields",
            diagnostics={"readiness": "missing_product"},
        )
        data = workflow.to_dict()

        self.assertEqual(data["workflow_id"], "CONTENT_PLAN")
        self.assertEqual(data["status"], "collecting_content_inputs")
        self.assertEqual(data["required_fields"], ["product_or_business_type"])
        self.assertEqual(data["collected_fields"], {})
        self.assertEqual(data["missing_fields"], ["product_or_business_type"])
        self.assertEqual(data["next_required_action"], "collect_fields")
        self.assertEqual(data["diagnostics"]["readiness"], "missing_product")

    def test_compatible_with_existing_dict_style_data(self):
        legacy_workflow = {
            "workflow": "CONTENT_PLAN",
            "step": "collecting_content_inputs",
            "required_fields": ["product_or_business_type"],
            "collected_fields": {"product": "tea"},
            "missing_fields": [],
            "is_ready": True,
            "next_action": "generate",
            "last_updated": "2026-07-01T00:00:00+00:00",
            "unknown_legacy_field": "ignored",
        }

        workflow = workflow_state_from_legacy(legacy_workflow)
        data = workflow.to_dict()

        self.assertEqual(data["workflow_id"], "CONTENT_PLAN")
        self.assertEqual(data["status"], "collecting_content_inputs")
        self.assertEqual(data["next_required_action"], "generate")
        self.assertEqual(data["updated_at"], "2026-07-01T00:00:00+00:00")
        self.assertEqual(data["collected_fields"], {"product": "tea"})
        self.assertEqual(data["diagnostics"]["legacy_fields"]["is_ready"], True)
        self.assertNotIn("unknown_legacy_field", data)

        envelope_dict = {"turn_id": "turn-1", "text": "Done", "source": "legacy_pipeline"}
        self.assertEqual(ResponseEnvelope.from_dict(envelope_dict).text, "Done")
        self.assertEqual(to_canonical_dict(envelope_dict), envelope_dict)

    def test_from_dict_uses_independent_mutable_defaults(self):
        first = ConversationFrame.from_dict({})
        second = ConversationFrame.from_dict({})

        first.candidate_entities["product"] = "tea"
        first.ambiguity_flags.append("missing_audience")

        self.assertEqual(second.candidate_entities, {})
        self.assertEqual(second.ambiguity_flags, [])


if __name__ == "__main__":
    unittest.main()
