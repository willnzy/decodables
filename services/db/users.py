"""
Database Users - User profile and credit operations

@module services.db.users
@version 3.24
"""

import logging
import random
import string
from datetime import datetime, timezone, timedelta

from .core import supabase, retry_on_network_error

logger = logging.getLogger(__name__)


# ==========================================
# User Profile
# ==========================================

@retry_on_network_error()
def get_user_profile(user_id: str):
    """Get user profile by ID."""
    if not supabase or not user_id:
        return None
    result = supabase.table("profiles").select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else None


def generate_user_code() -> str:
    """Generate unique 6-char user code."""
    chars = string.ascii_uppercase + string.digits
    for _ in range(10):
        code = ''.join(random.choices(chars, k=6))
        existing = supabase.table("profiles").select("id").eq("user_code", code).execute()
        if not existing.data:
            return code
    return ''.join(random.choices(chars, k=8))


@retry_on_network_error()
def create_user_profile(user_id: str, email: str, username: str, avatar_url: str, 
                        first_name: str = None, last_name: str = None, timezone: str = "UTC"):
    """Create new user profile."""
    if not supabase:
        return None
    
    user_code = generate_user_code()
    
    data = {
        "id": user_id,
        "email": email,
        "username": username,
        "avatar_url": avatar_url,
        "first_name": first_name,
        "last_name": last_name,
        "tier": "free",
        "credits_monthly": 0,
        "credits_permanent": 50,
        "user_code": user_code,
        "timezone": timezone,
    }
    
    result = supabase.table("profiles").insert(data).execute()
    
    if result.data:
        log_credit_transaction(user_id, 50, "permanent", "signup_bonus", "Welcome bonus", timezone)
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def update_subscription_tier(user_id: str, tier: str, stripe_customer_id: str = None, 
                             subscription_status: str = "active"):
    """Update user subscription tier."""
    if not supabase:
        return None
    
    update_data = {"tier": tier, "subscription_status": subscription_status}
    if stripe_customer_id:
        update_data["stripe_customer_id"] = stripe_customer_id
    
    result = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
    return result.data[0] if result.data else None


@retry_on_network_error()
def update_user_profile(user_id: str, avatar_url: str = None, username: str = None,
                        first_name: str = None, last_name: str = None, timezone_val: str = None):
    """Update user profile fields."""
    if not supabase:
        return None
    
    update_data = {}
    if avatar_url is not None:
        update_data["avatar_url"] = avatar_url
    if username is not None:
        update_data["username"] = username
    if first_name is not None:
        update_data["first_name"] = first_name
    if last_name is not None:
        update_data["last_name"] = last_name
    if timezone_val is not None:
        update_data["timezone"] = timezone_val
    
    if not update_data:
        return None
    
    result = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
    return result.data[0] if result.data else None


@retry_on_network_error()
def update_user_timezone(user_id: str, tz: str):
    """Update user timezone."""
    if not supabase:
        return None
    result = supabase.table("profiles").update({"timezone": tz}).eq("id", user_id).execute()
    return result.data[0] if result.data else None


def get_user_timezone(user_id: str) -> str:
    """Get user timezone, default to UTC."""
    if not supabase or not user_id:
        return "UTC"
    try:
        result = supabase.table("profiles").select("timezone").eq("id", user_id).execute()
        if result.data:
            return result.data[0].get("timezone") or "UTC"
    except:
        pass
    return "UTC"


# ==========================================
# Credits Management
# ==========================================

def log_credit_transaction(user_id: str, amount: int, bucket: str, type: str, 
                           description: str, tz: str = "UTC"):
    """Log credit transaction."""
    if not supabase:
        return
    try:
        supabase.table("credit_transactions").insert({
            "user_id": user_id,
            "amount": amount,
            "bucket": bucket,
            "type": type,
            "description": description,
            "timezone": tz,
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log credit transaction: {e}")


@retry_on_network_error()
def credit_deduct(user_id: str, amount: int, type: str, description: str, tz: str = "UTC") -> dict:
    """Deduct credits using atomic RPC function."""
    if not supabase:
        return {"success": False, "error": "Database not available"}
    
    try:
        result = supabase.rpc("deduct_credits_atomic", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_type": type,
            "p_description": description,
            "p_timezone": tz
        }).execute()
        
        if result.data:
            return {
                "success": True,
                "balance_monthly": result.data.get("balance_monthly", 0),
                "balance_permanent": result.data.get("balance_permanent", 0),
                "total": result.data.get("total_balance", 0),
                "deducted_from": result.data.get("deducted_from", "unknown")
            }
        return {"success": False, "error": "RPC returned no data"}
    except Exception as e:
        error_str = str(e)
        if "INSUFFICIENT" in error_str:
            return {"success": False, "error": "INSUFFICIENT_CREDITS"}
        logger.error(f"credit_deduct failed: {e}")
        return {"success": False, "error": error_str}


@retry_on_network_error()
def add_credits_permanent(user_id: str, amount: int, description: str, 
                          type: str = "topup_purchase", tz: str = "UTC"):
    """Add permanent credits."""
    if not supabase:
        return None
    
    try:
        result = supabase.rpc("add_credits_atomic", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_bucket": "permanent",
            "p_type": type,
            "p_description": description,
            "p_timezone": tz
        }).execute()
        return result.data if result.data else None
    except Exception as e:
        logger.error(f"add_credits_permanent failed: {e}")
        return None


@retry_on_network_error()
def add_credits_monthly(user_id: str, amount: int, description: str,
                        type: str = "sub_grant", tz: str = "UTC"):
    """Add monthly credits."""
    if not supabase:
        return None
    
    try:
        result = supabase.rpc("add_credits_atomic", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_bucket": "monthly",
            "p_type": type,
            "p_description": description,
            "p_timezone": tz
        }).execute()
        return result.data if result.data else None
    except Exception as e:
        logger.error(f"add_credits_monthly failed: {e}")
        return None


def add_credits(user_id: str, amount: int, description: str, type: str = "purchase", tz: str = "UTC"):
    """Add credits (defaults to permanent)."""
    return add_credits_permanent(user_id, amount, description, type, tz)


@retry_on_network_error()
def get_credit_history(user_id: str, page: int = 1, limit: int = 20):
    """Get credit transaction history."""
    if not supabase:
        return {"items": [], "total": 0}
    
    offset = (page - 1) * limit
    result = supabase.table("credit_transactions").select("*", count="exact")\
        .eq("user_id", user_id).order("created_at", desc=True)\
        .range(offset, offset + limit - 1).execute()
    
    return {"items": result.data or [], "total": result.count or 0}


@retry_on_network_error()
def refresh_monthly_credits(user_id: str, tier: str):
    """Reset monthly credits based on tier."""
    if not supabase:
        return None
    
    tier_credits = {"starter": 500, "pro": 1000}
    amount = tier_credits.get(tier, 0)
    
    if amount == 0:
        return None
    
    supabase.table("profiles").update({
        "credits_monthly": amount,
        "credits_reset_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", user_id).execute()
    
    log_credit_transaction(user_id, amount, "monthly", "monthly_reset", f"{tier} monthly refresh")
    return {"credits_monthly": amount}


def check_and_reset_monthly_credits_if_needed(user_id: str):
    """Check and reset monthly credits if 30 days passed."""
    if not supabase:
        return
    
    profile = get_user_profile(user_id)
    if not profile:
        return
    
    tier = profile.get("tier", "free")
    if tier not in ["starter", "pro"]:
        return
    
    reset_at = profile.get("credits_reset_at")
    if not reset_at:
        refresh_monthly_credits(user_id, tier)
        return
    
    try:
        if isinstance(reset_at, str):
            reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
        else:
            reset_dt = reset_at
        
        days_since = (datetime.now(timezone.utc) - reset_dt).days
        if days_since >= 30:
            refresh_monthly_credits(user_id, tier)
    except Exception as e:
        logger.warning(f"Error checking credit reset: {e}")


# ==========================================
# User Search & Discount
# ==========================================

def search_users(query: str):
    """Search users by email, username, or user_code."""
    if not supabase:
        return []
    result = supabase.table("profiles").select("id, email, username, user_code, tier")\
        .or_(f"email.ilike.%{query}%,username.ilike.%{query}%,user_code.ilike.%{query}%")\
        .limit(20).execute()
    return result.data or []


def get_users_by_tier(tier: str):
    """Get all user IDs for a specific tier."""
    if not supabase:
        return []
    result = supabase.table("profiles").select("id").eq("tier", tier).execute()
    return [u["id"] for u in (result.data or [])]


def get_user_discount(user_id: str, target_plan: str = None):
    """Get active discount for user."""
    if not supabase:
        return None
    query = supabase.table("user_discounts").select("*")\
        .eq("user_id", user_id).eq("is_used", False)\
        .gte("expires_at", datetime.now(timezone.utc).isoformat())
    if target_plan:
        query = query.eq("target_plan", target_plan)
    result = query.order("discount_percent", desc=True).limit(1).execute()
    return result.data[0] if result.data else None


def create_user_discount(user_id: str, discount_percent: int, valid_days: int, target_plan: str = None):
    """Create a user discount."""
    if not supabase:
        return None
    expires_at = datetime.now(timezone.utc) + timedelta(days=valid_days)
    result = supabase.table("user_discounts").insert({
        "user_id": user_id,
        "discount_percent": discount_percent,
        "expires_at": expires_at.isoformat(),
        "target_plan": target_plan,
    }).execute()
    return result.data[0] if result.data else None
