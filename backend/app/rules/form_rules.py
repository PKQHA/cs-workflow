from app.core.errors import BusinessRuleError
from app.schemas.domain import ORDER_STATUSES


def room_status_for_order(order_status: str) -> str:
    if order_status == "已完成":
        return "已住"
    if order_status == "待完成":
        return "已预订"
    raise BusinessRuleError("FORM_STATUS_INVALID", "订单状态必须是 已完成 或 待完成。")


def ensure_valid_order_status(order_status: str) -> None:
    if order_status not in ORDER_STATUSES:
        raise BusinessRuleError("FORM_STATUS_INVALID", "订单状态必须是 已完成 或 待完成。")


def ensure_can_complete_pending(current_status: str) -> None:
    if current_status != "待完成":
        raise BusinessRuleError("FORM_UPDATE_NOT_ALLOWED", "只有待完成表单可以改为已完成。")
