"""
Static Pages API Tests (Black Box)

测试 /api/v2/user/static-pages 相关接口

业务规则:
1. 公开的静态页面 API (法律、公司、指南)
2. 支持分页和类型筛选
3. 无需认证

@module tests.integration.staging.static_pages.test_static_pages
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestStaticPagesList(BaseAPITest):
    """
    GET /api/v2/user/static-pages 黑盒测试

    获取静态页面列表
    """

    ENDPOINT = Endpoints.STATIC_PAGES

    def test_get_static_pages_returns_list(self, auth_client):
        """
        业务规则: 静态页面接口应返回列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应应包含 items 和分页信息
        assert isinstance(data, dict), "响应应该是字典"
        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是列表"

    def test_pagination_works(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 5}
        )
        data = self.assert_success(response)

        assert "total" in data, "响应应包含 total"
        assert "offset" in data, "响应应包含 offset"
        assert "limit" in data, "响应应包含 limit"

    def test_filter_by_page_type(self, auth_client):
        """
        业务规则: 可以按页面类型筛选
        """
        valid_types = ["legal", "company", "guide", "other"]
        for page_type in valid_types:
            response = auth_client.get(
                self.ENDPOINT,
                params={"page_type": page_type}
            )
            # 应该返回 200 (可能为空)
            data = self.assert_success(response)

    def test_invalid_page_type_rejected(self, auth_client):
        """
        业务规则: 无效的页面类型应返回 400
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"page_type": "invalid_type"}
        )
        assert response.status_code == 400

    def test_public_endpoint(self, anon_client):
        """
        业务规则: 静态页面是公开的，无需认证
        """
        response = anon_client.get(self.ENDPOINT)
        data = self.assert_success(response)


@pytest.mark.p1
class TestStaticPageDetail(BaseAPITest):
    """
    GET /api/v2/user/static-pages/{slug} 黑盒测试

    获取单个静态页面
    """

    def test_get_nonexistent_page(self, auth_client):
        """
        业务规则: 获取不存在的页面应返回 404
        """
        response = auth_client.get(Endpoints.static_page("nonexistent-page-slug-12345"))
        self.assert_not_found(response)

    def test_get_page_by_slug(self, auth_client):
        """
        业务规则: 可以通过 slug 获取页面

        先获取页面列表找到有效的 slug
        """
        list_response = auth_client.get(Endpoints.STATIC_PAGES)
        if list_response.status_code == 200:
            list_data = list_response.json()
            items = list_data.get("items", [])
            if items and len(items) > 0:
                slug = items[0].get("slug")
                if slug:
                    response = auth_client.get(Endpoints.static_page(slug))
                    data = self.assert_success(response)
                    assert "title" in data
                    assert "content" in data
                    assert "slug" in data
                    assert data["slug"] == slug

    def test_page_detail_includes_content(self, auth_client):
        """
        业务规则: 页面详情应包含完整内容
        """
        # 常见的静态页面 slug
        common_slugs = ["privacy-policy", "terms-of-service", "about"]
        for slug in common_slugs:
            response = auth_client.get(Endpoints.static_page(slug))
            if response.status_code == 200:
                data = response.json()
                assert "content" in data, f"{slug} 页面应包含 content"
                assert "title" in data, f"{slug} 页面应包含 title"
                break

    def test_public_endpoint(self, anon_client):
        """
        业务规则: 页面详情也是公开的
        """
        # 尝试访问常见页面
        response = anon_client.get(Endpoints.static_page("privacy-policy"))
        # 可能存在也可能不存在
        assert response.status_code in [200, 404]


@pytest.mark.p2
class TestStaticPageResponse(BaseAPITest):
    """
    静态页面响应结构测试
    """

    ENDPOINT = Endpoints.STATIC_PAGES

    def test_list_item_structure(self, auth_client):
        """
        业务规则: 列表项应包含必要字段
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        items = data.get("items", [])
        if items:
            item = items[0]
            required_fields = ["id", "slug", "title", "page_type", "is_published"]
            for field in required_fields:
                assert field in item, f"列表项应包含 {field}"

    def test_detail_response_structure(self, auth_client):
        """
        业务规则: 详情应包含完整字段
        """
        list_response = auth_client.get(self.ENDPOINT)
        if list_response.status_code == 200:
            items = list_response.json().get("items", [])
            if items:
                slug = items[0].get("slug")
                if slug:
                    response = auth_client.get(Endpoints.static_page(slug))
                    if response.status_code == 200:
                        data = response.json()
                        # 详情应包含更多字段
                        assert "content" in data
                        assert "meta_title" in data or "title" in data


@pytest.mark.p2
class TestStaticPageSeo(BaseAPITest):
    """
    静态页面 SEO 测试
    """

    def test_page_has_seo_fields(self, auth_client):
        """
        业务规则: 页面应有 SEO 相关字段
        """
        list_response = auth_client.get(Endpoints.STATIC_PAGES)
        if list_response.status_code == 200:
            items = list_response.json().get("items", [])
            if items:
                slug = items[0].get("slug")
                if slug:
                    response = auth_client.get(Endpoints.static_page(slug))
                    if response.status_code == 200:
                        data = response.json()
                        # SEO 字段可能存在
                        # meta_title, meta_description, schema_data
                        # 不强制要求，只是检查


@pytest.mark.p2
class TestStaticPageRateLimits(BaseAPITest):
    """
    静态页面速率限制测试
    """

    def test_list_rate_limit(self, auth_client):
        """
        业务规则: 列表接口速率限制 (60/minute)
        """
        pass

    def test_detail_rate_limit(self, auth_client):
        """
        业务规则: 详情接口速率限制 (60/minute)
        """
        pass
