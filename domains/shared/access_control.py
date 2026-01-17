"""
Shared Domain - Access Control Rules.

Business rules for user permissions, tier-based access, and marketplace visibility.

@module domains.shared.access_control
@version 1.1.0

Changes in v1.1.0:
- Deprecated can_use_ocr() - use TierService.can_use_feature() instead
- AccessControl class now uses TierService for permission checks
- Added tier hierarchy for t4 (Enterprise)
"""

import warnings
from typing import Dict, List, Any, Optional


def is_member(user: Dict[str, Any]) -> bool:
    """
    Check if user is an active member (Starter/Pro/Enterprise).

    Business Rule: User must have t2/t3/t4 tier AND active/trialing subscription status.

    Args:
        user: User profile dict with tier and subscription_status

    Returns:
        True if user is active member
    """
    if not user:
        return False

    tier = user.get("tier", "t1")
    subscription_status = user.get("subscription_status", "inactive")

    if tier in ["t2", "t3", "t4"]:
        return subscription_status in ["active", "trialing"]

    return False


def can_access_resource(user: Dict[str, Any], allowed_tiers: List[str]) -> bool:
    """
    Check if user can access a resource based on tier.

    Business Rule:
    - "all" in allowed_tiers → everyone can access
    - User tier must be in allowed_tiers OR higher in hierarchy
    - Hierarchy: free(0) < starter(1) < pro(2) < enterprise(3)

    Args:
        user: User profile dict with tier
        allowed_tiers: List of allowed tiers (e.g., ["t2", "t3"])

    Returns:
        True if user can access resource
    """
    if not user or not allowed_tiers:
        return False

    user_tier = user.get("tier", "t1")

    # Check exact match or "all"
    if "all" in allowed_tiers or user_tier in allowed_tiers:
        return True

    # Check tier hierarchy
    tier_hierarchy = {"t1": 0, "t2": 1, "t3": 2, "t4": 3}
    user_level = tier_hierarchy.get(user_tier, 0)

    for allowed in allowed_tiers:
        if tier_hierarchy.get(allowed, 99) <= user_level:
            return True

    return False


def get_total_credits(user: Dict[str, Any]) -> int:
    """
    Get total credits (monthly + permanent).

    Args:
        user: User profile dict with credits_monthly and credits_permanent

    Returns:
        Total credits available
    """
    if not user:
        return 0

    return user.get("credits_monthly", 0) + user.get("credits_permanent", 0)


def publish_permission(user: Dict[str, Any], resource_type: str, price_credits: int) -> Dict[str, Any]:
    """
    Check if user can publish to marketplace.

    Business Rule:
    - User must be active member (Starter/Pro)
    - Price must be non-negative

    Args:
        user: User profile dict
        resource_type: Type of resource (project/asset)
        price_credits: Price in credits

    Returns:
        Dict with allowed (bool) and optional reason (str)
    """
    if not is_member(user):
        return {"allowed": False, "reason": "Membership required"}

    if price_credits < 0:
        return {"allowed": False, "reason": "Invalid price"}

    return {"allowed": True}


def validate_allowed_tiers(allowed_tiers: List[str]) -> Dict[str, Any]:
    """
    Validate tier list.

    Args:
        allowed_tiers: List of tier names

    Returns:
        Dict with valid (bool), tiers (list), and optional reason (str)
    """
    valid_tiers = ["t1", "t2", "t3", "t4", "all"]

    if not allowed_tiers:
        return {"valid": True, "tiers": ["all"]}

    invalid = [t for t in allowed_tiers if t not in valid_tiers]

    if invalid:
        return {"valid": False, "reason": f"Invalid tiers: {invalid}"}

    return {"valid": True, "tiers": allowed_tiers}


def listing_is_public_visible(listing: Dict[str, Any]) -> bool:
    """
    Check if marketplace listing is publicly visible.

    Business Rule: Listing must be:
    - is_public = True
    - is_deleted = False
    - moderation_status = "approved"

    Args:
        listing: Marketplace listing dict

    Returns:
        True if listing is publicly visible
    """
    if not listing:
        return False

    return (
        listing.get("is_public", False)
        and not listing.get("is_deleted", False)
        and listing.get("moderation_status") == "approved"
    )


class AccessControl:
    """
    Access control utility class for permission checks.

    This class provides static methods for checking user permissions
    based on tier and trial status.

    DEPRECATED: For new code, use TierService.can_use_feature() instead.
    This class is kept for backward compatibility.
    """

    @staticmethod
    def can_use_ocr(user: Dict[str, Any], is_trial: bool = False) -> bool:
        """
        Check if user can use OCR/Smart Scan feature.

        DEPRECATED: Use TierService.can_use_feature(tier, FeatureKey.AI_FEATURES, is_trial) instead.

        Business Rule: OCR is available to:
        - Pro/Enterprise tier users
        - Free tier users during trial period

        Args:
            user: User profile dict with tier information
            is_trial: Whether user is in trial period

        Returns:
            True if user can use OCR
        """
        warnings.warn(
            "AccessControl.can_use_ocr() is deprecated. "
            "Use TierService.can_use_feature() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        if not user:
            return False

        # UserProfile may be dict or object, handle both for backward compatibility
        if hasattr(user, 'tier'):
            tier = (user.tier.value if user.tier else "t1").lower()
        else:
            tier = (user.get("tier") or "t1").lower()

        # Pro/Enterprise users always have access
        if tier in ("t3", "t4"):
            return True

        # Free users can use during trial
        if tier == "t1" and is_trial:
            return True

        return False
