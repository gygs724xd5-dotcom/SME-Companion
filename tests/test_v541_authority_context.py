import json
import unittest

from brain.authority_engine import build_authority_context
from brain.authority_models import (
    AUTHORITY_CONTEXT_VERSION,
    CUSTOMER_SERVICE_AUTHORITY,
    GENERAL_BUSINESS_AUTHORITY,
    PRICING_AUTHORITY,
    AuthorityContext,
)


def _situation(objective: str, **overrides) -> dict:
    data = {
        "situation_id": "business_situation_test",
        "objective": objective,
        "business_context": {},
        "known_evidence": [
            {
                "source": "user",
                "kind": "current_message",
                "summary": objective,
                "confidence": 1.0,
            }
        ],
        "known_constraints": [],
        "material_uncertainty": [],
        "relevant_business_entities": {},
        "business_topic": "general_business",
        "conversation_purpose": "help",
        "required_capabilities": [],
        "potential_business_risks": [],
        "potential_opportunities": [],
        "assumptions": [],
        "diagnostics": {"business_situation_created": True},
        "version": "5.4.0",
    }
    data.update(overrides)
    return data


class AuthorityContextTest(unittest.TestCase):
    def test_authority_context_can_be_created_from_business_situation_like_dict(self):
        context = build_authority_context(_situation("help me with my business"))

        self.assertIsInstance(context, AuthorityContext)
        payload = context.to_dict()
        self.assertEqual(payload["business_situation_id"], "business_situation_test")
        self.assertEqual(payload["version"], AUTHORITY_CONTEXT_VERSION)
        self.assertIn("primary_authority", payload)
        self.assertIn("authority_resolution", payload)
        self.assertIn("authority_path", payload)

    def test_pricing_related_situation_selects_pricing_authority(self):
        context = build_authority_context(
            _situation("Customer says the price is too expensive and asks for a discount")
        )

        self.assertEqual(context.primary_authority, PRICING_AUTHORITY)
        self.assertIn(CUSTOMER_SERVICE_AUTHORITY, context.secondary_authorities)
        self.assertIn(context.authority_confidence, {"high", "medium"})

    def test_customer_service_related_situation_selects_customer_service_authority(self):
        context = build_authority_context(
            _situation("Customer complaint: help me reply about service problem")
        )

        self.assertEqual(context.primary_authority, CUSTOMER_SERVICE_AUTHORITY)
        self.assertIn(context.authority_confidence, {"high", "medium"})

    def test_unknown_situation_falls_back_to_general_business_authority(self):
        context = build_authority_context(_situation("What should I think about next?"))

        self.assertEqual(context.primary_authority, GENERAL_BUSINESS_AUTHORITY)
        self.assertEqual(context.authority_confidence, "low")
        self.assertTrue(context.authority_resolution["fallback_used"])

    def test_diagnostics_prove_diagnostics_only_mode(self):
        diagnostics = build_authority_context(_situation("price question")).authority_diagnostics

        self.assertTrue(diagnostics["authority_context_created"])
        self.assertEqual(diagnostics["authority_version"], AUTHORITY_CONTEXT_VERSION)
        self.assertEqual(diagnostics["runtime_mode"], "diagnostics_only")
        self.assertFalse(diagnostics["routes_changed"])
        self.assertFalse(diagnostics["planner_output_changed"])
        self.assertFalse(diagnostics["workflow_changed"])
        self.assertFalse(diagnostics["responses_changed"])
        self.assertFalse(diagnostics["commit_boundary_changed"])
        self.assertEqual(diagnostics["authority_selected_by"], "authority_engine")
        self.assertFalse(diagnostics["workflow_decided_authority"])

    def test_no_workflow_ownership_appears(self):
        payload = build_authority_context(_situation("stock shortage")).to_dict()

        self.assertNotIn("workflow_owner", payload)
        self.assertNotIn("execution_owner", payload)
        self.assertNotEqual(payload["primary_authority"], "workflow_authority")
        self.assertNotIn("workflow_authority", payload["secondary_authorities"])
        self.assertFalse(payload["authority_diagnostics"]["workflow_decided_authority"])

    def test_function_is_deterministic(self):
        situation = _situation("calculate margin and price")

        first = build_authority_context(situation).to_dict()
        second = build_authority_context(situation).to_dict()

        self.assertEqual(first, second)

    def test_returned_object_is_dict_serializable(self):
        payload = build_authority_context(_situation("reply to a customer complaint")).to_dict()

        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.assertIn("authority_context_id", encoded)


if __name__ == "__main__":
    unittest.main()
