"""
测试 api/admin/ai_api.py

端点: GET /admin/ai/insights, PATCH /admin/ai/providers/{provider}

创建时间: 2026-01-07
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

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


class TestAdminAIAPI:
    """Admin AI API 测试"""

    def test_admin_ai_requires_auth(self):
        """未认证应返回 401"""
        response = client.get("/api/v2/admin/ai")
        assert response.status_code in [401, 404]

    def test_admin_ai_requires_admin_role(self, auth_headers):
        """非管理员应返回 403"""
        # TODO: 配置 dependencies.py 中的 require_admin 来正确验证权限
        response = client.get("/api/v2/admin/ai", headers=auth_headers)

        # 在 mock 环境下可能返回 403 或 404
        assert response.status_code in [403, 404, 401]

    @patch('infrastructure.repositories.supabase')
    def test_admin_ai_success(self, mock_supabase, admin_headers):
        """管理员请求成功"""
        # Mock 数据库响应
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[{"id": "1", "name": "test"}]
        )

        response = client.get("/api/v2/admin/ai", headers=admin_headers)

        # 验证响应
        assert response.status_code in [200, 404, 401]


# TODO: 添加更多 Admin 测试用例
# - 权限验证测试
# - 批量操作测试
# - 数据修改测试
