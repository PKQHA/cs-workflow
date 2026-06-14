from datetime import datetime
from uuid import uuid4

from app.core.errors import ExcelNotUploadedError, NotFoundError
from app.repositories.excel_repository import ExcelRepository
from app.rules.booking_requirements_rule import get_system_checkin_date
from app.rules.form_rules import ensure_can_complete_pending, ensure_valid_order_status, room_status_for_order
from app.rules.room_rules import ensure_rooms_are_available
from app.schemas.domain import OrderForm
from app.schemas.requests import CreateFormRequest, FromRecommendationRequest
from app.services.room_catalog_service import RoomCatalogService


class FormService:
    def __init__(self, excel_repository: ExcelRepository | None, room_catalog: RoomCatalogService) -> None:
        self.excel_repository = excel_repository
        self.room_catalog = room_catalog

    def create_form(self, request: CreateFormRequest) -> OrderForm:
        if not self.excel_repository:
            raise ExcelNotUploadedError()
        ensure_valid_order_status(request.order_status)
        rooms = [self.room_catalog.get_room(room_number) for room_number in request.room_numbers]
        ensure_rooms_are_available([room for room in rooms if room is not None])
        if any(room is None for room in rooms):
            missing = [request.room_numbers[index] for index, room in enumerate(rooms) if room is None]
            raise NotFoundError("ROOM_NOT_FOUND", f"房间不存在：{'、'.join(missing)}")

        now = datetime.now()
        room_status = room_status_for_order(request.order_status)
        form = OrderForm(
            form_id=f"form_{uuid4().hex[:12]}",
            contact_name=request.contact_name,
            gender=request.gender,
            phone=request.phone,
            total_amount=request.total_amount,
            guest_count=request.guest_count,
            guest_type=request.guest_type,
            checkin_date=get_system_checkin_date(),
            stay_days=request.stay_days,
            room_numbers=request.room_numbers,
            order_status=request.order_status,
            room_status_result=room_status,
            created_at=now,
            updated_at=now,
        )
        self.excel_repository.append_form(form)
        for room_number in request.room_numbers:
            self.room_catalog.set_status(room_number, room_status)
            self.excel_repository.update_room_status(room_number, room_status)
        return form

    def create_from_recommendation(self, request: FromRecommendationRequest, recommendation) -> OrderForm:
        create_request = CreateFormRequest(
            contact_name=request.contact_name,
            gender=request.gender,
            phone=request.phone,
            total_amount=recommendation.total_amount,
            guest_count=recommendation.guest_count,
            guest_type=recommendation.guest_type,
            stay_days=recommendation.stay_days,
            room_numbers=recommendation.room_numbers,
            order_status=request.order_status,
        )
        return self.create_form(create_request)

    def list_pending_forms(self) -> list[dict[str, str]]:
        if not self.excel_repository:
            raise ExcelNotUploadedError()
        return self.excel_repository.list_pending_forms()

    def complete_pending_form(self, form_id: str) -> OrderForm:
        if not self.excel_repository:
            raise ExcelNotUploadedError()
        record = self.excel_repository.get_form_record(form_id)
        if record is None:
            raise NotFoundError("FORM_NOT_FOUND", f"表单 {form_id} 不存在。")
        ensure_can_complete_pending(str(record["订单状态"]))
        now = datetime.now()
        form = OrderForm(
            form_id=str(record["表单唯一标识"]),
            contact_name=str(record["联系人"]),
            gender=str(record["性别"]),
            phone=str(record["手机号"]),
            total_amount=float(record["总金额"]),
            guest_count=int(record["人数"]),
            guest_type=str(record["人数类型"]),
            checkin_date=__import__("datetime").date.fromisoformat(str(record["入住日期"])),
            stay_days=int(record["居住天数"]),
            room_numbers=str(record["房间号"]).split(","),
            order_status="已完成",
            room_status_result="已住",
            created_at=__import__("datetime").datetime.fromisoformat(str(record["创建时间"])),
            updated_at=now,
        )
        self.excel_repository.update_form(form)
        for room_number in form.room_numbers:
            self.room_catalog.set_status(room_number, "已住")
            self.excel_repository.update_room_status(room_number, "已住")
        return form
