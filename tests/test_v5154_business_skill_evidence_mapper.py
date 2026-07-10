import copy
import unittest

from brain.business_skill import CONTRACTED, BusinessSkill, RequiredEvidence, create_cost_change_analysis_skill
from brain.business_skill_candidate_matcher import score_business_skill_candidate
from brain.business_skill_evidence_mapper import (
    ASSUMABLE,
    CONFIRMATION_REQUIRED,
    INVALID,
    LOW_CONFIDENCE,
    MISSING,
    OPTIONAL_MISSING,
    PRESENT,
    STALE,
    build_business_skill_evidence_diagnostics,
    map_business_skill_evidence,
    map_candidate_skill_evidence,
    normalize_available_evidence,
)
from brain.business_skill_registry import get_business_skill_registry


def skill_with(required=(), optional=()):
    return BusinessSkill(
        skill_id="test.evidence.v1", skill_version="1", skill_name="Evidence Test",
        business_domain="COST", intent_patterns=("test",), required_evidence=tuple(required),
        optional_evidence=tuple(optional), active_status=CONTRACTED,
    )


class BusinessSkillEvidenceMapperTests(unittest.TestCase):
    def test_empty_and_complete_cost_evidence(self):
        skill = create_cost_change_analysis_skill()
        empty = map_business_skill_evidence(skill, {})
        self.assertEqual(empty["missing_required_evidence"], ["previous_cost", "current_cost"])
        self.assertFalse(empty["evidence_ready"])
        complete = map_business_skill_evidence(skill, {"previous_cost": 30, "current_cost": 40})
        self.assertTrue(complete["evidence_ready"])
        self.assertEqual(complete["present_required_evidence"], ["previous_cost", "current_cost"])

    def test_one_missing_blocks_and_zero_is_present(self):
        result = map_business_skill_evidence(create_cost_change_analysis_skill(), {"previous_cost": 0})
        self.assertEqual(result["present_required_evidence"], ["previous_cost"])
        self.assertEqual(result["missing_required_evidence"], ["current_cost"])
        self.assertFalse(result["evidence_ready"])

    def test_false_is_present_for_boolean_and_empty_values_are_missing(self):
        boolean_skill = skill_with((RequiredEvidence("flag", "boolean"),))
        self.assertTrue(map_business_skill_evidence(boolean_skill, {"flag": False})["evidence_ready"])
        for value in (None, "", "  ", [], (), set(), {}):
            self.assertEqual(map_business_skill_evidence(boolean_skill, {"flag": value})["evidence_mappings"][0]["mapping_status"], MISSING)

    def test_normalization_defaults_enrichment_invalid_confidence_and_no_mutation(self):
        supplied = {"raw": 4, "rich": {"value": 5, "confidence": "bad", "source": "current_turn", "freshness": "recent", "user_confirmed": True, "ignored": 9}}
        original = copy.deepcopy(supplied)
        normalized = normalize_available_evidence(supplied)
        self.assertEqual(normalized["raw"]["confidence"], 1.0)
        self.assertEqual(normalized["raw"]["source"], "explicit_input")
        self.assertEqual(normalized["raw"]["freshness"], "current")
        self.assertFalse(normalized["raw"]["user_confirmed"])
        self.assertEqual(normalized["rich"]["confidence"], 0.0)
        self.assertTrue(normalized["rich"]["validation_errors"])
        self.assertEqual(supplied, original)

    def test_confidence_and_freshness_quality(self):
        contract = RequiredEvidence("amount", "number", freshness="current_or_recent", confidence_required=.8)
        skill = skill_with((contract,))
        low = map_business_skill_evidence(skill, {"amount": {"value": 2, "confidence": .7}})
        self.assertEqual(low["evidence_mappings"][0]["mapping_status"], LOW_CONFIDENCE)
        self.assertFalse(low["evidence_ready"])
        recent = map_business_skill_evidence(skill, {"amount": {"value": 2, "freshness": "recent"}})
        self.assertEqual(recent["evidence_mappings"][0]["mapping_status"], PRESENT)
        for freshness in ("stale", "unknown"):
            result = map_business_skill_evidence(skill, {"amount": {"value": 2, "freshness": freshness}})
            self.assertEqual(result["evidence_mappings"][0]["mapping_status"], STALE)

    def test_conservative_types(self):
        cases = [
            ("number", 1, PRESENT), ("number", 1.2, PRESENT), ("number", True, INVALID),
            ("integer", 1, PRESENT), ("integer", 1.2, INVALID), ("integer", False, INVALID),
            ("text", "yes", PRESENT), ("text", "", MISSING),
        ]
        for field_type, value, status in cases:
            with self.subTest(field_type=field_type, value=value):
                result = map_business_skill_evidence(skill_with((RequiredEvidence("x", field_type),)), {"x": value})
                self.assertEqual(result["evidence_mappings"][0]["mapping_status"], status)

    def test_optional_missing_and_invalid_are_non_blocking(self):
        skill = skill_with((RequiredEvidence("x", "number"),), (RequiredEvidence("note", "number", required=False),))
        missing = map_business_skill_evidence(skill, {"x": 1})
        self.assertEqual(missing["evidence_mappings"][1]["mapping_status"], OPTIONAL_MISSING)
        self.assertTrue(missing["evidence_ready"])
        invalid = map_business_skill_evidence(skill, {"x": 1, "note": "wrong"})
        self.assertEqual(invalid["evidence_mappings"][1]["mapping_status"], INVALID)
        self.assertFalse(invalid["evidence_mappings"][1]["blocking"])
        self.assertTrue(invalid["evidence_ready"])

    def test_assumptions_sensitive_and_confirmation(self):
        plain = RequiredEvidence("x", "number", can_assume=True, assumption_default=1)
        result = map_business_skill_evidence(skill_with((plain,)), {})
        self.assertEqual(result["evidence_mappings"][0]["mapping_status"], ASSUMABLE)
        self.assertTrue(result["evidence_mappings"][0]["assumed"])
        sensitive = RequiredEvidence("x", "number", can_assume=True, assumption_default=1, sensitive=True)
        self.assertEqual(map_business_skill_evidence(skill_with((sensitive,)), {})["evidence_mappings"][0]["mapping_status"], MISSING)
        confirm = RequiredEvidence("x", "number", user_confirmation_required=True)
        self.assertEqual(map_business_skill_evidence(skill_with((confirm,)), {"x": 1})["evidence_mappings"][0]["mapping_status"], CONFIRMATION_REQUIRED)
        confirmed = {"x": {"value": 1, "user_confirmed": True}}
        self.assertTrue(map_business_skill_evidence(skill_with((confirm,)), confirmed)["evidence_ready"])

    def test_readiness_is_always_shadow_only(self):
        result = map_business_skill_evidence(create_cost_change_analysis_skill(), {"previous_cost": 30, "current_cost": 40})
        self.assertTrue(result["evidence_ready"])
        self.assertTrue(result["evidence_shadow_mode"])
        self.assertFalse(result["evidence_selected"])
        self.assertFalse(result["evidence_authorized"])
        self.assertFalse(result["evidence_executed"])

    def test_candidate_bridge_exact_id_no_mutation_and_no_confidence_reuse(self):
        skill = create_cost_change_analysis_skill()
        candidate = score_business_skill_candidate("cost changed", skill)
        original = copy.deepcopy(candidate)
        result = map_candidate_skill_evidence(candidate, {"previous_cost": 30, "current_cost": 40})
        self.assertTrue(result["candidate_mapped"])
        self.assertEqual(candidate, original)
        self.assertEqual(result["evidence_confidence_floor"], 1.0)
        self.assertNotEqual(result["evidence_confidence_floor"], candidate["candidate_confidence"])
        unknown = map_candidate_skill_evidence({"skill_id": "cost.change_analysis.v1.extra"}, {})
        self.assertFalse(unknown["candidate_mapped"])
        self.assertFalse(unknown["evidence_ready"])

    def test_diagnostics_redact_sensitive_values(self):
        skill = skill_with((RequiredEvidence("secret", "text", sensitive=True),))
        diagnostics = build_business_skill_evidence_diagnostics(skill, {"secret": "private"})
        self.assertEqual(diagnostics["evidence_mappings"][0]["observed_value"], "[REDACTED]")
        self.assertNotIn("private", repr(diagnostics))

    def test_current_lifecycle_progression_does_not_change_evidence_boundary(self):
        registry = get_business_skill_registry()
        self.assertEqual(len(registry), 10)
        self.assertEqual(sum(skill.active_status == CONTRACTED for skill in registry), 8)
        self.assertEqual(sum(skill.active_status == "UNIT_TESTED" for skill in registry), 2)


if __name__ == "__main__":
    unittest.main()
