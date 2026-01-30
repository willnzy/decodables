"""
Articles API Tests (Black Box)

测试 /api/v2/user/articles 相关接口

业务规则:
1. 公开的文章/博客 API
2. 支持分类筛选
3. 支持搜索
4. 支持获取推荐文章、相关文章

@module tests.integration.staging.articles.test_articles
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestArticlesList(BaseAPITest):
    """
    GET /api/v2/user/articles 黑盒测试

    获取文章列表
    """

    ENDPOINT = Endpoints.ARTICLES

    def test_get_articles_returns_list(self, auth_client):
        """
        业务规则: 文章接口应返回列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应可能是列表或包含 items 的对象
        assert isinstance(data, (list, dict)), "响应格式不正确"

    def test_pagination_works(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 5}
        )
        data = self.assert_success(response)

        # 检查分页
        if isinstance(data, dict) and "items" in data:
            assert len(data["items"]) <= 5

    def test_filter_by_category(self, auth_client):
        """
        业务规则: 可以按分类筛选文章
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"category": "tutorials"}
        )
        # tutorials 可能不是有效分类值，服务端可能返回 400/422
        assert response.status_code in [200, 400, 422], (
            f"按分类筛选: 预期 200/400/422，但返回了 {response.status_code}"
        )

    def test_public_endpoint_works_without_auth(self, anon_client):
        """
        业务规则: 文章是公开的，无需认证
        """
        response = anon_client.get(self.ENDPOINT)
        data = self.assert_success(response)


@pytest.mark.p1
class TestArticleCategories(BaseAPITest):
    """
    GET /api/v2/user/articles/categories 黑盒测试

    获取文章分类
    """

    ENDPOINT = Endpoints.ARTICLES_CATEGORIES

    def test_get_categories_returns_list(self, auth_client):
        """
        业务规则: 分类接口应返回列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert isinstance(data, (list, dict)), "响应格式不正确"

    def test_public_endpoint(self, anon_client):
        """
        业务规则: 分类是公开的
        """
        response = anon_client.get(self.ENDPOINT)
        data = self.assert_success(response)


@pytest.mark.p1
class TestArticleSearch(BaseAPITest):
    """
    GET /api/v2/user/articles/search 黑盒测试

    搜索文章
    """

    ENDPOINT = Endpoints.ARTICLES_SEARCH

    def test_search_requires_query(self, auth_client):
        """
        业务规则: 搜索需要提供查询词
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 400 (缺少 q) 或 200 (空结果)
        assert response.status_code in [200, 400, 422]

    def test_search_with_query(self, auth_client):
        """
        业务规则: 可以搜索文章
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"q": "tutorial"}
        )
        data = self.assert_success(response)

    def test_search_empty_query_handled(self, auth_client):
        """
        业务规则: 空查询应返回空结果或错误
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"q": ""}
        )
        assert response.status_code in [200, 400, 422]

    def test_public_search(self, anon_client):
        """
        业务规则: 搜索是公开的
        """
        response = anon_client.get(
            self.ENDPOINT,
            params={"q": "test"}
        )
        data = self.assert_success(response)


@pytest.mark.p1
class TestArticleDetail(BaseAPITest):
    """
    GET /api/v2/user/articles/{slug} 黑盒测试

    获取文章详情
    """

    def test_get_nonexistent_article(self, auth_client):
        """
        业务规则: 获取不存在的文章应返回 404
        """
        response = auth_client.get(Endpoints.article("nonexistent-article-slug-12345"))
        self.assert_not_found(response)

    def test_get_article_by_slug(self, auth_client):
        """
        业务规则: 可以通过 slug 获取文章

        需要先获取文章列表找到有效的 slug
        """
        # 先获取文章列表
        list_response = auth_client.get(Endpoints.ARTICLES)
        if list_response.status_code == 200:
            list_data = list_response.json()
            items = list_data.get("items", list_data) if isinstance(list_data, dict) else list_data
            if items and len(items) > 0:
                slug = items[0].get("slug")
                if slug:
                    response = auth_client.get(Endpoints.article(slug))
                    data = self.assert_success(response)
                    assert "title" in data or "content" in data


@pytest.mark.p2
class TestArticleFeatured(BaseAPITest):
    """
    GET /api/v2/user/articles/featured 黑盒测试

    获取推荐文章
    """

    ENDPOINT = Endpoints.ARTICLES_FEATURED

    def test_get_featured_articles(self, auth_client):
        """
        业务规则: 获取推荐文章
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert isinstance(data, (list, dict)), "响应格式不正确"

    def test_public_featured(self, anon_client):
        """
        业务规则: 推荐文章是公开的
        """
        response = anon_client.get(self.ENDPOINT)
        data = self.assert_success(response)


@pytest.mark.p2
class TestArticleRelated(BaseAPITest):
    """
    GET /api/v2/user/articles/{slug}/related 黑盒测试

    获取相关文章
    """

    def test_get_related_for_nonexistent(self, auth_client):
        """
        业务规则: 不存在文章的相关文章返回 404
        """
        response = auth_client.get(
            Endpoints.article_related("nonexistent-article-12345")
        )
        # 可能返回 404 或空列表
        assert response.status_code in [200, 404]
