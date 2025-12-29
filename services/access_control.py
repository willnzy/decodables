"""
Access Control Service
Handles permission and access validation

@module services/access_control
"""

from typing import List, Tuple, Optional
from config import MEMBER_TIERS, ALLOWED_TIERS_WHITELIST, MAX_LISTING_PRICE


class AccessControl:
    """
    Service for managing access control.
    
    Key rules (PRD v3.2):
    - Only Starter/Pro are "members"
    - Free users have limited access
    - Resources are gated by allowed_tiers
    - Publishing requires membership with tier-specific restrictions
    """
    
    @staticmethod
    def is_member(user: dict) -> bool:
        """
        Check if user is a member (Starter/Pro with active subscription).
        
        Args:
            user: User profile dict
        
        Returns:
            True if user is an active member
        """
        tier = user.get("tier", "free")
        status = user.get("subscription_status", "inactive")
        return tier in MEMBER_TIERS and status == "active"
    
    @staticmethod
    def can_access_resource(user: dict, allowed_tiers: List[str]) -> bool:
        """
        Check if user can access a resource based on allowed_tiers.
        
        Rules:
        - If 'free' in allowed_tiers: any logged-in user can access
        - Otherwise: must be member AND user.tier in allowed_tiers
        
        Args:
            user: User profile dict
            allowed_tiers: List of allowed tiers (e.g., ['free'], ['starter','pro'], ['pro'])
        
        Returns:
            True if user can access the resource
        """
        if not allowed_tiers:
            return True  # No restriction
        
        if "free" in allowed_tiers:
            return True  # Available to everyone
        
        # Need to be a member with matching tier
        if not AccessControl.is_member(user):
            return False
        
        user_tier = user.get("tier", "free")
        return user_tier in allowed_tiers
    
    @staticmethod
    def publish_permission(
        user: dict, 
        resource_type: str, 
        price_credits: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user can publish content.
        
        Rules (PRD v3.2):
        - Must be active member (Starter/Pro with subscription_status='active')
        - Free: Cannot publish anything
        - Starter: Only free assets (resource_type='asset', price_credits=0)
        - Pro: Any assets or templates (0-500 credits)
        
        Args:
            user: User profile dict
            resource_type: 'template' or 'asset'
            price_credits: Price in credits
        
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        tier = user.get("tier", "free")
        
        # Free users cannot publish
        if tier == "free":
            return (False, "Free users cannot publish to marketplace")
        
        # Must be active member (PRD requirement)
        if not AccessControl.is_member(user):
            return (False, "Active membership required to publish")
        
        # Validate price
        if price_credits < 0 or price_credits > MAX_LISTING_PRICE:
            return (False, f"Price must be between 0 and {MAX_LISTING_PRICE} credits")
        
        # Starter restrictions
        if tier == "starter":
            if resource_type != "asset":
                return (False, "Starter members can only publish assets, not templates")
            if price_credits != 0:
                return (False, "Starter members can only publish free assets (price must be 0)")
        
        # Pro can do anything within limits
        return (True, None)
    
    @staticmethod
    def validate_allowed_tiers(allowed_tiers: List[str]) -> bool:
        """
        Validate allowed_tiers against whitelist.
        
        Valid options:
        - ['free']
        - ['starter', 'pro']
        - ['pro']
        
        Args:
            allowed_tiers: List to validate
        
        Returns:
            True if valid
        """
        if not allowed_tiers:
            return True  # Will use default
        
        # Sort for comparison
        sorted_tiers = sorted(allowed_tiers)
        
        for valid_option in ALLOWED_TIERS_WHITELIST:
            if sorted(valid_option) == sorted_tiers:
                return True
        
        return False
    
    @staticmethod
    def can_use_stickers(user: dict, is_trial: bool = False) -> bool:
        """
        Check if user can use sticker library.
        
        Rules:
        - Free: Trial only
        - Starter/Pro: Yes
        
        Args:
            user: User profile dict
            is_trial: Whether user is in trial period
        
        Returns:
            True if can use stickers
        """
        tier = user.get("tier", "free")
        if tier in MEMBER_TIERS:
            return True
        return is_trial
    
    @staticmethod
    def can_use_ocr(user: dict, is_trial: bool = False) -> bool:
        """
        Check if user can use OCR/Smart Scan.
        
        Rules (PRD v3.2):
        - Pro: Yes (5 Credits/次)
        - Free: Trial only
        - Starter: No (not included in Starter plan)
        
        Args:
            user: User profile dict
            is_trial: Whether user is in trial period
        
        Returns:
            True if can use OCR
        """
        tier = user.get("tier", "free")
        
        # Pro members always have access
        if tier == "pro" and AccessControl.is_member(user):
            return True
        
        # Free users during trial period only
        if tier == "free" and is_trial:
            return True
        
        # Starter users do NOT have OCR access (PRD: ❌)
        return False
    
    @staticmethod
    def can_export_zip(user: dict) -> bool:
        """
        Check if user can export ZIP (PRD v3.2).
        
        Rules: Pro only (Starter can only export PDF)
        
        Args:
            user: User profile dict
        
        Returns:
            True if can export ZIP
        """
        tier = user.get("tier", "free")
        return tier == "pro"
    
    @staticmethod
    def can_purchase(user: dict, listing: dict) -> Tuple[bool, Optional[str]]:
        """
        Check if user can purchase a listing.
        
        Validates:
        - Listing is approved, public, not deleted
        - User has access based on allowed_tiers
        - PRD v3.2: Starter can only purchase Assets, Pro can purchase Assets + Templates
        
        Args:
            user: User profile dict
            listing: Listing dict
        
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        # Check listing status
        if listing.get("moderation_status") != "approved":
            return (False, "Listing is not approved")
        if not listing.get("is_public", False):
            return (False, "Listing is not public")
        if listing.get("is_deleted", False):
            return (False, "Listing has been deleted")
        
        # Check tier access for allowed_tiers
        allowed_tiers = listing.get("allowed_tiers", ["free"])
        if not AccessControl.can_access_resource(user, allowed_tiers):
            return (False, f"Requires {'/'.join(allowed_tiers)} membership")
        
        # PRD v3.2: Starter can only purchase Assets, Pro can purchase Assets + Templates
        resource_type = listing.get("resource_type", "asset")
        user_tier = user.get("tier", "free")
        if resource_type == "template" and user_tier != "pro":
            return (False, "Only Pro members can purchase templates. Upgrade to Pro to access templates.")
        
        return (True, None)

