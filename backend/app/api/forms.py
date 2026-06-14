try:
    from fastapi import APIRouter, Depends
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None
    Depends = lambda dependency: dependency

from app.core.errors import NotFoundError
from app.api.dependencies import AppContainer, get_container
from app.schemas.common import ok
from app.schemas.requests import CreateFormRequest, FromRecommendationRequest

router = APIRouter(prefix="/api/forms", tags=["forms"]) if APIRouter else None


if router:
    @router.post("/create")
    async def create_form(request: CreateFormRequest, container: AppContainer = Depends(get_container)):
        form = container.form_service().create_form(request)
        return ok(form.model_dump(), message="表单创建成功")

    @router.post("/from-recommendation")
    async def create_from_recommendation(
        request: FromRecommendationRequest,
        container: AppContainer = Depends(get_container),
    ):
        context = container.context_service.get_context(request.session_id)
        recommendation = next(
            (item for item in context.recommendations if item.recommendation_id == request.recommendation_id),
            None,
        )
        if recommendation is None:
            raise NotFoundError("RECOMMENDATION_NOT_FOUND", "未找到对应推荐方案，请重新生成推荐。")
        form = container.form_service().create_from_recommendation(request, recommendation)
        return ok(form.model_dump(), message="推荐方案已转为表单")

    @router.get("/pending")
    async def list_pending_forms(container: AppContainer = Depends(get_container)):
        return ok(container.form_service().list_pending_forms())

    @router.post("/complete")
    async def complete_pending_form(request: dict, container: AppContainer = Depends(get_container)):
        form_id = request.get("form_id")
        form = container.form_service().complete_pending_form(form_id)
        return ok(form.model_dump(), message="待完成表单已更新为已完成")
