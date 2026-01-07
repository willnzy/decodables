"""
Database Utilities - Business logic helpers.

@module services.db.utils
@version 3.24
"""

import logging
from core.database import supabase

logger = logging.getLogger(__name__)


# ==========================================
# Permission Helpers
# ==========================================

def is_member(user: dict) -> bool:
    """Check if user is an active member (Starter/Pro)."""
    if not user:
        return False
    tier = user.get("tier", "free")
    subscription_status = user.get("subscription_status", "inactive")
    if tier in ["starter", "pro"]:
        return subscription_status in ["active", "trialing"]
    return False


def can_access_resource(user: dict, allowed_tiers: list) -> bool:
    """Check if user can access a resource based on tier."""
    if not user or not allowed_tiers:
        return False
    user_tier = user.get("tier", "free")
    if "all" in allowed_tiers or user_tier in allowed_tiers:
        return True
    tier_hierarchy = {"free": 0, "starter": 1, "pro": 2}
    user_level = tier_hierarchy.get(user_tier, 0)
    for allowed in allowed_tiers:
        if tier_hierarchy.get(allowed, 99) <= user_level:
            return True
    return False


def get_total_credits(user: dict) -> int:
    """Get total credits (monthly + permanent)."""
    if not user:
        return 0
    return user.get("credits_monthly", 0) + user.get("credits_permanent", 0)


def publish_permission(user: dict, resource_type: str, price_credits: int) -> dict:
    """Check if user can publish to marketplace."""
    if not is_member(user):
        return {"allowed": False, "reason": "Membership required"}
    if price_credits < 0:
        return {"allowed": False, "reason": "Invalid price"}
    return {"allowed": True}


def validate_allowed_tiers(allowed_tiers: list) -> dict:
    """Validate tier list."""
    valid_tiers = ["free", "starter", "pro", "all"]
    if not allowed_tiers:
        return {"valid": True, "tiers": ["all"]}
    invalid = [t for t in allowed_tiers if t not in valid_tiers]
    if invalid:
        return {"valid": False, "reason": f"Invalid tiers: {invalid}"}
    return {"valid": True, "tiers": allowed_tiers}


def listing_is_public_visible(listing: dict) -> bool:
    """Check if listing is publicly visible."""
    if not listing:
        return False
    return (
        listing.get("is_public", False)
        and not listing.get("is_deleted", False)
        and listing.get("moderation_status") == "approved"
    )


# ==========================================
# Activity Logging
# ==========================================

def log_activity(user_id: str, action: str, metadata: dict = None):
    """Log user activity."""
    if not supabase:
        return
    try:
        supabase.table("activity_logs").insert({
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {}
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log activity: {e}")
