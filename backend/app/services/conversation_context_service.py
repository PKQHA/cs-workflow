from copy import deepcopy

from app.schemas.domain import BookingDraft, ConversationContext, RecommendationItem


class ConversationContextService:
    def __init__(self) -> None:
        self._contexts: dict[str, ConversationContext] = {}

    def get_context(self, session_id: str) -> ConversationContext:
        if session_id not in self._contexts:
            self._contexts[session_id] = ConversationContext(session_id=session_id)
        return deepcopy(self._contexts[session_id])

    def append_history(self, session_id: str, text: str) -> ConversationContext:
        context = self.get_context(session_id)
        context.history.append(text)
        self._contexts[session_id] = context
        return deepcopy(context)

    def merge_booking_draft(self, session_id: str, draft: BookingDraft) -> ConversationContext:
        context = self.get_context(session_id)
        old = context.booking_draft or BookingDraft()
        merged = old.model_copy(
            update={
                "guest_count": draft.guest_count if draft.guest_count is not None else old.guest_count,
                "room_count": draft.room_count if draft.room_count is not None else old.room_count,
                "budget": draft.budget if draft.budget is not None else old.budget,
                "stay_days": draft.stay_days if draft.stay_days is not None else old.stay_days,
                "guest_type": draft.guest_type if draft.guest_type is not None else old.guest_type,
                "preferences": [*old.preferences, *[p for p in draft.preferences if p not in old.preferences]],
            }
        )
        context.booking_draft = merged
        self._contexts[session_id] = context
        return deepcopy(context)

    def save_missing_fields(self, session_id: str, missing_fields: list[str]) -> ConversationContext:
        context = self.get_context(session_id)
        context.pending_missing_fields = missing_fields
        self._contexts[session_id] = context
        return deepcopy(context)

    def save_recommendations(self, session_id: str, recommendations: list[RecommendationItem]) -> ConversationContext:
        context = self.get_context(session_id)
        context.recommendations = recommendations
        self._contexts[session_id] = context
        return deepcopy(context)

    def reset(self, session_id: str) -> ConversationContext:
        self._contexts[session_id] = ConversationContext(session_id=session_id)
        return deepcopy(self._contexts[session_id])
