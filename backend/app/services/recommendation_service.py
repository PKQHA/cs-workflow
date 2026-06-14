from app.core.errors import BusinessRuleError
from app.rules.recommendation_rules import build_candidate_room_sets
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
            total_amount = sum(room.price_per_day for room in rooms) * int(draft.stay_days)
            copy = self.ai_gateway.call_structured(
                "recommendation_copy",
                {"draft": draft.model_dump(), "rooms": [room.model_dump() for room in rooms], "total_amount": total_amount},
            )
            results.append(
                RecommendationItem(
                    recommendation_id=f"rec_{index:03d}",
                    room_numbers=[room.room_number for room in rooms],
                    total_amount=total_amount,
                    guest_count=int(draft.guest_count),
                    room_count=int(draft.room_count),
                    stay_days=int(draft.stay_days),
                    guest_type=str(draft.guest_type),
                    reason_text=copy.get("reason_text", "该方案符合当前人数、预算和房态要求。"),
                    reply_text=copy.get("reply_text", "您好，已为您整理出可入住方案，请确认是否选择。"),
                )
            )
        return results
