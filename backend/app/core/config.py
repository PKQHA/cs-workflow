from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel, Field, ValidationError, field_validator


class Settings(BaseModel):
    app_name: str = "酒店客服自动化系统"
    app_version: str = "0.1.0"
    backend_host: str = "0.0.0.0"
    backend_port: int = Field(default=7860, ge=1, le=65535)
    frontend_backend_url: str = "http://localhost:7860"
    excel_work_dir: Path = Path("data")
    current_excel_path: Path | None = None
    model_provider: str = "mock"
    model_name: str = "mock-hotel-assistant"
    model_api_key: str | None = None
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError("LOG_LEVEL 必须是 DEBUG/INFO/WARNING/ERROR/CRITICAL 之一。")
        return normalized

    @field_validator("model_api_key")
    @classmethod
    def require_key_for_real_provider(cls, value: str | None, info) -> str | None:
        provider = info.data.get("model_provider", "mock")
        if provider != "mock" and not value:
            raise ValueError("MODEL_PROVIDER 不是 mock 时必须配置 MODEL_API_KEY。")
        return value


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings(
            app_name=os.getenv("APP_NAME", "酒店客服自动化系统"),
            app_version=os.getenv("APP_VERSION", "0.1.0"),
            backend_host=os.getenv("BACKEND_HOST", "0.0.0.0"),
            backend_port=int(os.getenv("BACKEND_PORT", "7860")),
            frontend_backend_url=os.getenv("FRONTEND_BACKEND_URL", "http://localhost:7860"),
            excel_work_dir=Path(os.getenv("EXCEL_WORK_DIR", "data")),
            current_excel_path=_optional_path(os.getenv("CURRENT_EXCEL_PATH")),
            model_provider=os.getenv("MODEL_PROVIDER", "mock"),
            model_name=os.getenv("MODEL_NAME", "mock-hotel-assistant"),
            model_api_key=os.getenv("MODEL_API_KEY"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
    except (ValidationError, ValueError) as exc:
        raise RuntimeError(f"配置加载失败：{exc}") from exc
