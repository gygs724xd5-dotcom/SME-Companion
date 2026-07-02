import json
import unittest

from brain.authority_engine import build_authority_context
from brain.authority_models import (
    CUSTOMER_SERVICE_AUTHORITY,
    FINANCE_AUTHORITY,
    GENERAL_BUSINESS_AUTHORITY,
    INVENTORY_AUTHORITY,
    MARKETING_AUTHORITY,
    OPERATIONS_AUTHORITY,
    POLICY_AUTHORITY,
    PRICING_AUTHORITY,
    PRINCIPLES_AUTHORITY,
    SALES_AUTHORITY,
)
from brain.authority_registry import (
    AUTHORITY_REGISTRY_VERSION,
    COMMERCIAL_FAMILY,
    CUSTOMER_FAMILY,
    FINANCIAL_FAMILY,
    GENERAL_FAMILY,
    authority_exists,
    enrich_authority_context,
    get_authorities_by_family,
    get_authority_definition,
    get_secondary_authority_candidates,
    list_authorities,
)
from brain.task_router import build_task_route


INITIAL_AUTHORITIES = {
    SALES_AUTHORITY,
    PRICING_AUTHORITY,
    MARKETING_AUTHORITY,
    CUSTOMER_SERVICE_AUTHORITY,
    FINANCE_AUTHORITY,
    INVENTORY_AUTHORITY,
    OPERATIONS_AUTHORITY,
    POLICY_AUTHORITY,
    PRINCIPLES_AUTHORITY,
    GENERAL_BUSINESS_AUTHORITY,
}


class AuthorityRegistryTest(unittest.TestCase):
    def test_all_initial_authorities_exist(self):
        for authority_id in INITIAL_AUTHORITIES:
            self.assertTrue(authority_exists(authority_id))
            self.assertIsNotNone(get_authority_definition(authority_id))

    def test_authority_families_are_defined(self):
        self.assertEqual(
            get_authority_definition(PRICING_AUTHORITY)["authority_family"],
            COMMERCIAL_FAMILY,
        )
        self.assertEqual(
            get_authority_definition(FINANCE_AUTHORITY)["authority_family"],
            FINANCIAL_FAMILY,
        )
        self.assertEqual(
            get_authority_definition(CUSTOMER_SERVICE_AUTHORITY)["authority_family"],
            CUSTOMER_FAMILY,
        )
        self.assertEqual(
            get_authority_definition(GENERAL_BUSINESS_AUTHORITY)["authority_family"],
            GENERAL_FAMILY,
        )

    def test_unknown_authority_returns_none_or_false_safely(self):
        self.assertIsNone(get_authority_definition("unknown_authority"))
        self.assertFalse(authority_exists("unknown_authority"))
        self.assertEqual(get_secondary_authority_candidates("unknown_authority"), [])

    def test_list_authorities_is_deterministic(self):
        first = list_authorities()
        second = list_authorities()

        self.assertEqual(first, second)
        self.assertEqual(
            [item["authority_id"] for item in first],
            sorted(item["authority_id"] for item in first),
        )
        self.assertEqual({item["authority_id"] for item in first}, INITIAL_AUTHORITIES)

    def test_get_authorities_by_family_works(self):
        commercial = get_authorities_by_family(COMMERCIAL_FAMILY)
        commercial_ids = {item["authority_id"] for item in commercial}

        self.assertIn(PRICING_AUTHORITY, commercial_ids)
        self.assertIn(SALES_AUTHORITY, commercial_ids)
        self.assertIn(MARKETING_AUTHORITY, commercial_ids)
        self.assertNotIn(FINANCE_AUTHORITY, commercial_ids)

    def test_get_secondary_authority_candidates_works(self):
        candidates = get_secondary_authority_candidates(PRICING_AUTHORITY)

        self.assertIn(FINANCE_AUTHORITY, candidates)
        self.assertIn(SALES_AUTHORITY, candidates)
        self.assertIn(CUSTOMER_SERVICE_AUTHORITY, candidates)

    def test_registry_is_json_serializable(self):
        encoded = json.dumps(list_authorities(), ensure_ascii=False, sort_keys=True)

        self.assertIn(PRICING_AUTHORITY, encoded)
        self.assertIn(AUTHORITY_REGISTRY_VERSION, encoded)

    def test_enrich_authority_context_does_not_mutate_input(self):
        context = build_authority_context(
            {
                "situation_id": "situation-pricing",
                "objective": "Customer says price is too expensive",
                "known_evidence": [],
            }
        ).to_dict()
        original = json.loads(json.dumps(context, ensure_ascii=False))

        enriched = enrich_authority_context(context)

        self.assertEqual(context, original)
        self.assertEqual(enriched["primary_authority"], context["primary_authority"])
        self.assertIn("authority_registry", enriched)
        self.assertEqual(
            enriched["authority_registry"]["primary_authority_definition"]["authority_id"],
            PRICING_AUTHORITY,
        )
        self.assertTrue(enriched["authority_diagnostics"]["authority_registry_enriched"])
        self.assertEqual(
            enriched["authority_diagnostics"]["authority_registry_mode"],
            "diagnostics_only",
        )

    def test_no_workflow_ownership_appears(self):
        definition = get_authority_definition(PRICING_AUTHORITY)
        enriched = enrich_authority_context(
            {
                "primary_authority": PRICING_AUTHORITY,
                "secondary_authorities": [],
                "authority_diagnostics": {},
            }
        )
        encoded = json.dumps(
            {
                "definition": definition,
                "enriched": enriched,
                "registry": list_authorities(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertNotIn("workflow_owner", encoded)
        self.assertNotIn("execution_owner", encoded)
        self.assertNotIn("workflow_authority", encoded)

    def test_registry_does_not_change_runtime_behavior(self):
        before = build_task_route({}, "price?")
        _ = list_authorities()
        _ = get_authority_definition(PRICING_AUTHORITY)
        _ = get_authorities_by_family(COMMERCIAL_FAMILY)
        after = build_task_route({}, "price?")

        self.assertEqual(before["planner_output"]["task_type"], after["planner_output"]["task_type"])
        self.assertEqual(before["planner_output"]["workflow"], after["planner_output"]["workflow"])
        self.assertEqual(before.get("final_response_gate"), after.get("final_response_gate"))
        self.assertEqual(before.get("workflow_response_allowed"), after.get("workflow_response_allowed"))


if __name__ == "__main__":
    unittest.main()
