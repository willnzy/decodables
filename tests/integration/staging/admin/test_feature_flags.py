"""
Admin Feature Flags API Tests (Black Box)

测试 /api/admin/feature-flags 相关接口

业务规则:
1. Feature Flags 支持渐进式发布
2. 支持按 tier 筛选 (t1, t2, t3, t4)
3. 支持开关控制
4. 有审计日志记录变更

@module tests.integration.staging.admin.test_feature_flags
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminFeatureFlagsList(BaseAPITest):
    """
    GET /api/admin/feature-flags 黑盒测试

    获取 Feature Flags 列表
    """

    ENDPOINT = Endpoints.ADMIN_FEATURE_FLAGS

    def test_list_flags_requires_admin(self, anon_client):
        """
        业务规则: 获取列表需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_list_flags_with_auth(self, auth_client):
        """
        业务规则: 认证用户获取列表
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_list_flags_pagination(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 10}
        )
        assert response.status_code in [200, 403]

    def test_list_flags_filter_by_enabled(self, auth_client):
        """
        业务规则: 按启用状态筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"enabled": True}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminFeatureFlagCreate(BaseAPITest):
    """
    POST /api/admin/feature-flags 黑盒测试

    创建 Feature Flag
    """

    ENDPOINT = Endpoints.ADMIN_FEATURE_FLAGS

    def test_create_flag_requires_admin(self, anon_client):
        """
        业务规则: 创建需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "key": "test_flag_key",
                "name": "Test Flag",
                "description": "Test description"
            }
        )
        self.assert_unauthorized(response)

    def test_create_flag_missing_key(self, auth_client):
        """
        业务规则: 缺少 key
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test Flag",
                "description": "Test description"
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_flag_invalid_key_format(self, auth_client):
        """
        业务规则: 无效的 key 格式 (含特殊字符)
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": "invalid key!@#",
                "name": "Test Flag"
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_flag_with_tiers(self, auth_client):
        """
        业务规则: 创建带 tier 限制的 flag
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": f"test_tier_flag_{uuid.uuid4().hex[:8]}",
                "name": "Tier Limited Flag",
                "allowed_tiers": ["t2", "t3"]
            }
        )
        assert response.status_code in [200, 201, 403]

    def test_create_flag_invalid_tier(self, auth_client):
        """
        业务规则: 无效的 tier 值
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": "test_flag",
                "name": "Test Flag",
                "allowed_tiers": ["invalid_tier"]
            }
        )
        assert response.status_code in [400, 403, 422]


@pytest.mark.p1
class TestAdminFeatureFlagGet(BaseAPITest):
    """
    GET /api/admin/feature-flags/{key} 黑盒测试

    获取单个 Feature Flag
    """

    def test_get_flag_requires_admin(self, anon_client, test_flag_key):
        """
        业务规则: 获取详情需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_feature_flag(test_flag_key))
        self.assert_unauthorized(response)

    def test_get_nonexistent_flag(self, auth_client):
        """
        业务规则: 获取不存在的 flag
        """
        fake_key = f"nonexistent_flag_{uuid.uuid4().hex[:10]}"
        response = auth_client.get(Endpoints.admin_feature_flag(fake_key))
        assert response.status_code in [403, 404]

    def test_get_flag_with_auth(self, auth_client, test_flag_key):
        """
        业务规则: 获取 flag 详情
        """
        response = auth_client.get(Endpoints.admin_feature_flag(test_flag_key))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminFeatureFlagUpdate(BaseAPITest):
    """
    PATCH /api/admin/feature-flags/{key} 黑盒测试

    更新 Feature Flag
    """

    def test_update_flag_requires_admin(self, anon_client, test_flag_key):
        """
        业务规则: 更新需要管理员权限
        """
        response = anon_client.patch(
            Endpoints.admin_feature_flag(test_flag_key),
            json={"name": "Updated Flag Name"}
        )
        self.assert_unauthorized(response)

    def test_update_nonexistent_flag(self, auth_client):
        """
        业务规则: 更新不存在的 flag
        """
        fake_key = f"nonexistent_flag_{uuid.uuid4().hex[:10]}"
        response = auth_client.patch(
            Endpoints.admin_feature_flag(fake_key),
            json={"name": "Updated"}
        )
        assert response.status_code in [403, 404]

    def test_update_flag_invalid_tier(self, auth_client, test_flag_key):
        """
        业务规则: 更新为无效的 tier
        """
        response = auth_client.patch(
            Endpoints.admin_feature_flag(test_flag_key),
            json={"allowed_tiers": ["invalid_tier"]}
        )
        assert response.status_code in [400, 403, 404, 422]


@pytest.mark.p1
class TestAdminFeatureFlagToggle(BaseAPITest):
    """
    POST /api/admin/feature-flags/{key}/toggle 黑盒测试

    切换 Feature Flag 状态
    """

    def test_toggle_requires_admin(self, anon_client, test_flag_key):
        """
        业务规则: 切换需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_feature_flag_toggle(test_flag_key))
        self.assert_unauthorized(response)

    def test_toggle_nonexistent_flag(self, auth_client):
        """
        业务规则: 切换不存在的 flag
        """
        fake_key = f"nonexistent_flag_{uuid.uuid4().hex[:10]}"
        response = auth_client.post(Endpoints.admin_feature_flag_toggle(fake_key))
        assert response.status_code in [403, 404]

    def test_toggle_flag(self, auth_client, test_flag_key):
        """
        业务规则: 切换 flag 状态
        """
        response = auth_client.post(Endpoints.admin_feature_flag_toggle(test_flag_key))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminFeatureFlagDelete(BaseAPITest):
    """
    DELETE /api/admin/feature-flags/{key} 黑盒测试

    归档 Feature Flag
    """

    def test_delete_requires_admin(self, anon_client, test_flag_key):
        """
        业务规则: 归档需要管理员权限
        """
        response = anon_client.delete(Endpoints.admin_feature_flag(test_flag_key))
        self.assert_unauthorized(response)

    def test_delete_nonexistent_flag(self, auth_client):
        """
        业务规则: 归档不存在的 flag
        """
        fake_key = f"nonexistent_flag_{uuid.uuid4().hex[:10]}"
        response = auth_client.delete(Endpoints.admin_feature_flag(fake_key))
        assert response.status_code in [403, 404]


@pytest.mark.p1
class TestAdminFeatureFlagTestEvaluation(BaseAPITest):
    """
    POST /api/admin/feature-flags/test-evaluation 黑盒测试

    测试 Flag 评估
    """

    ENDPOINT = Endpoints.ADMIN_FEATURE_FLAGS_TEST

    def test_evaluation_requires_admin(self, anon_client):
        """
        业务规则: 测试评估需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "flag_key": "test_flag",
                "user_id": "user_test_123",
                "tier": "t1"
            }
        )
        self.assert_unauthorized(response)

    def test_evaluation_missing_flag_key(self, auth_client):
        """
        业务规则: 缺少 flag_key
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_123",
                "tier": "t1"
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_evaluation_with_context(self, auth_client):
        """
        业务规则: 带上下文的评估
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "flag_key": "test_flag",
                "user_id": "user_test_123",
                "tier": "t2",
                "context": {"country": "US"}
            }
        )
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminFeatureFlagAudit(BaseAPITest):
    """
    GET /api/admin/feature-flags/{key}/audit 黑盒测试

    获取 Flag 审计日志
    """

    def test_audit_requires_admin(self, anon_client, test_flag_key):
        """
        业务规则: 查看审计日志需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_feature_flag_audit(test_flag_key))
        self.assert_unauthorized(response)

    def test_audit_nonexistent_flag(self, auth_client):
        """
        业务规则: 不存在 flag 的审计日志
        """
        fake_key = f"nonexistent_flag_{uuid.uuid4().hex[:10]}"
        response = auth_client.get(Endpoints.admin_feature_flag_audit(fake_key))
        assert response.status_code in [403, 404]

    def test_audit_with_auth(self, auth_client, test_flag_key):
        """
        业务规则: 获取审计日志
        """
        response = auth_client.get(Endpoints.admin_feature_flag_audit(test_flag_key))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p2
class TestAdminFeatureFlagClient(BaseAPITest):
    """
    GET /api/admin/feature-flags/client/flags 黑盒测试

    客户端获取 Flags (可能不需要 admin 权限)
    """

    ENDPOINT = Endpoints.ADMIN_FEATURE_FLAGS_CLIENT

    def test_client_flags_public_access(self, anon_client):
        """
        业务规则: 客户端 Flags 可能是公开的
        """
        response = anon_client.get(self.ENDPOINT)
        # 可能是公开的，也可能需要认证
        assert response.status_code in [200, 401]

    def test_client_flags_with_auth(self, auth_client):
        """
        业务规则: 认证用户获取客户端 Flags
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)
        # 响应应该是字典或列表
        assert isinstance(data, (dict, list))


@pytest.mark.p2
class TestAdminFeatureFlagsValidation(BaseAPITest):
    """
    Admin Feature Flags API 参数验证测试
    """

    ENDPOINT = Endpoints.ADMIN_FEATURE_FLAGS

    def test_flag_key_snake_case(self, auth_client):
        """
        业务规则: key 应使用 snake_case
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": "valid_snake_case_key",
                "name": "Valid Key"
            }
        )
        assert response.status_code in [200, 201, 403]

    def test_flag_key_with_numbers(self, auth_client):
        """
        业务规则: key 可以包含数字
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": f"flag_v2_{uuid.uuid4().hex[:8]}",
                "name": "Flag V2"
            }
        )
        assert response.status_code in [200, 201, 403]

    def test_flag_valid_tiers(self, auth_client):
        """
        业务规则: 测试所有有效的 tier 值
        """
        valid_tiers = ["t1", "t2", "t3", "t4"]
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": f"all_tiers_flag_{uuid.uuid4().hex[:8]}",
                "name": "All Tiers Flag",
                "allowed_tiers": valid_tiers
            }
        )
        assert response.status_code in [200, 201, 403]

    def test_flag_percentage_rollout(self, auth_client):
        """
        业务规则: 百分比发布
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": f"rollout_flag_{uuid.uuid4().hex[:8]}",
                "name": "Rollout Flag",
                "rollout_percentage": 50
            }
        )
        assert response.status_code in [200, 201, 403]

    def test_flag_invalid_percentage(self, auth_client):
        """
        业务规则: 无效的百分比值
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": "invalid_percentage_flag",
                "name": "Invalid Percentage",
                "rollout_percentage": 150  # 超过 100
            }
        )
        assert response.status_code in [400, 403, 422]
