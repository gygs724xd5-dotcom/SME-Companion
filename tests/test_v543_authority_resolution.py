import ast
import copy
import json
import unittest
from pathlib import Path

from brain.authority_engine import build_authority_context
from brain.authority_models import (
    CUSTOMER_SERVICE_AUTHORITY,
    FINANCE_AUTHORITY,
    GENERAL_BUSINESS_AUTHORITY,
    PRICING_AUTHORITY,
    SALES_AUTHORITY,
)
from brain.authority_resolution import (
    AUTHORITY_RESOLUTION_VERSION,
    AuthorityResolution,
    resolve_authority,
)


def _candidate(authority: str, score: int, **overrides) -> dict:
    data = {
        "source": "authority_engine",
        "signal": "keyword_match",
        "authority": authority,
        "score": score,
        "matched_keywords": [authority],
    }
    data.update(overrides)
    return data


class AuthorityResolutionTest(unittest.TestCase):
    def test_highest_score_selected(self):
        resolution = resolve_authority(
            [
                _candidate(SALES_AUTHORITY, 1),
                _candidate(PRICING_AUTHORITY, 3),
                _candidate(FINANCE_AUTHORITY, 2),
            ]
        )

        self.assertIsInstance(resolution, AuthorityResolution)
        self.assertEqual(resolution.primary_authority, PRICING_AUTHORITY)
        self.assertEqual(resolution.confidence, "high")

    def test_deterministic_tie_handling(self):
        first = resolve_authority(
            [
                _candidate(SALES_AUTHORITY, 2),
                _candidate(PRICING_AUTHORITY, 2),
            ]
        ).to_dict()
        second = resolve_authority(
            [
                _candidate(PRICING_AUTHORITY, 2),
                _candidate(SALES_AUTHORITY, 2),
            ]
        ).to_dict()

        self.assertEqual(first, second)
        self.assertEqual(first["primary_authority"], GENERAL_BUSINESS_AUTHORITY)
        self.assertEqual(first["confidence"], "conflicted")
        self.assertEqual(first["secondary_authorities"], [PRICING_AUTHORITY, SALES_AUTHORITY])

    def test_conflict_recording(self):
        resolution = resolve_authority(
            [
                _candidate(PRICING_AUTHORITY, 3),
                _candidate(FINANCE_AUTHORITY, 2),
            ]
        )

        self.assertEqual(resolution.primary_authority, PRICING_AUTHORITY)
        self.assertEqual(resolution.conflicts[0]["kind"], "authority_conflict")
        self.assertEqual(
            resolution.conflicts[0]["authorities"],
            [PRICING_AUTHORITY, FINANCE_AUTHORITY],
        )

    def test_secondary_authorities_preserved(self):
        resolution = resolve_authority(
            [
                _candidate(PRICING_AUTHORITY, 4),
                _candidate(FINANCE_AUTHORITY, 2),
                _candidate(CUSTOMER_SERVICE_AUTHORITY, 1),
            ]
        )

        self.assertEqual(
            resolution.secondary_authorities,
            [FINANCE_AUTHORITY, CUSTOMER_SERVICE_AUTHORITY],
        )

    def test_fallback_to_general_business_authority(self):
        resolution = resolve_authority([])

        self.assertEqual(resolution.primary_authority, GENERAL_BUSINESS_AUTHORITY)
        self.assertEqual(resolution.confidence, "low")
        self.assertEqual(resolution.secondary_authorities, [])

    def test_unknown_authority(self):
        resolution = resolve_authority(
            [
                _candidate("unknown_authority", 99),
                _candidate(PRICING_AUTHORITY, 0),
            ]
        )

        self.assertEqual(resolution.primary_authority, GENERAL_BUSINESS_AUTHORITY)
        self.assertEqual(resolution.confidence, "low")
        self.assertTrue(resolution.resolution_path[0]["ignored"])

    def test_deterministic_output(self):
        candidates = [
            _candidate(FINANCE_AUTHORITY, 2),
            _candidate(PRICING_AUTHORITY, 4),
            _candidate(SALES_AUTHORITY, 1),
        ]

        self.assertEqual(
            resolve_authority(candidates).to_dict(),
            resolve_authority(candidates).to_dict(),
        )

    def test_json_serializable(self):
        payload = resolve_authority([_candidate(PRICING_AUTHORITY, 2)]).to_dict()
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertIn(AUTHORITY_RESOLUTION_VERSION, encoded)
        self.assertIn(PRICING_AUTHORITY, encoded)

    def test_no_workflow_dependency(self):
        source = Path("brain/authority_resolution.py").read_text(encoding="utf-8")
        parsed = ast.parse(source)
        imported_modules = []
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imported_modules.append(node.module or "")

        forbidden = ("task_router", "planner", "workflow")
        self.assertFalse(
            [
                module
                for module in imported_modules
                if any(name in module for name in forbidden)
            ]
        )

    def test_no_mutation_of_inputs(self):
        candidates = [
            _candidate(PRICING_AUTHORITY, 3, matched_keywords=["price", "margin"]),
            _candidate(FINANCE_AUTHORITY, 2, matched_keywords=["cost"]),
        ]
        original = copy.deepcopy(candidates)

        resolve_authority(candidates)

        self.assertEqual(candidates, original)

    def test_engine_uses_resolution_diagnostics_only(self):
        context = build_authority_context(
            {
                "situation_id": "situation-resolution",
                "objective": "Customer says price is too expensive",
                "known_evidence": [],
            }
        )

        diagnostics = context.authority_diagnostics
        self.assertEqual(diagnostics["authority_resolution_version"], "5.4.3")
        self.assertEqual(diagnostics["runtime_mode"], "diagnostics_only")
        self.assertFalse(diagnostics["resolution_changed_runtime"])
        self.assertFalse(diagnostics["workflow_changed"])
        self.assertFalse(diagnostics["planner_changed"])
        self.assertFalse(diagnostics["responses_changed"])
        self.assertEqual(context.primary_authority, PRICING_AUTHORITY)
        self.assertEqual(
            context.authority_resolution["authority_resolution"]["primary_authority"],
            PRICING_AUTHORITY,
        )


if __name__ == "__main__":
    unittest.main()
