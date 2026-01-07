"""
DateTime Utilities - Timezone-aware datetime handling.

@module core.utils.datetime
@version 1.0.0
"""

from datetime import datetime, timezone
from typing import Optional, Union

# Common IANA timezones for quick validation
COMMON_TIMEZONES = {
    "UTC",
    "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Tokyo", "Asia/Seoul",
    "Asia/Singapore", "Asia/Taipei", "Asia/Bangkok",
    "America/New_York", "America/Los_Angeles", "America/Chicago",
    "Europe/London", "Europe/Paris", "Europe/Berlin",
    "Pacific/Auckland", "Australia/Sydney",
}


def utc_now() -> datetime:
    """
    Get current time in UTC with timezone info.

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: Datetime to convert (naive assumed as UTC)

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_iso(dt: datetime) -> str:
    """
    Format datetime as ISO 8601 string.

    Args:
        dt: Datetime to format

    Returns:
        ISO 8601 formatted string
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_iso(iso_string: str) -> Optional[datetime]:
    """
    Parse ISO 8601 datetime string.

    Args:
        iso_string: ISO 8601 formatted string

    Returns:
        Parsed datetime or None if invalid
    """
    if not iso_string:
        return None

    try:
        # Handle various ISO formats
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return to_utc(dt)
    except (ValueError, AttributeError):
        return None


def is_valid_timezone(tz: str) -> bool:
    """
    Validate if the timezone string is a valid IANA timezone identifier.

    IANA timezones must be in Area/Location format (e.g., America/New_York).
    Abbreviations like EST, PST, GMT+8 are NOT valid IANA identifiers.

    Args:
        tz: Timezone string to validate

    Returns:
        True if valid IANA timezone
    """
    if not tz or not isinstance(tz, str):
        return False

    tz = tz.strip()
    if not tz:
        return False

    # UTC is always valid
    if tz == "UTC":
        return True

    # Must be in Area/Location format
    if "/" not in tz:
        return False

    # Quick check against common timezones
    if tz in COMMON_TIMEZONES:
        return True

    # Try Python's zoneinfo (Python 3.9+)
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(tz)
        return True
    except (ImportError, KeyError):
        pass

    # Fallback: basic format validation
    parts = tz.split("/")
    return len(parts) >= 2 and all(part.strip() for part in parts)


def sanitize_timezone(tz: Optional[str], default: str = "UTC") -> str:
    """
    Sanitize and validate timezone string.

    Args:
        tz: Timezone string to sanitize
        default: Default timezone if invalid

    Returns:
        Valid IANA timezone string
    """
    if not tz:
        return default

    tz = tz.strip()
    return tz if is_valid_timezone(tz) else default
