import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from app.core.errors import ExcelNotUploadedError, ExcelRepositoryError
from app.repositories.excel_repository import ExcelRepository
from app.schemas.requests import CreateFormRequest
from app.services.form_service import FormService
from app.services.room_catalog_service import RoomCatalogService


class ExcelAndFormTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.excel_path = Path(self.tmpdir.name) / "hotel.xlsx"
        ExcelRepository.create_template(self.excel_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_append_and_update_pending_form(self):
        catalog = RoomCatalogService()
        repository = ExcelRepository(self.excel_path)
        service = FormService(repository, catalog)
        created = service.create_form(
            CreateFormRequest(
                contact_name="张三",
                gender="男",
                phone="13800000000",
                total_amount=268,
                guest_count=2,
                guest_type="多人",
                stay_days=1,
                room_numbers=["202"],
                order_status="待完成",
            )
        )
        self.assertEqual(catalog.get_room("202").status, "已预订")
        pending = service.list_pending_forms()
        self.assertEqual(len(pending), 1)

        completed = service.complete_pending_form(created.form_id)
        self.assertEqual(completed.order_status, "已完成")
        self.assertEqual(catalog.get_room("202").status, "已住")
        self.assertEqual(service.list_pending_forms(), [])

    def test_create_completed_form_sets_room_occupied(self):
        catalog = RoomCatalogService()
        repository = ExcelRepository(self.excel_path)
        service = FormService(repository, catalog)
        created = service.create_form(
            CreateFormRequest(
                contact_name="李四",
                gender="女",
                phone="13900000000",
                total_amount=188,
                guest_count=1,
                guest_type="个人",
                stay_days=1,
                room_numbers=["201"],
                order_status="已完成",
            )
        )
        self.assertEqual(created.room_status_result, "已住")
        self.assertEqual(catalog.get_room("201").status, "已住")

    def test_unuploaded_excel_blocks_form_creation(self):
        service = FormService(None, RoomCatalogService())
        with self.assertRaises(ExcelNotUploadedError):
            service.create_form(
                CreateFormRequest(
                    contact_name="张三",
                    gender="男",
                    phone="13800000000",
                    total_amount=188,
                    guest_count=1,
                    guest_type="个人",
                    stay_days=1,
                    room_numbers=["201"],
                )
            )

    def test_missing_header_is_reported(self):
        workbook = load_workbook(self.excel_path)
        sheet = workbook["订单表单"]
        sheet.cell(row=1, column=2, value="错误表头")
        workbook.save(self.excel_path)
        workbook.close()
        repository = ExcelRepository(self.excel_path)
        with self.assertRaises(ExcelRepositoryError) as ctx:
            repository.validate()
        self.assertEqual(ctx.exception.error_code, "EXCEL_INVALID_FORMAT")
        self.assertIn("联系人", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()
