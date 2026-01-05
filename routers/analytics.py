"""
Analytics Router - Analytics events endpoint

@module routers.analytics
@version 3.24

Endpoints:
- POST /api/analytics/events - Log analytics events (batch)
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends

from services.db_service import supabase, log_user_event, log_activity
from services.rate_limiter import limiter
from schemas import UserEventsRequest
from dependencies import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# =====================================================
# IP/Geo Helpers
# =====================================================

def get_client_ip(request: Request) -> str:
    """
    Retrieve the client IP, supporting X-Forwarded-For / X-Real-IP / CF-Connecting-IP.
    """
    # Cloudflare
    if cf_ip := request.headers.get("CF-Connecting-IP"):
        return cf_ip
    
    # Standard proxy headers
    if x_forwarded_for := request.headers.get("X-Forwarded-For"):
        # Use first IP in list (originating client)
        return x_forwarded_for.split(",")[0].strip()
    
    if x_real_ip := request.headers.get("X-Real-IP"):
        return x_real_ip
    
    # Direct connection fallback
    return request.client.host if request.client else "unknown"


def get_country_from_ip(ip: str) -> dict:
    """
    Infer country from IP (demo only – use GeoIP in production).
    """
    country_info = {
        "country_code": "unknown",
        "country_name": "Unknown",
        "continent": "Unknown",
    }
    
    # Sample prefix checks for demo purposes
    if ip.startswith("127.") or ip.startswith("localhost") or ip == "::1":
        country_info = {"country_code": "LOCAL", "country_name": "Localhost", "continent": "Local"}
    elif ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        country_info = {"country_code": "PRIVATE", "country_name": "Private Network", "continent": "Private"}
    
    return country_info


def get_cloudflare_geo(request: Request) -> dict:
    """
    Extract geo info from Cloudflare headers.
    """
    return {
        "country_code": request.headers.get("CF-IPCountry", "unknown"),
        "city": request.headers.get("CF-IPCity", "unknown"),
        "region": request.headers.get("CF-IPRegion", "unknown"),
        "timezone": request.headers.get("CF-IPTimezone", "unknown"),
    }


# =====================================================
# Analytics Events
# =====================================================

@router.post("/events")
@limiter.limit("60/minute")
async def log_analytics_events(
    request: Request, 
    req: UserEventsRequest, 
    user: dict = Depends(get_current_user_optional)
):
    """
    Record user analytics events (batch submission with auto IP/geo/device enrichment).
    
    Writes to both user_events and analytics_events tables:
    - user_events: For behavioral analytics with enriched properties
    - analytics_events: For structured event tracking with event_level support
    """
    user_id = user.get("id") if user else None
    
    # Enrich with server-side IP + geo
    client_ip = get_client_ip(request)
    geo_info = get_cloudflare_geo(request)
    country_info = get_country_from_ip(client_ip) if geo_info.get("country_code") == "unknown" else {}
    
    # Merge geo info
    location_info = {
        "ip": client_ip,
        "country_code": geo_info.get("country_code") or country_info.get("country_code", "unknown"),
        "city": geo_info.get("city", "unknown"),
        "region": geo_info.get("region", "unknown"),
        "cf_timezone": geo_info.get("timezone", "unknown"),
    }
    
    # Capture user agent metadata
    user_agent = request.headers.get("User-Agent", "unknown")
    accept_language = request.headers.get("Accept-Language", "unknown")
    
    # Event types that should also log to activity_logs
    ACTIVITY_LOG_EVENTS = {
        "project_print": "print_project",
        "project_export_pdf": "download_pdf",
        "project_export_zip": "export_zip",
        "project_preview": "preview_pdf",
        "project_delete": "delete_project",
        "project_create_complete": "create_project",
    }
    
    for event in req.events:
        event_type = event.get("event_type")
        event_id = event.get("event_id")  # v3.19: For CAPI deduplication
        event_level = event.get("event_level")
        properties = event.get("properties", {})
        env_info = event.get("env", {})
        user_properties = event.get("user_properties", {})
        
        # Merge server-side enrichment into properties
        enriched_properties = {
            **properties,
            # Server-side info (authoritative)
            "server_ip": client_ip,
            "server_country": location_info.get("country_code"),
            "server_city": location_info.get("city"),
            "server_region": location_info.get("region"),
            "server_user_agent": user_agent,
            "server_accept_language": accept_language,
            # Client-provided environment info
            "client_browser": env_info.get("browser"),
            "client_os": env_info.get("os"),
            "client_device_type": env_info.get("device_type"),
            "client_timezone": env_info.get("timezone"),
            "client_timezone_offset": env_info.get("timezone_offset"),
            "client_language": env_info.get("language"),
            "client_connection_type": env_info.get("connection_type"),
        }
        
        # 1. Store to user_events table (behavioral analytics)
        # v3.19: Pass event_id for CAPI/sGTM deduplication
        log_user_event(
            user_id=user_id,
            event_type=event_type,
            properties=enriched_properties,
            session_id=event.get("session_id"),
            event_id=event_id
        )
        
        # 2. Also store to analytics_events table (structured analytics)
        # This table supports event_level and is used for aggregation/reporting
        try:
            event_data = {
                "event_type": event_type,
                "event_level": event_level,
                "timestamp": event.get("timestamp"),
                "properties": enriched_properties,
                "session_id": event.get("session_id"),
                "env": env_info,
                "user_properties": user_properties,
            }
            supabase.table("analytics_events").insert({
                "user_id": user_id or user_properties.get("user_id"),
                "event_type": event_type,
                "event_id": event_id,  # v3.19: For CAPI deduplication
                "event_level": event_level,
                "event_data": event_data,
                "session_id": event.get("session_id"),
            }).execute()
        except Exception as e:
            # Don't fail if analytics_events insert fails
            logger.warning(f"[Analytics] Failed to insert to analytics_events: {e}")
        
        # 3. Mirror key events into activity_logs
        if user_id and event_type in ACTIVITY_LOG_EVENTS:
            log_activity(user_id, ACTIVITY_LOG_EVENTS[event_type], enriched_properties)
    
    return {"status": "ok", "count": len(req.events), "ip": client_ip, "country": location_info.get("country_code")}
