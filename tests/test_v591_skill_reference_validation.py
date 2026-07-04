import unittest

from brain.skill_authority_validator import validate_skill_authority
from brain.skill_markdown_parser import parse_skill_markdown, parse_skill_markdown_text
from brain.skill_reference_validator import resolve_alias, validate_skill_references


class V591SkillReferenceValidationTest(unittest.TestCase):
    def test_valid_reference_passes(self):
        doc = parse_skill_markdown("business_knowledge/canonical_skills/analyze_operating_capacity.md")
        result = validate_skill_references(doc)
        self.assertTrue(result["canonical_reference_valid"])

    def test_unknown_reference_fails_and_alias_must_be_approved(self):
        doc = parse_skill_markdown_text("""---
skill_id: bad
display_name: Bad
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: x
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - NOT_REAL
  metrics:
    input:
      - not_real_metric
  evidence:
    required:
      - not_real_metric
authority:
  allowed:
    - procedural_analysis
  forbidden: []
compatibility:
  mode: strict_canonical
review:
  status: approved
---
# Bad
""")
        result = validate_skill_references(doc)
        codes = {item["code"] for item in result["validation_issues"]}
        self.assertIn("UNKNOWN_KNOWLEDGE_ID", codes)
        self.assertIn("UNKNOWN_METRIC_ID", codes)
        self.assertEqual(resolve_alias("old", [{"legacy_id": "old", "canonical_id": "new", "approved": False}]), ("old", False))

    def test_authority_overreach_is_blocked(self):
        result = validate_skill_authority({"authority": {"allowed": ["procedural_analysis", "final_judgment"], "forbidden": ["final_judgment"]}})
        codes = {item["code"] for item in result["validation_issues"]}
        self.assertIn("FINAL_JUDGMENT_NOT_ALLOWED", codes)
        self.assertIn("ALLOWED_FORBIDDEN_CONFLICT", codes)
        self.assertFalse(result["authority_scope_valid"])


if __name__ == "__main__":
    unittest.main()
