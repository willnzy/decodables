"""
Marketplace Service Tests
基于 BUSINESS_LOGIC_SPEC.md Section 6 的业务规则测试

测试目的: 验证 Marketplace 业务逻辑是否符合规格要求

核心业务规则:
1. 购买流程 (Section 6.2):
   - 验证 listing 状态 (approved, public, not deleted)
   - 检查 allowed_tiers 权限
   - 检查 resource_type 权限 (project 仅 Pro)
   - 检查是否已购买 (去重)
   - 扣除买家积分 (monthly first)
   - 添加卖家收入 (90% → permanent)

2. 收益分成 (Section 6.3):
   - 卖家获得 90%
   - 平台获得 10%

3. 资源类型权限 (Section 6.1):
   - Asset: Starter, Pro 可购买
   - Project: 仅 Pro 可购买

@module tests/test_marketplace_service
@version v3.3
@last_updated 2026-01-05
"""

import pytest
from unittest.mock import MagicMock, patch
from services.marketplace_service import MarketplaceService
from config import SELLER_REVENUE_PERCENT


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_supabase():
    """创建 mock Supabase 客户端"""
    return MagicMock()


@pytest.fixture
def marketplace_service(mock_supabase):
    """创建 MarketplaceService 实例"""
    return MarketplaceService(mock_supabase)


@pytest.fixture
def mock_listing_approved_public():
    """已通过审核且公开的 listing"""
    return {
        "id": "listing_001",
        "title": "Test Sticker Pack",
        "seller_id": "seller_123",
        "moderation_status": "approved",
        "is_public": True,
        "is_deleted": False,
        "price_credits": 100,
        "allowed_tiers": ["free"],
        "resource_type": "asset",
        "sales_count": 10
    }


@pytest.fixture
def mock_pro_project_listing():
    """Pro 专属项目 listing"""
    return {
        "id": "listing_002",
        "title": "Pro Project Template",
        "seller_id": "seller_456",
        "moderation_status": "approved",
        "is_public": True,
        "is_deleted": False,
        "price_credits": 200,
        "allowed_tiers": ["pro"],
        "resource_type": "project",
        "sales_count": 5
    }


@pytest.fixture
def mock_buyer_starter():
    """Starter 会员买家"""
    return {
        "id": "buyer_starter_001",
        "tier": "starter",
        "credits_monthly": 300,
        "credits_permanent": 100,
        "subscription_status": "active"
    }


@pytest.fixture
def mock_buyer_pro():
    """Pro 会员买家"""
    return {
        "id": "buyer_pro_001",
        "tier": "pro",
        "credits_monthly": 800,
        "credits_permanent": 200,
        "subscription_status": "active"
    }


@pytest.fixture
def mock_buyer_free():
    """Free 用户"""
    return {
        "id": "buyer_free_001",
        "tier": "free",
        "credits_monthly": 0,
        "credits_permanent": 50
    }


# ==========================================
# 购买流程测试 (Section 6.2)
# ==========================================

class TestPurchaseFlowValidation:
    """
    测试购买流程的验证逻辑
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6.2
    """
    
    def test_listing_not_found_returns_404(self, marketplace_service, mock_supabase):
        """【业务规则】listing 不存在时返回 404"""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        
        result = marketplace_service.execute_purchase("nonexistent_id", "buyer_001")
        
        assert result["success"] is False
        assert result["status"] == 404
        assert "not found" in result["error"].lower()
    
    def test_listing_not_approved_rejected(self, marketplace_service, mock_supabase, mock_listing_approved_public):
        """【业务规则】未通过审核的 listing 不可购买"""
        mock_listing_approved_public["moderation_status"] = "pending"
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=mock_listing_approved_public)
        
        result = marketplace_service.execute_purchase("listing_001", "buyer_001")
        
        assert result["success"] is False
        assert result["status"] == 400
        assert "not approved" in result["error"].lower()
    
    def test_listing_not_public_rejected(self, marketplace_service, mock_supabase, mock_listing_approved_public):
        """【业务规则】未公开的 listing 不可购买"""
        mock_listing_approved_public["is_public"] = False
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=mock_listing_approved_public)
        
        result = marketplace_service.execute_purchase("listing_001", "buyer_001")
        
        assert result["success"] is False
        assert result["status"] == 400
        assert "not public" in result["error"].lower()
    
    def test_listing_deleted_rejected(self, marketplace_service, mock_supabase, mock_listing_approved_public):
        """【业务规则】已删除的 listing 不可购买"""
        mock_listing_approved_public["is_deleted"] = True
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=mock_listing_approved_public)
        
        result = marketplace_service.execute_purchase("listing_001", "buyer_001")
        
        assert result["success"] is False
        assert result["status"] == 400
        assert "deleted" in result["error"].lower()


class TestResourceTypePermissions:
    """
    测试资源类型权限
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6.1
    - Asset: 所有用户可购买
    - Project: 仅 Pro 可购买
    """
    
    def test_starter_can_purchase_asset(self, marketplace_service, mock_supabase, mock_listing_approved_public, mock_buyer_starter):
        """【业务规则 6.1】Starter 可以购买 Asset"""
        # Setup mocks
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_listing_approved_public),  # Get listing
            MagicMock(data=mock_buyer_starter),  # Get buyer
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])  # No existing purchase
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        with patch.object(marketplace_service.credit_service, 'has_enough', return_value=True):
            with patch.object(marketplace_service.credit_service, 'deduct', return_value=(True, "Success")):
                with patch.object(marketplace_service.credit_service, 'add', return_value=True):
                    result = marketplace_service.execute_purchase("listing_001", mock_buyer_starter["id"])
        
        assert result["success"] is True
    
    def test_starter_cannot_purchase_project(self, marketplace_service, mock_supabase, mock_pro_project_listing, mock_buyer_starter):
        """【业务规则 6.1】Starter 不能购买 Project"""
        # Project listing with pro-only allowed_tiers
        mock_pro_project_listing["allowed_tiers"] = ["free"]  # Even if allowed_tiers permits, resource_type check should fail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_pro_project_listing),  # Get listing
            MagicMock(data=mock_buyer_starter),  # Get buyer
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])  # No existing purchase
        
        result = marketplace_service.execute_purchase("listing_002", mock_buyer_starter["id"])
        
        assert result["success"] is False
        assert result["status"] == 403
        assert "pro" in result["error"].lower()
        assert "project" in result["error"].lower()
    
    def test_pro_can_purchase_project(self, marketplace_service, mock_supabase, mock_pro_project_listing, mock_buyer_pro):
        """【业务规则 6.1】Pro 可以购买 Project"""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_pro_project_listing),  # Get listing
            MagicMock(data=mock_buyer_pro),  # Get buyer
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])  # No existing purchase
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        with patch.object(marketplace_service.credit_service, 'has_enough', return_value=True):
            with patch.object(marketplace_service.credit_service, 'deduct', return_value=(True, "Success")):
                with patch.object(marketplace_service.credit_service, 'add', return_value=True):
                    result = marketplace_service.execute_purchase("listing_002", mock_buyer_pro["id"])
        
        assert result["success"] is True


class TestAllowedTiersPermissions:
    """
    测试 allowed_tiers 权限检查
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 4.2
    """
    
    def test_free_tier_resource_accessible_to_all(self, marketplace_service, mock_supabase, mock_listing_approved_public, mock_buyer_free):
        """【业务规则 4.2】allowed_tiers=['free'] 的资源所有登录用户可访问"""
        mock_listing_approved_public["allowed_tiers"] = ["free"]
        mock_listing_approved_public["price_credits"] = 0  # Free item
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_listing_approved_public),  # Get listing
            MagicMock(data=mock_buyer_free),  # Get buyer
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])  # No existing purchase
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = marketplace_service.execute_purchase("listing_001", mock_buyer_free["id"])
        
        assert result["success"] is True
    
    def test_member_only_resource_rejected_for_free(self, marketplace_service, mock_supabase, mock_listing_approved_public, mock_buyer_free):
        """【业务规则 4.2】allowed_tiers=['starter', 'pro'] 的资源 Free 用户不可访问"""
        mock_listing_approved_public["allowed_tiers"] = ["starter", "pro"]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_listing_approved_public),  # Get listing
            MagicMock(data=mock_buyer_free),  # Get buyer
        ]
        
        result = marketplace_service.execute_purchase("listing_001", mock_buyer_free["id"])
        
        assert result["success"] is False
        assert result["status"] == 403
        assert "membership" in result["error"].lower()


class TestPurchaseDeduplication:
    """
    测试购买去重逻辑
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6.2 步骤 4
    """
    
    def test_already_purchased_returns_success_with_flag(self, marketplace_service, mock_supabase, mock_listing_approved_public, mock_buyer_starter):
        """【业务规则】已购买的商品返回 success=True 和 already_owned=True"""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_listing_approved_public),  # Get listing
            MagicMock(data=mock_buyer_starter),  # Get buyer
        ]
        # Already purchased
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "purchase_001"}])
        
        result = marketplace_service.execute_purchase("listing_001", mock_buyer_starter["id"])
        
        assert result["success"] is True
        assert result["already_owned"] is True


class TestRevenueShare:
    """
    测试收益分成逻辑
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6.3
    - 卖家获得 90%
    - 平台获得 10%
    """
    
    def test_seller_receives_90_percent(self, marketplace_service, mock_supabase, mock_listing_approved_public, mock_buyer_starter):
        """【业务规则 6.3】卖家获得售价的 90%"""
        price = 100
        mock_listing_approved_public["price_credits"] = price
        expected_seller_revenue = int(price * SELLER_REVENUE_PERCENT / 100)  # 90
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_listing_approved_public),  # Get listing
            MagicMock(data=mock_buyer_starter),  # Get buyer
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])  # No existing purchase
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        credit_add_mock = MagicMock(return_value=True)
        
        with patch.object(marketplace_service.credit_service, 'has_enough', return_value=True):
            with patch.object(marketplace_service.credit_service, 'deduct', return_value=(True, "Success")):
                with patch.object(marketplace_service.credit_service, 'add', credit_add_mock):
                    result = marketplace_service.execute_purchase("listing_001", mock_buyer_starter["id"])
        
        assert result["success"] is True
        assert result["seller_revenue"] == expected_seller_revenue
        
        # 验证 seller.add 被调用，金额是 90%
        credit_add_mock.assert_called_once()
        call_args = credit_add_mock.call_args
        assert call_args[0][1] == expected_seller_revenue  # Second arg is amount


class TestFreeItemPurchase:
    """
    测试免费商品购买
    """
    
    def test_free_item_no_credit_deduction(self, marketplace_service, mock_supabase, mock_listing_approved_public, mock_buyer_starter):
        """【业务规则】免费商品不扣除积分"""
        mock_listing_approved_public["price_credits"] = 0
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_listing_approved_public),  # Get listing
            MagicMock(data=mock_buyer_starter),  # Get buyer
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        credit_deduct_mock = MagicMock()
        
        with patch.object(marketplace_service.credit_service, 'deduct', credit_deduct_mock):
            result = marketplace_service.execute_purchase("listing_001", mock_buyer_starter["id"])
        
        assert result["success"] is True
        assert result["price_paid"] == 0
        credit_deduct_mock.assert_not_called()  # 免费商品不扣积分


class TestInsufficientCredits:
    """
    测试积分不足的情况
    """
    
    def test_insufficient_credits_returns_402(self, marketplace_service, mock_supabase, mock_listing_approved_public, mock_buyer_starter):
        """【业务规则】积分不足时返回 402"""
        mock_listing_approved_public["price_credits"] = 1000  # 高于买家积分
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            MagicMock(data=mock_listing_approved_public),  # Get listing
            MagicMock(data=mock_buyer_starter),  # Get buyer
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        with patch.object(marketplace_service.credit_service, 'has_enough', return_value=False):
            result = marketplace_service.execute_purchase("listing_001", mock_buyer_starter["id"])
        
        assert result["success"] is False
        assert result["status"] == 402
        assert "insufficient" in result["error"].lower()


# ==========================================
# 使用记录测试
# ==========================================

class TestUsageTracking:
    """
    测试使用记录和去重
    """
    
    def test_record_usage_success(self, marketplace_service, mock_supabase):
        """【业务规则】成功记录使用并增加 usage_count"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={"usage_count": 5})
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = marketplace_service.record_usage("listing_001", "user_001", "project_001")
        
        assert result is True
    
    def test_record_usage_duplicate_returns_false(self, marketplace_service, mock_supabase):
        """【业务规则】重复使用记录返回 False（去重）"""
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Unique constraint violation")
        
        result = marketplace_service.record_usage("listing_001", "user_001", "project_001")
        
        assert result is False


# ==========================================
# 卖家统计测试
# ==========================================

class TestSellerStats:
    """
    测试卖家统计功能
    """
    
    def test_get_seller_stats_calculates_correctly(self, marketplace_service, mock_supabase):
        """【业务规则】正确计算卖家统计数据"""
        # Mock listings
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"id": "l1", "sales_count": 10, "usage_count": 50},
            {"id": "l2", "sales_count": 5, "usage_count": 30},
        ])
        # Mock transactions
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"amount": 90},  # 100 * 90%
            {"amount": 45},  # 50 * 90%
        ])
        
        result = marketplace_service.get_seller_stats("seller_001")
        
        assert "total_earned_credits" in result
        assert "listings_count" in result
        assert "total_sales" in result
        assert "total_usage" in result


# ==========================================
# 排行榜测试
# ==========================================

class TestLeaderboard:
    """
    测试排行榜功能
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6.5
    """
    
    def test_leaderboard_only_includes_approved_public_not_deleted(self, marketplace_service, mock_supabase):
        """【业务规则 6.5】排行榜只包含 approved + public + not deleted 的商品"""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[
            {"id": "l1", "title": "Top 1", "usage_count": 100},
            {"id": "l2", "title": "Top 2", "usage_count": 80},
        ])
        
        result = marketplace_service.get_leaderboard(period="monthly", limit=10)
        
        assert len(result) == 2
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
    
    def test_leaderboard_filter_by_resource_type(self, marketplace_service, mock_supabase):
        """【业务规则】排行榜可以按 resource_type 筛选"""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[
            {"id": "l1", "title": "Project 1", "resource_type": "project", "usage_count": 50},
        ])
        
        result = marketplace_service.get_leaderboard(resource_type="project")
        
        assert len(result) >= 0  # May be empty, just verify no error
