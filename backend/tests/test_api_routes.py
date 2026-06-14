from fastapi.testclient import TestClient

from app.main import create_app


def test_health_and_rooms_api():
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["data"]["status"] == "ok"

    rooms = client.get("/api/rooms")
    assert rooms.status_code == 200
    assert rooms.json()["success"] is True
    assert len(rooms.json()["data"]) == 32


def test_conversation_qa_and_booking_missing_info():
    client = TestClient(create_app())
    qa = client.post("/api/conversation/analyze", json={"session_id": "api_s1", "text": "退房时间是几点"})
    assert qa.status_code == 200
    assert qa.json()["data"]["intent"] == "qa"

    booking = client.post("/api/conversation/analyze", json={"session_id": "api_s2", "text": "我们3个人开2个房间"})
    assert booking.status_code == 200
    assert booking.json()["data"]["status"] == "missing_info"
    assert "预算" in booking.json()["data"]["missing_fields"]


def test_complaint_api():
    client = TestClient(create_app())
    response = client.post("/api/complaints/analyze", json={"text": "床单有污渍，卫生不好"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["complaint_type"] == "卫生"
    assert data["severity"] == "轻度"


def test_create_form_without_excel_returns_error_code():
    client = TestClient(create_app())
    response = client.post(
        "/api/forms/create",
        json={
            "contact_name": "张三",
            "gender": "男",
            "phone": "13800000000",
            "total_amount": 188,
            "guest_count": 1,
            "guest_type": "个人",
            "stay_days": 1,
            "room_numbers": ["201"],
            "order_status": "已完成",
        },
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "EXCEL_NOT_UPLOADED"
