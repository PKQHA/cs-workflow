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
    model_base_url: str | None = None
    model_api_key: str | None = None
    model_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
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


def _load_env_file() -> dict[str, str]:
    env_path = Path(".env")
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env(name: str, default: str | None = None, env_file_values: dict[str, str] | None = None) -> str | None:
    if name in os.environ:
        return os.environ[name]
    if env_file_values and name in env_file_values:
        return env_file_values[name]
    return default


@lru_cache
def get_settings() -> Settings:
    env_file_values = _load_env_file()
    try:
        return Settings(
            app_name=_env("APP_NAME", "酒店客服自动化系统", env_file_values),
            app_version=_env("APP_VERSION", "0.1.0", env_file_values),
            backend_host=_env("BACKEND_HOST", "0.0.0.0", env_file_values),
            backend_port=int(_env("BACKEND_PORT", "7860", env_file_values) or "7860"),
            frontend_backend_url=_env("FRONTEND_BACKEND_URL", "http://localhost:7860", env_file_values),
            excel_work_dir=Path(_env("EXCEL_WORK_DIR", "data", env_file_values) or "data"),
            current_excel_path=_optional_path(_env("CURRENT_EXCEL_PATH", env_file_values=env_file_values)),
            model_provider=_env("MODEL_PROVIDER", "mock", env_file_values),
            model_name=_env("MODEL_NAME", "mock-hotel-assistant", env_file_values),
            model_base_url=_env("MODEL_BASE_URL", _env("OPENAI_BASE_URL", env_file_values=env_file_values), env_file_values),
            model_api_key=_env("MODEL_API_KEY", _env("OPENAI_API_KEY", env_file_values=env_file_values), env_file_values),
            model_timeout_seconds=float(_env("MODEL_TIMEOUT_SECONDS", "20", env_file_values) or "20"),
            log_level=_env("LOG_LEVEL", "INFO", env_file_values),
        )
    except (ValidationError, ValueError) as exc:
        raise RuntimeError(f"配置加载失败：{exc}") from exc
