from contextlib import asynccontextmanager
import logging

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
except ModuleNotFoundError:  # pragma: no cover - lets core tests run without optional web deps.
    FastAPI = None
    Request = object
    JSONResponse = None

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app():
    settings = get_settings()
    configure_logging(settings.log_level)
    if FastAPI is None:
        raise RuntimeError("缺少 FastAPI 依赖。请先安装 backend/requirements.txt 后再启动后端服务。")

    @asynccontextmanager
    async def lifespan(_app):
        logger.info("酒店客服自动化系统后端启动")
        yield
        logger.info("酒店客服自动化系统后端关闭")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="演示版酒店客服自动化系统后端 API",
        lifespan=lifespan,
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error_code": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception):
        logger.exception("未处理异常：%s", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error_code": "INTERNAL_ERROR", "message": "系统内部错误，请查看后端日志定位原因。"},
        )

    @app.get("/health")
    async def health():
        return {"success": True, "data": {"status": "ok", "version": settings.app_version}}

    from app.api import complaints, conversation, files, forms, rooms

    for module in (conversation, rooms, forms, complaints, files):
        if module.router is not None:
            app.include_router(module.router)

    return app


app = create_app() if FastAPI is not None else None
