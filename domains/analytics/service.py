"""
Analytics Service - Domain service for analytics events processing.

@module domains.analytics.service
@version 1.0.0

Handles analytics events batch processing, enrichment, and persistence.
"""

import logging
import uuid
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


# Event types that should also log to activity_logs
ACTIVITY_LOG_EVENTS = {
    "project_print": "print_project",
    "project_export_pdf": "download_pdf",
    "project_export_zip": "export_zip",
    "project_preview": "preview_pdf",
    "project_delete": "delete_project",
    "project_create_complete": "create_project",
}


class AnalyticsService:
    """
    Domain service for analytics events processing.

    Responsibilities:
    - Enrich events with server-side context
    - Build batch data for repository insertion
    - Coordinate event logging across multiple tables
    """

    def __init__(self, analytics_events_repo):
        """
        Initialize service with repository.

        Args:
            analytics_events_repo: AnalyticsEventsRepository instance
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

            # Build user_events row
            # 注意: user_events 表使用 event_data (JSONB), 不是 properties
            # 注意: user_events 表没有 event_id 字段，主键是 id (UUID, 自动生成)
            user_event_rows.append({
                "user_id": user_id,
                "event_type": event_type,
                "event_data": enriched_properties,  # 修复: properties -> event_data
                "session_id": session_id,
                # 移除 event_id (表里不存在)
            })

            # Build analytics_events row
            # 注意: analytics_events 表使用 properties 和 context (JSONB), 不是 event_data
            # 注意: analytics_events 表没有 event_level 字段
            context_data = {
                "event_level": event_level,
                "timestamp": timestamp,
                "env": env_info,
                "user_properties": event.get("user_properties", {}),
            }
            analytics_event_rows.append({
                "user_id": user_id,  # Only use authenticated user_id
                "event_type": event_type,
                "event_id": event_id,
                "properties": enriched_properties,  # 修复: event_data -> properties
                "context": context_data,            # 额外信息放入 context
                "session_id": session_id,
                # 移除 event_level (表里不存在，已放入 context)
            })

            # Build activity_logs row (only for key events with user_id)
            if user_id and event_type in ACTIVITY_LOG_EVENTS:
                activity_rows.append({
                    "user_id": user_id,
                    "action": ACTIVITY_LOG_EVENTS[event_type],
                    "metadata": enriched_properties,
                })

        return user_event_rows, analytics_event_rows, activity_rows
