import json
import math
import re
from pathlib import Path

from app.core.config import get_settings
from app.services.ai_gateway import AIGateway


class KnowledgeService:
    STOP_TOKENS = {"请问", "一下", "还有", "有没有", "附近", "哪里", "哪儿", "什么", "几点", "几楼", "是否", "可以", "吗", "呢"}

    def __init__(self, ai_gateway: AIGateway, kb_path: Path | None = None) -> None:
        self.ai_gateway = ai_gateway
        self.kb_path = kb_path or Path(__file__).resolve().parents[1] / "knowledge" / "hotel_kb.json"
        self.settings = get_settings()
        self._items = self._load_items()
        self._item_vectors: list[list[float]] | None = None

    def _load_items(self) -> list[dict[str, object]]:
        try:
            items = json.loads(self.kb_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(f"知识库文件不存在：{self.kb_path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"知识库 JSON 格式错误：{exc}") from exc

        normalized: list[dict[str, object]] = []
        for index, item in enumerate(items):
            raw_keywords = item.get("keywords", [])
            if isinstance(raw_keywords, list):
                keywords = [str(keyword).strip() for keyword in raw_keywords if str(keyword).strip()]
            elif raw_keywords:
                keywords = [str(raw_keywords).strip()]
            else:
                keywords = []

            title = str(item.get("title", "")).strip() or f"知识项{index + 1}"
            content = str(item.get("content") or item.get("answer") or "").strip()
            category = str(item.get("category", "通用")).strip() or "通用"
            normalized.append(
                {
                    "id": str(item.get("id", f"kb_{index:03d}")),
                    "category": category,
                    "title": title,
                    "content": content,
                    "keywords": keywords,
                    "answer": str(item.get("answer") or content).strip(),
                    "search_text": " ".join([category, title, content, " ".join(keywords)]).strip(),
                }
            )
        return normalized

    def answer(self, question: str) -> str:
        candidates = self.retrieve(question.strip())
        if not candidates:
            return "您好，暂时没有查到相关信息，需要客服进一步确认。"

        if self._should_use_local_answer(question, candidates[0]):
            return self._build_fallback_reply(candidates)

        try:
            result = self.ai_gateway.call_structured(
                "knowledge_answer",
                {
                    "question": question.strip(),
                    "knowledge_items": [
                        {
                            "id": item["id"],
                            "category": item["category"],
                            "title": item["title"],
                            "content": item["content"],
                        }
                        for item in candidates
                    ],
                },
            )
            reply = self.ai_gateway.clean_text(str(result.get("reply", "")))
            if result.get("grounded") is True:
                return reply
        except Exception:
            pass
        return self._build_fallback_reply(candidates)

    def retrieve(self, question: str) -> list[dict[str, object]]:
        if not question:
            return []

        lexical_scores = self._lexical_scores(question)
        semantic_scores = self._semantic_scores(question)
        ranked: list[tuple[float, dict[str, object]]] = []
        for index, item in enumerate(self._items):
            lexical = lexical_scores[index]
            semantic = semantic_scores[index]
            score = lexical if semantic <= 0 else (lexical * 0.55 + semantic * 0.45)
            if score < 0.18:
                continue
            enriched = dict(item)
            enriched["retrieval_score"] = round(score, 4)
            ranked.append((score, enriched))

        ranked.sort(key=lambda pair: pair[0], reverse=True)
        top_limit = min(3, self.settings.rag_top_k)
        return [item for _, item in ranked[:top_limit]]

    def _should_use_local_answer(self, question: str, top_candidate: dict[str, object]) -> bool:
        if self.ai_gateway.provider == "mock":
            return "knowledge_answer" not in self.ai_gateway.canned_responses

        compact_question = self._compact(question)
        compact_title = self._compact(str(top_candidate.get("title", "")))
        compact_content = self._compact(str(top_candidate.get("content", "")))
        keywords = [self._compact(str(keyword)) for keyword in top_candidate.get("keywords", [])]
        retrieval_score = float(top_candidate.get("retrieval_score", 0.0))

        if compact_title and compact_title in compact_question:
            return True
        if compact_question and compact_question in compact_content:
            return True
        if any(keyword and keyword in compact_question for keyword in keywords):
            return True
        return retrieval_score >= 1.0

    def _build_fallback_reply(self, candidates: list[dict[str, object]]) -> str:
        if not candidates:
            return "您好，暂时没有查到相关信息，需要客服进一步确认。"
        top = candidates[0]
        content = str(top.get("content", "")).strip()
        return content or "您好，暂时没有查到相关信息，需要客服进一步确认。"

    def _lexical_scores(self, question: str) -> list[float]:
        compact_question = self._compact(question)
        question_tokens = self._tokenize(question)
        scores: list[float] = []
        for item in self._items:
            title = str(item["title"])
            content = str(item["content"])
            keywords = [str(keyword) for keyword in item["keywords"]]
            search_text = str(item["search_text"])

            score = 0.0
            if title and self._compact(title) in compact_question:
                score += 0.55
            if compact_question and compact_question in self._compact(content):
                score += 0.55
            if any(self._compact(keyword) and self._compact(keyword) in compact_question for keyword in keywords):
                score += 0.35

            search_tokens = self._tokenize(search_text)
            overlap_tokens = question_tokens & search_tokens
            overlap = len(overlap_tokens)
            if overlap >= 2:
                score += min(0.6, overlap / max(2, len(question_tokens)))
            elif overlap == 1 and next(iter(overlap_tokens)) not in self.STOP_TOKENS:
                score += 0.2

            if compact_question and compact_question in self._compact(search_text):
                score += 0.35

            scores.append(min(score, 1.5))
        return scores

    def _semantic_scores(self, question: str) -> list[float]:
        if self.ai_gateway.provider == "mock":
            return [0.0 for _ in self._items]
        try:
            if self._item_vectors is None:
                self._item_vectors = self.ai_gateway.embed_texts([str(item["search_text"]) for item in self._items])
            question_vector = self.ai_gateway.embed_texts([question])[0]
        except Exception:
            return [0.0 for _ in self._items]
        return [max(0.0, self._cosine_similarity(question_vector, item_vector)) for item_vector in self._item_vectors]

    @staticmethod
    def _compact(text: str) -> str:
        return re.sub(r"\s+", "", text.lower())

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        lowered = text.lower()
        compact = re.sub(r"\s+", "", lowered)
        ascii_tokens = set(re.findall(r"[a-z0-9]+", lowered))
        cjk_bigrams = {compact[index : index + 2] for index in range(max(0, len(compact) - 1)) if re.search(r"[\u4e00-\u9fff]", compact[index : index + 2])}
        tokens = ascii_tokens | cjk_bigrams
        return {token for token in tokens if token and token not in cls.STOP_TOKENS}

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
