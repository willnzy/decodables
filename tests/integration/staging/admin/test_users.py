"""
Admin Users API Tests (Black Box)

测试 /api/v2/admin/users 相关接口

业务规则:
1. 只有 admin 才能访问用户管理接口
2. 支持用户搜索、审计查看、积分调整、tier 更新
3. 支持用户项目管理
4. 所有操作都有审计日志

@module tests.integration.staging.admin.test_users
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import API_ADMIN


@pytest.mark.p1
class TestAdminUsersSearch(BaseAPITest):
    """
    GET /api/v2/admin/users 黑盒测试

    搜索用户 (by user_id, email, or user_code)
    """

    ENDPOINT = f"{API_ADMIN}/users"

    def test_search_users_requires_admin(self, anon_client):
        """
        业务规则: 搜索用户需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT, params={"query": "test"})
        self.assert_unauthorized(response)

    def test_search_users_missing_query(self, auth_client):
        """
        业务规则: 必须提供搜索关键词
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 422 (缺少 query) 或 403 (非 admin)
        assert response.status_code in [400, 403, 422]

    def test_search_users_with_query(self, auth_client):
        """
        业务规则: 认证用户搜索
        """
        response = auth_client.get(self.ENDPOINT, params={"query": "test"})
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_search_users_with_limit(self, auth_client):
        """
        业务规则: 支持 limit 参数
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"query": "test", "limit": 10}
        )
        assert response.status_code in [200, 403]

    def test_search_users_empty_query(self, auth_client):
        """
        业务规则: 空查询应返回错误
        """
        response = auth_client.get(self.ENDPOINT, params={"query": ""})
        assert response.status_code in [400, 403, 422]


@pytest.mark.p1
class TestAdminUsersByTier(BaseAPITest):
    """
    GET /api/v2/admin/users/by-tier/{tier} 黑盒测试

    按 tier 获取用户列表
    """

    def _get_endpoint(self, tier: str) -> str:
        return f"{API_ADMIN}/users/by-tier/{tier}"

    def test_by_tier_requires_admin(self, anon_client):
        """
        业务规则: 按 tier 查询需要管理员权限
        """
        response = anon_client.get(self._get_endpoint("t1"))
        self.assert_unauthorized(response)

    def test_by_tier_valid_tiers(self, auth_client):
        """
        业务规则: 支持有效的 tier 值
        """
        for tier in ["t1", "t2", "t3"]:
            response = auth_client.get(self._get_endpoint(tier))
            assert response.status_code in [200, 403]

    def test_by_tier_invalid_tier(self, auth_client):
        """
        业务规则: 无效的 tier 值
        """
        response = auth_client.get(self._get_endpoint("invalid_tier"))
        assert response.status_code in [400, 403]

    def test_by_tier_pagination(self, auth_client):
        """
        业务规则: 支持分页
        """
        response = auth_client.get(
            self._get_endpoint("t1"),
            params={"offset": 0, "limit": 10}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminUserAudit(BaseAPITest):
    """
    GET /api/v2/admin/users/{uid} 黑盒测试

    获取用户审计信息
    """

    def _get_endpoint(self, uid: str) -> str:
        return f"{API_ADMIN}/users/{uid}"

    def test_audit_requires_admin(self, anon_client):
        """
        业务规则: 获取审计信息需要管理员权限
        """
        response = anon_client.get(self._get_endpoint("user_test_12345"))
        self.assert_unauthorized(response)

    def test_audit_nonexistent_user(self, auth_client):
        """
        业务规则: 获取不存在用户的审计信息
        """
        fake_uid = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.get(self._get_endpoint(fake_uid))
        # 可能返回 200 (空数据) 或 404 或 403 (非 admin)
        assert response.status_code in [200, 403, 404]

    def test_audit_uid_too_long(self, auth_client):
        """
        业务规则: uid 太长应返回 400
        """
        long_uid = "a" * 150
        response = auth_client.get(self._get_endpoint(long_uid))
        assert response.status_code in [400, 403]


@pytest.mark.p1
class TestAdminUserCredits(BaseAPITest):
    """
    POST /api/v2/admin/users/{uid}/credits 黑盒测试

    调整用户积分
    """

    def _get_endpoint(self, uid: str) -> str:
        return f"{API_ADMIN}/users/{uid}/credits"

    def test_credits_requires_admin(self, anon_client):
        """
        业务规则: 调整积分需要管理员权限
        """
        response = anon_client.post(
            self._get_endpoint("user_test_12345"),
            json={"amount": 100, "bucket": "permanent", "reason": "Test"}
        )
        self.assert_unauthorized(response)

    def test_credits_missing_amount(self, auth_client):
        """
        业务规则: 缺少 amount 字段
        """
        response = auth_client.post(
            self._get_endpoint("user_test_12345"),
            json={"bucket": "permanent"}
        )
        assert response.status_code in [400, 403, 422]

    def test_credits_invalid_bucket(self, auth_client):
        """
        业务规则: 无效的 bucket 值

        bucket 只能是 monthly 或 permanent
        """
        response = auth_client.post(
            self._get_endpoint("user_test_12345"),
            json={"amount": 100, "bucket": "invalid_bucket"}
        )
        assert response.status_code in [400, 403, 422]

    def test_credits_valid_buckets(self, auth_client):
        """
        业务规则: 测试有效的 bucket 值
        """
        for bucket in ["monthly", "permanent"]:
            response = auth_client.post(
                self._get_endpoint("user_test_12345"),
                json={"amount": 100, "bucket": bucket, "reason": "Test"}
            )
            # 可能成功或失败 (非 admin / 用户不存在)
            assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminUserTierUpdate(BaseAPITest):
    """
    PATCH /api/v2/admin/users/{uid} 黑盒测试

    更新用户 tier
    """

    def _get_endpoint(self, uid: str) -> str:
        return f"{API_ADMIN}/users/{uid}"

    def test_tier_update_requires_admin(self, anon_client):
        """
        业务规则: 更新 tier 需要管理员权限
        """
        response = anon_client.patch(
            self._get_endpoint("user_test_12345"),
            json={"tier": "t2"}
        )
        self.assert_unauthorized(response)

    def test_tier_update_invalid_tier(self, auth_client):
        """
        业务规则: 无效的 tier 值
        """
        response = auth_client.patch(
            self._get_endpoint("user_test_12345"),
            json={"tier": "invalid_tier"}
        )
        assert response.status_code in [400, 403, 422]

    def test_tier_update_valid_tiers(self, auth_client):
        """
        业务规则: 测试有效的 tier 值
        """
        for tier in ["t1", "t2", "t3", "free", "starter", "pro"]:
            response = auth_client.patch(
                self._get_endpoint("user_test_12345"),
                json={"tier": tier}
            )
            assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminUserDiscount(BaseAPITest):
    """
    POST /api/v2/admin/users/{uid}/discount 黑盒测试

    创建用户折扣
    """

    def _get_endpoint(self, uid: str) -> str:
        return f"{API_ADMIN}/users/{uid}/discount"

    def test_discount_requires_admin(self, anon_client):
        """
        业务规则: 创建折扣需要管理员权限
        """
        response = anon_client.post(
            self._get_endpoint("user_test_12345"),
            json={"discount_percent": 20}
        )
        self.assert_unauthorized(response)

    def test_discount_invalid_percent(self, auth_client):
        """
        业务规则: 折扣百分比范围 1-100
        """
        # 0% 无效
        response = auth_client.post(
            self._get_endpoint("user_test_12345"),
            json={"discount_percent": 0}
        )
        assert response.status_code in [400, 403, 422]

        # 101% 无效
        response = auth_client.post(
            self._get_endpoint("user_test_12345"),
            json={"discount_percent": 101}
        )
        assert response.status_code in [400, 403, 422]

    def test_discount_valid(self, auth_client):
        """
        业务规则: 创建有效的折扣
        """
        response = auth_client.post(
            self._get_endpoint("user_test_12345"),
            json={
                "discount_percent": 20,
                "valid_days": 7,
                "target_plan": "t2"
            }
        )
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminUserPayments(BaseAPITest):
    """
    GET /api/v2/admin/users/{uid}/payments 黑盒测试

    获取用户支付历史
    """

    def _get_endpoint(self, uid: str) -> str:
        return f"{API_ADMIN}/users/{uid}/payments"

    def test_payments_requires_admin(self, anon_client):
        """
        业务规则: 获取支付历史需要管理员权限
        """
        response = anon_client.get(self._get_endpoint("user_test_12345"))
        self.assert_unauthorized(response)

    def test_payments_with_auth(self, auth_client):
        """
        业务规则: 获取用户支付历史
        """
        response = auth_client.get(self._get_endpoint("user_test_12345"))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminUserProjects(BaseAPITest):
    """
    GET /api/v2/admin/users/{uid}/projects 黑盒测试

    获取用户项目列表
    """

    def _get_endpoint(self, uid: str) -> str:
        return f"{API_ADMIN}/users/{uid}/projects"

    def test_projects_requires_admin(self, anon_client):
        """
        业务规则: 获取项目列表需要管理员权限
        """
        response = anon_client.get(self._get_endpoint("user_test_12345"))
        self.assert_unauthorized(response)

    def test_projects_with_auth(self, auth_client):
        """
        业务规则: 获取用户项目
        """
        response = auth_client.get(self._get_endpoint("user_test_12345"))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p2
class TestAdminUserAssetUsage(BaseAPITest):
    """
    GET /api/v2/admin/users/{uid}/asset-usage 黑盒测试

    获取用户素材使用情况
    """

    def _get_endpoint(self, uid: str) -> str:
        return f"{API_ADMIN}/users/{uid}/asset-usage"

    def test_asset_usage_requires_admin(self, anon_client):
        """
        业务规则: 获取素材使用需要管理员权限
        """
        response = anon_client.get(self._get_endpoint("user_test_12345"))
        self.assert_unauthorized(response)

    def test_asset_usage_with_auth(self, auth_client):
        """
        业务规则: 获取用户素材使用情况
        """
        response = auth_client.get(self._get_endpoint("user_test_12345"))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p2
class TestAdminUserEnvStats(BaseAPITest):
    """
    GET /api/v2/admin/users/{uid}/env-stats 黑盒测试

    获取用户环境统计
    """

    def _get_endpoint(self, uid: str) -> str:
        return f"{API_ADMIN}/users/{uid}/env-stats"

    def test_env_stats_requires_admin(self, anon_client):
        """
        业务规则: 获取环境统计需要管理员权限
        """
        response = anon_client.get(self._get_endpoint("user_test_12345"))
        self.assert_unauthorized(response)

    def test_env_stats_with_auth(self, auth_client):
        """
        业务规则: 获取用户环境统计
        """
        response = auth_client.get(self._get_endpoint("user_test_12345"))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p2
class TestAdminProjectRestore(BaseAPITest):
    """
    POST /api/v2/admin/projects/{project_id}/restore 黑盒测试

    恢复删除的项目
    """

    def _get_endpoint(self, project_id: str) -> str:
        return f"{API_ADMIN}/projects/{project_id}/restore"

    def test_restore_requires_admin(self, anon_client):
        """
        业务规则: 恢复项目需要管理员权限
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(self._get_endpoint(fake_id))
        self.assert_unauthorized(response)

    def test_restore_nonexistent_project(self, auth_client):
        """
        业务规则: 恢复不存在的项目
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(self._get_endpoint(fake_id))
        assert response.status_code in [400, 403, 404]


@pytest.mark.p2
class TestAdminProjectFeed(BaseAPITest):
    """
    GET /api/v2/admin/projects/feed 黑盒测试

    获取全站项目 Feed
    """

    ENDPOINT = f"{API_ADMIN}/projects/feed"

    def test_feed_requires_admin(self, anon_client):
        """
        业务规则: 获取 Feed 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_feed_with_auth(self, auth_client):
        """
        业务规则: 获取项目 Feed
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]
