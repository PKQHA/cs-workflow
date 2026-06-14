import tempfile
import unittest
from pathlib import Path

from app.core.errors import AppError, BusinessRuleError
from app.repositories.excel_repository import ExcelRepository
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
        service = IntentService(AIGateway())
        self.assertEqual(service.detect("我们3个人住1天"), "booking")
        self.assertEqual(service.detect("早餐几点开始"), "qa")

    def test_knowledge_hit_and_fallback(self):
        service = KnowledgeService(AIGateway())
        self.assertIn("12点", service.answer("退房时间是几点"))
        self.assertIn("暂未覆盖", service.answer("附近有没有剧院"))

    def test_booking_extract_single_and_multi_turn(self):
        service = BookingExtractService(AIGateway())
        first = service.extract("我们有3个人，开2个房间")
        second = service.extract("预算1000元，住2天，怎么便宜怎么来", first)
        self.assertEqual(second.guest_count, 3)
        self.assertEqual(second.room_count, 2)
        self.assertEqual(second.budget, 1000)
        self.assertEqual(second.stay_days, 2)
        self.assertIn("价格优先", second.preferences)

    def test_recommendation_generates_multiple_results(self):
        catalog = RoomCatalogService()
        service = RecommendationService(AIGateway())
        draft = BookingDraft(guest_count=3, room_count=1, budget=500, stay_days=1, guest_type="多人")
        recommendations = service.recommend(draft, catalog.available_rooms())
        self.assertGreaterEqual(len(recommendations), 1)
        self.assertLessEqual(len(recommendations), 3)

    def test_recommendation_budget_too_low(self):
        catalog = RoomCatalogService()
        service = RecommendationService(AIGateway())
        draft = BookingDraft(guest_count=3, room_count=1, budget=10, stay_days=1, guest_type="多人")
        with self.assertRaises(BusinessRuleError):
            service.recommend(draft, catalog.available_rooms())

    def test_complaint_branches(self):
        service = ComplaintService(AIGateway())
        mild = service.analyze("房间床单有污渍，影响体验")
        self.assertEqual(mild.complaint_type, "卫生")
        self.assertEqual(mild.severity, "轻度")
        medium = service.analyze("前台服务态度很差，我要投诉")
        self.assertEqual(medium.severity, "中度")
        severe = service.analyze("无法入住，要求全部退款并曝光")
        self.assertEqual(severe.severity, "重度")

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


if __name__ == "__main__":
    unittest.main()
