import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies import container
from app.main import create_app
from app.repositories.excel_repository import ExcelRepository
from app.services.file_service import FileService


def _use_mock_gateway():
    container.ai_gateway.provider = "mock"
    container.ai_gateway.api_key = None
    container.ai_gateway.base_url = "https://api.openai.com/v1"


def _upload_workspace(client: TestClient, file_path: Path) -> str:
    with file_path.open("rb") as file_obj:
        response = client.post(
            "/api/files/upload-excel",
            files={
                "file": (
                    file_path.name,
                    file_obj,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    assert response.status_code == 200
    return response.json()["data"]["workspace_id"]


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
    assert "207 房间当前状态" in data["reply"]


def test_conversation_general_availability_uses_room_status_service():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/conversation/analyze", json={"session_id": "api_avail", "text": "还有空房吗"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "qa"
    assert data["slots"]["qa_type"] == "room_availability"
    assert "可用空房数量" in data["reply"]


def test_conversation_dinner_question_stays_in_qa():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/conversation/analyze", json={"session_id": "api_dinner", "text": "晚饭有什么"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "qa"
    assert "晚餐" in data["reply"]


def test_conversation_semantic_style_queries_hit_knowledge():
    _use_mock_gateway()
    client = TestClient(create_app())

    restaurant = client.post("/api/conversation/analyze", json={"session_id": "api_restaurant", "text": "餐厅在几楼"})
    assert restaurant.status_code == 200
    assert restaurant.json()["data"]["intent"] == "qa"
    assert "二楼" in restaurant.json()["data"]["reply"]

    breakfast = client.post("/api/conversation/analyze", json={"session_id": "api_breakfast", "text": "早餐去哪吃"})
    assert breakfast.status_code == 200
    assert breakfast.json()["data"]["intent"] == "qa"
    assert "餐厅" in breakfast.json()["data"]["reply"]


def test_conversation_unknown_intent_does_not_enter_booking():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/conversation/analyze", json={"session_id": "api_unknown", "text": "你好"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "unknown"
    assert "咨询问题" in data["reply"]


def test_conversation_only_explicit_booking_enters_booking_flow():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/conversation/analyze", json={"session_id": "api_booking", "text": "我要订房"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "booking"
    assert data["status"] == "missing_info"


def test_conversation_missing_knowledge_does_not_hallucinate():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/conversation/analyze", json={"session_id": "api_unknown_kb", "text": "附近有没有剧院"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] in {"qa", "unknown"}
    if data["intent"] == "qa":
        assert "需要客服进一步确认" in data["reply"]


def test_complaint_api():
    _use_mock_gateway()
    client = TestClient(create_app())
    response = client.post("/api/complaints/analyze", json={"text": "房间床单有污渍，卫生不好"})
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


def test_workspace_upload_and_download_flow():
    _use_mock_gateway()
    with tempfile.TemporaryDirectory() as tmp:
        old_file_service = container.file_service
        try:
            container.file_service = FileService(Path(tmp))
            source = ExcelRepository.create_template(Path(tmp) / "source.xlsx")
            client = TestClient(create_app())

            workspace_id = _upload_workspace(client, source)
            status = client.get("/api/files/status", params={"workspace_id": workspace_id})
            download = client.get("/api/files/download", params={"workspace_id": workspace_id})

            assert status.status_code == 200
            assert status.json()["data"]["uploaded"] is True
            assert download.status_code == 200
            assert "attachment; filename=\"data.xlsx\"" in download.headers["content-disposition"]
            assert download.content
        finally:
            container.file_service = old_file_service


def test_workspace_isolation_for_forms_and_rooms():
    _use_mock_gateway()
    with tempfile.TemporaryDirectory() as tmp:
        old_file_service = container.file_service
        try:
            container.file_service = FileService(Path(tmp))
            source = ExcelRepository.create_template(Path(tmp) / "source.xlsx")
            client = TestClient(create_app())

            workspace_a = _upload_workspace(client, source)
            workspace_b = _upload_workspace(client, source)

            created = client.post(
                "/api/forms/create",
                params={"workspace_id": workspace_a},
                json={
                    "contact_name": "张三",
                    "gender": "男",
                    "phone": "13800000000",
                    "total_amount": 188,
                    "guest_count": 1,
                    "guest_type": "个人",
                    "stay_days": 1,
                    "room_numbers": ["201"],
                    "order_status": "待完成",
                },
            )
            assert created.status_code == 200

            pending_a = client.get("/api/forms/pending", params={"workspace_id": workspace_a})
            pending_b = client.get("/api/forms/pending", params={"workspace_id": workspace_b})
            rooms_a = client.get("/api/rooms", params={"workspace_id": workspace_a, "room_status": "已预订"})
            rooms_b = client.get("/api/rooms", params={"workspace_id": workspace_b, "room_status": "已预订"})

            assert len(pending_a.json()["data"]) == 1
            assert pending_b.json()["data"] == []
            assert [room["room_number"] for room in rooms_a.json()["data"]] == ["201"]
            assert rooms_b.json()["data"] == []
        finally:
            container.file_service = old_file_service


def test_workspace_scopes_conversation_context_for_recommendation_form():
    _use_mock_gateway()
    with tempfile.TemporaryDirectory() as tmp:
        old_file_service = container.file_service
        try:
            container.file_service = FileService(Path(tmp))
            source = ExcelRepository.create_template(Path(tmp) / "source.xlsx")
            client = TestClient(create_app())

            workspace_a = _upload_workspace(client, source)
            workspace_b = _upload_workspace(client, source)
            session_id = "shared_session"

            response = client.post(
                "/api/conversation/analyze",
                params={"workspace_id": workspace_a},
                json={"session_id": session_id, "text": "我们3个人，开1个房间，预算500元，住1天"},
            )
            assert response.status_code == 200
            recommendation = response.json()["data"]["recommendations"][0]

            missing_recommendation = client.post(
                "/api/forms/from-recommendation",
                params={"workspace_id": workspace_b},
                json={
                    "session_id": session_id,
                    "recommendation_id": recommendation["recommendation_id"],
                    "contact_name": "李四",
                    "gender": "男",
                    "phone": "13800000000",
                    "selected_room_numbers": recommendation["room_numbers"],
                    "order_status": "待完成",
                },
            )
            assert missing_recommendation.status_code == 400
            assert missing_recommendation.json()["error_code"] == "RECOMMENDATION_NOT_FOUND"
        finally:
            container.file_service = old_file_service
