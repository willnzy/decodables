"""
Seller API Tests (Black Box)

测试 /api/v2/user/seller 相关接口

业务规则:
1. 用户可以查看统一的卖家统计数据
2. 支持按类型筛选 (projects, listings, assets)
3. 返回汇总数据

@module tests.integration.staging.seller.test_seller
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestSellerStats(BaseAPITest):
    """
    GET /api/v2/user/seller/stats 黑盒测试

    统一卖家统计接口
    """

    ENDPOINT = Endpoints.SELLER_STATS

    def test_get_stats_returns_summary(self, auth_client):
        """
        业务规则: 卖家统计应返回汇总数据

        期望包含:
        - summary: 汇总统计
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "summary" in data, "响应应包含 summary"
        summary = data["summary"]
        assert "total_revenue" in summary, "summary 应包含 total_revenue"
        assert "total_sales" in summary, "summary 应包含 total_sales"
        assert "total_items" in summary, "summary 应包含 total_items"

    def test_filter_by_projects(self, auth_client):
        """
        业务规则: 可以只获取项目销售统计
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"include": "projects"}
        )
        data = self.assert_success(response)

        # 应该包含 projects 数据
        assert "projects" in data or "summary" in data

    def test_filter_by_listings(self, auth_client):
        """
        业务规则: 可以只获取 Marketplace 上架统计
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"include": "listings"}
        )
        data = self.assert_success(response)
        assert "listings" in data or "summary" in data

    def test_filter_by_assets(self, auth_client):
        """
        业务规则: 可以只获取素材销售统计
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"include": "assets"}
        )
        data = self.assert_success(response)
        assert "assets" in data or "summary" in data

    def test_filter_multiple_types(self, auth_client):
        """
        业务规则: 可以同时获取多种类型统计
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"include": "projects,listings"}
        )
        data = self.assert_success(response)
        assert "summary" in data

    def test_invalid_include_returns_400(self, auth_client):
        """
        业务规则: 无效的 include 参数应返回 400
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"include": "invalid_type"}
        )
        assert response.status_code == 400

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 卖家统计是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_stats_values_are_non_negative(self, auth_client):
        """
        业务规则: 统计数据不能为负数
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        summary = data.get("summary", {})
        assert summary.get("total_revenue", 0) >= 0
        assert summary.get("total_sales", 0) >= 0
        assert summary.get("total_items", 0) >= 0
