"""
Database Compatibility Layer - Bridges old services/db to new repositories.

@module infrastructure.db_compat
@version 1.0.0

This module provides backward-compatible synchronous wrappers around
the new async repositories. It allows existing synchronous API code
to continue working while we gradually migrate to async/await.

⚠️ TEMPORARY: This compatibility layer should be removed once all APIs
are migrated to use repositories directly with async/await.

Usage:
    # Old way (still works):
    from services.db import get_user_profile
    profile = get_user_profile(user_id)

    # New way (preferred):
    from infrastructure.repositories import SupabaseUserRepository
    repo = SupabaseUserRepository(get_database_client())
    profile = await repo.get_by_id(user_id)
"""

import asyncio
import logging
from typing import Optional, Any
from functools import wraps

from core.database import get_database_client
from infrastructure.repositories import (
    SupabaseConfigRepository,
    SupabasePaymentRepository,
    SupabaseUserRepository,
    SupabaseCreditRepository,
    SupabaseProjectRepository,
    SupabaseListingRepository,
)
from infrastructure.repositories.user_repository_extended import SupabaseUserRepositoryExtended
from infrastructure.repositories.credit_repository_extended import SupabaseCreditRepositoryExtended

logger = logging.getLogger(__name__)

# Singleton repository instances
_repos = {}


def _get_repo(repo_class):
    """Get or create repository instance."""
    if repo_class not in _repos:
        _repos[repo_class] = repo_class(get_database_client())
    return _repos[repo_class]


def async_to_sync(async_func):
    """
    Decorator to run async function synchronously.

    This is needed for backward compatibility with synchronous API code.
    """
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(async_func(*args, **kwargs))

    return wrapper


# ==========================================
# Config Functions
# ==========================================

@async_to_sync
async def get_system_config(key: str, default_value: Optional[str] = None):
    """Get system config by key."""
    repo = _get_repo(SupabaseConfigRepository)
    return await repo.get_by_key(key, default_value)


@async_to_sync
async def get_all_system_configs(group: Optional[str] = None, include_inactive: bool = False):
    """Get all system configs."""
    repo = _get_repo(SupabaseConfigRepository)
    return await repo.get_all(group, include_inactive)


@async_to_sync
async def get_configs_by_group(group: str):
    """Get configs by group."""
    repo = _get_repo(SupabaseConfigRepository)
    return await repo.get_by_group(group)


# ==========================================
# Payment Functions
# ==========================================

@async_to_sync
async def log_payment_record(
    user_id: str,
    amount: float,
    currency: str,
    payment_type: str,
    stripe_payment_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    tz: str = "UTC"
):
    """Log payment record."""
    repo = _get_repo(SupabasePaymentRepository)
    return await repo.create(
        user_id, amount, currency, payment_type,
        stripe_payment_id, metadata, tz
    )


@async_to_sync
async def get_user_payments(user_id: str, page: int = 1, limit: int = 20):
    """Get user payments."""
    repo = _get_repo(SupabasePaymentRepository)
    return await repo.get_by_user(user_id, page, limit)


# ==========================================
# User Profile Functions
# ==========================================

@async_to_sync
async def get_user_profile(user_id: str):
    """Get user profile by ID."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.get_profile(user_id)


def generate_user_code() -> str:
    """Generate unique 6-char user code."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return repo.generate_user_code()


@async_to_sync
async def create_user_profile(
    user_id: str,
    email: str,
    username: str,
    avatar_url: str,
    first_name: str = None,
    last_name: str = None,
    timezone: str = "UTC"
):
    """Create new user profile."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    profile = await repo.create_profile(
        user_id, email, username, avatar_url,
        first_name, last_name, timezone
    )

    # Log signup bonus credit transaction
    if profile:
        credit_repo = _get_repo(SupabaseCreditRepositoryExtended)
        credit_repo.log_transaction(
            user_id, 50, "permanent", "signup_bonus",
            "Welcome bonus", timezone
        )

    return profile


@async_to_sync
async def update_subscription_tier(
    user_id: str,
    tier: str,
    stripe_customer_id: str = None,
    subscription_status: str = "active"
):
    """Update user subscription tier."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.update_subscription_tier(
        user_id, tier, stripe_customer_id, subscription_status
    )


@async_to_sync
async def update_user_profile(
    user_id: str,
    avatar_url: str = None,
    username: str = None,
    first_name: str = None,
    last_name: str = None,
    timezone_val: str = None
):
    """Update user profile fields."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.update_profile(
        user_id, avatar_url, username, first_name, last_name, timezone_val
    )


@async_to_sync
async def update_user_timezone(user_id: str, tz: str):
    """Update user timezone."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.update_timezone(user_id, tz)


@async_to_sync
async def get_user_timezone(user_id: str) -> str:
    """Get user timezone, default to UTC."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.get_timezone(user_id)


@async_to_sync
async def search_users(query: str):
    """Search users by email, username, or user_code."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.search_users(query)


@async_to_sync
async def get_users_by_tier(tier: str):
    """Get all user IDs for a specific tier."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.get_users_by_tier(tier)


@async_to_sync
async def get_user_discount(user_id: str, target_plan: str = None):
    """Get active discount for user."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.get_user_discount(user_id, target_plan)


@async_to_sync
async def create_user_discount(
    user_id: str,
    discount_percent: int,
    valid_days: int,
    target_plan: str = None
):
    """Create a user discount."""
    repo = _get_repo(SupabaseUserRepositoryExtended)
    return await repo.create_user_discount(
        user_id, discount_percent, valid_days, target_plan
    )


# ==========================================
# Credit Functions
# ==========================================

def log_credit_transaction(
    user_id: str,
    amount: int,
    bucket: str,
    type: str,
    description: str,
    tz: str = "UTC"
):
    """Log credit transaction (synchronous, fire-and-forget)."""
    repo = _get_repo(SupabaseCreditRepositoryExtended)
    repo.log_transaction(user_id, amount, bucket, type, description, tz)


@async_to_sync
async def credit_deduct(
    user_id: str,
    amount: int,
    type: str,
    description: str,
    tz: str = "UTC"
) -> dict:
    """Deduct credits using atomic RPC function."""
    repo = _get_repo(SupabaseCreditRepositoryExtended)
    return await repo.deduct_credits(user_id, amount, type, description, tz)


@async_to_sync
async def add_credits_permanent(
    user_id: str,
    amount: int,
    description: str,
    type: str = "topup_purchase",
    tz: str = "UTC"
):
    """Add permanent credits."""
    repo = _get_repo(SupabaseCreditRepositoryExtended)
    return await repo.add_credits_permanent(user_id, amount, description, type, tz)


@async_to_sync
async def add_credits_monthly(
    user_id: str,
    amount: int,
    description: str,
    type: str = "sub_grant",
    tz: str = "UTC"
):
    """Add monthly credits."""
    repo = _get_repo(SupabaseCreditRepositoryExtended)
    return await repo.add_credits_monthly(user_id, amount, description, type, tz)


@async_to_sync
async def add_credits(
    user_id: str,
    amount: int,
    description: str,
    type: str = "purchase",
    tz: str = "UTC"
):
    """Add credits (defaults to permanent)."""
    repo = _get_repo(SupabaseCreditRepositoryExtended)
    return await repo.add_credits(user_id, amount, description, type, tz)


@async_to_sync
async def get_credit_history(user_id: str, page: int = 1, limit: int = 20):
    """Get credit transaction history."""
    repo = _get_repo(SupabaseCreditRepositoryExtended)
    return await repo.get_credit_history(user_id, page, limit)


@async_to_sync
async def refresh_monthly_credits(user_id: str, tier: str):
    """Reset monthly credits based on tier."""
    repo = _get_repo(SupabaseCreditRepositoryExtended)
    return await repo.refresh_monthly_credits(user_id, tier)


@async_to_sync
async def check_and_reset_monthly_credits_if_needed(user_id: str):
    """Check and reset monthly credits if 30 days passed."""
    repo = _get_repo(SupabaseCreditRepositoryExtended)
    return await repo.check_and_reset_monthly_credits_if_needed(user_id)


# ==========================================
# Export All
# ==========================================

__all__ = [
    # Config functions
    'get_system_config',
    'get_all_system_configs',
    'get_configs_by_group',
    # Payment functions
    'log_payment_record',
    'get_user_payments',
    # User profile functions
    'get_user_profile',
    'generate_user_code',
    'create_user_profile',
    'update_subscription_tier',
    'update_user_profile',
    'update_user_timezone',
    'get_user_timezone',
    'search_users',
    'get_users_by_tier',
    'get_user_discount',
    'create_user_discount',
    # Credit functions
    'log_credit_transaction',
    'credit_deduct',
    'add_credits_permanent',
    'add_credits_monthly',
    'add_credits',
    'get_credit_history',
    'refresh_monthly_credits',
    'check_and_reset_monthly_credits_if_needed',
]
