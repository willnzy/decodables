"""
Repository Implementations - Supabase/PostgreSQL data access.

@package infrastructure.repositories
@version 1.0.0
"""

# Base Repository
from .base_repository import BaseRepository

# Field Mappings (Single Source of Truth)
from .field_mappings import (
    PROFILES_DB_TO_DOMAIN,
    CREDIT_TX_DB_TO_DOMAIN,
    PROJECTS_DB_TO_DOMAIN,
    LISTINGS_DB_TO_DOMAIN,
    PURCHASES_DB_TO_DOMAIN,
    CONFIGS_DB_TO_DOMAIN,
    map_db_to_domain,
    map_domain_to_db,
    get_db_fields,
    get_domain_fields,
    validate_db_record,
)

# Repository Implementations
from .credit_repository import SupabaseCreditRepository
from .user_repository import SupabaseUserRepository
from .project_repository import SupabaseProjectRepository
from .listing_repository import SupabaseListingRepository
from .feature_flag_repository import SupabaseFeatureFlagRepository
from .experiment_repository import SupabaseExperimentRepository
from .system_resource_repository import SupabaseSystemResourceRepository
from .config_repository import SupabaseConfigRepository
from .payment_repository import SupabasePaymentRepository
from .asset_repository import SupabaseAssetRepository
from .notification_repository import SupabaseNotificationRepository
from .support_repository import SupabaseSupportRepository
from .admin_repository import (
    SupabaseAdminUsersRepository,
    SupabaseAdminModerationRepository,
    SupabaseAdminStatsRepository,
)
from .tasks_repository import SupabaseTasksRepository
from .error_logs_repository import SupabaseErrorLogsRepository
from .analytics_repository import SupabaseAnalyticsRepository
from .subscription_repository import SupabaseSubscriptionRepository
from .metrics_repository import SupabaseMetricsRepository
from .webhook_repository import SupabaseWebhookRepository
from .article_repository import SupabaseArticleRepository
from .static_page_repository import SupabaseStaticPageRepository
from .notification_template_repository import SupabaseNotificationTemplateRepository
from .workspace_repository import SupabaseWorkspaceRepository
from .folder_repository import SupabaseFolderRepository
from .activity_log_repository import ActivityLogRepository

__all__ = [
    # Base Repository
    'BaseRepository',
    # Field Mappings
    'PROFILES_DB_TO_DOMAIN',
    'CREDIT_TX_DB_TO_DOMAIN',
    'PROJECTS_DB_TO_DOMAIN',
    'LISTINGS_DB_TO_DOMAIN',
    'PURCHASES_DB_TO_DOMAIN',
    'CONFIGS_DB_TO_DOMAIN',
    'map_db_to_domain',
    'map_domain_to_db',
    'get_db_fields',
    'get_domain_fields',
    'validate_db_record',
    # Repository Implementations
    'SupabaseCreditRepository',
    'SupabaseUserRepository',
    'SupabaseProjectRepository',
    'SupabaseListingRepository',
    'SupabaseFeatureFlagRepository',
    'SupabaseExperimentRepository',
    'SupabaseSystemResourceRepository',
    'SupabaseConfigRepository',
    'SupabasePaymentRepository',
    'SupabaseAssetRepository',
    'SupabaseNotificationRepository',
    'SupabaseSupportRepository',
    'SupabaseAdminUsersRepository',
    'SupabaseAdminModerationRepository',
    'SupabaseAdminStatsRepository',
    'SupabaseTasksRepository',
    'SupabaseErrorLogsRepository',
    'SupabaseAnalyticsRepository',
    'SupabaseSubscriptionRepository',
    'SupabaseMetricsRepository',
    'SupabaseWebhookRepository',
    'SupabaseArticleRepository',
    'SupabaseStaticPageRepository',
    'SupabaseNotificationTemplateRepository',
    'SupabaseWorkspaceRepository',
    'SupabaseFolderRepository',
    'ActivityLogRepository',
]
