import logging
from typing import Any

from app.core.errors import AppError

logger = logging.getLogger(__name__)


class AIGateway:
    def __init__(self, canned_responses: dict[str, dict[str, Any]] | None = None) -> None:
        self.canned_responses = canned_responses or {}

    def call_structured(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        logger.info("调用 AI 网关 prompt=%s", prompt_name)
        try:
            if prompt_name in self.canned_responses:
                return self.canned_responses[prompt_name]
            return self._mock_response(prompt_name, payload)
        except AppError:
            raise
        except Exception as exc:
            raise AppError("AI_GATEWAY_FAILED", f"AI 服务调用失败：{exc}") from exc

    def clean_text(self, text: str | None) -> str:
        if not text:
            raise AppError("AI_RESPONSE_INVALID", "AI 返回为空，无法继续处理。")
        return " ".join(text.strip().split())

    def _mock_response(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text", ""))
        if prompt_name == "intent":
            qa_words = ("退房", "早餐", "保洁", "发票", "停车", "Wi-Fi", "wifi", "押金", "宠物", "加床")
            if any(word in text for word in qa_words):
                return {"intent": "qa"}
            booking_words = ("住", "订", "房", "间", "预算", "人", "天")
            return {"intent": "booking" if any(word in text for word in booking_words) else "qa"}
        if prompt_name == "recommendation_copy":
            return {
                "reason_text": "该方案基于当前空房、预算和入住人数生成，价格相对合适。",
                "reply_text": "您好，已根据您的需求为您整理出可选入住方案，您可以直接确认其中一个方案。",
            }
        if prompt_name == "complaint_copy":
            return {
                "comfort_reply": "非常抱歉给您带来不佳的入住体验，我们会立即记录并协助处理。",
                "solution": "安排工作人员尽快核实并提供现场补救。",
                "compensation": "可根据现场情况提供合理演示补偿。",
                "escalation_note": "该问题建议上报上级，由管理人员进一步跟进。",
                "escalation_summary": text[:120],
            }
        return {}
