import ast
import copy
import inspect
import unittest
from dataclasses import replace

import brain.business_skill_lifecycle_qualification as qualification_module
from brain.business_skill import CONTRACTED, COST, SHADOW_AVAILABLE, UNIT_TESTED, BusinessSkill
from brain.business_skill_candidate_matcher import match_business_skill_candidates, top_business_skill_candidate
from brain.business_skill_evidence_mapper import map_business_skill_evidence
from brain.business_skill_lifecycle_qualification import (
    INCOMPLETE_QUALIFICATION_EVIDENCE,
    INVALID_CURRENT_STATUS,
    INVALID_SKILL_CONTRACT,
    OUT_OF_SCOPE,
    QUALIFICATION_FAILED,
    QUALIFICATION_PASSED,
    QUALIFICATION_TARGET_SKILL_IDS,
    UNKNOWN_SKILL,
    build_business_skill_qualification_diagnostics,
    evaluate_unit_test_qualification,
    qualify_seed_business_skills,
)
from brain.business_skill_registry import EXPECTED_SEED_SKILL_IDS, get_business_skill_registry
from brain.business_skill_shadow_selector import LIFECYCLE_INELIGIBLE, select_shadow_business_skill


def complete_qualification_evidence():
    return {
        "declared_test_files": ["tests/test_v5156_business_skill_lifecycle_qualification.py"],
        "targeted_tests_passed": True,
        "candidate_positive_cases_passed": True,
        "candidate_negative_cases_passed": True,
        "evidence_complete_cases_passed": True,
        "evidence_missing_cases_passed": True,
        "evidence_invalid_cases_passed": True,
        "determinism_cases_passed": True,
        "mutation_safety_cases_passed": True,
        "boundary_cases_passed": True,
        "regression_tests_passed": True,
        "full_suite_passed": True,
        "full_suite_test_count": 1,
        "py_compile_passed": True,
        "diff_check_passed": True,
    }


class V5156BusinessSkillLifecycleQualificationTests(unittest.TestCase):
    def setUp(self):
        self.registry = get_business_skill_registry()
        self.by_id = {skill.skill_id: skill for skill in self.registry}

    def candidate_matrix(self, skill_id):
        other_id = QUALIFICATION_TARGET_SKILL_IDS[1 - QUALIFICATION_TARGET_SKILL_IDS.index(skill_id)]
        skill = self.by_id[skill_id]
        english = "my cost increased from 30 to 40" if skill_id.endswith("change_analysis.v1") else "please calculate cost per unit"
        competing = "please calculate cost per unit" if skill_id.endswith("change_analysis.v1") else "my cost increased from 30 to 40"
        for message in (english, skill.example_questions[0]):
            candidate = top_business_skill_candidate(message, self.registry)
            self.assertEqual(candidate["skill_id"], skill_id)
            self.assertFalse(candidate["candidate_selected"])
            self.assertFalse(candidate["candidate_authorized"])
            self.assertIsNone(candidate["candidate_reasoning_ready"])
        self.assertEqual(match_business_skill_candidates("hello", self.registry), [])
        competing_candidates = match_business_skill_candidates(competing, self.registry, limit=None)
        ranks = {item["skill_id"]: item["candidate_rank"] for item in competing_candidates}
        self.assertIn(other_id, ranks)
        self.assertTrue(skill_id not in ranks or ranks[skill_id] > ranks[other_id])

    def evidence_matrix(self, skill_id):
        skill = self.by_id[skill_id]
        if skill_id.endswith("change_analysis.v1"):
            complete = {"previous_cost": 30, "current_cost": 40}
            zero = {"previous_cost": 30, "current_cost": 0}
            missing = ({"current_cost": 40}, {"previous_cost": 30})
            invalid = (
                {"previous_cost": True, "current_cost": 40},
                {"previous_cost": "not-a-number", "current_cost": 40},
                {"previous_cost": {"value": 30, "freshness": "stale"}, "current_cost": 40},
                {"previous_cost": {"value": 30, "confidence": 0.1}, "current_cost": 40},
            )
            self.assertTrue(map_business_skill_evidence(skill, zero)["evidence_ready"])
        else:
            complete = {"total_cost": 100, "unit_quantity": 10}
            missing = ({"unit_quantity": 10}, {"total_cost": 100})
            invalid = (
                {"total_cost": 100, "unit_quantity": 0},
                {"total_cost": 100, "unit_quantity": True},
                {"total_cost": {"value": 100, "freshness": "stale"}, "unit_quantity": 10},
                {"total_cost": 100, "unit_quantity": {"value": 10, "confidence": 0.1}},
            )
        ready = map_business_skill_evidence(skill, complete)
        self.assertTrue(ready["evidence_ready"])
        self.assertFalse(ready["evidence_selected"])
        self.assertFalse(ready["evidence_authorized"])
        self.assertFalse(ready["evidence_executed"])
        for case in missing + invalid:
            self.assertFalse(map_business_skill_evidence(skill, case)["evidence_ready"])
        candidate = top_business_skill_candidate(skill.example_questions[0], self.registry)
        decision = select_shadow_business_skill([candidate], [ready], self.registry)
        self.assertEqual(decision["selection_status"], LIFECYCLE_INELIGIBLE)
        self.assertFalse(decision["shadow_selected"])
        self.assertFalse(decision["authorized"])
        self.assertFalse(decision["executed"])
        self.assertFalse(decision["reasoning_executed"])
        self.assertFalse(decision["follow_up_generated"])
        self.assertFalse(decision["response_generated"])

    def test_actual_acceptance_matrix_for_both_cost_skills(self):
        for skill_id in QUALIFICATION_TARGET_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                self.candidate_matrix(skill_id)
                self.evidence_matrix(skill_id)

    def test_complete_evidence_qualifies_both_cost_skills_without_authority(self):
        for skill_id in QUALIFICATION_TARGET_SKILL_IDS:
            evidence = complete_qualification_evidence()
            original = copy.deepcopy(evidence)
            first = evaluate_unit_test_qualification(self.by_id[skill_id], evidence, self.registry)
            second = evaluate_unit_test_qualification(self.by_id[skill_id], evidence, self.registry)
            self.assertEqual(first, second)
            self.assertEqual(evidence, original)
            self.assertEqual(first["qualification_status"], QUALIFICATION_PASSED)
            self.assertTrue(first["qualification_passed"])
            self.assertEqual(first["current_status"], CONTRACTED)
            self.assertEqual(first["recommended_next_status"], UNIT_TESTED)
            self.assertNotEqual(first["recommended_next_status"], SHADOW_AVAILABLE)
            for boundary in ("lifecycle_mutated", "shadow_available", "shadow_selected", "authorized", "executed", "response_generated"):
                self.assertFalse(first[boundary])

    def test_missing_evidence_and_strict_types_fail(self):
        skill = self.by_id[QUALIFICATION_TARGET_SKILL_IDS[0]]
        missing = evaluate_unit_test_qualification(skill, {}, self.registry)
        self.assertEqual(missing["qualification_status"], INCOMPLETE_QUALIFICATION_EVIDENCE)
        self.assertTrue(missing["missing_qualification_evidence"])
        for field, value in (("targeted_tests_passed", "true"), ("full_suite_test_count", True)):
            evidence = complete_qualification_evidence()
            evidence[field] = value
            result = evaluate_unit_test_qualification(skill, evidence, self.registry)
            self.assertEqual(result["qualification_status"], QUALIFICATION_FAILED)
            self.assertFalse(result["qualification_passed"])

    def test_each_failed_boolean_gate_prevents_qualification(self):
        skill = self.by_id[QUALIFICATION_TARGET_SKILL_IDS[0]]
        for field in [name for name in complete_qualification_evidence() if name.endswith("_passed")]:
            evidence = complete_qualification_evidence()
            evidence[field] = False
            with self.subTest(field=field):
                self.assertFalse(evaluate_unit_test_qualification(skill, evidence, self.registry)["qualification_passed"])

    def test_unknown_out_of_scope_invalid_contract_and_status_are_safe(self):
        evidence = complete_qualification_evidence()
        unknown = evaluate_unit_test_qualification({"skill_id": "unknown.v1"}, evidence, self.registry)
        self.assertEqual(unknown["qualification_status"], UNKNOWN_SKILL)
        other = self.registry[2]
        self.assertEqual(evaluate_unit_test_qualification(other, evidence, self.registry)["qualification_status"], OUT_OF_SCOPE)
        target = self.by_id[QUALIFICATION_TARGET_SKILL_IDS[0]]
        invalid = replace(target, business_domain="NOT_CANONICAL")
        self.assertEqual(evaluate_unit_test_qualification(invalid, evidence, self.registry)["qualification_status"], INVALID_SKILL_CONTRACT)
        wrong_status = replace(target, active_status=UNIT_TESTED)
        self.assertEqual(evaluate_unit_test_qualification(wrong_status, evidence, (wrong_status,))["qualification_status"], INVALID_CURRENT_STATUS)

    def test_batch_evaluates_exactly_two_and_only_proposes_status_counts(self):
        evidence = {skill_id: complete_qualification_evidence() for skill_id in QUALIFICATION_TARGET_SKILL_IDS}
        before = tuple(skill.active_status for skill in self.registry)
        batch = qualify_seed_business_skills(evidence, self.registry)
        self.assertEqual(batch["evaluated_skill_ids"], list(QUALIFICATION_TARGET_SKILL_IDS))
        self.assertEqual(batch["passed_qualification_skill_ids"], list(QUALIFICATION_TARGET_SKILL_IDS))
        self.assertEqual(batch["failed_qualification_skill_ids"], [])
        self.assertEqual(set(batch["out_of_scope_skill_ids"]), set(EXPECTED_SEED_SKILL_IDS) - set(QUALIFICATION_TARGET_SKILL_IDS))
        self.assertEqual(batch["recommended_unit_tested_skill_ids"], list(QUALIFICATION_TARGET_SKILL_IDS))
        self.assertEqual(batch["current_registry_status_counts"], {CONTRACTED: 10})
        self.assertEqual(batch["proposed_status_counts"], {CONTRACTED: 8, UNIT_TESTED: 2})
        self.assertEqual(batch["lifecycle_mutations_applied"], 0)
        self.assertTrue(batch["all_registry_skills_unchanged"])
        self.assertEqual(tuple(skill.active_status for skill in self.registry), before)
        self.assertTrue(all(skill.active_status == CONTRACTED for skill in get_business_skill_registry()))

    def test_diagnostics_are_safe_and_contain_no_evidence_values(self):
        evidence = {skill_id: complete_qualification_evidence() for skill_id in QUALIFICATION_TARGET_SKILL_IDS}
        evidence[QUALIFICATION_TARGET_SKILL_IDS[0]]["unspecified_sensitive_value"] = "SECRET-123"
        diagnostics = build_business_skill_qualification_diagnostics(evidence, self.registry)
        self.assertNotIn("SECRET-123", repr(diagnostics))
        self.assertEqual(diagnostics["recommended_promotion_ids"], list(QUALIFICATION_TARGET_SKILL_IDS))
        self.assertEqual(diagnostics["shadow_eligible_ids"], [])
        self.assertEqual(diagnostics["lifecycle_mutation_count"], 0)
        self.assertIsNone(diagnostics["selected_skill_id"])
        self.assertIsNone(diagnostics["authorized_skill_id"])
        self.assertIsNone(diagnostics["executed_skill_id"])

    def test_module_imports_only_allowed_pure_layers(self):
        tree = ast.parse(inspect.getsource(qualification_module))
        imports = {alias.name.casefold() for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports.update(node.module.casefold() for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
        forbidden = ("streamlit", "app", "memory", "workflow", "planner", "router", "response_authority", "llm", "subprocess", "pathlib", "os", "brain.business_skill_matcher")
        self.assertFalse(any(name == token or name.startswith(token + ".") for name in imports for token in forbidden))


if __name__ == "__main__":
    unittest.main()
