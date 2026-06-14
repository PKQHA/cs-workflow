try:
    from fastapi import APIRouter, Depends
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None
    Depends = lambda dependency: dependency

from app.api.dependencies import AppContainer, get_container
from app.schemas.common import ok
from app.schemas.requests import ComplaintRequest

router = APIRouter(prefix="/api/complaints", tags=["complaints"]) if APIRouter else None


if router:
    @router.post("/analyze")
    async def analyze_complaint(request: ComplaintRequest, container: AppContainer = Depends(get_container)):
        result = container.complaint_service.analyze(request.text)
        return ok(result.model_dump())
