from datetime import date

from app.schemas.domain import BookingDraft

REQUIRED_FIELDS = ("guest_count", "room_count", "budget", "stay_days")
FIELD_LABELS = {
    "guest_count": "人数",
    "room_count": "房间数",
    "budget": "预算",
    "stay_days": "居住天数",
}


def get_missing_booking_fields(draft: BookingDraft) -> list[str]:
    return [FIELD_LABELS[field] for field in REQUIRED_FIELDS if getattr(draft, field) in (None, "")]


def is_booking_complete(draft: BookingDraft) -> bool:
    return not get_missing_booking_fields(draft)


def normalize_guest_type(draft: BookingDraft) -> str | None:
    if draft.guest_type in {"企业团建", "情侣"}:
        return draft.guest_type
    if draft.guest_count == 1:
        return "个人"
    if draft.guest_count and draft.guest_count > 1:
        return "多人"
    return draft.guest_type


def get_system_checkin_date() -> date:
    return date.today()
