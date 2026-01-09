"""
Repository Implementations - Supabase/PostgreSQL data access.

@package infrastructure.repositories
@version 1.0.0
"""

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

__all__ = [
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
]
