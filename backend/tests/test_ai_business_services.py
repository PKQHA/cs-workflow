import tempfile
import unittest
from pathlib import Path

from app.core.errors import AppError, BusinessRuleError
from app.repositories.excel_repository import ExcelRepository, FORM_HEADERS, ROOM_STATUS_HEADERS
from app.schemas.domain import BookingDraft
from app.services.ai_gateway import AIGateway
from app.services.booking_extract_service import BookingExtractService
from app.services.complaint_service import ComplaintService
from app.services.conversation_context_service import ConversationContextService
from app.services.file_service import FileService
from app.services.intent_service import IntentService
from app.services.knowledge_service import KnowledgeService
from app.services.recommendation_service import RecommendationService
from app.services.room_catalog_service import RoomCatalogService


class AIBusinessServiceTests(unittest.TestCase):
    @staticmethod
    def _mock_gateway(canned_responses=None):
        return AIGateway(canned_responses=canned_responses, provider="mock")

    def test_context_accumulates_and_resets(self):
        service = ConversationContextService()
        service.append_history("s1", "3人")
        service.merge_booking_draft("s1", BookingDraft(guest_count=3))
        service.merge_booking_draft("s1", BookingDraft(room_count=2, budget=1000, stay_days=1))
        context = service.get_context("s1")
        self.assertEqual(context.booking_draft.guest_count, 3)
        self.assertEqual(context.booking_draft.room_count, 2)
        self.assertEqual(service.reset("s1").history, [])

    def test_intent_detection(self):
        service = IntentService(self._mock_gateway())
        self.assertEqual(service.detect("我们3个人住1天"), "booking")
        self.assertEqual(service.detect("早餐几点开始"), "qa")

    def test_intent_router_handles_room_status_and_unknown(self):
        service = IntentService(self._mock_gateway())
        room_status = service.route("207现在有人吗")
        self.assertEqual(room_status.intent, "qa")
        self.assertEqual(room_status.slots["room_number"], "207")

        unknown = service.route("你好")
        self.assertEqual(unknown.intent, "unknown")

    def test_knowledge_hit_and_fallback(self):
        service = KnowledgeService(self._mock_gateway())
        self.assertIn("12点", service.answer("退房时间是几点"))
        self.assertIn("暂未覆盖", service.answer("附近有没有剧院"))
        self.assertEqual(service.answer("晚饭有什么"), "我暂时没有查到晚餐信息，请客服确认后补充。")

    def test_knowledge_can_use_grounded_model_answer(self):
        service = KnowledgeService(
            self._mock_gateway(
                canned_responses={
                    "knowledge_answer": {
                        "reply": "根据现有酒店信息，早餐在二楼餐厅供应。",
                        "grounded": True,
                    }
                }
            )
        )
        self.assertEqual(service.answer("早餐在哪吃"), "根据现有酒店信息，早餐在二楼餐厅供应。")

    def test_booking_extract_single_and_multi_turn(self):
        service = BookingExtractService(self._mock_gateway())
        first = service.extract("我们有3个人，开2个房间")
        second = service.extract("预算1000元，住2天，怎么便宜怎么来", first)
        self.assertEqual(second.guest_count, 3)
        self.assertEqual(second.room_count, 2)
        self.assertEqual(second.budget, 1000)
        self.assertEqual(second.stay_days, 2)
        self.assertIn("价格优先", second.preferences)

    def test_booking_extract_prefers_model_output_when_available(self):
        service = BookingExtractService(
            self._mock_gateway(
                canned_responses={
                    "booking_extract": {
                        "guest_count": 6,
                        "room_count": 2,
                        "budget": 1200,
                        "stay_days": 2,
                        "guest_type": "多人",
                        "preferences": ["安静"],
                    }
                }
            )
        )
        draft = service.extract("帮我安排一下")
        self.assertEqual(draft.guest_count, 6)
        self.assertEqual(draft.room_count, 2)
        self.assertEqual(draft.budget, 1200)
        self.assertEqual(draft.stay_days, 2)
        self.assertIn("安静", draft.preferences)

    def test_recommendation_generates_multiple_results(self):
        catalog = RoomCatalogService()
        service = RecommendationService(self._mock_gateway())
        draft = BookingDraft(guest_count=3, room_count=1, budget=500, stay_days=1, guest_type="多人")
        recommendations = service.recommend(draft, catalog.available_rooms())
        self.assertGreaterEqual(len(recommendations), 1)
        self.assertLessEqual(len(recommendations), 3)

    def test_recommendation_copy_failure_does_not_break_candidates(self):
        catalog = RoomCatalogService()
        gateway = AIGateway(provider="openai", api_key="demo", base_url="http://127.0.0.1:1", timeout_seconds=0.1)
        service = RecommendationService(gateway)
        draft = BookingDraft(guest_count=3, room_count=1, budget=500, stay_days=1, guest_type="多人")
        recommendations = service.recommend(draft, catalog.available_rooms())
        self.assertGreaterEqual(len(recommendations), 1)
        self.assertTrue(all(item.reason_text for item in recommendations))

    def test_recommendation_budget_too_low(self):
        catalog = RoomCatalogService()
        service = RecommendationService(self._mock_gateway())
        draft = BookingDraft(guest_count=3, room_count=1, budget=10, stay_days=1, guest_type="多人")
        with self.assertRaises(BusinessRuleError):
            service.recommend(draft, catalog.available_rooms())

    def test_complaint_branches(self):
        service = ComplaintService(self._mock_gateway())
        mild = service.analyze("房间床单有污渍，影响体验")
        self.assertEqual(mild.complaint_type, "卫生")
        self.assertEqual(mild.severity, "轻度")
        medium = service.analyze("前台服务态度很差，我要投诉")
        self.assertEqual(medium.severity, "中度")
        severe = service.analyze("无法入住，要求全部退款并曝光")
        self.assertEqual(severe.severity, "重度")

    def test_complaint_uses_model_fields_when_valid(self):
        service = ComplaintService(
            self._mock_gateway(
                canned_responses={
                    "complaint_analysis": {
                        "complaint_type": "设施故障",
                        "severity": "重度",
                        "comfort_reply": "我们马上处理。",
                        "solution": "安排工程人员立即上门。",
                        "compensation": "视现场情况补偿。",
                        "escalation_note": "需要值班经理介入。",
                        "escalation_summary": "空调损坏且无法入住。",
                    }
                }
            )
        )
        case = service.analyze("空调坏了，今晚根本没法住")
        self.assertEqual(case.complaint_type, "设施故障")
        self.assertEqual(case.severity, "重度")
        self.assertEqual(case.escalation_note, "需要值班经理介入。")

    def test_real_provider_without_key_is_reported(self):
        gateway = AIGateway(provider="openai", api_key="")
        with self.assertRaises(AppError) as ctx:
            gateway.call_structured("intent", {"text": "早餐几点"})
        self.assertEqual(ctx.exception.error_code, "AI_PROVIDER_NOT_CONFIGURED")

    def test_file_upload_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = ExcelRepository.create_template(tmp_path / "source.xlsx")
            service = FileService(tmp_path / "uploads")
            uploaded = service.upload_excel(source)
            self.assertTrue(uploaded.exists())
            self.assertTrue(service.has_uploaded_excel())
            invalid = tmp_path / "bad.txt"
            invalid.write_text("bad", encoding="utf-8")
            with self.assertRaises(AppError):
                service.upload_excel(invalid)

    def test_file_upload_initializes_blank_workbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "blank.xlsx"
            workbook = __import__("openpyxl").Workbook()
            workbook.save(source)
            workbook.close()

            service = FileService(tmp_path / "uploads")
            uploaded = service.upload_excel(source)

            workbook = __import__("openpyxl").load_workbook(uploaded)
            self.assertIn("订单表单", workbook.sheetnames)
            self.assertIn("房态", workbook.sheetnames)
            form_headers = [cell.value for cell in workbook["订单表单"][1][: len(FORM_HEADERS)]]
            room_headers = [cell.value for cell in workbook["房态"][1][: len(ROOM_STATUS_HEADERS)]]
            self.assertEqual(form_headers, FORM_HEADERS)
            self.assertEqual(room_headers, ROOM_STATUS_HEADERS)
            workbook.close()


if __name__ == "__main__":
    unittest.main()
