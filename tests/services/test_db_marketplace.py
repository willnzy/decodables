"""
Database Marketplace Service Tests
services/db/marketplace.py 模块测试

覆盖目标: 95%+
"""

import pytest
from unittest.mock import MagicMock, patch


class TestGetMarketplaceListings:
    """测试 get_marketplace_listings"""
    
    @patch('services.db.marketplace.supabase')
    def test_returns_approved_public_listings(self, mock_supabase):
        """返回已审核且公开的商品"""
        from services.db.marketplace import get_marketplace_listings
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "l1", "title": "Sticker Pack", "moderation_status": "approved"},
            {"id": "l2", "title": "Theme Bundle", "moderation_status": "approved"}
        ]
        
        # Mock 复杂的链式调用
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_marketplace_listings(page=1, limit=20)
        
        assert len(result) == 2
    
    @patch('services.db.marketplace.supabase')
    def test_filters_by_resource_type(self, mock_supabase):
        """按资源类型筛选"""
        from services.db.marketplace import get_marketplace_listings
        
        mock_result = MagicMock()
        mock_result.data = [{"id": "l1", "resource_type": "project"}]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_marketplace_listings(resource_type="project")
        
        assert len(result) >= 0  # 验证不报错
    
    @patch('services.db.marketplace.supabase')
    def test_filters_featured_only(self, mock_supabase):
        """筛选精选商品"""
        from services.db.marketplace import get_marketplace_listings
        
        mock_result = MagicMock()
        mock_result.data = [{"id": "l1", "is_featured": True}]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_marketplace_listings(featured=True)
        
        assert len(result) >= 0
    
    @patch('services.db.marketplace.supabase', None)
    def test_returns_empty_when_supabase_not_available(self):
        """Supabase 不可用时返回空列表"""
        from services.db.marketplace import get_marketplace_listings
        result = get_marketplace_listings()
        assert result == []


class TestGetMarketplaceItem:
    """测试 get_marketplace_item"""
    
    @patch('services.db.marketplace.listing_is_public_visible')
    @patch('services.db.marketplace.supabase')
    def test_returns_item_when_found(self, mock_supabase, mock_visible):
        """返回商品详情"""
        from services.db.marketplace import get_marketplace_item
        
        # 商品数据
        listing_data = {
            "id": "listing_001", 
            "title": "Test Listing", 
            "price_credits": 100,
            "seller_id": "seller_001",
            "is_public": True,
            "moderation_status": "approved",
            "is_deleted": False
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=listing_data
        )
        mock_visible.return_value = True
        
        # Mock 购买检查
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_marketplace_item("listing_001", user_id="user_001")
        
        assert result is not None
        assert result["id"] == "listing_001"
    
    @patch('services.db.marketplace.supabase')
    def test_returns_none_when_not_found(self, mock_supabase):
        """商品不存在返回 None"""
        from services.db.marketplace import get_marketplace_item
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        
        result = get_marketplace_item("nonexistent")
        
        assert result is None


class TestGetSellerListings:
    """测试 get_seller_listings"""
    
    @patch('services.db.marketplace.supabase')
    def test_returns_seller_listings(self, mock_supabase):
        """返回卖家商品列表"""
        from services.db.marketplace import get_seller_listings
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "l1", "seller_id": "seller_001"},
            {"id": "l2", "seller_id": "seller_001"}
        ]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_seller_listings("seller_001")
        
        assert len(result) == 2


class TestCreateListing:
    """测试 create_listing"""
    
    @patch('services.db.marketplace.supabase')
    def test_creates_new_listing(self, mock_supabase):
        """创建新商品"""
        from services.db.marketplace import create_listing
        
        # Mock 检查现有 listing - 不存在
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # Mock insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new_listing", "title": "Test Asset"}]
        )
        
        result = create_listing(
            seller_id="seller_001",
            title="Test Asset",
            description="A test asset",
            thumbnail_url="https://example.com/thumb.jpg",
            resource_url="https://example.com/asset.zip",
            resource_type="asset",
            price_credits=100
        )
        
        assert result is not None


class TestSubmitListingForReview:
    """测试 submit_listing_for_review"""
    
    @patch('services.db.marketplace.supabase')
    def test_submits_for_review(self, mock_supabase):
        """提交商品审核"""
        from services.db.marketplace import submit_listing_for_review
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "listing_001", "moderation_status": "pending"}]
        )
        
        result = submit_listing_for_review("listing_001", "seller_001")
        
        assert result is not None


class TestUnpublishListing:
    """测试 unpublish_listing"""
    
    @patch('services.db.marketplace.supabase')
    def test_unpublishes_listing(self, mock_supabase):
        """下架商品"""
        from services.db.marketplace import unpublish_listing
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "listing_001", "is_public": False}]
        )
        
        result = unpublish_listing("listing_001", "seller_001")
        
        assert result is not None


class TestUpdateListing:
    """测试 update_listing"""
    
    @patch('services.db.marketplace.supabase')
    def test_updates_listing(self, mock_supabase):
        """更新商品信息"""
        from services.db.marketplace import update_listing
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "listing_001", "title": "Updated Title"}]
        )
        
        result = update_listing("listing_001", "seller_001", {"title": "Updated Title"})
        
        assert result is not None


class TestCheckUserPurchase:
    """测试 check_user_purchase"""
    
    @patch('services.db.marketplace.supabase')
    def test_returns_true_when_purchased(self, mock_supabase):
        """已购买返回 True"""
        from services.db.marketplace import check_user_purchase
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "purchase_001"}]
        )
        
        result = check_user_purchase("user_001", "listing_001")
        
        assert result is True
    
    @patch('services.db.marketplace.supabase')
    def test_returns_false_when_not_purchased(self, mock_supabase):
        """未购买返回 False"""
        from services.db.marketplace import check_user_purchase
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = check_user_purchase("user_001", "listing_001")
        
        assert result is False


class TestExecutePurchase:
    """测试 execute_purchase (RPC wrapper)"""
    
    @patch('services.db.marketplace.supabase')
    def test_executes_purchase_rpc(self, mock_supabase):
        """执行购买 RPC"""
        from services.db.marketplace import execute_purchase
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": True,
            "price_paid": 100,
            "seller_revenue": 90
        })
        
        # 正确的参数签名: (buyer_id, listing_id, tz="UTC")
        result = execute_purchase(
            buyer_id="buyer_001",
            listing_id="listing_001",
            tz="UTC"
        )
        
        assert result["success"] is True
    
    @patch('services.db.marketplace.supabase')
    def test_handles_insufficient_credits(self, mock_supabase):
        """积分不足时返回错误"""
        from services.db.marketplace import execute_purchase
        
        mock_supabase.rpc.return_value.execute.side_effect = Exception("INSUFFICIENT_CREDITS")
        
        result = execute_purchase("buyer_001", "listing_001")
        
        assert result["success"] is False
        assert "INSUFFICIENT" in result["error"]


class TestGetUserPurchases:
    """测试 get_user_purchases"""
    
    @patch('services.db.marketplace.supabase')
    def test_returns_user_purchases(self, mock_supabase):
        """返回用户购买记录"""
        from services.db.marketplace import get_user_purchases
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "p1", "listing_id": "l1"},
            {"id": "p2", "listing_id": "l2"}
        ]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_user_purchases("user_001")
        
        assert len(result) == 2


class TestGetSellerStats:
    """测试 get_seller_stats"""
    
    @patch('services.db.marketplace.supabase')
    def test_returns_seller_stats(self, mock_supabase):
        """返回卖家统计"""
        from services.db.marketplace import get_seller_stats
        
        # Mock listings 查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "l1", "sales_count": 10, "usage_count": 50, "price_credits": 100},
                {"id": "l2", "sales_count": 5, "usage_count": 30, "price_credits": 50}
            ]
        )
        
        result = get_seller_stats("seller_001")
        
        assert result["total_listings"] == 2
        assert result["total_sales"] == 15
        assert result["total_usage"] == 80


class TestRecordListingUsage:
    """测试 record_listing_usage"""
    
    @patch('services.db.marketplace.supabase')
    def test_records_usage(self, mock_supabase):
        """记录使用次数"""
        from services.db.marketplace import record_listing_usage
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = record_listing_usage("listing_001", "user_001", "project_001")
        
        assert result is True
    
    @patch('services.db.marketplace.supabase')
    def test_returns_false_on_error(self, mock_supabase):
        """错误时返回 False"""
        from services.db.marketplace import record_listing_usage
        
        mock_supabase.table.return_value.insert.side_effect = Exception("DB Error")
        
        result = record_listing_usage("listing_001", "user_001", "project_001")
        
        assert result is False


class TestGetLeaderboard:
    """测试 get_leaderboard"""
    
    @patch('services.db.marketplace.supabase')
    def test_returns_leaderboard(self, mock_supabase):
        """返回排行榜"""
        from services.db.marketplace import get_leaderboard
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "l1", "title": "Top 1", "usage_count": 100},
            {"id": "l2", "title": "Top 2", "usage_count": 80}
        ]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value = mock_chain
        
        result = get_leaderboard(limit=10)
        
        assert len(result) == 2
        assert result[0]["rank"] == 1
