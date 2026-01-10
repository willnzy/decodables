"""
Trial Period Helper - Utilities for checking user trial status.

@module domains.identity.trial_helper
@version 1.0.0

This module provides helper functions to check if a user is in their trial period.
Trial period is configurable via system_configs (default: 30 days).
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .constants import DEFAULT_TRIAL_DURATION_DAYS, TIER_T1, normalize_tier

logger = logging.getLogger(__name__)


def is_user_in_trial(
    user_data: Dict[str, Any],
    trial_days: Optional[int] = None
) -> bool:
    """
    Check if a free tier user is within their trial period.

    Args:
        user_data: User dictionary with 'tier' and 'created_at' fields
        trial_days: Trial duration in days (if None, uses default)

    Returns:
        True if user is free tier AND within trial period, False otherwise

    Example:
        >>> user = {"tier": "t1", "created_at": "2024-01-01T00:00:00Z"}
        >>> is_user_in_trial(user, trial_days=30)
        True  # If today is within 30 days of 2024-01-01
    """
    # Default to constant if not provided
    if trial_days is None:
        trial_days = DEFAULT_TRIAL_DURATION_DAYS

    # Only free tier users have trial periods
    user_tier_raw = user_data.get("tier") or "t1"

    try:
        user_tier = normalize_tier(user_tier_raw)
    except ValueError:
        # Invalid tier, treat as t1 for backward compatibility
        user_tier = TIER_T1

    if user_tier != TIER_T1:
        return False

    # Check registration date
    created_at = user_data.get("created_at")
    if not created_at:
        return False

    try:
        # Parse created_at
        if isinstance(created_at, str):
            created_at_str = created_at.replace("Z", "+00:00")
            registration_date = datetime.fromisoformat(created_at_str)
        else:
            registration_date = created_at

        # Ensure timezone aware
        if registration_date.tzinfo is None:
            registration_date = registration_date.replace(tzinfo=timezone.utc)

        # Calculate days since registration
        days_since = (datetime.now(timezone.utc) - registration_date).total_seconds() / (24 * 3600)

        return days_since <= trial_days

    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse user registration date: {e}")
        return False


async def is_user_in_trial_async(
    user_data: Dict[str, Any],
    tier_service: Optional[Any] = None
) -> bool:
    """
    Async version that fetches trial duration from TierService.

    Args:
        user_data: User dictionary with 'tier' and 'created_at' fields
        tier_service: Optional TierService instance to fetch configured trial days

    Returns:
        True if user is free tier AND within trial period, False otherwise

    Example:
        >>> tier_service = TierService(config_repo)
        >>> await is_user_in_trial_async(user, tier_service=tier_service)
        True
    """
    # Get trial duration from service if available
    trial_days = DEFAULT_TRIAL_DURATION_DAYS

    if tier_service:
        try:
            trial_days = await tier_service.get_trial_duration_days()
        except Exception as e:
            logger.error(f"Failed to fetch trial duration, using default {DEFAULT_TRIAL_DURATION_DAYS}: {e}")

    return is_user_in_trial(user_data, trial_days=trial_days)
