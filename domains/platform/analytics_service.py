"""
Analytics Service - Server-Side Event Tracking (v3.11)
======================================================

This module provides server-side analytics tracking for FastAPI.
Use this for tracking important backend events that shouldn't rely on client-side tracking.

IMPORTANT: This is separate from activity_logs!
- analytics_events: High-volume behavioral data for product insights (this module)
- activity_logs: Security audit trail for admin/user visibility (existing log_activity)

Table: analytics_events (see migrations/v3.11_analytics_events.sql)

Usage:
    from analytics_service import track_event, track_event_async, AnalyticsEvents
    
    # Synchronous (fire-and-forget with thread pool)
    track_event(
        event_name=AnalyticsEvents.AI_GENERATE_SUCCESS,
        user_id="user_123",
        properties={"model": "flux", "cost_credits": 5, "duration_ms": 3200}
    )
    
    # Async (for async contexts)
    await track_event_async(
        event_name=AnalyticsEvents.CHECKOUT_COMPLETED,
        user_id="user_123", 
        properties={"amount_cents": 2990, "plan": "t3"}
    )
    
    # Convenience functions
    track_ai_generation(user_id, success=True, model="flux", cost_credits=5)
    track_payment(user_id, "checkout_completed", amount_cents=2990, plan="t3")

Architecture:
    - Uses thread pool for non-blocking writes in sync contexts
    - Direct Supabase insert for async contexts
    - Automatic context enrichment (source=server, timestamp)
    - Fire-and-forget by default (won't block API response)
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import threading

# Thread pool for fire-and-forget tracking
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="analytics_")
_logger = logging.getLogger(__name__)

# Import Supabase client
try:
    from .db_service import supabase
except ImportError:
    try:
        # Fallback for direct script execution
        from infrastructure.db_compat import supabase
    except ImportError:
        supabase = None
        _logger.warning("Supabase client not available for analytics")


# ==========================================
# Event Names Constants
# ==========================================

class AnalyticsEvents:
    """Standard event names for consistency."""
    
    # Page Views
    PAGE_VIEW = "page_view"
    
    # User Actions
    BTN_CLICK = "btn_click"
    FORM_SUBMIT = "form_submit"
    SEARCH = "search"
    
    # Project Actions
    PROJECT_CREATED = "project_created"
    PROJECT_OPENED = "project_opened"
    PROJECT_SAVED = "project_saved"
    PROJECT_EXPORTED = "project_exported"
    PROJECT_DUPLICATED = "project_duplicated"
    PROJECT_DELETED = "project_deleted"
    
    # AI Features
    AI_GENERATE_STARTED = "ai_generate_started"
    AI_GENERATE_SUCCESS = "ai_generate_success"
    AI_GENERATE_FAILED = "ai_generate_failed"
    AI_ENHANCE_PROMPT = "ai_enhance_prompt"
    AI_OCR_SUCCESS = "ai_ocr_success"
    AI_OCR_FAILED = "ai_ocr_failed"
    
    # Marketplace
    MARKETPLACE_VIEW = "marketplace_view"
    MARKETPLACE_PURCHASE = "marketplace_purchase"
    MARKETPLACE_PUBLISH = "marketplace_publish"
    MARKETPLACE_UNPUBLISH = "marketplace_unpublish"
    
    # Auth
    USER_SIGNED_UP = "user_signed_up"
    USER_SIGNED_IN = "user_signed_in"
    USER_SIGNED_OUT = "user_signed_out"
    
    # Payments
    CHECKOUT_STARTED = "checkout_started"
    CHECKOUT_COMPLETED = "checkout_completed"
    SUBSCRIPTION_CHANGED = "subscription_changed"
    CREDITS_PURCHASED = "credits_purchased"
    CREDITS_DEDUCTED = "credits_deducted"
    
    # Assets
    ASSET_UPLOADED = "asset_uploaded"
    ASSET_DELETED = "asset_deleted"
    ASSET_SAVED_TO_LIBRARY = "asset_saved_to_library"


# ==========================================
# Core Tracking Functions
# ==========================================

def _insert_event(
    event_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    anonymous_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,  # v3.19: For CAPI/sGTM deduplication
) -> bool:
    """
    Internal function to insert event into database.
    Returns True if successful, False otherwise.
    
    Args:
        event_id: Optional event ID for CAPI/sGTM deduplication. 
                  If not provided, auto-generated for server-side events.
    """
    if supabase is None:
        _logger.warning(f"Analytics: Supabase not available, skipping event: {event_name}")
        return False
    
    try:
        # Build event data
        # v3.19: Include event_id for CAPI/sGTM deduplication
        generated_event_id = event_id or str(uuid.uuid4())
        
        event_data = {
            "event_name": event_name,
            "event_id": generated_event_id,  # v3.19: For CAPI deduplication
            "user_id": user_id,
            "session_id": session_id or str(uuid.uuid4()),  # Generate if not provided
            "anonymous_id": anonymous_id,
            "properties": properties or {},
            "context": {
                "source": "server",
                "timestamp_server": datetime.now(timezone.utc).isoformat(),
                **(context or {})
            },
            "source": "server",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Insert into database
        result = supabase.table("analytics_events").insert(event_data).execute()
        
        if result.data:
            _logger.debug(f"Analytics: Tracked event '{event_name}' for user '{user_id}'")
            return True
        else:
            _logger.warning(f"Analytics: Failed to insert event '{event_name}'")
            return False
            
    except Exception as e:
        _logger.error(f"Analytics: Error tracking event '{event_name}': {e}")
        return False


def track_event(
    event_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    blocking: bool = False,
    event_id: Optional[str] = None,  # v3.19: For CAPI/sGTM deduplication
) -> None:
    """
    Track an analytics event (fire-and-forget by default).
    
    Args:
        event_name: Event type (use AnalyticsEvents constants)
        user_id: User ID (optional for anonymous events)
        session_id: Browser session ID (optional, auto-generated if not provided)
        properties: Event-specific data
        context: Additional context (IP, user agent, etc.)
        blocking: If True, wait for database write to complete
        event_id: Optional event ID for CAPI/sGTM deduplication (v3.19)
    
    Example:
        track_event(
            AnalyticsEvents.AI_GENERATE_SUCCESS,
            user_id="user_123",
            properties={"model": "flux", "cost_credits": 5, "duration_ms": 3200}
        )
    """
    if blocking:
        _insert_event(event_name, user_id, session_id, None, properties, context, event_id)
    else:
        # Fire-and-forget: submit to thread pool
        _executor.submit(
            _insert_event,
            event_name, user_id, session_id, None, properties, context, event_id
        )


async def track_event_async(
    event_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,  # v3.19: For CAPI/sGTM deduplication
) -> bool:
    """
    Track an analytics event asynchronously.
    
    Use this in async contexts (async def handlers).
    Returns True if successful.
    
    Args:
        event_id: Optional event ID for CAPI/sGTM deduplication (v3.19)
    
    Example:
        await track_event_async(
            AnalyticsEvents.CHECKOUT_COMPLETED,
            user_id="user_123",
            properties={"amount": 1999, "plan": "t3"}
        )
    """
    import asyncio
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        lambda: _insert_event(event_name, user_id, session_id, None, properties, context, event_id)
    )


def track_event_batch(events: list) -> int:
    """
    Track multiple events in a single database call.
    
    Args:
        events: List of event dicts with keys: event_name, user_id, session_id, properties, context
    
    Returns:
        Number of events successfully inserted
    
    Example:
        track_event_batch([
            {"event_name": "page_view", "user_id": "user_123", "properties": {"page": "/dashboard"}},
            {"event_name": "btn_click", "user_id": "user_123", "properties": {"button": "create"}},
        ])
    """
    if supabase is None:
        _logger.warning("Analytics: Supabase not available for batch insert")
        return 0
    
    try:
        batch_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Prepare events for batch insert
        prepared_events = []
        for event in events:
            prepared_events.append({
                "event_name": event.get("event_name"),
                "user_id": event.get("user_id"),
                "session_id": event.get("session_id") or str(uuid.uuid4()),
                "anonymous_id": event.get("anonymous_id"),
                "properties": event.get("properties", {}),
                "context": {
                    "source": "server",
                    "timestamp_server": timestamp,
                    **(event.get("context", {}))
                },
                "source": "server",
                "batch_id": batch_id,
                "created_at": timestamp,
            })
        
        # Batch insert
        result = supabase.table("analytics_events").insert(prepared_events).execute()
        
        inserted_count = len(result.data) if result.data else 0
        _logger.debug(f"Analytics: Batch inserted {inserted_count} events")
        return inserted_count
        
    except Exception as e:
        _logger.error(f"Analytics: Batch insert failed: {e}")
        return 0


# ==========================================
# Convenience Functions for Common Events
# ==========================================

def track_ai_generation(
    user_id: str,
    success: bool,
    model: str,
    cost_credits: int,
    duration_ms: Optional[int] = None,
    error_code: Optional[str] = None,
    extra_properties: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Track AI image generation event.
    
    Example:
        track_ai_generation(
            user_id="user_123",
            success=True,
            model="flux-schnell",
            cost_credits=5,
            duration_ms=3200
        )
    """
    event_name = AnalyticsEvents.AI_GENERATE_SUCCESS if success else AnalyticsEvents.AI_GENERATE_FAILED
    
    properties = {
        "model": model,
        "cost_credits": cost_credits,
    }
    
    if duration_ms is not None:
        properties["duration_ms"] = duration_ms
    
    if error_code is not None:
        properties["error_code"] = error_code
    
    if extra_properties:
        properties.update(extra_properties)
    
    track_event(event_name, user_id=user_id, properties=properties)


def track_payment(
    user_id: str,
    event_type: str,
    amount_cents: int,
    currency: str = "usd",
    plan: Optional[str] = None,
    stripe_payment_id: Optional[str] = None,
    extra_properties: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Track payment-related event.
    
    Args:
        event_type: 'checkout_started', 'checkout_completed', 'subscription_changed', 'credits_purchased'
    
    Example:
        track_payment(
            user_id="user_123",
            event_type="checkout_completed",
            amount_cents=2990,
            plan="t3",
            stripe_payment_id="pi_xxx"
        )
    """
    properties = {
        "amount_cents": amount_cents,
        "currency": currency,
    }
    
    if plan:
        properties["plan"] = plan
    
    if stripe_payment_id:
        properties["stripe_payment_id"] = stripe_payment_id
    
    if extra_properties:
        properties.update(extra_properties)
    
    track_event(event_type, user_id=user_id, properties=properties)


def track_marketplace_action(
    user_id: str,
    action: str,
    listing_id: str,
    resource_type: str,
    price_credits: Optional[int] = None,
    extra_properties: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Track marketplace action.
    
    Args:
        action: 'view', 'purchase', 'publish', 'unpublish'
    
    Example:
        track_marketplace_action(
            user_id="user_123",
            action="purchase",
            listing_id="listing_456",
            resource_type="asset",
            price_credits=50
        )
    """
    event_map = {
        "view": AnalyticsEvents.MARKETPLACE_VIEW,
        "purchase": AnalyticsEvents.MARKETPLACE_PURCHASE,
        "publish": AnalyticsEvents.MARKETPLACE_PUBLISH,
        "unpublish": AnalyticsEvents.MARKETPLACE_UNPUBLISH,
    }
    
    event_name = event_map.get(action, f"marketplace_{action}")
    
    properties = {
        "listing_id": listing_id,
        "resource_type": resource_type,
    }
    
    if price_credits is not None:
        properties["price_credits"] = price_credits
    
    if extra_properties:
        properties.update(extra_properties)
    
    track_event(event_name, user_id=user_id, properties=properties)


def track_project_action(
    user_id: str,
    action: str,
    project_id: str,
    extra_properties: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Track project action.
    
    Args:
        action: 'created', 'opened', 'saved', 'exported', 'duplicated', 'deleted'
    
    Example:
        track_project_action(
            user_id="user_123",
            action="exported",
            project_id="proj_456",
            extra_properties={"format": "pdf"}
        )
    """
    event_map = {
        "created": AnalyticsEvents.PROJECT_CREATED,
        "opened": AnalyticsEvents.PROJECT_OPENED,
        "saved": AnalyticsEvents.PROJECT_SAVED,
        "exported": AnalyticsEvents.PROJECT_EXPORTED,
        "duplicated": AnalyticsEvents.PROJECT_DUPLICATED,
        "deleted": AnalyticsEvents.PROJECT_DELETED,
    }
    
    event_name = event_map.get(action, f"project_{action}")
    
    properties = {
        "project_id": project_id,
    }
    
    if extra_properties:
        properties.update(extra_properties)
    
    track_event(event_name, user_id=user_id, properties=properties)


# ==========================================
# Cleanup on shutdown
# ==========================================

def shutdown_analytics():
    """
    Graceful shutdown - wait for pending events to be sent.
    Call this during application shutdown.
    """
    _logger.info("Analytics: Shutting down, waiting for pending events...")
    _executor.shutdown(wait=True, cancel_futures=False)
    _logger.info("Analytics: Shutdown complete")


# Register shutdown handler
import atexit
atexit.register(shutdown_analytics)
