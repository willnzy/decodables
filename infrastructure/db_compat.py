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
from infrastructure.repositories.project_repository_extended import SupabaseProjectRepositoryExtended
from infrastructure.repositories.listing_repository_extended import SupabaseListingRepositoryExtended
from infrastructure.repositories.asset_repository_extended import SupabaseAssetRepositoryExtended
from infrastructure.repositories.notification_repository_extended import SupabaseNotificationRepositoryExtended
from infrastructure.repositories.support_repository_extended import SupabaseSupportRepositoryExtended

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
# Project Functions
# ==========================================

@async_to_sync
async def get_user_projects(
    user_id: str,
    page: int = 1,
    limit: int = 20,
    search: str = None,
    include_canvas_data: bool = True
):
    """Get user's projects with pagination."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.get_user_projects(user_id, page, limit, search, include_canvas_data)


@async_to_sync
async def count_user_projects(user_id: str, search: str = None):
    """Count user's projects."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.count_user_projects(user_id, search)


@async_to_sync
async def get_project_detail(project_id: str, user_id: str):
    """Get project detail (must be owner or purchased)."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.get_project_detail(project_id, user_id)


@async_to_sync
async def create_project(
    user_id: str,
    title: str = None,
    canvas_data: dict = None,
    tz: str = "UTC"
):
    """Create new project."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.create_project(user_id, title, canvas_data, tz)


@async_to_sync
async def duplicate_project(project_id: str, user_id: str, tz: str = "UTC"):
    """Duplicate a project."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.duplicate_project(project_id, user_id, tz)


@async_to_sync
async def save_project(
    project_id: str,
    user_id: str,
    canvas_data: dict = None,
    thumbnail_url: str = None,
    title: str = None
):
    """Save/update project."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.save_project(project_id, user_id, canvas_data, thumbnail_url, title)


@async_to_sync
async def soft_delete_project(project_id: str, user_id: str):
    """Soft delete project."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.soft_delete_project(project_id, user_id)


@async_to_sync
async def restore_project(project_id: str):
    """Restore soft-deleted project (admin)."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.restore_project(project_id)


@async_to_sync
async def user_restore_project(project_id: str, user_id: str):
    """Restore soft-deleted project (user)."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.user_restore_project(project_id, user_id)


@async_to_sync
async def get_user_deleted_projects(user_id: str, page: int = 1, limit: int = 20):
    """Get user's deleted projects."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.get_user_deleted_projects(user_id, page, limit)


@async_to_sync
async def permanently_hide_project(project_id: str, user_id: str):
    """Permanently hide project (stage 2 delete)."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.permanently_hide_project(project_id, user_id)


@async_to_sync
async def update_project_hash(project_id: str, new_hash: str):
    """Update project content hash."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.update_project_hash(project_id, new_hash)


@async_to_sync
async def get_all_projects_feed(page: int = 1, limit: int = 50):
    """Get site-wide project feed (admin)."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.get_all_projects_feed(page, limit)


@async_to_sync
async def get_dashboard_projects(
    user_id: str,
    view_type: str = "all",
    page: int = 1,
    limit: int = 20,
    search: str = None,
    include_canvas_data: bool = True
):
    """Get projects for dashboard with view type filtering."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.get_dashboard_projects(
        user_id, view_type, page, limit, search, include_canvas_data
    )


@async_to_sync
async def get_seller_project_stats(user_id: str):
    """Get seller statistics for projects."""
    repo = _get_repo(SupabaseProjectRepositoryExtended)
    return await repo.get_seller_project_stats(user_id)


# ==========================================
# Marketplace/Listing Functions
# ==========================================

@async_to_sync
async def get_marketplace_listings(
    featured: bool = False,
    resource_type: str = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "latest",
    tier_filter: str = None,
    price_filter: str = None,
    mine: bool = False,
    user_id: str = None,
    user_tier: str = None
):
    """Get marketplace listings with filtering and sorting."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.get_marketplace_listings(
        featured, resource_type, page, limit, sort,
        tier_filter, price_filter, mine, user_id, user_tier
    )


@async_to_sync
async def get_marketplace_item(listing_id: str, user_id: str = None):
    """Get single listing detail."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.get_marketplace_item(listing_id, user_id)


@async_to_sync
async def get_seller_listings(seller_id: str, page: int = 1, limit: int = 20):
    """Get seller's own listings."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.get_seller_listings(seller_id, page, limit)


@async_to_sync
async def create_listing(
    seller_id: str,
    title: str,
    description: str,
    thumbnail_url: str,
    resource_url: str,
    resource_type: str,
    price_credits: int,
    allowed_tiers: list = None,
    submit_for_review: bool = True,
    resource_id: str = None,
    version: str = "1.0",
    changelog: str = "",
    timezone: str = "UTC"
):
    """Create or update listing."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.create_listing(
        seller_id, title, description, thumbnail_url, resource_url,
        resource_type, price_credits, allowed_tiers, submit_for_review,
        resource_id, version, changelog, timezone
    )


@async_to_sync
async def submit_listing_for_review(listing_id: str, seller_id: str = None):
    """Submit listing for review."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.submit_listing_for_review(listing_id, seller_id)


@async_to_sync
async def unpublish_listing(listing_id: str, seller_id: str):
    """Unpublish listing."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.unpublish_listing(listing_id, seller_id)


@async_to_sync
async def update_listing(listing_id: str, seller_id: str, updates: dict):
    """Update listing."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.update_listing(listing_id, seller_id, updates)


@async_to_sync
async def check_user_purchase(user_id: str, listing_id: str) -> bool:
    """Check if user has purchased listing."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.check_user_purchase(user_id, listing_id)


@async_to_sync
async def execute_purchase(buyer_id: str, listing_id: str, tz: str = "UTC"):
    """Execute marketplace purchase using atomic RPC."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.execute_purchase(buyer_id, listing_id, tz)


@async_to_sync
async def get_user_purchases(user_id: str, page: int = 1, limit: int = 50):
    """Get user's purchases."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.get_user_purchases(user_id, page, limit)


@async_to_sync
async def get_seller_stats(seller_id: str) -> dict:
    """Get seller statistics."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.get_seller_stats(seller_id)


@async_to_sync
async def record_listing_usage(listing_id: str, used_by_user_id: str, project_id: str) -> bool:
    """Record listing usage."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.record_listing_usage(listing_id, used_by_user_id, project_id)


@async_to_sync
async def get_leaderboard(period: str = "monthly", board_type: str = "all", limit: int = 10):
    """Get marketplace leaderboard."""
    repo = _get_repo(SupabaseListingRepositoryExtended)
    return await repo.get_leaderboard(period, board_type, limit)


# ==========================================
# Asset Functions
# ==========================================

@async_to_sync
async def save_asset(user_id: str, url: str, asset_type: str, project_id: str = None,
                     prompt: str = None, tz: str = "UTC"):
    """Save new asset."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.save_asset(user_id, url, asset_type, project_id, prompt, tz)


@async_to_sync
async def get_assets(user_id: str, project_id: str = None):
    """Get user assets."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.get_assets(user_id, project_id)


@async_to_sync
async def soft_delete_asset(asset_id: str, user_id: str):
    """Soft delete asset."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.soft_delete_asset(asset_id, user_id)


@async_to_sync
async def permanently_hide_asset(asset_id: str, user_id: str):
    """Permanently hide asset."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.permanently_hide_asset(asset_id, user_id)


@async_to_sync
async def restore_asset(asset_id: str, user_id: str):
    """Restore soft-deleted asset."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.restore_asset(asset_id, user_id)


@async_to_sync
async def get_deleted_assets(user_id: str, page: int = 1, limit: int = 20):
    """Get user's deleted assets."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.get_deleted_assets(user_id, page, limit)


# Alias for backward compatibility
get_user_deleted_assets = get_deleted_assets


@async_to_sync
async def increment_asset_usage(asset_id: str, user_id: str):
    """Increment asset usage count."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.increment_asset_usage(asset_id, user_id)


@async_to_sync
async def get_dashboard_assets(user_id: str, view: str = "all", page: int = 1, limit: int = 20):
    """Get assets for dashboard."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.get_dashboard_assets(user_id, view, page, limit)


@async_to_sync
async def get_seller_asset_stats(user_id: str):
    """Get seller statistics for assets."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    return await repo.get_seller_asset_stats(user_id)


def get_system_resources(resource_type: str = "sticker", user_tier: str = "free"):
    """Get system resources by type (synchronous, no async needed)."""
    repo = _get_repo(SupabaseAssetRepositoryExtended)
    # This is intentionally synchronous since it's a simple query
    result = repo.client.table("system_resources").select("*").eq(
        "resource_type", resource_type
    ).eq("is_active", True).order("sort_order").execute()
    return result.data or []


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
    # Project functions
    'get_user_projects',
    'count_user_projects',
    'get_project_detail',
    'create_project',
    'duplicate_project',
    'save_project',
    'soft_delete_project',
    'restore_project',
    'user_restore_project',
    'get_user_deleted_projects',
    'permanently_hide_project',
    'update_project_hash',
    'get_all_projects_feed',
    'get_dashboard_projects',
    'get_seller_project_stats',
    # Marketplace/Listing functions
    'get_marketplace_listings',
    'get_marketplace_item',
    'get_seller_listings',
    'create_listing',
    'submit_listing_for_review',
    'unpublish_listing',
    'update_listing',
    'check_user_purchase',
    'execute_purchase',
    'get_user_purchases',
    'get_seller_stats',
    'record_listing_usage',
    'get_leaderboard',
    # Asset functions
    'save_asset',
    'get_assets',
    'soft_delete_asset',
    'permanently_hide_asset',
    'restore_asset',
    'get_deleted_assets',
    'get_user_deleted_assets',  # Alias for backward compatibility
    'increment_asset_usage',
    'get_dashboard_assets',
    'get_seller_asset_stats',
    'get_system_resources',
    # Notification functions
    'get_user_notifications',
    'mark_notification_read',
    'mark_all_notifications_read',
    'create_broadcast',
    'send_notification_to_user',
    'send_notification_to_users',
    'get_all_notification_stats',
    'get_notification_history',
    # Support functions
    'create_support_ticket',
    'send_support_email',
    'send_feedback_with_images',
    'create_report',
    'get_user_reports',
]

# ==========================================
# Notification Functions
# ==========================================


@async_to_sync
async def get_user_notifications(user_id: str, unread_only: bool = False, limit: int = 20):
    """Get user notifications."""
    repo = _get_repo(SupabaseNotificationRepositoryExtended)
    return await repo.get_user_notifications(user_id, unread_only, limit)

@async_to_sync
async def mark_notification_read(notification_id: str, user_id: str):
    """Mark notification as read."""
    repo = _get_repo(SupabaseNotificationRepositoryExtended)
    return await repo.mark_notification_read(notification_id, user_id)

@async_to_sync
async def mark_all_notifications_read(user_id: str):
    """Mark all notifications as read."""
    repo = _get_repo(SupabaseNotificationRepositoryExtended)
    return await repo.mark_all_notifications_read(user_id)

@async_to_sync
async def create_broadcast(title: str, content: str, target_group: str = "all"):
    """Create broadcast notification."""
    repo = _get_repo(SupabaseNotificationRepositoryExtended)
    return await repo.create_broadcast(title, content, target_group)

@async_to_sync
async def send_notification_to_user(user_id: str, title: str, content: str, notification_type: str = "system"):
    """Send notification to single user."""
    repo = _get_repo(SupabaseNotificationRepositoryExtended)
    return await repo.send_notification_to_user(user_id, title, content, notification_type)

@async_to_sync
async def send_notification_to_users(user_ids: list, title: str, content: str, notification_type: str = "system"):
    """Send notification to multiple users."""
    repo = _get_repo(SupabaseNotificationRepositoryExtended)
    return await repo.send_notification_to_users(user_ids, title, content, notification_type)

@async_to_sync
async def get_all_notification_stats():
    """Get notification statistics."""
    repo = _get_repo(SupabaseNotificationRepositoryExtended)
    return await repo.get_all_notification_stats()

@async_to_sync
async def get_notification_history(page: int = 1, limit: int = 50, notification_type: str = None):
    """Get notification history (admin)."""
    repo = _get_repo(SupabaseNotificationRepositoryExtended)
    return await repo.get_notification_history(page, limit, notification_type)

# ==========================================
# Support Functions
# ==========================================

@async_to_sync
async def create_support_ticket(user_id: str, email: str, message: str):
    """Create support ticket."""
    repo = _get_repo(SupabaseSupportRepositoryExtended)
    return await repo.create_support_ticket(user_id, email, message)

def send_support_email(user_id: str, user_email: str, message: str, images: list = None):
    """Send support email (synchronous)."""
    repo = _get_repo(SupabaseSupportRepositoryExtended)
    return repo.send_support_email(user_id, user_email, message, images)

def send_feedback_with_images(user_id: str, user_email: str, message: str, images: list = None):
    """Send feedback with images (synchronous)."""
    repo = _get_repo(SupabaseSupportRepositoryExtended)
    return repo.send_feedback_with_images(user_id, user_email, message, images)

@async_to_sync
async def create_report(reporter_id: str, listing_id: str, reason: str):
    """Create content report."""
    repo = _get_repo(SupabaseSupportRepositoryExtended)
    return await repo.create_report(reporter_id, listing_id, reason)

@async_to_sync
async def get_user_reports(user_id: str, page: int = 1, limit: int = 20):
    """Get user's reports."""
    repo = _get_repo(SupabaseSupportRepositoryExtended)
    return await repo.get_user_reports(user_id, page, limit)
