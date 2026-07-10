import copy
import unittest
from dataclasses import replace

from brain.business_skill import CONTRACTED, SHADOW_AVAILABLE, UNIT_TESTED, RequiredEvidence
from brain.business_skill_registry import get_business_skill, get_business_skill_registry
from brain.business_skill_shadow_availability_qualification import (
    INVALID_SOURCE_LIFECYCLE,
    NOT_QUALIFIED,
    QUALIFIED,
    UNKNOWN_SKILL,
    UNSUPPORTED_SKILL,
    get_shadow_availability_qualification_target,
    qualify_business_skill_shadow_availability,
    qualify_business_skills_shadow_availability,
)


CASES = {
    "cost.change_analysis.v1": ("my cost increased from 30 to 40", {"previous_cost": 30, "current_cost": 40}),
    "cost.per_unit_calculation.v1": ("please calculate cost per unit", {"total_cost": 100, "unit_quantity": 10}),
}


class V5158BusinessSkillShadowAvailabilityQualificationTests(unittest.TestCase):
    def historical_registry(self):
        return tuple(replace(skill, active_status=UNIT_TESTED)
                     if skill.skill_id in CASES else skill
                     for skill in get_business_skill_registry())

    def qualify(self, skill_id, message=None, evidence=None, **kwargs):
        default_message, default_evidence = CASES[skill_id]
        registry = self.historical_registry()
        skill = next(item for item in registry if item.skill_id == skill_id)
        return qualify_business_skill_shadow_availability(
            skill, default_message if message is None else message,
            default_evidence if evidence is None else evidence, registry, **kwargs,
        )

    def test_both_cost_skills_pass_full_path_independently(self):
        for skill_id in CASES:
            with self.subTest(skill_id=skill_id):
                report = self.qualify(skill_id)
                self.assertEqual(report.qualification_status, QUALIFIED)
                self.assertTrue(report.qualified)
                self.assertEqual(report.source_lifecycle, UNIT_TESTED)
                self.assertEqual(report.evaluated_lifecycle, SHADOW_AVAILABLE)
                self.assertTrue(all((report.candidate_gate, report.evidence_gate, report.lifecycle_gate,
                                     report.confidence_gate, report.ambiguity_gate)))
                self.assertEqual(report.shadow_selection_result, "SHADOW_SELECTED")
                self.assertEqual(report.shadow_selected_skill_id, skill_id)
                self.assertTrue(report.promotion_recommended)
                self.assertEqual(report.recommended_next_status, SHADOW_AVAILABLE)

    def test_qualification_does_not_change_promoted_canonical_registry(self):
        before = get_business_skill_registry()
        for skill_id in CASES:
            self.qualify(skill_id)
        after = get_business_skill_registry()
        self.assertEqual(before, after)
        self.assertEqual(sum(s.active_status == UNIT_TESTED for s in after), 0)
        self.assertEqual(sum(s.active_status == CONTRACTED for s in after), 8)
        self.assertEqual(sum(s.active_status == SHADOW_AVAILABLE for s in after), 2)

    def test_unrelated_and_context_only_messages_do_not_match(self):
        for skill_id in CASES:
            for current in ("hello there", "thanks, that is all"):
                with self.subTest(skill_id=skill_id, current=current):
                    report = self.qualify(skill_id, message=current)
                    self.assertFalse(report.qualified)
                    self.assertFalse(report.candidate_gate)
            # Historical text is deliberately not an input to the qualification API.
            historical = CASES[skill_id][0]
            self.assertTrue(historical)
            self.assertFalse(self.qualify(skill_id, message="continue").qualified)

    def test_missing_wrong_type_and_invalid_value_block(self):
        failures = (
            ("cost.change_analysis.v1", {"current_cost": 40}),
            ("cost.change_analysis.v1", {"previous_cost": True, "current_cost": 40}),
            ("cost.per_unit_calculation.v1", {"total_cost": 100, "unit_quantity": 0}),
        )
        for skill_id, evidence in failures:
            report = self.qualify(skill_id, evidence=evidence)
            self.assertFalse(report.qualified)
            self.assertFalse(report.evidence_gate)
            self.assertIn("evidence_gate_failed", report.diagnostic_reasons)

    def test_low_evidence_confidence_and_staleness_block(self):
        for evidence in (
            {"previous_cost": {"value": 30, "confidence": .1}, "current_cost": 40},
            {"previous_cost": {"value": 30, "freshness": "stale"}, "current_cost": 40},
        ):
            self.assertFalse(self.qualify("cost.change_analysis.v1", evidence=evidence).evidence_gate)

    def test_disallowed_assumption_blocks(self):
        evidence = {"previous_cost": {"value": 30, "assumed": True}, "current_cost": 40}
        report = self.qualify("cost.change_analysis.v1", evidence=evidence)
        self.assertFalse(report.evidence_gate)
        mapping = next(x for x in report.evidence_results[0]["evidence_mappings"] if x["field_name"] == "previous_cost")
        self.assertEqual(mapping["mapping_status"], "INVALID")

    def test_required_confirmation_blocks_until_confirmed(self):
        registry = self.historical_registry()
        source = next(item for item in registry if item.skill_id == "cost.change_analysis.v1")
        contract = replace(source.required_evidence[0], user_confirmation_required=True)
        source = replace(source, required_evidence=(contract, *source.required_evidence[1:]))
        missing = qualify_business_skill_shadow_availability(
            source, CASES[source.skill_id][0], {"previous_cost": 30, "current_cost": 40}, registry
        )
        confirmed = qualify_business_skill_shadow_availability(
            source, CASES[source.skill_id][0],
            {"previous_cost": {"value": 30, "user_confirmed": True}, "current_cost": 40}, registry
        )
        self.assertFalse(missing.qualified)
        self.assertTrue(confirmed.qualified)

    def test_low_candidate_confidence_is_not_normalized_upward(self):
        report = self.qualify("cost.change_analysis.v1", minimum_candidate_confidence=.99)
        self.assertFalse(report.qualified)
        self.assertFalse(report.confidence_gate)

    def test_stronger_competitor_and_ambiguity_block_target(self):
        message = "cost increased calculate cost per unit"
        evidence = {
            "cost.change_analysis.v1": CASES["cost.change_analysis.v1"][1],
            "cost.per_unit_calculation.v1": CASES["cost.per_unit_calculation.v1"][1],
        }
        change = self.qualify("cost.change_analysis.v1", message=message, evidence=evidence)
        self.assertFalse(change.qualified)
        self.assertFalse(change.candidate_gate)
        per_unit = self.qualify("cost.per_unit_calculation.v1", message=message, evidence=evidence)
        self.assertFalse(per_unit.qualified)
        self.assertFalse(per_unit.ambiguity_gate)
        self.assertEqual(per_unit.shadow_selection_result, "AMBIGUOUS_CANDIDATES")

    def test_wrong_lifecycle_unknown_and_unsupported_are_rejected(self):
        registry = self.historical_registry()
        target = next(item for item in registry if item.skill_id == "cost.change_analysis.v1")
        wrong = replace(target, active_status=SHADOW_AVAILABLE)
        result = qualify_business_skill_shadow_availability(wrong, "cost increased", {})
        self.assertEqual(result.qualification_status, INVALID_SOURCE_LIFECYCLE)
        unknown = replace(target, skill_id="unknown.v1")
        self.assertEqual(qualify_business_skill_shadow_availability(unknown, "x", {}).qualification_status, UNKNOWN_SKILL)
        other = get_business_skill_registry()[2]
        self.assertEqual(qualify_business_skill_shadow_availability(other, "promotion", {}).qualification_status, UNSUPPORTED_SKILL)
        self.assertIsNone(get_shadow_availability_qualification_target("COST.CHANGE_ANALYSIS.V1"))

    def test_determinism_batch_order_and_mutation_safety(self):
        registry = self.historical_registry()
        skill = next(item for item in registry if item.skill_id == "cost.change_analysis.v1")
        message = CASES[skill.skill_id][0]
        evidence = copy.deepcopy(CASES[skill.skill_id][1])
        before = copy.deepcopy((skill, message, evidence, get_business_skill_registry()))
        first = qualify_business_skill_shadow_availability(skill, message, evidence)
        second = qualify_business_skill_shadow_availability(skill, message, evidence)
        self.assertEqual(first, second)
        self.assertEqual((skill, message, evidence, get_business_skill_registry()), before)
        inputs = {sid: {"current_message": msg, "evidence": ev} for sid, (msg, ev) in reversed(tuple(CASES.items()))}
        batch = qualify_business_skills_shadow_availability(inputs, registry)
        self.assertEqual(tuple(r.skill_id for r in batch.reports), tuple(CASES))
        self.assertEqual(batch.qualified_skill_ids, tuple(CASES))
        self.assertEqual(batch.lifecycle_mutations_applied, 0)

    def test_authority_boundaries_and_failure_never_recommend(self):
        success = self.qualify("cost.change_analysis.v1")
        for field in ("lifecycle_mutated", "authorized", "executed", "reasoning_executed",
                      "tools_invoked", "follow_up_generated", "response_generated", "runtime_activated"):
            self.assertFalse(getattr(success, field))
        self.assertNotIn("answer", success.__dataclass_fields__)
        self.assertNotIn("response", success.__dataclass_fields__)
        failures = (
            self.qualify("cost.change_analysis.v1", message="hello"),
            self.qualify("cost.change_analysis.v1", evidence={}),
            self.qualify("cost.change_analysis.v1", minimum_candidate_confidence=.99),
        )
        for report in failures:
            self.assertEqual(report.qualification_status, NOT_QUALIFIED)
            self.assertFalse(report.promotion_recommended)
            self.assertIsNone(report.recommended_next_status)


if __name__ == "__main__":
    unittest.main()
