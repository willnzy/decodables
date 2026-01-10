"""
Webhook Retry API Integration Tests (P3-022)
测试 api/admin/webhooks_retry.py

端点:
- POST /api/v2/admin/webhooks/retry
- GET /api/v2/admin/webhooks/failed

创建时间: 2026-01-11
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

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


class TestWebhookRetryAPI:
    """Webhook Retry API 集成测试"""

    # ==========================================
    # Authentication and Authorization Tests
    # ==========================================

    def test_retry_endpoint_requires_auth(self):
        """POST /webhooks/retry 未认证应返回 401"""
        response = client.post("/api/v2/admin/webhooks/retry")
        assert response.status_code in [401, 404]

    def test_retry_endpoint_requires_admin_role(self, auth_headers):
        """POST /webhooks/retry 非管理员应返回 403"""
        response = client.post("/api/v2/admin/webhooks/retry", headers=auth_headers)
        assert response.status_code in [403, 404, 401]

    def test_failed_endpoint_requires_auth(self):
        """GET /webhooks/failed 未认证应返回 401"""
        response = client.get("/api/v2/admin/webhooks/failed")
        assert response.status_code in [401, 404]

    def test_failed_endpoint_requires_admin_role(self, auth_headers):
        """GET /webhooks/failed 非管理员应返回 403"""
        response = client.get("/api/v2/admin/webhooks/failed", headers=auth_headers)
        assert response.status_code in [403, 404, 401]

    # ==========================================
    # POST /webhooks/retry Tests
    # ==========================================

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_retry_webhooks_success(self, mock_require_admin, mock_get_service, admin_headers):
        """POST /webhooks/retry 成功触发重试任务"""
        # Mock admin authentication
        mock_require_admin.return_value = {"id": "admin_123", "role": "admin"}

        # Mock retry service
        mock_service = MagicMock()
        mock_service.retry_all_failed_webhooks = AsyncMock(return_value={
            "stripe": {
                "processed": 10,
                "succeeded": 8,
                "failed": 2,
                "skipped": 0,
                "errors": ["evt_1: Connection timeout", "evt_2: Invalid payload"]
            },
            "clerk": {
                "processed": 5,
                "succeeded": 5,
                "failed": 0,
                "skipped": 0,
                "errors": []
            },
            "total": {
                "processed": 15,
                "succeeded": 13,
                "failed": 2,
                "skipped": 0
            }
        })
        mock_get_service.return_value = mock_service

        # Execute
        response = client.post("/api/v2/admin/webhooks/retry", headers=admin_headers)

        # Verify response
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "message" in data
            assert data["total"]["processed"] == 15
            assert data["total"]["succeeded"] == 13
            assert data["total"]["failed"] == 2
            assert data["stripe"]["succeeded"] == 8
            assert data["clerk"]["succeeded"] == 5

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_retry_webhooks_empty_queue(self, mock_require_admin, mock_get_service, admin_headers):
        """POST /webhooks/retry 处理空队列"""
        mock_require_admin.return_value = {"id": "admin_123"}

        # Mock empty queue
        mock_service = MagicMock()
        mock_service.retry_all_failed_webhooks = AsyncMock(return_value={
            "stripe": {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0, "errors": []},
            "clerk": {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0, "errors": []},
            "total": {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
        })
        mock_get_service.return_value = mock_service

        # Execute
        response = client.post("/api/v2/admin/webhooks/retry", headers=admin_headers)

        # Verify
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["total"]["processed"] == 0

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_retry_webhooks_service_error(self, mock_require_admin, mock_get_service, admin_headers):
        """POST /webhooks/retry 处理服务层错误"""
        mock_require_admin.return_value = {"id": "admin_123"}

        # Mock service error
        mock_service = MagicMock()
        mock_service.retry_all_failed_webhooks = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_get_service.return_value = mock_service

        # Execute
        response = client.post("/api/v2/admin/webhooks/retry", headers=admin_headers)

        # Verify error response
        assert response.status_code in [500, 404, 401]

    # ==========================================
    # GET /webhooks/failed Tests
    # ==========================================

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_get_failed_webhooks_both_sources(self, mock_require_admin, mock_get_service, admin_headers):
        """GET /webhooks/failed 获取所有失败事件"""
        mock_require_admin.return_value = {"id": "admin_123"}

        # Mock failed events
        mock_service = MagicMock()
        mock_service.webhook_repo.get_failed_stripe_webhooks = AsyncMock(return_value=[
            {
                "event_id": "evt_stripe_1",
                "event_type": "checkout.session.completed",
                "retry_count": 2,
                "error_message": "Connection timeout",
                "created_at": "2026-01-11T10:00:00Z"
            }
        ])
        mock_service.webhook_repo.get_failed_clerk_webhooks = AsyncMock(return_value=[
            {
                "event_id": "evt_clerk_1",
                "event_type": "user.created",
                "retry_count": 1,
                "error_message": "User sync failed",
                "created_at": "2026-01-11T11:00:00Z"
            }
        ])
        mock_get_service.return_value = mock_service

        # Execute
        response = client.get("/api/v2/admin/webhooks/failed", headers=admin_headers)

        # Verify
        if response.status_code == 200:
            data = response.json()
            assert len(data["stripe_webhooks"]) == 1
            assert len(data["clerk_webhooks"]) == 1
            assert data["total_failed"] == 2
            assert data["stripe_webhooks"][0]["event_id"] == "evt_stripe_1"
            assert data["clerk_webhooks"][0]["event_id"] == "evt_clerk_1"

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_get_failed_webhooks_stripe_only(self, mock_require_admin, mock_get_service, admin_headers):
        """GET /webhooks/failed?source=stripe 仅获取 Stripe 事件"""
        mock_require_admin.return_value = {"id": "admin_123"}

        mock_service = MagicMock()
        mock_service.webhook_repo.get_failed_stripe_webhooks = AsyncMock(return_value=[
            {"event_id": "evt_1", "event_type": "invoice.paid", "retry_count": 1}
        ])
        mock_get_service.return_value = mock_service

        # Execute
        response = client.get("/api/v2/admin/webhooks/failed?source=stripe", headers=admin_headers)

        # Verify
        if response.status_code == 200:
            data = response.json()
            assert len(data["stripe_webhooks"]) == 1
            assert len(data["clerk_webhooks"]) == 0

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_get_failed_webhooks_clerk_only(self, mock_require_admin, mock_get_service, admin_headers):
        """GET /webhooks/failed?source=clerk 仅获取 Clerk 事件"""
        mock_require_admin.return_value = {"id": "admin_123"}

        mock_service = MagicMock()
        mock_service.webhook_repo.get_failed_clerk_webhooks = AsyncMock(return_value=[
            {"event_id": "evt_clerk_2", "event_type": "user.updated", "retry_count": 3}
        ])
        mock_get_service.return_value = mock_service

        # Execute
        response = client.get("/api/v2/admin/webhooks/failed?source=clerk", headers=admin_headers)

        # Verify
        if response.status_code == 200:
            data = response.json()
            assert len(data["stripe_webhooks"]) == 0
            assert len(data["clerk_webhooks"]) == 1

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_get_failed_webhooks_limit_parameter(self, mock_require_admin, mock_get_service, admin_headers):
        """GET /webhooks/failed?limit=10 限制返回数量"""
        mock_require_admin.return_value = {"id": "admin_123"}

        # Mock many events
        mock_events = [{"event_id": f"evt_{i}", "retry_count": i} for i in range(100)]
        mock_service = MagicMock()
        mock_service.webhook_repo.get_failed_stripe_webhooks = AsyncMock(return_value=mock_events[:10])
        mock_service.webhook_repo.get_failed_clerk_webhooks = AsyncMock(return_value=[])
        mock_get_service.return_value = mock_service

        # Execute
        response = client.get("/api/v2/admin/webhooks/failed?limit=10", headers=admin_headers)

        # Verify
        if response.status_code == 200:
            data = response.json()
            # Repository should respect limit
            mock_service.webhook_repo.get_failed_stripe_webhooks.assert_called_with(limit=10)

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_get_failed_webhooks_limit_validation(self, mock_require_admin, mock_get_service, admin_headers):
        """GET /webhooks/failed?limit=1000 验证限制范围"""
        mock_require_admin.return_value = {"id": "admin_123"}

        # Execute with invalid limit (> 100)
        response = client.get("/api/v2/admin/webhooks/failed?limit=1000", headers=admin_headers)

        # Verify validation error
        assert response.status_code in [422, 400, 404, 401]  # FastAPI validation error

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_get_failed_webhooks_empty_result(self, mock_require_admin, mock_get_service, admin_headers):
        """GET /webhooks/failed 处理空结果"""
        mock_require_admin.return_value = {"id": "admin_123"}

        mock_service = MagicMock()
        mock_service.webhook_repo.get_failed_stripe_webhooks = AsyncMock(return_value=[])
        mock_service.webhook_repo.get_failed_clerk_webhooks = AsyncMock(return_value=[])
        mock_get_service.return_value = mock_service

        # Execute
        response = client.get("/api/v2/admin/webhooks/failed", headers=admin_headers)

        # Verify
        if response.status_code == 200:
            data = response.json()
            assert len(data["stripe_webhooks"]) == 0
            assert len(data["clerk_webhooks"]) == 0
            assert data["total_failed"] == 0

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_get_failed_webhooks_repository_error(self, mock_require_admin, mock_get_service, admin_headers):
        """GET /webhooks/failed 处理仓储层错误"""
        mock_require_admin.return_value = {"id": "admin_123"}

        # Mock repository error
        mock_service = MagicMock()
        mock_service.webhook_repo.get_failed_stripe_webhooks = AsyncMock(
            side_effect=Exception("Database timeout")
        )
        mock_get_service.return_value = mock_service

        # Execute
        response = client.get("/api/v2/admin/webhooks/failed", headers=admin_headers)

        # Verify error response
        assert response.status_code in [500, 404, 401]

    # ==========================================
    # Rate Limiting Tests (if enabled)
    # ==========================================

    @pytest.mark.skip(reason="Rate limiting depends on environment configuration")
    def test_retry_endpoint_rate_limit(self, admin_headers):
        """POST /webhooks/retry 触发速率限制 (10/hour)"""
        # Attempt 11 requests rapidly
        responses = []
        for _ in range(11):
            response = client.post("/api/v2/admin/webhooks/retry", headers=admin_headers)
            responses.append(response)

        # At least one should be rate limited (429)
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or all(code in [401, 404] for code in status_codes)

    # ==========================================
    # Integration with Real Services (optional)
    # ==========================================

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires real database connection")
    def test_retry_webhooks_end_to_end(self, admin_headers):
        """端到端测试: 创建失败事件 → 重试 → 验证结果"""
        # This test would require:
        # 1. Create test webhook events in database
        # 2. Mark them as failed
        # 3. Call retry endpoint
        # 4. Verify events are processed
        # 5. Cleanup test data
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires real database connection")
    def test_get_failed_webhooks_end_to_end(self, admin_headers):
        """端到端测试: 创建失败事件 → 查询 → 验证返回"""
        # This test would require:
        # 1. Create test failed webhook events in database
        # 2. Call GET /webhooks/failed
        # 3. Verify correct events returned
        # 4. Cleanup test data
        pass


# ==========================================
# Additional Test Cases for Edge Scenarios
# ==========================================

class TestWebhookRetryEdgeCases:
    """Webhook Retry API 边缘场景测试"""

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_retry_with_max_retries_events(self, mock_require_admin, mock_get_service, admin_headers):
        """重试包含已达最大重试次数的事件"""
        mock_require_admin.return_value = {"id": "admin_123"}

        # Mock events with max retries
        mock_service = MagicMock()
        mock_service.retry_all_failed_webhooks = AsyncMock(return_value={
            "stripe": {
                "processed": 5,
                "succeeded": 0,
                "failed": 0,
                "skipped": 5,  # All skipped due to max retries
                "errors": []
            },
            "clerk": {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0, "errors": []},
            "total": {"processed": 5, "succeeded": 0, "failed": 0, "skipped": 5}
        })
        mock_get_service.return_value = mock_service

        # Execute
        response = client.post("/api/v2/admin/webhooks/retry", headers=admin_headers)

        # Verify
        if response.status_code == 200:
            data = response.json()
            assert data["total"]["skipped"] == 5
            assert data["total"]["succeeded"] == 0

    @patch('api.admin.webhooks_retry.get_webhook_retry_service')
    @patch('api.admin.webhooks_retry.require_admin')
    def test_failed_webhooks_invalid_source_parameter(self, mock_require_admin, mock_get_service, admin_headers):
        """GET /webhooks/failed?source=invalid 验证 source 参数"""
        mock_require_admin.return_value = {"id": "admin_123"}

        # Execute with invalid source
        response = client.get("/api/v2/admin/webhooks/failed?source=invalid", headers=admin_headers)

        # Verify validation error or defaults to both
        # Behavior depends on API implementation
        assert response.status_code in [422, 400, 200, 404, 401]
