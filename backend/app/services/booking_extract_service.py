import re

from app.rules.booking_requirements_rule import normalize_guest_type
from app.schemas.domain import BookingDraft
from app.services.ai_gateway import AIGateway


class BookingExtractService:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self.ai_gateway = ai_gateway

    def extract(self, text: str, existing: BookingDraft | None = None) -> BookingDraft:
        base = existing or BookingDraft()
        draft = BookingDraft(
            guest_count=self._number_before_any_unit(text, ("人", "位")),
            room_count=self._number_before_any_unit(text, ("间", "房")),
            budget=self._first_float(text, (r"预算\s*(\d+(?:\.\d+)?)", r"(\d+(?:\.\d+)?)\s*(?:r|元|块)")),
            stay_days=self._number_before_any_unit(text, ("天",)) or self._first_int(text, (r"住\s*(\d+)",)),
            guest_type=self._guest_type(text),
            preferences=self._preferences(text),
        )
        merged = base.model_copy(
            update={
                "guest_count": draft.guest_count if draft.guest_count is not None else base.guest_count,
                "room_count": draft.room_count if draft.room_count is not None else base.room_count,
                "budget": draft.budget if draft.budget is not None else base.budget,
                "stay_days": draft.stay_days if draft.stay_days is not None else base.stay_days,
                "guest_type": draft.guest_type if draft.guest_type is not None else base.guest_type,
                "preferences": [*base.preferences, *[p for p in draft.preferences if p not in base.preferences]],
            }
        )
        return merged.model_copy(update={"guest_type": normalize_guest_type(merged)})

    @staticmethod
    def _first_int(text: str, patterns: tuple[str, ...]) -> int | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _number_before_any_unit(text: str, units: tuple[str, ...]) -> int | None:
        for match in re.finditer(r"\d+", text):
            value = match.group(0)
            nearby = text[match.end() : match.end() + 4]
            if any(unit in nearby for unit in units):
                return int(value)
        return None

    @staticmethod
    def _first_float(text: str, patterns: tuple[str, ...]) -> float | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None

    @staticmethod
    def _guest_type(text: str) -> str | None:
        if "团建" in text or "企业" in text:
            return "企业团建"
        if "情侣" in text or "夫妻" in text:
            return "情侣"
        return None

    @staticmethod
    def _preferences(text: str) -> list[str]:
        preferences = []
        if "便宜" in text or "省钱" in text:
            preferences.append("价格优先")
        if "安静" in text:
            preferences.append("安静")
        if "特殊" in text or "套房" in text:
            preferences.append("特殊房")
        return preferences
