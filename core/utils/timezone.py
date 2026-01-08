"""
Timezone Utilities
==================
Provides timezone detection with multiple fallback strategies:
1. Client-provided timezone (from header/body)
2. Cloudflare CF-IPTimezone header (IP geolocation)
3. User profile timezone (from database)
4. Default UTC

@module core.utils.timezone

Usage:
    from core.utils.timezone import get_request_timezone

    # In FastAPI endpoint
    timezone = get_request_timezone(request, user_id=user.get("id"))
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import Request

logger = logging.getLogger(__name__)

# ==========================================
# IANA Timezone Validation
# ==========================================

# Common timezones for quick validation (most frequently used)
COMMON_TIMEZONES = {
    # UTC
    "UTC",
    # Asia
    "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Tokyo", "Asia/Seoul",
    "Asia/Singapore", "Asia/Taipei", "Asia/Bangkok", "Asia/Jakarta",
    "Asia/Manila", "Asia/Kuala_Lumpur", "Asia/Ho_Chi_Minh", "Asia/Kolkata",
    "Asia/Dubai", "Asia/Riyadh",
    # Americas
    "America/New_York", "America/Los_Angeles", "America/Chicago",
    "America/Denver", "America/Phoenix", "America/Toronto", "America/Vancouver",
    "America/Mexico_City", "America/Sao_Paulo", "America/Buenos_Aires",
    # Europe
    "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Madrid",
    "Europe/Rome", "Europe/Amsterdam", "Europe/Brussels", "Europe/Moscow",
    "Europe/Zurich", "Europe/Vienna",
    # Pacific
    "Pacific/Auckland", "Pacific/Sydney", "Australia/Sydney",
    "Australia/Melbourne", "Australia/Perth", "Pacific/Honolulu",
    # Africa
    "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos",
}

# Full IANA timezone validation (try to use pytz if available)
def is_valid_timezone(tz: str) -> bool:
    """
    Validate if the timezone string is a valid IANA timezone identifier.
    
    IANA timezones must be in Area/Location format (e.g., America/New_York).
    Abbreviations like EST, PST, GMT+8 are NOT valid IANA identifiers.
    
    Business Rule: Only accept standard IANA timezone identifiers.
    
    Args:
        tz: Timezone string to validate
        
    Returns:
        bool: True if valid IANA timezone
    """
    if not tz or not isinstance(tz, str):
        return False
    
    # Strip whitespace
    tz = tz.strip()
    if not tz:
        return False
    
    # IANA timezones must contain "/" (except UTC)
    # This rejects abbreviations like EST, PST, GMT+8
    if tz == "UTC":
        return True
    
    # Must be in Area/Location format
    if "/" not in tz:
        return False
    
    # Quick check against common timezones
    if tz in COMMON_TIMEZONES:
        return True
    
    # Try to validate using Python's zoneinfo (Python 3.9+)
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(tz)
        return True
    except (ImportError, KeyError):
        pass
    
    # Try pytz as fallback - but only if it's IANA format (contains /)
    try:
        import pytz
        # Only accept if it's in the common_timezones set (proper IANA format)
        # This excludes pytz's legacy abbreviations
        return tz in pytz.common_timezones
    except ImportError:
        pass
    
    # Fallback: basic format validation
    # IANA format: Area/Location or Area/Sub_area/Location
    parts = tz.split("/")
    if len(parts) >= 2 and all(part.strip() for part in parts):
        return True
    
    return False


def sanitize_timezone(tz: Optional[str], default: str = "UTC") -> str:
    """
    Sanitize and validate timezone string.
    
    Args:
        tz: Timezone string to sanitize
        default: Default timezone if invalid
        
    Returns:
        str: Valid IANA timezone string
    """
    if not tz:
        return default
    
    tz = tz.strip()
    
    if is_valid_timezone(tz):
        return tz
    
    logger.warning(f"Invalid timezone '{tz}', falling back to '{default}'")
    return default


# ==========================================
# Request Timezone Extraction
# ==========================================

def get_timezone_from_cloudflare(request: Request) -> Optional[str]:
    """
    Extract timezone from Cloudflare geolocation headers.
    
    Cloudflare automatically adds these headers based on IP geolocation:
    - CF-IPTimezone: IANA timezone (e.g., 'Asia/Shanghai')
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str or None: Timezone if available and valid
    """
    cf_timezone = request.headers.get("CF-IPTimezone")
    
    if cf_timezone and cf_timezone not in ("unknown", ""):
        if is_valid_timezone(cf_timezone):
            logger.debug(f"Timezone from Cloudflare: {cf_timezone}")
            return cf_timezone
        else:
            logger.warning(f"Invalid Cloudflare timezone: {cf_timezone}")
    
    return None


def get_timezone_from_header(request: Request) -> Optional[str]:
    """
    Extract timezone from custom request header.
    
    Frontend can send timezone via:
    - X-Timezone header
    - X-User-Timezone header
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str or None: Timezone if available and valid
    """
    # Check custom headers
    for header_name in ("X-Timezone", "X-User-Timezone"):
        tz = request.headers.get(header_name)
        if tz and is_valid_timezone(tz):
            logger.debug(f"Timezone from header {header_name}: {tz}")
            return tz
    
    return None


async def get_timezone_from_body(request: Request) -> Optional[str]:
    """
    Extract timezone from request body (if JSON).
    
    Note: This consumes the request body, so it should be called carefully.
    In practice, timezone should be extracted before Pydantic validation.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str or None: Timezone if available and valid
    """
    try:
        # Try to get timezone from cached body (if available)
        if hasattr(request.state, "body_json"):
            body = request.state.body_json
            tz = body.get("timezone")
            if tz and is_valid_timezone(tz):
                return tz
    except Exception:
        pass
    
    return None


def get_timezone_from_user_profile(user_id: Optional[str]) -> Optional[str]:
    """
    Get timezone from user's database profile.
    
    Args:
        user_id: User ID
        
    Returns:
        str or None: Timezone if user has one set
    """
    if not user_id:
        return None
    
    try:
        from infrastructure.db_compat import get_user_timezone
        tz = get_user_timezone(user_id)
        if tz and tz != "UTC":  # Only return if explicitly set
            logger.debug(f"Timezone from user profile: {tz}")
            return tz
    except Exception as e:
        logger.warning(f"Failed to get user timezone: {e}")
    
    return None


# ==========================================
# Main Timezone Resolution Function
# ==========================================

def get_request_timezone(
    request: Request,
    user_id: Optional[str] = None,
    timezone_override: Optional[str] = None,
    default: str = "UTC"
) -> str:
    """
    Get timezone for the current request with multiple fallback strategies.
    
    Resolution order (first valid wins):
    1. timezone_override (explicit parameter from request body/params)
    2. X-Timezone / X-User-Timezone header (frontend-provided)
    3. CF-IPTimezone header (Cloudflare IP geolocation - THE IP FALLBACK)
    4. User profile timezone (from database)
    5. Default (UTC)
    
    This function is designed to always return a valid IANA timezone.
    
    Args:
        request: FastAPI Request object
        user_id: Optional user ID for profile lookup
        timezone_override: Explicit timezone from request body/params
        default: Default timezone if all methods fail
        
    Returns:
        str: Valid IANA timezone identifier
        
    Example:
        # In FastAPI endpoint
        @app.post("/api/purchase")
        async def purchase(request: Request, body: PurchaseRequest, user = Depends(get_current_user)):
            timezone = get_request_timezone(
                request, 
                user_id=user.get("id"),
                timezone_override=body.timezone
            )
            # Use timezone for logging...
    """
    # 1. Explicit override (from request body)
    if timezone_override:
        tz = sanitize_timezone(timezone_override)
        if tz != default:
            logger.debug(f"Using explicit timezone override: {tz}")
            return tz
    
    # 2. Custom header (frontend-provided)
    header_tz = get_timezone_from_header(request)
    if header_tz:
        return header_tz
    
    # 3. Cloudflare IP geolocation (THE IP FALLBACK!)
    cf_tz = get_timezone_from_cloudflare(request)
    if cf_tz:
        logger.info(f"Using Cloudflare IP-based timezone: {cf_tz}")
        return cf_tz
    
    # 4. User profile
    profile_tz = get_timezone_from_user_profile(user_id)
    if profile_tz:
        return profile_tz
    
    # 5. Default fallback
    logger.debug(f"No timezone found, using default: {default}")
    return default


def get_timezone_info(request: Request, user_id: Optional[str] = None) -> dict:
    """
    Get detailed timezone information for debugging/analytics.
    
    Returns a dict with all available timezone sources and the resolved timezone.
    
    Args:
        request: FastAPI Request object
        user_id: Optional user ID
        
    Returns:
        dict: Timezone resolution details
    """
    return {
        "resolved": get_request_timezone(request, user_id),
        "sources": {
            "header": get_timezone_from_header(request),
            "cloudflare": get_timezone_from_cloudflare(request),
            "user_profile": get_timezone_from_user_profile(user_id) if user_id else None,
        },
        "cloudflare_headers": {
            "CF-IPTimezone": request.headers.get("CF-IPTimezone"),
            "CF-IPCountry": request.headers.get("CF-IPCountry"),
            "CF-IPCity": request.headers.get("CF-IPCity"),
        },
        "default": "UTC",
    }


# ==========================================
# Country to Timezone Mapping (Fallback)
# ==========================================

# When Cloudflare doesn't provide timezone but provides country
COUNTRY_DEFAULT_TIMEZONES = {
    "CN": "Asia/Shanghai",
    "HK": "Asia/Hong_Kong",
    "TW": "Asia/Taipei",
    "JP": "Asia/Tokyo",
    "KR": "Asia/Seoul",
    "SG": "Asia/Singapore",
    "MY": "Asia/Kuala_Lumpur",
    "TH": "Asia/Bangkok",
    "VN": "Asia/Ho_Chi_Minh",
    "ID": "Asia/Jakarta",
    "PH": "Asia/Manila",
    "IN": "Asia/Kolkata",
    "AE": "Asia/Dubai",
    "SA": "Asia/Riyadh",
    "US": "America/New_York",  # Default to Eastern
    "CA": "America/Toronto",
    "MX": "America/Mexico_City",
    "BR": "America/Sao_Paulo",
    "AR": "America/Buenos_Aires",
    "GB": "Europe/London",
    "FR": "Europe/Paris",
    "DE": "Europe/Berlin",
    "ES": "Europe/Madrid",
    "IT": "Europe/Rome",
    "NL": "Europe/Amsterdam",
    "BE": "Europe/Brussels",
    "CH": "Europe/Zurich",
    "AT": "Europe/Vienna",
    "RU": "Europe/Moscow",
    "AU": "Australia/Sydney",
    "NZ": "Pacific/Auckland",
    "ZA": "Africa/Johannesburg",
    "EG": "Africa/Cairo",
    "NG": "Africa/Lagos",
}


def get_timezone_from_country(country_code: Optional[str]) -> Optional[str]:
    """
    Get default timezone for a country code (ISO 3166-1 alpha-2).
    
    This is a fallback when Cloudflare provides country but not timezone.
    Note: Many countries span multiple timezones, so this returns a "default".
    
    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., 'CN', 'US')
        
    Returns:
        str or None: Default timezone for the country
    """
    if not country_code:
        return None
    
    return COUNTRY_DEFAULT_TIMEZONES.get(country_code.upper())


def get_request_timezone_with_country_fallback(
    request: Request,
    user_id: Optional[str] = None,
    timezone_override: Optional[str] = None,
    default: str = "UTC"
) -> str:
    """
    Enhanced timezone resolution with country-based fallback.
    
    Same as get_request_timezone but adds country-based inference
    when Cloudflare timezone is not available.
    
    Resolution order:
    1-4. Same as get_request_timezone
    5. Country code fallback (CF-IPCountry header)
    6. Default (UTC)
    """
    # Try standard resolution first
    tz = get_request_timezone(request, user_id, timezone_override, default=None)
    if tz:
        return tz
    
    # Try country-based fallback
    country_code = request.headers.get("CF-IPCountry")
    country_tz = get_timezone_from_country(country_code)
    if country_tz:
        logger.info(f"Using country-based timezone: {country_tz} (from {country_code})")
        return country_tz
    
    return default
