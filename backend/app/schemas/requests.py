from pydantic import BaseModel, Field, field_validator

from app.schemas.domain import ORDER_STATUSES, ROOM_STATUSES


class AnalyzeRequest(BaseModel):
    session_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=5000)


class CreateFormRequest(BaseModel):
    contact_name: str = Field(min_length=1)
    gender: str = Field(min_length=1)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    total_amount: float = Field(gt=0)
    guest_count: int = Field(ge=1)
    guest_type: str = Field(min_length=1)
    stay_days: int = Field(ge=1)
    room_numbers: list[str] = Field(min_length=1)
    order_status: str = "已完成"

    @field_validator("order_status")
    @classmethod
    def validate_order_status(cls, value: str) -> str:
        if value not in ORDER_STATUSES:
            raise ValueError("订单状态必须是 已完成 或 待完成。")
        return value


class FromRecommendationRequest(BaseModel):
    session_id: str = Field(min_length=1)
    recommendation_id: str = Field(min_length=1)
    contact_name: str = Field(min_length=1)
    gender: str = Field(min_length=1)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    order_status: str = "已完成"

    @field_validator("order_status")
    @classmethod
    def validate_order_status(cls, value: str) -> str:
        if value not in ORDER_STATUSES:
            raise ValueError("订单状态必须是 已完成 或 待完成。")
        return value


class UpdateRoomStatusRequest(BaseModel):
    room_number: str = Field(min_length=3, max_length=3)
    target_status: str

    @field_validator("target_status")
    @classmethod
    def validate_target_status(cls, value: str) -> str:
        if value not in ROOM_STATUSES:
            raise ValueError("目标房态必须是 空房、已预订 或 已住。")
        return value


class ComplaintRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
