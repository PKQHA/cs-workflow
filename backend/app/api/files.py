from pathlib import Path
import shutil
import tempfile

try:
    from fastapi import APIRouter, Depends, UploadFile
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None
    Depends = lambda dependency: dependency
    UploadFile = object

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
            uploaded = container.file_service.upload_excel(temp_path, file.content_type)
            return ok({"file_name": uploaded.name}, message="Excel 上传成功")
        finally:
            temp_path.unlink(missing_ok=True)

    @router.get("/status")
    async def upload_status(container: AppContainer = Depends(get_container)):
        return ok({"uploaded": container.file_service.has_uploaded_excel()})
