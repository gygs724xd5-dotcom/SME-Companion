import unittest

from brain.business_knowledge_runtime import (
    KNOWLEDGE_CONTEXT_VERSION,
    KNOWLEDGE_RUNTIME_SOURCE,
    BusinessKnowledgeRuntime,
    create_knowledge_context,
)
from brain.business_skill_registry import BusinessSkill, SkillRegistry, create_registry
from brain.task_router import build_task_route, developer_diagnostics


def registry_skill(skill_id="01.001.customer_asks_price", *, intent="Handle customer price question"):
    return BusinessSkill(
        skill_id=skill_id,
        skill_name="Customer asks price",
        domain_id="01",
        domain_name="Sales",
        intent=intent,
        description="A customer asks how much a product costs.",
        workflow_id="sales_reply",
        required_entities=["product", "price"],
        required_memory=["pricing_strategy"],
        business_rules=["Price first when known."],
        reasoning="Answer clearly and protect perceived value.",
        response_style="NORMAL_CHAT",
        confidence="High when product is clear.",
        status="test",
        version="test",
        metadata={"tools": ["none"]},
    )


class BusinessKnowledgeRuntimeTest(unittest.TestCase):
    def test_knowledge_context_creation(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())

        context = create_knowledge_context(
            user_message="price question",
            business_intelligence={
                "matched_skill": {"skill_id": "01.001.customer_asks_price", "business_domain": "01 Sales"},
                "matched_domain": "01 Sales",
                "confidence": 0.8,
            },
            registry=registry,
        )

        data = context.to_dict()
        self.assertEqual(data["version"], KNOWLEDGE_CONTEXT_VERSION)
        self.assertEqual(data["selected_domain"], "01 Sales")
        self.assertEqual(data["selected_skill"], "01.001.customer_asks_price")
        self.assertEqual(data["confidence"], 0.8)
        self.assertTrue(data["diagnostics"]["knowledge_context_created"])

    def test_registry_lookup_and_metadata(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())
        runtime = BusinessKnowledgeRuntime(registry)

        domain = runtime.domain_metadata("01")
        skill = runtime.skill_metadata("customer_asks_price")

        self.assertEqual(domain["domain_name"], "Sales")
        self.assertEqual(skill["skill_id"], "01.001.customer_asks_price")
        self.assertEqual(skill["workflow_id"], "sales_reply")

    def test_candidate_domain_and_skill_generation(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())
        runtime = BusinessKnowledgeRuntime(registry)

        skills = runtime.candidate_skills(intent="price question")
        domains = runtime.candidate_domains(intent="price question", candidate_skills=skills)

        self.assertEqual([skill.skill_id for skill in skills], ["01.001.customer_asks_price"])
        self.assertEqual(domains[0]["domain_id"], "01")

    def test_context_exposes_rules_entities_memory_workflows_and_tools(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())

        context = create_knowledge_context(
            user_message="price question",
            business_intelligence={
                "matched_skill": {"skill_id": "01.001.customer_asks_price"},
                "confidence": 0.7,
            },
            registry=registry,
        ).to_dict()

        self.assertEqual(context["required_entities"], ["product", "price"])
        self.assertEqual(context["required_memory"], ["pricing_strategy"])
        self.assertEqual(context["business_rules"], ["Price first when known."])
        self.assertEqual(context["reasoning_pattern"], "Answer clearly and protect perceived value.")
        self.assertEqual(context["workflow_candidates"][0]["workflow_id"], "sales_reply")
        self.assertEqual(context["tool_candidates"], ["none"])

    def test_diagnostics_generation(self):
        registry = SkillRegistry()
        registry.register_skill(registry_skill())

        diagnostics = create_knowledge_context(
            user_message="price question",
            registry=registry,
        ).diagnostics

        self.assertEqual(diagnostics["knowledge_context_version"], KNOWLEDGE_CONTEXT_VERSION)
        self.assertEqual(diagnostics["candidate_domain_count"], 1)
        self.assertEqual(diagnostics["candidate_skill_count"], 1)
        self.assertEqual(diagnostics["knowledge_runtime_source"], KNOWLEDGE_RUNTIME_SOURCE)
        self.assertEqual(diagnostics["runtime_mode"], "diagnostics_only")

    def test_compatible_with_existing_registry(self):
        runtime = BusinessKnowledgeRuntime(create_registry())

        context = runtime.create_context(
            user_message="price",
            business_intelligence={
                "matched_skill": {"skill_id": "01.001.customer_asks_price", "business_domain": "01 Sales"},
                "matched_domain": "01 Sales",
            },
        )

        self.assertGreaterEqual(len(context.candidate_domains), 1)
        self.assertGreaterEqual(len(context.candidate_skills), 1)
        self.assertEqual(context.selected_skill, "01.001.customer_asks_price")

    def test_task_router_adds_runtime_diagnostics_without_planner_migration(self):
        route = build_task_route({}, "price?")
        diagnostics = developer_diagnostics(route)

        self.assertIn("knowledge_context", route)
        self.assertIn("business_knowledge", diagnostics)
        self.assertTrue(diagnostics["knowledge_context_created"])
        self.assertEqual(diagnostics["knowledge_context_version"], KNOWLEDGE_CONTEXT_VERSION)
        self.assertEqual(diagnostics["knowledge_runtime_source"], KNOWLEDGE_RUNTIME_SOURCE)
        self.assertEqual(route["planner_output"], diagnostics["Planner Output"])
        self.assertTrue(route["planner_output"]["task_type"])
        self.assertNotEqual(route["planner_output"]["next_step"], "business_knowledge_runtime")


if __name__ == "__main__":
    unittest.main()
