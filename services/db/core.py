"""
Database Core - Supabase client and common utilities

@module services.db.core
@version 3.24
"""

import os
import time
import logging
from functools import wraps
from supabase import create_client, Client
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ==========================================
# Supabase Configuration
# ==========================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL = SUPABASE_URL + '/'

# ==========================================
# Network Retry Configuration
# ==========================================

MAX_RETRIES = 3
RETRY_DELAY = 0.5
RETRY_BACKOFF = 2

RETRYABLE_ERRORS = [
    'resource temporarily unavailable',
    'connection reset',
    'connection refused',
    'timeout',
    'timed out',
    'network is unreachable',
    'name or service not known',
    'temporary failure in name resolution',
    'ssl: certificate_verify_failed',
    'readtimeout',
    'connecttimeout',
]


def is_retryable_error(error: Exception) -> bool:
    """Check if error is retryable (network-related)"""
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in RETRYABLE_ERRORS)


def retry_on_network_error(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY, backoff: float = RETRY_BACKOFF):
    """Decorator for automatic retry on network errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if not is_retryable_error(e):
                        raise e
                    if attempt >= max_retries:
                        logger.error(f"[DB] {func.__name__} failed after {max_retries + 1} attempts: {e}")
                        raise e
                    logger.warning(f"[DB] {func.__name__} retry {attempt + 1}/{max_retries + 1}: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            raise last_error
        return wrapper
    return decorator


# ==========================================
# Supabase Client
# ==========================================

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

if supabase:
    logger.info("[DB] Supabase client initialized")
else:
    logger.warning("[DB] Supabase not initialized - missing URL or KEY")


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
