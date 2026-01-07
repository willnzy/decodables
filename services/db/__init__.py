"""
Database Service Package

Modular database operations organized by domain.

@package services.db
@version 3.24
"""

# Core - Client and utilities
from core.database import supabase, retry_on_network_error, is_retryable_error
from .utils import (
    is_member,
    can_access_resource,
    get_total_credits,
    publish_permission,
    validate_allowed_tiers,
    listing_is_public_visible,
    log_activity,
)

# Users, Projects & Marketplace - Now imported from infrastructure.db_compat
from infrastructure.db_compat import (
    # User functions
    get_user_profile,
    create_user_profile,
    update_subscription_tier,
    update_user_profile,
    update_user_timezone,
    get_user_timezone,
    refresh_monthly_credits,
    check_and_reset_monthly_credits_if_needed,
    log_credit_transaction,
    credit_deduct,
    add_credits_permanent,
    add_credits_monthly,
    add_credits,
    get_credit_history,
    search_users,
    get_users_by_tier,
    get_user_discount,
    create_user_discount,
    generate_user_code,
    # Project functions
    get_user_projects,
    count_user_projects,
    get_project_detail,
    create_project,
    duplicate_project,
    save_project,
    soft_delete_project,
    restore_project,
    user_restore_project,
    get_user_deleted_projects,
    permanently_hide_project,
    update_project_hash,
    get_all_projects_feed,
    get_dashboard_projects,
    get_seller_project_stats,
    # Marketplace functions
    get_marketplace_listings,
    get_marketplace_item,
    get_seller_listings,
    create_listing,
    submit_listing_for_review,
    unpublish_listing,
    update_listing,
    check_user_purchase,
    execute_purchase,
    get_user_purchases,
    get_seller_stats,
    record_listing_usage,
    get_leaderboard,
    # Asset functions
    save_asset,
    get_assets,
    soft_delete_asset,
    permanently_hide_asset,
    restore_asset,
    get_deleted_assets,
    get_user_deleted_assets,  # Alias for backward compatibility
    increment_asset_usage,
    get_dashboard_assets,
    get_seller_asset_stats,
    get_system_resources,
)

# Notifications
from .notifications import (
    get_user_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    create_broadcast,
    send_notification_to_user,
    send_notification_to_users,
    get_all_notification_stats,
    get_notification_history,
)

# Support
from .support import (
    create_support_ticket,
    send_support_email,
    send_feedback_with_images,
    create_report,
    get_user_reports,
)

# Payments
from .payments import (
    log_payment_record,
    get_user_payments,
    admin_get_all_payments,
    get_payment_by_stripe_id,
    update_payment_status,
    admin_get_revenue_stats,
)

# Admin - Users
from .admin_users import (
    get_full_user_audit,
    admin_adjust_credits,
    admin_get_user_projects,
    admin_log_operation,
    admin_get_operation_logs,
)

# Admin - Moderation
from .admin_moderation import (
    admin_get_moderation_list,
    admin_get_moderation_detail,
    admin_approve_listing,
    admin_reject_listing,
    admin_delete_listing,
    admin_unpublish_listing,
    admin_get_reports,
    admin_get_reports_count,
    admin_respond_to_report,
    admin_get_report_detail,
)

# Admin - Stats
from .admin_stats import (
    admin_get_dashboard_stats,
    admin_get_user_growth_stats,
    admin_get_tier_distribution,
    admin_get_project_stats,
    admin_get_credit_usage_stats,
    admin_get_conversion_funnel,
    log_user_event,
    admin_get_user_events,
    admin_get_event_stats,
    get_aggregated_stats,
    get_aggregated_stats_range,
    upsert_aggregated_stats,
    admin_get_ai_insights,
    admin_get_ai_recommendations,
    admin_get_behavior_analysis,
)

# Config
from .config import (
    get_system_config,
    get_all_system_configs,
    get_configs_by_group,
    admin_get_system_configs,
    admin_get_config_groups,
    admin_create_system_config,
    admin_update_system_config,
    admin_delete_system_config,
    admin_get_config_audit_logs,
    invalidate_config_cache_api,
    # Backward-compatible aliases
    get_public_configs,
    get_config_by_key,
    get_config_group,
)

__all__ = [
    # Core
    'supabase', 'retry_on_network_error', 'is_retryable_error',
    'is_member', 'can_access_resource', 'get_total_credits',
    'publish_permission', 'validate_allowed_tiers', 'listing_is_public_visible',
    'log_activity',
    
    # Users
    'get_user_profile', 'create_user_profile', 'update_subscription_tier',
    'update_user_profile', 'update_user_timezone', 'get_user_timezone',
    'generate_user_code', 'refresh_monthly_credits',
    'check_and_reset_monthly_credits_if_needed', 'log_credit_transaction',
    'credit_deduct', 'add_credits_permanent', 'add_credits_monthly', 'add_credits',
    'get_credit_history', 'search_users', 'get_users_by_tier',
    'get_user_discount', 'create_user_discount',
    
    # Projects
    'get_user_projects', 'count_user_projects', 'get_project_detail',
    'create_project', 'duplicate_project', 'save_project',
    'soft_delete_project', 'restore_project', 'user_restore_project',
    'get_user_deleted_projects', 'permanently_hide_project',
    'update_project_hash', 'get_all_projects_feed',
    'get_dashboard_projects', 'get_seller_project_stats',
    
    # Assets
    'save_asset', 'get_assets', 'soft_delete_asset', 'permanently_hide_asset',
    'restore_asset', 'get_user_deleted_assets', 'increment_asset_usage',
    'get_dashboard_assets', 'get_seller_asset_stats', 'get_system_resources',
    
    # Marketplace
    'get_marketplace_listings', 'get_marketplace_item', 'get_seller_listings',
    'create_listing', 'submit_listing_for_review', 'unpublish_listing',
    'update_listing', 'check_user_purchase', 'execute_purchase',
    'get_user_purchases', 'get_seller_stats', 'record_listing_usage', 'get_leaderboard',
    
    # Notifications
    'get_user_notifications', 'mark_notification_read', 'mark_all_notifications_read',
    'create_broadcast', 'send_notification_to_user', 'send_notification_to_users',
    'get_all_notification_stats', 'get_notification_history',
    
    # Support
    'create_support_ticket', 'send_support_email', 'send_feedback_with_images',
    'create_report', 'get_user_reports',
    
    # Payments
    'log_payment_record', 'get_user_payments', 'admin_get_all_payments',
    'get_payment_by_stripe_id', 'update_payment_status', 'admin_get_revenue_stats',
    
    # Admin Users
    'get_full_user_audit', 'admin_adjust_credits', 'admin_get_user_projects',
    'admin_log_operation', 'admin_get_operation_logs',
    
    # Admin Moderation
    'admin_get_moderation_list', 'admin_get_moderation_detail',
    'admin_approve_listing', 'admin_reject_listing',
    'admin_delete_listing', 'admin_unpublish_listing',
    'admin_get_reports', 'admin_get_reports_count',
    'admin_respond_to_report', 'admin_get_report_detail',
    
    # Admin Stats
    'admin_get_dashboard_stats', 'admin_get_user_growth_stats',
    'admin_get_tier_distribution', 'admin_get_project_stats',
    'admin_get_credit_usage_stats', 'admin_get_conversion_funnel',
    'log_user_event', 'admin_get_user_events', 'admin_get_event_stats',
    'get_aggregated_stats', 'get_aggregated_stats_range', 'upsert_aggregated_stats',
    'admin_get_ai_insights', 'admin_get_ai_recommendations', 'admin_get_behavior_analysis',
    
    # Config
    'get_system_config', 'get_all_system_configs', 'get_configs_by_group',
    'admin_get_system_configs', 'admin_get_config_groups',
    'admin_create_system_config', 'admin_update_system_config',
    'admin_delete_system_config', 'admin_get_config_audit_logs',
    'invalidate_config_cache_api',
    # Backward-compatible aliases
    'get_public_configs', 'get_config_by_key', 'get_config_group',
]
