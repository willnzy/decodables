"""
System Resources API Integration Tests (Admin)

测试 System Resources 管理相关接口 (需要管理员权限):
- GET /api/v2/user/system-resources - List resources
- GET /api/v2/user/system-resources/stats - Get stats
- GET /api/v2/user/system-resources/{resource_id} - Get resource
- POST /api/v2/user/system-resources - Create resource
- PATCH /api/v2/user/system-resources/{resource_id} - Update resource
- POST /api/v2/user/system-resources/{resource_id}/replace - Replace file
- DELETE /api/v2/user/system-resources/{resource_id} - Delete resource
- POST /api/v2/user/system-resources/batch - Batch operations
- GET /api/v2/user/system-resources/{resource_id}/audit-log - Audit log

TDD Approach:
- Sad Path First: 401 → 403 → 400 → 422 → 200
- Admin-only endpoints

@module tests.integration.staging.system_resources.test_system_resources
"""

import uuid
import pytest

from tests.integration.staging.constants import Endpoints


# ==========================================
# Base Test Class
# ==========================================

class BaseAPITest:
    """Base class with common assertion methods."""

    def assert_success(self, response, expected_status: int = 200) -> dict:
        """Assert successful response and return JSON data."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )
        return response.json()

    def assert_unauthorized(self, response):
        """Assert 401 Unauthorized."""
        assert response.status_code == 401, (
            f"Expected 401, got {response.status_code}"
        )

    def assert_forbidden(self, response):
        """Assert 403 Forbidden."""
        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}"
        )

    def assert_not_found(self, response):
        """Assert 404 Not Found."""
        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}"
        )


# ==========================================
# Test: List System Resources
# ==========================================

@pytest.mark.admin
@pytest.mark.p1
class TestSystemResourceList(BaseAPITest):
    """
    GET /api/v2/user/system-resources 黑盒测试

    获取系统资源列表 (管理员视图)

    业务规则:
    1. 需要管理员权限
    2. 支持 type, category, is_active, search 过滤
    3. 支持分页 (page, limit)
    """

    ENDPOINT = Endpoints.SYSTEM_RESOURCES

    def test_list_requires_admin(self, auth_client):
        """
        业务规则: 需要管理员权限

        Sad Path First: 403 Forbidden (普通用户)
        """
        response = auth_client.get(self.ENDPOINT)
        self.assert_forbidden(response)

    def test_list_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_list_resources_as_admin(self, admin_client):
        """
        业务规则: 管理员可以获取资源列表
        """
        response = admin_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"
        assert "total" in data, "响应应包含 total"

    def test_list_with_type_filter(self, admin_client):
        """
        业务规则: 支持按 type 过滤
        """
        response = admin_client.get(
            self.ENDPOINT,
            params={"type": "sticker"}
        )
        data = self.assert_success(response)
        assert "items" in data

    def test_list_with_category_filter(self, admin_client):
        """
        业务规则: 支持按 category 过滤
        """
        response = admin_client.get(
            self.ENDPOINT,
            params={"category": "animals"}
        )
        data = self.assert_success(response)
        assert "items" in data

    def test_list_with_pagination(self, admin_client):
        """
        业务规则: 支持分页
        """
        response = admin_client.get(
            self.ENDPOINT,
            params={"page": 1, "limit": 10}
        )
        data = self.assert_success(response)

        assert "page" in data or "items" in data
        if "items" in data:
            assert len(data["items"]) <= 10

    def test_list_invalid_page_rejected(self, admin_client):
        """
        业务规则: page 必须 >= 1

        Sad Path: 验证错误
        """
        response = admin_client.get(
            self.ENDPOINT,
            params={"page": 0}
        )

        assert response.status_code in [400, 422], (
            f"无效 page 应被拒绝，但返回了 {response.status_code}"
        )

    def test_list_invalid_limit_rejected(self, admin_client):
        """
        业务规则: limit 必须在有效范围内 (1-200)

        Sad Path: 验证错误
        """
        response = admin_client.get(
            self.ENDPOINT,
            params={"limit": 0}
        )

        assert response.status_code in [400, 422], (
            f"无效 limit 应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: System Resource Stats
# ==========================================

@pytest.mark.admin
@pytest.mark.p2
class TestSystemResourceStats(BaseAPITest):
    """
    GET /api/v2/user/system-resources/stats 黑盒测试

    获取系统资源统计
    """

    ENDPOINT = Endpoints.SYSTEM_RESOURCES_STATS

    def test_stats_requires_admin(self, auth_client):
        """
        业务规则: 需要管理员权限

        Sad Path First: 403 Forbidden
        """
        response = auth_client.get(self.ENDPOINT)
        self.assert_forbidden(response)

    def test_stats_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_get_stats_as_admin(self, admin_client):
        """
        业务规则: 管理员可以获取统计
        """
        response = admin_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 统计数据是一个字典
        assert isinstance(data, dict), "统计数据应该是字典"


# ==========================================
# Test: Get System Resource by ID
# ==========================================

@pytest.mark.admin
@pytest.mark.p1
class TestSystemResourceGet(BaseAPITest):
    """
    GET /api/v2/user/system-resources/{resource_id} 黑盒测试

    通过 ID 获取系统资源
    """

    def test_get_requires_admin(self, auth_client):
        """
        业务规则: 需要管理员权限

        Sad Path First: 403 Forbidden
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.system_resource(fake_id))
        self.assert_forbidden(response)

    def test_get_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.system_resource(fake_id))
        self.assert_unauthorized(response)

    def test_get_nonexistent_resource_returns_404(self, admin_client):
        """
        业务规则: 资源不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = admin_client.get(Endpoints.system_resource(fake_id))
        self.assert_not_found(response)

    def test_get_invalid_id_format_rejected(self, admin_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = admin_client.get(Endpoints.system_resource("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Update System Resource
# ==========================================

@pytest.mark.admin
@pytest.mark.p1
class TestSystemResourceUpdate(BaseAPITest):
    """
    PATCH /api/v2/user/system-resources/{resource_id} 黑盒测试

    更新系统资源元数据
    """

    def test_update_requires_admin(self, auth_client):
        """
        业务规则: 需要管理员权限

        Sad Path First: 403 Forbidden
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.patch(
            Endpoints.system_resource(fake_id),
            json={"name": "Updated"}
        )
        self.assert_forbidden(response)

    def test_update_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.patch(
            Endpoints.system_resource(fake_id),
            json={"name": "Updated"}
        )
        self.assert_unauthorized(response)

    def test_update_nonexistent_resource_returns_404(self, admin_client):
        """
        业务规则: 资源不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = admin_client.patch(
            Endpoints.system_resource(fake_id),
            json={"name": "Updated"}
        )
        self.assert_not_found(response)

    def test_update_invalid_id_format_rejected(self, admin_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = admin_client.patch(
            Endpoints.system_resource("invalid-uuid"),
            json={"name": "Updated"}
        )
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Delete System Resource
# ==========================================

@pytest.mark.admin
@pytest.mark.p1
class TestSystemResourceDelete(BaseAPITest):
    """
    DELETE /api/v2/user/system-resources/{resource_id} 黑盒测试

    删除系统资源 (软删除)
    """

    def test_delete_requires_admin(self, auth_client):
        """
        业务规则: 需要管理员权限

        Sad Path First: 403 Forbidden
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.system_resource(fake_id))
        self.assert_forbidden(response)

    def test_delete_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.delete(Endpoints.system_resource(fake_id))
        self.assert_unauthorized(response)

    def test_delete_nonexistent_resource_returns_404(self, admin_client):
        """
        业务规则: 资源不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = admin_client.delete(Endpoints.system_resource(fake_id))
        self.assert_not_found(response)

    def test_delete_invalid_id_format_rejected(self, admin_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = admin_client.delete(Endpoints.system_resource("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Batch Operations
# ==========================================

@pytest.mark.admin
@pytest.mark.p2
class TestSystemResourceBatch(BaseAPITest):
    """
    POST /api/v2/user/system-resources/batch 黑盒测试

    批量操作系统资源
    """

    ENDPOINT = Endpoints.SYSTEM_RESOURCES_BATCH

    def test_batch_requires_admin(self, auth_client):
        """
        业务规则: 需要管理员权限

        Sad Path First: 403 Forbidden
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "action": "activate",
                "resource_ids": [str(uuid.uuid4())]
            }
        )
        self.assert_forbidden(response)

    def test_batch_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "action": "activate",
                "resource_ids": [str(uuid.uuid4())]
            }
        )
        self.assert_unauthorized(response)

    def test_batch_invalid_uuid_rejected(self, admin_client):
        """
        业务规则: resource_ids 必须是有效的 UUID

        Sad Path: 验证错误
        """
        response = admin_client.post(
            self.ENDPOINT,
            json={
                "action": "activate",
                "resource_ids": ["invalid-uuid"]
            }
        )

        assert response.status_code in [400, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_batch_exceeds_limit_rejected(self, admin_client):
        """
        业务规则: 批量操作不能超过 100 个

        Sad Path: 验证错误
        """
        response = admin_client.post(
            self.ENDPOINT,
            json={
                "action": "activate",
                "resource_ids": [str(uuid.uuid4()) for _ in range(101)]
            }
        )

        assert response.status_code in [400, 422], (
            f"超过批量限制应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Resource Audit Log
# ==========================================

@pytest.mark.admin
@pytest.mark.p2
class TestSystemResourceAudit(BaseAPITest):
    """
    GET /api/v2/user/system-resources/{resource_id}/audit-log 黑盒测试

    获取资源审计日志
    """

    def test_audit_requires_admin(self, auth_client):
        """
        业务规则: 需要管理员权限

        Sad Path First: 403 Forbidden
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.system_resource_audit(fake_id))
        self.assert_forbidden(response)

    def test_audit_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.system_resource_audit(fake_id))
        self.assert_unauthorized(response)

    def test_audit_invalid_id_format_rejected(self, admin_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = admin_client.get(Endpoints.system_resource_audit("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )
