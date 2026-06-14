from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

try:
    from fastapi import APIRouter, Depends, UploadFile
    from fastapi.responses import FileResponse
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None
    Depends = lambda dependency: dependency
    UploadFile = object
    FileResponse = None

from app.api.dependencies import AppContainer, get_container
from app.schemas.common import ok

router = APIRouter(prefix="/api/files", tags=["files"]) if APIRouter else None


if router:
    @router.post("/upload-excel")
    async def upload_excel(file: UploadFile, container: AppContainer = Depends(get_container)):
        suffix = Path(file.filename or "").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = Path(tmp.name)
            shutil.copyfileobj(file.file, tmp)
        try:
            workspace_id, uploaded = container.file_service.create_workspace_from_upload(temp_path, file.content_type)
            return ok({"workspace_id": workspace_id, "file_name": uploaded.name}, message="Excel 上传成功")
        finally:
            temp_path.unlink(missing_ok=True)

    @router.get("/status")
    async def upload_status(workspace_id: str | None = None, container: AppContainer = Depends(get_container)):
        return ok({"uploaded": container.file_service.has_uploaded_excel(workspace_id), "workspace_id": workspace_id})

    @router.get("/download")
    async def download_excel(workspace_id: str, container: AppContainer = Depends(get_container)):
        path = container.file_service.get_download_path(workspace_id)
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="data.xlsx",
        )
