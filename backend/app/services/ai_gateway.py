import json
import logging
import re
from hashlib import sha256
from time import perf_counter
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.prompts.system_prompts import get_prompt

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
        self.embedding_model_name = (settings.embedding_model_name or self.model_name).strip()
        self.embedding_base_url = (settings.embedding_base_url or self.base_url).rstrip("/")
        self.embedding_api_key = settings.embedding_api_key if settings.embedding_api_key is not None else self.api_key
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
                "AI gateway completed prompt=%s provider=%s fallback=%s elapsed_ms=%s",
                prompt_name,
                self.provider,
                fallback_used,
                elapsed_ms,
            )

    def clean_text(self, text: str | None) -> str:
        if not text:
            raise AppError("AI_RESPONSE_INVALID", "AI 返回为空，无法继续处理。")
        return " ".join(text.strip().split())

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.provider == "mock":
            return [self._mock_embedding(text) for text in texts]
        if not self.embedding_api_key:
            raise AppError("AI_PROVIDER_NOT_CONFIGURED", "未配置 Embedding API Key，无法调用向量模型。")
        headers = {"Authorization": f"Bearer {self.embedding_api_key}", "Content-Type": "application/json"}
        request_body = {"model": self.embedding_model_name, "input": texts}
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.embedding_base_url}/embeddings", headers=headers, json=request_body)
        except httpx.HTTPError as exc:
            raise AppError("AI_GATEWAY_FAILED", f"Embedding 调用失败：{exc}") from exc
        if response.status_code >= 400:
            raise AppError("AI_GATEWAY_FAILED", f"Embedding 服务返回错误：HTTP {response.status_code}")
        try:
            response_json = response.json()
            data = response_json["data"]
            return [list(item["embedding"]) for item in sorted(data, key=lambda item: item["index"])]
        except (ValueError, KeyError, TypeError) as exc:
            raise AppError("AI_RESPONSE_INVALID", "Embedding 返回结构不合法。") from exc

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
        try:
            system_prompt = get_prompt(prompt_name)
        except KeyError:
            raise AppError("AI_PROMPT_NOT_SUPPORTED", f"暂不支持的 AI prompt：{prompt_name}")
        return [
            {"role": "system", "content": system_prompt},
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
        lowered = text.lower()
        if prompt_name == "intent":
            if re.search(r"(?<!\d)([2-6]0[1-7])(?!\d)", text) and any(word in text for word in ("空", "住", "房态", "有人", "状态")):
                room_number = re.search(r"(?<!\d)([2-6]0[1-7])(?!\d)", text).group(1)
                return {
                    "intent": "qa",
                    "confidence": 0.99,
                    "reason": "识别为具体房号的房态查询。",
                    "slots": {"room_number": room_number, "qa_type": "room_status"},
                }
            if any(phrase in text for phrase in ("还有空房", "有空房", "还有房吗", "有没有房", "房态")):
                return {"intent": "qa", "confidence": 0.96, "reason": "识别为房态查询。", "slots": {"qa_type": "room_availability"}}
            if any(phrase in text for phrase in ("我要订房", "帮我订房", "预订房间", "安排住宿", "推荐房型")):
                return {"intent": "booking", "confidence": 0.95, "reason": "识别为明确订房意图。", "slots": {}}
            slot_signals = 0
            for pattern in (
                r"\d+\s*(?:人|位)",
                r"\d+\s*(?:间|个房间|间房)",
                r"\d+\s*(?:晚|天)",
                r"预算\s*\d+|\d+\s*(?:元|块)",
                r"今天入住|明天入住|后天入住|\d+月\d+日入住|入住日期",
                r"安静|高楼层|亲子|老人|孩子|情侣|家庭|房型偏好",
            ):
                if re.search(pattern, text):
                    slot_signals += 1
            if slot_signals >= 2:
                return {"intent": "booking", "confidence": 0.92, "reason": "识别到多个订房槽位。", "slots": {}}
            if any(word in lowered for word in ("早餐", "早饭", "晚饭", "晚餐", "餐厅", "发票", "停车", "wifi", "wi-fi", "宠物", "加床", "退房")):
                return {"intent": "qa", "confidence": 0.9, "reason": "识别为酒店咨询问题。", "slots": {"qa_type": "knowledge"}}
            return {"intent": "unknown", "confidence": 0.4, "reason": "暂时无法确定意图。", "slots": {}}
        if prompt_name == "booking_extract":
            return {}
        if prompt_name == "knowledge_answer":
            knowledge_items = payload.get("knowledge_items") or []
            if not knowledge_items:
                return {"reply": "您好，暂时没有查到相关信息，需要客服进一步确认。", "grounded": False}
            first_item = knowledge_items[0]
            content = str(first_item.get("content", "")).strip()
            if not content:
                return {"reply": "您好，暂时没有查到相关信息，需要客服进一步确认。", "grounded": False}
            return {"reply": content, "grounded": True}
        if prompt_name == "recommendation_copy":
            return {
                "reason_text": "该方案基于当前空房、预算和入住人数生成，匹配度较高。",
                "reply_text": "您好，已根据您的需求整理出可选入住方案，您可以直接确认其中一个方案。",
            }
        if prompt_name == "complaint_analysis":
            complaint_type = str(payload.get("type", "服务态度"))
            severity = str(payload.get("severity", "轻度"))
            return {
                "complaint_type": complaint_type,
                "severity": severity,
                "comfort_reply": "非常抱歉给您带来不佳的入住体验，我们会立即记录并协助处理。",
                "solution": "安排工作人员尽快核实并提供现场补救。",
                "compensation": "可根据现场情况提供合理补偿。",
                "escalation_note": "该问题建议上报上级，由管理人员进一步跟进。",
                "escalation_summary": text[:120],
            }
        return {}

    @staticmethod
    def _mock_embedding(text: str) -> list[float]:
        digest = sha256(text.encode("utf-8")).digest()
        return [((byte / 255.0) * 2.0) - 1.0 for byte in digest[:16]]
