"""
Revenue Statistics Aggregators

@module scheduled_tasks.aggregators.revenue_stats
@version 3.24
"""

from datetime import datetime, timedelta, timezone
from .base import log, get_supabase, upsert_stats


def aggregate_daily_revenue():
    """Aggregate daily revenue statistics."""
    log("💰 Starting daily revenue aggregation...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        payments = supabase.table("credit_transactions").select("type, description")\
            .eq("bucket", "payment")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        subscription_revenue = 0.0
        credits_revenue = 0.0
        
        for tx in payments.data or []:
            tx_type = tx.get("type", "")
            desc = tx.get("description", "")
            
            amount = 0
            if "|" in desc:
                parts = desc.split("|")[-1].strip().split()
                if len(parts) >= 2:
                    try:
                        amount = int(parts[1]) / 100
                    except (ValueError, TypeError):
                        pass
            
            if "sub" in tx_type.lower():
                subscription_revenue += amount
            else:
                credits_revenue += amount
        
        upsert_stats("daily_revenue", {
            "subscriptions": round(subscription_revenue, 2),
            "credits": round(credits_revenue, 2),
            "total": round(subscription_revenue + credits_revenue, 2)
        }, date)
    
    log("✅ Daily revenue complete")


def aggregate_subscription_events():
    """Aggregate subscription events (upgrades, downgrades, cancels)."""
    log("📊 Starting subscription events...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        events_data = {"upgrades": 0, "downgrades": 0, "cancellations": 0, "renewals": 0}
        
        # Count subscription-related credit transactions
        txs = supabase.table("credit_transactions").select("type")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        for tx in txs.data or []:
            tx_type = tx.get("type", "").lower()
            if "upgrade" in tx_type or tx_type in ("sub_grant", "subscription_grant"):  # Phase 2: support both old+new
                events_data["upgrades"] += 1
            elif "downgrade" in tx_type:
                events_data["downgrades"] += 1
            elif "cancel" in tx_type:
                events_data["cancellations"] += 1
            elif "renew" in tx_type or "renewal" in tx_type:
                events_data["renewals"] += 1
        
        upsert_stats("subscription_events", events_data, date)
    
    log("✅ Subscription events complete")
