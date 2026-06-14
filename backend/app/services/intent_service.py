import re

from app.schemas.domain import IntentRouteResult
from app.services.ai_gateway import AIGateway


class IntentService:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self.ai_gateway = ai_gateway

    def route(self, text: str, context_summary: str = "") -> IntentRouteResult:
        rule_result = self._route_by_rules(text)
        if rule_result is not None:
            return rule_result
        fallback_result = self._fallback_route_by_rules(text)
        try:
            result = self.ai_gateway.call_structured("intent", {"text": text, "context": context_summary})
            intent = result.get("intent")
            if intent in {"qa", "booking", "unknown"}:
                route = IntentRouteResult(
                    intent=intent,
                    confidence=float(result.get("confidence", 0.6)),
                    reason=str(result.get("reason", "AI 意图识别结果。")),
                    slots=result.get("slots") or {},
                )
                if route.intent == "unknown" and fallback_result is not None:
                    return fallback_result
                return route
        except Exception:
            pass
        if fallback_result is not None:
            return fallback_result
        return IntentRouteResult(
            intent="unknown",
            confidence=0.3,
            reason="未命中明确规则，且 AI 意图识别未返回可用结果。",
            slots={},
        )

    def detect(self, text: str, context_summary: str = "") -> str:
        return self.route(text, context_summary).intent

    @staticmethod
    def _route_by_rules(text: str) -> IntentRouteResult | None:
        normalized = text.strip()
        room_number = IntentService._extract_room_number(normalized)
        if room_number and IntentService._is_room_status_question(normalized):
            return IntentRouteResult(
                intent="qa",
                confidence=0.98,
                reason="识别到具体房号的房态咨询问题。",
                slots={"room_number": room_number, "qa_type": "room_status"},
            )

        return None

    @staticmethod
    def _fallback_route_by_rules(text: str) -> IntentRouteResult | None:
        normalized = text.strip()
        if IntentService._contains_any(
            normalized,
            ("早餐", "晚饭", "晚餐", "停车", "加床", "退房", "发票", "wifi", "Wi-Fi", "无线", "宠物"),
        ):
            return IntentRouteResult(
                intent="qa",
                confidence=0.92,
                reason="命中酒店信息咨询关键词。",
                slots={"qa_type": "knowledge"},
            )

        if IntentService._contains_any(
            normalized,
            ("订房", "预订", "入住", "安排", "房型", "家庭住", "家庭入住", "多人房", "开房"),
        ) or IntentService._looks_like_booking_request(normalized):
            return IntentRouteResult(
                intent="booking",
                confidence=0.9,
                reason="命中订房意图关键词或订房需求表达。",
                slots={},
            )

        return None

    @staticmethod
    def _extract_room_number(text: str) -> str | None:
        match = re.search(r"(?<!\d)([2-6]0[1-7])(?!\d)", text)
        return match.group(1) if match else None

    @staticmethod
    def _is_room_status_question(text: str) -> bool:
        return IntentService._contains_any(
            text,
            ("空缺", "空房", "空着", "能住", "有人", "有房", "可住", "是否空", "还有吗", "状态"),
        )

    @staticmethod
    def _looks_like_booking_request(text: str) -> bool:
        has_people_or_room_count = bool(re.search(r"\d+\s*(?:人|位|间|房|天|晚)", text))
        return has_people_or_room_count and IntentService._contains_any(
            text,
            ("住", "订", "入住", "安排", "房间", "房型", "晚"),
        )

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        lowered = text.lower()
        return any(keyword.lower() in lowered for keyword in keywords)
