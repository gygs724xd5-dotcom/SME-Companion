import unittest

from brain.response_transformation_engine import (
    TRANSFORMATION_TYPES,
    build_response_memory,
    detect_response_transformation,
    transform_response,
)
from brain.task_router import developer_diagnostics


class V497ResponseTransformationIntelligenceTest(unittest.TestCase):
    def _state_with_memory(self, memory):
        return {
            "conversation": {
                **memory,
                "response_memory": memory,
                "chat_history": [
                    {"role": "assistant", "content": memory["last_generated_response"]},
                ],
            },
            "workflow": {
                "current_workflow": "content_plan",
                "workflow_state_v2": {"workflow": "content_plan", "step": "completed"},
            },
        }

    def test_detects_supported_transformation_types(self):
        examples = {
            "เอาแบบสั้น": "SHORTEN",
            "เพิ่ม Emoji": "EMOJI",
            "SEO": "SEO",
            "ขออีกแบบ": "VARIANT",
            "แปลอังกฤษ": "TRANSLATE",
            "สุภาพขึ้น": "FORMAL",
            "วัยรุ่นกว่าเดิม": "YOUTH",
            "ขายเก่งกว่าเดิม": "SALES",
            "Bullet": "BULLET",
            "CTA": "CTA",
            "เหลือ 1 ประโยค": "COMPRESS",
            "Summary": "SUMMARIZE",
        }

        self.assertTrue({"SHORTEN", "EXPAND", "REWRITE", "VARIANT", "TRANSLATE", "BULLET", "CTA", "EMOJI", "CASUAL", "FORMAL", "YOUTH", "PROFESSIONAL", "SEO", "SALES", "SUMMARIZE", "COMPRESS", "IMPROVE"}.issubset(TRANSFORMATION_TYPES))
        for message, expected_type in examples.items():
            with self.subTest(message=message):
                decision = detect_response_transformation(message)
                self.assertTrue(decision["is_transformation"])
                self.assertEqual(decision["transformation_type"], expected_type)

    def test_transformation_chain_edits_previous_generated_response_without_workflow(self):
        memory = build_response_memory(
            "ได้เลยครับ\n\nชาไทยหอมเข้มสำหรับลูกค้าออฟฟิศ ดื่มแล้วสดชื่น ทักแชทเพื่อสั่งได้เลย",
            response_type="content_post",
            generation_context={"workflow": "content_plan", "product": "ชาไทย"},
        )
        sequence = [
            ("เอาแบบสั้น", "SHORTEN"),
            ("เพิ่ม Emoji", "EMOJI"),
            ("SEO", "SEO"),
            ("ขออีกแบบ", "VARIANT"),
            ("แปลอังกฤษ", "TRANSLATE"),
            ("สุภาพขึ้น", "FORMAL"),
            ("วัยรุ่นกว่าเดิม", "YOUTH"),
            ("ปรับให้ดีขึ้น", "IMPROVE"),
            ("Bullet", "BULLET"),
            ("CTA", "CTA"),
            ("เหลือ 1 ประโยค", "COMPRESS"),
            ("Summary", "SUMMARIZE"),
        ]

        previous_reply = memory["last_generated_response"]
        for message, expected_type in sequence:
            with self.subTest(message=message):
                result = transform_response(message, self._state_with_memory(memory))
                self.assertTrue(result["handled"])
                self.assertTrue(result["used_previous_response"])
                self.assertTrue(result["planner_skipped"])
                self.assertEqual(result["transformation_type"], expected_type)
                self.assertEqual(result["previous_response"], previous_reply)
                self.assertEqual(result["response_source"], "response_transformation")
                self.assertNotEqual(result["reply"], previous_reply)

                memory = build_response_memory(
                    result["reply"],
                    response_type=result["response_type"],
                    generation_context=result["last_generation_context"],
                    previous_memory=memory,
                    transformation_result=result,
                )
                previous_reply = result["reply"]

        self.assertEqual(memory["last_transformation_chain"], [item[1] for item in sequence])
        self.assertEqual(len(memory["transformation_history"]), len(sequence))

    def test_transformation_diagnostics_include_v497_fields(self):
        diagnostics = developer_diagnostics(
            {
                "response_type": "transformation_seo",
                "response_source": "response_transformation",
                "response_reason": "transformed_previous_generated_response",
                "transformation_type": "SEO",
                "transformation_reason": "matched_seo_instruction",
                "transformation_source": "completed_response",
                "transformation_chain": ["SHORTEN", "EMOJI", "SEO"],
                "transformation_history": [
                    {"transformation_type": "SHORTEN"},
                    {"transformation_type": "EMOJI"},
                    {"transformation_type": "SEO"},
                ],
                "used_previous_response": True,
                "rewrite_mode": "seo",
                "translation_mode": None,
                "planner_skipped": True,
            }
        )

        self.assertEqual(diagnostics["transformation_type"], "SEO")
        self.assertEqual(diagnostics["transformation_reason"], "matched_seo_instruction")
        self.assertEqual(diagnostics["transformation_source"], "completed_response")
        self.assertEqual(diagnostics["transformation_chain"], ["SHORTEN", "EMOJI", "SEO"])
        self.assertEqual(len(diagnostics["transformation_history"]), 3)
        self.assertTrue(diagnostics["used_previous_response"])
        self.assertEqual(diagnostics["rewrite_mode"], "seo")
        self.assertIsNone(diagnostics["translation_mode"])
        self.assertTrue(diagnostics["planner_skipped"])

    def test_completed_response_has_priority_over_completed_workflow(self):
        memory = build_response_memory("โพสต์ล่าสุดจากคำตอบก่อนหน้า", response_type="content_post")
        app_state = {
            "conversation": {**memory, "response_memory": memory},
            "store": {
                "last_completed_workflow": {
                    "workflow_id": "content_plan",
                    "generated_response": "โพสต์จาก completed workflow",
                }
            },
        }

        result = transform_response("ขออีกแบบ", app_state)

        self.assertTrue(result["handled"])
        self.assertEqual(result["transformation_source"], "completed_response")
        self.assertEqual(result["previous_response"], "โพสต์ล่าสุดจากคำตอบก่อนหน้า")
        self.assertNotIn("completed workflow", result["reply"])


if __name__ == "__main__":
    unittest.main()
