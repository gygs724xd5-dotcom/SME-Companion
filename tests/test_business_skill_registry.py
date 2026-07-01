import unittest

from brain.business_skill_registry import (
    BusinessSkill,
    SkillRegistry,
    create_registry,
    find_skill,
    get_skill,
    list_domains,
    list_skills,
)
from brain.task_router import developer_diagnostics


def registry_skill(skill_id="01.001.customer_asks_price", *, intent="Customer asks price") -> BusinessSkill:
    return BusinessSkill(
        skill_id=skill_id,
        skill_name="Customer asks price",
        domain_id="01",
        domain_name="Sales",
        intent=intent,
        description="A customer asks how much a product costs.",
        workflow_id="Sales Planning",
        required_entities=["product", "price"],
        required_memory=["pricing_strategy"],
        business_rules=["Price first when known."],
        reasoning="Answer clearly and protect perceived value.",
        response_style="NORMAL_CHAT",
        confidence="High when product is clear.",
        status="test",
        version="test",
    )


class BusinessSkillRegistryTest(unittest.TestCase):
    def test_registry_creation_loads_existing_skills_through_adapters(self):
        registry = create_registry()

        diagnostics = registry.diagnostics()

        self.assertEqual(diagnostics["registry_version"], "5.1.0")
        self.assertEqual(diagnostics["registered_skills"], 10)
        self.assertGreaterEqual(diagnostics["registered_domains"], 1)
        self.assertIsNotNone(registry.get_skill("01.001.customer_asks_price"))

    def test_skill_registration_and_lookup(self):
        registry = SkillRegistry()
        registered = registry.register_skill(registry_skill())

        self.assertEqual(registered.skill_id, "01.001.customer_asks_price")
        self.assertEqual(registry.get_skill("01.001.customer_asks_price"), registered)
        self.assertEqual(registry.get_skill("customer_asks_price"), registered)

    def test_domain_listing(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())

        domains = registry.list_domains()

        self.assertEqual(len(domains), 1)
        self.assertEqual(domains[0].domain_id, "01")
        self.assertEqual(domains[0].domain_name, "Sales")

    def test_intent_lookup(self):
        registry = SkillRegistry()
        expected = registry.register_skill(registry_skill(intent="Handle customer price question"))

        self.assertEqual(registry.find_skill("price question"), expected)

    def test_duplicate_registration_protection(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())

        with self.assertRaises(ValueError):
            registry.register_skill(registry_skill())

    def test_module_helpers_expose_default_registry(self):
        self.assertIsNotNone(get_skill("customer_asks_price"))
        self.assertIsNotNone(find_skill("price"))
        self.assertGreaterEqual(len(list_domains()), 1)
        self.assertEqual(len(list_skills()), 10)

    def test_developer_diagnostics_include_registry_foundation(self):
        diagnostics = developer_diagnostics({})

        self.assertEqual(diagnostics["registry_version"], "5.1.0")
        self.assertEqual(diagnostics["registered_skills"], 10)
        self.assertGreaterEqual(diagnostics["registered_domains"], 1)
        self.assertEqual(
            diagnostics["diagnostic_groups"]["Business Knowledge"]["registered_skills"],
            10,
        )


if __name__ == "__main__":
    unittest.main()
