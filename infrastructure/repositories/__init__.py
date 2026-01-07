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
from .user_repository_extended import SupabaseUserRepositoryExtended
from .credit_repository_extended import SupabaseCreditRepositoryExtended
from .project_repository_extended import SupabaseProjectRepositoryExtended
from .asset_repository_extended import SupabaseAssetRepositoryExtended
from .notification_repository_extended import SupabaseNotificationRepositoryExtended
from .support_repository_extended import SupabaseSupportRepositoryExtended
from .admin_users_repository_extended import SupabaseAdminUsersRepositoryExtended
from .admin_moderation_repository_extended import SupabaseAdminModerationRepositoryExtended
from .admin_stats_repository_extended import SupabaseAdminStatsRepositoryExtended

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
    'SupabaseUserRepositoryExtended',
    'SupabaseCreditRepositoryExtended',
    'SupabaseProjectRepositoryExtended',
    'SupabaseAssetRepositoryExtended',
    'SupabaseNotificationRepositoryExtended',
    'SupabaseSupportRepositoryExtended',
    'SupabaseAdminUsersRepositoryExtended',
    'SupabaseAdminModerationRepositoryExtended',
    'SupabaseAdminStatsRepositoryExtended',
]
