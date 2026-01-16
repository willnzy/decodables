"""
Metrics ETL Utils - Shared utilities

@module application.services.metrics.utils
@version 3.25 (Log Hygiene)

Changes:
- v3.25: Replaced print-based log function with proper logging
- v3.24: Initial implementation
"""

import logging
import re
from datetime import datetime, timedelta, timezone, date
from typing import Optional, Tuple

from core.database import supabase

logger = logging.getLogger(__name__)

# Bot User-Agent patterns to filter
BOT_PATTERNS = re.compile(
    r'bot|crawler|spider|scraper|headless|phantom|selenium|puppeteer|playwright|'
    r'googlebot|bingbot|slurp|duckduckbot|baiduspider|yandexbot|facebookexternalhit|'
    r'twitterbot|linkedinbot|whatsapp|telegram|discord|slack',
    re.IGNORECASE
)

# Subscription pricing (cents)
TIER_PRICING = {
    'starter': 999,    # $9.99/month
    'pro': 2499,       # $24.99/month
}

# Retention periods to calculate
RETENTION_DAYS = [1, 7, 14, 30, 60, 90]


def get_supabase():
    """Get Supabase client."""
    return supabase


def log(message: str, level: str = "INFO"):
    """Structured logging using standard logging."""
    level_upper = level.upper()
    if level_upper == "ERROR":
        logger.error(message)
    elif level_upper == "WARNING":
        logger.warning(message)
    elif level_upper == "DEBUG":
        logger.debug(message)
    else:
        logger.info(message)


def is_bot(user_agent: Optional[str]) -> bool:
    """Check if user agent indicates a bot."""
    if not user_agent:
        return False
    return bool(BOT_PATTERNS.search(user_agent))


def get_utc_date_range(target_date: date) -> Tuple[str, str]:
    """Get UTC timestamp range for a date."""
    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()
