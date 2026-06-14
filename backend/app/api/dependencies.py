from pathlib import Path

from app.core.config import get_settings
from app.repositories.excel_repository import ExcelRepository
from app.services.ai_gateway import AIGateway
from app.services.booking_extract_service import BookingExtractService
from app.services.complaint_service import ComplaintService
from app.services.conversation_context_service import ConversationContextService
from app.services.file_service import FileService
from app.services.form_service import FormService
from app.services.intent_service import IntentService
from app.services.knowledge_service import KnowledgeService
from app.services.recommendation_service import RecommendationService
from app.services.room_catalog_service import RoomCatalogService
from app.services.room_status_service import RoomStatusService


class AppContainer:
    def __init__(self) -> None:
        settings = get_settings()
        self.ai_gateway = AIGateway()
        self.context_service = ConversationContextService()
        self.room_catalog = RoomCatalogService()
        self.file_service = FileService(settings.excel_work_dir)
        self.intent_service = IntentService(self.ai_gateway)
        self.knowledge_service = KnowledgeService(self.ai_gateway)
        self.booking_extract_service = BookingExtractService(self.ai_gateway)
        self.recommendation_service = RecommendationService(self.ai_gateway)
        self.complaint_service = ComplaintService(self.ai_gateway)

    def excel_repository(self) -> ExcelRepository | None:
        path = self.file_service.current_excel_path
        return ExcelRepository(Path(path)) if path else None

    def form_service(self) -> FormService:
        return FormService(self.excel_repository(), self.room_catalog)

    def room_status_service(self) -> RoomStatusService:
        return RoomStatusService(self.room_catalog, self.excel_repository())


container = AppContainer()


def get_container() -> AppContainer:
    return container
