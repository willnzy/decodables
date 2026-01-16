"""
Analytics API - Analytics events endpoint (v2).

@module api.user.analytics
@version 2.4.0 (Container DI Migration)

Changes in v2.4.0:
- Container DI Migration
  - Migrated to Container-based dependency injection
  - Removed direct get_async_db_client() calls
  - Removed direct infrastructure.repositories imports
  - Architecture: API → Container → Service → Repository

Endpoints:
- POST /api/v2/user/analytics/events - Log analytics events (batch)

Architecture Migration (v2.3.0):
- DDD Compliance: Migrated to use AnalyticsService and Repository
- API layer now uses dependency injection for AnalyticsService
- Removed direct supabase access from API layer
- All database operations moved to SupabaseAnalyticsEventsRepository

Performance Optimization (v2.1.0):
- Batch INSERT: N events → 3 DB calls (instead of 3N)
- run_in_threadpool: Prevents event loop blocking (now in Repository)
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
from pydantic import BaseModel, Field, field_validator

from dependencies import get_current_user_optional
from infrastructure.rate_limiter import limiter
from container import get_container
from domains.analytics import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["user-analytics-v2"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_analytics_service() -> AnalyticsService:
    """
    Dependency injection factory for AnalyticsService via Container.

    WHY Container-based DI?
    - Centralized service instantiation
    - Testable (mock injection)
    - Follows DIP (Dependency Inversion Principle)
    """
    container = get_container()
    return await container.get_analytics_service()


# ==========================================
# Request/Response Models
# ==========================================

class AnalyticsEvent(BaseModel):
    """Single analytics event."""
    event_type: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9_]+$")
    event_id: Optional[str] = Field(None, max_length=100)
    event_level: Optional[str] = Field(None, pattern="^(critical|important|normal|debug)$")
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


# ==========================================
# Endpoints
# ==========================================

@router.post("/events")
@limiter.limit("60/minute")
async def log_analytics_events(
    request: Request,
    req: AnalyticsEventsRequest,
    user: Optional[dict] = Depends(get_current_user_optional),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
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

    # Convert Pydantic models to dicts for service
    events_data = [
        {
            "event_type": event.event_type,
            "event_id": event.event_id,
            "event_level": event.event_level,
            "timestamp": event.timestamp,
            "session_id": event.session_id,
            "properties": event.properties,
            "env": event.env,
            "user_properties": event.user_properties,
        }
        for event in req.events
    ]

    # Use AnalyticsService to process and save events
    requested, total_inserted = await analytics_service.process_and_save_events(
        events=events_data,
        user_id=user_id,
        location_info=location_info,
        user_agent=user_agent,
        accept_language=accept_language,
    )

    return AnalyticsEventsResponse(
        status="ok",
        requested=requested,
        inserted=total_inserted,
        ip=client_ip,
        country=location_info.get("country_code", "unknown"),
    )
