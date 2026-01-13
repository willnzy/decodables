"""
Analytics Service - Domain service for analytics events processing.

@module domains.analytics.service
@version 2.0.0

Unified analytics service supporting:
1. Frontend batch events (process_and_save_events) - for /api/v2/user/analytics/events
2. Backend server-side tracking (track_event, track_ai_generation, etc.) - for domain services

Architecture: Complete DDD implementation with Entity and Repository pattern.
"""

import logging
import uuid
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone

from .entities import AnalyticsEvent
from .repository import IAnalyticsRepository
from .value_objects import ACTIVITY_LOG_EVENT_MAPPING, USER_EVENT_TYPES

logger = logging.getLogger(__name__)


# Backward compatibility: import from value_objects
ACTIVITY_LOG_EVENTS = ACTIVITY_LOG_EVENT_MAPPING


class AnalyticsService:
    """
    Domain service for analytics events processing.

    Responsibilities:
    - Enrich events with server-side context
    - Build batch data for repository insertion
    - Coordinate event logging across multiple tables
    """

    def __init__(self, analytics_events_repo: IAnalyticsRepository):
        """
        Initialize service with repository.

        Args:
            analytics_events_repo: IAnalyticsRepository implementation
        """
        self._repo = analytics_events_repo

    async def process_and_save_events(
        self,
        events: List[Dict[str, Any]],
        user_id: Optional[str],
        location_info: Dict[str, str],
        user_agent: str,
        accept_language: str,
    ) -> Tuple[int, int]:
        """
        Process analytics events and save to database.

        Args:
            events: List of event dictionaries from client
            user_id: User ID (None for anonymous)
            location_info: IP/country/city/region info
            user_agent: User agent string
            accept_language: Accept-Language header

        Returns:
            Tuple of (requested count, inserted count)
        """
        client_ip = location_info.get("ip", "unknown")

        # Build batch data (no DB calls)
        user_event_rows, analytics_event_rows, activity_rows = self._build_batch_data(
            events, user_id, location_info, user_agent, accept_language
        )

        # Batch INSERT (3 DB calls max)
        user_events_inserted, analytics_events_inserted, activity_logs_inserted = (
            await self._repo.batch_insert_all(
                user_event_rows, analytics_event_rows, activity_rows
            )
        )

        # At least one table must succeed (preferably analytics_events)
        total_inserted = max(user_events_inserted, analytics_events_inserted)

        logger.info(
            f"[AnalyticsService] Processed {len(events)} events: "
            f"user_events={user_events_inserted}, "
            f"analytics_events={analytics_events_inserted}, "
            f"activity_logs={activity_logs_inserted}"
        )

        return len(events), total_inserted

    def _build_batch_data(
        self,
        events: List[Dict[str, Any]],
        user_id: Optional[str],
        location_info: Dict[str, str],
        user_agent: str,
        accept_language: str,
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Build batch data for insertion (no DB calls).

        Args:
            events: List of event dictionaries
            user_id: User ID
            location_info: IP/country/city/region info
            user_agent: User agent string
            accept_language: Accept-Language header

        Returns:
            Tuple of (user_event_rows, analytics_event_rows, activity_rows)
        """
        user_event_rows = []
        analytics_event_rows = []
        activity_rows = []

        client_ip = location_info.get("ip", "unknown")

        for event in events:
            env_info = event.get("env", {})
            properties = event.get("properties", {})
            event_type = event.get("event_type", "")
            event_level = event.get("event_level")
            timestamp = event.get("timestamp")
            session_id = event.get("session_id")

            # Generate event_id if not provided
            event_id = event.get("event_id") or str(uuid.uuid4())

            # Enrich properties with server-side info
            # Use __ prefix to prevent client from overwriting server fields
            enriched_properties = {
                **properties,  # Client properties (already validated by Pydantic)
                "__server_ip": client_ip,
                "__server_country": location_info.get("country_code"),
                "__server_city": location_info.get("city"),
                "__server_region": location_info.get("region"),
                "__server_user_agent": user_agent,
                "__server_accept_language": accept_language,
                "__client_browser": env_info.get("browser"),
                "__client_os": env_info.get("os"),
                "__client_device_type": env_info.get("device_type"),
                "__client_timezone": env_info.get("timezone"),
                "__client_timezone_offset": env_info.get("timezone_offset"),
                "__client_language": env_info.get("language"),
                "__client_connection_type": env_info.get("connection_type"),
            }

            # Build user_events row (only for authenticated users with valid event types)
            # 注意: user_events 表使用 event_data (JSONB), 不是 properties
            # 注意: user_events 表的 user_id 是 NOT NULL，所以匿名事件不能插入
            # 注意: user_events 表有 event_type 约束，只允许特定类型
            if user_id and event_type in USER_EVENT_TYPES:
                user_event_rows.append({
                    "user_id": user_id,
                    "event_type": event_type,
                    "event_data": enriched_properties,
                    "session_id": session_id,
                })

            # Build analytics_events row
            # 注意: analytics_events 表需要 event_name (NOT NULL) 和 event_type
            # 注意: analytics_events 表使用 properties 和 context (JSONB), 不是 event_data
            context_data = {
                "event_level": event_level,
                "timestamp": timestamp,
                "env": env_info,
                "user_properties": event.get("user_properties", {}),
            }
            # event_name 可以从 event 中获取，或使用 event_type 作为默认值
            event_name = event.get("event_name") or event.get("name") or event_type
            analytics_event_rows.append({
                "user_id": user_id,  # 可以为 null (匿名事件)
                "event_type": event_type,
                "event_name": event_name,  # 必填字段
                "event_id": event_id,
                "properties": enriched_properties,
                "context": context_data,
                "session_id": session_id,
            })

            # Build activity_logs row (only for key events with user_id)
            if user_id and event_type in ACTIVITY_LOG_EVENTS:
                activity_rows.append({
                    "user_id": user_id,
                    "action": ACTIVITY_LOG_EVENTS[event_type],
                    "metadata": enriched_properties,
                })

        return user_event_rows, analytics_event_rows, activity_rows
    
    # ========================================================================
    # Backend Server-Side Tracking Methods (v2.0)
    # ========================================================================
    
    async def track_event(
        self,
        event_name: str,
        event_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source: str = "server"
    ) -> AnalyticsEvent:
        """
        Track a single analytics event (backend server-side tracking).
        
        Business rules:
        - Normalize event names and types (lowercase)
        - Validate event structure
        - Auto-generate event_id
        - Fire-and-forget (no blocking)
        
        Args:
            event_name: Human-readable event name (e.g., "User Signup")
            event_type: Machine event type (e.g., "user_signup")
            user_id: Optional user ID
            session_id: Optional session ID
            properties: Optional event properties
            source: Event source (default: "server")
            
        Returns:
            AnalyticsEvent: Created event entity
            
        Example:
            event = await analytics.track_event(
                event_name="AI Generation Success",
                event_type="ai_generate_success",
                user_id="user_123",
                properties={"model": "flux", "cost_credits": 5}
            )
        """
        # Create entity (applies business rules)
        event = AnalyticsEvent(
            event_name=event_name,
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            properties=properties or {},
            source=source
        )
        
        # Persist (fire-and-forget, log errors but don't fail)
        try:
            await self._repo.save(event)
            logger.info(
                f"[Analytics] Tracked event: {event_name} (type={event_type}, user={user_id})"
            )
        except Exception as e:
            logger.error(
                f"[Analytics] Failed to track event {event_name}: {e}",
                exc_info=True,
                extra={
                    "event_name": event_name,
                    "event_type": event_type,
                    "user_id": user_id
                }
            )
            # Business decision: Analytics failures should not affect main flow
        
        return event
    
    async def track_ai_generation(
        self,
        user_id: str,
        success: bool,
        model: str,
        cost_credits: int,
        duration_ms: Optional[int] = None,
        error_code: Optional[str] = None,
        **extra_properties
    ) -> AnalyticsEvent:
        """
        Convenience method: Track AI generation event.
        
        Args:
            user_id: User ID
            success: Whether generation succeeded
            model: AI model used (e.g., "flux", "dall-e-3")
            cost_credits: Credits consumed
            duration_ms: Optional generation duration in milliseconds
            error_code: Optional error code if failed
            extra_properties: Additional custom properties
            
        Returns:
            AnalyticsEvent: Created event entity
            
        Example:
            await analytics.track_ai_generation(
                user_id="user_123",
                success=True,
                model="flux",
                cost_credits=5,
                duration_ms=3200
            )
        """
        event_name = "AI Generation Success" if success else "AI Generation Failure"
        event_type = "ai_generate_success" if success else "ai_generate_failure"
        
        properties = {
            "model": model,
            "cost_credits": cost_credits,
            "success": success,
            **extra_properties
        }
        
        if duration_ms is not None:
            properties["duration_ms"] = duration_ms
        
        if error_code:
            properties["error_code"] = error_code
        
        return await self.track_event(
            event_name=event_name,
            event_type=event_type,
            user_id=user_id,
            properties=properties,
            source="server"
        )
    
    async def track_payment(
        self,
        user_id: str,
        event_name: str,
        amount_cents: Optional[int] = None,
        plan: Optional[str] = None,
        stripe_payment_id: Optional[str] = None,
        **extra_properties
    ) -> AnalyticsEvent:
        """
        Convenience method: Track payment event.
        
        Args:
            user_id: User ID
            event_name: Event name (e.g., "checkout_completed", "subscription_started")
            amount_cents: Optional amount in cents
            plan: Optional plan name (e.g., "t3", "pro")
            stripe_payment_id: Optional Stripe payment ID
            extra_properties: Additional custom properties
            
        Returns:
            AnalyticsEvent: Created event entity
            
        Example:
            await analytics.track_payment(
                user_id="user_123",
                event_name="checkout_completed",
                amount_cents=2990,
                plan="t3"
            )
        """
        properties = {**extra_properties}
        
        if amount_cents is not None:
            properties["amount_cents"] = amount_cents
        
        if plan:
            properties["plan"] = plan
        
        if stripe_payment_id:
            properties["stripe_payment_id"] = stripe_payment_id
        
        # Map event_name to event_type (normalize)
        event_type = event_name.lower().replace(" ", "_")
        
        return await self.track_event(
            event_name=event_name.replace("_", " ").title(),
            event_type=event_type,
            user_id=user_id,
            properties=properties,
            source="server"
        )
    
    async def track_marketplace_action(
        self,
        user_id: str,
        action: str,
        listing_id: Optional[str] = None,
        **extra_properties
    ) -> AnalyticsEvent:
        """
        Convenience method: Track marketplace action.
        
        Args:
            user_id: User ID
            action: Action type (e.g., "view", "purchase", "publish")
            listing_id: Optional listing ID
            extra_properties: Additional custom properties
            
        Returns:
            AnalyticsEvent: Created event entity
            
        Example:
            await analytics.track_marketplace_action(
                user_id="user_123",
                action="purchase",
                listing_id="listing_456",
                price_credits=50
            )
        """
        event_type = f"marketplace_{action}"
        event_name = f"Marketplace {action.title()}"
        
        properties = {**extra_properties}
        if listing_id:
            properties["listing_id"] = listing_id
        
        return await self.track_event(
            event_name=event_name,
            event_type=event_type,
            user_id=user_id,
            properties=properties,
            source="server"
        )
    
    async def track_project_action(
        self,
        user_id: str,
        action: str,
        project_id: Optional[str] = None,
        **extra_properties
    ) -> AnalyticsEvent:
        """
        Convenience method: Track project action.
        
        Args:
            user_id: User ID
            action: Action type (e.g., "created", "updated", "deleted", "exported")
            project_id: Optional project ID
            extra_properties: Additional custom properties
            
        Returns:
            AnalyticsEvent: Created event entity
            
        Example:
            await analytics.track_project_action(
                user_id="user_123",
                action="created",
                project_id="project_789"
            )
        """
        event_type = f"project_{action}"
        event_name = f"Project {action.title()}"
        
        properties = {**extra_properties}
        if project_id:
            properties["project_id"] = project_id
        
        return await self.track_event(
            event_name=event_name,
            event_type=event_type,
            user_id=user_id,
            properties=properties,
            source="server"
        )