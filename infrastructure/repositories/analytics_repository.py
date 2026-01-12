"""
Analytics Repository - Analytics events data access.

@module infrastructure.repositories.analytics_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited

Provides analytics event aggregation for admin dashboards.
"""

import logging
from typing import Dict, Any
from collections import Counter
from urllib.parse import urlparse

from core.database import DatabaseClient, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseAnalyticsRepository:
    """
    Repository for analytics-related admin operations.

    Provides aggregated environment statistics for admin dashboards.
    """

    def __init__(self, client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            client: Database client (Supabase)
        """
        self.client = client

    @retry_on_network_error()
    async def get_user_env_stats(
        self,
        user_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get aggregated environment statistics for a user.

        Queries analytics_events for page_view events and aggregates
        browser, device, OS, and referrer information.

        Args:
            user_id: User ID
            limit: Maximum number of events to query (default: 100, reduced from 500 to prevent OOM)

        Returns:
            Dict with aggregated statistics:
            {
                "total_events": int,
                "browsers": Dict[str, int],
                "devices": Dict[str, int],
                "os_stats": Dict[str, int],
                "referrers": Dict[str, int]
            }
        """
        try:
            # Query analytics events with limit
            result = await self.client.table("analytics_events").select(
                "user_agent, device_type, os, referrer"
            ).eq("user_id", user_id).eq("event_type", "page_view").limit(limit).execute()

            events = result.data or []

            # Aggregate browser info (from user_agent)
            browsers = Counter()
            for event in events:
                user_agent = event.get("user_agent", "unknown")
                browser = self._parse_browser(user_agent)
                browsers[browser] += 1

            # Aggregate device types
            devices = Counter()
            for event in events:
                device_type = event.get("device_type", "unknown")
                devices[device_type] += 1

            # Aggregate OS
            os_stats = Counter()
            for event in events:
                os = event.get("os", "unknown")
                os_stats[os] += 1

            # Aggregate referrers (safely parse domain)
            referrers = Counter()
            for event in events:
                referrer = event.get("referrer")
                if referrer:
                    try:
                        parsed = urlparse(referrer)
                        domain = parsed.netloc or "direct"
                        referrers[domain] += 1
                    except Exception:
                        # Fallback if URL parsing fails
                        referrers["unknown"] += 1
                else:
                    referrers["direct"] += 1

            return {
                "total_events": len(events),
                "browsers": dict(browsers),
                "devices": dict(devices),
                "os_stats": dict(os_stats),
                "referrers": dict(referrers),
                "queried_limit": limit,
                "is_truncated": len(events) >= limit
            }

        except Exception as e:
            logger.error(f"Failed to get env stats for user {user_id}: {e}")
            raise

    def _parse_browser(self, user_agent: str) -> str:
        """
        Parse browser name from user agent string.

        Args:
            user_agent: User agent string

        Returns:
            Browser name (Chrome, Safari, Firefox, Edge, etc.)
        """
        if not user_agent:
            return "unknown"

        ua_lower = user_agent.lower()

        # Check in order of specificity
        if "edg/" in ua_lower or "edge/" in ua_lower:
            return "Edge"
        elif "chrome" in ua_lower and "edg" not in ua_lower:
            return "Chrome"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            return "Safari"
        elif "firefox" in ua_lower:
            return "Firefox"
        elif "opera" in ua_lower or "opr/" in ua_lower:
            return "Opera"
        else:
            return "Other"
