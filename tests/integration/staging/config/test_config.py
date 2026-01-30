"""
Config API Tests (Black Box)

测试 /api/v2/user/config 相关接口

业务规则:
1. 公开的配置 API
2. 支持按 key 获取单个配置
3. 支持按 group 获取一组配置

@module tests.integration.staging.config.test_config
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestConfigList(BaseAPITest):
    """
    GET /api/v2/user/config 黑盒测试

    获取所有公开配置
    """

    ENDPOINT = Endpoints.CONFIG

    def test_get_configs_returns_dict(self, auth_client):
        """
        业务规则: 配置接口应返回字典
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 配置通常是 key-value 字典
        assert isinstance(data, dict), "响应应该是字典"

    def test_public_endpoint(self, anon_client):
        """
        业务规则: 配置是公开的，无需认证
        """
        response = anon_client.get(self.ENDPOINT)
        data = self.assert_success(response)


@pytest.mark.p1
class TestConfigByKey(BaseAPITest):
    """
    GET /api/v2/user/config/{key} 黑盒测试

    按 key 获取单个配置
    """

    def test_get_nonexistent_key(self, auth_client):
        """
        业务规则: 获取不存在的配置 key

        可能返回 404 或 null
        """
        response = auth_client.get(Endpoints.config_key("nonexistent_config_key_12345"))
        # 可能返回 404 或 200 + null
        assert response.status_code in [200, 404]

    def test_get_valid_config_key(self, auth_client):
        """
        业务规则: 获取存在的配置 key

        先获取所有配置，找到一个有效的 key
        """
        # 先获取所有配置
        all_response = auth_client.get(Endpoints.CONFIG)
        if all_response.status_code == 200:
            all_configs = all_response.json()
            if all_configs and isinstance(all_configs, dict):
                # 找第一个 key
                first_key = list(all_configs.keys())[0] if all_configs else None
                if first_key:
                    response = auth_client.get(Endpoints.config_key(first_key))
                    data = self.assert_success(response)

    def test_non_public_key_returns_403(self, auth_client):
        """
        业务规则: 非公开 key 返回 403

        config/{key} 端点会检查 is_config_public(key)，
        不在白名单 (FEATURE_*, UI_*, PRICING_*, tier.* 等) 中的 key 返回 403。
        "app_name" 不匹配任何公开前缀，因此返回 403。
        """
        response = auth_client.get(Endpoints.config_key("app_name"))
        assert response.status_code == 403

    def test_public_key_accessible(self, auth_client):
        """
        业务规则: 匹配公开白名单的 key 可以访问

        白名单前缀包括: FEATURE_, UI_, PRICING_, tier. 等
        """
        response = auth_client.get(Endpoints.config_key("FEATURE_dark_mode"))
        # 200 (key 存在) 或 404 (key 不存在但前缀合法)
        assert response.status_code in [200, 404]


@pytest.mark.p1
class TestConfigByGroup(BaseAPITest):
    """
    GET /api/v2/user/config/group/{group} 黑盒测试

    按 group 获取一组配置
    """

    def test_get_nonexistent_group(self, auth_client):
        """
        业务规则: 获取不存在的配置组

        可能返回 404 或空对象
        """
        response = auth_client.get(Endpoints.config_group("nonexistent_group_12345"))
        # 可能返回 404 或 200 + 空对象
        assert response.status_code in [200, 404]

    def test_get_pricing_group(self, auth_client):
        """
        业务规则: 获取 pricing 配置组

        pricing 是常见的配置组
        """
        response = auth_client.get(Endpoints.config_group("pricing"))
        # 可能存在也可能不存在
        assert response.status_code in [200, 404]

    def test_get_features_group(self, auth_client):
        """
        业务规则: 获取 features 配置组
        """
        response = auth_client.get(Endpoints.config_group("features"))
        assert response.status_code in [200, 404]

    def test_public_endpoint(self, anon_client):
        """
        业务规则: 配置组也是公开的
        """
        response = anon_client.get(Endpoints.config_group("app"))
        assert response.status_code in [200, 404]


@pytest.mark.p2
class TestConfigValidation(BaseAPITest):
    """
    Config API 参数验证测试
    """

    def test_key_with_special_chars(self, auth_client):
        """
        业务规则: key 包含特殊字符的处理
        """
        response = auth_client.get(Endpoints.config_key("test/key/with/slashes"))
        # 可能返回 400 (无效格式) 或 404 (未找到)
        assert response.status_code in [200, 400, 404]

    def test_very_long_key(self, auth_client):
        """
        业务规则: 很长的 key 应被拒绝或截断
        """
        long_key = "a" * 500
        response = auth_client.get(Endpoints.config_key(long_key))
        # 应该不会返回 500
        assert response.status_code in [200, 400, 404]


@pytest.mark.p2
class TestConfigResponse(BaseAPITest):
    """
    Config API 响应结构测试
    """

    ENDPOINT = Endpoints.CONFIG

    def test_config_values_types(self, auth_client):
        """
        业务规则: 配置值可以是多种类型
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 检查值类型是否合理
        for key, value in data.items():
            # 值可以是 string, number, boolean, list, dict, null
            assert isinstance(value, (str, int, float, bool, list, dict, type(None))), (
                f"配置 {key} 的值类型不合理: {type(value)}"
            )
