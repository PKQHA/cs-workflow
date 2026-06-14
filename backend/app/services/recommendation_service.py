from collections import Counter

from app.core.errors import AppError, BusinessRuleError
from app.rules.recommendation_rules import build_candidate_room_sets, room_descriptor, room_signature
from app.schemas.domain import BookingDraft, RecommendationItem, Room
from app.services.ai_gateway import AIGateway


class RecommendationService:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self.ai_gateway = ai_gateway

    def recommend(self, draft: BookingDraft, available_rooms: list[Room]) -> list[RecommendationItem]:
        candidate_sets = build_candidate_room_sets(draft, available_rooms)
        if not candidate_sets:
            raise BusinessRuleError("NO_RECOMMENDATION_AVAILABLE", "当前空房或预算不足，暂无法生成符合条件的推荐方案。")

        results: list[RecommendationItem] = []
        for index, rooms in enumerate(candidate_sets, start=1):
            signature = room_signature(rooms)
            selectable_room_numbers = self._selectable_room_numbers(signature, available_rooms)
            total_amount = sum(room.price_per_day for room in rooms) * int(draft.stay_days)
            fallback_reason = self._build_reason_text(draft, rooms, selectable_room_numbers, total_amount)
            fallback_reply = self._build_reply_text(rooms, selectable_room_numbers, total_amount)
            try:
                copy = self.ai_gateway.call_structured(
                    "recommendation_copy",
                    {
                        "draft": draft.model_dump(),
                        "rooms": [room.model_dump() for room in rooms],
                        "selectable_room_numbers": selectable_room_numbers,
                        "total_amount": total_amount,
                    },
                )
            except AppError:
                copy = {}
            reason_text = copy.get("reason_text") if self.ai_gateway.provider != "mock" else None
            reply_text = copy.get("reply_text") if self.ai_gateway.provider != "mock" else None
            results.append(
                RecommendationItem(
                    recommendation_id=f"rec_{index:03d}",
                    room_numbers=[room.room_number for room in rooms],
                    selectable_room_numbers=selectable_room_numbers,
                    room_signature=signature,
                    total_amount=total_amount,
                    guest_count=int(draft.guest_count),
                    room_count=int(draft.room_count),
                    stay_days=int(draft.stay_days),
                    guest_type=str(draft.guest_type),
                    reason_text=str(reason_text).strip() if str(reason_text or "").strip() else fallback_reason,
                    reply_text=str(reply_text).strip() if str(reply_text or "").strip() else fallback_reply,
                )
            )
        return results

    def _selectable_room_numbers(self, signature: str, available_rooms: list[Room]) -> list[str]:
        descriptor_counts = Counter(signature.split("|"))
        allowed_descriptors = set(descriptor_counts.keys())
        selectable = [room.room_number for room in available_rooms if self._descriptor_key(room) in allowed_descriptors]
        return sorted(selectable)

    def _build_reason_text(self, draft: BookingDraft, rooms: list[Room], selectable_room_numbers: list[str], total_amount: float) -> str:
        room_summary = self._describe_room_mix(rooms)
        selectable_text = "、".join(selectable_room_numbers)
        return (
            f"根据当前人数、房间数和预算，推荐 {room_summary}。"
            f" {int(draft.stay_days)}晚总费用 {total_amount:.0f} 元，符合预算 {int(draft.budget)} 元。"
            f" 本方案可选空房号为：{selectable_text}，客服可在确认后手动填写最终房号。"
        )

    def _build_reply_text(self, rooms: list[Room], selectable_room_numbers: list[str], total_amount: float) -> str:
        room_summary = self._describe_room_mix(rooms)
        selectable_text = "、".join(selectable_room_numbers)
        return (
            f"您好，当前可为您安排 {room_summary}，总费用约 {total_amount:.0f} 元。"
            f" 可选空房号包括：{selectable_text}。确认后我可以继续为您登记最终房号。"
        )

    def _describe_room_mix(self, rooms: list[Room]) -> str:
        counts = Counter(self._room_label(room) for room in rooms)
        parts = []
        for label, count in counts.items():
            parts.append(f"{count}间{label}")
        return "，".join(parts)

    @staticmethod
    def _room_label(room: Room) -> str:
        if room.special_type:
            return room.special_type
        return room.room_name

    @staticmethod
    def _descriptor_key(room: Room) -> str:
        capacity, category, special, price = room_descriptor(room)
        return f"{capacity}:{category}:{special}:{price:.2f}"
