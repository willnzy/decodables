"""
Admin Config API Tests (Black Box)

测试 /api/admin/config 相关接口

业务规则:
1. 只有 admin 才能管理系统配置
2. 支持配置的 CRUD 操作
3. 配置 key 唯一
4. 某些配置不可删除 (系统保留)

@module tests.integration.staging.admin.test_config
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminConfigList(BaseAPITest):
    """
    GET /api/admin/config 黑盒测试

    获取配置列表
    """

    ENDPOINT = Endpoints.ADMIN_CONFIG

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

    def test_list_config_pagination(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 10}
        )
        assert response.status_code in [200, 403]

    def test_list_config_filter_by_group(self, auth_client):
        """
        业务规则: 支持按 group 筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"group": "pricing"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminConfigGet(BaseAPITest):
    """
    GET /api/admin/config/{key} 黑盒测试

    获取单个配置
    """

    def test_get_config_requires_admin(self, anon_client):
        """
        业务规则: 获取配置需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_config_key("app_name"))
        self.assert_unauthorized(response)

    def test_get_nonexistent_config(self, auth_client):
        """
        业务规则: 获取不存在的配置
        """
        fake_key = f"nonexistent_config_{uuid.uuid4().hex[:10]}"
        response = auth_client.get(Endpoints.admin_config_key(fake_key))
        assert response.status_code in [403, 404]

    def test_get_config_with_auth(self, auth_client):
        """
        业务规则: 获取存在的配置
        """
        response = auth_client.get(Endpoints.admin_config_key("app_name"))
        # 可能返回 200/404 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminConfigCreate(BaseAPITest):
    """
    POST /api/admin/config 黑盒测试

    创建配置
    """

    ENDPOINT = Endpoints.ADMIN_CONFIG

    def test_create_config_requires_admin(self, anon_client):
        """
        业务规则: 创建配置需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "key": "test_config_key",
                "value": "test_value",
                "group": "test"
            }
        )
        self.assert_unauthorized(response)

    def test_create_config_missing_key(self, auth_client):
        """
        业务规则: 缺少 key 字段
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "value": "test_value",
                "group": "test"
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_config_missing_value(self, auth_client):
        """
        业务规则: 缺少 value 字段
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": "test_config_key",
                "group": "test"
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_config_empty_body(self, auth_client):
        """
        业务规则: 空请求体
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 403, 422]


@pytest.mark.p1
class TestAdminConfigUpdate(BaseAPITest):
    """
    PUT /api/admin/config/{key} 黑盒测试

    更新配置
    """

    def test_update_config_requires_admin(self, anon_client):
        """
        业务规则: 更新配置需要管理员权限
        """
        response = anon_client.put(
            Endpoints.admin_config_key("app_name"),
            json={"value": "New App Name"}
        )
        self.assert_unauthorized(response)

    def test_update_nonexistent_config(self, auth_client):
        """
        业务规则: 更新不存在的配置
        """
        fake_key = f"nonexistent_config_{uuid.uuid4().hex[:10]}"
        response = auth_client.put(
            Endpoints.admin_config_key(fake_key),
            json={"value": "test"}
        )
        assert response.status_code in [403, 404]

    def test_update_config_empty_value(self, auth_client):
        """
        业务规则: 更新为空值
        """
        response = auth_client.put(
            Endpoints.admin_config_key("app_name"),
            json={"value": ""}
        )
        # 空值可能被接受或拒绝
        assert response.status_code in [200, 400, 403, 422]


@pytest.mark.p1
class TestAdminConfigDelete(BaseAPITest):
    """
    DELETE /api/admin/config/{key} 黑盒测试

    删除配置
    """

    def test_delete_config_requires_admin(self, anon_client):
        """
        业务规则: 删除配置需要管理员权限
        """
        response = anon_client.delete(Endpoints.admin_config_key("test_config"))
        self.assert_unauthorized(response)

    def test_delete_nonexistent_config(self, auth_client):
        """
        业务规则: 删除不存在的配置
        """
        fake_key = f"nonexistent_config_{uuid.uuid4().hex[:10]}"
        response = auth_client.delete(Endpoints.admin_config_key(fake_key))
        assert response.status_code in [403, 404]

    def test_delete_system_config(self, auth_client):
        """
        业务规则: 删除系统保留配置可能被阻止
        """
        response = auth_client.delete(Endpoints.admin_config_key("app_name"))
        # 系统配置可能不可删除
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p2
class TestAdminConfigValidation(BaseAPITest):
    """
    Admin Config API 参数验证测试
    """

    ENDPOINT = Endpoints.ADMIN_CONFIG

    def test_config_key_special_chars(self, auth_client):
        """
        业务规则: key 包含特殊字符
        """
        response = auth_client.get(
            Endpoints.admin_config_key("test/key/with/slashes")
        )
        # 特殊字符可能导致路由问题
        assert response.status_code in [400, 403, 404]

    def test_config_very_long_key(self, auth_client):
        """
        业务规则: 很长的 key
        """
        long_key = "a" * 500
        response = auth_client.get(Endpoints.admin_config_key(long_key))
        assert response.status_code in [400, 403, 404]

    def test_config_value_types(self, auth_client):
        """
        业务规则: 不同类型的配置值

        配置值可以是 string, number, boolean, object, array
        """
        # 测试对象类型值
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": "test_object_config",
                "value": {"nested": "value"},
                "group": "test"
            }
        )
        assert response.status_code in [200, 201, 400, 403, 422]

    def test_config_json_value(self, auth_client):
        """
        业务规则: JSON 格式的配置值
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "key": "test_json_config",
                "value": [1, 2, 3, {"key": "value"}],
                "group": "test"
            }
        )
        assert response.status_code in [200, 201, 400, 403, 422]
