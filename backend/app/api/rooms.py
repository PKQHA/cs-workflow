try:
    from fastapi import APIRouter, Depends
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None
    Depends = lambda dependency: dependency

from app.api.dependencies import AppContainer, get_container
from app.schemas.common import ok
from app.schemas.requests import UpdateRoomStatusRequest

router = APIRouter(prefix="/api/rooms", tags=["rooms"]) if APIRouter else None


if router:
    @router.get("")
    async def list_rooms(
        capacity_type: str | None = None,
        room_status: str | None = None,
        room_category: str | None = None,
        container: AppContainer = Depends(get_container),
    ):
        rooms = container.room_catalog.list_rooms(capacity_type, room_status, room_category)
        return ok([room.model_dump() for room in rooms])

    @router.post("/update-status")
    async def update_room_status(request: UpdateRoomStatusRequest, container: AppContainer = Depends(get_container)):
        updated = container.room_status_service().release_room_to_available(request.room_number)
        return ok(updated.model_dump(), message="房态更新成功")
