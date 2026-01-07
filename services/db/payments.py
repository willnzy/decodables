"""
Database Payments - Payment record operations

@module services.db.payments
@version 3.24
"""

import logging
from datetime import datetime, timezone

from core.database import supabase, retry_on_network_error

logger = logging.getLogger(__name__)


@retry_on_network_error()
def log_payment_record(user_id: str, amount: float, currency: str, payment_type: str,
                       stripe_payment_id: str = None, metadata: dict = None, tz: str = "UTC"):
    """Log payment record."""
    if not supabase:
        return None
    
    result = supabase.table("payment_records").insert({
        "user_id": user_id,
        "amount": amount,
        "currency": currency,
        "payment_type": payment_type,
        "stripe_payment_id": stripe_payment_id,
        "metadata": metadata or {},
        "timezone": tz,
        "status": "completed",
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def get_user_payments(user_id: str, page: int = 1, limit: int = 20):
    """Get user payment records."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    result = supabase.table("payment_records").select("*")\
        .eq("user_id", user_id).order("created_at", desc=True)\
        .range(offset, offset + limit - 1).execute()
    
    return result.data or []


@retry_on_network_error()
def admin_get_all_payments(page: int = 1, limit: int = 50, user_id: str = None,
                           payment_type: str = None):
    """Admin get all payment records."""
    if not supabase:
        return {"items": [], "total": 0}
    
    offset = (page - 1) * limit
    query = supabase.table("payment_records").select("*, profiles(email, username)", count="exact")
    
    if user_id:
        query = query.eq("user_id", user_id)
    if payment_type:
        query = query.eq("payment_type", payment_type)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return {"items": result.data or [], "total": result.count or 0}


@retry_on_network_error()
def get_payment_by_stripe_id(stripe_payment_id: str):
    """Get payment by Stripe ID."""
    if not supabase:
        return None
    
    result = supabase.table("payment_records").select("*")\
        .eq("stripe_payment_id", stripe_payment_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def update_payment_status(payment_id: str, status: str, metadata: dict = None):
    """Update payment status."""
    if not supabase:
        return None
    
    update_data = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if metadata:
        update_data["metadata"] = metadata
    
    result = supabase.table("payment_records").update(update_data)\
        .eq("id", payment_id).execute()
    
    return result.data[0] if result.data else None


# ==========================================
# Revenue Statistics
# ==========================================

@retry_on_network_error()
def admin_get_revenue_stats(start_date: str = None, end_date: str = None, group_by: str = "day"):
    """Get revenue statistics."""
    if not supabase:
        return {}
    
    from datetime import timedelta
    
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = datetime.now(timezone.utc).isoformat()
    
    result = supabase.table("payment_records").select("amount, created_at, payment_type")\
        .gte("created_at", start_date).lte("created_at", end_date)\
        .eq("status", "completed").execute()
    
    total = sum(p.get("amount", 0) for p in (result.data or []))
    
    by_type = {}
    for p in (result.data or []):
        pt = p.get("payment_type", "unknown")
        by_type[pt] = by_type.get(pt, 0) + p.get("amount", 0)
    
    # Group by date
    by_date = {}
    for p in (result.data or []):
        date_str = p.get("created_at", "")[:10]
        by_date[date_str] = by_date.get(date_str, 0) + p.get("amount", 0)
    
    return {
        "total": total,
        "by_type": by_type,
        "by_date": [{"date": k, "amount": v} for k, v in sorted(by_date.items())],
        "transaction_count": len(result.data or []),
    }
