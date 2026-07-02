import ast
from pathlib import Path
import unittest

from brain.task_router import build_task_route
from brain.workflow_lifecycle import (
    classify_completed_workflow_followup,
    completed_to_workflow_state,
)
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION


ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "brain"


WORKFLOW_MODULES = [
    BRAIN / "business_workflow_engine.py",
    BRAIN / "conversation_workflow_engine.py",
    BRAIN / "workflow_execution_runtime.py",
    BRAIN / "workflow_field_extractor.py",
    BRAIN / "workflow_lifecycle.py",
    BRAIN / "workflow_readiness.py",
    BRAIN / "workflow_registry.py",
    BRAIN / "workflow_reply_builder.py",
    BRAIN / "workflow_state_machine.py",
]

RESPONSE_MODULES = [
    BRAIN / "natural_response_engine.py",
    BRAIN / "response_cleaner.py",
    BRAIN / "response_envelope_runtime.py",
    BRAIN / "response_intelligence_engine.py",
    BRAIN / "response_mode_engine.py",
    BRAIN / "response_transformation_engine.py",
    BRAIN / "workflow_reply_builder.py",
]


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _constant_string(node: ast.AST):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _dict_keys(tree: ast.AST) -> set[str]:
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                value = _constant_string(key)
                if value:
                    keys.add(value)
    return keys


def _function_names(tree: ast.AST) -> set[str]:
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def _imports_forbidden_workflow_selectors(tree: ast.AST) -> list[str]:
    forbidden_modules = {
        "brain.planner_engine",
        "brain.business_workflow_engine",
        "brain.intent_resolver",
    }
    forbidden_from_imports = {
        "detect_workflow_intent",
        "decide_business_workflow",
        "build_execution_plan",
        "resolve_intent",
    }
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in forbidden_modules:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported = {alias.name for alias in node.names}
            if module in forbidden_modules:
                violations.append(module)
            for name in sorted(imported & forbidden_from_imports):
                violations.append(f"{module}.{name}")
    return violations


def _call_keyword_values(tree: ast.AST, function_name: str, keyword_name: str) -> list[ast.AST]:
    values = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == function_name:
            for keyword in node.keywords:
                if keyword.arg == keyword_name:
                    values.append(keyword.value)
    return values


class V525ArchitectureDoctrineTest(unittest.TestCase):
    def test_architecture_doctrine_document_is_present(self):
        doctrine = (ROOT / "docs" / "ARCHITECTURE_DOCTRINE.md").read_text(encoding="utf-8")

        for rule in [
            "Planner owns decisions.",
            "Workflow owns execution.",
            "Runtime owns state.",
            "Business Knowledge owns knowledge.",
            "Reasoning owns analysis.",
            "Response owns communication.",
        ]:
            self.assertIn(rule, doctrine)

    def test_workflow_modules_do_not_define_intent_resolution_authority(self):
        forbidden_route_keys = {"resolved_intent", "resolved_workflow", "planner_output"}
        forbidden_function_names = {"resolve_intent", "build_execution_plan"}
        violations = []

        for path in WORKFLOW_MODULES:
            tree = _tree(path)
            forbidden_keys = sorted(_dict_keys(tree) & forbidden_route_keys)
            forbidden_functions = sorted(_function_names(tree) & forbidden_function_names)
            if forbidden_keys or forbidden_functions:
                violations.append(
                    f"{path.relative_to(ROOT)} keys={forbidden_keys} functions={forbidden_functions}"
                )

        self.assertEqual([], violations)

    def test_response_modules_do_not_select_workflow(self):
        forbidden_function_names = {
            "detect_workflow_intent",
            "decide_business_workflow",
            "build_execution_plan",
            "resolve_intent",
        }
        violations = []

        for path in RESPONSE_MODULES:
            tree = _tree(path)
            forbidden_imports = _imports_forbidden_workflow_selectors(tree)
            forbidden_functions = sorted(_function_names(tree) & forbidden_function_names)
            if forbidden_imports or forbidden_functions:
                violations.append(
                    f"{path.relative_to(ROOT)} imports={forbidden_imports} functions={forbidden_functions}"
                )

        self.assertEqual([], violations)

    def test_completed_workflow_context_is_diagnostics_history_only(self):
        completed = {
            "workflow_id": WORKFLOW_CONTENT_PLAN,
            "collected_fields": {"product": "Thai tea"},
            "completed_at": "2026-07-02T00:00:00+00:00",
        }
        state = {"business_memory": {"completed_workflows": [completed]}}

        followup = classify_completed_workflow_followup(state, "cost per unit 200 baht 100 units")
        diagnostic_state = completed_to_workflow_state(completed)
        route = build_task_route(state, "cost per unit 200 baht 100 units")

        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertEqual(
            followup["workflow_transition_reason"],
            "completed workflows are diagnostics only; planner owns next workflow",
        )
        self.assertEqual(diagnostic_state["next_action"], "diagnostics_only")
        self.assertTrue(diagnostic_state["workflow_complete"])
        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertEqual(
            (route["business_workflow"].get("workflow_state") or {}).get("workflow_id"),
            WORKFLOW_COST_CALCULATION,
        )

    def test_planner_output_remains_source_for_workflow_execution(self):
        task_router_tree = _tree(BRAIN / "task_router.py")
        resolved_workflow_values = _call_keyword_values(
            task_router_tree,
            "decide_business_workflow",
            "resolved_workflow",
        )

        self.assertEqual(1, len(resolved_workflow_values))
        value = resolved_workflow_values[0]
        self.assertIsInstance(value, ast.BoolOp)
        self.assertIsInstance(value.op, ast.Or)
        first_source = value.values[0]
        self.assertIsInstance(first_source, ast.Call)
        self.assertIsInstance(first_source.func, ast.Attribute)
        self.assertIsInstance(first_source.func.value, ast.Name)
        self.assertEqual("plan", first_source.func.value.id)
        self.assertEqual("get", first_source.func.attr)
        self.assertEqual("workflow", _constant_string(first_source.args[0]))

        route = build_task_route({}, "profit price 150 cost 100")
        planner_workflow = route["planner_output"]["workflow"]
        workflow_state = route["business_workflow"].get("workflow_state") or {}

        self.assertEqual(planner_workflow, route["intent_resolution"]["resolved_workflow"])
        self.assertEqual(planner_workflow, workflow_state.get("workflow_id"))


if __name__ == "__main__":
    unittest.main()
