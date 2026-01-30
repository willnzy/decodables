"""
Admin Config API Tests (Black Box)

测试 /api/v2/admin/config 相关接口

业务规则:
1. 只有 admin 才能管理系统配置
2. 支持获取所有配置、单个配置、更新配置
3. 支持速率限制配置管理
4. 支持缓存清除

实际端点 (router prefix = /config):
- GET /config - 获取所有配置
- GET /config/{config_key} - 获取单个配置
- PUT /config - 更新配置
- PUT /config/batch - 批量更新配置
- GET /config/rate-limits - 获取速率限制
- POST /config/rate-limits/preset - 应用速率限制预设
- GET /config/rate-limits/presets - 获取速率限制预设列表
- POST /config/cache/clear - 清除配置缓存

@module tests.integration.staging.admin.test_config
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import API_ADMIN

# Base path for config endpoints (router prefix is /config)
CONFIG_BASE = f"{API_ADMIN}/config"


@pytest.mark.p1
class TestAdminConfigList(BaseAPITest):
    """
    GET /api/v2/admin/config 黑盒测试

    获取所有配置 (router prefix = /config, route = GET /)
    """

    ENDPOINT = CONFIG_BASE

    def test_list_config_requires_admin(self, anon_client):
        """
        业务规则: 获取配置列表需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_list_config_with_auth(self, auth_client):
        """
        业务规则: 认证用户获取配置列表
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_list_config_with_category_filter(self, auth_client):
        """
        业务规则: 支持按 category 筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"category": "rate_limit"}
        )
        assert response.status_code in [200, 403]

    def test_list_config_invalid_category(self, auth_client):
        """
        业务规则: 无效的 category 值
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"category": "invalid_category_12345"}
        )
        assert response.status_code in [400, 403]


@pytest.mark.p1
class TestAdminConfigGetSingle(BaseAPITest):
    """
    GET /api/v2/admin/config/{config_key} 黑盒测试

    获取单个配置 (router prefix = /config, route = GET /{config_key})
    """

    def _get_endpoint(self, config_key: str) -> str:
        return f"{CONFIG_BASE}/{config_key}"

    def test_get_config_requires_admin(self, anon_client):
        """
        业务规则: 获取配置需要管理员权限
        """
        response = anon_client.get(self._get_endpoint("app_name"))
        self.assert_unauthorized(response)

    def test_get_nonexistent_config(self, auth_client):
        """
        业务规则: 获取不存在的配置
        """
        fake_key = f"nonexistent_config_{uuid.uuid4().hex[:10]}"
        response = auth_client.get(self._get_endpoint(fake_key))
        assert response.status_code in [403, 404]

    def test_get_config_with_auth(self, auth_client):
        """
        业务规则: 获取存在的配置
        """
        response = auth_client.get(self._get_endpoint("app_name"))
        # 可能返回 200/404 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminConfigUpdate(BaseAPITest):
    """
    PUT /api/v2/admin/config 黑盒测试

    更新配置 (router prefix = /config, route = PUT /)
    """

    ENDPOINT = CONFIG_BASE

    def test_update_config_requires_admin(self, anon_client):
        """
        业务规则: 更新配置需要管理员权限
        """
        response = anon_client.put(
            self.ENDPOINT,
            json={"config_key": "app_name", "value": "New App Name"}
        )
        self.assert_unauthorized(response)

    def test_update_config_missing_key(self, auth_client):
        """
        业务规则: 缺少 config_key 字段
        """
        response = auth_client.put(
            self.ENDPOINT,
            json={"value": "test_value"}
        )
        assert response.status_code in [400, 403, 422]

    def test_update_config_missing_value(self, auth_client):
        """
        业务规则: 缺少 value 字段
        """
        response = auth_client.put(
            self.ENDPOINT,
            json={"config_key": "app_name"}
        )
        assert response.status_code in [400, 403, 422]

    def test_update_config_empty_body(self, auth_client):
        """
        业务规则: 空请求体
        """
        response = auth_client.put(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 403, 422]

    def test_update_nonexistent_config(self, auth_client):
        """
        业务规则: 更新不存在的配置
        """
        fake_key = f"nonexistent_config_{uuid.uuid4().hex[:10]}"
        response = auth_client.put(
            self.ENDPOINT,
            json={"config_key": fake_key, "value": "test"}
        )
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminConfigBatchUpdate(BaseAPITest):
    """
    PUT /api/v2/admin/config/batch 黑盒测试

    批量更新配置 (router prefix = /config, route = PUT /batch)
    """

    ENDPOINT = f"{CONFIG_BASE}/batch"

    def test_batch_update_requires_admin(self, anon_client):
        """
        业务规则: 批量更新需要管理员权限
        """
        response = anon_client.put(
            self.ENDPOINT,
            json={"updates": [{"config_key": "test", "value": "value"}]}
        )
        self.assert_unauthorized(response)

    def test_batch_update_empty_updates(self, auth_client):
        """
        业务规则: 空更新列表
        """
        response = auth_client.put(
            self.ENDPOINT,
            json={"updates": []}
        )
        assert response.status_code in [200, 400, 403, 422]

    def test_batch_update_valid(self, auth_client):
        """
        业务规则: 有效的批量更新
        """
        response = auth_client.put(
            self.ENDPOINT,
            json={
                "updates": [
                    {"config_key": "test_key_1", "value": "value_1"},
                    {"config_key": "test_key_2", "value": "value_2"}
                ]
            }
        )
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminRateLimits(BaseAPITest):
    """
    GET /api/v2/admin/config/rate-limits 黑盒测试

    获取速率限制配置
    """

    ENDPOINT = f"{CONFIG_BASE}/rate-limits"

    def test_rate_limits_requires_admin(self, anon_client):
        """
        业务规则: 获取速率限制需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_rate_limits_with_auth(self, auth_client):
        """
        业务规则: 认证用户获取速率限制
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminRateLimitPresets(BaseAPITest):
    """
    GET /api/v2/admin/config/rate-limits/presets 黑盒测试

    获取速率限制预设列表
    """

    ENDPOINT = f"{CONFIG_BASE}/rate-limits/presets"

    def test_presets_requires_admin(self, anon_client):
        """
        业务规则: 获取预设列表需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_presets_with_auth(self, auth_client):
        """
        业务规则: 认证用户获取预设列表
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminRateLimitPresetApply(BaseAPITest):
    """
    POST /api/v2/admin/config/rate-limits/preset 黑盒测试

    应用速率限制预设
    """

    ENDPOINT = f"{CONFIG_BASE}/rate-limits/preset"

    def test_apply_preset_requires_admin(self, anon_client):
        """
        业务规则: 应用预设需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"preset_name": "default"}
        )
        self.assert_unauthorized(response)

    def test_apply_preset_missing_name(self, auth_client):
        """
        业务规则: 缺少预设名称
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 403, 422]

    def test_apply_invalid_preset(self, auth_client):
        """
        业务规则: 无效的预设名称
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"preset_name": "nonexistent_preset_12345"}
        )
        assert response.status_code in [400, 403, 422]


@pytest.mark.p1
class TestAdminConfigCacheClear(BaseAPITest):
    """
    POST /api/v2/admin/config/cache/clear 黑盒测试

    清除配置缓存 (router prefix = /config, route = POST /cache/clear)
    """

    ENDPOINT = f"{CONFIG_BASE}/cache/clear"

    def test_cache_clear_requires_admin(self, anon_client):
        """
        业务规则: 清除缓存需要管理员权限
        """
        response = anon_client.post(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_cache_clear_with_auth(self, auth_client):
        """
        业务规则: 认证用户清除缓存
        """
        response = auth_client.post(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminConfigValidation(BaseAPITest):
    """
    Admin Config API 参数验证测试
    """

    def test_config_key_special_chars(self, auth_client):
        """
        业务规则: key 包含特殊字符 (斜杠)
        """
        response = auth_client.get(
            f"{CONFIG_BASE}/test/key/with/slashes"
        )
        # 特殊字符可能导致路由问题
        assert response.status_code in [400, 403, 404]

    def test_config_very_long_key(self, auth_client):
        """
        业务规则: 很长的 key (超过 200 字符)
        """
        long_key = "a" * 250
        response = auth_client.get(f"{CONFIG_BASE}/{long_key}")
        assert response.status_code in [400, 403, 404, 422]

    def test_update_with_json_value(self, auth_client):
        """
        业务规则: JSON 格式的配置值
        """
        response = auth_client.put(
            CONFIG_BASE,
            json={
                "config_key": "test_json_config",
                "value": {"nested": "value", "array": [1, 2, 3]}
            }
        )
        assert response.status_code in [200, 400, 403, 422]
