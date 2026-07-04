import copy
import unittest

from brain.brain_observatory import build_brain_observatory
from brain.business_situation import build_business_situation
from brain.perspective_frame_registry import (
    PerspectiveFrameRegistry,
    get_perspective_frame,
    list_perspective_frames,
)
from brain.perspective_runtime import build_perspective_runtime
from brain.task_router import build_task_route, developer_diagnostics


def _perspective(message: str) -> dict:
    return build_business_situation(user_message=message)["diagnostics"]["perspective"]


class V585SituationFrameRegistryAndPerspectiveClassificationTest(unittest.TestCase):
    def test_registry_loads_initial_frames_with_unique_ids_and_boundaries(self):
        registry = PerspectiveFrameRegistry()
        frames = registry.list()
        ids = [frame.frame_id for frame in frames]

        self.assertGreaterEqual(len(frames), 13)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("UNKNOWN_SITUATION", ids)
        for frame in frames:
            self.assertTrue(frame.allowed_outputs)
            self.assertTrue(frame.forbidden_outputs)

    def test_registry_lookup_is_deterministic(self):
        first = get_perspective_frame("PROFIT_COMPRESSION")
        second = get_perspective_frame("PROFIT_COMPRESSION")

        self.assertEqual(first, second)
        self.assertEqual(
            [frame.frame_id for frame in list_perspective_frames()],
            [frame.frame_id for frame in PerspectiveFrameRegistry().list()],
        )

    def test_profit_compression_from_customers_and_profit(self):
        perspective = _perspective("ลูกค้าเพิ่มแต่กำไรลด")

        self.assertEqual(perspective["selected_frame"], "PROFIT_COMPRESSION")
        self.assertGreaterEqual(perspective["frame_confidence"], 0.65)

    def test_profit_compression_from_sales_and_profit(self):
        self.assertEqual(_perspective("ยอดขายเพิ่มแต่กำไรลด")["selected_frame"], "PROFIT_COMPRESSION")

    def test_sales_decline(self):
        self.assertEqual(_perspective("ยอดขายลดลงต่อเนื่อง")["selected_frame"], "SALES_DECLINE")

    def test_inventory_risk(self):
        self.assertEqual(_perspective("ของเหลือแค่ 3 ชิ้น")["selected_frame"], "INVENTORY_RISK")

    def test_cash_flow_stress(self):
        self.assertEqual(_perspective("ขายได้แต่ไม่มีเงินสด")["selected_frame"], "CASH_FLOW_STRESS")

    def test_demand_surge(self):
        self.assertEqual(_perspective("ออเดอร์เพิ่มขึ้นมาก")["selected_frame"], "DEMAND_SURGE")

    def test_demand_weakness(self):
        self.assertEqual(_perspective("ลูกค้าน้อยลงต่อเนื่อง")["selected_frame"], "DEMAND_WEAKNESS")

    def test_backlog_selects_deterministic_operational_frame(self):
        frame = _perspective("ออเดอร์ค้างเพราะทำไม่ทัน")["selected_frame"]
        self.assertIn(frame, {"OPERATIONAL_BOTTLENECK", "CAPACITY_CONSTRAINT"})

    def test_capacity_constraint(self):
        self.assertEqual(_perspective("โรงงานผลิตไม่ทันยอดสั่ง")["selected_frame"], "CAPACITY_CONSTRAINT")

    def test_supplier_disruption(self):
        self.assertEqual(_perspective("ซัพพลายเออร์ส่งของช้า")["selected_frame"], "SUPPLIER_DISRUPTION")

    def test_customer_retention_risk(self):
        self.assertEqual(_perspective("ลูกค้าไม่กลับมาซื้อซ้ำ")["selected_frame"], "CUSTOMER_RETENTION_RISK")

    def test_unsupported_message_is_unknown_with_low_confidence(self):
        perspective = _perspective("วันนี้อากาศดี")

        self.assertEqual(perspective["selected_frame"], "UNKNOWN_SITUATION")
        self.assertLess(perspective["frame_confidence"], 0.4)

    def test_multi_frame_input_produces_ranked_candidates_and_material_primary(self):
        perspective = _perspective("ลูกค้าเพิ่ม แต่กำไรลด และเงินสดไม่พอ")
        candidate_ids = [item["frame_id"] for item in perspective["candidate_frames"]]

        self.assertEqual(perspective["selected_frame"], "PROFIT_COMPRESSION")
        self.assertIn("PROFIT_COMPRESSION", candidate_ids)
        self.assertIn("CASH_FLOW_STRESS", candidate_ids)
        self.assertIn("DEMAND_SURGE", candidate_ids)
        self.assertEqual(candidate_ids[0], "PROFIT_COMPRESSION")

    def test_confidence_is_bounded(self):
        for message in ("ลูกค้าเพิ่มแต่กำไรลด", "วันนี้อากาศดี"):
            confidence = _perspective(message)["frame_confidence"]
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)

    def test_inputs_are_not_mutated(self):
        situation = build_business_situation(user_message="ลูกค้าเพิ่มแต่กำไรลด")
        evidence = situation["diagnostics"]["evidence"]
        truth = situation["diagnostics"]["truth"]
        evidence_gap = situation["diagnostics"]["evidence_gap"]
        before = copy.deepcopy((situation, evidence, truth, evidence_gap))

        build_perspective_runtime(
            business_situation=situation,
            evidence_runtime=evidence,
            truth_runtime=truth,
            evidence_gap_runtime=evidence_gap,
        )

        self.assertEqual((situation, evidence, truth, evidence_gap), before)

    def test_boundaries_do_not_invoke_future_layers_or_workflows(self):
        route = build_task_route({}, "ลูกค้าเพิ่มแต่กำไรลด")
        perspective = route["business_situation"]["diagnostics"]["perspective"]
        invariants = perspective["constitutional_invariants"]

        self.assertNotEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertFalse(invariants["knowledge_invoked"])
        self.assertFalse(invariants["judgment_invoked"])
        self.assertFalse(invariants["decision_invoked"])
        self.assertFalse(invariants["recommendations_generated"])
        self.assertFalse(invariants["root_causes_diagnosed"])
        self.assertNotIn("ควร", route.get("final_response_text") or "")

    def test_clarification_reads_profit_compression_frame_and_requests_evidence(self):
        route = build_task_route({}, "ลูกค้าเพิ่มแต่กำไรลด")
        clarification = route["clarification_authority"]

        self.assertEqual(route["business_situation"]["diagnostics"]["perspective"]["selected_frame"], "PROFIT_COMPRESSION")
        self.assertTrue(clarification["perspective_consulted"])
        self.assertEqual(clarification["perspective_selected_frame"], "PROFIT_COMPRESSION")
        self.assertIn("revenue", clarification["requested_fields"])
        self.assertIn("cost", clarification["requested_fields"])
        self.assertNotIn("ต้นทุนสูงแน่นอน", route["final_response_text"])
        self.assertNotIn("ควรขึ้นราคา", route["final_response_text"])

    def test_low_confidence_frame_does_not_produce_strong_framing(self):
        route = build_task_route({}, "วันนี้อากาศดี")
        clarification = route["clarification_authority"]

        self.assertEqual(route["business_situation"]["diagnostics"]["perspective"]["selected_frame"], "UNKNOWN_SITUATION")
        self.assertFalse(clarification["perspective_used_for_framing"])

    def test_admitted_workflow_behavior_remains_unchanged(self):
        route = build_task_route({}, "ช่วยคำนวนกำไรให้หน่อย")

        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual((route["business_workflow"]["workflow_state"] or {}).get("workflow_id"), "PROFIT_CALCULATION")

    def test_audit_records_perspective_authority_boundaries(self):
        route = build_task_route({}, "ลูกค้าเพิ่มแต่กำไรลด")
        audit = route["cognitive_authority_audit"]

        self.assertTrue(audit["perspective_classification_performed"])
        self.assertEqual(audit["perspective_selected_frame"], "PROFIT_COMPRESSION")
        self.assertTrue(audit["perspective_authoritative_for_framing"])
        self.assertFalse(audit["perspective_authoritative_for_routing"])
        self.assertFalse(audit["perspective_authoritative_for_workflow"])

    def test_observatory_shows_registry_and_classification_diagnostics(self):
        route = build_task_route({}, "ลูกค้าเพิ่มแต่กำไรลด")
        observatory = build_brain_observatory(route)
        layers = {layer["layer"]: layer for layer in observatory["layers"]}
        perspective_state = layers["Perspective"]["runtime_state"]

        self.assertEqual(
            observatory["layer_order"][observatory["layer_order"].index("Evidence Gap") + 1],
            "Perspective",
        )
        self.assertEqual(perspective_state["selected_frame"], "PROFIT_COMPRESSION")
        self.assertTrue(perspective_state["classification_performed"])
        self.assertGreaterEqual(perspective_state["registered_frame_count"], 13)
        self.assertIn("PROFIT_COMPRESSION", perspective_state["registered_frame_ids"])

    def test_workflow_regressions(self):
        self.assertNotEqual(build_task_route({}, "ร้านของฉันกำไรดีไหม")["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertNotEqual(build_task_route({}, "ลูกค้าเพิ่มแต่กำไรลด")["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(build_task_route({}, "ช่วยคำนวนกำไรให้หน่อย")["workflow_admission_gate"]["decision"], "ADMIT")

        numeric = build_task_route({}, "ขาย 80 บาท ต้นทุน 35 บาท กำไรกี่บาท")
        self.assertEqual(numeric["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(
            numeric["business_workflow"]["extracted_entities"]["price"]
            - numeric["business_workflow"]["extracted_entities"]["cost"],
            45,
        )

    def test_developer_diagnostics_expose_perspective_fields(self):
        diagnostics = developer_diagnostics(build_task_route({}, "ลูกค้าเพิ่มแต่กำไรลด"))
        perspective_group = diagnostics["diagnostic_groups"]["Perspective"]

        self.assertEqual(diagnostics["perspective_selected_frame"], "PROFIT_COMPRESSION")
        self.assertEqual(perspective_group["selected_frame"], "PROFIT_COMPRESSION")
        self.assertTrue(perspective_group["classification_performed"])
        self.assertGreaterEqual(perspective_group["registered_frame_count"], 13)


if __name__ == "__main__":
    unittest.main()
