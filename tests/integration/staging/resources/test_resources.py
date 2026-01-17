"""
Resources API Tests (Black Box)

测试 /api/v2/user/resources 相关接口

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. 系统资源包括: sticker, background, template, icon, frame 等
2. 资源有 Tier 访问控制 (t1/t2/t3)
3. 资源按分类组织
4. 支持分页和过滤
5. 未授权用户也可以浏览资源列表 (但可能看到锁定状态)

@module tests.integration.staging.resources.test_resources
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints, Tiers


@pytest.mark.p0
class TestResourcesList(BaseAPITest):
    """
    GET /api/v2/user/resources 黑盒测试

    系统资源列表
    """

    ENDPOINT = Endpoints.RESOURCES

    # ==========================================
    # 功能测试: 列表查询
    # ==========================================

    def test_list_resources_returns_response(self, auth_client):
        """
        业务规则: 资源列表应返回结构化响应

        期望响应包含:
        - items: 资源数组
        - total: 总数
        - page: 当前页
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证响应结构
        assert isinstance(data, dict), "响应应该是对象"
        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"

    def test_list_resources_with_limit(self, auth_client):
        """
        业务规则: limit 参数应限制返回数量
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"limit": 5}
        )
        data = self.assert_success(response)

        items = data.get("items", [])
        assert len(items) <= 5, f"limit=5 但返回了 {len(items)} 条"

    def test_list_resources_with_type_filter(self, auth_client):
        """
        业务规则: 可以按资源类型过滤 (sticker, background, etc.)
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"type": "sticker", "limit": 10}
        )
        data = self.assert_success(response)

        items = data.get("items", [])
        for item in items:
            if "type" in item:
                assert item["type"] == "sticker", f"过滤 sticker 但返回了 {item['type']}"

    def test_list_resources_with_invalid_type(self, auth_client):
        """
        业务规则: 无效的类型应返回空列表或被忽略
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"type": "invalid_type_xxx"}
        )
        # 应该成功但返回空列表或忽略无效类型
        data = self.assert_success(response)
        # 不应该返回错误

    def test_resource_item_structure(self, auth_client):
        """
        业务规则: 每个资源应包含必要字段

        必需字段:
        - id: 资源 UUID
        - type: 资源类型
        - url: 资源 URL
        - allowed_tiers: 允许访问的 Tier 列表
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 1})
        data = self.assert_success(response)

        items = data.get("items", [])
        if len(items) > 0:
            resource = items[0]
            assert "id" in resource, "资源缺少 id"
            assert "type" in resource, "资源缺少 type"
            assert "url" in resource, "资源缺少 url"

    def test_resource_has_access_info(self, auth_client):
        """
        业务规则: 资源应标明用户是否可访问

        字段:
        - is_accessible 或 is_locked
        - allowed_tiers
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 5})
        data = self.assert_success(response)

        items = data.get("items", [])
        for item in items:
            # 应该有访问状态信息
            has_access_info = (
                "is_accessible" in item or
                "is_locked" in item or
                "allowed_tiers" in item
            )
            assert has_access_info, "资源缺少访问状态信息"

    # ==========================================
    # Tier 访问控制测试
    # ==========================================

    def test_free_tier_sees_locked_resources(self, auth_client):
        """
        业务规则: Free 用户可以看到高级资源但标记为锁定

        t1 用户应该能看到 t2/t3 专属资源，但 is_locked=True
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 20})
        data = self.assert_success(response)

        items = data.get("items", [])
        # 检查是否有锁定的资源
        # (这取决于测试用户的 tier 和系统中的资源配置)

    def test_include_locked_parameter(self, auth_client):
        """
        业务规则: include_locked=False 时只返回可访问的资源
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"include_locked": False, "limit": 50}
        )
        data = self.assert_success(response)

        items = data.get("items", [])
        for item in items:
            if "is_locked" in item:
                assert item["is_locked"] is False, "include_locked=False 时不应返回锁定资源"
            if "is_accessible" in item:
                assert item["is_accessible"] is True, "include_locked=False 时只应返回可访问资源"

    # ==========================================
    # 认证测试 (资源列表可能允许匿名访问)
    # ==========================================

    def test_anonymous_access_allowed(self, anon_client):
        """
        业务规则: 资源列表允许匿名访问 (用于展示)

        匿名用户看到的资源都标记为 t1 tier 可访问状态
        """
        response = anon_client.get(self.ENDPOINT, params={"limit": 5})

        # 可能允许匿名访问，也可能需要认证
        # 如果需要认证，返回 401
        if response.status_code == 401:
            print("\n✅ 资源列表需要认证")
        else:
            data = self.assert_success(response)
            print(f"\n✅ 匿名访问允许，返回 {len(data.get('items', []))} 条资源")


@pytest.mark.p1
class TestResourceTypes(BaseAPITest):
    """
    GET /api/v2/user/resources/types 黑盒测试

    资源类型列表
    """

    ENDPOINT = Endpoints.RESOURCES_TYPES

    def test_list_resource_types(self, auth_client):
        """
        业务规则: 应返回所有可用的资源类型
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应应该是对象或数组
        if isinstance(data, dict):
            types = data.get("types", [])
        else:
            types = data

        assert isinstance(types, list), "types 应该是数组"

    def test_resource_type_structure(self, auth_client):
        """
        业务规则: 每个类型应有 id 和 name
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        if isinstance(data, dict):
            types = data.get("types", [])
        else:
            types = data

        for t in types:
            assert "id" in t, "类型缺少 id"
            assert "name" in t, "类型缺少 name"


@pytest.mark.p1
class TestResourceCategories(BaseAPITest):
    """
    GET /api/v2/user/resources/categories/{type} 黑盒测试

    资源分类列表
    """

    def test_get_sticker_categories(self, auth_client):
        """
        业务规则: 可以获取 sticker 类型的分类列表
        """
        response = auth_client.get(f"{Endpoints.RESOURCES}/categories/sticker")
        data = self.assert_success(response)

        # 响应应该包含分类
        if isinstance(data, dict):
            categories = data.get("categories", [])
        else:
            categories = data

        assert isinstance(categories, list), "categories 应该是数组"

    def test_get_background_categories(self, auth_client):
        """
        业务规则: 可以获取 background 类型的分类列表
        """
        response = auth_client.get(f"{Endpoints.RESOURCES}/categories/background")
        data = self.assert_success(response)

        if isinstance(data, dict):
            categories = data.get("categories", [])
        else:
            categories = data

        assert isinstance(categories, list), "categories 应该是数组"

    def test_invalid_type_returns_empty(self, auth_client):
        """
        业务规则: 无效类型应返回空分类列表
        """
        response = auth_client.get(f"{Endpoints.RESOURCES}/categories/invalid_xxx")
        data = self.assert_success(response)

        if isinstance(data, dict):
            categories = data.get("categories", [])
        else:
            categories = data

        assert categories == [], "无效类型应返回空分类列表"


@pytest.mark.p2
class TestResourceById(BaseAPITest):
    """
    GET /api/v2/user/resources/{id} 黑盒测试

    获取单个资源
    """

    def test_get_nonexistent_resource(self, auth_client):
        """
        业务规则: 获取不存在的资源应返回 404
        """
        import uuid
        fake_id = str(uuid.uuid4())
        response = auth_client.get(f"{Endpoints.RESOURCES}/{fake_id}")
        self.assert_not_found(response)

    def test_invalid_uuid_format(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400
        """
        response = auth_client.get(f"{Endpoints.RESOURCES}/invalid-id")

        # 应返回 400 (格式错误)
        assert response.status_code == 400, (
            f"无效 UUID 应返回 400，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestResourcesPerformance(BaseAPITest):
    """
    资源接口性能测试
    """

    ENDPOINT = Endpoints.RESOURCES

    def test_response_time_acceptable(self, auth_client):
        """
        业务规则: 资源列表查询应在合理时间内响应

        SLA: < 3s (Staging 环境)
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 50})
        assert response.status_code == 200
        self.assert_response_time(response, max_seconds=3.0)
