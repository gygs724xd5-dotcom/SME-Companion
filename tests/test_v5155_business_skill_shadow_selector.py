import ast
import copy
import unittest
from dataclasses import replace
from pathlib import Path

from brain.business_skill import CONTRACTED, SHADOW_AVAILABLE, UNIT_TESTED
from brain.business_skill_candidate_matcher import score_business_skill_candidate
from brain.business_skill_evidence_mapper import map_business_skill_evidence
from brain.business_skill_registry import get_business_skill_registry
from brain.business_skill_shadow_selector import (
    AMBIGUOUS_CANDIDATES,
    BELOW_CONFIDENCE_THRESHOLD,
    EVIDENCE_MISSING,
    EVIDENCE_NOT_READY,
    INVALID_CANDIDATE,
    LIFECYCLE_INELIGIBLE,
    NO_CANDIDATES,
    SHADOW_SELECTED,
    UNKNOWN_SKILL,
    build_business_skill_shadow_selection_diagnostics,
    evaluate_shadow_candidate_eligibility,
    select_shadow_business_skill,
)


class BusinessSkillShadowSelectorTests(unittest.TestCase):
    def setUp(self):
        base = get_business_skill_registry()[0]
        self.skill = replace(base, active_status=SHADOW_AVAILABLE)
        self.registry = (self.skill,)
        self.candidate = score_business_skill_candidate("cost increased", self.skill)
        self.candidate["candidate_rank"] = 1
        self.evidence = map_business_skill_evidence(
            self.skill, {"previous_cost": 30, "current_cost": 40}
        )

    def decision(self, candidates=None, evidence=None, **kwargs):
        return select_shadow_business_skill(
            [self.candidate] if candidates is None else candidates,
            [self.evidence] if evidence is None else evidence,
            registry=self.registry,
            **kwargs,
        )

    def test_empty_and_malformed_candidates_are_safe(self):
        self.assertEqual(self.decision(candidates=[])["selection_status"], NO_CANDIDATES)
        result = self.decision(candidates=[None])
        self.assertEqual(result["selection_status"], INVALID_CANDIDATE)
        self.assertFalse(result["shadow_selected"])

    def test_unknown_and_lifecycle_mismatch_are_rejected(self):
        unknown = {**self.candidate, "skill_id": "unknown.skill.v1"}
        self.assertEqual(self.decision(candidates=[unknown])["selection_status"], UNKNOWN_SKILL)
        mismatch = {**self.candidate, "active_status": CONTRACTED}
        self.assertEqual(self.decision(candidates=[mismatch])["selection_status"], LIFECYCLE_INELIGIBLE)

    def test_contracted_real_registry_and_unit_tested_are_ineligible(self):
        real = get_business_skill_registry()[0]
        candidate = score_business_skill_candidate("cost increased", real)
        evidence = map_business_skill_evidence(real, {"previous_cost": 30, "current_cost": 40})
        result = select_shadow_business_skill([candidate], [evidence])
        self.assertEqual(result["selection_status"], LIFECYCLE_INELIGIBLE)
        unit = replace(real, active_status=UNIT_TESTED)
        candidate = score_business_skill_candidate("cost increased", unit)
        evidence = map_business_skill_evidence(unit, {"previous_cost": 30, "current_cost": 40})
        self.assertEqual(select_shadow_business_skill([candidate], [evidence], (unit,))["selection_status"], LIFECYCLE_INELIGIBLE)

    def test_injected_shadow_available_skill_can_be_selected(self):
        result = self.decision()
        self.assertEqual(result["selection_status"], SHADOW_SELECTED)
        self.assertEqual(result["shadow_selected_skill_id"], self.skill.skill_id)

    def test_candidate_boundary_flags_are_required(self):
        for field, value in (
            ("candidate_shadow_mode", False),
            ("candidate_selected", True),
            ("candidate_authorized", True),
            ("candidate_reasoning_ready", True),
        ):
            with self.subTest(field=field):
                result = self.decision(candidates=[{**self.candidate, field: value}])
                self.assertEqual(result["selection_status"], INVALID_CANDIDATE)

    def test_candidate_confidence_validation_and_threshold(self):
        for value in (True, None, -0.1, 1.1, "0.9"):
            with self.subTest(value=value):
                result = self.decision(candidates=[{**self.candidate, "candidate_confidence": value}])
                self.assertEqual(result["selection_status"], INVALID_CANDIDATE)
        low = {**self.candidate, "candidate_confidence": 0.49}
        self.assertEqual(self.decision(candidates=[low])["selection_status"], BELOW_CONFIDENCE_THRESHOLD)

    def test_evidence_identity_missing_and_duplicate_are_rejected(self):
        self.assertEqual(self.decision(evidence=[])["selection_status"], EVIDENCE_MISSING)
        mismatch = {**self.evidence, "skill_id": "other.skill.v1"}
        self.assertEqual(self.decision(evidence={self.skill.skill_id: mismatch})["selection_status"], EVIDENCE_MISSING)
        duplicate = [self.evidence, copy.deepcopy(self.evidence)]
        self.assertEqual(self.decision(evidence=duplicate)["selection_status"], EVIDENCE_NOT_READY)

    def test_evidence_readiness_and_boundary_flags_are_required(self):
        changes = (
            ("evidence_ready", False),
            ("blocking_evidence", ["previous_cost"]),
            ("evidence_shadow_mode", False),
            ("evidence_selected", True),
            ("evidence_authorized", True),
            ("evidence_executed", True),
            ("evidence_mapping_valid", False),
        )
        for field, value in changes:
            with self.subTest(field=field):
                result = self.decision(evidence=[{**self.evidence, field: value}])
                self.assertEqual(result["selection_status"], EVIDENCE_NOT_READY)

    def test_confidence_separation_selects_and_close_or_tied_is_ambiguous(self):
        second_skill = replace(get_business_skill_registry()[1], active_status=SHADOW_AVAILABLE)
        second = score_business_skill_candidate("cost per unit", second_skill)
        second_evidence = map_business_skill_evidence(
            second_skill, {"total_cost": 100, "unit_quantity": 10}
        )
        registry = (self.skill, second_skill)
        first = {**self.candidate, "candidate_confidence": 0.9, "candidate_rank": 1}
        second = {**second, "candidate_confidence": 0.7, "candidate_rank": 2}
        result = select_shadow_business_skill([first, second], [self.evidence, second_evidence], registry)
        self.assertEqual(result["selection_status"], SHADOW_SELECTED)
        close = {**second, "candidate_confidence": 0.85}
        result = select_shadow_business_skill([first, close], [self.evidence, second_evidence], registry)
        self.assertEqual(result["selection_status"], AMBIGUOUS_CANDIDATES)
        tied_evidence = {**second_evidence, "evidence_confidence_floor": 1.0}
        tied = {**second, "candidate_confidence": 0.9}
        result = select_shadow_business_skill([first, tied], [self.evidence, tied_evidence], registry)
        self.assertEqual(result["selection_status"], AMBIGUOUS_CANDIDATES)
        self.assertEqual(result["eligible_candidate_ids"], [first["skill_id"], tied["skill_id"]])

    def test_success_preserves_all_authority_boundaries(self):
        result = self.decision()
        for field in (
            "authorized", "executed", "reasoning_executed", "response_generated",
            "follow_up_generated", "lifecycle_advanced",
        ):
            self.assertFalse(result[field])
        self.assertTrue(result["shadow_mode"])
        diagnostics = build_business_skill_shadow_selection_diagnostics(
            [self.candidate], [self.evidence], self.registry
        )
        self.assertIsNone(diagnostics["selected_skill_id_for_runtime"])
        self.assertIsNone(diagnostics["response_authority"])

    def test_inputs_are_not_mutated_and_calls_are_deterministic(self):
        candidates = [copy.deepcopy(self.candidate)]
        evidence = [copy.deepcopy(self.evidence)]
        registry = tuple(self.registry)
        before = copy.deepcopy((candidates, evidence, registry))
        first = select_shadow_business_skill(candidates, evidence, registry)
        second = select_shadow_business_skill(candidates, evidence, registry)
        self.assertEqual(first, second)
        self.assertEqual((candidates, evidence, registry), before)

    def test_real_registry_remains_exactly_ten_contracted_skills(self):
        registry = get_business_skill_registry()
        self.assertEqual(len(registry), 10)
        self.assertTrue(all(skill.active_status == CONTRACTED for skill in registry))

    def test_module_has_no_forbidden_runtime_imports(self):
        path = Path(__file__).parents[1] / "brain" / "business_skill_shadow_selector.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        forbidden = ("streamlit", "app", "memory", "workflow", "planner", "router", "llm", "business_skill_matcher")
        self.assertFalse(any(any(part in name.lower() for part in forbidden) for name in imports))


if __name__ == "__main__":
    unittest.main()
