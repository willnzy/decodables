"""
Access Control Service Tests
访问控制服务测试

Coverage target: 90%+
"""

import pytest
from unittest.mock import patch


class TestIsMember:
    """Test AccessControl.is_member"""
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_starter_active_is_member(self):
        """Starter with active subscription is member"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "active"}
        assert AccessControl.is_member(user) is True
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_pro_active_is_member(self):
        """Pro with active subscription is member"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        assert AccessControl.is_member(user) is True
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_free_is_not_member(self):
        """Free user is not member"""
        from services.access_control import AccessControl
        
        user = {"tier": "free", "subscription_status": "active"}
        assert AccessControl.is_member(user) is False
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_inactive_subscription_not_member(self):
        """Inactive subscription is not member"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "inactive"}
        assert AccessControl.is_member(user) is False
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_missing_tier_defaults_free(self):
        """Missing tier defaults to free"""
        from services.access_control import AccessControl
        
        user = {"subscription_status": "active"}
        assert AccessControl.is_member(user) is False
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_missing_status_defaults_inactive(self):
        """Missing status defaults to inactive"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro"}
        assert AccessControl.is_member(user) is False


class TestCanAccessResource:
    """Test AccessControl.can_access_resource"""
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_no_restriction(self):
        """Empty allowed_tiers means no restriction"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        assert AccessControl.can_access_resource(user, []) is True
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_free_tier_allows_everyone(self):
        """'free' in allowed_tiers allows everyone"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        assert AccessControl.can_access_resource(user, ["free"]) is True
        
        user = {"tier": "pro", "subscription_status": "active"}
        assert AccessControl.can_access_resource(user, ["free"]) is True
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_requires_membership(self):
        """Requires membership when not 'free'"""
        from services.access_control import AccessControl
        
        free_user = {"tier": "free"}
        assert AccessControl.can_access_resource(free_user, ["starter", "pro"]) is False
        
        inactive_user = {"tier": "starter", "subscription_status": "inactive"}
        assert AccessControl.can_access_resource(inactive_user, ["starter", "pro"]) is False
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_member_with_matching_tier(self):
        """Member with matching tier can access"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "active"}
        assert AccessControl.can_access_resource(user, ["starter", "pro"]) is True
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_member_with_non_matching_tier(self):
        """Member with non-matching tier cannot access"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "active"}
        assert AccessControl.can_access_resource(user, ["pro"]) is False


class TestPublishPermission:
    """Test AccessControl.publish_permission"""
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    @patch('services.access_control.MAX_LISTING_PRICE', 500)
    def test_free_cannot_publish(self):
        """Free users cannot publish"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        allowed, reason = AccessControl.publish_permission(user, "asset", 0)
        
        assert allowed is False
        assert "Free users" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    @patch('services.access_control.MAX_LISTING_PRICE', 500)
    def test_inactive_member_cannot_publish(self):
        """Inactive members cannot publish"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "inactive"}
        allowed, reason = AccessControl.publish_permission(user, "asset", 0)
        
        assert allowed is False
        assert "Active membership" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    @patch('services.access_control.MAX_LISTING_PRICE', 500)
    def test_negative_price_invalid(self):
        """Negative price is invalid"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        allowed, reason = AccessControl.publish_permission(user, "asset", -10)
        
        assert allowed is False
        assert "between 0 and" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    @patch('services.access_control.MAX_LISTING_PRICE', 500)
    def test_exceeds_max_price(self):
        """Price exceeding max is invalid"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        allowed, reason = AccessControl.publish_permission(user, "asset", 1000)
        
        assert allowed is False
        assert "between 0 and" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    @patch('services.access_control.MAX_LISTING_PRICE', 500)
    def test_starter_can_only_publish_free_assets(self):
        """Starter can only publish free assets"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "active"}
        
        # Free asset: OK
        allowed, reason = AccessControl.publish_permission(user, "asset", 0)
        assert allowed is True
        
        # Paid asset: Not OK
        allowed, reason = AccessControl.publish_permission(user, "asset", 50)
        assert allowed is False
        assert "price must be 0" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    @patch('services.access_control.MAX_LISTING_PRICE', 500)
    def test_starter_cannot_publish_projects(self):
        """Starter cannot publish projects"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "active"}
        allowed, reason = AccessControl.publish_permission(user, "project", 0)
        
        assert allowed is False
        assert "only publish assets" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    @patch('services.access_control.MAX_LISTING_PRICE', 500)
    def test_pro_can_publish_anything(self):
        """Pro can publish any valid listing"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        
        # Free asset
        allowed, _ = AccessControl.publish_permission(user, "asset", 0)
        assert allowed is True
        
        # Paid asset
        allowed, _ = AccessControl.publish_permission(user, "asset", 100)
        assert allowed is True
        
        # Project
        allowed, _ = AccessControl.publish_permission(user, "project", 200)
        assert allowed is True


class TestValidateAllowedTiers:
    """Test AccessControl.validate_allowed_tiers"""
    
    @patch('services.access_control.ALLOWED_TIERS_WHITELIST', [['free'], ['starter', 'pro'], ['pro']])
    def test_empty_is_valid(self):
        """Empty list is valid (uses default)"""
        from services.access_control import AccessControl
        
        assert AccessControl.validate_allowed_tiers([]) is True
    
    @patch('services.access_control.ALLOWED_TIERS_WHITELIST', [['free'], ['starter', 'pro'], ['pro']])
    def test_free_is_valid(self):
        """['free'] is valid"""
        from services.access_control import AccessControl
        
        assert AccessControl.validate_allowed_tiers(["free"]) is True
    
    @patch('services.access_control.ALLOWED_TIERS_WHITELIST', [['free'], ['starter', 'pro'], ['pro']])
    def test_starter_pro_is_valid(self):
        """['starter', 'pro'] is valid"""
        from services.access_control import AccessControl
        
        assert AccessControl.validate_allowed_tiers(["starter", "pro"]) is True
        # Order shouldn't matter
        assert AccessControl.validate_allowed_tiers(["pro", "starter"]) is True
    
    @patch('services.access_control.ALLOWED_TIERS_WHITELIST', [['free'], ['starter', 'pro'], ['pro']])
    def test_pro_only_is_valid(self):
        """['pro'] is valid"""
        from services.access_control import AccessControl
        
        assert AccessControl.validate_allowed_tiers(["pro"]) is True
    
    @patch('services.access_control.ALLOWED_TIERS_WHITELIST', [['free'], ['starter', 'pro'], ['pro']])
    def test_invalid_combination(self):
        """Invalid combination returns False"""
        from services.access_control import AccessControl
        
        assert AccessControl.validate_allowed_tiers(["free", "pro"]) is False
        assert AccessControl.validate_allowed_tiers(["starter"]) is False
        assert AccessControl.validate_allowed_tiers(["enterprise"]) is False


class TestCanUseStickers:
    """Test AccessControl.can_use_stickers"""
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_member_can_use(self):
        """Members can use stickers"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter"}
        assert AccessControl.can_use_stickers(user) is True
        
        user = {"tier": "pro"}
        assert AccessControl.can_use_stickers(user) is True
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_free_cannot_use(self):
        """Free users cannot use stickers (no trial)"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        assert AccessControl.can_use_stickers(user) is False
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_free_can_use_during_trial(self):
        """Free users can use stickers during trial"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        assert AccessControl.can_use_stickers(user, is_trial=True) is True


class TestCanUseOcr:
    """Test AccessControl.can_use_ocr"""
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_pro_can_use(self):
        """Pro members can use OCR"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        assert AccessControl.can_use_ocr(user) is True
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_starter_cannot_use(self):
        """Starter members cannot use OCR"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "active"}
        assert AccessControl.can_use_ocr(user) is False
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_free_cannot_use(self):
        """Free users cannot use OCR (no trial)"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        assert AccessControl.can_use_ocr(user) is False
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_free_can_use_during_trial(self):
        """Free users can use OCR during trial"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        assert AccessControl.can_use_ocr(user, is_trial=True) is True
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_inactive_pro_cannot_use(self):
        """Inactive Pro cannot use OCR"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "inactive"}
        assert AccessControl.can_use_ocr(user) is False


class TestCanExportZip:
    """Test AccessControl.can_export_zip"""
    
    def test_pro_can_export(self):
        """Pro users can export ZIP"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro"}
        assert AccessControl.can_export_zip(user) is True
    
    def test_starter_cannot_export(self):
        """Starter users cannot export ZIP"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter"}
        assert AccessControl.can_export_zip(user) is False
    
    def test_free_cannot_export(self):
        """Free users cannot export ZIP"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        assert AccessControl.can_export_zip(user) is False


class TestCanPurchase:
    """Test AccessControl.can_purchase"""
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_not_approved_cannot_purchase(self):
        """Cannot purchase unapproved listing"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        listing = {"moderation_status": "pending", "is_public": True, "is_deleted": False}
        
        allowed, reason = AccessControl.can_purchase(user, listing)
        assert allowed is False
        assert "not approved" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_not_public_cannot_purchase(self):
        """Cannot purchase non-public listing"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        listing = {"moderation_status": "approved", "is_public": False, "is_deleted": False}
        
        allowed, reason = AccessControl.can_purchase(user, listing)
        assert allowed is False
        assert "not public" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_deleted_cannot_purchase(self):
        """Cannot purchase deleted listing"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        listing = {"moderation_status": "approved", "is_public": True, "is_deleted": True}
        
        allowed, reason = AccessControl.can_purchase(user, listing)
        assert allowed is False
        assert "deleted" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_tier_restriction(self):
        """Cannot purchase if tier not in allowed_tiers"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        listing = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False,
            "allowed_tiers": ["starter", "pro"],
            "resource_type": "asset"
        }
        
        allowed, reason = AccessControl.can_purchase(user, listing)
        assert allowed is False
        assert "membership" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_starter_cannot_purchase_projects(self):
        """Starter cannot purchase projects"""
        from services.access_control import AccessControl
        
        user = {"tier": "starter", "subscription_status": "active"}
        listing = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False,
            "allowed_tiers": ["starter", "pro"],
            "resource_type": "project"
        }
        
        allowed, reason = AccessControl.can_purchase(user, listing)
        assert allowed is False
        assert "Pro members" in reason
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_pro_can_purchase_projects(self):
        """Pro can purchase projects"""
        from services.access_control import AccessControl
        
        user = {"tier": "pro", "subscription_status": "active"}
        listing = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False,
            "allowed_tiers": ["free"],
            "resource_type": "project"
        }
        
        allowed, reason = AccessControl.can_purchase(user, listing)
        assert allowed is True
        assert reason is None
    
    @patch('services.access_control.MEMBER_TIERS', ['starter', 'pro'])
    def test_anyone_can_purchase_free_assets(self):
        """Anyone can purchase free-tier assets"""
        from services.access_control import AccessControl
        
        user = {"tier": "free"}
        listing = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False,
            "allowed_tiers": ["free"],
            "resource_type": "asset"
        }
        
        allowed, reason = AccessControl.can_purchase(user, listing)
        assert allowed is True
