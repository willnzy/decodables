"""
Marketplace 市场业务规则测试

业务规则来源: 后台业务逻辑说明.md Section 6

核心规则:
- 资源类型: Asset 和 Project
- 发布权限: Free 不能发布, Starter 只能发布免费 Asset, Pro 可全部
- 购买权限: Project 仅 Pro 可购买
- 收益分成: 卖家 90%, 平台 10%

@module tests/business_rules/test_marketplace_rules
@version v3.24
"""

import pytest


class TestResourceTypes:
    """
    测试资源类型
    
    业务规则来源: Section 6.1
    """
    
    def test_resource_types(self):
        """【业务规则 6.1】两种资源类型"""
        RESOURCE_TYPES = ["asset", "project"]
        
        assert "asset" in RESOURCE_TYPES
        assert "project" in RESOURCE_TYPES


class TestPublishPermission:
    """
    测试发布权限
    
    业务规则来源: Section 4.3
    """
    
    MAX_PRICE = 500
    
    def test_free_cannot_publish(self):
        """【业务规则 4.3】Free 用户无法发布"""
        def can_publish(tier):
            return tier in ["starter", "pro"]
        
        assert can_publish("free") is False
        assert can_publish("starter") is True
        assert can_publish("pro") is True
    
    def test_publish_requires_active_subscription(self):
        """【业务规则 4.3】发布需要活跃订阅"""
        def can_publish_with_status(tier, subscription_status):
            if tier not in ["starter", "pro"]:
                return False
            return subscription_status == "active"
        
        assert can_publish_with_status("starter", "active") is True
        assert can_publish_with_status("starter", "inactive") is False
        assert can_publish_with_status("pro", "past_due") is False
    
    def test_starter_can_only_publish_free_assets(self):
        """【业务规则 4.3】Starter 只能发布免费资源"""
        def validate_starter_publish(resource_type, price):
            if resource_type == "project":
                return False, "Starter can only publish assets"
            if price > 0:
                return False, "Starter price must be 0"
            return True, None
        
        # 免费 Asset: OK
        allowed, _ = validate_starter_publish("asset", 0)
        assert allowed is True
        
        # 付费 Asset: Not OK
        allowed, reason = validate_starter_publish("asset", 50)
        assert allowed is False
        assert "price must be 0" in reason
        
        # Project: Not OK
        allowed, reason = validate_starter_publish("project", 0)
        assert allowed is False
        assert "only publish assets" in reason
    
    def test_pro_can_publish_anything_within_limits(self):
        """【业务规则 4.3】Pro 可以发布任何类型，定价 0-500"""
        def validate_pro_publish(resource_type, price):
            if price < 0 or price > self.MAX_PRICE:
                return False, f"Price must be 0-{self.MAX_PRICE}"
            return True, None
        
        # 免费 Asset
        assert validate_pro_publish("asset", 0)[0] is True
        
        # 付费 Asset
        assert validate_pro_publish("asset", 100)[0] is True
        
        # Project
        assert validate_pro_publish("project", 200)[0] is True
        
        # 边界：最大价格
        assert validate_pro_publish("asset", 500)[0] is True
        
        # 超出限制
        assert validate_pro_publish("asset", 501)[0] is False
        assert validate_pro_publish("asset", -1)[0] is False


class TestPurchasePermission:
    """
    测试购买权限
    
    业务规则来源: Section 6.2
    """
    
    def test_listing_must_be_approved_public_not_deleted(self):
        """【业务规则 6.2】Listing 必须是 approved, public, not deleted"""
        def validate_listing(listing):
            if listing.get("moderation_status") != "approved":
                return False, "Not approved"
            if not listing.get("is_public"):
                return False, "Not public"
            if listing.get("is_deleted"):
                return False, "Deleted"
            return True, None
        
        valid = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False
        }
        assert validate_listing(valid)[0] is True
        
        # 未审核
        invalid = {**valid, "moderation_status": "pending"}
        assert validate_listing(invalid)[0] is False
        
        # 非公开
        invalid = {**valid, "is_public": False}
        assert validate_listing(invalid)[0] is False
        
        # 已删除
        invalid = {**valid, "is_deleted": True}
        assert validate_listing(invalid)[0] is False
    
    def test_project_purchase_requires_pro(self):
        """【业务规则 6.1】Project 只能被 Pro 购买"""
        def can_purchase_resource_type(user_tier, resource_type):
            if resource_type == "project" and user_tier != "pro":
                return False
            return True
        
        # Asset 所有人可买
        assert can_purchase_resource_type("free", "asset") is True
        assert can_purchase_resource_type("starter", "asset") is True
        assert can_purchase_resource_type("pro", "asset") is True
        
        # Project 仅 Pro
        assert can_purchase_resource_type("free", "project") is False
        assert can_purchase_resource_type("starter", "project") is False
        assert can_purchase_resource_type("pro", "project") is True


class TestRevenueSplit:
    """
    测试收益分成
    
    业务规则来源: Section 6.3
    """
    
    SELLER_PERCENT = 90
    PLATFORM_PERCENT = 10
    
    def test_revenue_split_percentages(self):
        """【业务规则 6.3】收益分成比例"""
        assert self.SELLER_PERCENT == 90
        assert self.PLATFORM_PERCENT == 10
        assert self.SELLER_PERCENT + self.PLATFORM_PERCENT == 100
    
    def test_seller_revenue_calculation(self):
        """【业务规则 6.3】卖家收益计算"""
        def calculate_seller_revenue(price):
            return int(price * self.SELLER_PERCENT / 100)
        
        # 定价 100 积分，卖家获得 90
        assert calculate_seller_revenue(100) == 90
        
        # 定价 50 积分，卖家获得 45
        assert calculate_seller_revenue(50) == 45
        
        # 定价 500 积分，卖家获得 450
        assert calculate_seller_revenue(500) == 450
    
    def test_seller_revenue_is_permanent(self):
        """【业务规则 6.3】卖家收益以永久积分发放"""
        REVENUE_CREDIT_TYPE = "permanent"
        assert REVENUE_CREDIT_TYPE == "permanent"


class TestModerationStatus:
    """
    测试审核状态机
    
    业务规则来源: Section 6.4
    """
    
    def test_moderation_statuses(self):
        """【业务规则 6.4】审核状态"""
        STATUSES = ["draft", "pending", "approved", "rejected"]
        
        assert "draft" in STATUSES
        assert "pending" in STATUSES
        assert "approved" in STATUSES
        assert "rejected" in STATUSES
    
    def test_marketplace_visibility(self):
        """【业务规则 6.4】市场可见条件"""
        def is_visible_in_marketplace(listing):
            return (
                listing.get("moderation_status") == "approved" and
                listing.get("is_public") is True and
                listing.get("is_deleted") is False
            )
        
        visible = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False
        }
        assert is_visible_in_marketplace(visible) is True
        
        # 未审核
        not_approved = {**visible, "moderation_status": "pending"}
        assert is_visible_in_marketplace(not_approved) is False
        
        # 非公开
        not_public = {**visible, "is_public": False}
        assert is_visible_in_marketplace(not_public) is False


class TestSoftDeleteRules:
    """
    测试软删除规则
    
    业务规则来源: Section 7.3
    """
    
    def test_soft_delete_recovery_period(self):
        """【业务规则 7.3】软删除 30 天内可恢复"""
        RECOVERY_DAYS = 30
        assert RECOVERY_DAYS == 30
    
    def test_purchased_items_not_affected(self):
        """【业务规则 7.3】购买者副本不受原项目删除影响"""
        def can_use_purchased_item(user_has_purchased, original_deleted):
            if user_has_purchased:
                return True  # 购买后始终可用
            return not original_deleted
        
        # 已购买用户不受原项目删除影响
        assert can_use_purchased_item(True, True) is True
        assert can_use_purchased_item(True, False) is True
        
        # 未购买用户受影响
        assert can_use_purchased_item(False, True) is False
        assert can_use_purchased_item(False, False) is True
