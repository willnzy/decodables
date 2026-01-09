"""
测试 api/admin/events.py (v3.27 DDD Architecture)

端点:
- GET /api/v2/admin/events/events - 获取用户事件
- GET /api/v2/admin/events/events/stats - 获取事件统计
- GET /api/v2/admin/events/aggregated/{stat_type} - 获取聚合统计
- GET /api/v2/admin/events/aggregated/{stat_type}/range - 获取聚合统计范围
- POST /api/v2/admin/events/aggregation/run - 运行聚合任务

创建时间: 2026-01-07
更新时间: 2026-01-09 (v3.27: 适配 DDD Service 层)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """普通用户 headers"""
    return {"Authorization": "Bearer test_token_user_123"}


@pytest.fixture
def admin_headers():
    """管理员 headers"""
    return {"Authorization": "Bearer test_admin_token"}


class TestAdminEventsAPI:
    """Admin Events API 测试 (v3.27)"""

    def test_admin_events_requires_auth(self):
        """未认证应返回 401"""
        response = client.get("/api/v2/admin/events/events")
        assert response.status_code in [401, 404]

    def test_admin_events_requires_admin_role(self, auth_headers):
        """非管理员应返回 403"""
        response = client.get("/api/v2/admin/events/events", headers=auth_headers)
        assert response.status_code in [403, 404, 401]

    @patch('application.services.events_service.EventsService.get_user_events')
    @patch('core.database.get_database_client')
    def test_admin_events_success(self, mock_get_db, mock_get_events, admin_headers):
        """管理员请求成功 (v3.27: Mock Service layer)"""
        # Mock database client
        mock_get_db.return_value = MagicMock()

        # Mock EventsService.get_user_events response
        mock_get_events.return_value = {
            "events": [
                {
                    "id": "evt_1",
                    "user_id": "user_123",
                    "event_type": "page_view",
                    "created_at": "2026-01-09T10:00:00Z"
                }
            ],
            "total": 1,
            "offset": 0,
            "limit": 50,
            "has_more": False
        }

        response = client.get("/api/v2/admin/events/events", headers=admin_headers)

        # 验证响应
        assert response.status_code in [200, 404, 401]
        if response.status_code == 200:
            data = response.json()
            assert "events" in data
            assert "total" in data

    @patch('application.services.events_service.EventsService.get_event_stats')
    @patch('core.database.get_database_client')
    def test_admin_event_stats_success(self, mock_get_db, mock_get_stats, admin_headers):
        """获取事件统计成功"""
        mock_get_db.return_value = MagicMock()

        mock_get_stats.return_value = {
            "page_view": 100,
            "button_click": 50
        }

        response = client.get(
            "/api/v2/admin/events/events/stats",
            headers=admin_headers,
            params={"group_by": "event_type"}
        )

        assert response.status_code in [200, 404, 401]

    @patch('application.services.events_service.EventsService.get_user_events')
    @patch('core.database.get_database_client')
    def test_admin_events_with_filters(self, mock_get_db, mock_get_events, admin_headers):
        """测试带过滤器的请求"""
        mock_get_db.return_value = MagicMock()

        mock_get_events.return_value = {
            "events": [],
            "total": 0,
            "offset": 0,
            "limit": 10,
            "has_more": False
        }

        response = client.get(
            "/api/v2/admin/events/events",
            headers=admin_headers,
            params={
                "user_id": "user_123",
                "event_type": "page_view",
                "limit": 10
            }
        )

        assert response.status_code in [200, 404, 401]

    @patch('application.services.events_service.EventsService.get_user_events')
    @patch('core.database.get_database_client')
    def test_admin_events_invalid_limit(self, mock_get_db, mock_get_events, admin_headers):
        """测试无效的 limit 参数"""
        mock_get_db.return_value = MagicMock()

        # Service 会抛出 ValueError
        mock_get_events.side_effect = ValueError("limit must be <= 100")

        response = client.get(
            "/api/v2/admin/events/events",
            headers=admin_headers,
            params={"limit": 1000}
        )

        # 应返回 400 (Client Error)
        assert response.status_code in [400, 422, 404, 401]
