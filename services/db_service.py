import os
import time
import logging
from functools import wraps
from supabase import create_client, Client
from datetime import datetime, timezone
import uuid

from .cache import cache_service

# Configure logging
logger = logging.getLogger(__name__)

# Get configuration from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Ensure URL has trailing slash to avoid SDK warning
if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL = SUPABASE_URL + '/'

# ==========================================
# Network Retry Configuration
# ==========================================

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds
RETRY_BACKOFF = 2  # exponential backoff multiplier

# Network error keywords to trigger retry
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
    """
    Decorator for automatic retry on network errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for exponential backoff
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    # Only retry on network-related errors
                    if not is_retryable_error(e):
                        raise e
                    
                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        logger.error(f"[DB] {func.__name__} failed after {max_retries + 1} attempts: {e}")
                        raise e
                    
                    # Log retry attempt
                    logger.warning(
                        f"[DB] {func.__name__} network error (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {current_delay:.1f}s: {e}"
                    )
                    
                    # Wait before retry with exponential backoff
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_error
        return wrapper
    return decorator

# ==========================================
# Supabase Client Initialization
# ==========================================

# Initialize client (simple and reliable)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

if supabase:
    logger.info("[DB] Supabase client initialized successfully")
else:
    logger.warning("[DB] Supabase client not initialized - missing URL or KEY")

# ==========================================
# 0. Permission Helpers
# ==========================================

def is_member(user: dict) -> bool:
    """
    Check if user is an active member.
    Only Starter/Pro with active subscription are considered members.
    """
    if not user:
        return False
    tier = user.get("tier", "free")
    subscription_status = user.get("subscription_status", "inactive")
    
    # Only starter/pro are members
    if tier not in ["starter", "pro"]:
        return False
    
    # Subscription must be active
    if subscription_status not in ["active", "trialing"]:
        return False
    
    return True

def can_access_resource(user: dict, allowed_tiers: list) -> bool:
    """
    Check if user has permission to access the resource.
    
    Rules:
    - If 'free' in allowed_tiers: Access allowed (no membership required)
    - If 'free' not in allowed_tiers: Must be is_member(user)=true AND user.tier in allowed_tiers
    """
    if not user or not allowed_tiers:
        return False
    
    user_tier = user.get("tier", "free")
    
    # If resource allows free users, anyone can access
    if "free" in allowed_tiers:
        return True
    
    # Otherwise must be active member and tier in allowed list
    if not is_member(user):
        return False
    
    return user_tier in allowed_tiers

def publish_permission(user: dict, resource_type: str, price_credits: int) -> dict:
    """
    Check user publish permission (PRD Chapter 7)
    
    Rules:
    - Free: Cannot publish anything
    - Starter: Only allow resource_type='asset' AND price_credits=0
    - Pro: Allow resource_type='asset'|'project' AND price_credits in 0..500
    
    Returns: { allowed: bool, reason: str }
    """
    if not user:
        return {"allowed": False, "reason": "User not found"}
    
    tier = user.get("tier", "free")
    
    # Free users cannot publish
    if tier == "free":
        return {"allowed": False, "reason": "Free users cannot publish. Upgrade to Starter or Pro."}
    
    # Price limit check
    if price_credits < 0 or price_credits > 500:
        return {"allowed": False, "reason": "Price must be between 0 and 500 credits"}
    
    # Starter user limits
    if tier == "starter":
        if resource_type != "asset":
            return {"allowed": False, "reason": "Starter users can only publish Assets. Upgrade to Pro to publish Projects."}
        if price_credits > 0:
            return {"allowed": False, "reason": "Starter users can only publish free assets. Upgrade to Pro to sell."}
    
    # Pro users can publish asset or project
    if tier == "pro":
        if resource_type not in ["asset", "project"]:
            return {"allowed": False, "reason": "Invalid resource type. Must be 'asset' or 'project'."}
    
    return {"allowed": True, "reason": ""}

def validate_allowed_tiers(allowed_tiers: list) -> dict:
    """
    Validate allowed_tiers whitelist (PRD Chapter 7)
    
    Only allow one of the following:
    - ['free']
    - ['starter', 'pro']
    - ['pro']
    
    Returns: { valid: bool, reason: str }
    """
    valid_combinations = [
        ['free'],
        ['starter', 'pro'],
        ['pro']
    ]
    
    # Compare after sorting
    sorted_tiers = sorted(allowed_tiers) if allowed_tiers else []
    
    for valid_combo in valid_combinations:
        if sorted_tiers == sorted(valid_combo):
            return {"valid": True, "reason": ""}
    
    return {
        "valid": False, 
        "reason": "allowed_tiers must be one of: ['free'], ['starter', 'pro'], or ['pro']"
    }

def listing_is_public_visible(listing: dict) -> bool:
    """
    Check if listing is publicly visible (PRD Chapter 8)
    
    Must satisfy:
    - is_public = true
    - is_deleted = false
    - moderation_status = 'approved'
    """
    if not listing:
        return False
    
    return (
        listing.get("is_public", False) == True and
        listing.get("is_deleted", False) == False and
        listing.get("moderation_status", "draft") == "approved"
    )

def get_total_credits(user: dict) -> int:
    """Get user total available credits (monthly + permanent)"""
    if not user:
        return 0
    return user.get("credits_monthly", 0) + user.get("credits_permanent", 0)

# ==========================================
# 1. User Profiles
# ==========================================

@retry_on_network_error()
def get_user_profile(user_id: str):
    """Get user profile with automatic retry on network errors"""
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if res.data:
        user = res.data[0]
        # Calculate total credits (compatible with frontend)
        user["credits"] = get_total_credits(user)
        return user
    return None

def generate_user_code() -> str:
    """
    Generate unique user code
    Format: YYYYMMDDHHMMSS + ms(3 digits) + sequence(7 digits)
    Example: 202512301430251230000001
    
    Use UTC-0 time to ensure global consistency
    Sequence padded to 7 digits
    
    Total length: 14 + 3 + 7 = 24 chars
    """
    from datetime import timezone
    
    # Get current UTC time (precise to ms)
    now_utc = datetime.now(timezone.utc)
    timestamp_part = now_utc.strftime("%Y%m%d%H%M%S") + f"{now_utc.microsecond // 1000:03d}"
    
    # Get current user count
    count_result = supabase.table("profiles").select("id", count="exact").execute()
    user_count = count_result.count if count_result.count else 0
    
    # Sequence = current count + 1, padded to 7 digits
    sequence_part = f"{user_count + 1:07d}"
    
    return f"{timestamp_part}{sequence_part}"


@retry_on_network_error()
def create_user_profile(user_id: str, email: str, username: str, avatar_url: str, first_name: str = None, last_name: str = None, timezone: str = "UTC"):
    """
    Create new user and grant initial credits
    According to PRD: Free users get 50 Credits (One-time, Permanent)
    
    Args:
        user_id: Clerk user ID
        email: User email
        username: Username
        avatar_url: Avatar URL
        first_name: First name
        last_name: Last name
        timezone: IANA timezone identifier (e.g., 'Asia/Shanghai', 'America/New_York')
    """
    # Generate unique user code
    user_code = generate_user_code()
    
    data = {
        "id": user_id,
        "email": email,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "avatar_url": avatar_url,
        "user_code": user_code,    # User unique code
        "credits_monthly": 0,      # Monthly subscription credits
        "credits_permanent": 50,   # Registration bonus 50 Credits (Permanent)
        "tier": "free",
        "subscription_status": "inactive",
        "role": "user",
        "timezone": timezone or "UTC",  # User timezone (IANA format)
    }
    supabase.table("profiles").insert(data).execute()
    # Log bonus transaction with timezone snapshot
    log_credit_transaction(
        user_id=user_id, 
        amount=50, 
        bucket="permanent",
        balance_monthly_after=0, 
        balance_permanent_after=50, 
        type="signup_bonus", 
        description="Welcome Bonus - 50 Credits",
        timezone=timezone or "UTC"  # v3.9: Snapshot timezone at registration
    )

def update_subscription_tier(user_id: str, tier: str, stripe_customer_id: str = None, subscription_status: str = "active"):
    """
    Update subscription tier
    Updates tier, subscription_status and stripe_customer_id
    """
    data = {
        "tier": tier,
        "subscription_status": subscription_status
    }
    if stripe_customer_id:
        data["stripe_customer_id"] = stripe_customer_id
    supabase.table("profiles").update(data).eq("id", user_id).execute()

def update_user_profile(user_id: str, avatar_url: str = None, username: str = None, first_name: str = None, last_name: str = None, timezone: str = None):
    """
    Update user profile (avatar, username, name, timezone)
    Used for Clerk user.updated webhook events
    
    Args:
        user_id: User ID
        avatar_url: Avatar URL
        username: Username
        first_name: First name
        last_name: Last name
        timezone: IANA timezone identifier (e.g., 'Asia/Shanghai')
    """
    data = {}
    if avatar_url is not None:
        data["avatar_url"] = avatar_url
    if username is not None:
        data["username"] = username
    if first_name is not None:
        data["first_name"] = first_name
    if last_name is not None:
        data["last_name"] = last_name
    if timezone is not None:
        data["timezone"] = timezone
    
    if data:
        supabase.table("profiles").update(data).eq("id", user_id).execute()
        return True
    return False


def update_user_timezone(user_id: str, timezone: str):
    """
    Update user timezone.
    Called when user logs in from a new timezone or explicitly changes timezone.
    
    Args:
        user_id: User ID
        timezone: IANA timezone identifier (e.g., 'Asia/Shanghai', 'America/New_York')
    
    Returns:
        bool: True if updated successfully
    """
    if not timezone:
        return False
    
    supabase.table("profiles").update({"timezone": timezone}).eq("id", user_id).execute()
    return True


def get_user_timezone(user_id: str) -> str:
    """
    Get user's timezone.
    
    Args:
        user_id: User ID
    
    Returns:
        str: IANA timezone identifier, defaults to 'UTC'
    """
    result = supabase.table("profiles").select("timezone").eq("id", user_id).single().execute()
    if result.data:
        return result.data.get("timezone") or "UTC"
    return "UTC"

def refresh_monthly_credits(user_id: str, tier: str):
    """
    Refresh monthly credits (called at subscription cycle start)
    - Starter: 500 credits/month
    - Pro: 1000 credits/month
    - No rollover: Reset directly to monthly quota (permanent credits unaffected)
    """
    monthly_amounts = {
        "starter": 500,
        "pro": 1000,
        "free": 0
    }
    
    new_monthly = monthly_amounts.get(tier, 0)
    
    profile = get_user_profile(user_id)
    if not profile:
        return False
    
    # Important: permanent credits are unaffected
    permanent = profile.get("credits_permanent", 0)
    
    # Reset monthly credits (no rollover) - only reset monthly
    supabase.table("profiles").update({
        "credits_monthly": new_monthly,
        "monthly_credits_cycle_anchor": datetime.now().isoformat()
    }).eq("id", user_id).execute()
    
    # Log transaction
    log_credit_transaction(
        user_id=user_id,
        amount=new_monthly,
        bucket="monthly",
        balance_monthly_after=new_monthly,
        balance_permanent_after=permanent,  # permanent credits preserved
        type="sub_grant",
        description=f"Monthly {tier.capitalize()} Credits (Reset - Permanent credits preserved)"
    )
    
    return True

def check_and_reset_monthly_credits_if_needed(user_id: str):
    """
    Check and reset monthly credits if needed
    Called on user login or profile fetch to ensure monthly credits reset on time
    
    Rules:
    - If monthly_credits_cycle_anchor missing or > 30 days, and user is Starter/Pro, reset
    - permanent credits never reset
    """
    profile = get_user_profile(user_id)
    if not profile:
        return False
    
    tier = profile.get("tier", "free")
    subscription_status = profile.get("subscription_status", "inactive")
    
    # Only Starter/Pro with active sub need reset
    if tier not in ["starter", "pro"]:
        return False
    
    if subscription_status not in ["active", "trialing"]:
        return False
    
    cycle_anchor = profile.get("monthly_credits_cycle_anchor")
    
    # If no cycle_anchor, it's first time, set it
    if not cycle_anchor:
        refresh_monthly_credits(user_id, tier)
        return True
    
    # Check if > 30 days (one month)
    try:
        anchor_date = datetime.fromisoformat(cycle_anchor.replace('Z', '+00:00'))
        if anchor_date.tzinfo is None:
            anchor_date = anchor_date.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        days_since_reset = (now - anchor_date).total_seconds() / (24 * 3600)
        
        # If > 30 days, reset monthly credits
        if days_since_reset >= 30:
            refresh_monthly_credits(user_id, tier)
            return True
    except (ValueError, TypeError) as e:
        # If date parse fails, reset once
        print(f"Warning: Failed to parse monthly_credits_cycle_anchor for user {user_id}: {e}")
        refresh_monthly_credits(user_id, tier)
        return True
    
    return False

# ==========================================
# 2. Credits & Transactions
# ==========================================

def log_credit_transaction(
    user_id: str, 
    amount: int, 
    bucket: str,  # 'monthly' | 'permanent'
    balance_monthly_after: int, 
    balance_permanent_after: int, 
    type: str, 
    description: str,
    timezone: str = "UTC"  # v3.9: Snapshot timezone for dual-storage
):
    """
    [Internal] Log transaction - Support Credits Buckets
    
    v3.9: Added timezone parameter for dual-storage strategy.
    The timezone is a "snapshot" of the user's timezone at transaction time.
    Trigger will auto-compute created_at_local.
    """
    supabase.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": amount,
        "bucket": bucket,
        "balance_monthly_after": balance_monthly_after,
        "balance_permanent_after": balance_permanent_after,
        "type": type,
        "description": description,
        "timezone": timezone,  # v3.9: Snapshot timezone
        "created_at": datetime.now().isoformat()
    }).execute()

def log_payment_record(
    user_id: str, 
    amount_cents: int, 
    currency: str,
    type: str,  # 'sub_payment', 'sub_renewal', 'credits_purchase'
    description: str,
    timezone: str = "UTC"
):
    """
    Log payment record (subscription fee, credits purchase, etc.)
    amount_cents: Amount in cents
    currency: Currency code (e.g. 'USD')
    type: Payment type
    description: Description
    timezone: IANA timezone for transaction snapshot
    """
    # Get user current balance for logging
    profile = supabase.table("profiles").select("credits_monthly, credits_permanent").eq("id", user_id).single().execute()
    balance_monthly = profile.data.get("credits_monthly", 0) if profile.data else 0
    balance_permanent = profile.data.get("credits_permanent", 0) if profile.data else 0
    
    supabase.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": 0,  # Payment record doesn't affect credits directly here
        "bucket": "payment",  # Special bucket for payment records
        "balance_monthly_after": balance_monthly,
        "balance_permanent_after": balance_permanent,
        "type": type,
        "description": f"{description} | {currency} {amount_cents}",  # Include amount info
        "timezone": timezone,  # v3.9: Snapshot timezone
        "created_at": datetime.now().isoformat()
    }).execute()

def credit_deduct(user_id: str, amount: int, type: str, description: str, timezone: str = "UTC") -> dict:
    """
    [Core] Atomic deduction function using PostgreSQL RPC
    Priority: Deduct Monthly Credits first, then Permanent Credits
    
    v3.22: Uses atomic RPC function for:
    - Row locking (SELECT FOR UPDATE) to prevent race conditions
    - Atomic balance update and transaction logging
    - Better consistency under concurrent access
    
    Args:
        user_id: User ID
        amount: Amount to deduct
        type: Transaction type
        description: Transaction description
        timezone: v3.9 - Snapshot timezone for dual-storage
    
    Returns: { success: bool, balance_monthly: int, balance_permanent: int, total: int }
    Raises: Exception if insufficient credits or user not found
    """
    if amount <= 0:
        # No deduction needed, return current balance
        profile = get_user_profile(user_id)
        if not profile:
            raise Exception("User not found")
        monthly = profile.get("credits_monthly", 0)
        permanent = profile.get("credits_permanent", 0)
        return {
            "success": True,
            "balance_monthly": monthly,
            "balance_permanent": permanent,
            "total": monthly + permanent
        }
    
    try:
        # Call atomic RPC function
        result = supabase.rpc("deduct_credits_atomic", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_tx_type": type,
            "p_description": description,
            "p_timezone": timezone,
            "p_idempotency_key": None
        }).execute()
        
        data = result.data
        
        if not data:
            raise Exception("Database error: no response from RPC")
        
        if data.get("success"):
            balance_monthly = data.get("balance_monthly", 0)
            balance_permanent = data.get("balance_permanent", 0)
            return {
                "success": True,
                "balance_monthly": balance_monthly,
                "balance_permanent": balance_permanent,
                "total": balance_monthly + balance_permanent
            }
        else:
            error = data.get("error", "Unknown error")
            error_code = data.get("error_code", "")
            
            # Map error codes to exceptions for backward compatibility
            if error_code == "CREDITS_INSUFFICIENT":
                raise Exception("CREDITS_INSUFFICIENT")
            elif error_code == "USER_NOT_FOUND":
                raise Exception("User not found")
            else:
                raise Exception(error)
                
    except Exception as e:
        # Re-raise to maintain backward compatibility with callers
        logger.error(f"[DB] credit_deduct error for {user_id}: {e}")
        raise

def add_credits_permanent(user_id: str, amount: int, description: str, type: str = "topup_purchase", timezone: str = "UTC"):
    """
    Add permanent credits using atomic RPC (for purchase/sale earnings)
    Credits earned from buying/selling are always permanent
    
    v3.22: Uses atomic RPC function for consistency
    
    Args:
        user_id: User ID
        amount: Amount to add
        description: Transaction description
        type: Transaction type
        timezone: v3.9 - Snapshot timezone for dual-storage
    """
    if amount <= 0:
        profile = get_user_profile(user_id)
        if not profile:
            return None
        return {
            "balance_monthly": profile.get("credits_monthly", 0),
            "balance_permanent": profile.get("credits_permanent", 0)
        }
    
    try:
        result = supabase.rpc("add_credits_atomic", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_bucket": "permanent",
            "p_tx_type": type,
            "p_description": description,
            "p_timezone": timezone,
            "p_idempotency_key": None
        }).execute()
        
        data = result.data
        
        if data and data.get("success"):
            return {
                "balance_monthly": data.get("balance_monthly", 0),
                "balance_permanent": data.get("balance_permanent", 0)
            }
        else:
            logger.error(f"[DB] add_credits_permanent failed for {user_id}: {data}")
            return None
            
    except Exception as e:
        logger.error(f"[DB] add_credits_permanent exception for {user_id}: {e}")
        return None

def add_credits_monthly(user_id: str, amount: int, description: str, type: str = "sub_grant", timezone: str = "UTC"):
    """
    Add monthly credits using atomic RPC (for subscription grants)
    
    v3.22: Uses atomic RPC function for consistency
    
    Args:
        user_id: User ID
        amount: Amount to add
        description: Transaction description
        type: Transaction type
        timezone: v3.9 - Snapshot timezone for dual-storage
    """
    if amount <= 0:
        return None
    
    try:
        result = supabase.rpc("add_credits_atomic", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_bucket": "monthly",
            "p_tx_type": type,
            "p_description": description,
            "p_timezone": timezone,
            "p_idempotency_key": None
        }).execute()
        
        data = result.data
        
        if data and data.get("success"):
            return {
                "balance_monthly": data.get("balance_monthly", 0),
                "balance_permanent": data.get("balance_permanent", 0)
            }
        else:
            logger.error(f"[DB] add_credits_monthly failed for {user_id}: {data}")
            return None
            
    except Exception as e:
        logger.error(f"[DB] add_credits_monthly exception for {user_id}: {e}")
        return None
    
    return {"balance_monthly": new_monthly, "balance_permanent": permanent}

# Backward compatibility
def deduct_credits_atomic(user_id: str, amount: int, type: str, description: str, timezone: str = "UTC"):
    """[Compat] Atomic deduction - internally calls credit_deduct"""
    result = credit_deduct(user_id, amount, type, description, timezone=timezone)
    return result["success"]

def add_credits(user_id: str, amount: int, description: str, type: str = "purchase", timezone: str = "UTC"):
    """[Compat] Add credits - defaults to adding to permanent"""
    return add_credits_permanent(user_id, amount, description, type, timezone=timezone)

@retry_on_network_error()
def get_credit_history(user_id: str, page: int = 1, limit: int = 20):
    """Get credit history with total count for pagination
    
    Returns:
        dict: { "items": [...], "total": int }
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    # Get paginated items
    res = supabase.table("credit_transactions")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .range(start, end)\
        .execute()
    
    # Get total count (using count option)
    count_res = supabase.table("credit_transactions")\
        .select("id", count="exact")\
        .eq("user_id", user_id)\
        .execute()
    
    total = count_res.count if count_res.count is not None else len(res.data)
    
    return {"items": res.data, "total": total}

# ==========================================
# 3. Project Management (Projects)
# ==========================================

@retry_on_network_error()
def get_user_projects(user_id: str, page: int = 1, limit: int = 20, search: str = None, include_canvas_data: bool = True):
    """Get project list
    
    Args:
        user_id: User ID
        page: Page number
        limit: Items per page
        search: Search query
        include_canvas_data: Whether to include canvas_data (for step loading optimization)
    """
    start = (page - 1) * limit
    end = start + limit - 1
    print(f"[GET_PROJECTS] Query params: user_id={user_id}, page={page}, limit={limit}, search={search}, include_canvas_data={include_canvas_data}")
    
    # Determine fields based on include_canvas_data
    if include_canvas_data:
        select_fields = "id, title, thumbnail_url, canvas_data, source_listing_id, created_at, updated_at"
    else:
        # Without canvas_data, return basic info only (faster load)
        select_fields = "id, title, thumbnail_url, source_listing_id, created_at, updated_at"
    
    query = supabase.table("projects").select(select_fields)\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    # Add search filter if provided
    if search and search.strip():
        search_term = search.strip()
        print(f"[GET_PROJECTS] Adding search filter: {search_term}")
        query = query.ilike("title", f"%{search_term}%")
    
    res = query.range(start, end).order("updated_at", desc=True).execute()
    items = res.data or []
    items_count = len(items)
    print(f"[GET_PROJECTS] Returned {items_count} items")
    
    # Get corresponding marketplace_listings (if any)
    if items:
        project_ids = [item["id"] for item in items]
        # Use resource_id to match project.id (unified design)
        listings_res = supabase.table("marketplace_listings").select(
            "id, resource_id, moderation_status, is_public, allowed_tiers, price_credits, sales_count, version, changelog, version_history, description"
        ).in_("resource_id", project_ids).eq("is_deleted", False).execute()
        
        # Build resource_id -> listing map
        listings_map = {}
        if listings_res.data:
            for listing in listings_res.data:
                # resource_id is UUID, convert to string for matching
                rid = str(listing["resource_id"]) if listing.get("resource_id") else None
                if rid:
                    listings_map[rid] = {
                        "id": listing["id"],
                        "moderation_status": listing["moderation_status"],
                        "is_public": listing["is_public"],
                        "allowed_tiers": listing["allowed_tiers"],
                        "price_credits": listing["price_credits"],
                        "sales_count": listing["sales_count"],
                        "version": listing.get("version", "1.0"),
                        "changelog": listing.get("changelog", ""),
                        "version_history": listing.get("version_history", []),
                        "description": listing.get("description", ""),
                    }
        
        # Attach listing info to project data
        for item in items:
            item["marketplace_listing"] = listings_map.get(item["id"])
        
        # Get purchase source listing info
        source_listing_ids = [item["source_listing_id"] for item in items if item.get("source_listing_id")]
        if source_listing_ids:
            source_listings_res = supabase.table("marketplace_listings").select(
                "id, price_credits, sales_count"
            ).in_("id", source_listing_ids).execute()
            
            source_listings_map = {}
            if source_listings_res.data:
                for listing in source_listings_res.data:
                    source_listings_map[listing["id"]] = {
                        "price_credits": listing["price_credits"],
                        "sales_count": listing["sales_count"],
                    }
            
            # Attach purchase info to project data
            for item in items:
                if item.get("source_listing_id"):
                    item["purchase_info"] = source_listings_map.get(item["source_listing_id"])
    
    return items

def count_user_projects(user_id: str, search: str = None):
    """Get total user projects count (for pagination and limit check)"""
    try:
        print(f"[COUNT] Starting count query for user_id: {user_id}, search: {search}")
        
        # Method 1: Query IDs and count
        # Most reliable way, avoids Supabase count param compatibility issues
        query = supabase.table("projects").select("id")\
            .eq("user_id", user_id).eq("is_deleted", False)
        
        # Add search filter if provided
        if search and search.strip():
            search_term = search.strip()
            print(f"[COUNT] Adding search filter: {search_term}")
            query = query.ilike("title", f"%{search_term}%")
        
        res = query.execute()
        
        # Use result length as count
        count_value = len(res.data) if res.data else 0
        print(f"[COUNT] Final count: {count_value}")
        return count_value
    except Exception as e:
        print(f"[COUNT] Error counting projects: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: return 0 on error
        return 0

@retry_on_network_error()
def get_project_detail(project_id: str, user_id: str):
    """Get project detail with automatic retry on network errors"""
    print(f"[DB_GET] Fetching project {project_id} for user {user_id}")
    res = supabase.table("projects").select("*")\
        .eq("id", project_id).eq("user_id", user_id).single().execute()
    
    if res.data:
        canvas_data = res.data.get("canvas_data", {})
        if canvas_data:
            pages = canvas_data.get("pages", []) if isinstance(canvas_data, dict) else canvas_data
            print(f"[DB_GET] Project {project_id} has {len(pages)} pages")
            for i, page in enumerate(pages):
                if page:
                    has_json = bool(page.get("canvasJson"))
                    obj_count = len(page.get("canvasJson", {}).get("objects", [])) if page.get("canvasJson") else 0
                    print(f"[DB_GET] Page {i}: hasCanvasJson={has_json}, objectCount={obj_count}")
        else:
            print(f"[DB_GET] Project {project_id} has no canvas_data")
    else:
        print(f"[DB_GET] Project {project_id} not found")
    
    return res.data

@retry_on_network_error()
def create_project(user_id: str, title: str = None, canvas_data: dict = None, timezone: str = "UTC"):
    """Create project (optionally with initial data) with automatic retry on network errors
    
    Args:
        user_id: User ID
        title: Project title
        canvas_data: Initial canvas data
        timezone: IANA timezone for transaction snapshot
    """
    data = {
        "user_id": user_id,
        "title": title or "My Magic Story",
        "canvas_data": canvas_data or {},
        "last_downloaded_hash": "",
        "timezone": timezone  # v3.9: Snapshot timezone
    }
    res = supabase.table("projects").insert(data).execute()
    return res.data[0]

def duplicate_project(project_id: str, user_id: str, timezone: str = "UTC"):
    """
    Duplicate/Copy a project.
    
    - Own projects: Creates copy with title + " copied"
    - Purchased projects: Creates editable copy, NOT shown in Bought view
      - Records origin_owner_id to track original creator
      - Does NOT set is_purchased=true (so it shows in All, not Bought)
    
    Args:
        project_id: Project ID to duplicate
        user_id: User ID
        timezone: IANA timezone for transaction snapshot
    
    Returns: New project data or raises Exception
    """
    # Get original project
    original = supabase.table("projects").select("*")\
        .eq("id", project_id).eq("user_id", user_id).eq("is_deleted", False).single().execute()
    
    if not original.data:
        raise Exception("Project not found or permission denied")
    
    original_title = original.data.get('title', 'Untitled Project')
    is_purchased = bool(original.data.get("source_listing_id")) or bool(original.data.get("is_purchased"))
    
    # Create new project data
    new_data = {
        "user_id": user_id,
        "canvas_data": original.data.get("canvas_data", {}),
        "thumbnail_url": original.data.get("thumbnail_url"),
        "last_downloaded_hash": "",
        "is_purchased": False,  # Duplicated projects are NOT purchased, they're user-created copies
        "timezone": timezone,  # v3.9: Snapshot timezone
    }
    
    if is_purchased:
        # Purchased project: keep same name, record origin info for traceability
        new_data["title"] = f"{original_title} (Copy)"
        # Record the original owner ID for tracking origin
        new_data["origin_owner_id"] = original.data.get("origin_owner_id") or original.data.get("user_id")
        # Keep reference to source listing for traceability
        new_data["source_listing_id"] = original.data.get("source_listing_id")
    else:
        # Own project: add " copied" suffix
        new_data["title"] = f"{original_title} copied"
        # For own projects, origin_owner_id is the user themselves
        new_data["origin_owner_id"] = user_id
    
    res = supabase.table("projects").insert(new_data).execute()
    return res.data[0] if res.data else None

def save_project(project_id: str, user_id: str, canvas_data: dict = None, thumbnail_url: str = None, title: str = None):
    """Save project"""
    print(f"[DB_SAVE] Starting save for project {project_id}")
    data = {
        "updated_at": datetime.now().isoformat()
    }
    if canvas_data is not None:
        data["canvas_data"] = canvas_data
        # Debug: Log canvas_data structure
        pages = canvas_data.get("pages", []) if isinstance(canvas_data, dict) else canvas_data
        print(f"[DB_SAVE] canvas_data has {len(pages)} pages")
        for i, page in enumerate(pages):
            if page:
                has_json = bool(page.get("canvasJson"))
                obj_count = len(page.get("canvasJson", {}).get("objects", [])) if page.get("canvasJson") else 0
                print(f"[DB_SAVE] Page {i}: hasCanvasJson={has_json}, objectCount={obj_count}")
    else:
        print(f"[DB_SAVE] No canvas_data provided")
    if thumbnail_url:
        data["thumbnail_url"] = thumbnail_url
    if title:
        data["title"] = title
    
    result = supabase.table("projects").update(data).eq("id", project_id).eq("user_id", user_id).execute()
    print(f"[DB_SAVE] Save completed for project {project_id}")

def soft_delete_project(project_id: str, user_id: str):
    """Soft delete project"""
    from datetime import datetime
    res = supabase.table("projects").update({
        "is_deleted": True,
        "deleted_at": datetime.utcnow().isoformat()
    }).eq("id", project_id).eq("user_id", user_id).execute()
    if not res.data:
        raise Exception("Project not found or permission denied")
    return True

def restore_project(project_id: str):
    """[Admin] Restore deleted project"""
    res = supabase.table("projects").update({
        "is_deleted": False,
        "deleted_at": None
    }).eq("id", project_id).execute()
    return res.data[0] if res.data else None


def get_user_deleted_projects(user_id: str, page: int = 1, limit: int = 20):
    """Get user deleted projects (last 30 days, excluding hidden from trash)"""
    from datetime import datetime, timedelta, timezone
    
    start = (page - 1) * limit
    end = start + limit - 1
    
    # Only return projects deleted in last 30 days AND not hidden from trash
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    # Select fields: title, thumbnail, deleted_at, id
    res = supabase.table("projects").select(
        "id, title, thumbnail_url, deleted_at, created_at, updated_at"
    ).eq("user_id", user_id).eq("is_deleted", True)\
        .eq("is_hidden_from_trash", False)\
        .gte("deleted_at", cutoff_date)\
        .order("deleted_at", desc=True).range(start, end).execute()
    
    # Get total count (last 30 days, excluding hidden)
    count_res = supabase.table("projects").select("id", count="exact")\
        .eq("user_id", user_id).eq("is_deleted", True)\
        .eq("is_hidden_from_trash", False)\
        .gte("deleted_at", cutoff_date).execute()
    total = count_res.count if count_res.count else 0
    
    return {
        "items": res.data or [],
        "total": total,
        "page": page
    }


def permanently_hide_project(project_id: str, user_id: str):
    """
    Permanently hide project from trash (soft delete stage 2).
    Project data is retained but invisible to user.
    """
    # Check if project belongs to user and is already deleted
    check = supabase.table("projects").select("id")\
        .eq("id", project_id).eq("user_id", user_id).eq("is_deleted", True).execute()
    
    if not check.data:
        raise Exception("Project not found or not in trash")
    
    res = supabase.table("projects").update({
        "is_hidden_from_trash": True
    }).eq("id", project_id).eq("user_id", user_id).execute()
    
    return res.data[0] if res.data else None


@retry_on_network_error()
def get_dashboard_projects(
    user_id: str, 
    view_type: str = "all",  # "all" | "bought" | "selling"
    page: int = 1, 
    limit: int = 20, 
    search: str = None,
    include_canvas_data: bool = True
):
    """
    Get projects for dashboard with view type filtering.
    
    Args:
        user_id: User ID
        view_type: "all" (created + bought + selling), "bought" (purchased only), "selling" (active listings)
        page: Page number
        limit: Items per page
        search: Search query
        include_canvas_data: Whether to include canvas_data
    
    Returns:
        Dict with items, total, page, and view-specific metadata
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    print(f"[DASHBOARD_PROJECTS] view_type={view_type}, user_id={user_id}, page={page}")
    
    # Determine select fields
    if include_canvas_data:
        select_fields = "id, title, thumbnail_url, canvas_data, source_listing_id, is_purchased, origin_owner_id, listing_status, marketplace_listing_id, created_at, updated_at"
    else:
        select_fields = "id, title, thumbnail_url, source_listing_id, is_purchased, origin_owner_id, listing_status, marketplace_listing_id, created_at, updated_at"
    
    # Build base query
    query = supabase.table("projects").select(select_fields)\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    # Apply view type filter
    if view_type == "bought":
        # Only purchased projects (is_purchased = true OR source_listing_id IS NOT NULL)
        query = query.eq("is_purchased", True)
    elif view_type == "selling":
        # Only projects with active listings (listing_status = 'approved' and marketplace_listing.is_public = true)
        query = query.not_.is_("listing_status", "null")
    # "all" - no additional filter (shows all: created + bought + selling)
    
    # Apply search filter
    if search and search.strip():
        search_term = search.strip()
        query = query.ilike("title", f"%{search_term}%")
    
    # Execute query
    res = query.range(start, end).order("updated_at", desc=True).execute()
    items = res.data or []
    
    # Get total count with same filters
    count_query = supabase.table("projects").select("id")\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    if view_type == "bought":
        count_query = count_query.eq("is_purchased", True)
    elif view_type == "selling":
        count_query = count_query.not_.is_("listing_status", "null")
    
    if search and search.strip():
        count_query = count_query.ilike("title", f"%{search.strip()}%")
    
    count_res = count_query.execute()
    total = len(count_res.data) if count_res.data else 0
    
    # Enrich with marketplace listing data
    if items:
        project_ids = [item["id"] for item in items]
        marketplace_listing_ids = [item["marketplace_listing_id"] for item in items if item.get("marketplace_listing_id")]
        
        # Get marketplace listings for these projects
        if marketplace_listing_ids:
            listings_res = supabase.table("marketplace_listings").select(
                "id, title, description, moderation_status, is_public, allowed_tiers, price_credits, sales_count, unique_buyers_count, total_revenue, usage_count, version, changelog"
            ).in_("id", marketplace_listing_ids).execute()
            
            listings_map = {}
            if listings_res.data:
                for listing in listings_res.data:
                    listings_map[listing["id"]] = listing
            
            # Attach listing info to projects
            for item in items:
                if item.get("marketplace_listing_id"):
                    item["marketplace_listing"] = listings_map.get(item["marketplace_listing_id"])
        
        # Also check by resource_id (for projects without marketplace_listing_id)
        listings_by_id_res = supabase.table("marketplace_listings").select(
            "id, resource_id, moderation_status, is_public, allowed_tiers, price_credits, sales_count, unique_buyers_count, total_revenue, version, changelog"
        ).in_("resource_id", project_ids).eq("is_deleted", False).execute()
        
        if listings_by_id_res.data:
            for listing in listings_by_id_res.data:
                # Find the project and add listing if not already present
                rid = str(listing["resource_id"]) if listing.get("resource_id") else None
                for item in items:
                    if rid and item["id"] == rid and not item.get("marketplace_listing"):
                        item["marketplace_listing"] = listing
        
        # Get origin owner info for purchased projects
        origin_owner_ids = [item["origin_owner_id"] for item in items if item.get("origin_owner_id")]
        if origin_owner_ids:
            owners_res = supabase.table("profiles").select(
                "id, username, avatar_url"
            ).in_("id", origin_owner_ids).execute()
            
            owners_map = {}
            if owners_res.data:
                for owner in owners_res.data:
                    owners_map[owner["id"]] = owner
            
            for item in items:
                if item.get("origin_owner_id"):
                    item["origin_owner"] = owners_map.get(item["origin_owner_id"])
    
    # Filter for "selling" view: only show projects with active public listings
    if view_type == "selling":
        items = [
            item for item in items 
            if item.get("marketplace_listing") and 
               item["marketplace_listing"].get("is_public") and 
               item["marketplace_listing"].get("moderation_status") == "approved"
        ]
        total = len(items)  # Recalculate total after filtering
    
    # Get counts for all view types (for tab badges)
    # Count all (non-deleted) projects
    all_count_res = supabase.table("projects").select("id")\
        .eq("user_id", user_id).eq("is_deleted", False).execute()
    all_count = len(all_count_res.data) if all_count_res.data else 0
    
    # Count bought projects
    bought_count_res = supabase.table("projects").select("id")\
        .eq("user_id", user_id).eq("is_deleted", False).eq("is_purchased", True).execute()
    bought_count = len(bought_count_res.data) if bought_count_res.data else 0
    
    # Count selling projects (with active listings)
    selling_count_res = supabase.table("marketplace_listings").select("id")\
        .eq("seller_id", user_id).eq("resource_type", "project")\
        .eq("is_public", True).eq("moderation_status", "approved").eq("is_deleted", False).execute()
    selling_count = len(selling_count_res.data) if selling_count_res.data else 0
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "view_type": view_type,
        "counts": {
            "all": all_count,
            "bought": bought_count,
            "selling": selling_count
        }
    }


def get_seller_project_stats(user_id: str):
    """
    Get seller statistics for projects (for Selling view header).
    
    Returns:
        Dict with total_selling, total_sales, unique_buyers, total_revenue
    """
    # Get all active project listings for this seller
    res = supabase.table("marketplace_listings").select(
        "id, sales_count, unique_buyers_count, total_revenue, usage_count"
    ).eq("seller_id", user_id)\
        .eq("resource_type", "project")\
        .eq("is_public", True)\
        .eq("moderation_status", "approved")\
        .eq("is_deleted", False).execute()
    
    listings = res.data or []
    
    # Aggregate stats
    total_selling = len(listings)
    total_sales = sum(l.get("sales_count", 0) for l in listings)
    unique_buyers = sum(l.get("unique_buyers_count", 0) for l in listings)  # Note: May overcount across listings
    total_revenue = sum(l.get("total_revenue", 0) for l in listings)
    total_usage = sum(l.get("usage_count", 0) for l in listings)
    
    return {
        "total_selling": total_selling,
        "total_sales": total_sales,
        "unique_buyers": unique_buyers,
        "total_revenue": total_revenue,
        "total_usage": total_usage
    }


def user_restore_project(project_id: str, user_id: str):
    """User restore own deleted project"""
    # Check if project belongs to user and is deleted
    check = supabase.table("projects").select("id")\
        .eq("id", project_id).eq("user_id", user_id).eq("is_deleted", True).execute()
    
    if not check.data:
        raise Exception("Project not found or not deleted")
    
    res = supabase.table("projects").update({
        "is_deleted": False,
        "deleted_at": None
    }).eq("id", project_id).eq("user_id", user_id).execute()
    
    return res.data[0] if res.data else None

def update_project_hash(project_id: str, new_hash: str):
    """Update Hash only (for cache/dedup, no credit deduction)"""
    supabase.table("projects").update({"last_downloaded_hash": new_hash})\
        .eq("id", project_id).execute()

def get_all_projects_feed(page: int = 1, limit: int = 50):
    """[Admin] Get all projects feed"""
    start = (page - 1) * limit
    end = start + limit - 1
    res = supabase.table("projects").select("*, profiles(email, username)")\
        .eq("is_deleted", False)\
        .order("updated_at", desc=True)\
        .range(start, end).execute()
    return res.data

# ==========================================
# 4. Assets & Resources
# ==========================================

def save_asset(user_id: str, url: str, type: str, project_id: str = None, prompt: str = None, timezone: str = "UTC"):
    """Save asset
    
    Args:
        user_id: User ID
        url: Asset URL
        type: Asset type
        project_id: Optional project ID
        prompt: Optional generation prompt
        timezone: IANA timezone for transaction snapshot
    """
    data = {
        "user_id": user_id,
        "url": url,
        "type": type,
        "project_id": project_id,
        "prompt": prompt,
        "timezone": timezone  # v3.9: Snapshot timezone
    }
    supabase.table("assets").insert(data).execute()

@retry_on_network_error()
def get_assets(user_id: str, project_id: str = None):
    """Get user assets with marketplace_listing info and purchase_info"""
    query = supabase.table("assets").select("*").eq("user_id", user_id).eq("is_deleted", False)
    if project_id:
        query = query.eq("project_id", project_id)
    res = query.order("created_at", desc=True).execute()
    items = res.data or []
    
    # Get corresponding marketplace_listings (if any)
    # Use resource_id column to match asset.id
    if items:
        asset_ids = [item["id"] for item in items]
        listings_res = supabase.table("marketplace_listings").select(
            "id, resource_id, resource_url, moderation_status, is_public, allowed_tiers, price_credits, sales_count"
        ).in_("resource_id", asset_ids).eq("is_deleted", False).execute()
        
        # Build resource_id -> listing map
        listings_map = {}
        if listings_res.data:
            for listing in listings_res.data:
                listings_map[listing["resource_id"]] = {
                    "id": listing["id"],
                    "moderation_status": listing["moderation_status"],
                    "is_public": listing["is_public"],
                    "allowed_tiers": listing["allowed_tiers"],
                    "price_credits": listing["price_credits"],
                    "sales_count": listing["sales_count"],
                }
        
        # Attach listing info to asset data
        for item in items:
            item["marketplace_listing"] = listings_map.get(item["id"])
        
        # Get purchase source listing info (for purchased assets)
        source_listing_ids = [item["source_listing_id"] for item in items if item.get("source_listing_id")]
        if source_listing_ids:
            source_listings_res = supabase.table("marketplace_listings").select(
                "id, price_credits, sales_count"
            ).in_("id", source_listing_ids).execute()
            
            source_listings_map = {}
            if source_listings_res.data:
                for listing in source_listings_res.data:
                    source_listings_map[listing["id"]] = {
                        "price_credits": listing["price_credits"],
                        "sales_count": listing["sales_count"],
                    }
            
            # Attach purchase info to asset data
            for item in items:
                if item.get("source_listing_id"):
                    item["purchase_info"] = source_listings_map.get(item["source_listing_id"])
    
    return items


@retry_on_network_error()
def get_dashboard_assets(
    user_id: str, 
    view_type: str = "all",  # "all" | "bought" | "selling"
    page: int = 1, 
    limit: int = 15,  # 15 per page (5x3 grid)
    search: str = None
):
    """
    Get assets for dashboard with view type filtering.
    
    Args:
        user_id: User ID
        view_type: "all" (uploaded + bought + selling), "bought" (purchased only), "selling" (active listings)
        page: Page number
        limit: Items per page (default: 15 for 5x3 grid)
        search: Search query for asset name/description
    
    Returns:
        Dict with items, total, page, and view-specific metadata
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    print(f"[DASHBOARD_ASSETS] view_type={view_type}, user_id={user_id}, page={page}")
    
    # Build base query
    query = supabase.table("assets").select("*")\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    # Apply view type filter
    if view_type == "bought":
        # Only purchased assets (is_purchased = true OR source_listing_id IS NOT NULL)
        query = query.eq("is_purchased", True)
    elif view_type == "selling":
        # Only assets with active listings (listing_status is not null)
        query = query.not_.is_("listing_status", "null")
    # "all" - no additional filter
    
    # Apply search filter
    if search and search.strip():
        search_term = search.strip()
        # Search in name or description
        query = query.or_(f"name.ilike.%{search_term}%,description.ilike.%{search_term}%")
    
    # Execute query with pagination
    res = query.range(start, end).order("created_at", desc=True).execute()
    items = res.data or []
    
    # Get total count with same filters
    count_query = supabase.table("assets").select("id")\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    if view_type == "bought":
        count_query = count_query.eq("is_purchased", True)
    elif view_type == "selling":
        count_query = count_query.not_.is_("listing_status", "null")
    
    if search and search.strip():
        search_term = search.strip()
        count_query = count_query.or_(f"name.ilike.%{search_term}%,description.ilike.%{search_term}%")
    
    count_res = count_query.execute()
    total = len(count_res.data) if count_res.data else 0
    
    # Enrich with marketplace listing data
    if items:
        asset_ids = [item["id"] for item in items]
        marketplace_listing_ids = [item["marketplace_listing_id"] for item in items if item.get("marketplace_listing_id")]
        
        # Get marketplace listings for these assets
        if marketplace_listing_ids:
            listings_res = supabase.table("marketplace_listings").select(
                "id, title, description, moderation_status, is_public, allowed_tiers, price_credits, sales_count, unique_buyers_count, total_revenue, usage_count"
            ).in_("id", marketplace_listing_ids).execute()
            
            listings_map = {}
            if listings_res.data:
                for listing in listings_res.data:
                    listings_map[listing["id"]] = listing
            
            # Attach listing info to assets
            for item in items:
                if item.get("marketplace_listing_id"):
                    item["marketplace_listing"] = listings_map.get(item["marketplace_listing_id"])
        
        # Also check by resource_id (backwards compatibility)
        listings_by_id_res = supabase.table("marketplace_listings").select(
            "id, resource_id, moderation_status, is_public, allowed_tiers, price_credits, sales_count, unique_buyers_count, total_revenue"
        ).in_("resource_id", asset_ids).eq("is_deleted", False).execute()
        
        if listings_by_id_res.data:
            for listing in listings_by_id_res.data:
                # Find the asset and add listing if not already present
                for item in items:
                    if item["id"] == listing["resource_id"] and not item.get("marketplace_listing"):
                        item["marketplace_listing"] = listing
        
        # Get origin owner info for purchased assets
        origin_owner_ids = [item["origin_owner_id"] for item in items if item.get("origin_owner_id")]
        if origin_owner_ids:
            owners_res = supabase.table("profiles").select(
                "id, username, avatar_url"
            ).in_("id", origin_owner_ids).execute()
            
            owners_map = {}
            if owners_res.data:
                for owner in owners_res.data:
                    owners_map[owner["id"]] = owner
            
            for item in items:
                if item.get("origin_owner_id"):
                    item["origin_owner"] = owners_map.get(item["origin_owner_id"])
    
    # Filter for "selling" view: only show assets with active public listings
    if view_type == "selling":
        items = [
            item for item in items 
            if item.get("marketplace_listing") and 
               item["marketplace_listing"].get("is_public") and 
               item["marketplace_listing"].get("moderation_status") == "approved"
        ]
        total = len(items)  # Recalculate total after filtering
    
    # Get counts for all view types (for tab badges)
    # Count all (non-deleted) assets
    all_count_res = supabase.table("assets").select("id")\
        .eq("user_id", user_id).eq("is_deleted", False).execute()
    all_count = len(all_count_res.data) if all_count_res.data else 0
    
    # Count bought assets
    bought_count_res = supabase.table("assets").select("id")\
        .eq("user_id", user_id).eq("is_deleted", False).eq("is_purchased", True).execute()
    bought_count = len(bought_count_res.data) if bought_count_res.data else 0
    
    # Count selling assets (with active listings)
    selling_count_res = supabase.table("marketplace_listings").select("id")\
        .eq("seller_id", user_id).eq("resource_type", "asset")\
        .eq("is_public", True).eq("moderation_status", "approved").eq("is_deleted", False).execute()
    selling_count = len(selling_count_res.data) if selling_count_res.data else 0
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "view_type": view_type,
        "counts": {
            "all": all_count,
            "bought": bought_count,
            "selling": selling_count
        }
    }


def get_seller_asset_stats(user_id: str):
    """
    Get seller statistics for assets (for Selling view header).
    
    Returns:
        Dict with total_selling, total_sales, unique_buyers, total_revenue
    """
    # Get all active asset listings for this seller
    res = supabase.table("marketplace_listings").select(
        "id, sales_count, unique_buyers_count, total_revenue, usage_count"
    ).eq("seller_id", user_id)\
        .eq("resource_type", "asset")\
        .eq("is_public", True)\
        .eq("moderation_status", "approved")\
        .eq("is_deleted", False).execute()
    
    listings = res.data or []
    
    # Aggregate stats
    total_selling = len(listings)
    total_sales = sum(l.get("sales_count", 0) for l in listings)
    unique_buyers = sum(l.get("unique_buyers_count", 0) for l in listings)
    total_revenue = sum(l.get("total_revenue", 0) for l in listings)
    total_usage = sum(l.get("usage_count", 0) for l in listings)
    
    return {
        "total_selling": total_selling,
        "total_sales": total_sales,
        "unique_buyers": unique_buyers,
        "total_revenue": total_revenue,
        "total_usage": total_usage
    }


def get_user_deleted_assets(user_id: str, page: int = 1, limit: int = 20):
    """Get user deleted assets (last 30 days, excluding hidden from trash)"""
    from datetime import datetime, timedelta, timezone
    
    start = (page - 1) * limit
    end = start + limit - 1
    
    # Only return assets deleted in last 30 days AND not hidden from trash
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    res = supabase.table("assets").select(
        "id, name, url, thumbnail_url, deleted_at, created_at"
    ).eq("user_id", user_id).eq("is_deleted", True)\
        .eq("is_hidden_from_trash", False)\
        .gte("deleted_at", cutoff_date)\
        .order("deleted_at", desc=True).range(start, end).execute()
    
    # Get total count
    count_res = supabase.table("assets").select("id")\
        .eq("user_id", user_id).eq("is_deleted", True)\
        .eq("is_hidden_from_trash", False)\
        .gte("deleted_at", cutoff_date).execute()
    total = len(count_res.data) if count_res.data else 0
    
    return {
        "items": res.data or [],
        "total": total,
        "page": page
    }


def soft_delete_asset(asset_id: str, user_id: str):
    """Soft delete asset (stage 1)"""
    from datetime import datetime
    res = supabase.table("assets").update({
        "is_deleted": True,
        "deleted_at": datetime.utcnow().isoformat()
    }).eq("id", asset_id).eq("user_id", user_id).execute()
    if not res.data:
        raise Exception("Asset not found or permission denied")
    return True


def permanently_hide_asset(asset_id: str, user_id: str):
    """
    Permanently hide asset from trash (soft delete stage 2).
    Asset data is retained but invisible to user.
    """
    # Check if asset belongs to user and is already deleted
    check = supabase.table("assets").select("id")\
        .eq("id", asset_id).eq("user_id", user_id).eq("is_deleted", True).execute()
    
    if not check.data:
        raise Exception("Asset not found or not in trash")
    
    res = supabase.table("assets").update({
        "is_hidden_from_trash": True
    }).eq("id", asset_id).eq("user_id", user_id).execute()
    
    return res.data[0] if res.data else None


def restore_asset(asset_id: str, user_id: str):
    """Restore deleted asset"""
    check = supabase.table("assets").select("id")\
        .eq("id", asset_id).eq("user_id", user_id).eq("is_deleted", True).execute()
    
    if not check.data:
        raise Exception("Asset not found or not deleted")
    
    res = supabase.table("assets").update({
        "is_deleted": False,
        "deleted_at": None
    }).eq("id", asset_id).eq("user_id", user_id).execute()
    
    return res.data[0] if res.data else None


def get_system_resources(resource_type: str = "sticker", user_tier: str = "free"):
    """
    Get system resources (stickers, etc.)
    Filter accessible resources by user tier
    """
    res = supabase.table("system_resources").select("*").eq("type", resource_type).execute()
    
    # Filter accessible resources
    accessible = []
    for resource in res.data or []:
        allowed_tiers = resource.get("allowed_tiers", ["free", "starter", "pro"])
        if user_tier in allowed_tiers or "free" in allowed_tiers:
            resource["is_accessible"] = True
        else:
            resource["is_accessible"] = False
        accessible.append(resource)
    
    return accessible

# ==========================================
# 5. Marketplace
# ==========================================

@retry_on_network_error()
def get_marketplace_listings(
    featured: bool = False, 
    resource_type: str = None, 
    page: int = 1, 
    limit: int = 20,
    sort: str = "latest",  # 'latest' | 'popular' | 'best_selling'
    tier_filter: str = None,  # 'all' | 'free' | 'starter' | 'pro'
    price_filter: str = None,  # 'all' | 'free' | 'paid'
    mine: bool = False,
    user_id: str = None
):
    """
    Get marketplace listings (PRD Chapter 13) with automatic retry on network errors
    
    Public list defaults: moderation_status='approved' AND is_public=true AND is_deleted=false
    mine=true: Returns all statuses for owner (draft/pending/rejected/approved)
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    # Explicitly specify seller relationship
    # using profiles!marketplace_listings_seller_id_fkey
    query = supabase.table("marketplace_listings").select("*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)")
    
    if mine and user_id:
        # Seller views own listings (all statuses)
        query = query.eq("seller_id", user_id).eq("is_deleted", False)
    else:
        # Public list: Must be approved + public + not deleted (PRD rule)
        query = query.eq("is_public", True)\
            .eq("is_deleted", False)\
            .eq("moderation_status", "approved")
    
    # Resource type filter
    if resource_type:
        query = query.eq("resource_type", resource_type)
    
    # Tier filter
    if tier_filter and tier_filter != "all":
        # Use contains for allowed_tiers array
        query = query.contains("allowed_tiers", [tier_filter])
    
    # Price filter
    if price_filter == "free":
        query = query.eq("price_credits", 0)
    elif price_filter == "paid":
        query = query.gt("price_credits", 0)
    
    # Sorting
    if featured or sort == "best_selling":
        query = query.order("sales_count", desc=True)
    elif sort == "popular":
        query = query.order("usage_count", desc=True)
    else:  # latest
        query = query.order("created_at", desc=True)
    
    res = query.range(start, end).execute()
    return res.data

@retry_on_network_error()
def get_marketplace_item(listing_id: str, user_id: str = None):
    """
    Get single listing detail (PRD Chapter 13) with automatic retry on network errors
    
    Public access: Only approved + public + not deleted
    Seller access: Own listing in any status
    """
    # Explicitly specify seller relationship
    res = supabase.table("marketplace_listings").select("*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)")\
        .eq("id", listing_id).single().execute()
    
    if not res.data:
        return None
    
    listing = res.data
    
    # Check access permission
    is_seller = user_id and listing.get("seller_id") == user_id
    is_visible = listing_is_public_visible(listing)
    
    if not is_seller and not is_visible:
        return None
    
    return listing

def get_seller_listings(seller_id: str, page: int = 1, limit: int = 20):
    """Get seller's own listings"""
    start = (page - 1) * limit
    end = start + limit - 1
    
    res = supabase.table("marketplace_listings").select("*")\
        .eq("seller_id", seller_id).eq("is_deleted", False)\
        .order("created_at", desc=True).range(start, end).execute()
    return res.data

def create_listing(
    seller_id: str,
    title: str,
    description: str,
    thumbnail_url: str,
    resource_url: str,
    resource_type: str,
    price_credits: int,
    allowed_tiers: list = None,
    submit_for_review: bool = True,
    resource_id: str = None,
    version: str = "1.0",
    changelog: str = "",
    timezone: str = "UTC"
):
    """
    Create or update listing (PRD Chapter 7/8)
    
    If a listing already exists for this resource (by resource_id or resource_url),
    update it with new version; otherwise create a new listing.
    
    After submission moderation_status='pending', must be approved by admin to be listed
    
    Args:
        resource_id: The actual ID of the resource (asset.id or project.id)
        resource_url: For assets, the image URL; for projects, same as resource_id
        version: Version number (e.g., "1.0")
        changelog: What's new in this version
        timezone: IANA timezone for transaction snapshot
    """
    from datetime import datetime
    
    # Check if listing already exists for this resource
    existing_query = supabase.table("marketplace_listings").select("*")\
        .eq("seller_id", seller_id).eq("is_deleted", False)
    
    # Try to find by resource_id first (preferred), then by resource_url
    if resource_id:
        existing_query = existing_query.eq("resource_id", resource_id)
    else:
        existing_query = existing_query.eq("resource_url", resource_url)
    
    existing_res = existing_query.execute()
    existing_listing = existing_res.data[0] if existing_res.data else None
    
    if existing_listing:
        # Update existing listing with new version
        current_history = existing_listing.get("version_history") or []
        
        # Add new version to history
        new_entry = {
            "version": version,
            "changelog": changelog,
            "published_at": datetime.now().isoformat(),
        }
        current_history.append(new_entry)
        
        update_data = {
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "price_credits": price_credits,
            "allowed_tiers": allowed_tiers or ["free"],
            "version": version,
            "changelog": changelog,
            "version_history": current_history,
            "moderation_status": "pending" if submit_for_review else "draft",
            "moderation_note": None,  # Clear previous moderation note
            "is_public": True,
        }
        
        res = supabase.table("marketplace_listings").update(update_data)\
            .eq("id", existing_listing["id"]).execute()
        return res.data[0] if res.data else None
    
    # Create new listing
    version_history = [{
        "version": version,
        "changelog": changelog,
        "published_at": datetime.now().isoformat(),
    }]
    
    data = {
        "seller_id": seller_id,
        "title": title,
        "description": description,
        "thumbnail_url": thumbnail_url,
        "resource_url": resource_url,
        "resource_id": resource_id,  # Store actual resource ID
        "resource_type": resource_type,
        "price_credits": price_credits,
        "allowed_tiers": allowed_tiers or ["free"],
        "is_public": True,  # User wants public, but not visible until approved
        "is_deleted": False,
        "sales_count": 0,
        "usage_count": 0,
        "moderation_status": "pending" if submit_for_review else "draft",
        "moderation_note": None,
        "moderated_by": None,
        "moderated_at": None,
        "version": version,
        "changelog": changelog,
        "version_history": version_history,
        "timezone": timezone,  # v3.9: Snapshot timezone
    }
    res = supabase.table("marketplace_listings").insert(data).execute()
    return res.data[0]

def submit_listing_for_review(listing_id: str, seller_id: str):
    """
    Submit listing for review (PRD Chapter 8)
    
    draft -> pending
    rejected -> pending (allow resubmission after modification)
    """
    # Get listing and verify ownership
    res = supabase.table("marketplace_listings").select("*")\
        .eq("id", listing_id).eq("seller_id", seller_id).single().execute()
    
    if not res.data:
        return None
    
    listing = res.data
    current_status = listing.get("moderation_status", "draft")
    
    # Only draft or rejected can be submitted
    if current_status not in ["draft", "rejected"]:
        return {"error": f"Cannot submit listing with status '{current_status}'"}
    
    # Update status
    update_res = supabase.table("marketplace_listings").update({
        "moderation_status": "pending",
        "is_public": True
    }).eq("id", listing_id).execute()
    
    return update_res.data[0] if update_res.data else None

def unpublish_listing(listing_id: str, seller_id: str):
    """
    Unpublish listing (PRD Chapter 13)
    
    Set is_public=false, preserve history purchases and usage_count
    """
    res = supabase.table("marketplace_listings").update({
        "is_public": False
    }).eq("id", listing_id).eq("seller_id", seller_id).execute()
    
    return res.data[0] if res.data else None

def update_listing(listing_id: str, seller_id: str, updates: dict):
    """Update listing (only own listings)"""
    allowed_fields = ["title", "description", "price_credits", "is_public", "allowed_tiers"]
    data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    res = supabase.table("marketplace_listings").update(data)\
        .eq("id", listing_id).eq("seller_id", seller_id).execute()
    return res.data[0] if res.data else None

def check_user_purchase(user_id: str, listing_id: str) -> bool:
    """Check if user has purchased a listing"""
    res = supabase.table("user_purchases").select("id")\
        .eq("user_id", user_id).eq("listing_id", listing_id).execute()
    return len(res.data) > 0

def execute_purchase(
    buyer_id: str, 
    listing_id: str,
    idempotency_key: str = None,
    utm_source: str = None,
    utm_medium: str = None,
    utm_campaign: str = None,
    referral_context: str = None,
    timezone: str = "UTC"
) -> dict:
    """
    Execute purchase logic (PRD Chapter 13)
    
    Rules:
    0) Validate listing: moderation_status='approved' AND is_public=true AND is_deleted=false
    1) Validate listing.allowed_tiers vs user permissions
    2) Dedup: If already purchased return success
    3) Transaction deduct: Buyer pays price (priority monthly)
    4) Seller credit: price * 90% (to permanent)
    5) Platform fee: 10%
    6) Write user_purchases with snapshot
    
    Args:
        idempotency_key: Unique key to prevent duplicate purchases
        utm_source/utm_medium/utm_campaign: Analytics tracking
        referral_context: Where user came from ('homepage', 'search', etc.)
        timezone: IANA timezone for transaction snapshot
    
    Returns: { success: bool, message: str }
    """
    # 0. Idempotency check - prevent duplicate purchases from retries
    if idempotency_key:
        existing = supabase.table("user_purchases").select("id")\
            .eq("idempotency_key", idempotency_key).execute()
        if existing.data:
            return {"success": True, "message": "Already processed", "already_owned": True}
    
    # 1. Get listing info (must be approved + public + not deleted)
    listing_res = supabase.table("marketplace_listings").select("*")\
        .eq("id", listing_id)\
        .eq("is_public", True)\
        .eq("is_deleted", False)\
        .eq("moderation_status", "approved")\
        .single().execute()
    
    if not listing_res.data:
        return {"success": False, "message": "Listing not found or not available for purchase"}
    
    listing = listing_res.data
    price = listing.get("price_credits", 0)
    seller_id = listing.get("seller_id")
    allowed_tiers = listing.get("allowed_tiers", ["free", "starter", "pro"])
    
    # 2. Get buyer info
    buyer = get_user_profile(buyer_id)
    if not buyer:
        return {"success": False, "message": "Buyer not found"}
    
    # 3. Permission check
    if not can_access_resource(buyer, allowed_tiers):
        return {"success": False, "message": "Upgrade required to purchase this item"}
    
    # 4. Dedup check (by listing_id)
    if check_user_purchase(buyer_id, listing_id):
        return {"success": True, "message": "Already purchased", "already_owned": True}
    
    # 5. Build purchase record with snapshot (used for both free and paid)
    purchase_record = {
        "user_id": buyer_id,
        "listing_id": listing_id,
        "price_paid": price,
        # Idempotency key for duplicate prevention
        "idempotency_key": idempotency_key,
        # Snapshot - capture listing state at purchase time
        "snapshot_title": listing.get("title"),
        "snapshot_thumbnail_url": listing.get("thumbnail_url"),
        "snapshot_description": listing.get("description"),
        "snapshot_version": listing.get("version", "1.0"),
        "snapshot_resource_type": listing.get("resource_type"),
        "snapshot_resource_id": listing.get("resource_id"),
        # Analytics tracking
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "referral_context": referral_context,
        # v3.9: Timezone snapshot
        "timezone": timezone,
    }
    
    # 6. Free item handling
    if price == 0:
        purchase_record["price_paid"] = 0
        supabase.table("user_purchases").insert(purchase_record).execute()
        
        # Also create purchased item copy for free items
        _create_purchased_item_copy(buyer_id, listing, seller_id, listing_id, timezone=timezone)
        
        return {"success": True, "message": "Free item claimed"}
    
    # 6. Deduct buyer credits
    try:
        credit_deduct(buyer_id, price, "market_purchase", f"Purchase: {listing.get('title', 'Item')}", timezone=timezone)
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            return {"success": False, "message": "Insufficient credits"}
        raise e
    
    # 7. Seller credits (90%)
    if seller_id:
        seller_amount = int(price * 0.9)
        add_credits_permanent(
            seller_id, 
            seller_amount, 
            f"Sale: {listing.get('title', 'Item')}", 
            type="market_sale",
            timezone=timezone
        )
    
    # 8. Record purchase with snapshot
    supabase.table("user_purchases").insert(purchase_record).execute()
    
    # 9. Update sales count
    supabase.table("marketplace_listings").update({
        "sales_count": listing.get("sales_count", 0) + 1
    }).eq("id", listing_id).execute()
    
    # 10. Create purchased item copy in buyer's library
    _create_purchased_item_copy(buyer_id, listing, seller_id, listing_id, timezone=timezone)
    
    return {"success": True, "message": "Purchase successful"}


def _create_purchased_item_copy(buyer_id: str, listing: dict, seller_id: str, listing_id: str, timezone: str = "UTC"):
    """
    Create a copy of the purchased item in buyer's library.
    For projects: creates a new project record with is_purchased=True
    For assets: creates a new asset record with is_purchased=True
    
    Args:
        buyer_id: Buyer user ID
        listing: Listing data
        seller_id: Seller user ID
        listing_id: Listing ID
        timezone: IANA timezone for transaction snapshot
    """
    resource_type = listing.get("resource_type", "project")
    resource_url = listing.get("resource_url")  # For assets: image URL; for projects: thumbnail URL
    resource_id = listing.get("resource_id")  # The actual resource UUID (project.id or asset.id)
    
    if resource_type == "project" and resource_id:
        # Get original project data using resource_id (unified design)
        original_project = supabase.table("projects").select("*")\
            .eq("id", resource_id).single().execute()
        
        if original_project.data:
            # Create a copy for the buyer
            new_project_data = {
                "user_id": buyer_id,
                "title": original_project.data.get("title"),
                "canvas_data": original_project.data.get("canvas_data", {}),
                "thumbnail_url": original_project.data.get("thumbnail_url"),
                "is_purchased": True,
                "source_listing_id": listing_id,
                "origin_owner_id": seller_id,
                "timezone": timezone,  # v3.9: Snapshot timezone
            }
            supabase.table("projects").insert(new_project_data).execute()
            print(f"[PURCHASE] Created purchased project for buyer {buyer_id}")
    
    elif resource_type == "asset":
        # For assets, use resource_id if available, otherwise try resource_url
        original_asset_id = resource_id or resource_url
        
        if original_asset_id:
            # Get original asset data
            original_asset = supabase.table("assets").select("*")\
                .eq("id", original_asset_id).single().execute()
            
            if original_asset.data:
                # Create a reference for the buyer (same URL, different record)
                new_asset_data = {
                    "user_id": buyer_id,
                    "url": original_asset.data.get("url"),
                    "type": original_asset.data.get("type", "image"),
                    "prompt": original_asset.data.get("prompt"),
                    "description": original_asset.data.get("description"),
                    "is_purchased": True,
                    "source_listing_id": listing_id,
                    "origin_owner_id": seller_id,
                    "timezone": timezone,  # v3.9: Snapshot timezone
                }
                supabase.table("assets").insert(new_asset_data).execute()
                print(f"[PURCHASE] Created purchased asset for buyer {buyer_id}")

def get_user_purchases(user_id: str, page: int = 1, limit: int = 50):
    """Get user purchased items"""
    start = (page - 1) * limit
    end = start + limit - 1
    
    res = supabase.table("user_purchases").select("*, marketplace_listings(*)")\
        .eq("user_id", user_id)\
        .order("purchased_at", desc=True).range(start, end).execute()
    return res.data

def get_seller_stats(seller_id: str) -> dict:
    """Get seller stats (PRD Chapter 13)"""
    # Get all listings
    listings = supabase.table("marketplace_listings").select("id, sales_count, usage_count, price_credits, moderation_status")\
        .eq("seller_id", seller_id).eq("is_deleted", False).execute().data
    
    total_sales = sum(l.get("sales_count", 0) for l in listings)
    total_usage = sum(l.get("usage_count", 0) for l in listings)
    
    # Calculate total revenue (90% share)
    total_earned = 0
    for listing in listings:
        total_earned += int(listing.get("price_credits", 0) * listing.get("sales_count", 0) * 0.9)
    
    # Count by status
    status_counts = {}
    for listing in listings:
        status = listing.get("moderation_status", "draft")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "total_listings": len(listings),
        "total_sales": total_sales,
        "total_usage": total_usage,
        "total_earned_credits": total_earned,
        "status_counts": status_counts
    }

# ==========================================
# 5.1 Listing Usage (Usage Count)
# ==========================================

def record_listing_usage(listing_id: str, used_by_user_id: str, project_id: str) -> bool:
    """
    Record listing usage (PRD Chapter 9)
    
    Dedup rule: (listing_id, used_by_user_id, project_id) unique
    Same user applying same listing to same project counts once
    
    Returns: True if new usage recorded, False if already exists
    """
    # Check existence
    existing = supabase.table("listing_usages").select("id")\
        .eq("listing_id", listing_id)\
        .eq("used_by_user_id", used_by_user_id)\
        .eq("project_id", project_id).execute()
    
    if existing.data:
        return False  # Exists, no count
    
    try:
        # Insert usage record
        supabase.table("listing_usages").insert({
            "listing_id": listing_id,
            "used_by_user_id": used_by_user_id,
            "project_id": project_id
        }).execute()
        
        # Increment usage_count
        listing = supabase.table("marketplace_listings").select("usage_count")\
            .eq("id", listing_id).single().execute()
        
        if listing.data:
            current_count = listing.data.get("usage_count", 0)
            supabase.table("marketplace_listings").update({
                "usage_count": current_count + 1
            }).eq("id", listing_id).execute()
        
        return True
    except Exception as e:
        print(f"Failed to record listing usage: {e}")
        return False

def get_leaderboard(period: str = "monthly", board_type: str = "all", limit: int = 10):
    """
    Get leaderboard (PRD Chapter 9)
    
    period: 'monthly' | 'all_time'
    board_type: 'all' | 'project' | 'asset'
    
    Returns: Top 10 listings with usage_count and rank
    """
    # Explicitly specify seller relationship
    query = supabase.table("marketplace_listings").select("id, title, thumbnail_url, usage_count, resource_type, seller_id, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)")\
        .eq("is_public", True)\
        .eq("is_deleted", False)\
        .eq("moderation_status", "approved")
    
    if board_type != "all":
        query = query.eq("resource_type", board_type)
    
    query = query.order("usage_count", desc=True).limit(limit)
    
    res = query.execute()
    
    # Add rank
    leaderboard = []
    for idx, item in enumerate(res.data or []):
        item["rank"] = idx + 1
        leaderboard.append(item)
    
    return leaderboard

# ==========================================
# 6. Notification System
# ==========================================

@retry_on_network_error()
def get_user_notifications(user_id: str, unread_only: bool = False, limit: int = 20):
    """Get user notifications"""
    query = supabase.table("notifications").select("*")
    
    # Personal + Broadcast notifications
    query = query.or_(f"user_id.eq.{user_id},user_id.is.null")
    
    if unread_only:
        query = query.eq("is_read", False)
    
    res = query.order("created_at", desc=True).limit(limit).execute()
    return res.data

def mark_notification_read(notification_id: str, user_id: str):
    """Mark notification as read"""
    supabase.table("notifications").update({"is_read": True})\
        .eq("id", notification_id).execute()


def mark_all_notifications_read(user_id: str):
    """Mark all user notifications as read"""
    # Mark personal notifications
    supabase.table("notifications").update({"is_read": True})\
        .eq("user_id", user_id).eq("is_read", False).execute()
    # Note: Broadcast notifications (user_id=null) need separate handling for read status
    # Currently only handling personal notifications

def create_broadcast(title: str, content: str, target_group: str = "all"):
    """[Admin] Create broadcast notification"""
    data = {
        "user_id": None,  # NULL = Broadcast
        "target_group": target_group,
        "title": title,
        "content": content,
        "is_read": False
    }
    res = supabase.table("notifications").insert(data).execute()
    return res.data[0]


def send_notification_to_user(user_id: str, title: str, content: str, notification_type: str = "system"):
    """[Admin] Send notification to single user"""
    data = {
        "user_id": user_id,
        "target_group": None,
        "title": title,
        "content": content,
        "is_read": False
    }
    # Try adding notification_type (if supported by table)
    try:
        data["notification_type"] = notification_type
        res = supabase.table("notifications").insert(data).execute()
    except Exception as e:
        # If field doesn't exist, remove and retry
        if "notification_type" in str(e):
            del data["notification_type"]
            res = supabase.table("notifications").insert(data).execute()
        else:
            raise e
    return res.data[0] if res.data else None


def send_notification_to_users(user_ids: list, title: str, content: str, notification_type: str = "system"):
    """[Admin] Batch send notifications to multiple users"""
    notifications = []
    for user_id in user_ids:
        data = {
            "user_id": user_id,
            "target_group": None,
            "title": title,
            "content": content,
            "is_read": False
        }
        notifications.append(data)
    
    if not notifications:
        return []
    
    # Try adding notification_type (if supported by table)
    try:
        for n in notifications:
            n["notification_type"] = notification_type
        res = supabase.table("notifications").insert(notifications).execute()
    except Exception as e:
        # If field doesn't exist, remove and retry
        if "notification_type" in str(e):
            for n in notifications:
                if "notification_type" in n:
                    del n["notification_type"]
            res = supabase.table("notifications").insert(notifications).execute()
        else:
            raise e
    return res.data


def get_users_by_tier(tier: str):
    """Get all user IDs for specific tier"""
    res = supabase.table("profiles").select("id").eq("tier", tier).execute()
    return [u["id"] for u in res.data] if res.data else []


def get_all_notification_stats():
    """Get notification stats"""
    try:
        # Total notifications
        total_res = supabase.table("notifications").select("id", count="exact").execute()
        
        # Unread notifications
        unread_res = supabase.table("notifications").select("id", count="exact").eq("is_read", False).execute()
        
        # Recent 7 days notifications
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_res = supabase.table("notifications").select("id", count="exact")\
            .gte("created_at", week_ago).execute()
        
        return {
            "total": total_res.count or 0,
            "unread": unread_res.count or 0,
            "recent_7d": recent_res.count or 0
        }
    except Exception as e:
        print(f"[get_all_notification_stats] Error: {e}")
        return {
            "total": 0,
            "unread": 0,
            "recent_7d": 0
        }


def get_notification_history(page: int = 1, limit: int = 50, notification_type: str = None):
    """Get notification history"""
    try:
        query = supabase.table("notifications").select("*")
        
        # Only filter if type specified and supported
        if notification_type:
            try:
                query = query.eq("notification_type", notification_type)
            except:
                pass  # Field doesn't exist, ignore filter
        
        offset = (page - 1) * limit
        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return res.data or []
    except Exception as e:
        print(f"[get_notification_history] Error: {e}")
        return []

# ==========================================
# 7. Discounts System
# ==========================================

def get_user_discount(user_id: str, target_plan: str = None):
    """Get user valid discount"""
    query = supabase.table("user_discounts").select("*")\
        .eq("user_id", user_id)\
        .gte("valid_until", datetime.now().isoformat())
    
    if target_plan:
        query = query.eq("target_plan", target_plan)
    
    res = query.order("discount_percent", desc=True).limit(1).execute()
    return res.data[0] if res.data else None

def create_user_discount(user_id: str, discount_percent: int, valid_days: int, target_plan: str = None):
    """[Admin] Create user discount"""
    from datetime import timedelta
    valid_until = datetime.now() + timedelta(days=valid_days)
    
    data = {
        "user_id": user_id,
        "discount_percent": discount_percent,
        "valid_until": valid_until.isoformat(),
        "target_plan": target_plan
    }
    res = supabase.table("user_discounts").insert(data).execute()
    return res.data[0]

# ==========================================
# 8. Admin & Ops
# ==========================================

def log_activity(user_id: str, action: str, metadata: dict = None):
    """Log user activity"""
    supabase.table("activity_logs").insert({
        "user_id": user_id,
        "action": action,
        "metadata": metadata
    }).execute()

def create_support_ticket(user_id: str, email: str, message: str):
    """Create support ticket and send email notification"""
    # 1. Save to DB
    supabase.table("support_tickets").insert({
        "user_id": user_id,
        "email": email,
        "content": message,
        "category": "ticket_submission",
        "status": "open"
    }).execute()
    
    # 2. Send email notification to support
    try:
        send_support_email(user_id, email, message)
    except Exception as e:
        print(f"[WARNING] Failed to send support email: {e}")
        # Don't raise exception, ticket saved to DB


def send_support_email(user_id: str, user_email: str, message: str, images: list = None):
    """Send support email to support address, with image attachments support"""
    try:
        import resend
        from config import RESEND_API_KEY, SUPPORT_EMAIL, SUPPORT_EMAIL_FROM
        
        if not RESEND_API_KEY:
            print("[WARNING] RESEND_API_KEY not configured, skipping email")
            return
        
        resend.api_key = RESEND_API_KEY
        
        # Build email content
        html_content = f"""
        <h2>New Support Ticket</h2>
        <p><strong>User ID:</strong> {user_id}</p>
        <p><strong>User Email:</strong> {user_email}</p>
        <hr>
        <h3>Message Content:</h3>
        <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; white-space: pre-wrap;">{message}</pre>
        """
        
        # If images present, show in email
        if images and len(images) > 0:
            html_content += """
            <hr>
            <h3>Attached Screenshots:</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
            """
            for i, img in enumerate(images):
                # img is base64 data
                html_content += f'<img src="{img.get("data", "")}" alt="Screenshot {i+1}" style="max-width: 300px; border: 1px solid #ddd; border-radius: 5px;" />'
            html_content += "</div>"
        
        html_content += """
        <hr>
        <p style="color: #666; font-size: 12px;">This email is automatically sent by Make Decodables Support System</p>
        """
        
        email_data = {
            "from": SUPPORT_EMAIL_FROM,
            "to": SUPPORT_EMAIL,
            "subject": f"[Make Decodables] New Ticket - From {user_email}",
            "html": html_content,
            "reply_to": user_email
        }
        
        resend.Emails.send(email_data)
        
        print(f"[INFO] Support email sent to {SUPPORT_EMAIL} with {len(images) if images else 0} images")
        
    except ImportError:
        print("[WARNING] resend package not installed, skipping email")
    except Exception as e:
        print(f"[ERROR] Failed to send email via Resend: {e}")
        raise


def send_feedback_with_images(user_id: str, user_email: str, message: str, images: list = None):
    """Send feedback email (with images) to support address"""
    send_support_email(user_id, user_email, message, images)

def search_users(query: str):
    """[Admin] Search users (supports ID or Email fuzzy search)"""
    res = supabase.table("profiles").select("*")\
        .or_(f"id.eq.{query},email.ilike.%{query}%")\
        .execute()
    return res.data

def get_full_user_audit(user_id: str):
    """
    [Admin] Get full user audit view: profile, transactions, logs, tickets
    """
    # 1. Profile
    profile = get_user_profile(user_id)
    
    # 2. Credit Transactions
    txs = supabase.table("credit_transactions").select("*")\
        .eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    # 3. Activity Logs
    logs = supabase.table("activity_logs").select("*")\
        .eq("user_id", user_id).order("created_at", desc=True).limit(50).execute().data
    
    # 4. Support Tickets
    tickets = supabase.table("support_tickets").select("*")\
        .eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    # 5. Purchases
    purchases = get_user_purchases(user_id)
    
    return {
        "profile": profile,
        "transactions": txs,
        "logs": logs,
        "tickets": tickets,
        "purchases": purchases
    }

def admin_adjust_credits(user_id: str, amount: int, bucket: str, reason: str):
    """
    [Admin] Manually adjust credits
    bucket: 'monthly' | 'permanent'
    """
    profile = get_user_profile(user_id)
    if not profile:
        raise Exception("User not found")
    
    monthly = profile.get("credits_monthly", 0)
    permanent = profile.get("credits_permanent", 0)
    
    if bucket == "monthly":
        new_monthly = max(0, monthly + amount)
        supabase.table("profiles").update({"credits_monthly": new_monthly}).eq("id", user_id).execute()
        log_credit_transaction(
            user_id, amount, "monthly", new_monthly, permanent, "admin_adj", reason
        )
    else:
        new_permanent = max(0, permanent + amount)
        supabase.table("profiles").update({"credits_permanent": new_permanent}).eq("id", user_id).execute()
        log_credit_transaction(
            user_id, amount, "permanent", monthly, new_permanent, "admin_adj", reason
        )
    
    return True

# ==========================================
# 8.1 Admin Moderation (Marketplace)
# ==========================================

def admin_get_moderation_list(
    status: str = None,  # 'pending' | 'approved' | 'rejected' | 'all'
    resource_type: str = None,  # 'project' | 'asset'
    page: int = 1,
    limit: int = 20
):
    """
    [Admin] Get moderation list (PRD Chapter 16)
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    # Explicitly specify seller relationship (seller info, including user_code)
    query = supabase.table("marketplace_listings").select("*, profiles!marketplace_listings_seller_id_fkey(username, email, avatar_url, user_code, first_name, last_name)")\
        .eq("is_deleted", False)
    
    if status and status != "all":
        query = query.eq("moderation_status", status)
    
    if resource_type:
        query = query.eq("resource_type", resource_type)
    
    query = query.order("created_at", desc=True).range(start, end)
    
    res = query.execute()
    return res.data

def admin_get_moderation_detail(listing_id: str):
    """
    [Admin] Get moderation detail (PRD Chapter 16)
    """
    # Explicitly specify seller relationship (seller info)
    res = supabase.table("marketplace_listings").select("*, profiles!marketplace_listings_seller_id_fkey(username, email, avatar_url)")\
        .eq("id", listing_id).single().execute()
    
    return res.data

def admin_approve_listing(listing_id: str, admin_id: str):
    """
    [Admin] Approve listing (PRD Chapter 16)
    
    pending -> approved
    """
    from datetime import datetime
    
    res = supabase.table("marketplace_listings").update({
        "moderation_status": "approved",
        "moderated_by": admin_id,
        "moderated_at": datetime.now().isoformat()
    }).eq("id", listing_id).execute()
    
    return res.data[0] if res.data else None

def admin_reject_listing(listing_id: str, admin_id: str, reason: str):
    """
    [Admin] Reject listing (PRD Chapter 16)
    
    pending -> rejected (reason required)
    """
    from datetime import datetime
    
    if not reason or not reason.strip():
        raise Exception("Rejection reason is required")
    
    res = supabase.table("marketplace_listings").update({
        "moderation_status": "rejected",
        "moderation_note": reason,
        "moderated_by": admin_id,
        "moderated_at": datetime.now().isoformat()
    }).eq("id", listing_id).execute()
    
    return res.data[0] if res.data else None

def admin_delete_listing(listing_id: str):
    """
    [Admin] Soft delete listing (PRD Chapter 16)
    """
    res = supabase.table("marketplace_listings").update({
        "is_deleted": True
    }).eq("id", listing_id).execute()
    
    return res.data[0] if res.data else None

def admin_unpublish_listing(listing_id: str):
    """
    [Admin] Force unpublish listing (PRD Chapter 16)
    
    Set is_public=false
    """
    res = supabase.table("marketplace_listings").update({
        "is_public": False
    }).eq("id", listing_id).execute()
    
    return res.data[0] if res.data else None


# ==========================================
# 15. Admin Operation Logs (Audit)
# ==========================================

def admin_log_operation(admin_id: str, operation_type: str, target_user_id: str = None, details: str = None, reason: str = None):
    """
    [Admin] Log admin operation
    
    operation_type: 
      - credit_adjust: Credit adjustment
      - tier_change: Tier change
      - refund: Refund
      - subscription_cancel: Cancel subscription
      - subscription_downgrade: Downgrade subscription
      - listing_approve: Listing approved
      - listing_reject: Listing rejected
    """
    supabase.table("admin_operation_logs").insert({
        "admin_id": admin_id,
        "operation_type": operation_type,
        "target_user_id": target_user_id,
        "details": details,
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

def admin_get_operation_logs(
    operation_type: str = None,
    admin_id: str = None,
    target_user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    limit: int = 50
):
    """
    [Admin] Get operation logs list
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("admin_operation_logs").select(
        "*, admin:profiles!admin_operation_logs_admin_id_fkey(email), target:profiles!admin_operation_logs_target_user_id_fkey(email, user_code)"
    )
    
    if operation_type:
        query = query.eq("operation_type", operation_type)
    if admin_id:
        query = query.eq("admin_id", admin_id)
    if target_user_id:
        query = query.eq("target_user_id", target_user_id)
    if start_date:
        query = query.gte("created_at", start_date)
    if end_date:
        query = query.lte("created_at", end_date)
    
    # Get total count first
    count_query = supabase.table("admin_operation_logs").select("id", count="exact")
    if operation_type:
        count_query = count_query.eq("operation_type", operation_type)
    if start_date:
        count_query = count_query.gte("created_at", start_date)
    if end_date:
        count_query = count_query.lte("created_at", end_date)
    count_res = count_query.execute()
    total = count_res.count if count_res.count else 0
    
    # Get paginated data
    res = query.order("created_at", desc=True).range(start, end).execute()
    
    # Format return data
    logs = []
    for item in res.data or []:
        logs.append({
            "id": item.get("id"),
            "operation_type": item.get("operation_type"),
            "admin_id": item.get("admin_id"),
            "admin_email": item.get("admin", {}).get("email") if item.get("admin") else None,
            "target_user_id": item.get("target_user_id"),
            "target_user_email": item.get("target", {}).get("email") if item.get("target") else None,
            "target_user_code": item.get("target", {}).get("user_code") if item.get("target") else None,
            "details": item.get("details"),
            "reason": item.get("reason"),
            "created_at": item.get("created_at")
        })
    
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit
    }


# ==========================================
# 16. Admin User Projects (Management)
# ==========================================

def admin_get_user_projects(user_id: str, page: int = 1, limit: int = 20, include_deleted: bool = True):
    """
    [Admin] Get all projects for a specific user
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("projects").select("*").eq("user_id", user_id)
    
    if not include_deleted:
        query = query.is_("deleted_at", "null")
    
    # Get total count
    count_query = supabase.table("projects").select("id", count="exact").eq("user_id", user_id)
    if not include_deleted:
        count_query = count_query.is_("deleted_at", "null")
    count_res = count_query.execute()
    total = count_res.count if count_res.count else 0
    
    # Get paginated data
    res = query.order("created_at", desc=True).range(start, end).execute()
    
    return {
        "projects": res.data or [],
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit
    }


# ==========================================
# 17. Admin Stats & Analytics
# ==========================================

def admin_get_dashboard_stats(period: str = "month"):
    """
    [Admin] Get dashboard key stats
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    # Calculate time range
    if period == "week":
        days = 7
    elif period == "month":
        days = 30
    elif period == "quarter":
        days = 90
    else:  # year
        days = 365
    
    start_date = (now - timedelta(days=days)).isoformat()
    prev_start = (now - timedelta(days=days*2)).isoformat()
    
    # Users in current period
    users_current = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    current_users = users_current.count or 0
    
    # Users in previous period
    users_prev = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", prev_start).lt("created_at", start_date).execute()
    prev_users = users_prev.count or 0
    
    # Total users
    total_users = supabase.table("profiles").select("id", count="exact").execute()
    
    # Current period revenue (from credit_transactions payment type)
    revenue_current = supabase.table("credit_transactions").select("description")\
        .eq("bucket", "payment").gte("created_at", start_date).execute()
    
    current_revenue = 0
    for tx in revenue_current.data or []:
        desc = tx.get("description", "")
        # Parse amount (Format: "... | USD 1499")
        if "|" in desc:
            parts = desc.split("|")[-1].strip().split()
            if len(parts) >= 2:
                try:
                    current_revenue += int(parts[1]) / 100  # cents to dollars
                except:
                    pass
    
    # Previous period revenue
    revenue_prev = supabase.table("credit_transactions").select("description")\
        .eq("bucket", "payment").gte("created_at", prev_start).lt("created_at", start_date).execute()
    
    prev_revenue = 0
    for tx in revenue_prev.data or []:
        desc = tx.get("description", "")
        if "|" in desc:
            parts = desc.split("|")[-1].strip().split()
            if len(parts) >= 2:
                try:
                    prev_revenue += int(parts[1]) / 100
                except:
                    pass
    
    # Project stats
    projects_current = supabase.table("projects").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    projects_prev = supabase.table("projects").select("id", count="exact")\
        .gte("created_at", prev_start).lt("created_at", start_date).execute()
    total_projects = supabase.table("projects").select("id", count="exact").execute()
    
    # Credit usage stats
    credits_current = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", start_date).execute()
    credits_used = sum(abs(tx.get("amount", 0)) for tx in credits_current.data or [])
    
    credits_prev = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", prev_start).lt("created_at", start_date).execute()
    prev_credits = sum(abs(tx.get("amount", 0)) for tx in credits_prev.data or [])
    
    # Calculate growth rate
    def calc_growth(current, prev):
        if prev == 0:
            return 100 if current > 0 else 0
        return round((current - prev) / prev * 100, 1)
    
    return {
        "totalUsers": total_users.count or 0,
        "userGrowth": calc_growth(current_users, prev_users),
        "totalRevenue": current_revenue,
        "revenueGrowth": calc_growth(current_revenue, prev_revenue),
        "totalProjects": total_projects.count or 0,
        "projectGrowth": calc_growth(projects_current.count or 0, projects_prev.count or 0),
        "creditsUsed": credits_used,
        "creditGrowth": calc_growth(credits_used, prev_credits)
    }

def admin_get_user_growth_stats(start_date: str = None, end_date: str = None, group_by: str = "day"):
    """
    [Admin] Get user growth stats
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    # Get users registered in time range
    users = supabase.table("profiles").select("created_at")\
        .gte("created_at", start_date).lte("created_at", end_date)\
        .order("created_at").execute()
    
    # Group by date
    from collections import defaultdict
    daily_new = defaultdict(int)
    daily_active = defaultdict(int)
    
    for user in users.data or []:
        date_str = user.get("created_at", "")[:10]  # YYYY-MM-DD
        daily_new[date_str] += 1
    
    # Get active users (users with activity_logs)
    activities = supabase.table("activity_logs").select("user_id, created_at")\
        .gte("created_at", start_date).lte("created_at", end_date).execute()
    
    daily_active_users = defaultdict(set)
    for activity in activities.data or []:
        date_str = activity.get("created_at", "")[:10]
        daily_active_users[date_str].add(activity.get("user_id"))
    
    for date_str, users_set in daily_active_users.items():
        daily_active[date_str] = len(users_set)
    
    # Generate result
    result = []
    current = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        display_date = current.strftime("%b %d")
        result.append({
            "date": display_date,
            "newUsers": daily_new.get(date_str, 0),
            "activeUsers": daily_active.get(date_str, 0)
        })
        current += timedelta(days=1)
    
    return result

def admin_get_revenue_stats(start_date: str = None, end_date: str = None, group_by: str = "day"):
    """
    [Admin] Get revenue stats
    """
    from datetime import timedelta
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    # Get payment records
    payments = supabase.table("credit_transactions").select("created_at, type, description")\
        .eq("bucket", "payment").gte("created_at", start_date).lte("created_at", end_date).execute()
    
    daily_subs = defaultdict(float)
    daily_credits = defaultdict(float)
    
    for tx in payments.data or []:
        date_str = tx.get("created_at", "")[:10]
        tx_type = tx.get("type", "")
        desc = tx.get("description", "")
        
        # Parse amount
        amount = 0
        if "|" in desc:
            parts = desc.split("|")[-1].strip().split()
            if len(parts) >= 2:
                try:
                    amount = int(parts[1]) / 100  # cents to dollars
                except:
                    pass
        
        if "sub" in tx_type.lower():
            daily_subs[date_str] += amount
        else:
            daily_credits[date_str] += amount
    
    # Generate result
    result = []
    current = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        display_date = current.strftime("%b %d")
        result.append({
            "date": display_date,
            "subscriptions": round(daily_subs.get(date_str, 0), 2),
            "credits": round(daily_credits.get(date_str, 0), 2)
        })
        current += timedelta(days=1)
    
    return result

def admin_get_project_stats(start_date: str = None, end_date: str = None):
    """
    [Admin] Get project stats
    """
    try:
        from datetime import timedelta
        from collections import defaultdict
        now = datetime.now(timezone.utc)
        
        if not start_date:
            start_date = (now - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = now.isoformat()
        
        # Get project data
        projects = supabase.table("projects").select("created_at, updated_at, thumbnail_url")\
            .gte("created_at", start_date).lte("created_at", end_date).execute()
        
        daily_created = defaultdict(int)
        daily_completed = defaultdict(int)
        daily_exported = defaultdict(int)
        
        for project in projects.data or []:
            created_date = project.get("created_at", "")[:10]
            daily_created[created_date] += 1
            
            # Consider completed if thumbnail_url exists
            if project.get("thumbnail_url"):
                daily_completed[created_date] += 1
        
        # Get export records - use try/except in case activity_logs table doesn't exist
        try:
            exports = supabase.table("activity_logs").select("created_at")\
                .in_("action", ["export_pdf", "export_zip"])\
                .gte("created_at", start_date).lte("created_at", end_date).execute()
            
            for export in exports.data or []:
                date_str = export.get("created_at", "")[:10]
                daily_exported[date_str] += 1
        except Exception as e:
            logger.warning(f"Could not fetch activity_logs: {e}")
        
        # Generate result - handle date parsing more robustly
        result = []
        try:
            # Remove microseconds and handle timezone
            start_clean = start_date.split(".")[0].replace("Z", "+00:00")
            end_clean = end_date.split(".")[0].replace("Z", "+00:00")
            if "+" not in start_clean and "-" not in start_clean[-6:]:
                start_clean += "+00:00"
            if "+" not in end_clean and "-" not in end_clean[-6:]:
                end_clean += "+00:00"
            current = datetime.fromisoformat(start_clean)
            end_dt = datetime.fromisoformat(end_clean)
        except Exception as e:
            logger.warning(f"Date parsing error: {e}, using defaults")
            current = now - timedelta(days=30)
            end_dt = now
        
        while current <= end_dt:
            date_str = current.strftime("%Y-%m-%d")
            display_date = current.strftime("%b %d")
            result.append({
                "date": display_date,
                "created": daily_created.get(date_str, 0),
                "completed": daily_completed.get(date_str, 0),
                "exported": daily_exported.get(date_str, 0)
            })
            current += timedelta(days=1)
        
        return result
    except Exception as e:
        logger.error(f"Error in admin_get_project_stats: {e}")
        return []

def admin_get_credit_usage_stats(start_date: str = None, end_date: str = None):
    """
    [Admin] Get credit usage stats
    """
    from datetime import timedelta
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    # Get credit consumption records
    transactions = supabase.table("credit_transactions").select("type, amount")\
        .lt("amount", 0).gte("created_at", start_date).lte("created_at", end_date).execute()
    
    usage_by_type = defaultdict(int)
    type_labels = {
        "generation": "Image Generation",
        "text_generation": "Text Generation",
        "ocr": "OCR Scan",
        "market_purchase": "Marketplace",
        "export_pdf": "PDF Export",
        "export_zip": "ZIP Export"
    }
    
    for tx in transactions.data or []:
        tx_type = tx.get("type", "other")
        amount = abs(tx.get("amount", 0))
        label = type_labels.get(tx_type, tx_type.replace("_", " ").title())
        usage_by_type[label] += amount
    
    # Convert to list format
    result = [{"action": k, "credits": v} for k, v in sorted(usage_by_type.items(), key=lambda x: -x[1])]
    
    return result

def admin_get_tier_distribution():
    """
    [Admin] Get user tier distribution
    """
    # Count users by tier
    free_count = supabase.table("profiles").select("id", count="exact").eq("tier", "free").execute()
    starter_count = supabase.table("profiles").select("id", count="exact").eq("tier", "starter").execute()
    pro_count = supabase.table("profiles").select("id", count="exact").eq("tier", "pro").execute()
    
    return [
        {"name": "Free", "value": free_count.count or 0},
        {"name": "Starter", "value": starter_count.count or 0},
        {"name": "Pro", "value": pro_count.count or 0}
    ]

def admin_get_conversion_funnel(period: str = "month"):
    """
    [Admin] Get conversion funnel data
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    if period == "week":
        days = 7
    elif period == "month":
        days = 30
    else:  # quarter
        days = 90
    
    start_date = (now - timedelta(days=days)).isoformat()
    
    # 1. Signups
    signups = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    
    # 2. Users who created projects
    project_users = supabase.table("projects").select("user_id")\
        .gte("created_at", start_date).execute()
    unique_project_users = len(set(p.get("user_id") for p in project_users.data or []))
    
    # 3. Paid users (with payment records)
    paid_users = supabase.table("credit_transactions").select("user_id")\
        .eq("bucket", "payment").gte("created_at", start_date).execute()
    unique_paid_users = len(set(p.get("user_id") for p in paid_users.data or []))
    
    # 4. Active subscribers
    active_subs = supabase.table("profiles").select("id", count="exact")\
        .in_("tier", ["starter", "pro"]).eq("subscription_status", "active").execute()
    
    # Estimate visitors (3-4x signups)
    visitors = (signups.count or 0) * 4
    
    return [
        {"stage": "Visitors", "count": visitors},
        {"stage": "Sign Up", "count": signups.count or 0},
        {"stage": "First Project", "count": unique_project_users},
        {"stage": "Paid User", "count": unique_paid_users},
        {"stage": "Active Subscriber", "count": active_subs.count or 0}
    ]


# ==========================================
# 18. Admin AI Analysis
# ==========================================

def admin_get_ai_insights(analysis_type: str = "all"):
    """
    [Admin] Get AI insights
    Generate insights based on real data
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()
    
    insights = []
    
    # 1. Analyze project creation
    projects = supabase.table("projects").select("user_id, created_at, thumbnail_url, title")\
        .gte("created_at", start_date).execute()
    
    total_projects = len(projects.data or [])
    completed_projects = len([p for p in (projects.data or []) if p.get("thumbnail_url")])
    
    if total_projects > 0:
        completion_rate = completed_projects / total_projects * 100
        if completion_rate < 50:
            insights.append({
                "id": "1",
                "category": "user_behavior",
                "priority": "high",
                "title": "Low Project Completion Rate",
                "summary": f"Only {completion_rate:.1f}% of projects are completed. Consider simplifying the workflow.",
                "details": f"Out of {total_projects} projects created in the last 30 days, only {completed_projects} were completed.\n\nThis suggests users may be facing friction in the creation process.",
                "dataPoints": [f"{completion_rate:.1f}% completion rate", f"{total_projects} total projects", f"{completed_projects} completed"]
            })
    
    # 2. Analyze user retention
    users_30d = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    
    active_users = supabase.table("activity_logs").select("user_id")\
        .gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    unique_active = len(set(a.get("user_id") for a in active_users.data or []))
    
    total_users = supabase.table("profiles").select("id", count="exact").execute()
    if (total_users.count or 0) > 0:
        active_rate = unique_active / (total_users.count or 1) * 100
        if active_rate < 30:
            insights.append({
                "id": "2",
                "category": "retention",
                "priority": "high",
                "title": "User Activity Declining",
                "summary": f"Only {active_rate:.1f}% of users were active in the last 7 days.",
                "details": f"Out of {total_users.count} total users, only {unique_active} were active in the last week.\n\nConsider implementing re-engagement campaigns.",
                "dataPoints": [f"{active_rate:.1f}% active rate", f"{unique_active} active users", f"{total_users.count} total users"]
            })
    
    # 3. Analyze paid conversion
    paid_users = supabase.table("profiles").select("id", count="exact")\
        .in_("tier", ["starter", "pro"]).execute()
    
    if (total_users.count or 0) > 0:
        conversion_rate = (paid_users.count or 0) / (total_users.count or 1) * 100
        if conversion_rate < 5:
            insights.append({
                "id": "3",
                "category": "conversion",
                "priority": "medium",
                "title": "Low Free-to-Paid Conversion",
                "summary": f"Only {conversion_rate:.1f}% of users have upgraded to paid plans.",
                "details": f"Conversion rate is below industry average of 5-7% for SaaS products.\n\nConsider A/B testing pricing, adding trial periods, or improving the free tier value proposition.",
                "dataPoints": [f"{conversion_rate:.1f}% conversion", f"{paid_users.count} paid users", f"{total_users.count} total users"]
            })
    
    return insights

def admin_get_ai_recommendations(area: str = "all"):
    """
    [Admin] Get AI recommendations
    """
    recommendations = [
        {
            "id": "1",
            "area": "ux",
            "title": "Simplify Onboarding Flow",
            "summary": "Reduce steps from sign-up to first project creation to improve activation.",
            "impact": "+20% activation",
            "steps": [
                "Add a 'Quick Start' project selection during onboarding",
                "Pre-fill project settings with smart defaults",
                "Show progress indicators to set expectations",
                "Add tooltips for key features on first use"
            ],
            "metrics": ["Time to first project", "Onboarding completion rate", "Day 1 retention"]
        },
        {
            "id": "2",
            "area": "pricing",
            "title": "Introduce Annual Billing Option",
            "summary": "Offering 20% discount for annual subscriptions could increase LTV significantly.",
            "impact": "+35% LTV",
            "steps": [
                "Add annual billing option to pricing page",
                "Show monthly savings prominently",
                "Offer special upgrade incentives to monthly subscribers",
                "Create email campaign for existing users"
            ],
            "metrics": ["Annual subscription rate", "Average LTV", "Churn rate"]
        },
        {
            "id": "3",
            "area": "marketing",
            "title": "Create Educational Content Series",
            "summary": "Teachers discovering through content have 3x higher retention.",
            "impact": "+3x retention",
            "steps": [
                "Create 'Mini-Book Ideas' weekly blog series",
                "Develop video tutorials for common use cases",
                "Partner with teacher influencers",
                "Build SEO-optimized landing pages for specific subjects"
            ],
            "metrics": ["Organic traffic", "Content conversion rate", "User retention by source"]
        },
        {
            "id": "4",
            "area": "retention",
            "title": "Implement Re-engagement Campaigns",
            "summary": "Users who return after 7+ days have low engagement. Email campaigns could recover 15%.",
            "impact": "+15% DAU",
            "steps": [
                "Set up automated 'We miss you' email after 7 days",
                "Include personalized project suggestions",
                "Offer limited-time bonus credits for returning",
                "Add push notifications for mobile users"
            ],
            "metrics": ["DAU/MAU ratio", "Reactivation rate", "Email open rate"]
        }
    ]
    
    if area != "all":
        recommendations = [r for r in recommendations if r["area"] == area]
    
    return recommendations

def admin_get_behavior_analysis(start_date: str = None, end_date: str = None):
    """
    [Admin] Get user behavior analysis
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    
    # Active users stats
    activities = supabase.table("activity_logs").select("user_id, action, created_at")\
        .gte("created_at", start_date).execute()
    
    # Calculate avg session duration (simplified estimation)
    user_sessions = {}
    for activity in activities.data or []:
        user_id = activity.get("user_id")
        if user_id not in user_sessions:
            user_sessions[user_id] = []
        user_sessions[user_id].append(activity.get("created_at"))
    
    # Project completion rate
    projects = supabase.table("projects").select("id, thumbnail_url")\
        .gte("created_at", start_date).execute()
    total_projects = len(projects.data or [])
    completed = len([p for p in (projects.data or []) if p.get("thumbnail_url")])
    completion_rate = f"{(completed / max(total_projects, 1) * 100):.0f}%"
    
    # Feature adoption rate (users who used advanced features)
    advanced_actions = ["smart_scan", "regenerate", "export_pdf"]
    advanced_users = set()
    all_users = set()
    for activity in activities.data or []:
        all_users.add(activity.get("user_id"))
        if activity.get("action") in advanced_actions:
            advanced_users.add(activity.get("user_id"))
    
    feature_adoption = f"{(len(advanced_users) / max(len(all_users), 1) * 100):.0f}%"
    
    # Churn risk users (inactive for 14+ days)
    cutoff = (now - timedelta(days=14)).isoformat()
    all_profiles = supabase.table("profiles").select("id").execute()
    recent_active = supabase.table("activity_logs").select("user_id")\
        .gte("created_at", cutoff).execute()
    recent_active_set = set(a.get("user_id") for a in recent_active.data or [])
    
    churn_risk = len([p for p in (all_profiles.data or []) if p.get("id") not in recent_active_set])
    
    # Warnings
    warnings = []
    if churn_risk > 20:
        warnings.append(f"{churn_risk} users showing signs of churn (no activity in 14+ days)")
    
    # Check for credit usage spike
    credits_this_week = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    credits_last_week = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", (now - timedelta(days=14)).isoformat())\
        .lt("created_at", (now - timedelta(days=7)).isoformat()).execute()
    
    this_week = sum(abs(t.get("amount", 0)) for t in credits_this_week.data or [])
    last_week = sum(abs(t.get("amount", 0)) for t in credits_last_week.data or [])
    
    if last_week > 0 and this_week > last_week * 1.5:
        warnings.append("Credit usage spike detected - may need pricing adjustment")
    
    return {
        "avgSessionDuration": "5m 30s",  # Simplified return
        "completionRate": completion_rate,
        "featureAdoption": feature_adoption,
        "churnRisk": churn_risk,
        "warnings": warnings
    }


# ==========================================
# 19. User Events Tracking
# ==========================================

def log_user_event(user_id: str, event_type: str, properties: dict = None, session_id: str = None, event_id: str = None):
    """
    Log user behavioral event
    
    Args:
        user_id: User ID
        event_type: Event type string
        properties: Event properties dict
        session_id: Session ID
        event_id: Optional event ID for CAPI/sGTM deduplication (v3.19)
    """
    supabase.table("user_events").insert({
        "user_id": user_id,
        "event_type": event_type,
        "properties": properties or {},
        "session_id": session_id,
        "event_id": event_id,  # v3.19: For CAPI deduplication
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

def admin_get_user_events(
    event_type: str = None,
    user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    limit: int = 100
):
    """
    [Admin] Get user event list
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("user_events").select("*")
    
    if event_type:
        query = query.eq("event_type", event_type)
    if user_id:
        query = query.eq("user_id", user_id)
    if start_date:
        query = query.gte("created_at", start_date)
    if end_date:
        query = query.lte("created_at", end_date)
    
    res = query.order("created_at", desc=True).range(start, end).execute()
    
    return {
        "events": res.data or [],
        "page": page
    }

def admin_get_event_stats(start_date: str = None, end_date: str = None, group_by: str = "event_type"):
    """
    [Admin] Get event stats
    """
    from datetime import timedelta
    from collections import defaultdict
    now = datetime.now(timezone.utc)
    
    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = now.isoformat()
    
    events = supabase.table("user_events").select("event_type, user_id, properties")\
        .gte("created_at", start_date).lte("created_at", end_date).execute()
    
    stats = defaultdict(int)
    for event in events.data or []:
        if group_by == "event_type":
            key = event.get("event_type", "unknown")
        elif group_by == "page":
            key = event.get("properties", {}).get("page_name", "unknown")
        else:
            key = "unknown"
        stats[key] += 1
    
    return [{"key": k, "count": v} for k, v in sorted(stats.items(), key=lambda x: -x[1])]


# ===========================================
# Aggregated Stats Functions (Aggregated Stats)
# ===========================================

def get_aggregated_stats(stat_type: str, use_cache: bool = True):
    """
    Get aggregated stats
    Use Redis cache preferentially, then DB cache, calculate in real-time if not exists
    """
    from datetime import timedelta
    
    if use_cache:
        # Try Redis cache first
        cached = cache_service.get_stats(stat_type)
        if cached is not None:
            return cached
        
        # Try to get from DB cache
        try:
            res = supabase.table("aggregated_stats").select("data, updated_at")\
                .eq("stat_type", stat_type)\
                .order("date", desc=True)\
                .limit(1).execute()
            
            if res.data:
                db_cache = res.data[0]
                # Check if cache is fresh (within 1 hour)
                updated_at = db_cache.get("updated_at")
                if updated_at:
                    now = datetime.now(timezone.utc)
                    cache_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    if now - cache_time < timedelta(hours=1):
                        data = db_cache.get("data", {})
                        # Store in Redis for faster future access
                        cache_service.set_stats(stat_type, data)
                        return data
        except Exception as e:
            logger.warning(f"[Stats] Cache lookup failed: {e}")
    
    # Fall back to real-time calculation
    return None


def get_aggregated_stats_range(stat_type: str, days: int = 30):
    """
    Get aggregated stats within date range
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    
    res = supabase.table("aggregated_stats").select("date, data")\
        .eq("stat_type", stat_type)\
        .gte("date", start_date)\
        .order("date", desc=False).execute()
    
    return res.data or []


def upsert_aggregated_stats(date_str: str, stat_type: str, data: dict):
    """
    Update or insert aggregated stats data
    """
    supabase.table("aggregated_stats").upsert({
        "date": date_str,
        "stat_type": stat_type,
        "data": data,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }, on_conflict="date,stat_type").execute()
    
    # Invalidate Redis cache for this stat_type
    cache_service.invalidate_stats_cache(stat_type)


# ===========================================
# Content Reports
# ===========================================

def create_report(reporter_id: str, listing_id: str, reason: str):
    """
    Create a content report for a marketplace listing.
    
    Returns: Report data or raises Exception if duplicate
    """
    # Check if already reported (pending/reviewed)
    existing = supabase.table("content_reports").select("id")\
        .eq("reporter_id", reporter_id)\
        .eq("listing_id", listing_id)\
        .in_("status", ["pending", "reviewed"]).execute()
    
    if existing.data:
        raise Exception("You have already reported this item")
    
    # Verify listing exists
    listing = supabase.table("marketplace_listings").select("id, title")\
        .eq("id", listing_id).single().execute()
    
    if not listing.data:
        raise Exception("Listing not found")
    
    data = {
        "reporter_id": reporter_id,
        "listing_id": listing_id,
        "reason": reason,
        "status": "pending"
    }
    
    res = supabase.table("content_reports").insert(data).execute()
    return res.data[0] if res.data else None


def get_user_reports(user_id: str, page: int = 1, limit: int = 20):
    """Get reports submitted by a user."""
    start = (page - 1) * limit
    end = start + limit - 1
    
    res = supabase.table("content_reports")\
        .select("*, marketplace_listings(id, title, thumbnail_url)")\
        .eq("reporter_id", user_id)\
        .order("created_at", desc=True)\
        .range(start, end).execute()
    
    return res.data or []


def admin_get_reports(
    status: str = None,
    page: int = 1,
    limit: int = 20
):
    """
    [Admin] Get all content reports with optional filtering.
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("content_reports")\
        .select("*, marketplace_listings(id, title, thumbnail_url, seller_id, resource_type), profiles!content_reports_reporter_id_fkey(id, username, avatar_url)")
    
    if status:
        query = query.eq("status", status)
    
    res = query.order("created_at", desc=True).range(start, end).execute()
    
    return res.data or []


def admin_get_reports_count(status: str = None):
    """[Admin] Get count of reports by status."""
    query = supabase.table("content_reports").select("id", count="exact")
    
    if status:
        query = query.eq("status", status)
    
    res = query.execute()
    return res.count or 0


def admin_respond_to_report(
    report_id: str,
    admin_id: str,
    status: str,
    response: str = None
):
    """
    [Admin] Respond to a content report.
    
    Args:
        report_id: Report ID
        admin_id: Admin user ID
        status: New status ('reviewed', 'resolved', 'dismissed')
        response: Admin's response message to the reporter
    """
    if status not in ["reviewed", "resolved", "dismissed"]:
        raise Exception("Invalid status")
    
    data = {
        "status": status,
        "reviewed_by": admin_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat()
    }
    
    if response:
        data["admin_response"] = response
    
    res = supabase.table("content_reports").update(data)\
        .eq("id", report_id).execute()
    
    return res.data[0] if res.data else None


def admin_get_report_detail(report_id: str):
    """[Admin] Get detailed report information."""
    res = supabase.table("content_reports")\
        .select("*, marketplace_listings(id, title, thumbnail_url, seller_id, resource_type, description), profiles!content_reports_reporter_id_fkey(id, username, avatar_url, email)")\
        .eq("id", report_id).single().execute()
    
    return res.data


# ==========================================
# System Configuration Functions
# ==========================================

# Redis-backed cache for system configs (shared across instances)
# See services/cache/ for implementation details
#
# IMPORTANT: db_service uses a different cache key pattern than config_service
# to avoid conflicts:
# - db_service: stores raw string values (for generic system configs)
# - config_service: stores parsed dict values (for rate limit configs)

# Cache key prefix for db_service system configs (different from config_service)
# This avoids conflicts with config_service which stores parsed rate limit dicts
_DB_CONFIG_CACHE_PREFIX = "md:sysconfig:"


def _get_cached_config(key: str):
    """
    Get config from cache (string value).
    
    Note: Uses a separate cache namespace from config_service to avoid
    type conflicts (db_service stores strings, config_service stores dicts).
    """
    cache_key = f"{_DB_CONFIG_CACHE_PREFIX}{key}"
    return cache_service.get(cache_key)


def _set_cached_config(key: str, value):
    """
    Set config in cache (string value).
    """
    from .cache.cache_keys import CacheTTL
    cache_key = f"{_DB_CONFIG_CACHE_PREFIX}{key}"
    cache_service.set(cache_key, str(value) if value else "", CacheTTL.CONFIG)


def _get_cached_config_dict(key: str):
    """
    Get config dict from cache (for get_all_system_configs, get_configs_by_group).
    """
    cache_key = f"{_DB_CONFIG_CACHE_PREFIX}{key}"
    return cache_service.get_json(cache_key)


def _set_cached_config_dict(key: str, value: dict):
    """
    Set config dict in cache (for get_all_system_configs, get_configs_by_group).
    """
    from .cache.cache_keys import CacheTTL
    cache_key = f"{_DB_CONFIG_CACHE_PREFIX}{key}"
    cache_service.set_json(cache_key, value, CacheTTL.CONFIG)


def _invalidate_config_cache(key: str = None):
    """Invalidate config cache. If key is None, invalidate all."""
    if key:
        cache_key = f"{_DB_CONFIG_CACHE_PREFIX}{key}"
        cache_service.delete(cache_key)
        # Also invalidate the "all" caches
        cache_service.delete_pattern(f"{_DB_CONFIG_CACHE_PREFIX}__all__*")
        cache_service.delete_pattern(f"{_DB_CONFIG_CACHE_PREFIX}__group__*")
    else:
        cache_service.delete_pattern(f"{_DB_CONFIG_CACHE_PREFIX}*")
    
    # Also invalidate config_service cache (they may share some keys conceptually)
    cache_service.invalidate_config_cache(key)


@retry_on_network_error()
def get_system_config(key: str, default_value: str = None):
    """
    Get a single system config value by key.
    Uses in-memory cache with TTL.
    
    Args:
        key: Config key
        default_value: Default value if config not found
    
    Returns:
        Config value or default_value
    """
    # Check cache first
    cached = _get_cached_config(key)
    if cached is not None:
        return cached
    
    try:
        res = supabase.table("system_configs")\
            .select("value, value_type, is_active")\
            .eq("key", key)\
            .eq("is_active", True)\
            .single()\
            .execute()
        
        if res.data:
            value = res.data["value"]
            _set_cached_config(key, value)
            return value
    except Exception as e:
        logger.warning(f"[Config] Failed to get config {key}: {e}")
    
    return default_value


@retry_on_network_error()
def get_all_system_configs(group: str = None, include_inactive: bool = False):
    """
    Get all system configs, optionally filtered by group.
    Uses in-memory cache with TTL.
    
    Args:
        group: Optional config_group filter
        include_inactive: Include inactive configs (admin only)
    
    Returns:
        List of config objects or dict keyed by config key
    """
    cache_key = f"__all__{group or 'all'}_{include_inactive}"
    
    # Check cache first (only for public queries)
    if not include_inactive:
        cached = _get_cached_config_dict(cache_key)
        if cached is not None:
            return cached
    
    try:
        query = supabase.table("system_configs")\
            .select("key, value, value_type, config_group, description, is_active, updated_at")
        
        if not include_inactive:
            query = query.eq("is_active", True)
        
        if group:
            query = query.eq("config_group", group)
        
        res = query.order("config_group").order("key").execute()
        
        if res.data:
            # Cache as dict for easy lookup
            config_dict = {item["key"]: item for item in res.data}
            if not include_inactive:
                _set_cached_config_dict(cache_key, config_dict)
            return config_dict
    except Exception as e:
        logger.error(f"[Config] Failed to get all configs: {e}")
    
    return {}


@retry_on_network_error()
def get_configs_by_group(group: str):
    """
    Get all configs in a specific group.
    
    Args:
        group: Config group name
    
    Returns:
        Dict of key -> value
    """
    cache_key = f"__group__{group}"
    cached = _get_cached_config_dict(cache_key)
    if cached is not None:
        return cached
    
    try:
        res = supabase.table("system_configs")\
            .select("key, value, value_type")\
            .eq("config_group", group)\
            .eq("is_active", True)\
            .execute()
        
        if res.data:
            result = {item["key"]: item["value"] for item in res.data}
            _set_cached_config_dict(cache_key, result)
            return result
    except Exception as e:
        logger.warning(f"[Config] Failed to get configs for group {group}: {e}")
    
    return {}


def admin_get_system_configs(
    group: str = None,
    search: str = None,
    page: int = 1,
    limit: int = 50
):
    """
    [Admin] Get all system configs with pagination and filtering.
    
    Args:
        group: Filter by config_group
        search: Search in key or description
        page: Page number
        limit: Items per page
    
    Returns:
        Dict with items and total count
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    # Build query
    query = supabase.table("system_configs")\
        .select("*", count="exact")
    
    if group:
        query = query.eq("config_group", group)
    
    if search:
        # Search in key or description (case insensitive)
        query = query.or_(f"key.ilike.%{search}%,description.ilike.%{search}%")
    
    res = query.order("config_group").order("key").range(start, end).execute()
    
    return {
        "items": res.data or [],
        "total": res.count or 0,
        "page": page,
        "limit": limit
    }


def admin_get_config_groups():
    """
    [Admin] Get all distinct config groups.
    
    Returns:
        List of group names
    """
    try:
        res = supabase.table("system_configs")\
            .select("config_group")\
            .execute()
        
        groups = list(set(item["config_group"] for item in res.data if item.get("config_group")))
        return sorted(groups)
    except Exception as e:
        logger.error(f"[Config] Failed to get config groups: {e}")
        return []


def admin_create_system_config(
    key: str,
    value: str,
    value_type: str = "text",
    config_group: str = "general",
    description: str = None,
    admin_id: str = None
):
    """
    [Admin] Create a new system config.
    
    Args:
        key: Unique config key
        value: Config value
        value_type: Type of value ('text', 'boolean', 'json', 'number')
        config_group: Config group
        description: Description for admins
        admin_id: Admin user ID for audit
    
    Returns:
        Created config object
    """
    try:
        data = {
            "key": key,
            "value": value,
            "value_type": value_type,
            "config_group": config_group,
            "description": description,
            "is_active": True,
            "updated_by": admin_id
        }
        
        res = supabase.table("system_configs").insert(data).execute()
        
        if res.data:
            # Log audit
            _log_config_audit(key, None, value, "create", admin_id)
            # Invalidate cache
            _invalidate_config_cache()
            return res.data[0]
    except Exception as e:
        logger.error(f"[Config] Failed to create config {key}: {e}")
        raise Exception(f"Failed to create config: {str(e)}")
    
    return None


def admin_update_system_config(
    key: str,
    value: str = None,
    value_type: str = None,
    config_group: str = None,
    description: str = None,
    is_active: bool = None,
    admin_id: str = None
):
    """
    [Admin] Update an existing system config.
    
    Args:
        key: Config key to update
        value: New value (optional)
        value_type: New type (optional)
        config_group: New group (optional)
        description: New description (optional)
        is_active: Enable/disable (optional)
        admin_id: Admin user ID for audit
    
    Returns:
        Updated config object
    """
    try:
        # Get current value for audit
        current = supabase.table("system_configs")\
            .select("value")\
            .eq("key", key)\
            .single()\
            .execute()
        
        old_value = current.data["value"] if current.data else None
        
        # Build update data
        data = {"updated_by": admin_id}
        if value is not None:
            data["value"] = value
        if value_type is not None:
            data["value_type"] = value_type
        if config_group is not None:
            data["config_group"] = config_group
        if description is not None:
            data["description"] = description
        if is_active is not None:
            data["is_active"] = is_active
        
        res = supabase.table("system_configs")\
            .update(data)\
            .eq("key", key)\
            .execute()
        
        if res.data:
            # Log audit
            _log_config_audit(key, old_value, value, "update", admin_id)
            # Invalidate cache for this key
            _invalidate_config_cache(key)
            return res.data[0]
    except Exception as e:
        logger.error(f"[Config] Failed to update config {key}: {e}")
        raise Exception(f"Failed to update config: {str(e)}")
    
    return None


def admin_delete_system_config(key: str, admin_id: str = None):
    """
    [Admin] Delete a system config.
    
    Args:
        key: Config key to delete
        admin_id: Admin user ID for audit
    
    Returns:
        True if deleted
    """
    try:
        # Get current value for audit
        current = supabase.table("system_configs")\
            .select("value")\
            .eq("key", key)\
            .single()\
            .execute()
        
        old_value = current.data["value"] if current.data else None
        
        res = supabase.table("system_configs")\
            .delete()\
            .eq("key", key)\
            .execute()
        
        if res.data:
            # Log audit
            _log_config_audit(key, old_value, None, "delete", admin_id)
            # Invalidate cache
            _invalidate_config_cache(key)
            return True
    except Exception as e:
        logger.error(f"[Config] Failed to delete config {key}: {e}")
        raise Exception(f"Failed to delete config: {str(e)}")
    
    return False


def _log_config_audit(
    config_key: str,
    old_value: str,
    new_value: str,
    action: str,
    admin_id: str
):
    """
    Log config change to audit table.
    """
    try:
        supabase.table("config_audit_logs").insert({
            "config_key": config_key,
            "old_value": old_value,
            "new_value": new_value,
            "action": action,
            "changed_by": admin_id
        }).execute()
    except Exception as e:
        logger.warning(f"[Config] Failed to log audit: {e}")


def admin_get_config_audit_logs(
    config_key: str = None,
    page: int = 1,
    limit: int = 50
):
    """
    [Admin] Get config audit logs.
    
    Args:
        config_key: Filter by specific config key
        page: Page number
        limit: Items per page
    
    Returns:
        List of audit log entries
    """
    start = (page - 1) * limit
    end = start + limit - 1
    
    query = supabase.table("config_audit_logs")\
        .select("*, profiles!config_audit_logs_changed_by_fkey(id, username, avatar_url)")
    
    if config_key:
        query = query.eq("config_key", config_key)
    
    res = query.order("changed_at", desc=True).range(start, end).execute()
    
    return res.data or []


def invalidate_config_cache_api():
    """
    API endpoint helper to manually invalidate all config cache.
    Called after admin updates.
    
    Returns:
        True if successful
    """
    _invalidate_config_cache()
    return True
