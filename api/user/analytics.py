"""
Analytics API - Analytics events endpoint (v2).

@module api.user.analytics
@version 2.0.0

Endpoints:
- POST /api/v2/user/analytics/events - Log analytics events (batch)
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from dependencies import get_current_user_optional
from services.db_service import supabase, log_user_event, log_activity
from infrastructure.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["user-analytics-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class AnalyticsEvent(BaseModel):
    """Single analytics event."""
    event_type: str
    event_id: Optional[str] = None
    event_level: Optional[str] = None
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    properties: Dict[str, Any] = {}
    env: Dict[str, Any] = {}
    user_properties: Dict[str, Any] = {}


class AnalyticsEventsRequest(BaseModel):
    """Batch analytics events request."""
    events: List[AnalyticsEvent]


class AnalyticsEventsResponse(BaseModel):
    """Analytics events response."""
    status: str
    count: int
    ip: str
    country: str


# ==========================================
# Helper Functions
# ==========================================

def _get_client_ip(request: Request) -> str:
    """Get client IP from request headers."""
    # Cloudflare
    if cf_ip := request.headers.get("CF-Connecting-IP"):
        return cf_ip

    # Standard proxy headers
    if x_forwarded_for := request.headers.get("X-Forwarded-For"):
        return x_forwarded_for.split(",")[0].strip()

    if x_real_ip := request.headers.get("X-Real-IP"):
        return x_real_ip

    return request.client.host if request.client else "unknown"


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

    for event in req.events:
        env_info = event.env
        properties = event.properties

        # Enrich properties with server-side info
        enriched_properties = {
            **properties,
            "server_ip": client_ip,
            "server_country": location_info.get("country_code"),
            "server_city": location_info.get("city"),
            "server_region": location_info.get("region"),
            "server_user_agent": user_agent,
            "server_accept_language": accept_language,
            "client_browser": env_info.get("browser"),
            "client_os": env_info.get("os"),
            "client_device_type": env_info.get("device_type"),
            "client_timezone": env_info.get("timezone"),
            "client_timezone_offset": env_info.get("timezone_offset"),
            "client_language": env_info.get("language"),
            "client_connection_type": env_info.get("connection_type"),
        }

        # 1. Store to user_events table
        log_user_event(
            user_id=user_id,
            event_type=event.event_type,
            properties=enriched_properties,
            session_id=event.session_id,
            event_id=event.event_id,
        )

        # 2. Store to analytics_events table
        try:
            event_data = {
                "event_type": event.event_type,
                "event_level": event.event_level,
                "timestamp": event.timestamp,
                "properties": enriched_properties,
                "session_id": event.session_id,
                "env": env_info,
                "user_properties": event.user_properties,
            }
            supabase.table("analytics_events").insert({
                "user_id": user_id or event.user_properties.get("user_id"),
                "event_type": event.event_type,
                "event_id": event.event_id,
                "event_level": event.event_level,
                "event_data": event_data,
                "session_id": event.session_id,
            }).execute()
        except Exception as e:
            logger.warning(f"[Analytics] Failed to insert to analytics_events: {e}")

        # 3. Mirror key events to activity_logs
        if user_id and event.event_type in ACTIVITY_LOG_EVENTS:
            log_activity(user_id, ACTIVITY_LOG_EVENTS[event.event_type], enriched_properties)

    return AnalyticsEventsResponse(
        status="ok",
        count=len(req.events),
        ip=client_ip,
        country=location_info.get("country_code", "unknown"),
    )
