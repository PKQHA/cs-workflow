from collections import defaultdict
from dataclasses import dataclass

from app.core.errors import BusinessRuleError
from app.schemas.domain import BookingDraft, Room


@dataclass(frozen=True)
class RoomTypeGroup:
    descriptor: tuple[str, str, str, float]
    rooms: tuple[Room, ...]

    @property
    def capacity(self) -> int:
        return 1 if self.descriptor[0] == "单人间" else 4

    @property
    def price_per_day(self) -> float:
        return float(self.descriptor[3])

    @property
    def special_weight(self) -> int:
        return 0 if not self.descriptor[2] else 1


def room_capacity(room: Room) -> int:
    return 1 if room.capacity_type == "单人间" else 4


def room_descriptor(room: Room) -> tuple[str, str, str, float]:
    return (
        room.capacity_type,
        room.room_category,
        room.special_type or "",
        float(room.price_per_day),
    )


def room_signature(rooms: list[Room]) -> str:
    descriptors = sorted(room_descriptor(room) for room in rooms)
    return "|".join(f"{capacity}:{category}:{special}:{price:.2f}" for capacity, category, special, price in descriptors)


def build_candidate_room_sets(draft: BookingDraft, available_rooms: list[Room]) -> list[list[Room]]:
    if not draft.room_count or not draft.guest_count or not draft.stay_days or not draft.budget:
        raise BusinessRuleError("MISSING_REQUIRED_FIELDS", "订房信息不完整，暂无法生成推荐方案。")
    if len(available_rooms) < draft.room_count:
        return []
    if any(room.status != "空房" for room in available_rooms):
        raise BusinessRuleError("ROOM_STATUS_CONFLICT", "推荐候选中包含非空房，已被规则层拦截。")

    grouped = _build_room_type_groups(available_rooms)
    if not grouped:
        return []

    per_night_budget = float(draft.budget) / int(draft.stay_days)
    candidates: list[list[Room]] = []
    seen_signatures: set[str] = set()

    def backtrack(index: int, chosen: list[Room], total_capacity: int, total_price_per_day: float) -> None:
        chosen_count = len(chosen)
        remaining_slots = int(draft.room_count) - chosen_count
        if total_price_per_day > per_night_budget:
            return
        if remaining_slots == 0:
            if total_capacity >= int(draft.guest_count):
                signature = room_signature(chosen)
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    candidates.append(sorted(chosen, key=lambda room: room.room_number))
            return
        if index >= len(grouped):
            return
        if _max_additional_capacity(grouped, index, remaining_slots) + total_capacity < int(draft.guest_count):
            return
        if _min_additional_price(grouped, index, remaining_slots) + total_price_per_day > per_night_budget:
            return

        group = grouped[index]
        max_pick = min(len(group.rooms), remaining_slots)
        for pick_count in range(max_pick, -1, -1):
            next_rooms = list(group.rooms[:pick_count])
            next_capacity = total_capacity + (group.capacity * pick_count)
            next_price = total_price_per_day + (group.price_per_day * pick_count)
            if next_price > per_night_budget:
                continue
            backtrack(index + 1, chosen + next_rooms, next_capacity, next_price)

    backtrack(0, [], 0, 0.0)
    ranked = sorted(candidates, key=lambda rooms: _candidate_sort_key(rooms, draft))
    return ranked[:3]


def _build_room_type_groups(available_rooms: list[Room]) -> list[RoomTypeGroup]:
    grouped: dict[tuple[str, str, str, float], list[Room]] = defaultdict(list)
    for room in available_rooms:
        grouped[room_descriptor(room)].append(room)

    room_type_groups = [
        RoomTypeGroup(
            descriptor=descriptor,
            rooms=tuple(sorted(rooms, key=lambda room: room.room_number)),
        )
        for descriptor, rooms in grouped.items()
    ]
    return sorted(
        room_type_groups,
        key=lambda group: (
            group.price_per_day,
            group.special_weight,
            -group.capacity,
            group.descriptor[0],
            group.descriptor[1],
            group.descriptor[2],
        ),
    )


def _max_additional_capacity(groups: list[RoomTypeGroup], start_index: int, remaining_slots: int) -> int:
    capacities: list[int] = []
    for group in groups[start_index:]:
        capacities.extend([group.capacity] * len(group.rooms))
    capacities.sort(reverse=True)
    return sum(capacities[:remaining_slots])


def _min_additional_price(groups: list[RoomTypeGroup], start_index: int, remaining_slots: int) -> float:
    prices: list[float] = []
    for group in groups[start_index:]:
        prices.extend([group.price_per_day] * len(group.rooms))
    prices.sort()
    if len(prices) < remaining_slots:
        return float("inf")
    return sum(prices[:remaining_slots])


def _candidate_sort_key(rooms: list[Room], draft: BookingDraft) -> tuple[float, int, int, str]:
    total_amount = sum(room.price_per_day for room in rooms) * int(draft.stay_days)
    over_capacity = sum(room_capacity(room) for room in rooms) - int(draft.guest_count)
    special_count = sum(1 for room in rooms if room.special_type)
    return (total_amount, over_capacity, special_count, room_signature(rooms))
