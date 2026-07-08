import copy
import json
import unittest

from brain.diagnostics_dashboard import (
    ACCEPTANCE_GUARDED,
    CONTRACT_COMPLETE,
    HELPER_COMPLETE,
    RUNTIME_AUDITED,
    SHADOW_WIRED,
    build_brain_diagnostics_snapshot,
)


def _complete_layer_statuses():
    return [
        {
            "layer_name": "Response Authority",
            "contract_status": "complete",
            "helper_status": "complete",
            "shadow_wiring_status": "complete",
            "acceptance_status": "complete",
            "audit_status": "complete",
        },
        {
            "layer_name": "Evidence Gap",
            "contract_status": "complete",
            "helper_status": "complete",
            "shadow_wiring_status": "complete",
            "acceptance_status": "complete",
            "audit_status": "complete",
        },
        {
            "layer_name": "Business Situation",
            "contract_status": "complete",
            "helper_status": "complete",
            "shadow_wiring_status": "complete",
            "acceptance_status": "complete",
            "audit_status": "complete",
        },
    ]


class V5141DiagnosticsDashboardTest(unittest.TestCase):
    def test_default_snapshot_returns_stable_top_level_keys(self):
        snapshot = build_brain_diagnostics_snapshot()

        self.assertEqual(
            set(snapshot),
            {
                "dashboard_version",
                "layer_progress",
                "shadow_diagnostics",
                "current_turn_trace",
                "regression_safety_status",
                "test_health",
                "protected_dirty_files",
                "active_vs_shadow_layer_map",
                "mismatch_flags",
                "next_recommended_step",
                "diagnostics",
            },
        )
        self.assertEqual(len(snapshot["layer_progress"]), 3)

    def test_completed_foundation_layer_statuses_produce_readiness_100(self):
        snapshot = build_brain_diagnostics_snapshot(layer_statuses=_complete_layer_statuses())

        self.assertEqual(
            {row["layer_name"]: row["readiness_score"] for row in snapshot["layer_progress"]},
            {
                "Response Authority": RUNTIME_AUDITED,
                "Evidence Gap": RUNTIME_AUDITED,
                "Business Situation": RUNTIME_AUDITED,
            },
        )

    def test_incomplete_layer_status_produces_correct_readiness_score(self):
        statuses = _complete_layer_statuses()
        statuses[1]["audit_status"] = "missing"
        statuses[1]["acceptance_status"] = "complete"
        snapshot = build_brain_diagnostics_snapshot(layer_statuses=statuses)
        evidence_row = next(row for row in snapshot["layer_progress"] if row["layer_name"] == "Evidence Gap")

        self.assertEqual(evidence_row["readiness_score"], ACCEPTANCE_GUARDED)

    def test_contract_helper_and_shadow_status_scores_are_canonical(self):
        statuses = [
            {"layer_name": "Response Authority", "contract_status": "complete"},
            {"layer_name": "Evidence Gap", "contract_status": "complete", "helper_status": "complete"},
            {
                "layer_name": "Business Situation",
                "contract_status": "complete",
                "helper_status": "complete",
                "shadow_wiring_status": "complete",
            },
        ]
        snapshot = build_brain_diagnostics_snapshot(layer_statuses=statuses)
        scores = {row["layer_name"]: row["readiness_score"] for row in snapshot["layer_progress"]}

        self.assertEqual(scores["Response Authority"], CONTRACT_COMPLETE)
        self.assertEqual(scores["Evidence Gap"], HELPER_COMPLETE)
        self.assertEqual(scores["Business Situation"], SHADOW_WIRED)

    def test_shadow_diagnostics_preserve_response_authority_keys(self):
        diagnostics = {
            "response_authority_decision": "DIRECT_SEMANTIC_ANSWER",
            "response_authority_mode": "DIRECT_SEMANTIC_ANSWER",
            "response_authority_reason": "semantic_correction_detected",
            "response_authority_workflow_allowed": False,
            "response_authority_shadow_mode": True,
            "extra": "ignored",
        }
        snapshot = build_brain_diagnostics_snapshot(response_authority_diagnostics=diagnostics)

        self.assertEqual(snapshot["shadow_diagnostics"]["response_authority"], {k: diagnostics[k] for k in diagnostics if k != "extra"})

    def test_shadow_diagnostics_preserve_evidence_gap_keys(self):
        diagnostics = {
            "evidence_gap_profile": {"gap_type": "NO_GAP"},
            "evidence_gap_detected": False,
            "evidence_gap_type": "NO_GAP",
            "evidence_missing_fields": [],
            "evidence_conflicting_fields": [],
            "evidence_smallest_next_question": None,
            "evidence_sufficient": True,
            "evidence_can_answer_with_assumptions": False,
            "evidence_gap_reason": "current_turn_contains_required_evidence",
            "evidence_gap_confidence": 1.0,
            "evidence_gap_shadow_mode": True,
            "extra": "ignored",
        }
        snapshot = build_brain_diagnostics_snapshot(evidence_gap_diagnostics=diagnostics)

        self.assertEqual(snapshot["shadow_diagnostics"]["evidence_gap"], {k: diagnostics[k] for k in diagnostics if k != "extra"})

    def test_shadow_diagnostics_preserve_business_situation_keys(self):
        diagnostics = {
            "business_situation_profile": {"situation_type": "PRICING_DECISION"},
            "business_situation_detected": True,
            "business_situation_type": "PRICING_DECISION",
            "business_domain": "PRICING",
            "perspective_stance": "OWNER_ADVISORY",
            "business_risk_level": "LOW",
            "business_opportunity_level": "MEDIUM",
            "business_urgency_level": "LOW",
            "owner_attention": "Balance price and margin.",
            "recommended_response_posture": "OWNER_ADVISORY",
            "business_reasoning_summary": "pricing_decision_question",
            "business_situation_confidence": 0.86,
            "business_situation_shadow_mode": True,
            "extra": "ignored",
        }
        snapshot = build_brain_diagnostics_snapshot(business_situation_diagnostics=diagnostics)

        self.assertEqual(snapshot["shadow_diagnostics"]["business_situation"], {k: diagnostics[k] for k in diagnostics if k != "extra"})

    def test_active_gate_violation_flag_when_active_gate_true_while_shadow_expected(self):
        snapshot = build_brain_diagnostics_snapshot(active_gate_status={"enabled": True})

        self.assertIn("active_gate_violation", snapshot["mismatch_flags"])

    def test_diagnostics_missing_flag_appears_when_all_diagnostics_absent(self):
        snapshot = build_brain_diagnostics_snapshot()

        self.assertIn("diagnostics_missing", snapshot["mismatch_flags"])

    def test_evidence_sufficient_but_clarification_asked_mismatch_from_trace(self):
        snapshot = build_brain_diagnostics_snapshot(
            evidence_gap_diagnostics={"evidence_sufficient": True},
            current_turn_trace={"clarification_asked": True},
        )

        self.assertIn("evidence_sufficient_but_clarification_asked", snapshot["mismatch_flags"])

    def test_authority_direct_but_workflow_started_mismatch_from_trace(self):
        snapshot = build_brain_diagnostics_snapshot(
            response_authority_diagnostics={"response_authority_mode": "DIRECT_BUSINESS_ANALYSIS"},
            current_turn_trace={"workflow_started": True},
        )

        self.assertIn("authority_direct_but_workflow_started", snapshot["mismatch_flags"])

    def test_stale_context_reused_after_reset_mismatch_from_trace(self):
        snapshot = build_brain_diagnostics_snapshot(
            current_turn_trace={
                "reset_boundary_active": True,
                "completed_workflow_context_reused": True,
            }
        )

        self.assertIn("stale_context_reused_after_reset", snapshot["mismatch_flags"])

    def test_next_recommended_step_is_v5142_when_core_layers_audited_and_snapshot_exists(self):
        snapshot = build_brain_diagnostics_snapshot(layer_statuses=_complete_layer_statuses())

        self.assertEqual(
            snapshot["next_recommended_step"]["recommendation"],
            "Proceed to V5.14.2 shadow diagnostics snapshot wiring.",
        )

    def test_protected_dirty_files_are_included_but_do_not_mutate_inputs(self):
        protected = ["data/business_memory.json"]
        original = copy.deepcopy(protected)
        snapshot = build_brain_diagnostics_snapshot(protected_dirty_files=protected)

        self.assertEqual(snapshot["protected_dirty_files"], original)
        self.assertEqual(snapshot["test_health"]["protected_dirty_files"], original)
        self.assertEqual(protected, original)

    def test_malformed_inputs_do_not_crash(self):
        snapshot = build_brain_diagnostics_snapshot(
            layer_statuses={"bad": "shape"},
            response_authority_diagnostics=["bad"],
            evidence_gap_diagnostics="bad",
            business_situation_diagnostics=object(),
            test_health=["bad"],
            protected_dirty_files={"bad": "shape"},
            current_turn_trace=["bad"],
            active_gate_status=["bad"],
        )

        self.assertEqual(len(snapshot["layer_progress"]), 3)
        self.assertEqual(snapshot["shadow_diagnostics"]["response_authority"], {})
        self.assertEqual(snapshot["protected_dirty_files"], [])

    def test_helper_does_not_mutate_input_dictionaries_or_lists(self):
        layer_statuses = _complete_layer_statuses()
        response_authority = {"response_authority_mode": "DIRECT_SEMANTIC_ANSWER", "nested": {"keep": True}}
        evidence = {"evidence_sufficient": True, "evidence_missing_fields": []}
        business = {"business_situation_detected": True, "business_situation_type": "PRICING_DECISION"}
        test_health = {"known_warnings": ["none"]}
        protected = ["docs/v5/GLOSSARY.md"]
        trace = {"workflow_state_summary": {"status": "completed"}}
        active_gate = {"default_status": "shadow_only"}
        originals = copy.deepcopy((layer_statuses, response_authority, evidence, business, test_health, protected, trace, active_gate))

        build_brain_diagnostics_snapshot(
            layer_statuses=layer_statuses,
            response_authority_diagnostics=response_authority,
            evidence_gap_diagnostics=evidence,
            business_situation_diagnostics=business,
            test_health=test_health,
            protected_dirty_files=protected,
            current_turn_trace=trace,
            active_gate_status=active_gate,
        )

        self.assertEqual((layer_statuses, response_authority, evidence, business, test_health, protected, trace, active_gate), originals)

    def test_output_is_json_serializable(self):
        snapshot = build_brain_diagnostics_snapshot(
            layer_statuses=_complete_layer_statuses(),
            response_authority_diagnostics={"response_authority_mode": "DIRECT_SEMANTIC_ANSWER"},
            evidence_gap_diagnostics={"evidence_sufficient": True},
            business_situation_diagnostics={"business_situation_detected": False},
        )

        json.dumps(snapshot, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
