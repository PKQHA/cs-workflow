from __future__ import annotations

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
        self.demo_room_status_service = RoomStatusService.with_random_initial_occupied()
        self.ai_gateway = AIGateway()
        self.context_service = ConversationContextService()
        self.file_service = FileService(settings.excel_work_dir)
        self.intent_service = IntentService(self.ai_gateway)
        self.knowledge_service = KnowledgeService(self.ai_gateway)
        self.booking_extract_service = BookingExtractService(self.ai_gateway)
        self.recommendation_service = RecommendationService(self.ai_gateway)
        self.complaint_service = ComplaintService(self.ai_gateway)

    def excel_repository(self, workspace_id: str | None) -> ExcelRepository | None:
        if not workspace_id or not self.file_service.has_uploaded_excel(workspace_id):
            return None
        path = self.file_service.require_workspace_excel_path(workspace_id)
        return ExcelRepository(Path(path))

    def room_catalog(self, workspace_id: str | None) -> RoomCatalogService:
        repository = self.excel_repository(workspace_id)
        if repository is None:
            return self.demo_room_status_service.catalog
        return RoomCatalogService(repository.list_room_statuses())

    def form_service(self, workspace_id: str | None) -> FormService:
        return FormService(self.excel_repository(workspace_id), self.room_catalog(workspace_id))

    def room_status_service(self, workspace_id: str | None) -> RoomStatusService:
        repository = self.excel_repository(workspace_id)
        if repository is None:
            return self.demo_room_status_service
        return RoomStatusService(self.room_catalog(workspace_id), repository)

    @staticmethod
    def context_key(workspace_id: str | None, session_id: str) -> str:
        normalized_workspace = str(workspace_id or "").strip()
        if not normalized_workspace:
            return session_id
        return f"{normalized_workspace}:{session_id}"


container = AppContainer()


def get_container() -> AppContainer:
    return container
