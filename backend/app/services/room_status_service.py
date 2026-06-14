from random import Random

from app.repositories.excel_repository import ExcelRepository
from app.rules.room_rules import ensure_can_manual_release, ensure_room_exists
from app.services.room_catalog_service import RoomCatalogService


class RoomStatusService:
    def __init__(
        self,
        catalog: RoomCatalogService,
        excel_repository: ExcelRepository | None = None,
    ) -> None:
        self.catalog = catalog
        self.excel_repository = excel_repository

    @classmethod
    def with_random_initial_occupied(
        cls,
        seed: int = 20260614,
        excel_repository: ExcelRepository | None = None,
    ) -> "RoomStatusService":
        base_catalog = RoomCatalogService()
        room_numbers = [room.room_number for room in base_catalog.list_rooms()]
        occupied = set(Random(seed).sample(room_numbers, 7))
        catalog = RoomCatalogService({room_number: "已住" for room_number in occupied})
        return cls(catalog=catalog, excel_repository=excel_repository)

    def list_available_rooms(self):
        return self.catalog.available_rooms()

    def get_room_status(self, room_number: str):
        return self.catalog.get_room(room_number)

    def available_room_count(self) -> int:
        return len(self.catalog.available_rooms())

    def has_available_rooms(self) -> bool:
        return self.available_room_count() > 0

    def build_room_status_reply(self, room_number: str) -> str:
        room = self.get_room_status(room_number)
        if room is None:
            return f"您好，暂时没有查到 {room_number} 房间的房态信息，需要客服进一步确认。"
        return f"您好，{room_number} 房间当前状态为{room.status}。"

    def build_availability_reply(self) -> str:
        available_count = self.available_room_count()
        if available_count > 0:
            return f"您好，目前还有空房，当前可用空房数量为 {available_count} 间。"
        return "您好，目前暂时没有空房，需要客服进一步确认后为您安排。"

    def release_room_to_available(self, room_number: str):
        room = ensure_room_exists(self.catalog.get_room(room_number), room_number)
        ensure_can_manual_release(room.status, "空房")
        updated = self.catalog.set_status(room_number, "空房")
        if self.excel_repository:
            self.excel_repository.update_room_status(room_number, "空房")
        return updated

    def set_rooms_status(self, room_numbers: list[str], status: str) -> None:
        for room_number in room_numbers:
            ensure_room_exists(self.catalog.get_room(room_number), room_number)
        for room_number in room_numbers:
            self.catalog.set_status(room_number, status)
