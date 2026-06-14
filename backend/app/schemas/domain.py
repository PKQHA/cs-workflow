from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


ROOM_STATUSES = {"空房", "已预订", "已住"}
ORDER_STATUSES = {"已完成", "待完成"}
GUEST_TYPES = {"个人", "多人", "企业团建", "情侣"}
CAPACITY_TYPES = {"单人间", "多人间"}
ROOM_CATEGORIES = {"普通房", "特殊房"}
SPECIAL_TYPES = {"情侣套房", "文创套房"}
COMPLAINT_TYPES = {"卫生", "服务态度", "设施故障", "噪音", "退款"}
SEVERITIES = {"轻度", "中度", "重度"}
GENDERS = {"男", "女", "其他"}


class Room(BaseModel):
    room_number: str = Field(pattern=r"^[2-6]0[1-7]$")
    floor: int = Field(ge=2, le=6)
    room_name: str = Field(min_length=1)
    capacity_type: str
    room_category: str
    special_type: str | None = None
    price_per_day: float = Field(gt=0)
    status: str = "空房"
    image_url: str = Field(min_length=1)

    @field_validator("capacity_type")
    @classmethod
    def validate_capacity_type(cls, value: str) -> str:
        if value not in CAPACITY_TYPES:
            raise ValueError("容量类型必须是 单人间 或 多人间。")
        return value

    @field_validator("room_category")
    @classmethod
    def validate_room_category(cls, value: str) -> str:
        if value not in ROOM_CATEGORIES:
            raise ValueError("房型层级必须是 普通房 或 特殊房。")
        return value

    @field_validator("special_type")
    @classmethod
    def validate_special_type(cls, value: str | None) -> str | None:
        if value is not None and value not in SPECIAL_TYPES:
            raise ValueError("特殊房类型必须是 情侣套房 或 文创套房。")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ROOM_STATUSES:
            raise ValueError("房态必须是 空房、已预订 或 已住。")
        return value


class BookingDraft(BaseModel):
    guest_count: int | None = Field(default=None, ge=1)
    room_count: int | None = Field(default=None, ge=1)
    budget: float | None = Field(default=None, gt=0)
    stay_days: int | None = Field(default=None, ge=1)
    guest_type: str | None = None
    preferences: list[str] = Field(default_factory=list)

    @field_validator("guest_type")
    @classmethod
    def validate_guest_type(cls, value: str | None) -> str | None:
        if value is not None and value not in GUEST_TYPES:
            raise ValueError("客群类型必须是 个人、多人、企业团建 或 情侣。")
        return value


class RecommendationItem(BaseModel):
    recommendation_id: str = Field(min_length=1)
    room_numbers: list[str] = Field(min_length=1)
    selectable_room_numbers: list[str] = Field(default_factory=list)
    room_signature: str = Field(min_length=1)
    total_amount: float = Field(gt=0)
    guest_count: int = Field(ge=1)
    room_count: int = Field(ge=1)
    stay_days: int = Field(ge=1)
    guest_type: str
    reason_text: str = Field(min_length=1)
    reply_text: str = Field(min_length=1)

    @field_validator("guest_type")
    @classmethod
    def validate_guest_type(cls, value: str) -> str:
        if value not in GUEST_TYPES:
            raise ValueError("推荐方案客群类型不合法。")
        return value


class OrderForm(BaseModel):
    form_id: str = Field(min_length=1)
    contact_name: str = Field(min_length=1)
    gender: str
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    total_amount: float = Field(gt=0)
    guest_count: int = Field(ge=1)
    guest_type: str
    checkin_date: date
    stay_days: int = Field(ge=1)
    room_numbers: list[str] = Field(min_length=1)
    order_status: str = "已完成"
    room_status_result: str
    created_at: datetime
    updated_at: datetime

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        if value not in GENDERS:
            raise ValueError("性别必须是 男、女 或 其他。")
        return value

    @field_validator("guest_type")
    @classmethod
    def validate_guest_type(cls, value: str) -> str:
        if value not in GUEST_TYPES:
            raise ValueError("客群类型不合法。")
        return value

    @field_validator("order_status")
    @classmethod
    def validate_order_status(cls, value: str) -> str:
        if value not in ORDER_STATUSES:
            raise ValueError("订单状态必须是 已完成 或 待完成。")
        return value

    @field_validator("room_status_result")
    @classmethod
    def validate_room_status_result(cls, value: str) -> str:
        if value not in ROOM_STATUSES:
            raise ValueError("房态同步结果不合法。")
        return value


class ComplaintCase(BaseModel):
    complaint_type: str
    severity: str
    comfort_reply: str = Field(min_length=1)
    solution: str | None = None
    compensation: str | None = None
    escalation_note: str | None = None
    escalation_summary: str | None = None

    @field_validator("complaint_type")
    @classmethod
    def validate_complaint_type(cls, value: str) -> str:
        if value not in COMPLAINT_TYPES:
            raise ValueError("投诉类型不合法。")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in SEVERITIES:
            raise ValueError("投诉严重程度必须是 轻度、中度 或 重度。")
        return value


class ConversationContext(BaseModel):
    session_id: str = Field(min_length=1)
    history: list[str] = Field(default_factory=list)
    booking_draft: BookingDraft | None = None
    pending_missing_fields: list[str] = Field(default_factory=list)
    recommendations: list[RecommendationItem] = Field(default_factory=list)


class IntentRouteResult(BaseModel):
    intent: str
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1)
    slots: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ExcelRow(BaseModel):
    form_id: str
    contact_name: str
    gender: str
    phone: str
    total_amount: float
    guest_count: int
    guest_type: str
    checkin_date: str
    stay_days: int
    room_numbers_text: str
    order_status: str
    room_status_result: str
    created_at: str
    updated_at: str
