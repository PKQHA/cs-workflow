from app.services.ai_gateway import AIGateway


class IntentService:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self.ai_gateway = ai_gateway

    def detect(self, text: str, context_summary: str = "") -> str:
        try:
            result = self.ai_gateway.call_structured("intent", {"text": text, "context": context_summary})
            intent = result.get("intent")
            return intent if intent in {"qa", "booking"} else "qa"
        except Exception:
            return "booking" if any(word in text for word in ("住", "订房", "房间", "预算")) else "qa"
