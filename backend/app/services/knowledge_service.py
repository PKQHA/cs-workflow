import json
from pathlib import Path

from app.services.ai_gateway import AIGateway


class KnowledgeService:
    def __init__(self, ai_gateway: AIGateway, kb_path: Path | None = None) -> None:
        self.ai_gateway = ai_gateway
        self.kb_path = kb_path or Path(__file__).resolve().parents[1] / "knowledge" / "hotel_kb.json"
        self._items = self._load_items()

    def _load_items(self) -> list[dict[str, object]]:
        try:
            return json.loads(self.kb_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(f"知识库文件不存在：{self.kb_path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"知识库 JSON 格式错误：{exc}") from exc

    def answer(self, question: str) -> str:
        for item in self._items:
            if any(keyword.lower() in question.lower() for keyword in item["keywords"]):
                return str(item["answer"])
        return "您好，当前演示知识库暂未覆盖该问题，建议您记录客户诉求后联系前台或值班经理进一步确认。"
