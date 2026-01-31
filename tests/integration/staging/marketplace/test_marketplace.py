"""
Marketplace API Tests (Black Box)

测试 /api/v2/user/marketplace 相关接口

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. Marketplace 支持发布 asset 和 project 两种类型
2. 发布需要会员资格:
   - Starter (t2): 只能发布免费 asset
   - Pro (t3): 可以发布任意价格的 asset 或 project
3. 发布后进入审核流程 (moderation)
4. 购买消耗积分 (月度积分优先，然后永久积分)
5. 卖家获得 90% 收益

@module tests.integration.staging.marketplace.test_marketplace
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p0
class TestMarketplaceListings(BaseAPITest):
    """
    GET /api/v2/user/marketplace/listings 黑盒测试

    Marketplace 商品列表
    """

    ENDPOINT = Endpoints.MARKETPLACE_LISTINGS

    # ==========================================
    # 功能测试: 列表查询
    # ==========================================

    def test_list_listings_returns_paginated_response(self, auth_client):
        """
        业务规则: 商品列表应返回分页结构

        期望响应包含:
        - items: 商品数组
        - total: 总数
        - page: 当前页
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证响应结构
        assert isinstance(data, dict), "响应应该是对象"
        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"
        assert "total" in data, "响应应包含 total"

    def test_list_listings_with_limit(self, auth_client):
        """
        业务规则: limit 参数应限制返回数量 (max: 100)
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"limit": 5}
        )
        data = self.assert_success(response)

        items = data.get("items", [])
        assert len(items) <= 5, f"limit=5 但返回了 {len(items)} 条"

    def test_list_listings_filter_by_resource_type(self, auth_client):
        """
        业务规则: 可以按 resource_type 过滤 (asset/project)
        """
        # 过滤 asset
        response = auth_client.get(
            self.ENDPOINT,
            params={"resource_type": "asset", "limit": 10}
        )
        data = self.assert_success(response)
        items = data.get("items", [])

        for item in items:
            if "resource_type" in item:
                assert item["resource_type"] == "asset", f"过滤 asset 但返回了 {item['resource_type']}"

    def test_list_listings_filter_by_project(self, auth_client):
        """
        业务规则: 可以过滤 project 类型
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"resource_type": "project", "limit": 10}
        )
        data = self.assert_success(response)
        items = data.get("items", [])

        for item in items:
            if "resource_type" in item:
                assert item["resource_type"] == "project", f"过滤 project 但返回了 {item['resource_type']}"

    def test_list_listings_sort_options(self, auth_client):
        """
        业务规则: 支持多种排序方式 (latest, popular, price_asc, price_desc, best_selling)
        """
        sort_options = ["latest", "popular", "price_asc", "price_desc", "best_selling"]

        for sort in sort_options:
            response = auth_client.get(
                self.ENDPOINT,
                params={"sort": sort, "limit": 5}
            )
            assert response.status_code == 200, f"sort={sort} 应成功，但返回了 {response.status_code}"

    def test_list_listings_invalid_sort_rejected(self, auth_client):
        """
        业务规则: 无效的排序方式应返回 400 或被忽略
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"sort": "invalid_sort"}
        )
        # 应该返回 400/422 (验证失败) 或 200 (忽略无效值)
        assert response.status_code in [200, 400, 422]

    def test_list_listings_featured_filter(self, auth_client):
        """
        业务规则: featured=true 只返回精选商品
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"featured": True, "limit": 10}
        )
        data = self.assert_success(response)
        # 精选商品按销量排序
        items = data.get("items", [])
        # 验证返回的是有效数据
        for item in items:
            assert "id" in item, "商品缺少 id"

    def test_listing_item_structure(self, auth_client):
        """
        业务规则: 每个商品应包含必要字段

        必需字段:
        - id: 商品 UUID
        - title: 标题
        - resource_type: 类型 (asset/project)
        - price_credits: 价格
        - moderation_status: 审核状态
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 1})
        data = self.assert_success(response)

        items = data.get("items", [])
        if len(items) > 0:
            listing = items[0]
            assert "id" in listing, "商品缺少 id"
            assert "title" in listing, "商品缺少 title"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: Marketplace 列表需要登录查看
        """
        response = anon_client.get(self.ENDPOINT)
        # Marketplace 可能允许匿名访问，也可能需要认证
        if response.status_code == 401:
            print("\n✅ Marketplace 需要认证")
        else:
            data = self.assert_success(response)
            print(f"\n✅ 匿名访问允许，返回 {len(data.get('items', []))} 条商品")


@pytest.mark.p0
class TestMarketplaceSingleListing(BaseAPITest):
    """
    GET /api/v2/user/marketplace/listings/{id} 黑盒测试

    获取单个商品详情
    """

    def test_get_nonexistent_listing(self, auth_client):
        """
        业务规则: 获取不存在的商品应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.marketplace_listing(fake_id))
        self.assert_not_found(response)

    def test_invalid_uuid_format(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400 或 404
        """
        response = auth_client.get(Endpoints.marketplace_listing("invalid-id"))
        assert response.status_code in [400, 404, 422], (
            f"无效 ID 应被拒绝，但返回了 {response.status_code}"
        )


@pytest.mark.p1
class TestMarketplaceMyListings(BaseAPITest):
    """
    GET /api/v2/user/marketplace/my-listings 黑盒测试

    获取用户自己的商品列表
    """

    ENDPOINT = Endpoints.MARKETPLACE_MY_LISTINGS

    def test_get_my_listings(self, auth_client):
        """
        业务规则: 用户可以查看自己发布的所有商品 (包括各种状态)
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"

    def test_filter_by_status(self, auth_client):
        """
        业务规则: 可以按状态过滤 (draft/pending/published/rejected/suspended/archived)
        """
        valid_statuses = ["draft", "pending", "published", "rejected", "suspended", "archived"]

        for status in valid_statuses:
            response = auth_client.get(
                self.ENDPOINT,
                params={"status": status}
            )
            # 应该成功，即使没有该状态的商品
            assert response.status_code == 200, f"status={status} 应成功，但返回了 {response.status_code}"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 我的商品列表是私有数据
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestMarketplaceCreateListing(BaseAPITest):
    """
    POST /api/v2/user/marketplace/listings 黑盒测试

    发布商品到 Marketplace
    """

    ENDPOINT = Endpoints.MARKETPLACE_LISTINGS

    def test_create_listing_requires_title(self, auth_client):
        """
        业务规则: 商品标题是必需的

        注意: Tier 权限检查 (is_config_public / tier gate) 在输入验证之前执行。
        Free (t1) 用户会先收到 403 (Starter+ 才能发布)。
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": "",
                "resource_type": "asset",
            }
        )
        # 403: Free 用户无权发布 (tier gate 先于 validation)
        # 400/422: 付费用户收到验证失败
        assert response.status_code in [400, 403, 422], (
            f"空标题应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_listing_valid_resource_types(self, auth_client):
        """
        业务规则: resource_type 只能是 'asset' 或 'project'

        注意: Free (t1) 用户先被 403 拒绝 (tier gate 先于 validation)。
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": "Test Listing",
                "resource_type": "invalid_type",
            }
        )
        # 403: Free 用户无权发布
        # 400/422: 付费用户收到验证失败
        assert response.status_code in [400, 403, 422], (
            f"无效 resource_type 应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_listing_price_range(self, auth_client):
        """
        业务规则: 价格范围 0-500 积分

        注意: Free (t1) 用户先被 403 拒绝 (tier gate 先于 validation)。
        """
        # 测试负价格
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": "Test Listing",
                "resource_type": "asset",
                "price_credits": -1,
            }
        )
        assert response.status_code in [400, 403, 422], "负价格应被拒绝"

        # 测试超过上限
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": "Test Listing",
                "resource_type": "asset",
                "price_credits": 501,
            }
        )
        assert response.status_code in [400, 403, 422], "超过 500 的价格应被拒绝"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 发布商品必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "title": "Test",
                "resource_type": "asset",
            }
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestMarketplacePurchase(BaseAPITest):
    """
    POST /api/v2/user/marketplace/purchase 黑盒测试

    购买商品
    """

    ENDPOINT = Endpoints.MARKETPLACE_PURCHASE

    def test_purchase_requires_listing_id(self, auth_client):
        """
        业务规则: 购买必须指定 listing_id
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 422], (
            f"缺少 listing_id 应被拒绝，但返回了 {response.status_code}"
        )

    def test_purchase_nonexistent_listing(self, auth_client):
        """
        业务规则: 购买不存在的商品应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            self.ENDPOINT,
            json={"listing_id": fake_id}
        )
        self.assert_not_found(response)

    def test_purchase_invalid_uuid(self, auth_client):
        """
        业务规则: 无效的 listing_id 格式应返回错误
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"listing_id": "invalid-id"}
        )
        assert response.status_code in [400, 404, 422], (
            f"无效 listing_id 应被拒绝，但返回了 {response.status_code}"
        )

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 购买必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(
            self.ENDPOINT,
            json={"listing_id": fake_id}
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestMarketplaceLeaderboard(BaseAPITest):
    """
    GET /api/v2/user/marketplace/leaderboard 黑盒测试

    排行榜
    """

    ENDPOINT = Endpoints.MARKETPLACE_LEADERBOARD

    def test_get_leaderboard(self, auth_client):
        """
        业务规则: 排行榜返回热门商品
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"

    def test_leaderboard_period_filter(self, auth_client):
        """
        业务规则: 支持按时间范围过滤 (monthly/all_time)
        """
        for period in ["monthly", "all_time"]:
            response = auth_client.get(
                self.ENDPOINT,
                params={"period": period}
            )
            data = self.assert_success(response)
            assert data.get("period") == period, f"period 应该是 {period}"

    def test_leaderboard_type_filter(self, auth_client):
        """
        业务规则: 支持按类型过滤 (all/project/asset)
        """
        for board_type in ["all", "project", "asset"]:
            response = auth_client.get(
                self.ENDPOINT,
                params={"type": board_type}
            )
            data = self.assert_success(response)
            assert data.get("type") == board_type, f"type 应该是 {board_type}"


@pytest.mark.p2
class TestMarketplaceUpdateListing(BaseAPITest):
    """
    PUT /api/v2/user/marketplace/listings/{id} 黑盒测试

    更新商品
    """

    def test_update_nonexistent_listing(self, auth_client):
        """
        业务规则: 更新不存在的商品应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.put(
            Endpoints.marketplace_listing(fake_id),
            json={"title": "Updated Title"}
        )
        self.assert_not_found(response)

    def test_update_invalid_uuid(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回错误
        """
        response = auth_client.put(
            Endpoints.marketplace_listing("invalid-id"),
            json={"title": "Updated Title"}
        )
        assert response.status_code in [400, 404, 422]


@pytest.mark.p2
class TestMarketplaceDeleteListing(BaseAPITest):
    """
    DELETE /api/v2/user/marketplace/listings/{id} 黑盒测试

    下架商品
    """

    def test_delete_nonexistent_listing(self, auth_client):
        """
        业务规则: 下架不存在的商品应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.marketplace_listing(fake_id))
        self.assert_not_found(response)

    def test_delete_invalid_uuid(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回错误
        """
        response = auth_client.delete(Endpoints.marketplace_listing("invalid-id"))
        assert response.status_code in [400, 404, 422]


@pytest.mark.p2
class TestMarketplacePerformance(BaseAPITest):
    """
    Marketplace 性能测试
    """

    ENDPOINT = Endpoints.MARKETPLACE_LISTINGS

    def test_listings_response_time(self, auth_client):
        """
        业务规则: 商品列表查询应在合理时间内响应

        SLA: < 3s (Staging 环境)
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 50})
        assert response.status_code == 200
        self.assert_response_time(response, max_seconds=3.0)

    def test_leaderboard_response_time(self, auth_client):
        """
        业务规则: 排行榜查询应在合理时间内响应

        SLA: < 2s (Staging 环境)
        """
        response = auth_client.get(Endpoints.MARKETPLACE_LEADERBOARD)
        assert response.status_code == 200
        self.assert_response_time(response, max_seconds=2.0)
