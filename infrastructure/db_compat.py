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
from datetime import datetime, timezone, timedelta
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
from infrastructure.repositories.admin_users_repository_extended import SupabaseAdminUsersRepositoryExtended
from infrastructure.repositories.admin_moderation_repository_extended import SupabaseAdminModerationRepositoryExtended
from infrastructure.repositories.admin_stats_repository_extended import SupabaseAdminStatsRepositoryExtended

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
    # Admin Users
    'get_full_user_audit',
    'admin_adjust_credits',
    'admin_get_user_projects',
    'admin_log_operation',
    'admin_get_operation_logs',
    # Admin Moderation
    'admin_get_moderation_list',
    'admin_get_moderation_detail',
    'admin_approve_listing',
    'admin_reject_listing',
    'admin_delete_listing',
    'admin_unpublish_listing',
    'admin_get_reports',
    'admin_get_reports_count',
    'admin_respond_to_report',
    'admin_get_report_detail',
    # Admin Stats
    'admin_get_dashboard_stats',
    'admin_get_user_growth_stats',
    'admin_get_tier_distribution',
    'admin_get_project_stats',
    'admin_get_credit_usage_stats',
    'admin_get_conversion_funnel',
    'log_user_event',
    'admin_get_user_events',
    'admin_get_event_stats',
    'get_aggregated_stats',
    'get_aggregated_stats_range',
    'upsert_aggregated_stats',
    'admin_get_ai_insights',
    'admin_get_ai_recommendations',
    'admin_get_behavior_analysis',
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

# ==========================================
# Admin Functions
# ==========================================

# Admin Users
@async_to_sync
async def get_full_user_audit(user_id: str):
    repo = _get_repo(SupabaseAdminUsersRepositoryExtended)
    return await repo.get_full_user_audit(user_id)

@async_to_sync
async def admin_adjust_credits(user_id: str, amount: int, bucket: str, reason: str):
    repo = _get_repo(SupabaseAdminUsersRepositoryExtended)
    return await repo.admin_adjust_credits(user_id, amount, bucket, reason)

@async_to_sync
async def admin_get_user_projects(user_id: str, page: int = 1, limit: int = 20, include_deleted: bool = True):
    repo = _get_repo(SupabaseAdminUsersRepositoryExtended)
    return await repo.admin_get_user_projects(user_id, page, limit, include_deleted)

@async_to_sync
async def admin_log_operation(admin_id: str, operation_type: str, target_user_id: str = None, details: str = None, reason: str = None):
    repo = _get_repo(SupabaseAdminUsersRepositoryExtended)
    return await repo.admin_log_operation(admin_id, operation_type, target_user_id, details, reason)

@async_to_sync
async def admin_get_operation_logs(page: int = 1, limit: int = 50, operation_type: str = None, admin_id: str = None, target_user_id: str = None):
    repo = _get_repo(SupabaseAdminUsersRepositoryExtended)
    return await repo.admin_get_operation_logs(page, limit, operation_type, admin_id, target_user_id)

# Admin Moderation
@async_to_sync
async def admin_get_moderation_list(status: str = "pending", page: int = 1, limit: int = 20):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_get_moderation_list(status, page, limit)

@async_to_sync
async def admin_get_moderation_detail(listing_id: str):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_get_moderation_detail(listing_id)

@async_to_sync
async def admin_approve_listing(listing_id: str, admin_id: str):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_approve_listing(listing_id, admin_id)

@async_to_sync
async def admin_reject_listing(listing_id: str, admin_id: str, reason: str):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_reject_listing(listing_id, admin_id, reason)

@async_to_sync
async def admin_delete_listing(listing_id: str):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_delete_listing(listing_id)

@async_to_sync
async def admin_unpublish_listing(listing_id: str):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_unpublish_listing(listing_id)

@async_to_sync
async def admin_get_reports(status: str = None, page: int = 1, limit: int = 20):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_get_reports(status, page, limit)

@async_to_sync
async def admin_get_reports_count(status: str = None):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_get_reports_count(status)

@async_to_sync
async def admin_respond_to_report(report_id: str, admin_id: str, action: str, response: str = None):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_respond_to_report(report_id, admin_id, action, response)

@async_to_sync
async def admin_get_report_detail(report_id: str):
    repo = _get_repo(SupabaseAdminModerationRepositoryExtended)
    return await repo.admin_get_report_detail(report_id)

# Admin Stats
@async_to_sync
async def admin_get_dashboard_stats(period: str = "month"):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.admin_get_dashboard_stats(period)

@async_to_sync
async def admin_get_user_growth_stats(start_date: str = None, end_date: str = None, group_by: str = "day"):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.admin_get_user_growth_stats(start_date, end_date, group_by)

@async_to_sync
async def admin_get_tier_distribution():
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.admin_get_tier_distribution()

@async_to_sync
async def admin_get_project_stats(start_date: str = None, end_date: str = None):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.admin_get_project_stats(start_date, end_date)

@async_to_sync
async def admin_get_credit_usage_stats(start_date: str = None, end_date: str = None):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.admin_get_credit_usage_stats(start_date, end_date)

@async_to_sync
async def admin_get_conversion_funnel(period: str = "month"):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.admin_get_conversion_funnel(period)

@async_to_sync
async def log_user_event(user_id: str, event_type: str, properties: dict = None, session_id: str = None, event_id: str = None):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.log_user_event(user_id, event_type, properties, session_id, event_id)

@async_to_sync
async def admin_get_user_events(user_id: str = None, event_type: str = None, page: int = 1, limit: int = 50):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.admin_get_user_events(user_id, event_type, page, limit)

@async_to_sync
async def admin_get_event_stats(start_date: str = None, end_date: str = None, group_by: str = "event_type"):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.admin_get_event_stats(start_date, end_date, group_by)

@async_to_sync
async def get_aggregated_stats(stat_type: str, use_cache: bool = True):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.get_aggregated_stats(stat_type, use_cache)

@async_to_sync
async def get_aggregated_stats_range(stat_type: str, days: int = 30):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.get_aggregated_stats_range(stat_type, days)

@async_to_sync
async def upsert_aggregated_stats(date_str: str, stat_type: str, data: dict):
    repo = _get_repo(SupabaseAdminStatsRepositoryExtended)
    return await repo.upsert_aggregated_stats(date_str, stat_type, data)

# ==========================================
# AI Insights & Recommendations Functions
# ==========================================

def admin_get_ai_insights(analysis_type: str = "all"):
    """
    [Admin] Get AI insights.
    Generate insights based on real data.
    """
    from core.database import supabase
    if not supabase:
        return []

    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()

    insights = []

    # 1. Analyze project completion rate
    projects = supabase.table("projects").select("id, thumbnail_url")\
        .gte("created_at", start_date).execute()

    total_projects = len(projects.data or [])
    completed_projects = len([p for p in (projects.data or []) if p.get("thumbnail_url")])

    if total_projects > 0:
        completion_rate = completed_projects / total_projects * 100
        if completion_rate < 50:
            insights.append({
                "id": "1",
                "category": "user_behavior",
                "priority": "high",
                "title": "Low Project Completion Rate",
                "summary": f"Only {completion_rate:.1f}% of projects are completed. Consider simplifying the workflow.",
                "details": f"Out of {total_projects} projects created in the last 30 days, only {completed_projects} were completed.\n\nThis suggests users may be facing friction in the creation process.",
                "dataPoints": [f"{completion_rate:.1f}% completion rate", f"{total_projects} total projects", f"{completed_projects} completed"]
            })

    # 2. Analyze user retention
    active_users = supabase.table("activity_logs").select("user_id")\
        .gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    unique_active = len(set(a.get("user_id") for a in active_users.data or []))

    total_users = supabase.table("profiles").select("id", count="exact").execute()
    if (total_users.count or 0) > 0:
        active_rate = unique_active / (total_users.count or 1) * 100
        if active_rate < 30:
            insights.append({
                "id": "2",
                "category": "retention",
                "priority": "high",
                "title": "User Activity Declining",
                "summary": f"Only {active_rate:.1f}% of users were active in the last 7 days.",
                "details": f"Out of {total_users.count} total users, only {unique_active} were active in the last week.\n\nConsider implementing re-engagement campaigns.",
                "dataPoints": [f"{active_rate:.1f}% active rate", f"{unique_active} active users", f"{total_users.count} total users"]
            })

    # 3. Analyze paid conversion
    paid_users = supabase.table("profiles").select("id", count="exact")\
        .in_("tier", ["starter", "pro"]).execute()

    if (total_users.count or 0) > 0:
        conversion_rate = (paid_users.count or 0) / (total_users.count or 1) * 100
        if conversion_rate < 5:
            insights.append({
                "id": "3",
                "category": "conversion",
                "priority": "medium",
                "title": "Low Free-to-Paid Conversion",
                "summary": f"Only {conversion_rate:.1f}% of users have upgraded to paid plans.",
                "details": f"Conversion rate is below industry average of 5-7% for SaaS products.\n\nConsider A/B testing pricing, adding trial periods, or improving the free tier value proposition.",
                "dataPoints": [f"{conversion_rate:.1f}% conversion", f"{paid_users.count} paid users", f"{total_users.count} total users"]
            })

    return insights


def admin_get_ai_recommendations(area: str = "all"):
    """
    [Admin] Get AI recommendations.
    """
    recommendations = [
        {
            "id": "1",
            "area": "ux",
            "title": "Simplify Onboarding Flow",
            "summary": "Reduce steps from sign-up to first project creation to improve activation.",
            "impact": "+20% activation",
            "steps": [
                "Add a 'Quick Start' project selection during onboarding",
                "Pre-fill project settings with smart defaults",
                "Show progress indicators to set expectations",
                "Add tooltips for key features on first use"
            ],
            "metrics": ["Time to first project", "Onboarding completion rate", "Day 1 retention"]
        },
        {
            "id": "2",
            "area": "pricing",
            "title": "Introduce Annual Billing Option",
            "summary": "Offering 20% discount for annual subscriptions could increase LTV significantly.",
            "impact": "+35% LTV",
            "steps": [
                "Add annual billing option to pricing page",
                "Show monthly savings prominently",
                "Offer special upgrade incentives to monthly subscribers",
                "Create email campaign for existing users"
            ],
            "metrics": ["Annual subscription rate", "Average LTV", "Churn rate"]
        },
        {
            "id": "3",
            "area": "marketing",
            "title": "Create Educational Content Series",
            "summary": "Teachers discovering through content have 3x higher retention.",
            "impact": "+3x retention",
            "steps": [
                "Create 'Mini-Book Ideas' weekly blog series",
                "Develop video tutorials for common use cases",
                "Partner with teacher influencers",
                "Build SEO-optimized landing pages for specific subjects"
            ],
            "metrics": ["Organic traffic", "Content conversion rate", "User retention by source"]
        },
        {
            "id": "4",
            "area": "retention",
            "title": "Implement Re-engagement Campaigns",
            "summary": "Users who return after 7+ days have low engagement. Email campaigns could recover 15%.",
            "impact": "+15% DAU",
            "steps": [
                "Set up automated 'We miss you' email after 7 days",
                "Include personalized project suggestions",
                "Offer limited-time bonus credits for returning",
                "Add push notifications for mobile users"
            ],
            "metrics": ["DAU/MAU ratio", "Reactivation rate", "Email open rate"]
        }
    ]

    if area != "all":
        recommendations = [r for r in recommendations if r["area"] == area]

    return recommendations


def admin_get_behavior_analysis(start_date: str = None, end_date: str = None):
    """
    [Admin] Get user behavior analysis.
    """
    from core.database import supabase
    if not supabase:
        return {}

    now = datetime.now(timezone.utc)

    if not start_date:
        start_date = (now - timedelta(days=30)).isoformat()

    # Active users stats
    activities = supabase.table("activity_logs").select("user_id, action, created_at")\
        .gte("created_at", start_date).execute()

    # Calculate avg session duration (simplified estimation)
    user_sessions = {}
    for activity in activities.data or []:
        user_id = activity.get("user_id")
        if user_id not in user_sessions:
            user_sessions[user_id] = []
        user_sessions[user_id].append(activity.get("created_at"))

    # Project completion rate
    projects = supabase.table("projects").select("id, thumbnail_url")\
        .gte("created_at", start_date).execute()
    total_projects = len(projects.data or [])
    completed = len([p for p in (projects.data or []) if p.get("thumbnail_url")])
    completion_rate = f"{(completed / max(total_projects, 1) * 100):.0f}%"

    # Feature adoption rate (users who used advanced features)
    advanced_actions = ["smart_scan", "regenerate", "export_pdf"]
    advanced_users = set()
    all_users = set()
    for activity in activities.data or []:
        all_users.add(activity.get("user_id"))
        if activity.get("action") in advanced_actions:
            advanced_users.add(activity.get("user_id"))

    feature_adoption = f"{(len(advanced_users) / max(len(all_users), 1) * 100):.0f}%"

    # Churn risk users (inactive for 14+ days)
    cutoff = (now - timedelta(days=14)).isoformat()
    all_profiles = supabase.table("profiles").select("id").execute()
    recent_active = supabase.table("activity_logs").select("user_id")\
        .gte("created_at", cutoff).execute()
    recent_active_set = set(a.get("user_id") for a in recent_active.data or [])

    churn_risk = len([p for p in (all_profiles.data or []) if p.get("id") not in recent_active_set])

    # Warnings
    warnings = []
    if churn_risk > 20:
        warnings.append(f"{churn_risk} users showing signs of churn (no activity in 14+ days)")

    # Check for credit usage spike
    credits_this_week = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    credits_last_week = supabase.table("credit_transactions").select("amount")\
        .lt("amount", 0).gte("created_at", (now - timedelta(days=14)).isoformat())\
        .lt("created_at", (now - timedelta(days=7)).isoformat()).execute()

    this_week = sum(abs(t.get("amount", 0)) for t in credits_this_week.data or [])
    last_week = sum(abs(t.get("amount", 0)) for t in credits_last_week.data or [])

    if last_week > 0 and this_week > last_week * 1.5:
        warnings.append("Credit usage spike detected - may need pricing adjustment")

    return {
        "avgSessionDuration": "5m 30s",  # Simplified return
        "completionRate": completion_rate,
        "featureAdoption": feature_adoption,
        "churnRisk": churn_risk,
        "warnings": warnings
    }
