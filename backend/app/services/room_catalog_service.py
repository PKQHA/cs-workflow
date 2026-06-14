from copy import deepcopy

from app.schemas.domain import Room


class RoomCatalogService:
    def __init__(self, initial_statuses: dict[str, str] | None = None) -> None:
        self._rooms = self._build_rooms()
        if initial_statuses:
            for room in self._rooms:
                if room.room_number in initial_statuses:
                    room.status = initial_statuses[room.room_number]

    @staticmethod
    def _build_rooms() -> list[Room]:
        room_numbers = [
            *[f"20{i}" for i in range(1, 8)],
            *[f"30{i}" for i in range(1, 8)],
            *[f"40{i}" for i in range(1, 8)],
            *[f"50{i}" for i in range(1, 8)],
            *[f"60{i}" for i in range(1, 5)],
        ]
        rooms: list[Room] = []
        for index, room_number in enumerate(room_numbers):
            floor = int(room_number[0])
            capacity_type = "单人间" if index % 3 == 0 else "多人间"
            if room_number in {"206", "306", "406", "506", "602"}:
                room_category = "特殊房"
                special_type = "情侣套房"
                room_name = "情侣套房"
                price = 388.0
            elif room_number in {"207", "307", "407", "507", "603", "604"}:
                room_category = "特殊房"
                special_type = "文创套房"
                room_name = "文创套房"
                price = 428.0
            else:
                room_category = "普通房"
                special_type = None
                room_name = capacity_type
                price = 188.0 if capacity_type == "单人间" else 268.0

            rooms.append(
                Room(
                    room_number=room_number,
                    floor=floor,
                    room_name=room_name,
                    capacity_type=capacity_type,
                    room_category=room_category,
                    special_type=special_type,
                    price_per_day=price,
                    status="空房",
                    image_url=f"/static/rooms/{room_number}.jpg",
                )
            )
        return rooms

    def list_rooms(
        self,
        capacity_type: str | None = None,
        room_status: str | None = None,
        room_category: str | None = None,
    ) -> list[Room]:
        rooms = self._rooms
        if capacity_type and capacity_type != "全部":
            rooms = [room for room in rooms if room.capacity_type == capacity_type]
        if room_status and room_status != "全部":
            rooms = [room for room in rooms if room.status == room_status]
        if room_category and room_category != "全部":
            rooms = [room for room in rooms if room.room_category == room_category]
        return deepcopy(rooms)

    def get_room(self, room_number: str) -> Room | None:
        for room in self._rooms:
            if room.room_number == room_number:
                return deepcopy(room)
        return None

    def set_status(self, room_number: str, status: str) -> Room:
        for room in self._rooms:
            if room.room_number == room_number:
                room.status = status
                return deepcopy(room)
        raise KeyError(room_number)

    def available_rooms(self) -> list[Room]:
        return self.list_rooms(room_status="空房")
