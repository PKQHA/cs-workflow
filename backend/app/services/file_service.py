from pathlib import Path
import shutil

from app.core.errors import AppError
from app.repositories.excel_repository import ExcelRepository


class FileService:
    def __init__(self, work_dir: Path | str) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.current_excel_path: Path | None = None

    def upload_excel(self, source_path: Path | str, content_type: str | None = None) -> Path:
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
        target = self.work_dir / "current_hotel_data.xlsx"
        shutil.copyfile(source, target)
        ExcelRepository(target).validate()
        self.current_excel_path = target
        return target

    def has_uploaded_excel(self) -> bool:
        return bool(self.current_excel_path and self.current_excel_path.exists())
