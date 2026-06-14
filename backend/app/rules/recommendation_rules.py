from itertools import combinations

from app.core.errors import BusinessRuleError
from app.schemas.domain import BookingDraft, Room


def room_capacity(room: Room) -> int:
    return 1 if room.capacity_type == "单人间" else 4


def build_candidate_room_sets(draft: BookingDraft, available_rooms: list[Room]) -> list[list[Room]]:
    if not draft.room_count or not draft.guest_count or not draft.stay_days or not draft.budget:
        raise BusinessRuleError("MISSING_REQUIRED_FIELDS", "订房信息不完整，暂无法生成推荐方案。")
    if len(available_rooms) < draft.room_count:
        return []
    candidates = []
    for combo in combinations(available_rooms, draft.room_count):
        rooms = list(combo)
        if any(room.status != "空房" for room in rooms):
            raise BusinessRuleError("ROOM_STATUS_CONFLICT", "推荐候选中包含非空房，已被规则层拦截。")
        total_capacity = sum(room_capacity(room) for room in rooms)
        total_amount = sum(room.price_per_day for room in rooms) * draft.stay_days
        if total_capacity >= draft.guest_count and total_amount <= draft.budget:
            candidates.append(rooms)
    return sorted(candidates, key=lambda rooms: sum(room.price_per_day for room in rooms))[:3]
