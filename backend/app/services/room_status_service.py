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
