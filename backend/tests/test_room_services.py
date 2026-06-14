import unittest

from app.core.errors import BusinessRuleError
from app.services.room_catalog_service import RoomCatalogService
from app.services.room_status_service import RoomStatusService


class RoomServiceTests(unittest.TestCase):
    def test_catalog_has_32_fixed_rooms(self):
        catalog = RoomCatalogService()
        rooms = catalog.list_rooms()
        self.assertEqual(len(rooms), 32)
        self.assertEqual(rooms[0].room_number, "201")
        self.assertEqual(rooms[-1].room_number, "604")

    def test_catalog_filters_by_status_and_category(self):
        catalog = RoomCatalogService({"206": "已住"})
        rooms = catalog.list_rooms(room_status="已住", room_category="特殊房")
        self.assertEqual([room.room_number for room in rooms], ["206"])

    def test_random_initial_occupied_has_7_rooms(self):
        service = RoomStatusService.with_random_initial_occupied(seed=1)
        occupied = service.catalog.list_rooms(room_status="已住")
        self.assertEqual(len(occupied), 7)

    def test_release_occupied_room(self):
        catalog = RoomCatalogService({"201": "已住"})
        service = RoomStatusService(catalog)
        updated = service.release_room_to_available("201")
        self.assertEqual(updated.status, "空房")

    def test_release_available_room_is_blocked(self):
        service = RoomStatusService(RoomCatalogService())
        with self.assertRaises(BusinessRuleError):
            service.release_room_to_available("201")

    def test_build_room_status_reply(self):
        service = RoomStatusService(RoomCatalogService({"207": "已住"}))
        self.assertIn("已住", service.build_room_status_reply("207"))

    def test_build_availability_reply_contains_count(self):
        service = RoomStatusService(RoomCatalogService())
        self.assertIn("可用空房数量", service.build_availability_reply())


if __name__ == "__main__":
    unittest.main()
