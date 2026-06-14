from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str | None = None
    data: T | None = None
    error_code: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


def ok(data: T | None = None, message: str | None = None) -> ApiResponse[T]:
    return ApiResponse(success=True, message=message, data=data)


def fail(error_code: str, message: str) -> ApiResponse[None]:
    return ApiResponse(success=False, error_code=error_code, message=message)
