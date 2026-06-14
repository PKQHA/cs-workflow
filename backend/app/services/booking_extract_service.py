import re

from app.rules.booking_requirements_rule import normalize_guest_type
from app.schemas.domain import BookingDraft
from app.services.ai_gateway import AIGateway


class BookingExtractService:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self.ai_gateway = ai_gateway

    def extract(self, text: str, existing: BookingDraft | None = None) -> BookingDraft:
        base = existing or BookingDraft()
        model_draft = self._extract_with_model(text, base)
        rule_draft = self._extract_with_rules(text)
        merged = base.model_copy(
            update={
                "guest_count": self._choose_value(model_draft.guest_count, rule_draft.guest_count, base.guest_count),
                "room_count": self._choose_value(model_draft.room_count, rule_draft.room_count, base.room_count),
                "budget": self._choose_value(model_draft.budget, rule_draft.budget, base.budget),
                "stay_days": self._choose_value(model_draft.stay_days, rule_draft.stay_days, base.stay_days),
                "guest_type": self._choose_value(model_draft.guest_type, rule_draft.guest_type, base.guest_type),
                "preferences": self._merge_preferences(base.preferences, model_draft.preferences, rule_draft.preferences),
            }
        )
        return merged.model_copy(update={"guest_type": normalize_guest_type(merged)})

    def _extract_with_model(self, text: str, base: BookingDraft) -> BookingDraft:
        try:
            result = self.ai_gateway.call_structured(
                "booking_extract",
                {"text": text, "existing": base.model_dump()},
            )
        except Exception:
            return BookingDraft()
        preferences = result.get("preferences")
        return BookingDraft(
            guest_count=self._coerce_positive_int(result.get("guest_count")),
            room_count=self._coerce_positive_int(result.get("room_count")),
            budget=self._coerce_positive_float(result.get("budget")),
            stay_days=self._coerce_positive_int(result.get("stay_days")),
            guest_type=self._coerce_guest_type(result.get("guest_type")),
            preferences=[str(item).strip() for item in preferences if str(item).strip()] if isinstance(preferences, list) else [],
        )

    def _extract_with_rules(self, text: str) -> BookingDraft:
        return BookingDraft(
            guest_count=self._extract_guest_count(text),
            room_count=self._extract_room_count(text),
            budget=self._extract_budget(text),
            stay_days=self._extract_stay_days(text),
            guest_type=self._guest_type(text),
            preferences=self._preferences(text),
        )

    def _extract_guest_count(self, text: str) -> int | None:
        return self._first_int(text, (r"(\d+)\s*(?:个)?(?:人|位)",))

    def _extract_room_count(self, text: str) -> int | None:
        return self._first_int(text, (r"(\d+)\s*(?:间房|个房间|间|房)",))

    def _extract_stay_days(self, text: str) -> int | None:
        return self._first_int(text, (r"(\d+)\s*(?:天|晚)", r"住\s*(\d+)"))

    def _extract_budget(self, text: str) -> float | None:
        explicit_budget = self._first_float(
            text,
            (
                r"预算\s*(\d+(?:\.\d+)?)",
                r"(\d+(?:\.\d+)?)\s*(?:r|rb|rmb|元|块|块钱)",
            ),
        )
        if explicit_budget is not None:
            return explicit_budget

        number_candidates = [int(match.group(0)) for match in re.finditer(r"\d+", text)]
        filtered_candidates = [value for value in number_candidates if value >= 100]
        return float(filtered_candidates[0]) if filtered_candidates else None

    @staticmethod
    def _first_int(text: str, patterns: tuple[str, ...]) -> int | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return int(match.group(1))
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

    @staticmethod
    def _choose_value(model_value, rule_value, base_value):
        if model_value not in (None, "", []):
            return model_value
        if rule_value not in (None, "", []):
            return rule_value
        return base_value

    @staticmethod
    def _merge_preferences(*groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                if item not in merged:
                    merged.append(item)
        return merged

    @staticmethod
    def _coerce_positive_int(value: object) -> int | None:
        try:
            if value in (None, ""):
                return None
            number = int(float(str(value)))
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    @staticmethod
    def _coerce_positive_float(value: object) -> float | None:
        try:
            if value in (None, ""):
                return None
            number = float(str(value))
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    @staticmethod
    def _coerce_guest_type(value: object) -> str | None:
        normalized = str(value).strip() if value not in (None, "") else None
        if normalized in {"个人", "多人", "企业团建", "情侣"}:
            return normalized
        return None
