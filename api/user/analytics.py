"""
Analytics API - Analytics events endpoint (v2).

@module api.user.analytics
@version 2.2.0

Endpoints:
- POST /api/v2/user/analytics/events - Log analytics events (batch)

Performance Optimization (v2.1.0):
- Batch INSERT: N events → 3 DB calls (instead of 3N)
- run_in_threadpool: Prevents event loop blocking
- Reference: https://supabase.com/docs/reference/python/insert

Security & Validation Enhancements (v2.2.0):
- Input validation: event_type, event_level with strict patterns
- Properties filtering: max 100 keys, key format validation, value size limits
- IP validation: ipaddress format checking, prevents injection
- Server field protection: __ prefix to prevent client overwriting
- Event ID generation: auto-generate UUID if not provided
- User ID security: only use authenticated user_id, never client-provided
- Enhanced logging: detailed error messages with counts
- Accurate metrics: return requested vs inserted counts
"""

import logging
import re
import ipaddress
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from dependencies import get_current_user_optional
from infrastructure.rate_limiter import limiter
from core.database import get_supabase_client

supabase = get_supabase_client()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["user-analytics-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class AnalyticsEvent(BaseModel):
    """Single analytics event."""
    event_type: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9_]+$")
    event_id: Optional[str] = Field(None, max_length=100)
    event_level: Optional[str] = Field(None, pattern="^(info|warning|error|debug)$")
    timestamp: Optional[str] = Field(None, max_length=50)
    session_id: Optional[str] = Field(None, max_length=100)
    properties: Dict[str, Any] = Field(default_factory=dict)
    env: Dict[str, Any] = Field(default_factory=dict)
    user_properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("properties", "env", "user_properties")
    @classmethod
    def validate_dict_fields(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize dictionary fields."""
        if not isinstance(v, dict):
            return {}

        # Limit number of keys
        if len(v) > 100:
            raise ValueError("Maximum 100 keys allowed in dictionary fields")

        # Filter and validate keys (only alphanumeric and underscore)
        import re
        filtered = {}
        key_pattern = re.compile(r"^[a-zA-Z0-9_]{1,50}$")

        for key, value in v.items():
            # Validate key format
            if not key_pattern.match(key):
                continue  # Skip invalid keys

            # Limit string value size
            if isinstance(value, str) and len(value) > 10000:
                filtered[key] = value[:10000]
            else:
                filtered[key] = value

        return filtered


class AnalyticsEventsRequest(BaseModel):
    """Batch analytics events request."""
    events: List[AnalyticsEvent]


class AnalyticsEventsResponse(BaseModel):
    """Analytics events response."""
    status: str
    requested: int  # Number of events requested
    inserted: int  # Number of events successfully inserted
    ip: str
    country: str


# ==========================================
# Helper Functions
# ==========================================

def _validate_ip(ip_str: str) -> str:
    """
    Validate IP address format.

    Args:
        ip_str: IP address string to validate

    Returns:
        Valid IP address or "invalid"
    """
    if not ip_str or ip_str == "unknown":
        return "unknown"

    try:
        # Validate IP format (IPv4 or IPv6)
        ipaddress.ip_address(ip_str)
        return ip_str
    except ValueError:
        logger.warning(f"[Analytics] Invalid IP format received: {ip_str[:50]}")
        return "invalid"


def _get_client_ip(request: Request) -> str:
    """Get client IP from request headers with validation."""
    # Cloudflare
    if cf_ip := request.headers.get("CF-Connecting-IP"):
        return _validate_ip(cf_ip)

    # Standard proxy headers
    if x_forwarded_for := request.headers.get("X-Forwarded-For"):
        first_ip = x_forwarded_for.split(",")[0].strip()
        return _validate_ip(first_ip)

    if x_real_ip := request.headers.get("X-Real-IP"):
        return _validate_ip(x_real_ip)

    if request.client and request.client.host:
        return _validate_ip(request.client.host)

    return "unknown"


def _get_cloudflare_geo(request: Request) -> Dict[str, str]:
    """Extract geo info from Cloudflare headers."""
    return {
        "country_code": request.headers.get("CF-IPCountry", "unknown"),
        "city": request.headers.get("CF-IPCity", "unknown"),
        "region": request.headers.get("CF-IPRegion", "unknown"),
        "timezone": request.headers.get("CF-IPTimezone", "unknown"),
    }


def _get_country_from_ip(ip: str) -> Dict[str, str]:
    """Infer country from IP (demo only)."""
    if ip.startswith("127.") or ip == "localhost" or ip == "::1":
        return {"country_code": "LOCAL"}
    elif ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        return {"country_code": "PRIVATE"}
    return {"country_code": "unknown"}


# Event types that should also log to activity_logs
ACTIVITY_LOG_EVENTS = {
    "project_print": "print_project",
    "project_export_pdf": "download_pdf",
    "project_export_zip": "export_zip",
    "project_preview": "preview_pdf",
    "project_delete": "delete_project",
    "project_create_complete": "create_project",
}


# ==========================================
# Endpoints
# ==========================================

@router.post("/events")
@limiter.limit("60/minute")
async def log_analytics_events(
    request: Request,
    req: AnalyticsEventsRequest,
    user: Optional[dict] = Depends(get_current_user_optional),
) -> AnalyticsEventsResponse:
    """
    Record user analytics events (batch submission).

    Enriches events with server-side IP, geo, and device info.
    Writes to both user_events and analytics_events tables.
    """
    user_id = user.get("id") if user else None

    # Get client info
    client_ip = _get_client_ip(request)
    geo_info = _get_cloudflare_geo(request)
    country_info = _get_country_from_ip(client_ip) if geo_info.get("country_code") == "unknown" else {}

    location_info = {
        "ip": client_ip,
        "country_code": geo_info.get("country_code") or country_info.get("country_code", "unknown"),
        "city": geo_info.get("city", "unknown"),
        "region": geo_info.get("region", "unknown"),
        "cf_timezone": geo_info.get("timezone", "unknown"),
    }

    user_agent = request.headers.get("User-Agent", "unknown")
    accept_language = request.headers.get("Accept-Language", "unknown")

    # ========================================
    # Phase 1: Build batch data (no DB calls)
    # ========================================
    user_event_rows = []
    analytics_event_rows = []
    activity_rows = []

    for event in req.events:
        env_info = event.env
        properties = event.properties

        # Generate event_id if not provided
        event_id = event.event_id or str(uuid.uuid4())

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
        user_event_rows.append({
            "user_id": user_id,
            "event_type": event.event_type,
            "properties": enriched_properties,
            "session_id": event.session_id,
            "event_id": event_id,  # Use generated or provided event_id
        })

        # Build analytics_events row
        event_data = {
            "event_type": event.event_type,
            "event_level": event.event_level,
            "timestamp": event.timestamp,
            "properties": enriched_properties,
            "session_id": event.session_id,
            "env": env_info,
            "user_properties": event.user_properties,
        }
        analytics_event_rows.append({
            "user_id": user_id,  # Only use authenticated user_id, not client-provided
            "event_type": event.event_type,
            "event_id": event_id,  # Use generated or provided event_id
            "event_level": event.event_level,
            "event_data": event_data,
            "session_id": event.session_id,
        })

        # Build activity_logs row (only for key events with user_id)
        if user_id and event.event_type in ACTIVITY_LOG_EVENTS:
            activity_rows.append({
                "user_id": user_id,
                "action": ACTIVITY_LOG_EVENTS[event.event_type],
                "metadata": enriched_properties,
            })

    # ========================================
    # Phase 2: Batch INSERT (3 DB calls max)
    # ========================================
    # Performance: N events → 3 DB calls (instead of 3N)

    # Track successful insertions
    user_events_inserted = 0
    analytics_events_inserted = 0
    activity_logs_inserted = 0

    # 1. Batch insert to user_events table
    if user_event_rows:
        try:
            await run_in_threadpool(
                lambda: supabase.table("user_events").insert(user_event_rows).execute()
            )
            user_events_inserted = len(user_event_rows)
        except Exception as e:
            logger.warning(f"[Analytics] Failed to batch insert {len(user_event_rows)} events to user_events: {e}")

    # 2. Batch insert to analytics_events table
    if analytics_event_rows:
        try:
            await run_in_threadpool(
                lambda: supabase.table("analytics_events").insert(analytics_event_rows).execute()
            )
            analytics_events_inserted = len(analytics_event_rows)
        except Exception as e:
            logger.warning(f"[Analytics] Failed to batch insert {len(analytics_event_rows)} events to analytics_events: {e}")

    # 3. Batch insert to activity_logs table
    if activity_rows:
        try:
            await run_in_threadpool(
                lambda: supabase.table("activity_logs").insert(activity_rows).execute()
            )
            activity_logs_inserted = len(activity_rows)
        except Exception as e:
            logger.warning(f"[Analytics] Failed to batch insert {len(activity_rows)} events to activity_logs: {e}")

    # At least one table must succeed (preferably analytics_events as it's the primary table)
    total_inserted = max(user_events_inserted, analytics_events_inserted)

    return AnalyticsEventsResponse(
        status="ok",
        requested=len(req.events),
        inserted=total_inserted,
        ip=client_ip,
        country=location_info.get("country_code", "unknown"),
    )
