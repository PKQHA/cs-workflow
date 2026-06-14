try:
    from fastapi import APIRouter, Depends
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None
    Depends = lambda dependency: dependency

from app.api.dependencies import AppContainer, get_container
from app.rules.booking_requirements_rule import get_missing_booking_fields, is_booking_complete
from app.schemas.common import ok
from app.schemas.requests import AnalyzeRequest

router = APIRouter(prefix="/api/conversation", tags=["conversation"]) if APIRouter else None


if router:
    @router.post("/reset")
    async def reset_conversation(request: dict, container: AppContainer = Depends(get_container)):
        session_id = request.get("session_id")
        container.context_service.reset(session_id)
        return ok(message="新对话已开始")

    @router.post("/analyze")
    async def analyze(request: AnalyzeRequest, container: AppContainer = Depends(get_container)):
        context = container.context_service.append_history(request.session_id, request.text)
        intent = container.intent_service.detect(request.text, " ".join(context.history))
        if intent == "qa":
            return ok({"intent": "qa", "reply": container.knowledge_service.answer(request.text)})

        draft = container.booking_extract_service.extract(request.text, context.booking_draft)
        context = container.context_service.merge_booking_draft(request.session_id, draft)
        missing = get_missing_booking_fields(context.booking_draft)
        container.context_service.save_missing_fields(request.session_id, missing)
        if not is_booking_complete(context.booking_draft):
            missing_text = "、".join(missing)
            return ok(
                {
                    "intent": "booking",
                    "status": "missing_info",
                    "missing_fields": missing,
                    "reply": f"当前还缺少{missing_text}，请补充后我再为您推荐方案。",
                }
            )
        recommendations = container.recommendation_service.recommend(
            context.booking_draft,
            container.room_catalog.available_rooms(),
        )
        container.context_service.save_recommendations(request.session_id, recommendations)
        return ok(
            {
                "intent": "booking",
                "status": "recommendations_ready",
                "recommendations": [item.model_dump() for item in recommendations],
            }
        )
