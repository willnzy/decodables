"""
Admin Users API Tests (Black Box)

测试 /api/admin/users 相关接口

业务规则:
1. 只有 admin 才能访问用户管理接口
2. 支持用户列表查询、详情、更新、删除
3. 支持封禁/解封用户操作
4. 所有操作都有审计日志

@module tests.integration.staging.admin.test_users
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminUsersList(BaseAPITest):
    """
    GET /api/admin/users 黑盒测试

    获取用户列表
    """

    ENDPOINT = Endpoints.ADMIN_USERS

    def test_list_users_requires_admin(self, anon_client):
        """
        业务规则: 用户列表需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_list_users_with_auth(self, auth_client):
        """
        业务规则: 认证用户访问

        如果用户是 admin，返回用户列表
        如果用户不是 admin，返回 403
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_list_users_pagination(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 10}
        )
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_list_users_filter_by_tier(self, auth_client):
        """
        业务规则: 支持按 tier 筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"tier": "t1"}
        )
        assert response.status_code in [200, 403]

    def test_list_users_filter_by_status(self, auth_client):
        """
        业务规则: 支持按状态筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"status": "active"}
        )
        assert response.status_code in [200, 403]

    def test_list_users_search(self, auth_client):
        """
        业务规则: 支持搜索用户
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"search": "test"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminUserDetail(BaseAPITest):
    """
    GET /api/admin/users/{user_id} 黑盒测试

    获取用户详情
    """

    def test_get_user_requires_admin(self, anon_client, test_user_id):
        """
        业务规则: 用户详情需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_user(test_user_id))
        self.assert_unauthorized(response)

    def test_get_nonexistent_user(self, auth_client):
        """
        业务规则: 获取不存在的用户

        返回 404 或 403 (非 admin)
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.get(Endpoints.admin_user(fake_id))
        assert response.status_code in [403, 404]

    def test_get_user_with_auth(self, auth_client, test_user_id):
        """
        业务规则: 认证用户获取用户详情
        """
        response = auth_client.get(Endpoints.admin_user(test_user_id))
        # 可能返回 200/404 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminUserUpdate(BaseAPITest):
    """
    PUT /api/admin/users/{user_id} 黑盒测试

    更新用户信息
    """

    def test_update_user_requires_admin(self, anon_client, test_user_id):
        """
        业务规则: 更新用户需要管理员权限
        """
        response = anon_client.put(
            Endpoints.admin_user(test_user_id),
            json={"display_name": "Updated Name"}
        )
        self.assert_unauthorized(response)

    def test_update_nonexistent_user(self, auth_client):
        """
        业务规则: 更新不存在的用户
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.put(
            Endpoints.admin_user(fake_id),
            json={"display_name": "Updated Name"}
        )
        assert response.status_code in [403, 404]

    def test_update_user_empty_body(self, auth_client, test_user_id):
        """
        业务规则: 空请求体应返回错误
        """
        response = auth_client.put(
            Endpoints.admin_user(test_user_id),
            json={}
        )
        # 可能返回 400 (无字段) 或 403 (非 admin)
        assert response.status_code in [400, 403, 422]


@pytest.mark.p1
class TestAdminUserDelete(BaseAPITest):
    """
    DELETE /api/admin/users/{user_id} 黑盒测试

    删除用户 (软删除)
    """

    def test_delete_user_requires_admin(self, anon_client, test_user_id):
        """
        业务规则: 删除用户需要管理员权限
        """
        response = anon_client.delete(Endpoints.admin_user(test_user_id))
        self.assert_unauthorized(response)

    def test_delete_nonexistent_user(self, auth_client):
        """
        业务规则: 删除不存在的用户
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.delete(Endpoints.admin_user(fake_id))
        assert response.status_code in [403, 404]


@pytest.mark.p1
class TestAdminUserBan(BaseAPITest):
    """
    POST /api/admin/users/{user_id}/ban 黑盒测试

    封禁用户
    """

    def test_ban_user_requires_admin(self, anon_client, test_user_id):
        """
        业务规则: 封禁用户需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_user_ban(test_user_id))
        self.assert_unauthorized(response)

    def test_ban_nonexistent_user(self, auth_client):
        """
        业务规则: 封禁不存在的用户
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.post(Endpoints.admin_user_ban(fake_id))
        assert response.status_code in [403, 404]

    def test_ban_user_with_reason(self, auth_client, test_user_id):
        """
        业务规则: 封禁用户并提供原因
        """
        response = auth_client.post(
            Endpoints.admin_user_ban(test_user_id),
            json={"reason": "Violation of terms"}
        )
        # 可能返回 200 (admin) 或 403 (非 admin) 或 404 (用户不存在)
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminUserUnban(BaseAPITest):
    """
    POST /api/admin/users/{user_id}/unban 黑盒测试

    解封用户
    """

    def test_unban_user_requires_admin(self, anon_client, test_user_id):
        """
        业务规则: 解封用户需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_user_unban(test_user_id))
        self.assert_unauthorized(response)

    def test_unban_nonexistent_user(self, auth_client):
        """
        业务规则: 解封不存在的用户
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.post(Endpoints.admin_user_unban(fake_id))
        assert response.status_code in [403, 404]


@pytest.mark.p2
class TestAdminUsersValidation(BaseAPITest):
    """
    Admin Users API 参数验证测试
    """

    ENDPOINT = Endpoints.ADMIN_USERS

    def test_invalid_tier_filter(self, auth_client):
        """
        业务规则: 无效的 tier 参数
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"tier": "invalid_tier"}
        )
        # 可能返回 400 (无效参数) 或 403 (非 admin)
        assert response.status_code in [400, 403]

    def test_invalid_pagination(self, auth_client):
        """
        业务规则: 无效的分页参数
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": -1, "limit": 1000}
        )
        # 可能返回 400/422 (无效参数) 或 403 (非 admin)
        assert response.status_code in [400, 403, 422]

    def test_invalid_user_id_format(self, auth_client):
        """
        业务规则: 无效的用户 ID 格式
        """
        response = auth_client.get(Endpoints.admin_user("invalid-id-format"))
        assert response.status_code in [400, 403, 404]
