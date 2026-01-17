"""
Admin Users API Tests (Black Box)

测试 /api/v2/admin/users 相关接口

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. Admin API 需要管理员权限
2. 普通用户无法访问 Admin API
3. 可以搜索用户、查看用户详情、调整积分、修改 Tier
4. 支持用户项目管理和恢复

⚠️ 注意: 这些测试使用普通用户 Token，预期返回 403
如需完整测试 Admin 功能，需要配置 Admin Token

@module tests.integration.staging.admin.test_admin_users
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints, Tiers


# Admin API Base URL
API_ADMIN = "/api/v2/admin"


@pytest.mark.p0
class TestAdminUsersAccess(BaseAPITest):
    """
    Admin Users API 访问控制测试

    验证非管理员用户无法访问 Admin API
    """

    # ==========================================
    # 权限测试: 普通用户应被拒绝
    # ==========================================

    def test_list_users_requires_admin(self, auth_client):
        """
        业务规则: 用户列表需要管理员权限

        普通用户访问应返回 403 Forbidden
        """
        response = auth_client.get(f"{API_ADMIN}/users")

        # 普通用户应被拒绝
        assert response.status_code == 403, (
            f"普通用户访问 Admin API 应返回 403，但返回了 {response.status_code}"
        )

    def test_get_user_requires_admin(self, auth_client):
        """
        业务规则: 获取用户详情需要管理员权限
        """
        fake_uid = "user_test123"
        response = auth_client.get(f"{API_ADMIN}/users/{fake_uid}")

        assert response.status_code == 403, (
            f"普通用户访问应返回 403，但返回了 {response.status_code}"
        )

    def test_adjust_credits_requires_admin(self, auth_client):
        """
        业务规则: 调整积分需要管理员权限

        这是敏感操作，必须严格控制权限
        """
        fake_uid = "user_test123"
        response = auth_client.post(
            f"{API_ADMIN}/users/{fake_uid}/credits",
            json={
                "amount": 100,
                "bucket": "permanent",
                "reason": "Test adjustment"
            }
        )

        assert response.status_code == 403, (
            f"调整积分需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )

    def test_update_tier_requires_admin(self, auth_client):
        """
        业务规则: 修改用户 Tier 需要管理员权限

        Tier 变更影响用户权限和计费
        """
        fake_uid = "user_test123"
        response = auth_client.patch(
            f"{API_ADMIN}/users/{fake_uid}",
            json={"tier": "t2"}
        )

        assert response.status_code == 403, (
            f"修改 Tier 需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )

    def test_anonymous_rejected(self, anon_client):
        """
        业务规则: 未登录用户应返回 401
        """
        response = anon_client.get(f"{API_ADMIN}/users")

        # 未登录应返回 401
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestAdminUsersByTier(BaseAPITest):
    """
    GET /api/v2/admin/users/by-tier/{tier} 访问测试
    """

    def test_get_users_by_tier_requires_admin(self, auth_client):
        """
        业务规则: 按 Tier 查询用户需要管理员权限
        """
        for tier in [Tiers.FREE, Tiers.STARTER, Tiers.PRO]:
            response = auth_client.get(f"{API_ADMIN}/users/by-tier/{tier}")

            assert response.status_code == 403, (
                f"by-tier/{tier} 需要管理员权限，但返回了 {response.status_code}"
            )


@pytest.mark.p1
class TestAdminUserProjects(BaseAPITest):
    """
    Admin User Projects API 测试
    """

    def test_get_user_projects_requires_admin(self, auth_client):
        """
        业务规则: 查看用户项目需要管理员权限
        """
        fake_uid = "user_test123"
        response = auth_client.get(f"{API_ADMIN}/users/{fake_uid}/projects")

        assert response.status_code == 403, (
            f"查看用户项目需要管理员权限，但返回了 {response.status_code}"
        )

    def test_restore_project_requires_admin(self, auth_client):
        """
        业务规则: 恢复项目需要管理员权限
        """
        fake_project_id = str(uuid.uuid4())
        response = auth_client.post(f"{API_ADMIN}/projects/{fake_project_id}/restore")

        assert response.status_code == 403, (
            f"恢复项目需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p1
class TestAdminUserPayments(BaseAPITest):
    """
    Admin User Payments API 测试
    """

    def test_get_payment_history_requires_admin(self, auth_client):
        """
        业务规则: 查看支付历史需要管理员权限

        支付数据是敏感信息
        """
        fake_uid = "user_test123"
        response = auth_client.get(f"{API_ADMIN}/users/{fake_uid}/payments")

        assert response.status_code == 403, (
            f"查看支付历史需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminDiscount(BaseAPITest):
    """
    Admin Discount API 测试
    """

    def test_create_discount_requires_admin(self, auth_client):
        """
        业务规则: 创建折扣需要管理员权限
        """
        fake_uid = "user_test123"
        response = auth_client.post(
            f"{API_ADMIN}/users/{fake_uid}/discount",
            json={
                "discount_percent": 50,
                "valid_days": 7
            }
        )

        assert response.status_code == 403, (
            f"创建折扣需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminAssetUsage(BaseAPITest):
    """
    Admin Asset Usage API 测试
    """

    def test_get_asset_usage_requires_admin(self, auth_client):
        """
        业务规则: 查看资产使用情况需要管理员权限
        """
        fake_uid = "user_test123"
        response = auth_client.get(f"{API_ADMIN}/users/{fake_uid}/asset-usage")

        assert response.status_code == 403, (
            f"查看资产使用需要管理员权限，但返回了 {response.status_code}"
        )
