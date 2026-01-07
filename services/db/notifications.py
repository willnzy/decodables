"""
Database Notifications - Notification operations

@module services.db.notifications
@version 3.24
"""

import logging
from datetime import datetime, timezone

from core.database import supabase, retry_on_network_error

logger = logging.getLogger(__name__)


@retry_on_network_error()
def get_user_notifications(user_id: str, unread_only: bool = False, limit: int = 20):
    """Get user notifications."""
    if not supabase:
        return []
    
    query = supabase.table("notifications").select("*").eq("user_id", user_id)
    
    if unread_only:
        query = query.eq("is_read", False)
    
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


@retry_on_network_error()
def mark_notification_read(notification_id: str, user_id: str):
    """Mark notification as read."""
    if not supabase:
        return None
    
    result = supabase.table("notifications").update({"is_read": True})\
        .eq("id", notification_id).eq("user_id", user_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def mark_all_notifications_read(user_id: str):
    """Mark all notifications as read."""
    if not supabase:
        return None
    
    supabase.table("notifications").update({"is_read": True}).eq("user_id", user_id).execute()
    return True


@retry_on_network_error()
def create_broadcast(title: str, content: str, target_group: str = "all"):
    """Create broadcast notification."""
    if not supabase:
        return None
    
    result = supabase.table("broadcasts").insert({
        "title": title,
        "content": content,
        "target_group": target_group,
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def send_notification_to_user(user_id: str, title: str, content: str, 
                              notification_type: str = "system"):
    """Send notification to single user."""
    if not supabase:
        return None
    
    result = supabase.table("notifications").insert({
        "user_id": user_id,
        "title": title,
        "content": content,
        "type": notification_type,
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def send_notification_to_users(user_ids: list, title: str, content: str,
                               notification_type: str = "system"):
    """Send notification to multiple users."""
    if not supabase or not user_ids:
        return []
    
    records = [
        {
            "user_id": uid,
            "title": title,
            "content": content,
            "type": notification_type,
        }
        for uid in user_ids
    ]
    
    result = supabase.table("notifications").insert(records).execute()
    return result.data or []


@retry_on_network_error()
def get_all_notification_stats():
    """Get notification statistics."""
    if not supabase:
        return {}
    
    total = supabase.table("notifications").select("id", count="exact").execute()
    unread = supabase.table("notifications").select("id", count="exact")\
        .eq("is_read", False).execute()
    
    return {
        "total": total.count or 0,
        "unread": unread.count or 0,
    }


@retry_on_network_error()
def get_notification_history(page: int = 1, limit: int = 50, notification_type: str = None):
    """Get notification history (admin)."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    query = supabase.table("notifications").select("*")
    
    if notification_type:
        query = query.eq("type", notification_type)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return result.data or []
