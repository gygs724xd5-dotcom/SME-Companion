import tempfile
import unittest
from pathlib import Path

from brain.skill_markdown_parser import parse_skill_markdown, parse_skill_markdown_text
from brain.skill_schema_validator import validate_skill_schema


class V591SkillMarkdownParserTest(unittest.TestCase):
    def test_valid_front_matter_and_thai_body_parse_and_preserve_body(self):
        doc = parse_skill_markdown("business_knowledge/canonical_skills/analyze_operating_capacity.md")
        self.assertEqual(doc.parse_status, "PARSED")
        self.assertEqual(doc.metadata["skill_id"], "analyze_operating_capacity")
        self.assertIn("Analyze Operating Capacity", doc.raw_body)

    def test_missing_front_matter_is_legacy_not_crash(self):
        doc = parse_skill_markdown_text("# Legacy\n\nภาษาไทย")
        validation = validate_skill_schema(doc)
        self.assertEqual(doc.parse_status, "LEGACY_NO_FRONT_MATTER")
        self.assertEqual(validation["validation_status"], "LEGACY_COMPATIBLE")
        self.assertIn("ภาษาไทย", doc.raw_body)

    def test_invalid_yaml_is_isolated(self):
        doc = parse_skill_markdown_text("---\nskill_id: [bad\n---\n# Body")
        self.assertEqual(doc.parse_status, "INVALID_FRONT_MATTER")
        self.assertTrue(doc.parse_issues)

    def test_schema_rejects_primary_secondary_overlap_and_missing_skill_id(self):
        text = """---
display_name: Bad
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: operations
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - OPERATING_CAPACITY
    secondary:
      - OPERATING_CAPACITY
  metrics:
    input:
      - output_quantity
    derived: []
    context: []
  evidence:
    required:
      - output_quantity
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
"""
        validation = validate_skill_schema(parse_skill_markdown_text(text))
        codes = {item["code"] for item in validation["validation_issues"]}
        self.assertIn("MISSING_REQUIRED_FIELD", codes)
        self.assertIn("PRIMARY_SECONDARY_OVERLAP", codes)


if __name__ == "__main__":
    unittest.main()
