import unittest

from pydantic import ValidationError

from app.rules.booking_requirements_rule import get_missing_booking_fields, is_booking_complete, normalize_guest_type
from app.schemas.domain import BookingDraft, Room


class SchemaAndRuleTests(unittest.TestCase):
    def test_room_schema_rejects_invalid_status(self):
        with self.assertRaises(ValidationError):
            Room(
                room_number="201",
                floor=2,
                room_name="单人间",
                capacity_type="单人间",
                room_category="普通房",
                price_per_day=188,
                status="已出租",
                image_url="/static/rooms/201.jpg",
            )

    def test_booking_missing_fields_are_chinese_labels(self):
        draft = BookingDraft(guest_count=2, room_count=1)
        self.assertEqual(get_missing_booking_fields(draft), ["预算", "居住天数"])

    def test_booking_complete_when_required_fields_exist(self):
        draft = BookingDraft(guest_count=2, room_count=1, budget=500, stay_days=2)
        self.assertTrue(is_booking_complete(draft))

    def test_guest_type_defaults_to_multi_person(self):
        draft = BookingDraft(guest_count=3)
        self.assertEqual(normalize_guest_type(draft), "多人")

    def test_guest_type_keeps_couple(self):
        draft = BookingDraft(guest_count=2, guest_type="情侣")
        self.assertEqual(normalize_guest_type(draft), "情侣")


if __name__ == "__main__":
    unittest.main()
