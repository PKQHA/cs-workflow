from app.core.errors import BusinessRuleError, NotFoundError
from app.schemas.domain import ROOM_STATUSES, Room


def ensure_room_exists(room: Room | None, room_number: str) -> Room:
    if room is None:
        raise NotFoundError("ROOM_NOT_FOUND", f"房间 {room_number} 不存在，请检查房号是否输入正确。")
    return room


def ensure_valid_room_status(status: str) -> None:
    if status not in ROOM_STATUSES:
        raise BusinessRuleError("ROOM_STATUS_INVALID", "房态只能是 空房、已预订 或 已住。")


def ensure_can_manual_release(current_status: str, target_status: str) -> None:
    ensure_valid_room_status(target_status)
    if target_status != "空房":
        raise BusinessRuleError("ROOM_STATUS_CONFLICT", "手动房态维护当前只允许将已住或已预订改为空房。")
    if current_status == "空房":
        raise BusinessRuleError("ROOM_STATUS_CONFLICT", "该房间已经是空房，无需重复修改。")
    if current_status not in {"已住", "已预订"}:
        raise BusinessRuleError("ROOM_STATUS_CONFLICT", f"当前房态 {current_status} 不允许手动释放。")


def ensure_rooms_are_available(rooms: list[Room]) -> None:
    unavailable = [room.room_number for room in rooms if room.status != "空房"]
    if unavailable:
        joined = "、".join(unavailable)
        raise BusinessRuleError("ROOM_STATUS_CONFLICT", f"房态冲突：{joined} 当前不是空房，不能用于新表单。")
