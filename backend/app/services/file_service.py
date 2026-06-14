from __future__ import annotations

from pathlib import Path
import re
import shutil
from uuid import uuid4

from app.core.errors import AppError, NotFoundError
from app.repositories.excel_repository import ExcelRepository

WORKSPACES_DIR_NAME = "workspaces"
WORKSPACE_FILE_NAME = "data.xlsx"
WORKSPACE_ID_PATTERN = re.compile(r"^ws_[0-9a-f]{12}$")


class FileService:
    def __init__(self, work_dir: Path | str) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def create_workspace_from_upload(self, source_path: Path | str, content_type: str | None = None) -> tuple[str, Path]:
        source = Path(source_path)
        if source.suffix.lower() != ".xlsx":
            raise AppError("EXCEL_INVALID_FORMAT", "上传失败：仅支持 .xlsx Excel 文件。")
        if content_type and content_type not in {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        }:
            raise AppError("EXCEL_INVALID_FORMAT", "上传失败：文件 MIME 类型不是有效的 Excel 类型。")
        if not source.exists() or source.stat().st_size == 0:
            raise AppError("UPLOAD_FAILED", "上传失败：文件为空或不存在。")

        workspace_id = f"ws_{uuid4().hex[:12]}"
        target = self.get_workspace_excel_path(workspace_id, ensure_workspace=True)
        shutil.copyfile(source, target)
        ExcelRepository(target).initialize_template()
        return workspace_id, target

    def get_workspace_excel_path(self, workspace_id: str, ensure_workspace: bool = False) -> Path:
        normalized = self._normalize_workspace_id(workspace_id)
        workspace_dir = self.workspaces_dir / normalized
        if ensure_workspace:
            workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir / WORKSPACE_FILE_NAME

    def has_uploaded_excel(self, workspace_id: str | None) -> bool:
        if not workspace_id:
            return False
        return self.get_workspace_excel_path(workspace_id).exists()

    def require_workspace_excel_path(self, workspace_id: str) -> Path:
        path = self.get_workspace_excel_path(workspace_id)
        if not path.exists():
            raise NotFoundError("WORKSPACE_NOT_FOUND", "未找到对应的工作区文件，请重新上传 Excel。")
        return path

    def get_download_path(self, workspace_id: str) -> Path:
        return self.require_workspace_excel_path(workspace_id)

    @property
    def workspaces_dir(self) -> Path:
        path = self.work_dir / WORKSPACES_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _normalize_workspace_id(workspace_id: str | None) -> str:
        normalized = str(workspace_id or "").strip()
        if not WORKSPACE_ID_PATTERN.fullmatch(normalized):
            raise AppError("WORKSPACE_INVALID", "工作区标识不合法，请重新上传 Excel。")
        return normalized
