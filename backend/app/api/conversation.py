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
    async def reset_conversation(
        request: dict,
        workspace_id: str | None = None,
        container: AppContainer = Depends(get_container),
    ):
        session_id = request.get("session_id")
        container.context_service.reset(container.context_key(workspace_id, session_id))
        return ok(message="新对话已开始")

    @router.post("/analyze")
    async def analyze(
        request: AnalyzeRequest,
        workspace_id: str | None = None,
        container: AppContainer = Depends(get_container),
    ):
        context_key = container.context_key(workspace_id, request.session_id)
        context = container.context_service.append_history(context_key, request.text)
        route = container.intent_service.route(request.text, " ".join(context.history))
        if route.intent == "qa":
            reply = _build_qa_reply(request.text, route.slots, container, workspace_id)
            return ok(
                {
                    "intent": "qa",
                    "confidence": route.confidence,
                    "reason": route.reason,
                    "slots": route.slots,
                    "reply": reply,
                }
            )
        if route.intent == "unknown":
            return ok(
                {
                    "intent": "unknown",
                    "confidence": route.confidence,
                    "reason": route.reason,
                    "slots": route.slots,
                    "reply": "您好，我可以协助您查询酒店信息或安排订房。请问您现在是想咨询问题，还是需要预订房间？",
                }
            )

        draft = container.booking_extract_service.extract(request.text, context.booking_draft)
        context = container.context_service.merge_booking_draft(context_key, draft)
        missing = get_missing_booking_fields(context.booking_draft)
        container.context_service.save_missing_fields(context_key, missing)
        if not is_booking_complete(context.booking_draft):
            missing_text = "、".join(missing)
            return ok(
                {
                    "intent": "booking",
                    "confidence": route.confidence,
                    "reason": route.reason,
                    "slots": route.slots,
                    "status": "missing_info",
                    "missing_fields": missing,
                    "reply": f"您好，当前还缺少{missing_text}，请补充后我再为您推荐合适房型。",
                }
            )
        recommendations = container.recommendation_service.recommend(
            context.booking_draft,
            container.room_catalog(workspace_id).available_rooms(),
        )
        container.context_service.save_recommendations(context_key, recommendations)
        return ok(
            {
                "intent": "booking",
                "confidence": route.confidence,
                "reason": route.reason,
                "slots": route.slots,
                "status": "recommendations_ready",
                "recommendations": [item.model_dump() for item in recommendations],
            }
        )


def _build_qa_reply(question: str, slots: dict, container: AppContainer, workspace_id: str | None) -> str:
    room_status_service = container.room_status_service(workspace_id)
    qa_type = str(slots.get("qa_type", "")).strip()
    if qa_type == "room_status":
        room_number = str(slots.get("room_number", "")).strip()
        return room_status_service.build_room_status_reply(room_number)
    if qa_type == "room_availability":
        return room_status_service.build_availability_reply()
    return container.knowledge_service.answer(question)
