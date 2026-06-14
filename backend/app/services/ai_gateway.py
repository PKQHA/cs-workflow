import json
import logging
import re
from time import perf_counter
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)


class AIGateway:
    def __init__(
        self,
        canned_responses: dict[str, dict[str, Any]] | None = None,
        provider: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self.canned_responses = canned_responses or {}
        self.provider = (provider or settings.model_provider).strip().lower()
        self.model_name = (model_name or settings.model_name).strip()
        self.api_key = api_key if api_key is not None else settings.model_api_key
        self.base_url = (base_url or settings.model_base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.model_timeout_seconds

    def call_structured(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        started = perf_counter()
        fallback_used = False
        try:
            if prompt_name in self.canned_responses:
                return self.canned_responses[prompt_name]
            if self.provider == "mock":
                fallback_used = True
                return self._mock_response(prompt_name, payload)
            return self._call_openai_compatible(prompt_name, payload)
        except AppError:
            raise
        except Exception as exc:
            raise AppError("AI_GATEWAY_FAILED", f"AI 服务调用失败：{exc}") from exc
        finally:
            elapsed_ms = round((perf_counter() - started) * 1000, 2)
            logger.info(
                "AI 网关调用完成 prompt=%s provider=%s fallback=%s elapsed_ms=%s",
                prompt_name,
                self.provider,
                fallback_used,
                elapsed_ms,
            )

    def clean_text(self, text: str | None) -> str:
        if not text:
            raise AppError("AI_RESPONSE_INVALID", "AI 返回为空，无法继续处理。")
        return " ".join(text.strip().split())

    def _call_openai_compatible(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise AppError("AI_PROVIDER_NOT_CONFIGURED", "未配置模型 API Key，无法调用真实大模型。")
        messages = self._build_messages(prompt_name, payload)
        request_body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response_json = self._post_chat_completion(request_body, headers, allow_retry_without_response_format=True)
        content = self._extract_message_text(response_json)
        structured = self._extract_json_object(content)
        if not isinstance(structured, dict):
            raise AppError("AI_RESPONSE_INVALID", "模型未返回合法 JSON 对象。")
        return structured

    def _post_chat_completion(
        self,
        request_body: dict[str, Any],
        headers: dict[str, str],
        allow_retry_without_response_format: bool,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=request_body)
        except httpx.HTTPError as exc:
            raise AppError("AI_GATEWAY_FAILED", f"AI 服务调用失败：{exc}") from exc

        if response.status_code >= 400 and allow_retry_without_response_format and "response_format" in request_body:
            retry_body = {key: value for key, value in request_body.items() if key != "response_format"}
            return self._post_chat_completion(retry_body, headers, allow_retry_without_response_format=False)

        if response.status_code >= 400:
            raise AppError("AI_GATEWAY_FAILED", f"AI 服务返回错误：HTTP {response.status_code}")

        try:
            return response.json()
        except ValueError as exc:
            raise AppError("AI_RESPONSE_INVALID", "AI 服务返回了非 JSON 数据。") from exc

    def _build_messages(self, prompt_name: str, payload: dict[str, Any]) -> list[dict[str, str]]:
        instructions = {
            "intent": (
                "你是酒店客服意图路由器。"
                "你只能返回 JSON。"
                "intent 只能是 qa、booking、unknown。"
                "当问题是酒店信息咨询、房态询问、设施服务说明时，用 qa。"
                "当用户明确要订房、安排房间、询问适合入住方案时，用 booking。"
                "不确定时用 unknown，不要强行归为 booking。"
            ),
            "booking_extract": (
                "你是酒店订房信息抽取器。"
                "你只能返回 JSON。"
                "从用户表达和已有上下文中提取 guest_count、room_count、budget、stay_days、guest_type、preferences。"
                "无法确定的字段返回 null。preferences 返回字符串数组。"
                "不要臆造数字。"
            ),
            "knowledge_answer": (
                "你是酒店客服答疑助手。"
                "你只能依据提供的知识库上下文回答。"
                "如果知识库上下文不足以支撑答案，请返回 grounded=false，并给出保守回复。"
                "只返回 JSON。"
            ),
            "recommendation_copy": (
                "你是酒店订房推荐文案助手。"
                "只能根据提供的候选房间和价格信息生成稳定、简洁的中文推荐理由。"
                "不要修改房号、价格或房态。"
                "只返回 JSON。"
            ),
            "complaint_analysis": (
                "你是酒店投诉理解助手。"
                "你需要提炼 complaint_type、severity，并生成安抚回复和处理建议。"
                "complaint_type 必须使用现有中文类型，severity 必须是 轻度、中度 或 重度。"
                "不确定时可留空，但必须返回合法 JSON。"
            ),
        }
        if prompt_name not in instructions:
            raise AppError("AI_PROMPT_NOT_SUPPORTED", f"暂不支持的 AI prompt：{prompt_name}")
        return [
            {"role": "system", "content": instructions[prompt_name]},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

    @staticmethod
    def _extract_message_text(response_json: dict[str, Any]) -> str:
        try:
            content = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AppError("AI_RESPONSE_INVALID", "AI 返回结构不符合 OpenAI 兼容格式。") from exc
        if isinstance(content, list):
            text_parts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
            content = "".join(text_parts)
        return str(content)

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any]:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except ValueError:
            pass
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise AppError("AI_RESPONSE_INVALID", "AI 返回内容中未找到 JSON 对象。")
        try:
            parsed = json.loads(match.group(0))
        except ValueError as exc:
            raise AppError("AI_RESPONSE_INVALID", "AI 返回的 JSON 解析失败。") from exc
        if not isinstance(parsed, dict):
            raise AppError("AI_RESPONSE_INVALID", "AI 返回的 JSON 不是对象。")
        return parsed

    def _mock_response(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text", ""))
        if prompt_name == "intent":
            qa_words = ("退房", "早餐", "晚饭", "晚餐", "保洁", "发票", "停车", "Wi-Fi", "wifi", "押金", "宠物", "加床")
            if any(word in text for word in qa_words):
                return {"intent": "qa", "confidence": 0.9, "reason": "命中答疑关键词。", "slots": {}}
            booking_words = ("住", "订", "预算", "人", "天", "入住", "房型")
            if any(word in text for word in booking_words):
                return {"intent": "booking", "confidence": 0.8, "reason": "命中订房关键词。", "slots": {}}
            return {"intent": "unknown", "confidence": 0.4, "reason": "未命中明确关键词。", "slots": {}}
        if prompt_name == "booking_extract":
            return {}
        if prompt_name == "knowledge_answer":
            return {"reply": "您好，当前演示知识库暂未覆盖该问题，建议您记录客户诉求后联系前台或值班经理进一步确认。", "grounded": False}
        if prompt_name == "recommendation_copy":
            return {
                "reason_text": "该方案基于当前空房、预算和入住人数生成，价格相对合适。",
                "reply_text": "您好，已根据您的需求为您整理出可选入住方案，您可以直接确认其中一个方案。",
            }
        if prompt_name == "complaint_analysis":
            complaint_type = str(payload.get("type", "服务态度"))
            severity = str(payload.get("severity", "轻度"))
            return {
                "complaint_type": complaint_type,
                "severity": severity,
                "comfort_reply": "非常抱歉给您带来不佳的入住体验，我们会立即记录并协助处理。",
                "solution": "安排工作人员尽快核实并提供现场补救。",
                "compensation": "可根据现场情况提供合理演示补偿。",
                "escalation_note": "该问题建议上报上级，由管理人员进一步跟进。",
                "escalation_summary": text[:120],
            }
        return {}
