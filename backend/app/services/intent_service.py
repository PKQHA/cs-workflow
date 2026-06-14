import re

from app.schemas.domain import IntentRouteResult
from app.services.ai_gateway import AIGateway


class IntentService:
    EXPLICIT_BOOKING_PHRASES = (
        "我要订房",
        "帮我订房",
        "预订房间",
        "预定房间",
        "安排住宿",
        "推荐房型",
        "推荐房间",
        "帮我安排房间",
    )
    QA_KEYWORDS = (
        "早餐",
        "早饭",
        "晚饭",
        "晚餐",
        "餐厅",
        "退房",
        "入住流程",
        "发票",
        "停车",
        "wifi",
        "wi-fi",
        "无线网",
        "宠物",
        "加床",
        "保洁",
        "清洁",
        "押金",
        "洗衣",
        "叫醒",
        "早餐在哪",
        "去哪吃",
    )
    BOOKING_SIGNAL_PATTERNS = (
        r"\d+\s*(?:个)?(?:人|位)",
        r"\d+\s*(?:间|个房间|间房)",
        r"\d+\s*(?:晚|天)",
        r"预算\s*\d+|\d+\s*(?:元|块)",
        r"今天入住|明天入住|后天入住|\d+月\d+日入住|入住日期",
        r"安静|高楼层|亲子|老人|孩子|情侣|家庭|房型偏好",
    )

    def __init__(self, ai_gateway: AIGateway) -> None:
        self.ai_gateway = ai_gateway

    def route(self, text: str, context_summary: str = "") -> IntentRouteResult:
        rule_result = self._route_by_rules(text)
        if rule_result is not None:
            return rule_result

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
                if route.intent == "booking" and not self._should_accept_booking(text):
                    return IntentRouteResult(
                        intent="unknown",
                        confidence=0.45,
                        reason="未满足明确订房或隐式订房条件，先进入澄清。",
                        slots={},
                    )
                return route
        except Exception:
            pass

        return IntentRouteResult(
            intent="unknown",
            confidence=0.3,
            reason="未命中明确规则，且 AI 意图识别未返回可用结果。",
            slots={},
        )

    def detect(self, text: str, context_summary: str = "") -> str:
        return self.route(text, context_summary).intent

    @classmethod
    def _route_by_rules(cls, text: str) -> IntentRouteResult | None:
        normalized = text.strip()
        room_number = cls._extract_room_number(normalized)
        if room_number and cls._is_room_status_question(normalized):
            return IntentRouteResult(
                intent="qa",
                confidence=0.99,
                reason="识别为具体房号的房态查询。",
                slots={"room_number": room_number, "qa_type": "room_status"},
            )

        if cls._is_general_room_status_question(normalized):
            return IntentRouteResult(
                intent="qa",
                confidence=0.97,
                reason="识别为房态或空房查询。",
                slots={"qa_type": "room_availability"},
            )

        if cls._contains_explicit_booking_intent(normalized) or cls._has_booking_slot_bundle(normalized):
            return IntentRouteResult(
                intent="booking",
                confidence=0.95,
                reason="识别到明确订房表达或多个订房槽位。",
                slots={},
            )

        if cls._contains_any(normalized, cls.QA_KEYWORDS):
            return IntentRouteResult(
                intent="qa",
                confidence=0.92,
                reason="识别到酒店咨询或服务政策问题。",
                slots={"qa_type": "knowledge"},
            )
        return None

    @classmethod
    def _should_accept_booking(cls, text: str) -> bool:
        normalized = text.strip()
        return cls._contains_explicit_booking_intent(normalized) or cls._has_booking_slot_bundle(normalized)

    @classmethod
    def _contains_explicit_booking_intent(cls, text: str) -> bool:
        lowered = text.lower()
        return any(phrase.lower() in lowered for phrase in cls.EXPLICIT_BOOKING_PHRASES)

    @classmethod
    def _extract_room_number(cls, text: str) -> str | None:
        match = re.search(r"(?<!\d)([2-6]0[1-7])(?!\d)", text)
        return match.group(1) if match else None

    @classmethod
    def _is_room_status_question(cls, text: str) -> bool:
        return cls._contains_any(text, ("空缺", "空房", "空着", "能住", "有人", "已住", "可住", "是否空", "状态"))

    @classmethod
    def _is_general_room_status_question(cls, text: str) -> bool:
        return cls._contains_any(
            text,
            ("还有空房", "有空房", "还有房吗", "有没有房", "空房吗", "房态", "是否已住", "是不是已住"),
        )

    @classmethod
    def _has_booking_slot_bundle(cls, text: str) -> bool:
        signal_count = 0
        for pattern in cls.BOOKING_SIGNAL_PATTERNS:
            if re.search(pattern, text):
                signal_count += 1
        return signal_count >= 2

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        lowered = text.lower()
        return any(keyword.lower() in lowered for keyword in keywords)
