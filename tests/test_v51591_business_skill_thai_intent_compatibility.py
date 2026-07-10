import copy
import dataclasses
import unittest

from brain.business_skill import CONTRACTED, LIMITED_ACTIVE, SHADOW_AVAILABLE, STABLE, UNIT_TESTED
from brain.business_skill_candidate_matcher import (
    BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION,
    match_business_skill_candidates,
)
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry


CHANGE_MESSAGE = "เดือนก่อนต้นทุน 20,000 บาท เดือนนี้ 24,000 บาท ต้นทุนเปลี่ยนไปเท่าไร"
PER_UNIT_MESSAGE = "ต้นทุนรวม 1,000 บาท ผลิตได้ 100 ชิ้น ต้นทุนต่อชิ้นเท่าไร"
CHANGE_SKILL_ID = "cost.change_analysis.v1"
PER_UNIT_SKILL_ID = "cost.per_unit_calculation.v1"


class V51591BusinessSkillThaiIntentCompatibilityTests(unittest.TestCase):
    def candidates(self, message):
        return match_business_skill_candidates(message, limit=None)

    def test_exact_required_thai_phrases_identify_intended_cost_skills(self):
        cases = ((CHANGE_MESSAGE, CHANGE_SKILL_ID), (PER_UNIT_MESSAGE, PER_UNIT_SKILL_ID))
        for message, expected in cases:
            with self.subTest(expected=expected):
                candidates = self.candidates(message)
                self.assertTrue(candidates)
                self.assertEqual(candidates[0]["skill_id"], expected)

    def test_punctuation_and_outer_spacing_variants_are_deterministic(self):
        cases = (
            (f"  {CHANGE_MESSAGE}???  ", CHANGE_SKILL_ID),
            (f"...{PER_UNIT_MESSAGE}!!!", PER_UNIT_SKILL_ID),
        )
        for message, expected in cases:
            with self.subTest(expected=expected):
                first = self.candidates(message)
                second = self.candidates(message)
                self.assertEqual(first, second)
                self.assertEqual(first[0]["skill_id"], expected)

    def test_cost_phrases_do_not_cross_match(self):
        change_ids = tuple(item["skill_id"] for item in self.candidates("ต้นทุนเปลี่ยนไปเท่าไร"))
        per_unit_ids = tuple(item["skill_id"] for item in self.candidates("ต้นทุนต่อชิ้นเท่าไร"))
        self.assertIn(CHANGE_SKILL_ID, change_ids)
        self.assertNotIn(PER_UNIT_SKILL_ID, change_ids)
        self.assertIn(PER_UNIT_SKILL_ID, per_unit_ids)
        self.assertNotIn(CHANGE_SKILL_ID, per_unit_ids)

    def test_unrelated_thai_cost_messages_do_not_become_false_positives(self):
        for message in ("ต้นทุนคืออะไร", "วันนี้ซื้อวัตถุดิบ", "ช่วยดูค่าใช้จ่ายให้หน่อย"):
            with self.subTest(message=message):
                self.assertEqual(self.candidates(message), [])

    def test_historical_context_is_not_an_input(self):
        historical_context = CHANGE_MESSAGE
        self.assertTrue(self.candidates(historical_context))
        self.assertEqual(self.candidates("ทำต่อได้เลย"), [])

    def test_existing_english_and_canonical_thai_fixtures_still_match(self):
        cases = (
            ("my cost increased this month", CHANGE_SKILL_ID),
            ("please calculate cost per unit", PER_UNIT_SKILL_ID),
            ("ต้นทุนเพิ่มจาก 30 เป็น 40 บาท กระทบยังไง", CHANGE_SKILL_ID),
            ("ช่วยคิดต้นทุนต่อหน่วยให้หน่อย", PER_UNIT_SKILL_ID),
        )
        for message, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(self.candidates(message)[0]["skill_id"], expected)

    def test_candidate_order_confidence_and_inputs_are_deterministic_and_safe(self):
        message = CHANGE_MESSAGE
        registry = list(get_business_skill_registry())
        before = copy.deepcopy((message, registry))
        first = match_business_skill_candidates(message, registry, limit=None)
        second = match_business_skill_candidates(message, registry, limit=None)
        self.assertEqual(first, second)
        self.assertEqual((message, registry), before)
        self.assertEqual(tuple(item["candidate_rank"] for item in first), tuple(range(1, len(first) + 1)))
        self.assertEqual(first[0]["candidate_confidence"], 0.5833)

    def test_only_intent_patterns_changed_in_the_two_cost_contracts(self):
        registry = get_business_skill_registry()
        additions = {
            CHANGE_SKILL_ID: "ต้นทุนเปลี่ยนไปเท่าไร",
            PER_UNIT_SKILL_ID: "ต้นทุนต่อชิ้น",
        }
        for skill in registry:
            if skill.skill_id not in additions:
                continue
            old_patterns = tuple(item for item in skill.intent_patterns if item != additions[skill.skill_id])
            baseline = dataclasses.replace(skill, intent_patterns=old_patterns)
            changed = tuple(
                field.name for field in dataclasses.fields(skill)
                if getattr(skill, field.name) != getattr(baseline, field.name)
            )
            self.assertEqual(changed, ("intent_patterns",))

    def test_version_lifecycle_and_candidate_authority_boundaries_are_unchanged(self):
        self.assertEqual(BUSINESS_SKILL_REGISTRY_VERSION, "5.15.9.1")
        self.assertEqual(BUSINESS_SKILL_CANDIDATE_MATCHER_VERSION, "5.15.3")
        registry = get_business_skill_registry()
        self.assertEqual(sum(item.active_status == SHADOW_AVAILABLE for item in registry), 2)
        self.assertEqual(sum(item.active_status == CONTRACTED for item in registry), 8)
        self.assertEqual(sum(item.active_status == UNIT_TESTED for item in registry), 0)
        self.assertEqual(sum(item.active_status == LIMITED_ACTIVE for item in registry), 0)
        self.assertEqual(sum(item.active_status == STABLE for item in registry), 0)
        for candidate in self.candidates(CHANGE_MESSAGE) + self.candidates(PER_UNIT_MESSAGE):
            self.assertTrue(candidate["candidate_shadow_mode"])
            self.assertFalse(candidate["candidate_selected"])
            self.assertFalse(candidate["candidate_authorized"])
            self.assertIsNone(candidate["candidate_reasoning_ready"])
            self.assertNotIn("response", candidate)
            self.assertNotIn("answer", candidate)


if __name__ == "__main__":
    unittest.main()
