"""
Dependency Injection Container - Centralized service instantiation.

@module container
@version 1.0.0

This module provides a simple dependency injection container that:
- Creates and caches service instances
- Manages repository and service dependencies
- Supports lazy initialization
"""

from typing import Optional, TypeVar, Type
from functools import lru_cache
import logging

# Infrastructure - Repositories
from infrastructure.repositories import (
    SupabaseCreditRepository,
    SupabaseUserRepository,
    SupabaseProjectRepository,
    SupabaseListingRepository,
    SupabaseFeatureFlagRepository,
    SupabaseExperimentRepository,
)

# Domains - Services
from domains.billing import BillingService, ICreditRepository
from domains.identity import IdentityService, IUserRepository
from domains.creation import CreationService, IProjectRepository
from domains.marketplace import MarketplaceService, IListingRepository
from domains.platform import (
    PlatformService,
    IFeatureFlagRepository,
    IExperimentRepository,
)
from domains.support import SupportService  # v3.0.0

# Application - Command Handlers
from application.commands.billing import (
    DeductCreditsHandler,
    AddCreditsHandler,
    GrantSignupBonusHandler,
)
from application.commands.identity import (
    CreateUserHandler,
    UpdateUserProfileHandler,
    UpdateUserTierHandler,
)
from application.commands.creation import (
    CreateProjectHandler,
    UpdateProjectHandler,
    DeleteProjectHandler,
    RestoreProjectHandler,
)
from application.commands.marketplace import (
    CreateListingHandler,
    UpdateListingHandler,
    UnpublishListingHandler,
    PurchaseListingHandler,
    CreateReportHandler,  # v3.0.0
)
from application.commands.platform import (
    CreateFeatureFlagHandler,
    CreateExperimentHandler,
)

# Application - Query Handlers
from application.queries.billing import (
    GetUserCreditsHandler,
    GetTransactionHistoryHandler,
)
from application.queries.identity import GetUserProfileHandler
from application.queries.creation import (
    GetProjectHandler,
    GetUserProjectsHandler,
    GetDashboardProjectsHandler,
)
from application.queries.marketplace import (
    GetListingHandler,
    SearchListingsHandler,
    GetMyListingsHandler,  # v3.0.0
    GetSellerStatsHandler,  # v3.0.0
    GetLeaderboardHandler,  # v3.0.0
    GetMyReportsHandler,  # v3.0.0
)
from application.queries.platform import (
    EvaluateFeatureFlagHandler,
    GetExperimentVariantHandler,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Container:
    """
    Dependency Injection Container.

    Provides centralized service instantiation with lazy initialization.
    All instances are cached as singletons.
    """

    _instance: Optional['Container'] = None
    _repositories: dict = {}
    _services: dict = {}
    _handlers: dict = {}

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize container (only once)."""
        if self._initialized:
            return
        self._repositories = {}
        self._services = {}
        self._handlers = {}
        self._initialized = True
        logger.info("[Container] Dependency injection container initialized")

    # ========== Repositories ==========

    @property
    def credit_repository(self) -> ICreditRepository:
        """Get credit repository instance."""
        if 'credit' not in self._repositories:
            self._repositories['credit'] = SupabaseCreditRepository()
        return self._repositories['credit']

    @property
    def user_repository(self) -> IUserRepository:
        """Get user repository instance."""
        if 'user' not in self._repositories:
            self._repositories['user'] = SupabaseUserRepository()
        return self._repositories['user']

    @property
    def project_repository(self) -> IProjectRepository:
        """Get project repository instance."""
        if 'project' not in self._repositories:
            self._repositories['project'] = SupabaseProjectRepository()
        return self._repositories['project']

    @property
    def listing_repository(self) -> IListingRepository:
        """Get listing repository instance."""
        if 'listing' not in self._repositories:
            self._repositories['listing'] = SupabaseListingRepository()
        return self._repositories['listing']

    @property
    def feature_flag_repository(self) -> IFeatureFlagRepository:
        """Get feature flag repository instance."""
        if 'feature_flag' not in self._repositories:
            self._repositories['feature_flag'] = SupabaseFeatureFlagRepository()
        return self._repositories['feature_flag']

    @property
    def experiment_repository(self) -> IExperimentRepository:
        """Get experiment repository instance."""
        if 'experiment' not in self._repositories:
            self._repositories['experiment'] = SupabaseExperimentRepository()
        return self._repositories['experiment']

    # ========== Domain Services ==========

    @property
    def billing_service(self) -> BillingService:
        """Get billing service instance."""
        if 'billing' not in self._services:
            self._services['billing'] = BillingService(self.credit_repository)
        return self._services['billing']

    @property
    def identity_service(self) -> IdentityService:
        """Get identity service instance."""
        if 'identity' not in self._services:
            self._services['identity'] = IdentityService(self.user_repository)
        return self._services['identity']

    @property
    def creation_service(self) -> CreationService:
        """Get creation service instance."""
        if 'creation' not in self._services:
            self._services['creation'] = CreationService(self.project_repository)
        return self._services['creation']

    @property
    def marketplace_service(self) -> MarketplaceService:
        """Get marketplace service instance."""
        if 'marketplace' not in self._services:
            self._services['marketplace'] = MarketplaceService(self.listing_repository)
        return self._services['marketplace']

    @property
    def platform_service(self) -> PlatformService:
        """Get platform service instance."""
        if 'platform' not in self._services:
            self._services['platform'] = PlatformService(
                flag_repository=self.feature_flag_repository,
                experiment_repository=self.experiment_repository,
            )
        return self._services['platform']

    @property
    def support_service(self) -> SupportService:
        """Get support service instance (v3.0.0)."""
        from core.database import get_database_client
        if 'support' not in self._services:
            self._services['support'] = SupportService(get_database_client())
        return self._services['support']

    @property
    def logging_service(self):
        """Get logging service instance (v3.0.0)."""
        from core.database import get_database_client
        from domains.logging import LoggingService
        if 'logging' not in self._services:
            self._services['logging'] = LoggingService(get_database_client())
        return self._services['logging']

    @property
    def themes_service(self):
        """Get themes service instance (v3.0.0)."""
        from core.database import get_database_client
        from domains.themes import ThemesService
        if 'themes' not in self._services:
            self._services['themes'] = ThemesService(get_database_client())
        return self._services['themes']

    # ========== Command Handlers ==========

    @property
    def deduct_credits_handler(self) -> DeductCreditsHandler:
        """Get deduct credits handler."""
        if 'deduct_credits' not in self._handlers:
            self._handlers['deduct_credits'] = DeductCreditsHandler(self.billing_service)
        return self._handlers['deduct_credits']

    @property
    def add_credits_handler(self) -> AddCreditsHandler:
        """Get add credits handler."""
        if 'add_credits' not in self._handlers:
            self._handlers['add_credits'] = AddCreditsHandler(self.billing_service)
        return self._handlers['add_credits']

    @property
    def grant_signup_bonus_handler(self) -> GrantSignupBonusHandler:
        """Get grant signup bonus handler."""
        if 'grant_signup_bonus' not in self._handlers:
            self._handlers['grant_signup_bonus'] = GrantSignupBonusHandler(self.billing_service)
        return self._handlers['grant_signup_bonus']

    @property
    def create_user_handler(self) -> CreateUserHandler:
        """Get create user handler."""
        if 'create_user' not in self._handlers:
            self._handlers['create_user'] = CreateUserHandler(self.identity_service)
        return self._handlers['create_user']

    @property
    def update_user_profile_handler(self) -> UpdateUserProfileHandler:
        """Get update user profile handler."""
        if 'update_user_profile' not in self._handlers:
            self._handlers['update_user_profile'] = UpdateUserProfileHandler(self.identity_service)
        return self._handlers['update_user_profile']

    @property
    def update_user_tier_handler(self) -> UpdateUserTierHandler:
        """Get update user tier handler."""
        if 'update_user_tier' not in self._handlers:
            self._handlers['update_user_tier'] = UpdateUserTierHandler(self.identity_service)
        return self._handlers['update_user_tier']

    @property
    def create_project_handler(self) -> CreateProjectHandler:
        """Get create project handler."""
        if 'create_project' not in self._handlers:
            self._handlers['create_project'] = CreateProjectHandler(self.creation_service)
        return self._handlers['create_project']

    @property
    def update_project_handler(self) -> UpdateProjectHandler:
        """Get update project handler."""
        if 'update_project' not in self._handlers:
            self._handlers['update_project'] = UpdateProjectHandler(self.creation_service)
        return self._handlers['update_project']

    @property
    def delete_project_handler(self) -> DeleteProjectHandler:
        """Get delete project handler."""
        if 'delete_project' not in self._handlers:
            self._handlers['delete_project'] = DeleteProjectHandler(self.creation_service)
        return self._handlers['delete_project']

    @property
    def restore_project_handler(self) -> RestoreProjectHandler:
        """Get restore project handler."""
        if 'restore_project' not in self._handlers:
            self._handlers['restore_project'] = RestoreProjectHandler(self.creation_service)
        return self._handlers['restore_project']

    @property
    def create_listing_handler(self) -> CreateListingHandler:
        """Get create listing handler."""
        if 'create_listing' not in self._handlers:
            self._handlers['create_listing'] = CreateListingHandler(self.marketplace_service)
        return self._handlers['create_listing']

    @property
    def update_listing_handler(self) -> UpdateListingHandler:
        """Get update listing handler."""
        if 'update_listing' not in self._handlers:
            self._handlers['update_listing'] = UpdateListingHandler(self.marketplace_service)
        return self._handlers['update_listing']

    @property
    def unpublish_listing_handler(self) -> UnpublishListingHandler:
        """Get unpublish listing handler."""
        if 'unpublish_listing' not in self._handlers:
            self._handlers['unpublish_listing'] = UnpublishListingHandler(self.marketplace_service)
        return self._handlers['unpublish_listing']

    @property
    def purchase_listing_handler(self) -> PurchaseListingHandler:
        """Get purchase listing handler (cross-domain)."""
        if 'purchase_listing' not in self._handlers:
            self._handlers['purchase_listing'] = PurchaseListingHandler(
                marketplace_service=self.marketplace_service,
                billing_service=self.billing_service,
            )
        return self._handlers['purchase_listing']

    @property
    def create_feature_flag_handler(self) -> CreateFeatureFlagHandler:
        """Get create feature flag handler."""
        if 'create_feature_flag' not in self._handlers:
            self._handlers['create_feature_flag'] = CreateFeatureFlagHandler(self.platform_service)
        return self._handlers['create_feature_flag']

    @property
    def create_experiment_handler(self) -> CreateExperimentHandler:
        """Get create experiment handler."""
        if 'create_experiment' not in self._handlers:
            self._handlers['create_experiment'] = CreateExperimentHandler(self.platform_service)
        return self._handlers['create_experiment']

    @property
    def create_report_handler(self) -> CreateReportHandler:
        """Get create report handler (v3.0.0)."""
        if 'create_report' not in self._handlers:
            self._handlers['create_report'] = CreateReportHandler(self.support_service)
        return self._handlers['create_report']

    @property
    def create_error_log_handler(self):
        """Get create error log handler (v3.0.0)."""
        from application.commands.logging import CreateErrorLogHandler
        if 'create_error_log' not in self._handlers:
            self._handlers['create_error_log'] = CreateErrorLogHandler(self.logging_service)
        return self._handlers['create_error_log']

    @property
    def create_error_log_batch_handler(self):
        """Get create error log batch handler (v3.0.0)."""
        from application.commands.logging import CreateErrorLogBatchHandler
        if 'create_error_log_batch' not in self._handlers:
            self._handlers['create_error_log_batch'] = CreateErrorLogBatchHandler(self.logging_service)
        return self._handlers['create_error_log_batch']

    # ========== Query Handlers ==========

    @property
    def get_user_credits_handler(self) -> GetUserCreditsHandler:
        """Get user credits query handler."""
        if 'get_user_credits' not in self._handlers:
            self._handlers['get_user_credits'] = GetUserCreditsHandler(self.billing_service)
        return self._handlers['get_user_credits']

    @property
    def get_transaction_history_handler(self) -> GetTransactionHistoryHandler:
        """Get transaction history query handler."""
        if 'get_transaction_history' not in self._handlers:
            self._handlers['get_transaction_history'] = GetTransactionHistoryHandler(self.billing_service)
        return self._handlers['get_transaction_history']

    @property
    def get_user_profile_handler(self) -> GetUserProfileHandler:
        """Get user profile query handler."""
        if 'get_user_profile' not in self._handlers:
            self._handlers['get_user_profile'] = GetUserProfileHandler(self.identity_service)
        return self._handlers['get_user_profile']

    @property
    def get_project_handler(self) -> GetProjectHandler:
        """Get project query handler."""
        if 'get_project' not in self._handlers:
            self._handlers['get_project'] = GetProjectHandler(self.creation_service)
        return self._handlers['get_project']

    @property
    def get_current_theme_handler(self):
        """Get current theme query handler (v3.0.0)."""
        from application.queries.themes import GetCurrentThemeHandler
        if 'get_current_theme' not in self._handlers:
            self._handlers['get_current_theme'] = GetCurrentThemeHandler(self.themes_service)
        return self._handlers['get_current_theme']

    @property
    def get_user_projects_handler(self) -> GetUserProjectsHandler:
        """Get user projects query handler."""
        if 'get_user_projects' not in self._handlers:
            self._handlers['get_user_projects'] = GetUserProjectsHandler(self.creation_service)
        return self._handlers['get_user_projects']

    @property
    def get_dashboard_projects_handler(self) -> GetDashboardProjectsHandler:
        """Get dashboard projects query handler."""
        if 'get_dashboard_projects' not in self._handlers:
            self._handlers['get_dashboard_projects'] = GetDashboardProjectsHandler(self.project_repository)
        return self._handlers['get_dashboard_projects']

    @property
    def get_listing_handler(self) -> GetListingHandler:
        """Get listing query handler."""
        if 'get_listing' not in self._handlers:
            self._handlers['get_listing'] = GetListingHandler(self.marketplace_service)
        return self._handlers['get_listing']

    @property
    def search_listings_handler(self) -> SearchListingsHandler:
        """Get search listings query handler."""
        if 'search_listings' not in self._handlers:
            self._handlers['search_listings'] = SearchListingsHandler(self.marketplace_service)
        return self._handlers['search_listings']

    @property
    def evaluate_feature_flag_handler(self) -> EvaluateFeatureFlagHandler:
        """Get evaluate feature flag query handler."""
        if 'evaluate_feature_flag' not in self._handlers:
            self._handlers['evaluate_feature_flag'] = EvaluateFeatureFlagHandler(self.platform_service)
        return self._handlers['evaluate_feature_flag']

    @property
    def get_experiment_variant_handler(self) -> GetExperimentVariantHandler:
        """Get experiment variant query handler."""
        if 'get_experiment_variant' not in self._handlers:
            self._handlers['get_experiment_variant'] = GetExperimentVariantHandler(self.platform_service)
        return self._handlers['get_experiment_variant']

    @property
    def get_my_listings_handler(self) -> GetMyListingsHandler:
        """Get my listings query handler (v3.0.0)."""
        if 'get_my_listings' not in self._handlers:
            self._handlers['get_my_listings'] = GetMyListingsHandler(self.marketplace_service)
        return self._handlers['get_my_listings']

    @property
    def get_seller_stats_handler(self) -> GetSellerStatsHandler:
        """Get seller stats query handler (v3.0.0)."""
        if 'get_seller_stats' not in self._handlers:
            self._handlers['get_seller_stats'] = GetSellerStatsHandler(self.marketplace_service)
        return self._handlers['get_seller_stats']

    @property
    def get_leaderboard_handler(self) -> GetLeaderboardHandler:
        """Get leaderboard query handler (v3.0.0)."""
        if 'get_leaderboard' not in self._handlers:
            self._handlers['get_leaderboard'] = GetLeaderboardHandler(self.marketplace_service)
        return self._handlers['get_leaderboard']

    @property
    def get_my_reports_handler(self) -> GetMyReportsHandler:
        """Get my reports query handler (v3.0.0)."""
        if 'get_my_reports' not in self._handlers:
            self._handlers['get_my_reports'] = GetMyReportsHandler(self.support_service)
        return self._handlers['get_my_reports']

    # ========== Utility Methods ==========

    def reset(self):
        """Reset all cached instances (for testing)."""
        self._repositories.clear()
        self._services.clear()
        self._handlers.clear()
        logger.info("[Container] All instances reset")


# Module-level singleton accessor
@lru_cache(maxsize=1)
def get_container() -> Container:
    """Get the singleton container instance."""
    return Container()


# Convenience functions for FastAPI dependency injection
def get_billing_service() -> BillingService:
    """FastAPI dependency for billing service."""
    return get_container().billing_service


def get_identity_service() -> IdentityService:
    """FastAPI dependency for identity service."""
    return get_container().identity_service


def get_creation_service() -> CreationService:
    """FastAPI dependency for creation service."""
    return get_container().creation_service


def get_marketplace_service() -> MarketplaceService:
    """FastAPI dependency for marketplace service."""
    return get_container().marketplace_service


def get_platform_service() -> PlatformService:
    """FastAPI dependency for platform service."""
    return get_container().platform_service
