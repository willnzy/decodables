"""
Analytics Tracker - Convenience functions for analytics tracking.

@module infrastructure.monitoring.analytics_tracker
@version 1.0.0

Provides convenient global functions for analytics tracking without dependency injection.
Useful for contexts where FastAPI Depends is not available:
- Domain services (GenerationService, WebhookService, etc.)
- Background tasks
- Scheduled jobs

Architecture Note:
This is a convenience layer that wraps the proper DDD AnalyticsService.
For FastAPI routes, prefer using Depends(get_analytics_service) for better testability.
"""

import logging
from typing import Optional, Dict, Any

from dependencies import get_global_analytics_service
from domains.analytics.entities import AnalyticsEvent

logger = logging.getLogger(__name__)

# Initialize global service
_analytics_service = None


def _get_service():
    """Get or initialize analytics service singleton."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = get_global_analytics_service()
    return _analytics_service


# ============================================================================
# Convenience Functions (async)
# ============================================================================

async def track_event(
    event_name: str,
    event_type: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    source: str = "server"
) -> AnalyticsEvent:
    """
    Track a single analytics event.
    
    Convenience wrapper for AnalyticsService.track_event.
    
    Args:
        event_name: Human-readable event name
        event_type: Machine event type
        user_id: Optional user ID
        session_id: Optional session ID
        properties: Optional event properties
        source: Event source (default: "server")
        
    Returns:
        AnalyticsEvent: Created event entity
        
    Example:
        await track_event(
            event_name="User Signup",
            event_type="user_signup",
            user_id="user_123",
            properties={"source": "google"}
        )
    """
    service = _get_service()
    return await service.track_event(
        event_name=event_name,
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        properties=properties,
        source=source
    )


async def track_ai_generation(
    user_id: str,
    success: bool,
    model: str,
    cost_credits: int,
    duration_ms: Optional[int] = None,
    error_code: Optional[str] = None,
    **extra_properties
) -> AnalyticsEvent:
    """
    Track AI generation event.
    
    Convenience wrapper for AnalyticsService.track_ai_generation.
    
    Args:
        user_id: User ID
        success: Whether generation succeeded
        model: AI model used
        cost_credits: Credits consumed
        duration_ms: Optional generation duration
        error_code: Optional error code if failed
        extra_properties: Additional custom properties
        
    Returns:
        AnalyticsEvent: Created event entity
        
    Example:
        await track_ai_generation(
            user_id="user_123",
            success=True,
            model="flux",
            cost_credits=5,
            duration_ms=3200
        )
    """
    service = _get_service()
    return await service.track_ai_generation(
        user_id=user_id,
        success=success,
        model=model,
        cost_credits=cost_credits,
        duration_ms=duration_ms,
        error_code=error_code,
        **extra_properties
    )


async def track_payment(
    user_id: str,
    event_name: str,
    amount_cents: Optional[int] = None,
    plan: Optional[str] = None,
    stripe_payment_id: Optional[str] = None,
    **extra_properties
) -> AnalyticsEvent:
    """
    Track payment event.
    
    Convenience wrapper for AnalyticsService.track_payment.
    
    Args:
        user_id: User ID
        event_name: Event name
        amount_cents: Optional amount in cents
        plan: Optional plan name
        stripe_payment_id: Optional Stripe payment ID
        extra_properties: Additional custom properties
        
    Returns:
        AnalyticsEvent: Created event entity
        
    Example:
        await track_payment(
            user_id="user_123",
            event_name="checkout_completed",
            amount_cents=2990,
            plan="t3"
        )
    """
    service = _get_service()
    return await service.track_payment(
        user_id=user_id,
        event_name=event_name,
        amount_cents=amount_cents,
        plan=plan,
        stripe_payment_id=stripe_payment_id,
        **extra_properties
    )


async def track_marketplace_action(
    user_id: str,
    action: str,
    listing_id: Optional[str] = None,
    **extra_properties
) -> AnalyticsEvent:
    """
    Track marketplace action.
    
    Convenience wrapper for AnalyticsService.track_marketplace_action.
    
    Args:
        user_id: User ID
        action: Action type (e.g., "view", "purchase", "publish")
        listing_id: Optional listing ID
        extra_properties: Additional custom properties
        
    Returns:
        AnalyticsEvent: Created event entity
        
    Example:
        await track_marketplace_action(
            user_id="user_123",
            action="purchase",
            listing_id="listing_456",
            price_credits=50
        )
    """
    service = _get_service()
    return await service.track_marketplace_action(
        user_id=user_id,
        action=action,
        listing_id=listing_id,
        **extra_properties
    )


async def track_project_action(
    user_id: str,
    action: str,
    project_id: Optional[str] = None,
    **extra_properties
) -> AnalyticsEvent:
    """
    Track project action.
    
    Convenience wrapper for AnalyticsService.track_project_action.
    
    Args:
        user_id: User ID
        action: Action type (e.g., "created", "updated", "deleted")
        project_id: Optional project ID
        extra_properties: Additional custom properties
        
    Returns:
        AnalyticsEvent: Created event entity
        
    Example:
        await track_project_action(
            user_id="user_123",
            action="created",
            project_id="project_789"
        )
    """
    service = _get_service()
    return await service.track_project_action(
        user_id=user_id,
        action=action,
        project_id=project_id,
        **extra_properties
    )


# ============================================================================
# Backward Compatibility Exports
# ============================================================================

# Re-export standard event types for convenience
from domains.analytics.value_objects import StandardEventTypes as AnalyticsEvents

__all__ = [
    'track_event',
    'track_ai_generation',
    'track_payment',
    'track_marketplace_action',
    'track_project_action',
    'AnalyticsEvents',
]
