class AppError(Exception):
    """Base exception carrying a stable error code and friendly message."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class ExcelNotUploadedError(AppError):
    def __init__(self) -> None:
        super().__init__("EXCEL_NOT_UPLOADED", "未上传 Excel，无法保存数据。请先在文件页面上传 Excel。")


class ExcelRepositoryError(AppError):
    pass


class BusinessRuleError(AppError):
    pass


class NotFoundError(AppError):
    pass
