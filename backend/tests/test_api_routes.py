from fastapi.testclient import TestClient

from app.api.dependencies import container
from app.main import create_app


def _use_mock_gateway():
    container.ai_gateway.provider = "mock"
    container.ai_gateway.api_key = None
    container.ai_gateway.base_url = "https://api.openai.com/v1"


def test_health_and_rooms_api():
    _use_mock_gateway()
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["data"]["status"] == "ok"

    rooms = client.get("/api/rooms")
    assert rooms.status_code == 200
    assert rooms.json()["success"] is True
    room_data = rooms.json()["data"]
    assert len(room_data) == 32
    assert sum(1 for room in room_data if room["status"] == "已住") == 7


def test_conversation_qa_and_booking_missing_info():
    _use_mock_gateway()
    client = TestClient(create_app())
    qa = client.post("/api/conversation/analyze", json={"session_id": "api_s1", "text": "退房时间是几点"})
    assert qa.status_code == 200
    assert qa.json()["data"]["intent"] == "qa"

    booking = client.post("/api/conversation/analyze", json={"session_id": "api_s2", "text": "我们3个人开2个房间"})
    assert booking.status_code == 200
    assert booking.json()["data"]["status"] == "missing_info"
    assert "预算" in booking.json()["data"]["missing_fields"]


def test_conversation_room_status_question_routes_to_qa():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/conversation/analyze", json={"session_id": "api_room", "text": "207房间是否空缺"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "qa"
    assert data["slots"]["room_number"] == "207"
    assert "207 当前是" in data["reply"]


def test_conversation_dinner_question_uses_qa_fallback():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/conversation/analyze", json={"session_id": "api_dinner", "text": "晚饭有什么"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "qa"
    assert data["reply"] == "我暂时没有查到晚餐信息，请客服确认后补充。"


def test_conversation_unknown_intent_does_not_enter_booking():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/conversation/analyze", json={"session_id": "api_unknown", "text": "你好"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "unknown"
    assert "请问您现在需要哪一种" in data["reply"]


def test_complaint_api():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/complaints/analyze", json={"text": "床单有污渍，卫生不好"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["complaint_type"] == "卫生"
    assert data["severity"] == "轻度"


def test_create_form_without_excel_returns_error_code():
    _use_mock_gateway()
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
